// Timeout and retry rules for the unified Tempera client.
//
// The retry rules are deliberately narrow, because a retry that is not
// provably safe duplicates a side effect:
//
// - Only an operation whose generated `safeRetry` classification is `read`
//   (a GET) or `idempotent` (its request body carries a client-minted
//   idempotency key) is ever retried. `none` is sent exactly once. A
//   passthrough request has no classification, so it is derived from the HTTP
//   method: the RFC 9110 idempotent methods are retried, POST and PATCH are
//   not.
// - Only 408, 429, 500, 502, 503, 504 and connection failures are retried.
//   Every other 4xx is a caller error and is surfaced immediately. (The
//   TypeScript, Python, and Rust packages use this same set; it is a superset
//   of the 429/502/503/504 minimum.)
// - Every attempt resends the identical body, including the identical
//   idempotency key. A key is never minted, regenerated, or rewritten on
//   retry: the caller's bytes are the idempotency identity.
//
// What this package adds over the older three: a per-request timeout, jitter
// on the backoff so a fleet of clients does not retry in lockstep, and
// `Retry-After` when the server names a delay.

package dev.tempera.sdk

import java.time.DateTimeException
import java.time.Duration
import java.time.Instant
import java.time.format.DateTimeFormatter

/** Client-wide knobs: how long one attempt may take, and how attempts repeat. */
public data class TemperaClientConfiguration(
    /** How long one attempt may take before it is abandoned, in seconds. */
    public val timeoutSeconds: Double = DEFAULT_TIMEOUT_SECONDS,
    /** How failed attempts repeat. */
    public val retry: TemperaRetryPolicy = TemperaRetryPolicy(),
) {
    public companion object {
        /** Default per-request timeout, in seconds. */
        public const val DEFAULT_TIMEOUT_SECONDS: Double = 30.0
    }
}

/** The bounded retry policy. */
public data class TemperaRetryPolicy(
    /** Total attempts, including the first one. */
    public val maxAttempts: Int = 3,
    /** Backoff before the second attempt, in seconds; doubled thereafter. */
    public val initialBackoffSeconds: Double = 0.25,
    /** Ceiling for the exponential backoff, in seconds. */
    public val maxBackoffSeconds: Double = 8.0,
    /**
     * Fraction of the backoff that is randomized, in `0..1`. At the default
     * `0.5`, a delay lands uniformly in `[0.5 * base, base]`.
     */
    public val jitter: Double = 0.5,
    /** HTTP statuses a safe operation may be retried on. */
    public val retryableStatuses: Set<Int> = setOf(408, 429, 500, 502, 503, 504),
    /** Whether a `Retry-After` response header overrides the backoff. */
    public val respectsRetryAfter: Boolean = true,
    /** Ceiling for a server-named `Retry-After` delay, in seconds. */
    public val maxRetryAfterSeconds: Double = 30.0,
) {
    /** Total attempts admitted for one `safeRetry` classification. */
    public fun attemptBudget(safeRetry: String): Int =
        if (safeRetry == "none") 1 else maxOf(1, maxAttempts)

    /** Whether an HTTP status may be retried at all. */
    public fun isRetryable(status: Int): Boolean = retryableStatuses.contains(status)

    /**
     * Backoff before [attempt] (1-based; attempt 1 never waits).
     *
     * [retryAfterSeconds] is the server's own delay, which wins over the
     * backoff and is used without jitter -- the server named a time, not a
     * range. [random] is a value in `0..<1`, injected so tests observe an exact
     * delay.
     */
    public fun delaySeconds(
        attempt: Int,
        retryAfterSeconds: Double? = null,
        random: Double = 0.5,
    ): Double {
        if (respectsRetryAfter && retryAfterSeconds != null && retryAfterSeconds >= 0) {
            return minOf(retryAfterSeconds, maxRetryAfterSeconds)
        }
        val exponent = maxOf(0, attempt - 2)
        val base = minOf(initialBackoffSeconds * Math.pow(2.0, exponent.toDouble()), maxBackoffSeconds)
        val bounded = minOf(maxOf(random, 0.0), 1.0)
        val spread = minOf(maxOf(jitter, 0.0), 1.0)
        return base * (1.0 - spread + spread * bounded)
    }

    public companion object {
        /** A policy that sends every request exactly once. */
        public val NONE: TemperaRetryPolicy = TemperaRetryPolicy(maxAttempts = 1)

        /** HTTP methods RFC 9110 defines as idempotent. */
        public val IDEMPOTENT_METHODS: Set<String> =
            setOf("GET", "HEAD", "OPTIONS", "TRACE", "PUT", "DELETE")

        /**
         * The `safeRetry` classification to use for a request with no generated
         * operation behind it (a passthrough call, or an auth or MCP request).
         */
        public fun safeRetryForMethod(method: String): String =
            if (IDEMPOTENT_METHODS.contains(method.uppercase())) "read" else "none"

        /**
         * Parse a `Retry-After` header: delta-seconds, or an HTTP-date relative
         * to [now]. Returns `null` for anything else.
         */
        public fun parseRetryAfter(value: String, now: Instant = Instant.now()): Double? {
            val trimmed = value.trim()
            val seconds = trimmed.toDoubleOrNull()
            if (seconds != null) {
                return if (seconds >= 0) seconds else null
            }
            return try {
                val date = Instant.from(DateTimeFormatter.RFC_1123_DATE_TIME.parse(trimmed))
                maxOf(0.0, Duration.between(now, date).toMillis() / 1000.0)
            } catch (error: DateTimeException) {
                null
            }
        }
    }
}

/** Maximum wire length of an idempotency key, in bytes. */
public const val TEMPERA_MAX_IDEMPOTENCY_KEY_BYTES: Int = 256

/** Request-body field names that carry a client-minted idempotency key. */
public val TEMPERA_IDEMPOTENCY_KEY_FIELDS: List<String> =
    listOf("idempotencyKey", "idempotency_key")

/**
 * Return the exact key when it is safe for an HTTP header.
 *
 * Canonical rule, copied from tempera-mcp `src/idempotency.rs`: non-empty, at
 * most 256 bytes, every byte ASCII-graphic. No trimming, Unicode
 * normalization, or case folding is performed.
 */
public fun temperaCanonicalIdempotencyKey(value: String): String? {
    val bytes = value.toByteArray(Charsets.UTF_8)
    if (bytes.isEmpty() || bytes.size > TEMPERA_MAX_IDEMPOTENCY_KEY_BYTES) return null
    for (byte in bytes) {
        val code = byte.toInt() and 0xFF
        if (code < 0x21 || code > 0x7E) return null
    }
    return value
}

/**
 * Reject a malformed idempotency key before the first attempt, so a retry can
 * never be forced to choose between an unusable key and a fresh one.
 */
public fun temperaAssertCanonicalIdempotencyKeys(
    label: String,
    members: List<TemperaJsonMember>,
) {
    for (field in TEMPERA_IDEMPOTENCY_KEY_FIELDS) {
        val value = members.firstOrNull { it.key == field }?.value ?: continue
        val text = value.asString()
        if (text == null || temperaCanonicalIdempotencyKey(text) == null) {
            throw TemperaSdkException(
                label +
                    ": " +
                    field +
                    " must be 1-" +
                    TEMPERA_MAX_IDEMPOTENCY_KEY_BYTES +
                    " ASCII-graphic bytes"
            )
        }
    }
}
