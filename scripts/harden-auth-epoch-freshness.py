#!/usr/bin/env python3
"""Require signed security epochs and prove bounded central revocation freshness."""

from pathlib import Path

LIB = Path("packages/auth-rust/src/lib.rs")
TEST = Path("packages/auth-rust/tests/hybrid.rs")
README = Path("packages/auth-rust/README.md")

text = LIB.read_text(encoding="utf-8")
old = '''        let security_epoch = strict_u64(object, "security_epoch")?;
        let grant_id = strict_id(object, "grant_id", 256)?;'''
new = '''        let security_epoch = strict_u64(object, "security_epoch")?;
        if token_type == "access_token" && security_epoch.is_none() {
            return Err(AuthError::InvalidToken);
        }
        let grant_id = strict_id(object, "grant_id", 256)?;'''
if text.count(old) != 1:
    raise SystemExit(f"security epoch parse marker changed: {text.count(old)}")
LIB.write_text(text.replace(old, new, 1), encoding="utf-8")

hybrid = TEST.read_text(encoding="utf-8")
marker = '''#[tokio::test]
async fn forged_jwt_is_rejected_before_introspection() {'''
if hybrid.count(marker) != 1:
    raise SystemExit("hybrid insertion marker changed")
tests = r'''#[tokio::test]
async fn signed_access_tokens_require_a_security_epoch() {
    let transport = FakeTransport::new();
    let mut claims = access_claims();
    claims.as_object_mut().unwrap().remove("security_epoch");
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
async fn central_security_epoch_must_exactly_match_the_signed_epoch() {
    let transport = FakeTransport::new();
    let claims = access_claims();
    let token = access_token(&claims);
    let mut central = central_claims(&claims);
    central["security_epoch"] = Value::from(8_u64);
    transport.insert(&token, central).await;
    let authorizer = HybridAuthorizer::with_transport(config(), transport.clone()).unwrap();

    assert_eq!(
        authorizer.authorize(&token, &["document:read"]).await,
        Err(AuthError::ClaimMismatch),
    );
    assert_eq!(authorizer.metrics().claim_mismatches, 1);
}

#[tokio::test]
async fn central_revocation_is_observed_after_the_positive_freshness_window() {
    let transport = FakeTransport::new();
    let claims = access_claims();
    let token = access_token(&claims);
    transport.insert(&token, central_claims(&claims)).await;
    let mut bounded = config();
    bounded.positive_cache_ttl = Duration::from_millis(20);
    let authorizer = HybridAuthorizer::with_transport(bounded, transport.clone()).unwrap();

    authorizer
        .authorize(&token, &["document:read"])
        .await
        .expect("initial central authorization");
    transport.insert(&token, json!({ "active": false })).await;

    // A positive decision may be reused only inside the explicitly configured
    // freshness window.
    authorizer
        .authorize(&token, &["document:read"])
        .await
        .expect("bounded positive cache hit");
    tokio::time::sleep(Duration::from_millis(30)).await;
    assert_eq!(
        authorizer.authorize(&token, &["document:read"]).await,
        Err(AuthError::InvalidToken),
    );
    assert_eq!(transport.introspection_calls.load(Ordering::Relaxed), 2);
}

'''
TEST.write_text(hybrid.replace(marker, tests + marker, 1), encoding="utf-8")

readme = README.read_text(encoding="utf-8")
old = "- Access tokens require integer `iat` and `exp` claims. Their lifetime is bounded to one hour by default and is configurable only within the runtime's safety limits."
new = "- Access tokens require integer `iat`, `exp`, and `security_epoch` claims. Their lifetime is bounded to one hour by default; the signed security epoch must exactly match Auth Hub's current server-controlled epoch on central confirmation."
if readme.count(old) != 1:
    raise SystemExit("README access-token invariant changed")
README.write_text(readme.replace(old, new, 1), encoding="utf-8")

print("security epoch freshness hardening applied")
