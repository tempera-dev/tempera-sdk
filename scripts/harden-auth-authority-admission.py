#!/usr/bin/env python3
"""Bound Auth Hub authority concurrency and isolate JWKS refresh I/O."""

from __future__ import annotations

import re
from pathlib import Path

LIB = Path("packages/auth-rust/src/lib.rs")
HYBRID = Path("packages/auth-rust/tests/hybrid.rs")
HARDENING = Path("packages/auth-rust/tests/hardening.rs")
README = Path("packages/auth-rust/README.md")

text = LIB.read_text(encoding="utf-8")


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


replace_once(
    "use tokio::sync::Mutex;",
    "use tokio::sync::{Mutex, Semaphore};",
    "Tokio synchronization imports",
)
replace_once(
    '''const DEFAULT_MAX_CACHE_ENTRIES: usize = 8_192;
const DEFAULT_MAX_TOKEN_BYTES: usize = 16 * 1024;''',
    '''const DEFAULT_MAX_CACHE_ENTRIES: usize = 8_192;
const DEFAULT_MAX_ACTIVE_FLIGHTS: usize = 4_096;
const DEFAULT_MAX_WAITERS_PER_FLIGHT: usize = 256;
const DEFAULT_MAX_INTROSPECTION_IN_FLIGHT: usize = 128;
const DEFAULT_INTROSPECTION_QUEUE_TIMEOUT: Duration = Duration::from_millis(250);
const DEFAULT_MAX_TOKEN_BYTES: usize = 16 * 1024;''',
    "authority admission defaults",
)
replace_once(
    '''    /// Maximum positive authorization entries retained in memory.
    pub max_cache_entries: usize,
    /// Maximum accepted bearer-token size.''',
    '''    /// Maximum positive authorization entries retained in memory.
    pub max_cache_entries: usize,
    /// Maximum distinct credential misses coordinated at once.
    pub max_active_flights: usize,
    /// Maximum waiting callers behind one credential's active authorization.
    pub max_waiters_per_flight: usize,
    /// Maximum central introspection requests running concurrently.
    pub max_introspection_in_flight: usize,
    /// Maximum time a central introspection request may wait for admission.
    pub introspection_queue_timeout: Duration,
    /// Maximum accepted bearer-token size.''',
    "authority admission configuration fields",
)
replace_once(
    '''            max_cache_entries: DEFAULT_MAX_CACHE_ENTRIES,
            max_token_bytes: DEFAULT_MAX_TOKEN_BYTES,''',
    '''            max_cache_entries: DEFAULT_MAX_CACHE_ENTRIES,
            max_active_flights: DEFAULT_MAX_ACTIVE_FLIGHTS,
            max_waiters_per_flight: DEFAULT_MAX_WAITERS_PER_FLIGHT,
            max_introspection_in_flight: DEFAULT_MAX_INTROSPECTION_IN_FLIGHT,
            introspection_queue_timeout: DEFAULT_INTROSPECTION_QUEUE_TIMEOUT,
            max_token_bytes: DEFAULT_MAX_TOKEN_BYTES,''',
    "authority admission configuration defaults",
)
replace_once(
    '''            || !(1..=1_000_000).contains(&self.max_cache_entries)
            || !(256..=65_536).contains(&self.max_token_bytes)''',
    '''            || !(1..=1_000_000).contains(&self.max_cache_entries)
            || !(1..=1_000_000).contains(&self.max_active_flights)
            || self.max_waiters_per_flight > 65_536
            || !(1..=65_536).contains(&self.max_introspection_in_flight)
            || self.introspection_queue_timeout < Duration::from_millis(1)
            || self.introspection_queue_timeout > Duration::from_secs(30)
            || !(256..=65_536).contains(&self.max_token_bytes)''',
    "authority admission configuration validation",
)
replace_once(
    '''            .field("max_cache_entries", &self.max_cache_entries)
            .field("max_token_bytes", &self.max_token_bytes)''',
    '''            .field("max_cache_entries", &self.max_cache_entries)
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
            .field("max_token_bytes", &self.max_token_bytes)''',
    "authority admission configuration debug fields",
)
replace_once(
    '''    fn get(&mut self, key: [u8; 32], now: Instant) -> Option<Principal> {
        self.prune_expired(now);
        self.entries.get(&key).map(|entry| entry.principal.clone())
    }''',
    '''    fn get(&mut self, key: [u8; 32], now: Instant) -> Option<Principal> {
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
    }''',
    "direct requested-entry expiry check",
)
replace_regex(
    r'''impl FlightLease \{\n    fn acquire\(flights: &Arc<StdMutex<HashMap<\[u8; 32\], FlightEntry>>>, key: \[u8; 32\]\) -> Self \{.*?\n    \}\n\}\n''',
    '''impl FlightLease {
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
''',
    "bounded singleflight admission",
)
replace_once(
    '''    claim_mismatches: AtomicU64,
    cache_evictions: AtomicU64,
}''',
    '''    claim_mismatches: AtomicU64,
    cache_evictions: AtomicU64,
    coordination_rejections: AtomicU64,
    introspection_admission_rejections: AtomicU64,
    jwks_refreshes: AtomicU64,
}''',
    "authority admission metrics",
)
replace_once(
    '''    /// Current credential keys with an active or waiting singleflight caller.
    pub active_flights: usize,
}''',
    '''    /// Current credential keys with an active or waiting singleflight caller.
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
}''',
    "authority admission metric snapshot fields",
)
replace_once(
    '''    cache: StdMutex<PositiveCache>,
    flights: Arc<StdMutex<HashMap<[u8; 32], FlightEntry>>>,
    jwks: Mutex<JwksCache>,
    metrics: Metrics,''',
    '''    cache: StdMutex<PositiveCache>,
    flights: Arc<StdMutex<HashMap<[u8; 32], FlightEntry>>>,
    jwks: Mutex<JwksCache>,
    jwks_refresh: Mutex<()>,
    introspection_permits: Semaphore,
    metrics: Metrics,''',
    "authority admission runtime state",
)
replace_once(
    '''    pub fn with_transport(config: Config, transport: T) -> Result<Self, AuthError> {
        config.validate()?;
        Ok(Self {
            config,
            transport,
            cache: StdMutex::new(PositiveCache::default()),
            flights: Arc::new(StdMutex::new(HashMap::new())),
            jwks: Mutex::new(JwksCache::default()),
            metrics: Metrics::default(),
        })
    }''',
    '''    pub fn with_transport(config: Config, transport: T) -> Result<Self, AuthError> {
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
    }''',
    "authority admission runtime construction",
)
replace_once(
    '''        let flight = FlightLease::acquire(&self.flights, cache_key);
        let gate = Arc::clone(&flight.gate);''',
    '''        let flight = FlightLease::acquire(
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
        let gate = Arc::clone(&flight.gate);''',
    "bounded singleflight runtime admission",
)
replace_once(
    '''        let positive_cache_entries = lock_recover(&self.cache).len();
        let active_flights = lock_recover(&self.flights).len();
        MetricsSnapshot {''',
    '''        let positive_cache_entries = lock_recover(&self.cache).len();
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
        MetricsSnapshot {''',
    "bounded runtime metric gauges",
)
replace_once(
    '''            cache_evictions: self.metrics.cache_evictions.load(Ordering::Relaxed),
            positive_cache_entries,
            active_flights,
        }''',
    '''            cache_evictions: self.metrics.cache_evictions.load(Ordering::Relaxed),
            positive_cache_entries,
            active_flights,
            active_flight_participants,
            coordination_rejections: self
                .metrics
                .coordination_rejections
                .load(Ordering::Relaxed),
            introspection_admission_rejections: self
                .metrics
                .introspection_admission_rejections
                .load(Ordering::Relaxed),
            introspection_in_flight,
            jwks_refreshes: self.metrics.jwks_refreshes.load(Ordering::Relaxed),
        }''',
    "bounded runtime metric values",
)
replace_once(
    '''        self.metrics.introspections.fetch_add(1, Ordering::Relaxed);
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
            })?;''',
    '''        let permit = tokio::time::timeout(
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
        drop(permit);''',
    "bounded central introspection admission",
)
replace_regex(
    r'''    async fn jwks_key\(&self, kid: &str\) -> Result<DecodingKey, AuthError> \{.*?\n    \}\n\n    fn principal_from_claims''',
    '''    async fn jwks_key(&self, kid: &str) -> Result<DecodingKey, AuthError> {
        let now = Instant::now();
        {
            let cache = self.jwks.lock().await;
            if let Some(key) = lookup_jwks_key(
                &cache,
                kid,
                now,
                self.config.jwks_refresh_cooldown,
            )? {
                return Ok(key);
            }
        }

        let _refresh_guard = self.jwks_refresh.lock().await;
        let now = Instant::now();
        {
            let mut cache = self.jwks.lock().await;
            if let Some(key) = lookup_jwks_key(
                &cache,
                kid,
                now,
                self.config.jwks_refresh_cooldown,
            )? {
                return Ok(key);
            }
            cache.last_refresh_attempt = Some(now);
        }

        self.metrics
            .jwks_refreshes
            .fetch_add(1, Ordering::Relaxed);
        let document = self
            .transport
            .fetch_jwks(&self.config.jwks_url, self.config.max_response_bytes)
            .await
            .inspect_err(|_| {
                self.metrics
                    .authority_failures
                    .fetch_add(1, Ordering::Relaxed);
            })?;
        let keys = parse_jwks(document).inspect_err(|_| {
            self.metrics
                .authority_failures
                .fetch_add(1, Ordering::Relaxed);
        })?;
        let requested = keys.get(kid).map(|key| key.key.clone());
        {
            let mut cache = self.jwks.lock().await;
            cache.keys = keys;
            cache.expires_at = Some(Instant::now() + self.config.jwks_cache_ttl);
        }
        requested.ok_or(AuthError::InvalidToken)
    }

    fn principal_from_claims''',
    "nonblocking JWKS refresh",
)
replace_once(
    '''fn lock_recover<T>(mutex: &StdMutex<T>) -> std::sync::MutexGuard<'_, T> {''',
    '''fn lookup_jwks_key(
    cache: &JwksCache,
    kid: &str,
    now: Instant,
    refresh_cooldown: Duration,
) -> Result<Option<DecodingKey>, AuthError> {
    if cache.expires_at.is_some_and(|expiry| expiry > now) {
        if let Some(key) = cache.keys.get(kid) {
            return Ok(Some(key.key.clone()));
        }
        if cache.last_refresh_attempt.is_some_and(|attempt| {
            now.saturating_duration_since(attempt) < refresh_cooldown
        }) {
            return Err(AuthError::InvalidToken);
        }
        return Ok(None);
    }
    if cache.last_refresh_attempt.is_some_and(|attempt| {
        now.saturating_duration_since(attempt) < refresh_cooldown
    }) {
        return Err(AuthError::Unavailable);
    }
    Ok(None)
}

fn lock_recover<T>(mutex: &StdMutex<T>) -> std::sync::MutexGuard<'_, T> {''',
    "JWKS cache lookup helper",
)

LIB.write_text(text, encoding="utf-8")

hybrid = HYBRID.read_text(encoding="utf-8")
old = '''#[derive(Clone)]
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
'''
new = '''struct ActiveCallGuard {
    active: Arc<AtomicUsize>,
}

impl Drop for ActiveCallGuard {
    fn drop(&mut self) {
        self.active.fetch_sub(1, Ordering::Relaxed);
    }
}

#[derive(Clone)]
struct FakeTransport {
    jwks: Arc<Mutex<Value>>,
    decisions: Arc<Mutex<HashMap<String, Value>>>,
    jwks_calls: Arc<AtomicUsize>,
    introspection_calls: Arc<AtomicUsize>,
    active_introspections: Arc<AtomicUsize>,
    max_active_introspections: Arc<AtomicUsize>,
    introspection_delay: Duration,
    jwks_delay: Duration,
}

impl FakeTransport {
    fn new() -> Self {
        Self {
            jwks: Arc::new(Mutex::new(jwks())),
            decisions: Arc::new(Mutex::new(HashMap::new())),
            jwks_calls: Arc::new(AtomicUsize::new(0)),
            introspection_calls: Arc::new(AtomicUsize::new(0)),
            active_introspections: Arc::new(AtomicUsize::new(0)),
            max_active_introspections: Arc::new(AtomicUsize::new(0)),
            introspection_delay: Duration::ZERO,
            jwks_delay: Duration::ZERO,
        }
    }

    fn with_delay(mut self, delay: Duration) -> Self {
        self.introspection_delay = delay;
        self
    }

    fn with_jwks_delay(mut self, delay: Duration) -> Self {
        self.jwks_delay = delay;
        self
    }

    fn max_active_introspections(&self) -> usize {
        self.max_active_introspections.load(Ordering::Relaxed)
    }

    async fn insert(&self, token: impl Into<String>, claims: Value) {
        self.decisions.lock().await.insert(token.into(), claims);
    }
}
'''
if hybrid.count(old) != 1:
    raise SystemExit(f"fake transport shape: expected one source block, found {hybrid.count(old)}")
hybrid = hybrid.replace(old, new, 1)
old = '''    async fn fetch_jwks(&self, _url: &str, _max_bytes: usize) -> Result<Value, AuthError> {
        self.jwks_calls.fetch_add(1, Ordering::Relaxed);
        Ok(self.jwks.lock().await.clone())
    }
'''
new = '''    async fn fetch_jwks(&self, _url: &str, _max_bytes: usize) -> Result<Value, AuthError> {
        self.jwks_calls.fetch_add(1, Ordering::Relaxed);
        if !self.jwks_delay.is_zero() {
            tokio::time::sleep(self.jwks_delay).await;
        }
        Ok(self.jwks.lock().await.clone())
    }
'''
if hybrid.count(old) != 1:
    raise SystemExit("JWKS test transport shape changed")
hybrid = hybrid.replace(old, new, 1)
old = '''        self.introspection_calls.fetch_add(1, Ordering::Relaxed);
        if !self.delay.is_zero() {
            tokio::time::sleep(self.delay).await;
        }
        Ok(self
'''
new = '''        self.introspection_calls.fetch_add(1, Ordering::Relaxed);
        let active = self.active_introspections.fetch_add(1, Ordering::Relaxed) + 1;
        self.max_active_introspections
            .fetch_max(active, Ordering::Relaxed);
        let _active_guard = ActiveCallGuard {
            active: Arc::clone(&self.active_introspections),
        };
        if !self.introspection_delay.is_zero() {
            tokio::time::sleep(self.introspection_delay).await;
        }
        Ok(self
'''
if hybrid.count(old) != 1:
    raise SystemExit("introspection test transport shape changed")
hybrid = hybrid.replace(old, new, 1)
old = '''fn access_token(claims: &Value) -> String {
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
'''
new = '''fn access_token(claims: &Value) -> String {
    access_token_with_kid(claims, "kid_test")
}

fn access_token_with_kid(claims: &Value, kid: &str) -> String {
    let mut header = Header::new(Algorithm::RS256);
    header.kid = Some(kid.into());
    header.typ = Some("at+jwt".into());
    encode(
        &header,
        claims,
        &EncodingKey::from_rsa_pem(PRIVATE_KEY.as_bytes()).unwrap(),
    )
    .unwrap()
}

fn api_key_claims(key_id: &str) -> Value {
    json!({
        "active": true,
        "iss": "http://127.0.0.1:8080",
        "aud": "tempera-document",
        "sub": "usr_service",
        "client_id": "raw-api",
        "token_type": "api_key",
        "api_key_id": key_id,
        "org_id": "org_test",
        "project_id": "proj_test",
        "environment_id": "env_test",
        "scope": "document:read"
    })
}

async fn wait_for_counter(counter: &AtomicUsize, expected: usize) {
    tokio::time::timeout(Duration::from_secs(2), async {
        while counter.load(Ordering::Relaxed) < expected {
            tokio::task::yield_now().await;
        }
    })
    .await
    .unwrap();
}

async fn wait_for_flight_participants<T: AuthorityTransport>(
    authorizer: &HybridAuthorizer<T>,
    expected: usize,
) {
    tokio::time::timeout(Duration::from_secs(2), async {
        while authorizer.metrics().active_flight_participants < expected {
            tokio::task::yield_now().await;
        }
    })
    .await
    .unwrap();
}
'''
if hybrid.count(old) != 1:
    raise SystemExit("access token test helper shape changed")
hybrid = hybrid.replace(old, new, 1)
append_marker = '''#[test]
fn configuration_rejects_insecure_or_unbounded_authority() {'''
if hybrid.count(append_marker) != 1:
    raise SystemExit("hybrid authority test insertion marker changed")
new_tests = r'''#[tokio::test]
async fn central_introspection_concurrency_is_strictly_bounded() {
    let transport = FakeTransport::new().with_delay(Duration::from_millis(200));
    let mut bounded = config();
    bounded.max_introspection_in_flight = 2;
    bounded.introspection_queue_timeout = Duration::from_millis(20);
    let authorizer =
        Arc::new(HybridAuthorizer::with_transport(bounded, transport.clone()).unwrap());

    for suffix in ["a", "b", "c"] {
        transport
            .insert(format!("tp_key_{suffix}.secret"), api_key_claims(&format!("key_{suffix}")))
            .await;
    }
    let mut tasks = Vec::new();
    for suffix in ["a", "b"] {
        let authorizer = Arc::clone(&authorizer);
        let token = format!("tp_key_{suffix}.secret");
        tasks.push(tokio::spawn(async move {
            authorizer.authorize(&token, &["document:read"]).await
        }));
    }
    wait_for_counter(&transport.active_introspections, 2).await;
    assert_eq!(
        authorizer
            .authorize("tp_key_c.secret", &["document:read"])
            .await,
        Err(AuthError::Unavailable),
    );
    for task in tasks {
        assert!(task.await.unwrap().is_ok());
    }
    assert_eq!(transport.max_active_introspections(), 2);
    let metrics = authorizer.metrics();
    assert_eq!(metrics.introspection_admission_rejections, 1);
    assert_eq!(metrics.introspections, 2);
    assert_eq!(metrics.introspection_in_flight, 0);
}

#[tokio::test]
async fn distinct_credential_flights_are_strictly_bounded() {
    let transport = FakeTransport::new().with_delay(Duration::from_millis(200));
    let mut bounded = config();
    bounded.max_active_flights = 2;
    let authorizer =
        Arc::new(HybridAuthorizer::with_transport(bounded, transport.clone()).unwrap());

    for suffix in ["a", "b", "c"] {
        transport
            .insert(format!("tp_key_{suffix}.secret"), api_key_claims(&format!("key_{suffix}")))
            .await;
    }
    let mut tasks = Vec::new();
    for suffix in ["a", "b"] {
        let authorizer = Arc::clone(&authorizer);
        let token = format!("tp_key_{suffix}.secret");
        tasks.push(tokio::spawn(async move {
            authorizer.authorize(&token, &["document:read"]).await
        }));
    }
    wait_for_counter(&transport.active_introspections, 2).await;
    assert_eq!(
        authorizer
            .authorize("tp_key_c.secret", &["document:read"])
            .await,
        Err(AuthError::Unavailable),
    );
    for task in tasks {
        assert!(task.await.unwrap().is_ok());
    }
    assert_eq!(authorizer.metrics().coordination_rejections, 1);
    assert_eq!(transport.introspection_calls.load(Ordering::Relaxed), 2);
}

#[tokio::test]
async fn per_credential_waiters_are_strictly_bounded() {
    let transport = FakeTransport::new().with_delay(Duration::from_millis(200));
    let token = "tp_key_shared.secret";
    transport.insert(token, api_key_claims("key_shared")).await;
    let mut bounded = config();
    bounded.max_waiters_per_flight = 1;
    let authorizer =
        Arc::new(HybridAuthorizer::with_transport(bounded, transport.clone()).unwrap());

    let leader_authorizer = Arc::clone(&authorizer);
    let leader = tokio::spawn(async move {
        leader_authorizer
            .authorize(token, &["document:read"])
            .await
    });
    wait_for_counter(&transport.active_introspections, 1).await;
    let waiter_authorizer = Arc::clone(&authorizer);
    let waiter = tokio::spawn(async move {
        waiter_authorizer
            .authorize(token, &["document:read"])
            .await
    });
    wait_for_flight_participants(&authorizer, 2).await;
    assert_eq!(
        authorizer.authorize(token, &["document:read"]).await,
        Err(AuthError::Unavailable),
    );
    assert!(leader.await.unwrap().is_ok());
    assert!(waiter.await.unwrap().is_ok());
    assert_eq!(transport.introspection_calls.load(Ordering::Relaxed), 1);
    assert_eq!(authorizer.metrics().coordination_rejections, 1);
}

#[tokio::test]
async fn jwks_refresh_does_not_block_a_fresh_cached_key() {
    let transport = FakeTransport::new().with_jwks_delay(Duration::from_millis(200));
    let authorizer =
        Arc::new(HybridAuthorizer::with_transport(config(), transport.clone()).unwrap());

    let mut initial_claims = access_claims();
    initial_claims["jti"] = Value::String("jti_initial".into());
    let initial_token = access_token(&initial_claims);
    transport
        .insert(&initial_token, central_claims(&initial_claims))
        .await;
    authorizer
        .authorize(&initial_token, &["document:read"])
        .await
        .unwrap();

    let mut unknown_claims = access_claims();
    unknown_claims["jti"] = Value::String("jti_unknown".into());
    let unknown_token = access_token_with_kid(&unknown_claims, "kid_unknown");
    transport
        .insert(&unknown_token, central_claims(&unknown_claims))
        .await;
    let unknown_authorizer = Arc::clone(&authorizer);
    let unknown = tokio::spawn(async move {
        unknown_authorizer
            .authorize(&unknown_token, &["document:read"])
            .await
    });
    wait_for_counter(&transport.jwks_calls, 2).await;

    let mut known_claims = access_claims();
    known_claims["jti"] = Value::String("jti_known_during_refresh".into());
    let known_token = access_token(&known_claims);
    transport
        .insert(&known_token, central_claims(&known_claims))
        .await;
    let known_result = tokio::time::timeout(
        Duration::from_millis(100),
        authorizer.authorize(&known_token, &["document:read"]),
    )
    .await
    .expect("fresh cached key must not wait for unrelated JWKS refresh");
    assert!(known_result.is_ok());
    assert_eq!(unknown.await.unwrap(), Err(AuthError::InvalidToken));
    assert_eq!(transport.jwks_calls.load(Ordering::Relaxed), 2);
}

#[tokio::test]
async fn concurrent_unknown_key_refreshes_are_singleflighted() {
    let transport = FakeTransport::new().with_jwks_delay(Duration::from_millis(100));
    let authorizer =
        Arc::new(HybridAuthorizer::with_transport(config(), transport.clone()).unwrap());
    let mut tasks = Vec::new();
    for suffix in ["a", "b"] {
        let mut claims = access_claims();
        claims["jti"] = Value::String(format!("jti_unknown_{suffix}"));
        let token = access_token_with_kid(&claims, "kid_unknown");
        transport.insert(&token, central_claims(&claims)).await;
        let authorizer = Arc::clone(&authorizer);
        tasks.push(tokio::spawn(async move {
            authorizer.authorize(&token, &["document:read"]).await
        }));
    }
    for task in tasks {
        assert_eq!(task.await.unwrap(), Err(AuthError::InvalidToken));
    }
    assert_eq!(transport.jwks_calls.load(Ordering::Relaxed), 1);
    assert_eq!(authorizer.metrics().jwks_refreshes, 1);
}

'''
hybrid = hybrid.replace(append_marker, new_tests + append_marker, 1)
HYBRID.write_text(hybrid, encoding="utf-8")

hardening = HARDENING.read_text(encoding="utf-8")
hardening += r'''

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
'''
HARDENING.write_text(hardening, encoding="utf-8")

readme = README.read_text(encoding="utf-8")
old = "Concurrent misses for the same token are singleflighted through cancellation-safe leases. Positive-cache lookup is O(1), expiry and capacity eviction are O(log n), and cache/flight keys are SHA-256 digests; raw bearer values are never retained as map keys, metric labels, or log fields."
new = "Concurrent misses for the same token are singleflighted through cancellation-safe leases with hard limits on distinct credentials and per-token waiters. Positive-cache lookup is O(1), expiry and capacity eviction are O(log n), and cache/flight keys are SHA-256 digests; raw bearer values are never retained as map keys, metric labels, or log fields."
if readme.count(old) != 1:
    raise SystemExit("README singleflight paragraph changed")
readme = readme.replace(old, new, 1)
old = "- JWKS and introspection responses are size-bounded, redirects are disabled, and the runtime never authorizes from stale-on-error state."
new = "- JWKS and introspection responses are size-bounded, redirects are disabled, and the runtime never authorizes from stale-on-error state. JWKS network refresh is singleflighted without holding the shared key-cache lock."
if readme.count(old) != 1:
    raise SystemExit("README authority response bullet changed")
readme = readme.replace(old, new, 1)
old = "- Cancelling an authorization future releases its singleflight lease; later requests cannot inherit unreachable coordination state from an aborted caller."
new = "- Cancelling an authorization future releases its singleflight lease; later requests cannot inherit unreachable coordination state from an aborted caller. Distinct flights, per-token waiters, and concurrent introspection are all bounded, and overload fails as unavailable."
if readme.count(old) != 1:
    raise SystemExit("README cancellation bullet changed")
readme = readme.replace(old, new, 1)
old = "The package exposes privacy-safe counters and bounded-state gauges for cache hits/misses/evictions, local JWT rejection, introspection, authority failure, claim mismatch, positive-cache entries, and active singleflight keys. They contain no credential or tenant identifiers."
new = "The package exposes privacy-safe counters and bounded-state gauges for cache hits/misses/evictions, local JWT rejection, introspection admission, authority failure, claim mismatch, JWKS refresh, positive-cache entries, active singleflight keys/participants, and introspection in flight. They contain no credential or tenant identifiers."
if readme.count(old) != 1:
    raise SystemExit("README metrics paragraph changed")
README.write_text(readme.replace(old, new, 1), encoding="utf-8")

print("bounded Auth Hub authority admission and JWKS refresh applied")
