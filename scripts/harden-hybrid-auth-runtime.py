#!/usr/bin/env python3
"""Harden hybrid authority origins, JWT lifetimes, and claim parsing."""

from __future__ import annotations

import re
from pathlib import Path

LIB = Path("packages/auth-rust/src/lib.rs")
TEST = Path("packages/auth-rust/tests/hybrid.rs")
README = Path("packages/auth-rust/README.md")

text = LIB.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one source block, found {count}")
    text = text.replace(old, new, 1)


def replace_regex(pattern: str, replacement: str, label: str) -> None:
    global text
    text, count = re.subn(pattern, lambda _match: replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"{label}: expected one source block, found {count}")


replace_once("use url::Url;", "use url::{Host, Url};", "URL host import")
replace_once(
    "const DEFAULT_CLOCK_SKEW_SECONDS: u64 = 30;\n",
    "const DEFAULT_CLOCK_SKEW_SECONDS: u64 = 30;\n"
    "const DEFAULT_MAX_ACCESS_TOKEN_LIFETIME_SECONDS: u64 = 3_600;\n",
    "access-token lifetime default",
)
replace_once(
    '''    /// Accepted clock skew for JWT temporal claims.
    pub clock_skew_seconds: u64,
    /// Require organization, project, and environment claims.
''',
    '''    /// Accepted clock skew for JWT temporal claims.
    pub clock_skew_seconds: u64,
    /// Maximum permitted access-token lifetime (`exp - iat`).
    pub max_access_token_lifetime_seconds: u64,
    /// Require organization, project, and environment claims.
''',
    "access-token lifetime config field",
)
replace_once(
    '''            clock_skew_seconds: DEFAULT_CLOCK_SKEW_SECONDS,
            require_workspace: true,
''',
    '''            clock_skew_seconds: DEFAULT_CLOCK_SKEW_SECONDS,
            max_access_token_lifetime_seconds:
                DEFAULT_MAX_ACCESS_TOKEN_LIFETIME_SECONDS,
            require_workspace: true,
''',
    "access-token lifetime config default",
)
replace_regex(
    r'''    pub fn validate\(&self\) -> Result<\(\), AuthError> \{.*?\n        Ok\(\(\)\)\n    \}\n''',
    '''    pub fn validate(&self) -> Result<(), AuthError> {
        let issuer = validate_authority_url(
            &self.issuer_url,
            self.allow_insecure_http,
            "issuer_url",
        )?;
        let jwks = validate_authority_url(
            &self.jwks_url,
            self.allow_insecure_http,
            "jwks_url",
        )?;
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
        if !valid_audience(&self.audience) {
            return Err(AuthError::InvalidConfiguration(
                "audience must be a bounded URL-safe resource name".into(),
            ));
        }
        if self.required_scopes.iter().any(|scope| !valid_scope(scope)) {
            return Err(AuthError::InvalidConfiguration(
                "required scopes contain an invalid OAuth scope token".into(),
            ));
        }
        if self.positive_cache_ttl.is_zero()
            || self.positive_cache_ttl > Duration::from_secs(30)
            || self.jwks_cache_ttl < Duration::from_secs(30)
            || self.jwks_cache_ttl > Duration::from_hours(24)
            || self.jwks_refresh_cooldown.is_zero()
            || self.jwks_refresh_cooldown > self.jwks_cache_ttl
            || !(1..=1_000_000).contains(&self.max_cache_entries)
            || !(256..=65_536).contains(&self.max_token_bytes)
            || !(1_024..=16 * 1024 * 1024).contains(&self.max_response_bytes)
            || self.clock_skew_seconds > 300
            || !(60..=86_400).contains(&self.max_access_token_lifetime_seconds)
        {
            return Err(AuthError::InvalidConfiguration(
                "authorization cache/JWT bounds are unsafe".into(),
            ));
        }
        if self.introspection_secret.as_deref().is_some_and(|secret| {
            secret.is_empty()
                || secret.len() > 4_096
                || secret.bytes().any(|byte| byte.is_ascii_control())
        }) {
            return Err(AuthError::InvalidConfiguration(
                "introspection secret is empty, oversized, or contains control characters".into(),
            ));
        }
        Ok(())
    }
''',
    "configuration validation",
)
replace_once(
    '''            .field("clock_skew_seconds", &self.clock_skew_seconds)
            .field("require_workspace", &self.require_workspace)
''',
    '''            .field("clock_skew_seconds", &self.clock_skew_seconds)
            .field(
                "max_access_token_lifetime_seconds",
                &self.max_access_token_lifetime_seconds,
            )
            .field("require_workspace", &self.require_workspace)
''',
    "debug lifetime field",
)
replace_once(
    '''    /// JWT expiration, when present.
    pub expires_at_epoch_seconds: Option<u64>,
    /// User security epoch, when present.
''',
    '''    /// JWT issuance time, when present.
    pub issued_at_epoch_seconds: Option<u64>,
    /// JWT expiration, when present.
    pub expires_at_epoch_seconds: Option<u64>,
    /// User security epoch, when present.
''',
    "principal issuance field",
)
replace_once(
    '''        validation.set_required_spec_claims(&["exp", "iss", "aud", "sub", "jti"]);
''',
    '''        validation.set_required_spec_claims(&[
            "exp", "iat", "iss", "aud", "sub", "jti",
        ]);
''',
    "required issuance claim",
)
replace_regex(
    r'''    fn principal_from_claims\(\n        &self,\n        claims: &Value,\n        require_active: bool,\n    \) -> Result<Principal, AuthError> \{.*?\n    \}\n\n    async fn cached''',
    '''    fn principal_from_claims(
        &self,
        claims: &Value,
        require_active: bool,
    ) -> Result<Principal, AuthError> {
        let object = claims.as_object().ok_or(AuthError::InvalidToken)?;
        if require_active && object.get("active").and_then(Value::as_bool) != Some(true) {
            return Err(AuthError::InvalidToken);
        }
        let issuer = strict_claim_string(object, "iss", 2_048)?
            .ok_or(AuthError::WrongIssuer)?;
        if issuer != self.config.issuer_url {
            return Err(AuthError::WrongIssuer);
        }
        let audiences = strict_string_set(object.get("aud"), 32, valid_audience)?;
        if !audiences.contains(&self.config.audience) {
            return Err(AuthError::WrongAudience);
        }
        let mut scopes = strict_string_set(object.get("scope"), 256, valid_scope)?;
        scopes.extend(strict_string_set(
            object.get("scopes"),
            256,
            valid_scope,
        )?);
        if scopes.len() > 256 {
            return Err(AuthError::InvalidToken);
        }

        let subject = strict_identifier_claim(object, "sub", 256)?
            .ok_or(AuthError::InvalidToken)?;
        let token_type = strict_identifier_claim(object, "token_type", 32)?
            .unwrap_or_else(|| "access_token".into());
        if token_type != "access_token" && token_type != "api_key" {
            return Err(AuthError::InvalidToken);
        }
        let credential_id = if token_type == "api_key" {
            strict_identifier_claim(object, "api_key_id", 256)?
        } else {
            strict_identifier_claim(object, "jti", 256)?
        }
        .ok_or(AuthError::InvalidToken)?;
        let client_id = strict_identifier_claim(object, "client_id", 256)?
            .or(strict_identifier_claim(object, "azp", 256)?)
            .ok_or(AuthError::InvalidToken)?;
        let organization_id = strict_identifier_claim(object, "org_id", 256)?
            .or(strict_identifier_claim(object, "organization_id", 256)?);
        let project_id = strict_identifier_claim(object, "project_id", 256)?;
        let environment_id = strict_identifier_claim(object, "environment_id", 256)?;
        if self.config.require_workspace
            && (organization_id.is_none() || project_id.is_none() || environment_id.is_none())
        {
            return Err(AuthError::InvalidToken);
        }

        let issued_at_epoch_seconds = strict_u64_claim(object, "iat")?;
        let expires_at_epoch_seconds = strict_u64_claim(object, "exp")?;
        let now = unix_time_seconds();
        if issued_at_epoch_seconds.is_some_and(|issued| {
            issued > now.saturating_add(self.config.clock_skew_seconds)
        }) {
            return Err(AuthError::InvalidToken);
        }
        if expires_at_epoch_seconds.is_some_and(|expiry| {
            expiry.saturating_add(self.config.clock_skew_seconds) <= now
        }) {
            return Err(AuthError::InvalidToken);
        }
        if token_type == "access_token" {
            let issued = issued_at_epoch_seconds.ok_or(AuthError::InvalidToken)?;
            let expiry = expires_at_epoch_seconds.ok_or(AuthError::InvalidToken)?;
            if expiry < issued
                || expiry - issued > self.config.max_access_token_lifetime_seconds
            {
                return Err(AuthError::InvalidToken);
            }
        }

        let security_epoch = strict_u64_claim(object, "security_epoch")?;
        let grant_id = strict_identifier_claim(object, "grant_id", 256)?;
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

    async fn cached''',
    "strict principal parsing",
)
replace_once(
    '''        && local.scopes == central.scopes
        && local.expires_at_epoch_seconds == central.expires_at_epoch_seconds
''',
    '''        && local.scopes == central.scopes
        && local.issued_at_epoch_seconds == central.issued_at_epoch_seconds
        && local.expires_at_epoch_seconds == central.expires_at_epoch_seconds
''',
    "issuance reconciliation",
)
replace_regex(
    r'''fn claim_string\(claims: &Value, name: &str\) -> Option<String> \{.*?\n\}\n\nfn string_set\(value: Option<&Value>\) -> BTreeSet<String> \{.*?\n\}\n''',
    '''fn strict_claim_string(
    claims: &Map<String, Value>,
    name: &str,
    max_bytes: usize,
) -> Result<Option<String>, AuthError> {
    match claims.get(name) {
        None | Some(Value::Null) => Ok(None),
        Some(Value::String(value))
            if !value.is_empty()
                && value.len() <= max_bytes
                && value
                    .bytes()
                    .all(|byte| !byte.is_ascii_control()) =>
        {
            Ok(Some(value.clone()))
        }
        Some(_) => Err(AuthError::InvalidToken),
    }
}

fn strict_identifier_claim(
    claims: &Map<String, Value>,
    name: &str,
    max_bytes: usize,
) -> Result<Option<String>, AuthError> {
    let value = strict_claim_string(claims, name, max_bytes)?;
    if value.as_deref().is_some_and(|value| {
        !value.bytes().all(|byte| matches!(byte, 0x21..=0x7e))
    }) {
        return Err(AuthError::InvalidToken);
    }
    Ok(value)
}

fn strict_u64_claim(
    claims: &Map<String, Value>,
    name: &str,
) -> Result<Option<u64>, AuthError> {
    match claims.get(name) {
        None | Some(Value::Null) => Ok(None),
        Some(value) => value.as_u64().map(Some).ok_or(AuthError::InvalidToken),
    }
}

fn strict_string_set(
    value: Option<&Value>,
    max_items: usize,
    validator: fn(&str) -> bool,
) -> Result<BTreeSet<String>, AuthError> {
    let items: Vec<&str> = match value {
        None | Some(Value::Null) => return Ok(BTreeSet::new()),
        Some(Value::String(value)) => {
            if value.len() > 4_096 {
                return Err(AuthError::InvalidToken);
            }
            value.split_whitespace().collect()
        }
        Some(Value::Array(values)) if values.len() <= max_items => values
            .iter()
            .map(Value::as_str)
            .collect::<Option<Vec<_>>>()
            .ok_or(AuthError::InvalidToken)?,
        Some(_) => return Err(AuthError::InvalidToken),
    };
    if items.len() > max_items || items.iter().any(|item| !validator(item)) {
        return Err(AuthError::InvalidToken);
    }
    Ok(items.into_iter().map(str::to_owned).collect())
}
''',
    "strict authority claim helpers",
)
replace_regex(
    r'''fn validate_authority_url\(value: &str, allow_http: bool, name: &str\) -> Result<\(\), AuthError> \{.*?\n\}\n''',
    '''fn validate_authority_url(
    value: &str,
    allow_http: bool,
    name: &str,
) -> Result<Url, AuthError> {
    let url = Url::parse(value)
        .map_err(|_| AuthError::InvalidConfiguration(format!("{name} must be an absolute URL")))?;
    if url.username() != ""
        || url.password().is_some()
        || url.query().is_some()
        || url.fragment().is_some()
        || url.host().is_none()
    {
        return Err(AuthError::InvalidConfiguration(format!(
            "{name} must not contain credentials, query, or fragment"
        )));
    }
    let secure = url.scheme() == "https";
    let loopback_http =
        allow_http && url.scheme() == "http" && is_loopback_url(&url);
    if !secure && !loopback_http {
        return Err(AuthError::InvalidConfiguration(format!(
            "{name} must use HTTPS, except for explicit loopback development"
        )));
    }
    Ok(url)
}

fn is_loopback_url(url: &Url) -> bool {
    match url.host() {
        Some(Host::Ipv4(address)) => address.is_loopback(),
        Some(Host::Ipv6(address)) => address.is_loopback(),
        Some(Host::Domain(domain)) => domain.eq_ignore_ascii_case("localhost"),
        None => false,
    }
}

fn same_origin(left: &Url, right: &Url) -> bool {
    left.scheme() == right.scheme()
        && left.host_str().map(str::to_ascii_lowercase)
            == right.host_str().map(str::to_ascii_lowercase)
        && left.port_or_known_default() == right.port_or_known_default()
}
''',
    "loopback-only same-origin authority URLs",
)
LIB.write_text(text)

hybrid = TEST.read_text()
hybrid = hybrid.replace("http://auth.test", "http://127.0.0.1:4400")
hybrid = hybrid.replace('"iss": "http://auth.test"', '"iss": "http://127.0.0.1:4400"')
hybrid = hybrid.replace(
    '''    assert_eq!(principal.security_epoch, Some(7));
''',
    '''    assert_eq!(principal.security_epoch, Some(7));
    assert!(principal.issued_at_epoch_seconds.is_some());
''',
    1,
)
hybrid = hybrid.replace(
    '''    let secure = Config::new(
        "https://api.tempera.dev",
        "tempera-document",
        "https://api.tempera.dev/.well-known/jwks.json",
        "https://api.tempera.dev/v1/oauth/introspect",
    );
    assert!(secure.validate().is_ok());
''',
    '''    let mut secure = Config::new(
        "https://api.tempera.dev",
        "tempera-document",
        "https://api.tempera.dev/.well-known/jwks.json",
        "https://api.tempera.dev/v1/oauth/introspect",
    );
    secure.introspection_secret = Some("hosted-resource-server-secret".into());
    assert!(secure.validate().is_ok());
''',
    1,
)
append = r'''

#[tokio::test]
async fn future_and_overlong_access_tokens_fail_before_introspection() {
    for mut claims in [access_claims(), access_claims()] {
        if claims["jti"] == "jti_test" {
            claims["jti"] = Value::String(format!("jti_{}", claims["iat"]));
        }
        let issued = now();
        if claims["jti"].as_str().is_some_and(|value| value.contains(&issued.to_string())) {
            claims["iat"] = Value::from(issued + 301);
            claims["exp"] = Value::from(issued + 600);
        } else {
            claims["iat"] = Value::from(issued);
            claims["exp"] = Value::from(issued + 3_601);
        }
        let token = access_token(&claims);
        let transport = FakeTransport::new();
        transport.insert(&token, central_claims(&claims)).await;
        let authorizer = HybridAuthorizer::with_transport(config(), transport.clone()).unwrap();
        assert_eq!(
            authorizer.authorize(&token, &["document:read"]).await,
            Err(AuthError::InvalidToken),
        );
        assert_eq!(transport.introspection_calls.load(Ordering::Relaxed), 0);
    }
}

#[tokio::test]
async fn malformed_scope_claim_fails_instead_of_being_silently_dropped() {
    let transport = FakeTransport::new();
    let mut claims = access_claims();
    claims["scope"] = json!(["document:read", 7]);
    let token = access_token(&claims);
    transport.insert(&token, central_claims(&claims)).await;
    let authorizer = HybridAuthorizer::with_transport(config(), transport.clone()).unwrap();
    assert_eq!(
        authorizer.authorize(&token, &["document:read"]).await,
        Err(AuthError::InvalidToken),
    );
    assert_eq!(transport.introspection_calls.load(Ordering::Relaxed), 0);
}

#[tokio::test]
async fn missing_scope_releases_singleflight_and_preserves_bounded_authority_cache() {
    let transport = FakeTransport::new();
    let claims = access_claims();
    let token = access_token(&claims);
    transport.insert(&token, central_claims(&claims)).await;
    let authorizer = HybridAuthorizer::with_transport(config(), transport.clone()).unwrap();

    assert_eq!(
        authorizer.authorize(&token, &["admin"]).await,
        Err(AuthError::MissingScope("admin".into())),
    );
    let snapshot = authorizer.cache_snapshot().await;
    assert_eq!(snapshot.inflight_entries, 0);
    assert_eq!(snapshot.positive_entries, 1);
    authorizer
        .authorize(&token, &["document:read"])
        .await
        .unwrap();
    assert_eq!(transport.introspection_calls.load(Ordering::Relaxed), 1);
}

#[test]
fn authority_urls_are_loopback_only_for_http_same_origin_and_secret_bound() {
    let mut non_loopback = Config::new(
        "http://auth.internal",
        "tempera-document",
        "http://auth.internal/.well-known/jwks.json",
        "http://auth.internal/v1/oauth/introspect",
    );
    non_loopback.allow_insecure_http = true;
    non_loopback.introspection_secret = Some("secret".into());
    assert!(matches!(
        non_loopback.validate(),
        Err(AuthError::InvalidConfiguration(_)),
    ));

    let mut cross_origin = Config::new(
        "https://api.tempera.dev",
        "tempera-document",
        "https://keys.example.test/.well-known/jwks.json",
        "https://api.tempera.dev/v1/oauth/introspect",
    );
    cross_origin.introspection_secret = Some("secret".into());
    assert!(matches!(
        cross_origin.validate(),
        Err(AuthError::InvalidConfiguration(_)),
    ));

    let hosted_without_secret = Config::new(
        "https://api.tempera.dev",
        "tempera-document",
        "https://api.tempera.dev/.well-known/jwks.json",
        "https://api.tempera.dev/v1/oauth/introspect",
    );
    assert!(matches!(
        hosted_without_secret.validate(),
        Err(AuthError::InvalidConfiguration(_)),
    ));
}
'''
if "future_and_overlong_access_tokens_fail_before_introspection" in hybrid:
    raise SystemExit("security tests already appended")
hybrid += append
TEST.write_text(hybrid)

readme = README.read_text()
readme += '''

## Authority configuration

Hosted JWKS and introspection endpoints must use HTTPS and share the exact issuer origin. HTTP is accepted only for explicit loopback development. Hosted introspection requires a resource-server secret, preventing accidental unauthenticated or cross-origin authority calls.

Access tokens must include integer `iat` and `exp` claims, may not be issued in the future beyond configured skew, and may not exceed the configured maximum lifetime (one hour by default). Authority IDs and scope/audience collections are parsed strictly; malformed members fail the credential rather than being silently discarded.
'''
README.write_text(readme)

print("hybrid auth authority and JWT hardening applied")
