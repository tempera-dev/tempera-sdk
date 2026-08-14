//! Bounded hybrid authorization for Tempera resource servers.
//!
//! JWT access tokens are rejected locally when their structure, JOSE header,
//! signature, issuer, audience, lifetime, workspace, or scopes are invalid. A
//! successful local verification is still confirmed through Auth Hub
//! introspection on cache miss. Positive decisions are cached for at most a few
//! seconds, bounding revocation delay while removing a network round trip from
//! repeated requests. Opaque API keys always use central introspection.

use std::{
    collections::{BTreeSet, HashMap},
    fmt,
    sync::{
        Arc,
        atomic::{AtomicU64, Ordering},
    },
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

use async_trait::async_trait;
use base64::{Engine as _, engine::general_purpose::URL_SAFE_NO_PAD};
use futures_util::StreamExt as _;
use jsonwebtoken::{
    Algorithm, DecodingKey, Header, Validation, decode, decode_header,
    errors::ErrorKind as JwtErrorKind,
    jwk::{AlgorithmParameters, JwkSet, KeyAlgorithm, KeyOperations, PublicKeyUse},
};
use reqwest::{StatusCode, header};
use serde_json::{Map, Value, json};
use sha2::{Digest as _, Sha256};
use thiserror::Error;
use tokio::sync::Mutex;
use url::Url;

const DEFAULT_POSITIVE_CACHE_TTL: Duration = Duration::from_secs(5);
const DEFAULT_JWKS_CACHE_TTL: Duration = Duration::from_secs(300);
const DEFAULT_JWKS_REFRESH_COOLDOWN: Duration = Duration::from_secs(2);
const DEFAULT_MAX_CACHE_ENTRIES: usize = 8_192;
const DEFAULT_MAX_TOKEN_BYTES: usize = 16 * 1024;
const DEFAULT_MAX_RESPONSE_BYTES: usize = 64 * 1024;
const DEFAULT_CLOCK_SKEW_SECONDS: u64 = 30;
const MAX_JWKS_KEYS: usize = 32;

/// Runtime configuration for one resource audience.
#[derive(Clone)]
pub struct Config {
    /// Exact Auth Hub issuer URL.
    pub issuer_url: String,
    /// Exact resource audience accepted by this service.
    pub audience: String,
    /// Auth Hub JWKS URL.
    pub jwks_url: String,
    /// Auth Hub token-introspection URL.
    pub introspection_url: String,
    /// Resource-server credential used only for introspection.
    pub introspection_secret: Option<String>,
    /// Scopes required for every request through this authorizer.
    pub required_scopes: BTreeSet<String>,
    /// Maximum age of a positive central authorization decision.
    pub positive_cache_ttl: Duration,
    /// Maximum age of a successfully fetched JWKS set.
    pub jwks_cache_ttl: Duration,
    /// Minimum delay between failed/unknown-key JWKS refreshes.
    pub jwks_refresh_cooldown: Duration,
    /// Maximum positive authorization entries retained in memory.
    pub max_cache_entries: usize,
    /// Maximum accepted bearer-token size.
    pub max_token_bytes: usize,
    /// Maximum accepted JWKS or introspection response size.
    pub max_response_bytes: usize,
    /// Accepted clock skew for JWT temporal claims.
    pub clock_skew_seconds: u64,
    /// Require organization, project, and environment claims.
    pub require_workspace: bool,
    /// Permit HTTP authority URLs for explicit local development.
    pub allow_insecure_http: bool,
}

impl Config {
    /// Construct a configuration with secure production defaults.
    pub fn new(
        issuer_url: impl Into<String>,
        audience: impl Into<String>,
        jwks_url: impl Into<String>,
        introspection_url: impl Into<String>,
    ) -> Self {
        Self {
            issuer_url: issuer_url.into(),
            audience: audience.into(),
            jwks_url: jwks_url.into(),
            introspection_url: introspection_url.into(),
            introspection_secret: None,
            required_scopes: BTreeSet::new(),
            positive_cache_ttl: DEFAULT_POSITIVE_CACHE_TTL,
            jwks_cache_ttl: DEFAULT_JWKS_CACHE_TTL,
            jwks_refresh_cooldown: DEFAULT_JWKS_REFRESH_COOLDOWN,
            max_cache_entries: DEFAULT_MAX_CACHE_ENTRIES,
            max_token_bytes: DEFAULT_MAX_TOKEN_BYTES,
            max_response_bytes: DEFAULT_MAX_RESPONSE_BYTES,
            clock_skew_seconds: DEFAULT_CLOCK_SKEW_SECONDS,
            require_workspace: true,
            allow_insecure_http: false,
        }
    }

    /// Validate all security-sensitive bounds before serving traffic.
    pub fn validate(&self) -> Result<(), AuthError> {
        validate_authority_url(&self.issuer_url, self.allow_insecure_http, "issuer_url")?;
        validate_authority_url(&self.jwks_url, self.allow_insecure_http, "jwks_url")?;
        validate_authority_url(
            &self.introspection_url,
            self.allow_insecure_http,
            "introspection_url",
        )?;
        if !valid_audience(&self.audience) {
            return Err(AuthError::InvalidConfiguration(
                "audience must be a bounded URL-safe resource name".into(),
            ));
        }
        if self
            .required_scopes
            .iter()
            .any(|scope| !valid_scope(scope))
        {
            return Err(AuthError::InvalidConfiguration(
                "required scopes contain an invalid OAuth scope token".into(),
            ));
        }
        if self.positive_cache_ttl.is_zero()
            || self.positive_cache_ttl > Duration::from_secs(30)
            || self.jwks_cache_ttl < Duration::from_secs(30)
            || self.jwks_cache_ttl > Duration::from_secs(86_400)
            || self.jwks_refresh_cooldown.is_zero()
            || self.jwks_refresh_cooldown > self.jwks_cache_ttl
            || !(1..=1_000_000).contains(&self.max_cache_entries)
            || !(256..=65_536).contains(&self.max_token_bytes)
            || !(1_024..=16 * 1024 * 1024).contains(&self.max_response_bytes)
            || self.clock_skew_seconds > 300
        {
            return Err(AuthError::InvalidConfiguration(
                "authorization cache/JWT bounds are unsafe".into(),
            ));
        }
        if self
            .introspection_secret
            .as_deref()
            .is_some_and(|secret| secret.is_empty() || secret.len() > 4_096)
        {
            return Err(AuthError::InvalidConfiguration(
                "introspection secret is empty or oversized".into(),
            ));
        }
        Ok(())
    }
}

impl fmt::Debug for Config {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("Config")
            .field("issuer_url", &self.issuer_url)
            .field("audience", &self.audience)
            .field("jwks_url", &self.jwks_url)
            .field("introspection_url", &self.introspection_url)
            .field(
                "introspection_secret",
                &self.introspection_secret.as_ref().map(|_| "<redacted>"),
            )
            .field("required_scopes", &self.required_scopes)
            .field("positive_cache_ttl", &self.positive_cache_ttl)
            .field("jwks_cache_ttl", &self.jwks_cache_ttl)
            .field("jwks_refresh_cooldown", &self.jwks_refresh_cooldown)
            .field("max_cache_entries", &self.max_cache_entries)
            .field("max_token_bytes", &self.max_token_bytes)
            .field("max_response_bytes", &self.max_response_bytes)
            .field("clock_skew_seconds", &self.clock_skew_seconds)
            .field("require_workspace", &self.require_workspace)
            .field("allow_insecure_http", &self.allow_insecure_http)
            .finish()
    }
}

/// Verified identity returned to a resource server.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Principal {
    /// Stable Auth Hub subject.
    pub subject: String,
    /// OAuth client or resource-server identity.
    pub client_id: String,
    /// `access_token` or `api_key`.
    pub token_type: String,
    /// JWT JTI or API-key identifier.
    pub credential_id: String,
    /// Exact resource audience.
    pub audience: String,
    /// Organization claim.
    pub organization_id: Option<String>,
    /// Project claim.
    pub project_id: Option<String>,
    /// Environment claim.
    pub environment_id: Option<String>,
    /// Current scopes.
    pub scopes: BTreeSet<String>,
    /// JWT expiration, when present.
    pub expires_at_epoch_seconds: Option<u64>,
    /// User security epoch, when present.
    pub security_epoch: Option<u64>,
    /// OAuth grant identifier, when present.
    pub grant_id: Option<String>,
    /// Sanitized authority claims for application-specific use.
    pub claims: Map<String, Value>,
}

impl Principal {
    /// Return whether the principal carries one scope or wildcard authority.
    pub fn has_scope(&self, scope: &str) -> bool {
        self.scopes.contains(scope) || self.scopes.contains("*")
    }
}

/// Stable authorization failure vocabulary for resource servers.
#[derive(Debug, Error, Eq, PartialEq)]
pub enum AuthError {
    /// The presented credential is malformed, expired, revoked, or unknown.
    #[error("invalid credential")]
    InvalidToken,
    /// The credential was issued by a different authority.
    #[error("wrong token issuer")]
    WrongIssuer,
    /// The credential targets another resource.
    #[error("wrong token audience")]
    WrongAudience,
    /// The credential lacks a required scope.
    #[error("missing required scope: {0}")]
    MissingScope(String),
    /// Local JWT claims disagree with the central authority decision.
    #[error("local and central authorization claims disagree")]
    ClaimMismatch,
    /// The central authority or JWKS endpoint is unavailable or malformed.
    #[error("authorization authority unavailable")]
    Unavailable,
    /// Runtime configuration is invalid.
    #[error("invalid authorization configuration: {0}")]
    InvalidConfiguration(String),
}

/// Transport boundary used by the runtime. Tests can provide a deterministic
/// authority without opening sockets.
#[async_trait]
pub trait AuthorityTransport: Send + Sync + 'static {
    /// Fetch one JWKS document as JSON.
    async fn fetch_jwks(&self, url: &str, max_bytes: usize) -> Result<Value, AuthError>;

    /// Introspect one opaque credential or access token.
    async fn introspect(
        &self,
        url: &str,
        secret: Option<&str>,
        token: &str,
        max_bytes: usize,
    ) -> Result<Value, AuthError>;
}

/// Reqwest-backed authority transport with bounded responses and no redirects.
#[derive(Clone)]
pub struct ReqwestAuthorityTransport {
    client: reqwest::Client,
}

impl ReqwestAuthorityTransport {
    /// Construct the production transport.
    pub fn new(connect_timeout: Duration, request_timeout: Duration) -> Result<Self, AuthError> {
        let client = reqwest::Client::builder()
            .connect_timeout(connect_timeout)
            .timeout(request_timeout)
            .redirect(reqwest::redirect::Policy::none())
            .no_proxy()
            .build()
            .map_err(|_| AuthError::InvalidConfiguration("failed to build HTTP client".into()))?;
        Ok(Self { client })
    }
}

impl Default for ReqwestAuthorityTransport {
    fn default() -> Self {
        Self::new(Duration::from_secs(3), Duration::from_secs(5))
            .expect("default reqwest authority transport must be constructible")
    }
}

#[async_trait]
impl AuthorityTransport for ReqwestAuthorityTransport {
    async fn fetch_jwks(&self, url: &str, max_bytes: usize) -> Result<Value, AuthError> {
        let response = self
            .client
            .get(url)
            .header(header::ACCEPT, "application/jwk-set+json, application/json")
            .send()
            .await
            .map_err(|_| AuthError::Unavailable)?;
        if !response.status().is_success() || !json_content_type(response.headers()) {
            return Err(AuthError::Unavailable);
        }
        let body = bounded_response_bytes(response, max_bytes).await?;
        serde_json::from_slice(&body).map_err(|_| AuthError::Unavailable)
    }

    async fn introspect(
        &self,
        url: &str,
        secret: Option<&str>,
        token: &str,
        max_bytes: usize,
    ) -> Result<Value, AuthError> {
        let mut request = self.client.post(url).json(&json!({ "token": token }));
        if let Some(secret) = secret.filter(|secret| !secret.is_empty()) {
            request = request.bearer_auth(secret);
        }
        let response = request
            .send()
            .await
            .map_err(|_| AuthError::Unavailable)?;
        let status = response.status();
        if status.is_server_error() || status == StatusCode::TOO_MANY_REQUESTS {
            return Err(AuthError::Unavailable);
        }
        if !status.is_success() {
            return Err(AuthError::InvalidToken);
        }
        if !json_content_type(response.headers()) {
            return Err(AuthError::Unavailable);
        }
        let body = bounded_response_bytes(response, max_bytes).await?;
        serde_json::from_slice(&body).map_err(|_| AuthError::Unavailable)
    }
}

#[derive(Clone)]
struct CacheEntry {
    principal: Principal,
    expires_at: Instant,
}

#[derive(Clone)]
struct CachedJwk {
    key: DecodingKey,
}

#[derive(Default)]
struct JwksCache {
    keys: HashMap<String, CachedJwk>,
    expires_at: Option<Instant>,
    last_refresh_attempt: Option<Instant>,
}

#[derive(Default)]
struct Metrics {
    cache_hits: AtomicU64,
    cache_misses: AtomicU64,
    local_jwt_rejections: AtomicU64,
    introspections: AtomicU64,
    authority_failures: AtomicU64,
    claim_mismatches: AtomicU64,
}

/// Snapshot of runtime counters. No credential values are retained.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct MetricsSnapshot {
    /// Positive-cache hits.
    pub cache_hits: u64,
    /// Positive-cache misses.
    pub cache_misses: u64,
    /// JWTs rejected before contacting Auth Hub.
    pub local_jwt_rejections: u64,
    /// Central introspection requests.
    pub introspections: u64,
    /// Unavailable/malformed authority responses.
    pub authority_failures: u64,
    /// Local JWT and central claim mismatches.
    pub claim_mismatches: u64,
}

/// Hybrid local-verification and central-freshness authorizer.
pub struct HybridAuthorizer<T = ReqwestAuthorityTransport> {
    config: Config,
    transport: T,
    cache: Mutex<HashMap<[u8; 32], CacheEntry>>,
    flights: Mutex<HashMap<[u8; 32], Arc<Mutex<()>>>>,
    jwks: Mutex<JwksCache>,
    metrics: Metrics,
}

impl HybridAuthorizer<ReqwestAuthorityTransport> {
    /// Construct a production authorizer using the default reqwest transport.
    pub fn new(config: Config) -> Result<Self, AuthError> {
        Self::with_transport(config, ReqwestAuthorityTransport::default())
    }
}

impl<T: AuthorityTransport> HybridAuthorizer<T> {
    /// Construct an authorizer with an explicit transport.
    pub fn with_transport(config: Config, transport: T) -> Result<Self, AuthError> {
        config.validate()?;
        Ok(Self {
            config,
            transport,
            cache: Mutex::new(HashMap::new()),
            flights: Mutex::new(HashMap::new()),
            jwks: Mutex::new(JwksCache::default()),
            metrics: Metrics::default(),
        })
    }

    /// Authorize one bearer credential.
    ///
    /// `required_scopes` are operation-specific and are checked in addition to
    /// the baseline scopes configured for this service.
    pub async fn authorize(
        &self,
        token: &str,
        required_scopes: &[&str],
    ) -> Result<Principal, AuthError> {
        if token.is_empty() || token.len() > self.config.max_token_bytes {
            return Err(AuthError::InvalidToken);
        }
        for scope in required_scopes {
            if !valid_scope(scope) {
                return Err(AuthError::InvalidConfiguration(
                    "operation scope is invalid".into(),
                ));
            }
        }

        let cache_key: [u8; 32] = Sha256::digest(token.as_bytes()).into();
        if let Some(principal) = self.cached(cache_key).await {
            self.metrics.cache_hits.fetch_add(1, Ordering::Relaxed);
            require_scopes(&principal, &self.config.required_scopes, required_scopes)?;
            return Ok(principal);
        }
        self.metrics.cache_misses.fetch_add(1, Ordering::Relaxed);

        let flight = {
            let mut flights = self.flights.lock().await;
            flights
                .entry(cache_key)
                .or_insert_with(|| Arc::new(Mutex::new(())))
                .clone()
        };
        let guard = flight.lock().await;
        if let Some(principal) = self.cached(cache_key).await {
            self.metrics.cache_hits.fetch_add(1, Ordering::Relaxed);
            require_scopes(&principal, &self.config.required_scopes, required_scopes)?;
            drop(guard);
            self.remove_flight(cache_key, &flight).await;
            return Ok(principal);
        }

        let result = self.authorize_uncached(token).await;
        if let Ok(principal) = &result {
            require_scopes(principal, &self.config.required_scopes, required_scopes)?;
            self.store(cache_key, principal.clone()).await;
        }
        drop(guard);
        self.remove_flight(cache_key, &flight).await;
        result
    }

    /// Return a lock-free snapshot of authorization counters.
    pub fn metrics(&self) -> MetricsSnapshot {
        MetricsSnapshot {
            cache_hits: self.metrics.cache_hits.load(Ordering::Relaxed),
            cache_misses: self.metrics.cache_misses.load(Ordering::Relaxed),
            local_jwt_rejections: self.metrics.local_jwt_rejections.load(Ordering::Relaxed),
            introspections: self.metrics.introspections.load(Ordering::Relaxed),
            authority_failures: self.metrics.authority_failures.load(Ordering::Relaxed),
            claim_mismatches: self.metrics.claim_mismatches.load(Ordering::Relaxed),
        }
    }

    async fn authorize_uncached(&self, token: &str) -> Result<Principal, AuthError> {
        let local = if jwt_shaped(token) {
            match self.verify_jwt(token).await {
                Ok(principal) => Some(principal),
                Err(error) => {
                    self.metrics
                        .local_jwt_rejections
                        .fetch_add(1, Ordering::Relaxed);
                    return Err(error);
                }
            }
        } else {
            None
        };

        self.metrics.introspections.fetch_add(1, Ordering::Relaxed);
        let claims = self
            .transport
            .introspect(
                &self.config.introspection_url,
                self.config.introspection_secret.as_deref(),
                token,
                self.config.max_response_bytes,
            )
            .await
            .inspect_err(|error| {
                if error == &AuthError::Unavailable {
                    self.metrics
                        .authority_failures
                        .fetch_add(1, Ordering::Relaxed);
                }
            })?;
        let central = self.principal_from_claims(&claims, true)?;
        if let Some(local) = local
            && !equivalent_authority(&local, &central)
        {
            self.metrics
                .claim_mismatches
                .fetch_add(1, Ordering::Relaxed);
            return Err(AuthError::ClaimMismatch);
        }
        Ok(central)
    }

    async fn verify_jwt(&self, token: &str) -> Result<Principal, AuthError> {
        let header = decode_header(token).map_err(|_| AuthError::InvalidToken)?;
        validate_jwt_header(&header)?;
        if header.alg != Algorithm::RS256 {
            return Err(AuthError::InvalidToken);
        }
        let kid = header.kid.as_deref().ok_or(AuthError::InvalidToken)?;
        if !valid_key_id(kid) {
            return Err(AuthError::InvalidToken);
        }
        let issuer = unverified_jwt_issuer(token, self.config.max_token_bytes)?;
        if issuer != self.config.issuer_url {
            return Err(AuthError::WrongIssuer);
        }
        let key = self.jwks_key(kid).await?;
        let mut validation = Validation::new(Algorithm::RS256);
        validation.leeway = self.config.clock_skew_seconds;
        validation.validate_nbf = true;
        validation.set_required_spec_claims(&["exp", "iss", "aud", "sub", "jti"]);
        validation.set_issuer(&[self.config.issuer_url.as_str()]);
        validation.set_audience(&[self.config.audience.as_str()]);
        let claims = decode::<Value>(token, &key, &validation)
            .map_err(jwt_decode_failure)?
            .claims;
        self.principal_from_claims(&claims, false)
    }

    async fn jwks_key(&self, kid: &str) -> Result<DecodingKey, AuthError> {
        let mut cache = self.jwks.lock().await;
        let now = Instant::now();
        if cache.expires_at.is_some_and(|expiry| expiry > now) {
            if let Some(key) = cache.keys.get(kid) {
                return Ok(key.key.clone());
            }
            if cache.last_refresh_attempt.is_some_and(|attempt| {
                now.saturating_duration_since(attempt) < self.config.jwks_refresh_cooldown
            }) {
                return Err(AuthError::InvalidToken);
            }
        } else if cache.last_refresh_attempt.is_some_and(|attempt| {
            now.saturating_duration_since(attempt) < self.config.jwks_refresh_cooldown
        }) {
            return Err(AuthError::Unavailable);
        }

        cache.last_refresh_attempt = Some(now);
        let document = self
            .transport
            .fetch_jwks(&self.config.jwks_url, self.config.max_response_bytes)
            .await
            .inspect_err(|_| {
                self.metrics
                    .authority_failures
                    .fetch_add(1, Ordering::Relaxed);
            })?;
        cache.keys = parse_jwks(document)?;
        cache.expires_at = Some(Instant::now() + self.config.jwks_cache_ttl);
        cache
            .keys
            .get(kid)
            .map(|key| key.key.clone())
            .ok_or(AuthError::InvalidToken)
    }

    fn principal_from_claims(
        &self,
        claims: &Value,
        require_active: bool,
    ) -> Result<Principal, AuthError> {
        if require_active && claims.get("active").and_then(Value::as_bool) != Some(true) {
            return Err(AuthError::InvalidToken);
        }
        let issuer = claims
            .get("iss")
            .and_then(Value::as_str)
            .ok_or(AuthError::WrongIssuer)?;
        if issuer != self.config.issuer_url {
            return Err(AuthError::WrongIssuer);
        }
        let audiences = string_set(claims.get("aud"));
        if !audiences.contains(&self.config.audience) {
            return Err(AuthError::WrongAudience);
        }
        let mut scopes = string_set(claims.get("scope"));
        scopes.extend(string_set(claims.get("scopes")));
        let subject = claim_string(claims, "sub").ok_or(AuthError::InvalidToken)?;
        let token_type = claim_string(claims, "token_type")
            .unwrap_or_else(|| "access_token".into());
        if token_type != "access_token" && token_type != "api_key" {
            return Err(AuthError::InvalidToken);
        }
        let credential_id = if token_type == "api_key" {
            claim_string(claims, "api_key_id")
        } else {
            claim_string(claims, "jti")
        }
        .ok_or(AuthError::InvalidToken)?;
        let organization_id = claim_string(claims, "org_id")
            .or_else(|| claim_string(claims, "organization_id"));
        let project_id = claim_string(claims, "project_id");
        let environment_id = claim_string(claims, "environment_id");
        if self.config.require_workspace
            && (organization_id.is_none() || project_id.is_none() || environment_id.is_none())
        {
            return Err(AuthError::InvalidToken);
        }
        let expires_at_epoch_seconds = claims.get("exp").and_then(Value::as_u64);
        if token_type == "access_token" && expires_at_epoch_seconds.is_none() {
            return Err(AuthError::InvalidToken);
        }
        if expires_at_epoch_seconds.is_some_and(|expiry| expiry <= unix_time_seconds()) {
            return Err(AuthError::InvalidToken);
        }
        let client_id = claim_string(claims, "client_id")
            .or_else(|| claim_string(claims, "azp"))
            .unwrap_or_else(|| self.config.audience.clone());
        let mut object = claims.as_object().cloned().unwrap_or_default();
        for field in [
            "token",
            "access_token",
            "refresh_token",
            "client_secret",
            "introspection_secret",
        ] {
            object.remove(field);
        }
        Ok(Principal {
            subject,
            client_id,
            token_type,
            credential_id,
            audience: self.config.audience.clone(),
            organization_id,
            project_id,
            environment_id,
            scopes,
            expires_at_epoch_seconds,
            security_epoch: claims.get("security_epoch").and_then(Value::as_u64),
            grant_id: claim_string(claims, "grant_id"),
            claims: object,
        })
    }

    async fn cached(&self, key: [u8; 32]) -> Option<Principal> {
        let mut cache = self.cache.lock().await;
        let now = Instant::now();
        cache.retain(|_, entry| entry.expires_at > now);
        cache.get(&key).map(|entry| entry.principal.clone())
    }

    async fn store(&self, key: [u8; 32], principal: Principal) {
        let now_epoch = unix_time_seconds();
        let token_ttl = principal
            .expires_at_epoch_seconds
            .map_or(self.config.positive_cache_ttl.as_secs(), |expiry| {
                expiry.saturating_sub(now_epoch)
            });
        let ttl = self.config.positive_cache_ttl.min(Duration::from_secs(token_ttl));
        if ttl.is_zero() {
            return;
        }
        let mut cache = self.cache.lock().await;
        let now = Instant::now();
        cache.retain(|_, entry| entry.expires_at > now);
        if cache.len() >= self.config.max_cache_entries
            && let Some(oldest) = cache
                .iter()
                .min_by_key(|(_, entry)| entry.expires_at)
                .map(|(key, _)| *key)
        {
            cache.remove(&oldest);
        }
        cache.insert(
            key,
            CacheEntry {
                principal,
                expires_at: now + ttl,
            },
        );
    }

    async fn remove_flight(&self, key: [u8; 32], flight: &Arc<Mutex<()>>) {
        let mut flights = self.flights.lock().await;
        if flights
            .get(&key)
            .is_some_and(|existing| Arc::ptr_eq(existing, flight))
        {
            flights.remove(&key);
        }
    }
}

fn require_scopes(
    principal: &Principal,
    baseline: &BTreeSet<String>,
    operation: &[&str],
) -> Result<(), AuthError> {
    baseline
        .iter()
        .map(String::as_str)
        .chain(operation.iter().copied())
        .find(|scope| !principal.has_scope(scope))
        .map_or(Ok(()), |scope| Err(AuthError::MissingScope(scope.into())))
}

fn equivalent_authority(local: &Principal, central: &Principal) -> bool {
    local.token_type == "access_token"
        && central.token_type == "access_token"
        && local.subject == central.subject
        && local.client_id == central.client_id
        && local.credential_id == central.credential_id
        && local.audience == central.audience
        && local.organization_id == central.organization_id
        && local.project_id == central.project_id
        && local.environment_id == central.environment_id
        && local.scopes == central.scopes
        && local.expires_at_epoch_seconds == central.expires_at_epoch_seconds
        && local.security_epoch == central.security_epoch
        && local.grant_id == central.grant_id
}

fn parse_jwks(document: Value) -> Result<HashMap<String, CachedJwk>, AuthError> {
    let raw_keys = document
        .get("keys")
        .and_then(Value::as_array)
        .ok_or(AuthError::Unavailable)?;
    if raw_keys.is_empty() || raw_keys.len() > MAX_JWKS_KEYS {
        return Err(AuthError::Unavailable);
    }
    for raw in raw_keys {
        let object = raw.as_object().ok_or(AuthError::Unavailable)?;
        if ["d", "p", "q", "dp", "dq", "qi", "oth", "k"]
            .iter()
            .any(|field| object.contains_key(*field))
        {
            return Err(AuthError::Unavailable);
        }
    }
    let jwks: JwkSet = serde_json::from_value(document).map_err(|_| AuthError::Unavailable)?;
    let mut keys = HashMap::with_capacity(jwks.keys.len());
    for jwk in &jwks.keys {
        if !matches!(jwk.algorithm, AlgorithmParameters::RSA(_)) {
            continue;
        }
        let Some(kid) = jwk.common.key_id.as_deref() else {
            continue;
        };
        if !valid_key_id(kid) || keys.contains_key(kid) {
            return Err(AuthError::Unavailable);
        }
        if jwk
            .common
            .public_key_use
            .as_ref()
            .is_some_and(|usage| usage != &PublicKeyUse::Signature)
            || jwk
                .common
                .key_operations
                .as_ref()
                .is_some_and(|operations| !operations.contains(&KeyOperations::Verify))
            || jwk
                .common
                .key_algorithm
                .is_some_and(|algorithm| algorithm != KeyAlgorithm::RS256)
        {
            continue;
        }
        let key = DecodingKey::from_jwk(jwk).map_err(|_| AuthError::Unavailable)?;
        keys.insert(kid.to_owned(), CachedJwk { key });
    }
    (!keys.is_empty()).then_some(keys).ok_or(AuthError::Unavailable)
}

fn validate_jwt_header(header: &Header) -> Result<(), AuthError> {
    if header.jku.is_some()
        || header.jwk.is_some()
        || header.x5u.is_some()
        || header.x5c.is_some()
        || header.crit.is_some()
        || header.enc.is_some()
        || header.zip.is_some()
    {
        return Err(AuthError::InvalidToken);
    }
    if header.typ.as_deref().is_some_and(|value| {
        !value.eq_ignore_ascii_case("JWT") && !value.eq_ignore_ascii_case("at+jwt")
    }) {
        return Err(AuthError::InvalidToken);
    }
    Ok(())
}

fn unverified_jwt_issuer(token: &str, max_bytes: usize) -> Result<String, AuthError> {
    let mut parts = token.split('.');
    let (Some(_header), Some(payload), Some(_signature), None) =
        (parts.next(), parts.next(), parts.next(), parts.next())
    else {
        return Err(AuthError::InvalidToken);
    };
    if payload.is_empty() || payload.len() > max_bytes {
        return Err(AuthError::InvalidToken);
    }
    let decoded = URL_SAFE_NO_PAD
        .decode(payload)
        .map_err(|_| AuthError::InvalidToken)?;
    if decoded.len() > max_bytes {
        return Err(AuthError::InvalidToken);
    }
    let claims: Value = serde_json::from_slice(&decoded).map_err(|_| AuthError::InvalidToken)?;
    let issuer = claims
        .get("iss")
        .and_then(Value::as_str)
        .ok_or(AuthError::WrongIssuer)?;
    if issuer.is_empty()
        || issuer.len() > 2_048
        || issuer
            .bytes()
            .any(|byte| byte.is_ascii_control() || byte.is_ascii_whitespace())
    {
        return Err(AuthError::WrongIssuer);
    }
    Ok(issuer.to_owned())
}

fn jwt_decode_failure(error: jsonwebtoken::errors::Error) -> AuthError {
    match error.kind() {
        JwtErrorKind::InvalidAudience => AuthError::WrongAudience,
        JwtErrorKind::InvalidIssuer => AuthError::WrongIssuer,
        _ => AuthError::InvalidToken,
    }
}

fn claim_string(claims: &Value, name: &str) -> Option<String> {
    claims
        .get(name)
        .and_then(Value::as_str)
        .filter(|value| !value.is_empty() && value.len() <= 4_096)
        .map(str::to_owned)
}

fn string_set(value: Option<&Value>) -> BTreeSet<String> {
    match value {
        Some(Value::String(value)) => value
            .split_whitespace()
            .filter(|item| valid_scope(item) || valid_audience(item))
            .map(str::to_owned)
            .collect(),
        Some(Value::Array(values)) => values
            .iter()
            .filter_map(Value::as_str)
            .filter(|item| valid_scope(item) || valid_audience(item))
            .map(str::to_owned)
            .collect(),
        _ => BTreeSet::new(),
    }
}

fn jwt_shaped(token: &str) -> bool {
    token.split('.').count() == 3
}

fn valid_key_id(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value
            .bytes()
            .all(|byte| matches!(byte, 0x21..=0x7e))
}

fn valid_audience(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || b"._~-:/".contains(&byte))
}

fn valid_scope(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 256
        && value
            .bytes()
            .all(|byte| matches!(byte, 0x21 | 0x23..=0x5b | 0x5d..=0x7e))
}

fn validate_authority_url(value: &str, allow_http: bool, name: &str) -> Result<(), AuthError> {
    let url = Url::parse(value).map_err(|_| {
        AuthError::InvalidConfiguration(format!("{name} must be an absolute URL"))
    })?;
    if url.username() != "" || url.password().is_some() || url.query().is_some() || url.fragment().is_some() {
        return Err(AuthError::InvalidConfiguration(format!(
            "{name} must not contain credentials, query, or fragment"
        )));
    }
    if url.scheme() != "https" && !(allow_http && url.scheme() == "http") {
        return Err(AuthError::InvalidConfiguration(format!(
            "{name} must use HTTPS"
        )));
    }
    Ok(())
}

fn json_content_type(headers: &reqwest::header::HeaderMap) -> bool {
    let mut values = headers.get_all(header::CONTENT_TYPE).iter();
    let Some(value) = values.next() else {
        return false;
    };
    if values.next().is_some() {
        return false;
    }
    value.to_str().ok().is_some_and(|value| {
        matches!(
            value
                .split(';')
                .next()
                .unwrap_or_default()
                .trim()
                .to_ascii_lowercase()
                .as_str(),
            "application/json" | "application/jwk-set+json"
        )
    })
}

async fn bounded_response_bytes(
    response: reqwest::Response,
    max_bytes: usize,
) -> Result<Vec<u8>, AuthError> {
    if response
        .content_length()
        .is_some_and(|length| length > max_bytes as u64)
    {
        return Err(AuthError::Unavailable);
    }
    let mut body = Vec::with_capacity(
        response
            .content_length()
            .and_then(|length| usize::try_from(length).ok())
            .unwrap_or_default()
            .min(max_bytes),
    );
    let mut stream = response.bytes_stream();
    while let Some(chunk) = stream.next().await {
        let chunk = chunk.map_err(|_| AuthError::Unavailable)?;
        if body
            .len()
            .checked_add(chunk.len())
            .is_none_or(|length| length > max_bytes)
        {
            return Err(AuthError::Unavailable);
        }
        body.extend_from_slice(&chunk);
    }
    Ok(body)
}

fn unix_time_seconds() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}
