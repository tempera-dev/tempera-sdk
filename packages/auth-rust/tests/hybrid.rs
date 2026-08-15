//! Adversarial hybrid authorization tests.

use std::{
    collections::HashMap,
    sync::{
        Arc,
        atomic::{AtomicUsize, Ordering},
    },
    time::{Duration, SystemTime, UNIX_EPOCH},
};

use async_trait::async_trait;
use jsonwebtoken::{Algorithm, EncodingKey, Header, encode};
use serde_json::{Value, json};
use tempera_auth_runtime::{AuthError, AuthorityTransport, Config, HybridAuthorizer, Principal};
use tokio::sync::Mutex;

const PRIVATE_KEY: &str = r"-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDZsF3ktWlTVOg/
ys+jzw3QWWS/lcthMdYEtUw8treTA9xWGh6tTXr7xOicgdBG/kFxu3/eHBSVwCFE
+BNL0FwiFnMx6cgkV793lOAvLShj8FEqK5G/5vBLU4becgHoVLuDOLObaXJBvls+
4yqPK5oLg5K7BECaa2YcPSBUwvhCgVRZfOhcnm6CNiQKFlftM+VohlyA40QE1MXg
cp9hOgh7m4p/DwiDx2bkbwbm06LbfVar+tv4khXsJSSDqm0IpoIVD/8IhzNpvWuv
qYIt1UPJAcHJJi9ridQWvEe6xz4vEJl5S+9eaY7UKDT5F7KDLWaWB4cTdGyH/hWY
qpgA+VXfAgMBAAECggEAS5p2MZ1TtC5T7vvX+3NIv+icFfHHTb1KMB5rGNb4kKWR
m5G8v8GeCdzMULbBCDb7sa1F7nTgLVYp99MUmIsHxIr5fQdNjFmxVK2u4pOTaIop
FjVFjFl/cRnUSGNeCDuNWDiUIFCR7wVWmVO6Dzk8ae1LQ4ppiXftYbdVCDsij63J
AEv5G0KLCjIvE+6HMqd51fceBwNJPVnyJtvTbiQV2eGvpwdVnKBCJMHhjE+Enhb/
aQ3UlNfgZsntURjoN/+Vlhjrci8Z7dv63L3YbIEwiGTk72y1E57dpUH91tJL37WV
E7G1TujyxzYy/Nooh8tFwjibJbtPopMR1q4Gl1qkiQKBgQDx8GueQjoy6uU3VhW0
qAphUa29bVIjeTQtU7Ou2I9l9SqK329xLUph80Iza7hka0jqJpvwMYQo2SYg3XCs
U0rYfgBgr3XyTr0UGRDq3qKEDjgyXw036hDDLI5eCZuP1XqbQzYlgeak2jm9ogVj
Z7GGOZIbCZItBQp1z+aKH/sPEwKBgQDmVyae/sLGN5OVl2evJTCS4r/JlBvfAAvP
kuX8q4nk35fAMSFG1H5Que2UPDAv7CSpKneirHjLlV8K50+udIIfJomIhAalluFW
IRZj7X9JVXpgHa0TtddN5XLEjjlFb1sGmUFLB56TGavyhSOL/VUCv/iEOk893AW9
Kj9vJC6bhQKBgQCdJkYxCOGWuz7h/7efndsINa69sSm+QvciThETjDUwy9uzUsin
YfzDvOeOUPT3vTwiY6u8i91FTy9V/6A1PvEJyGZkZvQczQpB6Lo1ZSF412enSFhk
rlPvAp0C9giml8rI2RJtsH/pKpqA06HeXLdR8Uk26LObLIAL4Fvl8jn4IwKBgBe9
1eI/eg36PoEFuQ8pcydAren2FSVYGN+NUZ1IhQ8NKNQLfFWTo21orJ9B0OmvmlvB
X9Fpm43IWKKEEwd1RNA3Jafni9PXiGRbRraIDT2ezN1JUcSdUpLZ2ol961NH1gcJ
FtzH7UVWOQ3nQTG1q+R7qv7eD7rdic3ko+MtxIwNAoGAcPK3VNs0GNqLr7Fz5DvF
4WWlD8oFAroeAL+vV/tygAYUDSpr0sV+ZQQj6wUCwmCfDSWXm27eD9WHzCt0yR2m
HyGCvi0YYjH3WoHRlPVh6SUTSMSYsDu7/2AysIz5g6Mnc5DgfQNIYQUTH6PZLpR3
ggCuCXluMgEs4vPUzDm3M14=
-----END PRIVATE KEY-----
";

fn jwks() -> Value {
    json!({
        "keys": [{
            "kty": "RSA",
            "n": "2bBd5LVpU1ToP8rPo88N0Flkv5XLYTHWBLVMPLa3kwPcVhoerU16-8TonIHQRv5Bcbt_3hwUlcAhRPgTS9BcIhZzMenIJFe_d5TgLy0oY_BRKiuRv-bwS1OG3nIB6FS7gzizm2lyQb5bPuMqjyuaC4OSuwRAmmtmHD0gVML4QoFUWXzoXJ5ugjYkChZX7TPlaIZcgONEBNTF4HKfYToIe5uKfw8Ig8dm5G8G5tOi231Wq_rb-JIV7CUkg6ptCKaCFQ__CIczab1rr6mCLdVDyQHBySYva4nUFrxHusc-LxCZeUvvXmmO1Cg0-Reygy1mlgeHE3Rsh_4VmKqYAPlV3w",
            "e": "AQAB",
            "kid": "kid_test",
            "alg": "RS256",
            "use": "sig",
            "key_ops": ["verify"]
        }]
    })
}

#[derive(Clone)]
struct FakeTransport {
    jwks: Arc<Mutex<Value>>,
    decisions: Arc<Mutex<HashMap<String, Value>>>,
    jwks_calls: Arc<AtomicUsize>,
    introspection_calls: Arc<AtomicUsize>,
    delay: Duration,
}

impl FakeTransport {
    fn new() -> Self {
        Self {
            jwks: Arc::new(Mutex::new(jwks())),
            decisions: Arc::new(Mutex::new(HashMap::new())),
            jwks_calls: Arc::new(AtomicUsize::new(0)),
            introspection_calls: Arc::new(AtomicUsize::new(0)),
            delay: Duration::ZERO,
        }
    }

    fn with_delay(mut self, delay: Duration) -> Self {
        self.delay = delay;
        self
    }

    async fn insert(&self, token: impl Into<String>, claims: Value) {
        self.decisions.lock().await.insert(token.into(), claims);
    }
}

#[async_trait]
impl AuthorityTransport for FakeTransport {
    async fn fetch_jwks(&self, _url: &str, _max_bytes: usize) -> Result<Value, AuthError> {
        self.jwks_calls.fetch_add(1, Ordering::Relaxed);
        Ok(self.jwks.lock().await.clone())
    }

    async fn introspect(
        &self,
        _url: &str,
        _secret: Option<&str>,
        token: &str,
        _max_bytes: usize,
    ) -> Result<Value, AuthError> {
        self.introspection_calls.fetch_add(1, Ordering::Relaxed);
        if !self.delay.is_zero() {
            tokio::time::sleep(self.delay).await;
        }
        Ok(self
            .decisions
            .lock()
            .await
            .get(token)
            .cloned()
            .unwrap_or_else(|| json!({ "active": false })))
    }
}

fn config() -> Config {
    let mut config = Config::new(
        "http://127.0.0.1:8080",
        "tempera-document",
        "http://127.0.0.1:8080/.well-known/jwks.json",
        "http://127.0.0.1:8080/v1/oauth/introspect",
    );
    config.allow_insecure_http = true;
    config.introspection_secret = Some("resource-server-secret".into());
    config.positive_cache_ttl = Duration::from_secs(5);
    config.jwks_cache_ttl = Duration::from_mins(1);
    config.jwks_refresh_cooldown = Duration::from_millis(25);
    config
}

fn now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs()
}

fn access_claims() -> Value {
    let issued = now();
    json!({
        "iss": "http://127.0.0.1:8080",
        "aud": "tempera-document",
        "sub": "usr_test",
        "client_id": "tempera-public-site",
        "org_id": "org_test",
        "project_id": "proj_test",
        "environment_id": "env_test",
        "scope": "document:read document:write",
        "iat": issued,
        "exp": issued + 300,
        "jti": "jti_test",
        "security_epoch": 7,
        "grant_id": "grant_test"
    })
}

fn access_token(claims: &Value) -> String {
    let mut header = Header::new(Algorithm::RS256);
    header.kid = Some("kid_test".into());
    header.typ = Some("at+jwt".into());
    encode(
        &header,
        claims,
        &EncodingKey::from_rsa_pem(PRIVATE_KEY.as_bytes()).unwrap(),
    )
    .unwrap()
}

fn central_claims(local: &Value) -> Value {
    let mut object = local.as_object().unwrap().clone();
    object.insert("active".into(), Value::Bool(true));
    object.insert("token_type".into(), Value::String("access_token".into()));
    Value::Object(object)
}

fn assert_document_principal(principal: &Principal) {
    assert_eq!(principal.subject, "usr_test");
    assert_eq!(principal.client_id, "tempera-public-site");
    assert_eq!(principal.token_type, "access_token");
    assert_eq!(principal.credential_id, "jti_test");
    assert_eq!(principal.organization_id.as_deref(), Some("org_test"));
    assert_eq!(principal.project_id.as_deref(), Some("proj_test"));
    assert_eq!(principal.environment_id.as_deref(), Some("env_test"));
    assert_eq!(principal.security_epoch, Some(7));
    assert!(principal.has_scope("document:read"));
}

#[tokio::test]
async fn valid_jwt_is_locally_verified_centrally_confirmed_and_cached() {
    let transport = FakeTransport::new();
    let claims = access_claims();
    let token = access_token(&claims);
    transport.insert(&token, central_claims(&claims)).await;
    let authorizer = HybridAuthorizer::with_transport(config(), transport.clone()).unwrap();

    let first = authorizer
        .authorize(&token, &["document:read"])
        .await
        .unwrap();
    assert_document_principal(&first);
    let second = authorizer
        .authorize(&token, &["document:read"])
        .await
        .unwrap();
    assert_eq!(second, first);
    assert_eq!(transport.jwks_calls.load(Ordering::Relaxed), 1);
    assert_eq!(transport.introspection_calls.load(Ordering::Relaxed), 1);
    assert_eq!(authorizer.metrics().cache_hits, 1);
}

#[tokio::test]
async fn forged_jwt_is_rejected_before_introspection() {
    let transport = FakeTransport::new();
    let claims = access_claims();
    let mut token = access_token(&claims);
    let replacement = if token.ends_with('a') { 'b' } else { 'a' };
    token.pop();
    token.push(replacement);
    transport.insert(&token, central_claims(&claims)).await;
    let authorizer = HybridAuthorizer::with_transport(config(), transport.clone()).unwrap();

    assert_eq!(
        authorizer.authorize(&token, &["document:read"]).await,
        Err(AuthError::InvalidToken),
    );
    assert_eq!(transport.introspection_calls.load(Ordering::Relaxed), 0);
    assert_eq!(authorizer.metrics().local_jwt_rejections, 1);
}

#[tokio::test]
async fn central_revocation_and_claim_mismatch_fail_closed() {
    let revoked_transport = FakeTransport::new();
    let claims = access_claims();
    let token = access_token(&claims);
    revoked_transport
        .insert(&token, json!({ "active": false }))
        .await;
    let revoked = HybridAuthorizer::with_transport(config(), revoked_transport).unwrap();
    assert_eq!(
        revoked.authorize(&token, &["document:read"]).await,
        Err(AuthError::InvalidToken),
    );

    let mismatch_transport = FakeTransport::new();
    let mut central = central_claims(&claims);
    central["org_id"] = Value::String("org_other".into());
    mismatch_transport.insert(&token, central).await;
    let mismatch = HybridAuthorizer::with_transport(config(), mismatch_transport).unwrap();
    assert_eq!(
        mismatch.authorize(&token, &["document:read"]).await,
        Err(AuthError::ClaimMismatch),
    );
    assert_eq!(mismatch.metrics().claim_mismatches, 1);
}

#[tokio::test]
async fn opaque_api_keys_are_centrally_introspected_and_bounded_cached() {
    let transport = FakeTransport::new();
    let token = "tp_key_opaque.secret";
    transport
        .insert(
            token,
            json!({
                "active": true,
                "iss": "http://127.0.0.1:8080",
                "aud": "tempera-document",
                "sub": "usr_service",
                "client_id": "raw-api",
                "token_type": "api_key",
                "api_key_id": "key_opaque",
                "org_id": "org_test",
                "project_id": "proj_test",
                "environment_id": "env_test",
                "scope": "document:read"
            }),
        )
        .await;
    let authorizer = HybridAuthorizer::with_transport(config(), transport.clone()).unwrap();

    let first = authorizer
        .authorize(token, &["document:read"])
        .await
        .unwrap();
    let second = authorizer
        .authorize(token, &["document:read"])
        .await
        .unwrap();
    assert_eq!(first, second);
    assert_eq!(first.token_type, "api_key");
    assert_eq!(transport.jwks_calls.load(Ordering::Relaxed), 0);
    assert_eq!(transport.introspection_calls.load(Ordering::Relaxed), 1);
}

#[tokio::test]
async fn concurrent_cache_misses_singleflight_to_one_authority_decision() {
    let transport = FakeTransport::new().with_delay(Duration::from_millis(50));
    let claims = access_claims();
    let token = access_token(&claims);
    transport.insert(&token, central_claims(&claims)).await;
    let authorizer =
        Arc::new(HybridAuthorizer::with_transport(config(), transport.clone()).unwrap());

    let mut tasks = Vec::new();
    for _ in 0..32 {
        let authorizer = Arc::clone(&authorizer);
        let token = token.clone();
        tasks.push(tokio::spawn(async move {
            authorizer.authorize(&token, &["document:read"]).await
        }));
    }
    for task in tasks {
        assert_document_principal(&task.await.unwrap().unwrap());
    }
    assert_eq!(transport.jwks_calls.load(Ordering::Relaxed), 1);
    assert_eq!(transport.introspection_calls.load(Ordering::Relaxed), 1);
}

#[tokio::test]
async fn operation_scope_is_checked_against_cached_authority() {
    let transport = FakeTransport::new();
    let claims = access_claims();
    let token = access_token(&claims);
    transport.insert(&token, central_claims(&claims)).await;
    let authorizer = HybridAuthorizer::with_transport(config(), transport.clone()).unwrap();

    authorizer
        .authorize(&token, &["document:read"])
        .await
        .unwrap();
    assert_eq!(
        authorizer.authorize(&token, &["admin"]).await,
        Err(AuthError::MissingScope("admin".into())),
    );
    assert_eq!(transport.introspection_calls.load(Ordering::Relaxed), 1);
}

#[test]
fn configuration_rejects_insecure_or_unbounded_authority() {
    let mut secure = Config::new(
        "https://api.tempera.dev",
        "tempera-document",
        "https://api.tempera.dev/.well-known/jwks.json",
        "https://api.tempera.dev/v1/oauth/introspect",
    );
    secure.introspection_secret = Some("resource-server-secret".into());
    assert!(secure.validate().is_ok());

    let insecure = Config::new(
        "http://api.tempera.dev",
        "tempera-document",
        "http://api.tempera.dev/.well-known/jwks.json",
        "http://api.tempera.dev/v1/oauth/introspect",
    );
    assert!(matches!(
        insecure.validate(),
        Err(AuthError::InvalidConfiguration(_)),
    ));
}

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
