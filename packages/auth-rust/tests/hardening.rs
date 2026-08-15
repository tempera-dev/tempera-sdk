//! Adversarial configuration tests for the hybrid authorization runtime.

use std::time::Duration;
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
    assert!(matches!(
        c.validate(),
        Err(AuthError::InvalidConfiguration(_))
    ));
    let mut c = base();
    c.introspection_secret = None;
    assert!(matches!(
        c.validate(),
        Err(AuthError::InvalidConfiguration(_))
    ));
}

#[test]
fn insecure_http_is_loopback_only() {
    let mut c = Config::new(
        "http://127.0.0.1:8080",
        "tempera-document",
        "http://127.0.0.1:8080/jwks",
        "http://127.0.0.1:8080/introspect",
    );
    c.allow_insecure_http = true;
    assert!(c.validate().is_ok());
    c.issuer_url = "http://auth.example.test".into();
    c.jwks_url = "http://auth.example.test/jwks".into();
    c.introspection_url = "http://auth.example.test/introspect".into();
    assert!(matches!(
        c.validate(),
        Err(AuthError::InvalidConfiguration(_))
    ));
}

#[test]
fn jwt_lifetime_bounds_are_validated() {
    let mut c = base();
    c.max_access_token_lifetime_seconds = 59;
    assert!(matches!(
        c.validate(),
        Err(AuthError::InvalidConfiguration(_))
    ));
    c.max_access_token_lifetime_seconds = 3600;
    c.positive_cache_ttl = Duration::from_secs(31);
    assert!(matches!(
        c.validate(),
        Err(AuthError::InvalidConfiguration(_))
    ));
}

#[test]
fn required_scope_collections_are_bounded() {
    let mut c = base();
    c.required_scopes = (0..257).map(|index| format!("scope:{index}")).collect();
    assert!(matches!(
        c.validate(),
        Err(AuthError::InvalidConfiguration(_))
    ));
}

#[test]
fn authority_admission_bounds_are_validated() {
    let mut c = base();
    c.max_active_flights = 0;
    assert!(matches!(
        c.validate(),
        Err(AuthError::InvalidConfiguration(_))
    ));
    c.max_active_flights = 1;
    c.max_waiters_per_flight = 65_537;
    assert!(matches!(
        c.validate(),
        Err(AuthError::InvalidConfiguration(_))
    ));
    c.max_waiters_per_flight = 0;
    c.max_introspection_in_flight = 0;
    assert!(matches!(
        c.validate(),
        Err(AuthError::InvalidConfiguration(_))
    ));
    c.max_introspection_in_flight = 1;
    c.introspection_queue_timeout = Duration::ZERO;
    assert!(matches!(
        c.validate(),
        Err(AuthError::InvalidConfiguration(_))
    ));
}
