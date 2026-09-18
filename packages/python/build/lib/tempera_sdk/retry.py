"""Retry rules for the unified Tempera client, shared in shape with the
TypeScript and Rust packages.

The rules are deliberately narrow, because a retry that is not provably safe
duplicates a side effect:

- Only an operation whose generated ``safe_retry`` classification is ``"read"``
  (GET) or ``"idempotent"`` (its request body carries a client-minted
  idempotency key) is ever retried. ``"none"`` is sent exactly once.
- Only 408, 429, 500, 502, 503, 504 and connection failures are retried. Every
  other 4xx is a caller error and is surfaced immediately.
- At most 3 attempts, with exponential backoff starting at 250 ms.
- Every attempt resends the identical body, including the identical idempotency
  key. A key is never minted, regenerated, or rewritten on retry: the caller's
  bytes are the idempotency identity.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Mapping

from .errors import TemperaApiError, TemperaSdkError

#: Maximum wire length of an idempotency key, in bytes.
MAX_IDEMPOTENCY_KEY_BYTES = 256

#: Request-body field names that carry a client-minted idempotency key.
IDEMPOTENCY_KEY_FIELDS = ("idempotencyKey", "idempotency_key")

#: HTTP statuses a safe operation may be retried on.
RETRYABLE_STATUSES = frozenset({408, 429, 500, 502, 503, 504})

#: Total attempts, including the first one.
MAX_ATTEMPTS = 3

#: Backoff before the second attempt, in seconds; doubled thereafter.
INITIAL_BACKOFF_SECONDS = 0.25


def canonical_idempotency_key(value: Any) -> str | None:
    """Return the exact key when it is safe for an HTTP header.

    Canonical rule, copied from tempera-mcp ``src/idempotency.rs``: non-empty,
    at most 256 bytes, every byte ASCII-graphic. No trimming, Unicode
    normalization, or case folding is performed.
    """
    if not isinstance(value, str) or not value:
        return None
    encoded = value.encode("utf-8")
    if len(encoded) > MAX_IDEMPOTENCY_KEY_BYTES:
        return None
    if not all(0x21 <= byte <= 0x7E for byte in encoded):
        return None
    return value


def assert_canonical_idempotency_keys(label: str, body: Any) -> None:
    """Reject a malformed idempotency key before the first attempt, so a retry
    can never be forced to choose between an unusable key and a fresh one."""
    if not isinstance(body, Mapping):
        return
    for field in IDEMPOTENCY_KEY_FIELDS:
        if field not in body:
            continue
        if canonical_idempotency_key(body[field]) is None:
            raise TemperaSdkError(
                f"{label}: {field} must be 1-{MAX_IDEMPOTENCY_KEY_BYTES} "
                "ASCII-graphic bytes"
            )


def retry_delay_seconds(attempt: int) -> float:
    """Backoff before ``attempt`` (1-based); attempt 1 never waits."""
    return INITIAL_BACKOFF_SECONDS * (2 ** (attempt - 2))


def is_retryable_failure(error: BaseException) -> bool:
    """Whether this failure is transient for an operation that is safe to retry."""
    if isinstance(error, TemperaApiError):
        return error.status in RETRYABLE_STATUSES
    if isinstance(error, TemperaSdkError):
        return False
    # A transport-level OSError (urllib raises URLError, a subclass) means the
    # request never produced an HTTP response.
    return isinstance(error, OSError)


def send_with_retry(
    safe_retry: str,
    send: Callable[[int], Any],
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    """Send one already-built request, retrying only when the operation's
    ``safe_retry`` classification allows it.

    ``send`` receives the 1-based attempt number and must resend the identical
    request every time; this helper never rebuilds a body or a key.
    """
    attempts = 1 if safe_retry == "none" else MAX_ATTEMPTS
    attempt = 1
    while True:
        try:
            return send(attempt)
        except BaseException as error:  # noqa: BLE001 - re-raised below
            if attempt >= attempts or not is_retryable_failure(error):
                raise
            sleep(retry_delay_seconds(attempt + 1))
            attempt += 1


__all__ = [
    "IDEMPOTENCY_KEY_FIELDS",
    "INITIAL_BACKOFF_SECONDS",
    "MAX_ATTEMPTS",
    "MAX_IDEMPOTENCY_KEY_BYTES",
    "RETRYABLE_STATUSES",
    "assert_canonical_idempotency_keys",
    "canonical_idempotency_key",
    "is_retryable_failure",
    "retry_delay_seconds",
    "send_with_retry",
]
