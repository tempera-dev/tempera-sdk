//! Bounded hybrid authorization for Tempera resource servers.
//!
//! JWT access tokens are rejected locally when their structure, JOSE header,
//! signature, issuer, audience, lifetime, workspace, or scopes are invalid. A
//! successful local verification is still confirmed through Auth Hub
//! introspection on cache miss. Positive decisions are cached for at most a few
//! seconds, bounding revocation delay while removing a network round trip from
//! repeated requests. Opaque API keys always use central introspection.

use std::{
    cmp::Reverse,
    collections::{BTreeSet, BinaryHeap, HashMap},
    fmt,
    sync::{
        Arc, Mutex as StdMutex,
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
use reqwest::header;
use serde_json::{Map, Value, json};
use sha2::{Digest as _, Sha256};
use thiserror::Error;
use tokio::sync::{Mutex, Semaphore};
use url::{Host, Url};

const DEFAULT_POSITIVE_CACHE_TTL: Duration = Duration::from_secs(5);
const DEFAULT_JWKS_CACHE_TTL: Duration = Duration::from_mins(5);
const DEFAULT_JWKS_REFRESH_COOLDOWN: Duration = Duration::from_secs(2);
const DEFAULT_MAX_CACHE_ENTRIES: usize = 8_192;
const DEFAULT_MAX_ACTIVE_FLIGHTS: usize = 4_096;
const DEFAULT_MAX_WAITERS_PER_FLIGHT: usize = 256;
const DEFAULT_MAX_INTROSPECTION_IN_FLIGHT: usize = 128;
const DEFAULT_INTROSPECTION_QUEUE_TIMEOUT: Duration = Duration::from_millis(250);
const DEFAULT_MAX_TOKEN_BYTES: usize = 16 * 1024;
const DEFAULT_MAX_RESPONSE_BYTES: usize = 64 * 1024;
const DEFAULT_CLOCK_SKEW_SECONDS: u64 = 30;
const DEFAULT_MAX_ACCESS_TOKEN_LIFETIME_SECONDS: u64 = 3_600;
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
    /// Maximum distinct credential misses coordinated at once.
    pub max_active_flights: usize,
    /// Maximum waiting callers behind one credential's active authorization.
    pub max_waiters_per_flight: usize,
    /// Maximum central introspection requests running concurrently.
    pub max_introspection_in_flight: usize,
    /// Maximum time a central introspection request may wait for admission.
    pub introspection_queue_timeout: Duration,
    /// Maximum accepted bearer-token size.
    pub max_token_bytes: usize,
    /// Maximum accepted JWKS or introspection response size.
    pub max_response_bytes: usize,
    /// Accepted clock skew for JWT temporal claims.
    pub clock_skew_seconds: u64,
    /// Maximum permitted access-token lifetime (`exp - iat`).
    pub max_access_token_lifetime_seconds: u64,
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
            max_active_flights: DEFAULT_MAX_ACTIVE_FLIGHTS,
            max_waiters_per_flight: DEFAULT_MAX_WAITERS_PER_FLIGHT,
            max_introspection_in_flight: DEFAULT_MAX_INTROSPECTION_IN_FLIGHT,
            introspection_queue_timeout: DEFAULT_INTROSPECTION_QUEUE_TIMEOUT,
            max_token_bytes: DEFAULT_MAX_TOKEN_BYTES,
            max_response_bytes: DEFAULT_MAX_RESPONSE_BYTES,
            clock_skew_seconds: DEFAULT_CLOCK_SKEW_SECONDS,
            max_access_token_lifetime_seconds: DEFAULT_MAX_ACCESS_TOKEN_LIFETIME_SECONDS,
            require_workspace: true,
            allow_insecure_http: false,
        }
    }

    /// Validate all security-sensitive bounds before serving traffic.
    pub fn validate(&self) -> Result<(), AuthError> {
        let issuer =
            validate_authority_url(&self.issuer_url, self.allow_insecure_http, "issuer_url")?;
        let jwks = validate_authority_url(&self.jwks_url, self.allow_insecure_http, "jwks_url")?;
        let introspection = validate_authority_url(
            &self.introspection_url,
            self.allow_insecure_http,
            "introspection_url",
        )?;
        if !same_origin(&issuer, &jwks) || !same_origin(&issuer, &introspection) {
            return Err(AuthError::InvalidConfiguration(
                "JWKS and introspection endpoints must share the issuer origin".into(),
            ));
        }
        if !is_loopback_url(&issuer) && self.introspection_secret.is_none() {
            return Err(AuthError::InvalidConfiguration(
                "hosted introspection requires a resource-server secret".into(),
            ));
        }
        if !valid_audience(&self.audience)
            || self.required_scopes.len() > 256
            || self.required_scopes.iter().any(|scope| !valid_scope(scope))
            || self.positive_cache_ttl.is_zero()
            || self.positive_cache_ttl > Duration::from_secs(30)
            || self.jwks_cache_ttl < Duration::from_secs(30)
            || self.jwks_cache_ttl > Duration::from_hours(24)
            || self.jwks_refresh_cooldown.is_zero()
            || self.jwks_refresh_cooldown > self.jwks_cache_ttl
            || !(1..=1_000_000).contains(&self.max_cache_entries)
            || !(1..=1_000_000).contains(&self.max_active_flights)
            || self.max_waiters_per_flight > 65_536
            || !(1..=65_536).contains(&self.max_introspection_in_flight)
            || self.introspection_queue_timeout < Duration::from_millis(1)
            || self.introspection_queue_timeout > Duration::from_secs(30)
            || !(256..=65_536).contains(&self.max_token_bytes)
            || !(1_024..=16 * 1024 * 1024).contains(&self.max_response_bytes)
            || self.clock_skew_seconds > 300
            || !(60..=86_400).contains(&self.max_access_token_lifetime_seconds)
        {
            return Err(AuthError::InvalidConfiguration(
                "authorization configuration is outside safe bounds".into(),
            ));
        }
        if self.introspection_secret.as_deref().is_some_and(|secret| {
            secret.is_empty()
                || secret.len() > 4_096
                || secret.bytes().any(|b| b.is_ascii_control())
        }) {
            return Err(AuthError::InvalidConfiguration(
                "introspection secret is empty, oversized, or contains control characters".into(),
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
            .field("max_active_flights", &self.max_active_flights)
            .field("max_waiters_per_flight", &self.max_waiters_per_flight)
            .field(
                "max_introspection_in_flight",
                &self.max_introspection_in_flight,
            )
            .field(
                "introspection_queue_timeout",
                &self.introspection_queue_timeout,
            )
            .field("max_token_bytes", &self.max_token_bytes)
            .field("max_response_bytes", &self.max_response_bytes)
            .field("clock_skew_seconds", &self.clock_skew_seconds)
            .field(
                "max_access_token_lifetime_seconds",
                &self.max_access_token_lifetime_seconds,
            )
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
    /// JWT issuance time, when present.
    pub issued_at_epoch_seconds: Option<u64>,
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
        let response = request.send().await.map_err(|_| AuthError::Unavailable)?;
        let status = response.status();
        // Auth Hub represents an invalid credential with a successful
        // `active: false` response. Any HTTP failure therefore means the
        // authority, route, or resource-server credential is unavailable or
        // misconfigured; it must not be reported as a bad caller token.
        if !status.is_success() {
            return Err(AuthError::Unavailable);
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
    generation: u64,
}

#[derive(Default)]
struct PositiveCache {
    entries: HashMap<[u8; 32], CacheEntry>,
    expirations: BinaryHeap<Reverse<(Instant, u64, [u8; 32])>>,
    next_generation: u64,
}

impl PositiveCache {
    fn get(&mut self, key: [u8; 32], now: Instant) -> Option<Principal> {
        self.prune_expired(now);
        if self
            .entries
            .get(&key)
            .is_some_and(|entry| entry.expires_at <= now)
        {
            self.entries.remove(&key);
            return None;
        }
        self.entries.get(&key).map(|entry| entry.principal.clone())
    }

    fn insert(
        &mut self,
        key: [u8; 32],
        principal: Principal,
        expires_at: Instant,
        max_entries: usize,
    ) -> bool {
        self.prune_expired(Instant::now());
        let evicted = !self.entries.contains_key(&key)
            && self.entries.len() >= max_entries
            && self.evict_soonest_live();
        self.next_generation = self.next_generation.wrapping_add(1).max(1);
        let generation = self.next_generation;
        self.entries.insert(
            key,
            CacheEntry {
                principal,
                expires_at,
                generation,
            },
        );
        self.expirations
            .push(Reverse((expires_at, generation, key)));
        evicted
    }

    fn prune_expired(&mut self, now: Instant) {
        while let Some(Reverse((expires_at, generation, key))) = self.expirations.peek().copied() {
            if expires_at > now {
                break;
            }
            self.expirations.pop();
            if self
                .entries
                .get(&key)
                .is_some_and(|entry| entry.generation == generation && entry.expires_at <= now)
            {
                self.entries.remove(&key);
            }
        }
    }

    fn evict_soonest_live(&mut self) -> bool {
        while let Some(Reverse((_expires_at, generation, key))) = self.expirations.pop() {
            if self
                .entries
                .get(&key)
                .is_some_and(|entry| entry.generation == generation)
            {
                self.entries.remove(&key);
                return true;
            }
        }
        if let Some(key) = self.entries.keys().next().copied() {
            self.entries.remove(&key);
            return true;
        }
        false
    }

    fn len(&self) -> usize {
        self.entries.len()
    }
}

struct FlightEntry {
    gate: Arc<Mutex<()>>,
    users: usize,
}

struct FlightLease {
    key: [u8; 32],
    gate: Arc<Mutex<()>>,
    flights: Arc<StdMutex<HashMap<[u8; 32], FlightEntry>>>,
}

impl FlightLease {
    fn acquire(
        flights: &Arc<StdMutex<HashMap<[u8; 32], FlightEntry>>>,
        key: [u8; 32],
        max_active_flights: usize,
        max_waiters_per_flight: usize,
    ) -> Result<Self, AuthError> {
        let mut entries = lock_recover(flights);
        let gate = if let Some(entry) = entries.get_mut(&key) {
            if entry.users.saturating_sub(1) >= max_waiters_per_flight {
                return Err(AuthError::Unavailable);
            }
            entry.users = entry.users.saturating_add(1);
            Arc::clone(&entry.gate)
        } else {
            if entries.len() >= max_active_flights {
                return Err(AuthError::Unavailable);
            }
            let gate = Arc::new(Mutex::new(()));
            entries.insert(
                key,
                FlightEntry {
                    gate: Arc::clone(&gate),
                    users: 1,
                },
            );
            gate
        };
        Ok(Self {
            key,
            gate,
            flights: Arc::clone(flights),
        })
    }
}

impl Drop for FlightLease {
    fn drop(&mut self) {
        let mut entries = lock_recover(&self.flights);
        let should_remove = entries.get_mut(&self.key).is_some_and(|entry| {
            if !Arc::ptr_eq(&entry.gate, &self.gate) {
                return false;
            }
            if entry.users > 1 {
                entry.users -= 1;
                false
            } else {
                true
            }
        });
        if should_remove {
            entries.remove(&self.key);
        }
    }
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
    generation: u64,
}

#[derive(Default)]
struct Metrics {
    cache_hits: AtomicU64,
    cache_misses: AtomicU64,
    local_jwt_rejections: AtomicU64,
    introspections: AtomicU64,
    authority_failures: AtomicU64,
    claim_mismatches: AtomicU64,
    cache_evictions: AtomicU64,
    coordination_rejections: AtomicU64,
    introspection_admission_rejections: AtomicU64,
    jwks_refreshes: AtomicU64,
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
    /// Positive authorization entries evicted at the configured bound.
    pub cache_evictions: u64,
    /// Current positive authorization entries.
    pub positive_cache_entries: usize,
    /// Current credential keys with an active or waiting singleflight caller.
    pub active_flights: usize,
    /// Current callers participating in credential singleflight groups.
    pub active_flight_participants: usize,
    /// Credential coordination requests rejected at a configured bound.
    pub coordination_rejections: u64,
    /// Central introspection requests rejected after bounded queueing.
    pub introspection_admission_rejections: u64,
    /// Current central introspection requests holding admission permits.
    pub introspection_in_flight: usize,
    /// JWKS refreshes actually sent to the authority.
    pub jwks_refreshes: u64,
}

/// Hybrid local-verification and central-freshness authorizer.
pub struct HybridAuthorizer<T = ReqwestAuthorityTransport> {
    config: Config,
    transport: T,
    cache: StdMutex<PositiveCache>,
    flights: Arc<StdMutex<HashMap<[u8; 32], FlightEntry>>>,
    jwks: Mutex<JwksCache>,
    jwks_refresh: Mutex<()>,
    introspection_permits: Semaphore,
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
        let introspection_permits = Semaphore::new(config.max_introspection_in_flight);
        Ok(Self {
            config,
            transport,
            cache: StdMutex::new(PositiveCache::default()),
            flights: Arc::new(StdMutex::new(HashMap::new())),
            jwks: Mutex::new(JwksCache::default()),
            jwks_refresh: Mutex::new(()),
            introspection_permits,
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
        if required_scopes.len() > 256
            || self
                .config
                .required_scopes
                .len()
                .saturating_add(required_scopes.len())
                > 256
        {
            return Err(AuthError::InvalidConfiguration(
                "too many required scopes".into(),
            ));
        }
        for scope in required_scopes {
            if !valid_scope(scope) {
                return Err(AuthError::InvalidConfiguration(
                    "operation scope is invalid".into(),
                ));
            }
        }

        let cache_key: [u8; 32] = Sha256::digest(token.as_bytes()).into();
        if let Some(principal) = self.cached(cache_key) {
            self.metrics.cache_hits.fetch_add(1, Ordering::Relaxed);
            require_scopes(&principal, &self.config.required_scopes, required_scopes)?;
            return Ok(principal);
        }
        self.metrics.cache_misses.fetch_add(1, Ordering::Relaxed);

        let flight = FlightLease::acquire(
            &self.flights,
            cache_key,
            self.config.max_active_flights,
            self.config.max_waiters_per_flight,
        )
        .inspect_err(|_| {
            self.metrics
                .coordination_rejections
                .fetch_add(1, Ordering::Relaxed);
        })?;
        let gate = Arc::clone(&flight.gate);
        let guard = gate.lock().await;
        let result = if let Some(principal) = self.cached(cache_key) {
            self.metrics.cache_hits.fetch_add(1, Ordering::Relaxed);
            require_scopes(&principal, &self.config.required_scopes, required_scopes)
                .map(|()| principal)
        } else {
            match self.authorize_uncached(token).await {
                Ok(principal) => {
                    // Cache the centrally confirmed authority even when this
                    // particular operation lacks a scope. A later operation
                    // still rechecks its own scope set against the cached
                    // principal, and the cache remains bounded by freshness.
                    self.store(cache_key, principal.clone());
                    require_scopes(&principal, &self.config.required_scopes, required_scopes)
                        .map(|()| principal)
                }
                Err(error) => Err(error),
            }
        };
        drop(guard);
        drop(flight);
        result
    }

    /// Return a privacy-safe snapshot of authorization counters and bounds.
    pub fn metrics(&self) -> MetricsSnapshot {
        let positive_cache_entries = lock_recover(&self.cache).len();
        let (active_flights, active_flight_participants) = {
            let flights = lock_recover(&self.flights);
            (
                flights.len(),
                flights.values().map(|entry| entry.users).sum(),
            )
        };
        let introspection_in_flight = self
            .config
            .max_introspection_in_flight
            .saturating_sub(self.introspection_permits.available_permits());
        MetricsSnapshot {
            cache_hits: self.metrics.cache_hits.load(Ordering::Relaxed),
            cache_misses: self.metrics.cache_misses.load(Ordering::Relaxed),
            local_jwt_rejections: self.metrics.local_jwt_rejections.load(Ordering::Relaxed),
            introspections: self.metrics.introspections.load(Ordering::Relaxed),
            authority_failures: self.metrics.authority_failures.load(Ordering::Relaxed),
            claim_mismatches: self.metrics.claim_mismatches.load(Ordering::Relaxed),
            cache_evictions: self.metrics.cache_evictions.load(Ordering::Relaxed),
            positive_cache_entries,
            active_flights,
            active_flight_participants,
            coordination_rejections: self.metrics.coordination_rejections.load(Ordering::Relaxed),
            introspection_admission_rejections: self
                .metrics
                .introspection_admission_rejections
                .load(Ordering::Relaxed),
            introspection_in_flight,
            jwks_refreshes: self.metrics.jwks_refreshes.load(Ordering::Relaxed),
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

        let permit = tokio::time::timeout(
            self.config.introspection_queue_timeout,
            self.introspection_permits.acquire(),
        )
        .await
        .map_err(|_| {
            self.metrics
                .introspection_admission_rejections
                .fetch_add(1, Ordering::Relaxed);
            AuthError::Unavailable
        })?
        .map_err(|_| {
            self.metrics
                .introspection_admission_rejections
                .fetch_add(1, Ordering::Relaxed);
            AuthError::Unavailable
        })?;
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
        drop(permit);
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
        validation.set_required_spec_claims(&["exp", "iat", "iss", "aud", "sub", "jti"]);
        validation.set_issuer(&[self.config.issuer_url.as_str()]);
        validation.set_audience(&[self.config.audience.as_str()]);
        let claims = decode::<Value>(token, &key, &validation)
            .map_err(|error| jwt_decode_failure(&error))?
            .claims;
        self.principal_from_claims(&claims, false)
    }

    async fn jwks_key(&self, kid: &str) -> Result<DecodingKey, AuthError> {
        // Fast path: a known key in a fresh published snapshot never waits for
        // refresh coordination or network I/O.
        let observed_generation = {
            let cache = self.jwks.lock().await;
            if cache
                .expires_at
                .is_some_and(|expiry| expiry > Instant::now())
                && let Some(key) = cache.keys.get(kid)
            {
                return Ok(key.key.clone());
            }
            cache.generation
        };

        // Only one authority refresh may run at a time. The published JWKS
        // snapshot is not locked while the network request is in flight.
        let _refresh_guard = self.jwks_refresh.lock().await;
        let now = Instant::now();
        {
            let cache = self.jwks.lock().await;

            // A waiter that overlapped a completed refresh consumes that
            // publication rather than immediately issuing a second fetch.
            if cache.generation != observed_generation
                && cache.expires_at.is_some_and(|expiry| expiry > now)
            {
                return cache
                    .keys
                    .get(kid)
                    .map(|key| key.key.clone())
                    .ok_or(AuthError::InvalidToken);
            }

            if let Some(key) = lookup_jwks_key(&cache, kid, now, self.config.jwks_refresh_cooldown)?
            {
                return Ok(key);
            }
        }

        self.metrics.jwks_refreshes.fetch_add(1, Ordering::Relaxed);
        let document = match self
            .transport
            .fetch_jwks(&self.config.jwks_url, self.config.max_response_bytes)
            .await
        {
            Ok(document) => document,
            Err(error) => {
                self.metrics
                    .authority_failures
                    .fetch_add(1, Ordering::Relaxed);
                self.jwks.lock().await.last_refresh_attempt = Some(Instant::now());
                return Err(error);
            }
        };
        let keys = match parse_jwks(document) {
            Ok(keys) => keys,
            Err(error) => {
                self.metrics
                    .authority_failures
                    .fetch_add(1, Ordering::Relaxed);
                self.jwks.lock().await.last_refresh_attempt = Some(Instant::now());
                return Err(error);
            }
        };
        let requested = keys.get(kid).map(|key| key.key.clone());
        {
            // The cooldown begins when the completed document is published,
            // not when a potentially slow fetch started.
            let published_at = Instant::now();
            let mut cache = self.jwks.lock().await;
            cache.keys = keys;
            cache.expires_at = Some(published_at + self.config.jwks_cache_ttl);
            cache.last_refresh_attempt = Some(published_at);
            cache.generation = cache.generation.wrapping_add(1).max(1);
        }
        requested.ok_or(AuthError::InvalidToken)
    }

    fn principal_from_claims(
        &self,
        claims: &Value,
        require_active: bool,
    ) -> Result<Principal, AuthError> {
        let object = claims.as_object().ok_or(AuthError::InvalidToken)?;
        if require_active && object.get("active").and_then(Value::as_bool) != Some(true) {
            return Err(AuthError::InvalidToken);
        }
        let issuer = strict_string(object, "iss", 2_048)?.ok_or(AuthError::WrongIssuer)?;
        if issuer != self.config.issuer_url {
            return Err(AuthError::WrongIssuer);
        }
        let audiences = strict_set(object.get("aud"), 32, valid_audience)?;
        if audiences.len() != 1 || !audiences.contains(&self.config.audience) {
            return Err(AuthError::WrongAudience);
        }
        let scope = strict_set(object.get("scope"), 256, valid_scope)?;
        let scopes_alias = strict_set(object.get("scopes"), 256, valid_scope)?;
        let scopes = match (object.contains_key("scope"), object.contains_key("scopes")) {
            (true, true) if scope != scopes_alias => return Err(AuthError::InvalidToken),
            (true, _) => scope,
            (_, true) => scopes_alias,
            (false, false) => BTreeSet::new(),
        };

        let subject = strict_id(object, "sub", 256)?.ok_or(AuthError::InvalidToken)?;
        let token_type =
            strict_id(object, "token_type", 32)?.unwrap_or_else(|| "access_token".into());
        if token_type != "access_token" && token_type != "api_key" {
            return Err(AuthError::InvalidToken);
        }
        let credential_id = if token_type == "api_key" {
            strict_id(object, "api_key_id", 256)?
        } else {
            strict_id(object, "jti", 256)?
        }
        .ok_or(AuthError::InvalidToken)?;
        let client_id =
            strict_alias_id(object, "client_id", "azp", 256)?.ok_or(AuthError::InvalidToken)?;
        let organization_id = strict_alias_id(object, "org_id", "organization_id", 256)?;
        let project_id = strict_id(object, "project_id", 256)?;
        let environment_id = strict_id(object, "environment_id", 256)?;
        if self.config.require_workspace
            && (organization_id.is_none() || project_id.is_none() || environment_id.is_none())
        {
            return Err(AuthError::InvalidToken);
        }

        let issued_at_epoch_seconds = strict_u64(object, "iat")?;
        let expires_at_epoch_seconds = strict_u64(object, "exp")?;
        let now = unix_time_seconds();
        if issued_at_epoch_seconds
            .is_some_and(|issued_at| issued_at > now.saturating_add(self.config.clock_skew_seconds))
        {
            return Err(AuthError::InvalidToken);
        }
        if expires_at_epoch_seconds
            .is_some_and(|expiry| expiry.saturating_add(self.config.clock_skew_seconds) <= now)
        {
            return Err(AuthError::InvalidToken);
        }
        if token_type == "access_token" {
            let issued_at = issued_at_epoch_seconds.ok_or(AuthError::InvalidToken)?;
            let expiry = expires_at_epoch_seconds.ok_or(AuthError::InvalidToken)?;
            if expiry < issued_at
                || expiry - issued_at > self.config.max_access_token_lifetime_seconds
            {
                return Err(AuthError::InvalidToken);
            }
        }
        let security_epoch = strict_u64(object, "security_epoch")?;
        if token_type == "access_token" && security_epoch.is_none() {
            return Err(AuthError::InvalidToken);
        }
        let grant_id = strict_id(object, "grant_id", 256)?;
        let mut sanitized = object.clone();
        for field in [
            "token",
            "access_token",
            "refresh_token",
            "client_secret",
            "introspection_secret",
        ] {
            sanitized.remove(field);
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
            issued_at_epoch_seconds,
            expires_at_epoch_seconds,
            security_epoch,
            grant_id,
            claims: sanitized,
        })
    }

    fn cached(&self, key: [u8; 32]) -> Option<Principal> {
        lock_recover(&self.cache).get(key, Instant::now())
    }

    fn store(&self, key: [u8; 32], principal: Principal) {
        let now_epoch = unix_time_seconds();
        let token_ttl = principal
            .expires_at_epoch_seconds
            .map_or(self.config.positive_cache_ttl.as_secs(), |expiry| {
                expiry.saturating_sub(now_epoch)
            });
        let ttl = self
            .config
            .positive_cache_ttl
            .min(Duration::from_secs(token_ttl));
        if ttl.is_zero() {
            return;
        }
        let expires_at = Instant::now() + ttl;
        if lock_recover(&self.cache).insert(
            key,
            principal,
            expires_at,
            self.config.max_cache_entries,
        ) {
            self.metrics.cache_evictions.fetch_add(1, Ordering::Relaxed);
        }
    }
}

fn lookup_jwks_key(
    cache: &JwksCache,
    kid: &str,
    now: Instant,
    refresh_cooldown: Duration,
) -> Result<Option<DecodingKey>, AuthError> {
    if cache.expires_at.is_some_and(|expiry| expiry > now) {
        if let Some(key) = cache.keys.get(kid) {
            return Ok(Some(key.key.clone()));
        }
        if cache
            .last_refresh_attempt
            .is_some_and(|attempt| now.saturating_duration_since(attempt) < refresh_cooldown)
        {
            return Err(AuthError::InvalidToken);
        }
        return Ok(None);
    }
    if cache
        .last_refresh_attempt
        .is_some_and(|attempt| now.saturating_duration_since(attempt) < refresh_cooldown)
    {
        return Err(AuthError::Unavailable);
    }
    Ok(None)
}

fn lock_recover<T>(mutex: &StdMutex<T>) -> std::sync::MutexGuard<'_, T> {
    match mutex.lock() {
        Ok(guard) => guard,
        Err(poisoned) => poisoned.into_inner(),
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
        && local.issued_at_epoch_seconds == central.issued_at_epoch_seconds
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
    (!keys.is_empty())
        .then_some(keys)
        .ok_or(AuthError::Unavailable)
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

fn jwt_decode_failure(error: &jsonwebtoken::errors::Error) -> AuthError {
    match error.kind() {
        JwtErrorKind::InvalidAudience => AuthError::WrongAudience,
        JwtErrorKind::InvalidIssuer => AuthError::WrongIssuer,
        _ => AuthError::InvalidToken,
    }
}

fn strict_string(
    claims: &Map<String, Value>,
    name: &str,
    max: usize,
) -> Result<Option<String>, AuthError> {
    match claims.get(name) {
        None | Some(Value::Null) => Ok(None),
        Some(Value::String(v))
            if !v.is_empty() && v.len() <= max && v.bytes().all(|b| !b.is_ascii_control()) =>
        {
            Ok(Some(v.clone()))
        }
        Some(_) => Err(AuthError::InvalidToken),
    }
}
fn strict_id(
    claims: &Map<String, Value>,
    name: &str,
    max: usize,
) -> Result<Option<String>, AuthError> {
    let value = strict_string(claims, name, max)?;
    if value
        .as_deref()
        .is_some_and(|v| !v.bytes().all(|b| matches!(b, 0x21..=0x7e)))
    {
        return Err(AuthError::InvalidToken);
    }
    Ok(value)
}
fn strict_alias_id(
    claims: &Map<String, Value>,
    primary: &str,
    alias: &str,
    max: usize,
) -> Result<Option<String>, AuthError> {
    let primary_value = strict_id(claims, primary, max)?;
    let alias_value = strict_id(claims, alias, max)?;
    if primary_value.is_some() && alias_value.is_some() && primary_value != alias_value {
        return Err(AuthError::InvalidToken);
    }
    Ok(primary_value.or(alias_value))
}

fn strict_u64(claims: &Map<String, Value>, name: &str) -> Result<Option<u64>, AuthError> {
    match claims.get(name) {
        None | Some(Value::Null) => Ok(None),
        Some(v) => v.as_u64().map(Some).ok_or(AuthError::InvalidToken),
    }
}
fn strict_set(
    value: Option<&Value>,
    max: usize,
    validator: fn(&str) -> bool,
) -> Result<BTreeSet<String>, AuthError> {
    let items: Vec<&str> = match value {
        None | Some(Value::Null) => return Ok(BTreeSet::new()),
        Some(Value::String(v)) if v.len() <= 4_096 => v.split_whitespace().collect(),
        Some(Value::Array(v)) if v.len() <= max => v
            .iter()
            .map(Value::as_str)
            .collect::<Option<Vec<_>>>()
            .ok_or(AuthError::InvalidToken)?,
        Some(_) => return Err(AuthError::InvalidToken),
    };
    if items.len() > max || items.iter().any(|item| !validator(item)) {
        return Err(AuthError::InvalidToken);
    }
    Ok(items.into_iter().map(str::to_owned).collect())
}

fn jwt_shaped(token: &str) -> bool {
    token.split('.').count() == 3
}

fn valid_key_id(value: &str) -> bool {
    !value.is_empty() && value.len() <= 128 && value.bytes().all(|byte| matches!(byte, 0x21..=0x7e))
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

fn validate_authority_url(value: &str, allow_http: bool, name: &str) -> Result<Url, AuthError> {
    let url = Url::parse(value)
        .map_err(|_| AuthError::InvalidConfiguration(format!("{name} must be an absolute URL")))?;
    if url.username() != ""
        || url.password().is_some()
        || url.query().is_some()
        || url.fragment().is_some()
        || url.host().is_none()
    {
        return Err(AuthError::InvalidConfiguration(format!(
            "{name} contains forbidden URL components"
        )));
    }
    if url.scheme() != "https" && !(allow_http && url.scheme() == "http" && is_loopback_url(&url)) {
        return Err(AuthError::InvalidConfiguration(format!(
            "{name} must use HTTPS except for loopback development"
        )));
    }
    Ok(url)
}
fn is_loopback_url(url: &Url) -> bool {
    match url.host() {
        Some(Host::Ipv4(ip)) => ip.is_loopback(),
        Some(Host::Ipv6(ip)) => ip.is_loopback(),
        Some(Host::Domain(name)) => name.eq_ignore_ascii_case("localhost"),
        None => false,
    }
}
fn same_origin(a: &Url, b: &Url) -> bool {
    a.scheme() == b.scheme()
        && a.host_str().map(str::to_ascii_lowercase) == b.host_str().map(str::to_ascii_lowercase)
        && a.port_or_known_default() == b.port_or_known_default()
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
