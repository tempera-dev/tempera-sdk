//! Retry rules for the unified Tempera client, shared in shape with the
//! TypeScript and Python packages.
//!
//! The rules are deliberately narrow, because a retry that is not provably
//! safe duplicates a side effect:
//!
//! - Only an operation whose generated [`surface::OperationSpec::safe_retry`]
//!   classification is `"read"` (GET) or `"idempotent"` (its request body
//!   carries a client-minted idempotency key) is ever retried. `"none"` is
//!   sent exactly once.
//! - Only 408, 429, 500, 502, 503, 504 and connection failures are retried.
//!   Every other 4xx is a caller error and is surfaced immediately.
//! - At most 3 attempts, with exponential backoff starting at 250 ms.
//! - Every attempt resends the identical [`RequestSpec`], including the
//!   identical idempotency key. A key is never minted, regenerated, or
//!   rewritten on retry: the caller's bytes are the idempotency identity.
//!
//! The crate is HTTP-less, so [`send_with_retry`] drives a caller-supplied
//! sender over one already-built request rather than owning a socket.

use std::time::Duration;

use crate::client::RequestSpec;
use crate::error::TemperaApiError;

/// Maximum wire length of an idempotency key, in bytes.
pub const MAX_IDEMPOTENCY_KEY_BYTES: usize = 256;

/// Request-body field names that carry a client-minted idempotency key.
pub const IDEMPOTENCY_KEY_FIELDS: &[&str] = &["idempotencyKey", "idempotency_key"];

/// HTTP statuses a safe operation may be retried on.
pub const RETRYABLE_STATUSES: &[u16] = &[408, 429, 500, 502, 503, 504];

/// Total attempts, including the first one.
pub const MAX_ATTEMPTS: u32 = 3;

/// Backoff before the second attempt, in milliseconds; doubled thereafter.
pub const INITIAL_BACKOFF_MS: u64 = 250;

/// Return the exact key when it is safe for an HTTP header.
///
/// Canonical rule, copied from tempera-mcp `src/idempotency.rs`: non-empty, at
/// most 256 bytes, every byte ASCII-graphic. No trimming, Unicode
/// normalization, or case folding is performed.
pub fn canonical_idempotency_key(value: &str) -> Option<&str> {
    (!value.is_empty()
        && value.len() <= MAX_IDEMPOTENCY_KEY_BYTES
        && value.bytes().all(|byte| byte.is_ascii_graphic()))
    .then_some(value)
}

/// One failed send: either a real HTTP response or a connection failure.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SendError {
    /// The server answered with a non-success status.
    Api(TemperaApiError),
    /// The request never produced an HTTP response.
    Connection(String),
}

impl SendError {
    /// Whether this failure is transient for an operation that is safe to retry.
    pub fn is_retryable(&self) -> bool {
        match self {
            SendError::Api(error) => RETRYABLE_STATUSES.contains(&error.status),
            SendError::Connection(_) => true,
        }
    }
}

impl std::fmt::Display for SendError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SendError::Api(error) => write!(f, "{error}"),
            SendError::Connection(detail) => write!(f, "Tempera connection failed: {detail}"),
        }
    }
}

impl std::error::Error for SendError {}

/// Backoff before `attempt` (1-based); attempt 1 never waits.
pub fn retry_delay(attempt: u32) -> Duration {
    Duration::from_millis(INITIAL_BACKOFF_MS << (attempt.saturating_sub(2)))
}

/// Total attempts admitted for one `safe_retry` classification.
pub fn attempt_budget(safe_retry: &str) -> u32 {
    if safe_retry == "none" {
        1
    } else {
        MAX_ATTEMPTS
    }
}

/// Send one already-built request, retrying only when `safe_retry` allows it.
///
/// `send` receives the very same [`RequestSpec`] on every attempt, so the body
/// and its idempotency key are byte-identical by construction. `sleep` is
/// injected so a caller (or a test) controls how backoff is spent.
pub fn send_with_retry<S, W>(
    spec: &RequestSpec,
    safe_retry: &str,
    mut send: S,
    mut sleep: W,
) -> Result<String, SendError>
where
    S: FnMut(&RequestSpec, u32) -> Result<String, SendError>,
    W: FnMut(Duration),
{
    let budget = attempt_budget(safe_retry);
    let mut attempt = 1;
    loop {
        match send(spec, attempt) {
            Ok(body) => return Ok(body),
            Err(error) => {
                if attempt >= budget || !error.is_retryable() {
                    return Err(error);
                }
                sleep(retry_delay(attempt + 1));
                attempt += 1;
            }
        }
    }
}

/// [`send_with_retry`] that spends its backoff on the calling thread.
pub fn send_with_retry_blocking<S>(
    spec: &RequestSpec,
    safe_retry: &str,
    send: S,
) -> Result<String, SendError>
where
    S: FnMut(&RequestSpec, u32) -> Result<String, SendError>,
{
    send_with_retry(spec, safe_retry, send, std::thread::sleep)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn canonical_key_is_exact_ascii_graphic_bytes() {
        assert_eq!(
            canonical_idempotency_key("Request-1._~"),
            Some("Request-1._~")
        );
        for invalid in ["", "has space", "has\nnewline", "snowman-\u{2603}"] {
            assert!(canonical_idempotency_key(invalid).is_none());
        }
        assert!(canonical_idempotency_key(&"x".repeat(256)).is_some());
        assert!(canonical_idempotency_key(&"x".repeat(257)).is_none());
    }

    #[test]
    fn backoff_is_exponential_from_250_ms() {
        assert_eq!(retry_delay(2), Duration::from_millis(250));
        assert_eq!(retry_delay(3), Duration::from_millis(500));
    }

    #[test]
    fn only_the_documented_statuses_are_retryable() {
        for status in [408, 429, 500, 502, 503, 504] {
            assert!(
                SendError::Api(TemperaApiError {
                    status,
                    code: None,
                    message: String::new(),
                    reason: None,
                    request_id: None,
                })
                .is_retryable()
            );
        }
        for status in [400, 401, 403, 404, 409, 422, 501] {
            assert!(
                !SendError::Api(TemperaApiError {
                    status,
                    code: None,
                    message: String::new(),
                    reason: None,
                    request_id: None,
                })
                .is_retryable()
            );
        }
    }
}
