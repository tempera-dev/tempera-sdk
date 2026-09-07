/**
 * Retry rules for the unified Tempera client, shared in shape with the Python
 * and Rust packages.
 *
 * The rules are deliberately narrow, because a retry that is not provably safe
 * duplicates a side effect:
 *
 * - Only an operation whose generated `safeRetry` classification is `"read"`
 *   (GET) or `"idempotent"` (its request body carries a client-minted
 *   idempotency key) is ever retried. `"none"` is sent exactly once.
 * - Only 408, 429, 500, 502, 503, 504 and connection failures are retried.
 *   Every other 4xx is a caller error and is surfaced immediately.
 * - At most 3 attempts, with exponential backoff starting at 250 ms.
 * - Every attempt resends the identical body, including the identical
 *   idempotency key. A key is never minted, regenerated, or rewritten on
 *   retry: the caller's bytes are the idempotency identity.
 */

import { TemperaSdkError, TemperaApiError } from "./errors.js";

/** Maximum wire length of an idempotency key, in bytes. */
export const MAX_IDEMPOTENCY_KEY_BYTES = 256;

/** Request-body field names that carry a client-minted idempotency key. */
export const IDEMPOTENCY_KEY_FIELDS = Object.freeze([
  "idempotencyKey",
  "idempotency_key",
]);

/** HTTP statuses a safe operation may be retried on. */
export const RETRYABLE_STATUSES = Object.freeze([408, 429, 500, 502, 503, 504]);

/** Total attempts, including the first one. */
export const MAX_ATTEMPTS = 3;

/** Backoff before the second attempt, in milliseconds; doubled thereafter. */
export const INITIAL_BACKOFF_MS = 250;

/**
 * Return the exact key when it is safe for an HTTP header.
 *
 * Canonical rule, copied from tempera-mcp `src/idempotency.rs`: non-empty, at
 * most 256 bytes, every byte ASCII-graphic. No trimming, Unicode
 * normalization, or case folding is performed.
 */
export function canonicalIdempotencyKey(value) {
  if (typeof value !== "string" || value.length === 0) return null;
  const bytes = new TextEncoder().encode(value);
  if (bytes.length > MAX_IDEMPOTENCY_KEY_BYTES) return null;
  for (const byte of bytes) {
    if (byte < 0x21 || byte > 0x7e) return null;
  }
  return value;
}

/**
 * Reject a malformed idempotency key before the first attempt, so a retry can
 * never be forced to choose between an unusable key and a fresh one.
 */
export function assertCanonicalIdempotencyKeys(label, body) {
  if (body === null || typeof body !== "object" || ArrayBuffer.isView(body)) return;
  for (const field of IDEMPOTENCY_KEY_FIELDS) {
    if (!Object.hasOwn(body, field)) continue;
    if (canonicalIdempotencyKey(body[field]) === null) {
      throw new TemperaSdkError(
        `${label}: ${field} must be 1-${MAX_IDEMPOTENCY_KEY_BYTES} ASCII-graphic bytes`,
      );
    }
  }
}

/** Backoff before attempt `attempt` (1-based); attempt 1 never waits. */
export function retryDelayMs(attempt) {
  return INITIAL_BACKOFF_MS * 2 ** (attempt - 2);
}

/** Whether this failure is transient for an operation that is safe to retry. */
export function isRetryableFailure(error) {
  if (error instanceof TemperaApiError) {
    return RETRYABLE_STATUSES.includes(error.status);
  }
  // A non-API error escaping the transport is a connection failure: the
  // request never produced an HTTP response.
  return !(error instanceof TemperaSdkError);
}

const defaultSleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Send one already-built request, retrying only when the operation's
 * `safeRetry` classification allows it.
 *
 * `send` receives the 1-based attempt number and must resend the identical
 * request every time; this helper never rebuilds a body or a key.
 */
export async function sendWithRetry(safeRetry, send, { sleep = defaultSleep } = {}) {
  const attempts = safeRetry === "none" ? 1 : MAX_ATTEMPTS;
  for (let attempt = 1; ; attempt += 1) {
    try {
      return await send(attempt);
    } catch (error) {
      if (attempt >= attempts || !isRetryableFailure(error)) throw error;
      await sleep(retryDelayMs(attempt + 1));
    }
  }
}
