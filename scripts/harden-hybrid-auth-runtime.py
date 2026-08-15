#!/usr/bin/env python3
"""Apply bounded authority/JWT hardening to tempera-auth-runtime."""
from pathlib import Path
import re

LIB = Path("packages/auth-rust/src/lib.rs")
TEST = Path("packages/auth-rust/tests/hardening.rs")
text = LIB.read_text()


def once(old: str, new: str, name: str) -> None:
    global text
    if text.count(old) != 1:
        raise SystemExit(f"{name}: expected exactly one match")
    text = text.replace(old, new, 1)


def sub(pattern: str, replacement: str, name: str) -> None:
    global text
    text2, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"{name}: expected exactly one match, got {count}")
    text = text2


once("use url::Url;", "use url::{Host, Url};", "url import")
once(
    "const DEFAULT_CLOCK_SKEW_SECONDS: u64 = 30;\n",
    "const DEFAULT_CLOCK_SKEW_SECONDS: u64 = 30;\nconst DEFAULT_MAX_ACCESS_TOKEN_LIFETIME_SECONDS: u64 = 3_600;\n",
    "lifetime constant",
)
once(
    "    /// Require organization, project, and environment claims.\n    pub require_workspace: bool,",
    "    /// Maximum permitted access-token lifetime (`exp - iat`).\n    pub max_access_token_lifetime_seconds: u64,\n    /// Require organization, project, and environment claims.\n    pub require_workspace: bool,",
    "config field",
)
once(
    "            clock_skew_seconds: DEFAULT_CLOCK_SKEW_SECONDS,\n            require_workspace: true,",
    "            clock_skew_seconds: DEFAULT_CLOCK_SKEW_SECONDS,\n            max_access_token_lifetime_seconds: DEFAULT_MAX_ACCESS_TOKEN_LIFETIME_SECONDS,\n            require_workspace: true,",
    "config default",
)
sub(
    r"    pub fn validate\(&self\) -> Result<\(\), AuthError> \{.*?\n        Ok\(\(\)\)\n    \}\n",
    '''    pub fn validate(&self) -> Result<(), AuthError> {
        let issuer = validate_authority_url(&self.issuer_url, self.allow_insecure_http, "issuer_url")?;
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
            || self.required_scopes.iter().any(|scope| !valid_scope(scope))
            || self.positive_cache_ttl.is_zero()
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
                "authorization configuration is outside safe bounds".into(),
            ));
        }
        if self.introspection_secret.as_deref().is_some_and(|secret| {
            secret.is_empty() || secret.len() > 4_096 || secret.bytes().any(|b| b.is_ascii_control())
        }) {
            return Err(AuthError::InvalidConfiguration(
                "introspection secret is empty, oversized, or contains control characters".into(),
            ));
        }
        Ok(())
    }
''',
    "validate",
)
once(
    "            .field(\"clock_skew_seconds\", &self.clock_skew_seconds)\n            .field(\"require_workspace\", &self.require_workspace)",
    "            .field(\"clock_skew_seconds\", &self.clock_skew_seconds)\n            .field(\"max_access_token_lifetime_seconds\", &self.max_access_token_lifetime_seconds)\n            .field(\"require_workspace\", &self.require_workspace)",
    "debug field",
)
once(
    "    /// JWT expiration, when present.\n    pub expires_at_epoch_seconds: Option<u64>,",
    "    /// JWT issuance time, when present.\n    pub issued_at_epoch_seconds: Option<u64>,\n    /// JWT expiration, when present.\n    pub expires_at_epoch_seconds: Option<u64>,",
    "principal iat",
)
once(
    '        validation.set_required_spec_claims(&["exp", "iss", "aud", "sub", "jti"]);',
    '        validation.set_required_spec_claims(&["exp", "iat", "iss", "aud", "sub", "jti"]);',
    "required claims",
)
sub(
    r"    fn principal_from_claims\(.*?\n    \}\n\n    async fn cached",
    '''    fn principal_from_claims(
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
        if !audiences.contains(&self.config.audience) {
            return Err(AuthError::WrongAudience);
        }
        let mut scopes = strict_set(object.get("scope"), 256, valid_scope)?;
        scopes.extend(strict_set(object.get("scopes"), 256, valid_scope)?);
        if scopes.len() > 256 { return Err(AuthError::InvalidToken); }

        let subject = strict_id(object, "sub", 256)?.ok_or(AuthError::InvalidToken)?;
        let token_type = strict_id(object, "token_type", 32)?.unwrap_or_else(|| "access_token".into());
        if token_type != "access_token" && token_type != "api_key" { return Err(AuthError::InvalidToken); }
        let credential_id = if token_type == "api_key" {
            strict_id(object, "api_key_id", 256)?
        } else {
            strict_id(object, "jti", 256)?
        }.ok_or(AuthError::InvalidToken)?;
        let client_id = strict_id(object, "client_id", 256)?
            .or(strict_id(object, "azp", 256)?)
            .ok_or(AuthError::InvalidToken)?;
        let organization_id = strict_id(object, "org_id", 256)?
            .or(strict_id(object, "organization_id", 256)?);
        let project_id = strict_id(object, "project_id", 256)?;
        let environment_id = strict_id(object, "environment_id", 256)?;
        if self.config.require_workspace
            && (organization_id.is_none() || project_id.is_none() || environment_id.is_none())
        { return Err(AuthError::InvalidToken); }

        let issued_at_epoch_seconds = strict_u64(object, "iat")?;
        let expires_at_epoch_seconds = strict_u64(object, "exp")?;
        let now = unix_time_seconds();
        if issued_at_epoch_seconds.is_some_and(|issued_at| issued_at > now.saturating_add(self.config.clock_skew_seconds)) {
            return Err(AuthError::InvalidToken);
        }
        if expires_at_epoch_seconds.is_some_and(|expiry| expiry.saturating_add(self.config.clock_skew_seconds) <= now) {
            return Err(AuthError::InvalidToken);
        }
        if token_type == "access_token" {
            let issued_at = issued_at_epoch_seconds.ok_or(AuthError::InvalidToken)?;
            let expiry = expires_at_epoch_seconds.ok_or(AuthError::InvalidToken)?;
            if expiry < issued_at || expiry - issued_at > self.config.max_access_token_lifetime_seconds {
                return Err(AuthError::InvalidToken);
            }
        }
        let security_epoch = strict_u64(object, "security_epoch")?;
        let grant_id = strict_id(object, "grant_id", 256)?;
        let mut sanitized = object.clone();
        for field in ["token", "access_token", "refresh_token", "client_secret", "introspection_secret"] {
            sanitized.remove(field);
        }
        Ok(Principal {
            subject, client_id, token_type, credential_id,
            audience: self.config.audience.clone(),
            organization_id, project_id, environment_id, scopes,
            issued_at_epoch_seconds, expires_at_epoch_seconds,
            security_epoch, grant_id, claims: sanitized,
        })
    }

    async fn cached''',
    "principal parser",
)
once(
    "        && local.scopes == central.scopes\n        && local.expires_at_epoch_seconds == central.expires_at_epoch_seconds",
    "        && local.scopes == central.scopes\n        && local.issued_at_epoch_seconds == central.issued_at_epoch_seconds\n        && local.expires_at_epoch_seconds == central.expires_at_epoch_seconds",
    "authority equivalence",
)
sub(
    r"fn claim_string\(.*?\n\}\n\nfn string_set\(.*?\n\}\n",
    '''fn strict_string(claims: &Map<String, Value>, name: &str, max: usize) -> Result<Option<String>, AuthError> {
    match claims.get(name) {
        None | Some(Value::Null) => Ok(None),
        Some(Value::String(v)) if !v.is_empty() && v.len() <= max && v.bytes().all(|b| !b.is_ascii_control()) => Ok(Some(v.clone())),
        Some(_) => Err(AuthError::InvalidToken),
    }
}
fn strict_id(claims: &Map<String, Value>, name: &str, max: usize) -> Result<Option<String>, AuthError> {
    let value = strict_string(claims, name, max)?;
    if value.as_deref().is_some_and(|v| !v.bytes().all(|b| matches!(b, 0x21..=0x7e))) {
        return Err(AuthError::InvalidToken);
    }
    Ok(value)
}
fn strict_u64(claims: &Map<String, Value>, name: &str) -> Result<Option<u64>, AuthError> {
    match claims.get(name) {
        None | Some(Value::Null) => Ok(None),
        Some(v) => v.as_u64().map(Some).ok_or(AuthError::InvalidToken),
    }
}
fn strict_set(value: Option<&Value>, max: usize, validator: fn(&str) -> bool) -> Result<BTreeSet<String>, AuthError> {
    let items: Vec<&str> = match value {
        None | Some(Value::Null) => return Ok(BTreeSet::new()),
        Some(Value::String(v)) if v.len() <= 4_096 => v.split_whitespace().collect(),
        Some(Value::Array(v)) if v.len() <= max => v.iter().map(Value::as_str).collect::<Option<Vec<_>>>().ok_or(AuthError::InvalidToken)?,
        Some(_) => return Err(AuthError::InvalidToken),
    };
    if items.len() > max || items.iter().any(|item| !validator(item)) { return Err(AuthError::InvalidToken); }
    Ok(items.into_iter().map(str::to_owned).collect())
}
''',
    "strict helpers",
)
sub(
    r"fn validate_authority_url\(.*?\n\}\n",
    '''fn validate_authority_url(value: &str, allow_http: bool, name: &str) -> Result<Url, AuthError> {
    let url = Url::parse(value).map_err(|_| AuthError::InvalidConfiguration(format!("{name} must be an absolute URL")))?;
    if url.username() != "" || url.password().is_some() || url.query().is_some() || url.fragment().is_some() || url.host().is_none() {
        return Err(AuthError::InvalidConfiguration(format!("{name} contains forbidden URL components")));
    }
    if url.scheme() != "https" && !(allow_http && url.scheme() == "http" && is_loopback_url(&url)) {
        return Err(AuthError::InvalidConfiguration(format!("{name} must use HTTPS except for loopback development")));
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
''',
    "authority URL",
)
LIB.write_text(text)

TEST.write_text(r'''use std::time::Duration;
use tempera_auth_runtime::{AuthError, Config};

fn base() -> Config {
    let mut c = Config::new(
        "https://auth.example.test",
        "tempera-document",
        "https://auth.example.test/.well-known/jwks.json",
        "https://auth.example.test/v1/oauth/introspect",
    );
    c.introspection_secret = Some("secret".into());
    c
}

#[test]
fn hosted_authority_requires_same_origin_and_secret() {
    let mut c = base();
    c.jwks_url = "https://evil.example/.well-known/jwks.json".into();
    assert!(matches!(c.validate(), Err(AuthError::InvalidConfiguration(_))));
    let mut c = base();
    c.introspection_secret = None;
    assert!(matches!(c.validate(), Err(AuthError::InvalidConfiguration(_))));
}

#[test]
fn insecure_http_is_loopback_only() {
    let mut c = Config::new(
        "http://127.0.0.1:8080", "tempera-document",
        "http://127.0.0.1:8080/jwks", "http://127.0.0.1:8080/introspect",
    );
    c.allow_insecure_http = true;
    assert!(c.validate().is_ok());
    c.issuer_url = "http://auth.example.test".into();
    c.jwks_url = "http://auth.example.test/jwks".into();
    c.introspection_url = "http://auth.example.test/introspect".into();
    assert!(matches!(c.validate(), Err(AuthError::InvalidConfiguration(_))));
}

#[test]
fn jwt_lifetime_bounds_are_validated() {
    let mut c = base();
    c.max_access_token_lifetime_seconds = 59;
    assert!(matches!(c.validate(), Err(AuthError::InvalidConfiguration(_))));
    c.max_access_token_lifetime_seconds = 3600;
    c.positive_cache_ttl = Duration::from_secs(31);
    assert!(matches!(c.validate(), Err(AuthError::InvalidConfiguration(_))));
}
''')
print("hybrid auth hardening applied")
