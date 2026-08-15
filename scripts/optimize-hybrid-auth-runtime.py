#!/usr/bin/env python3
"""Make hybrid authorization cache and singleflight bounded and cancellation-safe."""

from __future__ import annotations

import re
from pathlib import Path

LIB = Path("packages/auth-rust/src/lib.rs")
TEST = Path("packages/auth-rust/tests/hybrid.rs")
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
    '''use std::{
    collections::{BTreeSet, HashMap},
    fmt,
    sync::{
        Arc,
        atomic::{AtomicU64, Ordering},
    },
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};''',
    '''use std::{
    cmp::Reverse,
    collections::{BTreeSet, BinaryHeap, HashMap},
    fmt,
    sync::{
        Arc, Mutex as StdMutex,
        atomic::{AtomicU64, Ordering},
    },
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};''',
    "bounded-cache imports",
)

replace_regex(
    r'''#\[derive\(Clone\)\]\nstruct CacheEntry \{.*?\n\}\n\n#\[derive\(Clone\)\]\nstruct CachedJwk''',
    '''#[derive(Clone)]
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
        while let Some(Reverse((expires_at, generation, key))) =
            self.expirations.peek().copied()
        {
            if expires_at > now {
                break;
            }
            self.expirations.pop();
            if self.entries.get(&key).is_some_and(|entry| {
                entry.generation == generation && entry.expires_at <= now
            }) {
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
    ) -> Self {
        let mut entries = lock_recover(flights);
        let entry = entries.entry(key).or_insert_with(|| FlightEntry {
            gate: Arc::new(Mutex::new(())),
            users: 0,
        });
        entry.users = entry.users.saturating_add(1);
        Self {
            key,
            gate: Arc::clone(&entry.gate),
            flights: Arc::clone(flights),
        }
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
struct CachedJwk''',
    "positive cache and flight lease",
)

replace_once(
    '''    claim_mismatches: AtomicU64,
}''',
    '''    claim_mismatches: AtomicU64,
    cache_evictions: AtomicU64,
}''',
    "cache eviction counter",
)
replace_once(
    '''    /// Local JWT and central claim mismatches.
    pub claim_mismatches: u64,
}''',
    '''    /// Local JWT and central claim mismatches.
    pub claim_mismatches: u64,
    /// Positive authorization entries evicted at the configured bound.
    pub cache_evictions: u64,
    /// Current positive authorization entries.
    pub positive_cache_entries: usize,
    /// Current credential keys with an active or waiting singleflight caller.
    pub active_flights: usize,
}''',
    "runtime diagnostic fields",
)
replace_once(
    '''    cache: Mutex<HashMap<[u8; 32], CacheEntry>>,
    flights: Mutex<HashMap<[u8; 32], Arc<Mutex<()>>>>,
    jwks: Mutex<JwksCache>,''',
    '''    cache: StdMutex<PositiveCache>,
    flights: Arc<StdMutex<HashMap<[u8; 32], FlightEntry>>>,
    jwks: Mutex<JwksCache>,''',
    "runtime bounded state fields",
)
replace_once(
    '''            cache: Mutex::new(HashMap::new()),
            flights: Mutex::new(HashMap::new()),
            jwks: Mutex::new(JwksCache::default()),''',
    '''            cache: StdMutex::new(PositiveCache::default()),
            flights: Arc::new(StdMutex::new(HashMap::new())),
            jwks: Mutex::new(JwksCache::default()),''',
    "runtime bounded state construction",
)

replace_once(
    '''        if let Some(principal) = self.cached(cache_key).await {
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
        let result = if let Some(principal) = self.cached(cache_key).await {''',
    '''        if let Some(principal) = self.cached(cache_key) {
            self.metrics.cache_hits.fetch_add(1, Ordering::Relaxed);
            require_scopes(&principal, &self.config.required_scopes, required_scopes)?;
            return Ok(principal);
        }
        self.metrics.cache_misses.fetch_add(1, Ordering::Relaxed);

        let flight = FlightLease::acquire(&self.flights, cache_key);
        let gate = Arc::clone(&flight.gate);
        let guard = gate.lock().await;
        let result = if let Some(principal) = self.cached(cache_key) {''',
    "cancellation-safe authorization entry",
)
replace_once(
    '''                    self.store(cache_key, principal.clone()).await;
                    require_scopes(&principal, &self.config.required_scopes, required_scopes)
                        .map(|()| principal)''',
    '''                    self.store(cache_key, principal.clone());
                    require_scopes(&principal, &self.config.required_scopes, required_scopes)
                        .map(|()| principal)''',
    "synchronous bounded cache store",
)
replace_once(
    '''        drop(guard);
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
    }''',
    '''        drop(guard);
        drop(flight);
        result
    }

    /// Return a privacy-safe snapshot of authorization counters and bounds.
    pub fn metrics(&self) -> MetricsSnapshot {
        let positive_cache_entries = lock_recover(&self.cache).len();
        let active_flights = lock_recover(&self.flights).len();
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
        }
    }''',
    "bounded runtime diagnostics",
)

replace_regex(
    r'''    async fn cached\(&self, key: \[u8; 32\]\) -> Option<Principal> \{.*?\n    async fn remove_flight\(&self, key: \[u8; 32\], flight: &Arc<Mutex<\(\)>>\) \{.*?\n    \}\n\}\n''',
    '''    fn cached(&self, key: [u8; 32]) -> Option<Principal> {
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
            self.metrics
                .cache_evictions
                .fetch_add(1, Ordering::Relaxed);
        }
    }
}
''',
    "bounded cache methods",
)

replace_once(
    '''fn require_scopes(
''',
    '''fn lock_recover<T>(mutex: &StdMutex<T>) -> std::sync::MutexGuard<'_, T> {
    match mutex.lock() {
        Ok(guard) => guard,
        Err(poisoned) => poisoned.into_inner(),
    }
}

fn require_scopes(
''',
    "poison-resilient short critical sections",
)

LIB.write_text(text, encoding="utf-8")

hybrid = TEST.read_text(encoding="utf-8")
marker = '''#[test]
fn configuration_rejects_insecure_or_unbounded_authority() {'''
if hybrid.count(marker) != 1:
    raise SystemExit("hybrid test insertion marker changed")
new_tests = r'''#[tokio::test]
async fn cancelled_authorization_releases_singleflight_state() {
    let transport = FakeTransport::new().with_delay(Duration::from_secs(30));
    let token = "tp_key_cancelled.secret";
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
                "api_key_id": "key_cancelled",
                "org_id": "org_test",
                "project_id": "proj_test",
                "environment_id": "env_test",
                "scope": "document:read"
            }),
        )
        .await;
    let authorizer =
        Arc::new(HybridAuthorizer::with_transport(config(), transport.clone()).unwrap());
    let task_authorizer = Arc::clone(&authorizer);
    let task = tokio::spawn(async move {
        task_authorizer.authorize(token, &["document:read"]).await
    });
    for _ in 0..100 {
        if transport.introspection_calls.load(Ordering::Relaxed) == 1 {
            break;
        }
        tokio::task::yield_now().await;
    }
    assert_eq!(transport.introspection_calls.load(Ordering::Relaxed), 1);
    task.abort();
    let _ = task.await;
    tokio::task::yield_now().await;
    assert_eq!(authorizer.metrics().active_flights, 0);
}

#[tokio::test]
async fn positive_cache_evicts_at_a_strict_bound() {
    let transport = FakeTransport::new();
    let mut bounded = config();
    bounded.max_cache_entries = 2;
    let authorizer = HybridAuthorizer::with_transport(bounded, transport.clone()).unwrap();
    for suffix in ["a", "b", "c"] {
        let token = format!("tp_key_{suffix}.secret");
        transport
            .insert(
                token.clone(),
                json!({
                    "active": true,
                    "iss": "http://127.0.0.1:8080",
                    "aud": "tempera-document",
                    "sub": "usr_service",
                    "client_id": "raw-api",
                    "token_type": "api_key",
                    "api_key_id": format!("key_{suffix}"),
                    "org_id": "org_test",
                    "project_id": "proj_test",
                    "environment_id": "env_test",
                    "scope": "document:read"
                }),
            )
            .await;
        authorizer
            .authorize(&token, &["document:read"])
            .await
            .unwrap();
    }
    let metrics = authorizer.metrics();
    assert_eq!(metrics.positive_cache_entries, 2);
    assert_eq!(metrics.cache_evictions, 1);

    authorizer
        .authorize("tp_key_a.secret", &["document:read"])
        .await
        .unwrap();
    assert_eq!(transport.introspection_calls.load(Ordering::Relaxed), 4);
}

'''
hybrid = hybrid.replace(marker, new_tests + marker, 1)
TEST.write_text(hybrid, encoding="utf-8")

readme = README.read_text(encoding="utf-8")
old = "Concurrent misses for the same token are singleflighted. Cache and flight keys are SHA-256 digests; raw bearer values are never retained as map keys, metrics labels, or log fields."
new = "Concurrent misses for the same token are singleflighted through cancellation-safe leases. Positive-cache lookup is O(1), expiry and capacity eviction are O(log n), and cache/flight keys are SHA-256 digests; raw bearer values are never retained as map keys, metrics labels, or log fields."
if readme.count(old) != 1:
    raise SystemExit("README cache paragraph changed")
readme = readme.replace(old, new, 1)
old = "The package exposes counters for cache hits/misses, local JWT rejection, introspection, authority failure, and claim mismatch. These counters contain no credential or tenant identifiers."
new = "The package exposes privacy-safe counters and bounded-state gauges for cache hits/misses/evictions, local JWT rejection, introspection, authority failure, claim mismatch, positive-cache entries, and active singleflight keys. They contain no credential or tenant identifiers."
if readme.count(old) != 1:
    raise SystemExit("README metrics paragraph changed")
README.write_text(readme.replace(old, new, 1), encoding="utf-8")

print("hybrid auth cache and singleflight optimization applied")
