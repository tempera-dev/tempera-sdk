#!/usr/bin/env python3
"""Apply bounded hot-path and authority-ambiguity hardening to tempera-auth-runtime."""

from __future__ import annotations

from pathlib import Path

LIB = Path("packages/auth-rust/src/lib.rs")
HYBRID = Path("packages/auth-rust/tests/hybrid.rs")
HARDENING = Path("packages/auth-rust/tests/hardening.rs")
README = Path("packages/auth-rust/README.md")

text = LIB.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one source block, found {count}")
    text = text.replace(old, new, 1)


replace_once(
    '''        if !valid_audience(&self.audience)
            || self.required_scopes.iter().any(|scope| !valid_scope(scope))
''',
    '''        if !valid_audience(&self.audience)
            || self.required_scopes.len() > 256
            || self.required_scopes.iter().any(|scope| !valid_scope(scope))
''',
    "bounded baseline scope count",
)

replace_once(
    '''        if token.is_empty() || token.len() > self.config.max_token_bytes {
            return Err(AuthError::InvalidToken);
        }
        for scope in required_scopes {
''',
    '''        if token.is_empty() || token.len() > self.config.max_token_bytes {
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
''',
    "bounded operation scope count",
)

replace_once(
    '''        let status = response.status();
        if status.is_server_error() || status == StatusCode::TOO_MANY_REQUESTS {
            return Err(AuthError::Unavailable);
        }
        if !status.is_success() {
            return Err(AuthError::InvalidToken);
        }
''',
    '''        let status = response.status();
        // Auth Hub represents an invalid credential with a successful
        // `active: false` response. Any HTTP failure therefore means the
        // authority, route, or resource-server credential is unavailable or
        // misconfigured; it must not be reported as a bad caller token.
        if !status.is_success() {
            return Err(AuthError::Unavailable);
        }
''',
    "authority HTTP failure classification",
)

replace_once(
    '''        let audiences = strict_set(object.get("aud"), 32, valid_audience)?;
        if !audiences.contains(&self.config.audience) {
            return Err(AuthError::WrongAudience);
        }
        let mut scopes = strict_set(object.get("scope"), 256, valid_scope)?;
        scopes.extend(strict_set(object.get("scopes"), 256, valid_scope)?);
        if scopes.len() > 256 {
            return Err(AuthError::InvalidToken);
        }
''',
    '''        let audiences = strict_set(object.get("aud"), 32, valid_audience)?;
        if audiences.len() != 1 || !audiences.contains(&self.config.audience) {
            return Err(AuthError::WrongAudience);
        }
        let scope = strict_set(object.get("scope"), 256, valid_scope)?;
        let scopes_alias = strict_set(object.get("scopes"), 256, valid_scope)?;
        let scopes = match (
            object.contains_key("scope"),
            object.contains_key("scopes"),
        ) {
            (true, true) if scope != scopes_alias => return Err(AuthError::InvalidToken),
            (true, _) => scope,
            (_, true) => scopes_alias,
            (false, false) => BTreeSet::new(),
        };
''',
    "single audience and unambiguous scope claims",
)

replace_once(
    '''        let client_id = strict_id(object, "client_id", 256)?
            .or(strict_id(object, "azp", 256)?)
            .ok_or(AuthError::InvalidToken)?;
        let organization_id =
            strict_id(object, "org_id", 256)?.or(strict_id(object, "organization_id", 256)?);
''',
    '''        let client_id = strict_alias_id(object, "client_id", "azp", 256)?
            .ok_or(AuthError::InvalidToken)?;
        let organization_id =
            strict_alias_id(object, "org_id", "organization_id", 256)?;
''',
    "unambiguous identifier aliases",
)

replace_once(
    '''    async fn cached(&self, key: [u8; 32]) -> Option<Principal> {
        let mut cache = self.cache.lock().await;
        let now = Instant::now();
        cache.retain(|_, entry| entry.expires_at > now);
        cache.get(&key).map(|entry| entry.principal.clone())
    }
''',
    '''    async fn cached(&self, key: [u8; 32]) -> Option<Principal> {
        let mut cache = self.cache.lock().await;
        let now = Instant::now();
        match cache.get(&key) {
            Some(entry) if entry.expires_at > now => Some(entry.principal.clone()),
            Some(_) => {
                cache.remove(&key);
                None
            }
            None => None,
        }
    }
''',
    "constant-work cache hit",
)

replace_once(
    '''fn strict_u64(claims: &Map<String, Value>, name: &str) -> Result<Option<u64>, AuthError> {
''',
    '''fn strict_alias_id(
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
''',
    "strict alias helper",
)

LIB.write_text(text)

hybrid = HYBRID.read_text()
marker = "async fn ambiguous_central_authority_claims_fail_closed()"
if marker not in hybrid:
    hybrid += '''

#[tokio::test]
async fn ambiguous_central_authority_claims_fail_closed() {
    let claims = access_claims();
    let token = access_token(&claims);

    let transport = FakeTransport::new();
    let mut multi_audience = central_claims(&claims);
    multi_audience["aud"] = json!(["tempera-document", "tempera-other"]);
    transport.insert(&token, multi_audience).await;
    let authorizer = HybridAuthorizer::with_transport(config(), transport).unwrap();
    assert_eq!(
        authorizer.authorize(&token, &["document:read"]).await,
        Err(AuthError::WrongAudience),
    );

    let transport = FakeTransport::new();
    let mut mismatched_scope_alias = central_claims(&claims);
    mismatched_scope_alias["scopes"] = json!(["document:read", "admin"]);
    transport.insert(&token, mismatched_scope_alias).await;
    let authorizer = HybridAuthorizer::with_transport(config(), transport).unwrap();
    assert_eq!(
        authorizer.authorize(&token, &["document:read"]).await,
        Err(AuthError::InvalidToken),
    );

    let transport = FakeTransport::new();
    let mut mismatched_client_alias = central_claims(&claims);
    mismatched_client_alias["azp"] = Value::String("other-client".into());
    transport.insert(&token, mismatched_client_alias).await;
    let authorizer = HybridAuthorizer::with_transport(config(), transport).unwrap();
    assert_eq!(
        authorizer.authorize(&token, &["document:read"]).await,
        Err(AuthError::InvalidToken),
    );
}
'''
HYBRID.write_text(hybrid)

hardening = HARDENING.read_text()
marker = "fn required_scope_collections_are_bounded()"
if marker not in hardening:
    hardening += '''

#[test]
fn required_scope_collections_are_bounded() {
    let mut c = base();
    c.required_scopes = (0..257).map(|index| format!("scope:{index}")).collect();
    assert!(matches!(
        c.validate(),
        Err(AuthError::InvalidConfiguration(_))
    ));
}
'''
HARDENING.write_text(hardening)

readme = README.read_text()
needle = "- Scope checks are repeated for each operation, including positive-cache hits.\n"
addition = (
    needle
    + "- Exactly one resource audience is accepted, and duplicate claim aliases must agree.\n"
    + "- Cache hits inspect only the requested entry; expiry sweeping remains off the hot path.\n"
)
if needle not in readme:
    raise SystemExit("README failure-boundary anchor changed")
README.write_text(readme.replace(needle, addition, 1))

print("auth runtime hot-path hardening applied")
