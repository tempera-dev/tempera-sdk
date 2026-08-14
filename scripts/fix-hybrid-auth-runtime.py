#!/usr/bin/env python3
"""Apply strict Clippy fixes and make singleflight cleanup unconditional."""

from pathlib import Path

path = Path("packages/auth-rust/src/lib.rs")
text = path.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one source block, found {count}")
    text = text.replace(old, new, 1)


replace_once(
    "const DEFAULT_JWKS_CACHE_TTL: Duration = Duration::from_secs(300);",
    "const DEFAULT_JWKS_CACHE_TTL: Duration = Duration::from_mins(5);",
    "readable JWKS TTL",
)
replace_once(
    "self.jwks_cache_ttl > Duration::from_secs(86_400)",
    "self.jwks_cache_ttl > Duration::from_hours(24)",
    "readable maximum JWKS TTL",
)
replace_once(
    ".map_err(jwt_decode_failure)?",
    ".map_err(|error| jwt_decode_failure(&error))?",
    "borrowed JWT decode error",
)
replace_once(
    "fn jwt_decode_failure(error: jsonwebtoken::errors::Error) -> AuthError {",
    "fn jwt_decode_failure(error: &jsonwebtoken::errors::Error) -> AuthError {",
    "borrowed JWT decode helper",
)

old_authorize = '''        let guard = flight.lock().await;
        if let Some(principal) = self.cached(cache_key).await {
            self.metrics.cache_hits.fetch_add(1, Ordering::Relaxed);
            require_scopes(&principal, &self.config.required_scopes, required_scopes)?;
            drop(guard);
            self.remove_flight(cache_key, &flight).await;
            return Ok(principal);
        }

        let result = self.authorize_uncached(token).await;
        if let Ok(principal) = &result {
            require_scopes(principal, &self.config.required_scopes, required_scopes)?;
            self.store(cache_key, principal.clone()).await;
        }
        drop(guard);
        self.remove_flight(cache_key, &flight).await;
        result
'''
new_authorize = '''        let guard = flight.lock().await;
        let result = if let Some(principal) = self.cached(cache_key).await {
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
                    self.store(cache_key, principal.clone()).await;
                    require_scopes(&principal, &self.config.required_scopes, required_scopes)
                        .map(|()| principal)
                }
                Err(error) => Err(error),
            }
        };
        drop(guard);
        self.remove_flight(cache_key, &flight).await;
        result
'''
replace_once(old_authorize, new_authorize, "unconditional singleflight cleanup")

path.write_text(text)
print("hybrid auth runtime strict fixes applied")
