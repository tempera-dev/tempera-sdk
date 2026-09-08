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

import Foundation

/// Client-wide knobs: how long one attempt may take, and how attempts repeat.
public struct TemperaClientConfiguration: Sendable, Equatable {
    /// Default per-request timeout, in seconds.
    public static let defaultTimeout: TimeInterval = 30

    /// How long one attempt may take before it is abandoned.
    public var timeout: TimeInterval
    /// How failed attempts repeat.
    public var retry: TemperaRetryPolicy

    /// Create a configuration. The defaults are a 30-second timeout and at
    /// most 3 attempts with jittered exponential backoff from 250 ms.
    public init(
        timeout: TimeInterval = TemperaClientConfiguration.defaultTimeout,
        retry: TemperaRetryPolicy = TemperaRetryPolicy()
    ) {
        self.timeout = timeout
        self.retry = retry
    }
}

/// The bounded retry policy.
public struct TemperaRetryPolicy: Sendable, Equatable {
    /// Total attempts, including the first one.
    public var maxAttempts: Int
    /// Backoff before the second attempt; doubled thereafter.
    public var initialBackoff: TimeInterval
    /// Ceiling for the exponential backoff.
    public var maxBackoff: TimeInterval
    /// Fraction of the backoff that is randomized, in `0...1`. At the default
    /// `0.5`, a delay lands uniformly in `[0.5 * base, base]`.
    public var jitter: Double
    /// HTTP statuses a safe operation may be retried on.
    public var retryableStatuses: Set<Int>
    /// Whether a `Retry-After` response header overrides the backoff.
    public var respectsRetryAfter: Bool
    /// Ceiling for a server-named `Retry-After` delay.
    public var maxRetryAfter: TimeInterval

    /// Create a policy; every default matches the documented rules above.
    public init(
        maxAttempts: Int = 3,
        initialBackoff: TimeInterval = 0.25,
        maxBackoff: TimeInterval = 8,
        jitter: Double = 0.5,
        retryableStatuses: Set<Int> = [408, 429, 500, 502, 503, 504],
        respectsRetryAfter: Bool = true,
        maxRetryAfter: TimeInterval = 30
    ) {
        self.maxAttempts = max(1, maxAttempts)
        self.initialBackoff = initialBackoff
        self.maxBackoff = maxBackoff
        self.jitter = min(max(jitter, 0), 1)
        self.retryableStatuses = retryableStatuses
        self.respectsRetryAfter = respectsRetryAfter
        self.maxRetryAfter = maxRetryAfter
    }

    /// A policy that sends every request exactly once.
    public static let none = TemperaRetryPolicy(maxAttempts: 1)

    /// HTTP methods RFC 9110 defines as idempotent.
    public static let idempotentMethods: Set<String> = [
        "GET", "HEAD", "OPTIONS", "TRACE", "PUT", "DELETE",
    ]

    /// The `safeRetry` classification to use for a request with no generated
    /// operation behind it (a passthrough call, or an auth or MCP request).
    public static func safeRetry(forMethod method: String) -> String {
        idempotentMethods.contains(method.uppercased()) ? "read" : "none"
    }

    /// Total attempts admitted for one `safeRetry` classification.
    public func attemptBudget(safeRetry: String) -> Int {
        safeRetry == "none" ? 1 : maxAttempts
    }

    /// Whether an HTTP status may be retried at all.
    public func isRetryable(status: Int) -> Bool {
        retryableStatuses.contains(status)
    }

    /// Backoff before `attempt` (1-based; attempt 1 never waits).
    ///
    /// `retryAfter` is the server's own delay, which wins over the backoff and
    /// is used without jitter -- the server named a time, not a range.
    /// `random` is a value in `0..<1`, injected so tests observe an exact delay.
    public func delay(
        beforeAttempt attempt: Int,
        retryAfter: TimeInterval? = nil,
        random: Double = 0.5
    ) -> TimeInterval {
        if respectsRetryAfter, let retryAfter, retryAfter >= 0 {
            return min(retryAfter, maxRetryAfter)
        }
        let exponent = max(0, attempt - 2)
        let base = min(initialBackoff * pow(2, Double(exponent)), maxBackoff)
        return base * (1 - jitter + jitter * min(max(random, 0), 1))
    }

    /// Parse a `Retry-After` header: delta-seconds, or an HTTP-date relative to
    /// `now`. Returns `nil` for anything else.
    public static func parseRetryAfter(_ value: String, now: Date = Date()) -> TimeInterval? {
        let trimmed = value.trimmingCharacters(in: .whitespaces)
        if let seconds = Double(trimmed) {
            return seconds >= 0 ? seconds : nil
        }
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(identifier: "GMT")
        for format in ["EEE, dd MMM yyyy HH:mm:ss zzz", "EEEE, dd-MMM-yy HH:mm:ss zzz"] {
            formatter.dateFormat = format
            if let date = formatter.date(from: trimmed) {
                return max(0, date.timeIntervalSince(now))
            }
        }
        return nil
    }
}

/// Maximum wire length of an idempotency key, in bytes.
public let temperaMaxIdempotencyKeyBytes = 256

/// Request-body field names that carry a client-minted idempotency key.
public let temperaIdempotencyKeyFields = ["idempotencyKey", "idempotency_key"]

/// Return the exact key when it is safe for an HTTP header.
///
/// Canonical rule, copied from tempera-mcp `src/idempotency.rs`: non-empty, at
/// most 256 bytes, every byte ASCII-graphic. No trimming, Unicode
/// normalization, or case folding is performed.
public func temperaCanonicalIdempotencyKey(_ value: String) -> String? {
    let bytes = Array(value.utf8)
    guard !bytes.isEmpty, bytes.count <= temperaMaxIdempotencyKeyBytes else { return nil }
    guard bytes.allSatisfy({ $0 >= 0x21 && $0 <= 0x7E }) else { return nil }
    return value
}

/// Reject a malformed idempotency key before the first attempt, so a retry can
/// never be forced to choose between an unusable key and a fresh one.
public func temperaAssertCanonicalIdempotencyKeys(
    _ label: String,
    _ members: [TemperaJSONMember]
) throws {
    for field in temperaIdempotencyKeyFields {
        guard let value = members.first(where: { $0.key == field })?.value else { continue }
        guard let text = value.stringValue, temperaCanonicalIdempotencyKey(text) != nil else {
            throw TemperaSdkError(
                "\(label): \(field) must be 1-\(temperaMaxIdempotencyKeyBytes) ASCII-graphic bytes"
            )
        }
    }
}
