#!/usr/bin/env python3
"""Finalize JWKS concurrency semantics after the bounded admission transform."""

from __future__ import annotations

import re
from pathlib import Path

LIB = Path("packages/auth-rust/src/lib.rs")
HYBRID = Path("packages/auth-rust/tests/hybrid.rs")

text = LIB.read_text(encoding="utf-8")

old_cache = '''struct JwksCache {
    keys: HashMap<String, CachedJwk>,
    expires_at: Option<Instant>,
    last_refresh_attempt: Option<Instant>,
}'''
new_cache = '''struct JwksCache {
    keys: HashMap<String, CachedJwk>,
    expires_at: Option<Instant>,
    last_refresh_attempt: Option<Instant>,
    generation: u64,
}'''
if text.count(old_cache) != 1:
    raise SystemExit(f"JwksCache shape changed: {text.count(old_cache)}")
text = text.replace(old_cache, new_cache, 1)

pattern = r'''    async fn jwks_key\(&self, kid: &str\) -> Result<DecodingKey, AuthError> \{.*?\n    \}\n\n    fn principal_from_claims'''
replacement = '''    async fn jwks_key(&self, kid: &str) -> Result<DecodingKey, AuthError> {
        // Fast path: a known key in a fresh published snapshot never waits for
        // refresh coordination or network I/O.
        let observed_generation = {
            let cache = self.jwks.lock().await;
            if cache.expires_at.is_some_and(|expiry| expiry > Instant::now())
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

            if let Some(key) = lookup_jwks_key(
                &cache,
                kid,
                now,
                self.config.jwks_refresh_cooldown,
            )? {
                return Ok(key);
            }
        }

        self.metrics
            .jwks_refreshes
            .fetch_add(1, Ordering::Relaxed);
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

    fn principal_from_claims'''
text, count = re.subn(pattern, lambda _: replacement, text, count=1, flags=re.S)
if count != 1:
    raise SystemExit(f"jwks_key shape changed: {count}")
LIB.write_text(text, encoding="utf-8")

hybrid = HYBRID.read_text(encoding="utf-8")

unknown_pattern = re.compile(
    r'''(async fn concurrent_unknown_key_refreshes_are_singleflighted\(\) \{\n'''
    r'''    let transport = FakeTransport::new\(\)\.with_jwks_delay\(Duration::from_millis\(100\)\);\n)'''
    r'''    let authorizer =\n        Arc::new\(HybridAuthorizer::with_transport\(config\(\), transport\.clone\(\)\)\.unwrap\(\)\);'''
)
unknown_replacement = '''\\1    let mut bounded = config();
    bounded.jwks_refresh_cooldown = Duration::from_secs(2);
    let authorizer = Arc::new(
        HybridAuthorizer::with_transport(bounded, transport.clone()).unwrap(),
    );'''
hybrid, count = unknown_pattern.subn(unknown_replacement, hybrid, count=1)
if count != 1:
    raise SystemExit(f"unknown-kid concurrency test shape changed: {count}")

progress_pattern = re.compile(
    r'''(async fn jwks_refresh_does_not_block_a_fresh_cached_key\(\) \{.*?'''
    r'''    authorizer\n        \.authorize\(&initial_token, &\["document:read"\]\)\n'''
    r'''        \.await\n        \.unwrap\(\);\n)(\n    let mut unknown_claims = access_claims\(\);)''',
    re.S,
)
progress_replacement = '''\\1
    // The initial successful fetch starts the negative-refresh cooldown.
    // Cross that boundary before starting a deliberately slow unknown-kid
    // refresh so this test measures read progress during real network I/O.
    tokio::time::sleep(Duration::from_millis(50)).await;
\\2'''
hybrid, count = progress_pattern.subn(progress_replacement, hybrid, count=1)
if count != 1:
    raise SystemExit(f"JWKS progress test shape changed: {count}")

HYBRID.write_text(hybrid, encoding="utf-8")
print("finalized authority admission JWKS semantics")
