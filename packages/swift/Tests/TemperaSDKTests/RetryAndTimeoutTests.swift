import Foundation
import XCTest

@testable import TemperaSDK

/// Records the backoff a client spends, so retry timing is asserted without
/// waiting for it.
actor DelayRecorder {
    private(set) var delays: [TimeInterval] = []

    func record(_ delay: TimeInterval) {
        delays.append(delay)
    }

    /// A sleeper closure the client can be built with.
    nonisolated func makeSleeper() -> @Sendable (TimeInterval) async throws -> Void {
        { delay in await self.record(delay) }
    }
}

final class RetryAndTimeoutTests: XCTestCase {

    // MARK: - Policy arithmetic

    func testBackoffIsExponentialFromTwoHundredFiftyMilliseconds() {
        let policy = TemperaRetryPolicy()
        // random = 1 is the top of the jitter band, i.e. the undiluted backoff.
        XCTAssertEqual(policy.delay(beforeAttempt: 2, random: 1), 0.25, accuracy: 1e-9)
        XCTAssertEqual(policy.delay(beforeAttempt: 3, random: 1), 0.5, accuracy: 1e-9)
        XCTAssertEqual(policy.delay(beforeAttempt: 4, random: 1), 1.0, accuracy: 1e-9)
        // random = 0 is the bottom of the band: half the backoff at jitter 0.5.
        XCTAssertEqual(policy.delay(beforeAttempt: 2, random: 0), 0.125, accuracy: 1e-9)
        XCTAssertEqual(policy.delay(beforeAttempt: 3, random: 0.5), 0.375, accuracy: 1e-9)
        // The ceiling holds.
        XCTAssertEqual(policy.delay(beforeAttempt: 20, random: 1), policy.maxBackoff)
    }

    func testJitterAlwaysLandsInsideTheBand() {
        let policy = TemperaRetryPolicy()
        for _ in 0..<200 {
            let delay = policy.delay(beforeAttempt: 3, random: Double.random(in: 0..<1))
            XCTAssertGreaterThanOrEqual(delay, 0.25)
            XCTAssertLessThanOrEqual(delay, 0.5)
        }
    }

    func testRetryAfterOverridesTheBackoffAndIsClamped() {
        let policy = TemperaRetryPolicy()
        XCTAssertEqual(policy.delay(beforeAttempt: 2, retryAfter: 3, random: 1), 3)
        XCTAssertEqual(policy.delay(beforeAttempt: 2, retryAfter: 600, random: 1), 30)
        let ignoring = TemperaRetryPolicy(respectsRetryAfter: false)
        XCTAssertEqual(ignoring.delay(beforeAttempt: 2, retryAfter: 3, random: 1), 0.25)
    }

    func testParseRetryAfterAcceptsSecondsAndHttpDates() {
        XCTAssertEqual(TemperaRetryPolicy.parseRetryAfter("7"), 7)
        XCTAssertEqual(TemperaRetryPolicy.parseRetryAfter("  7 "), 7)
        XCTAssertNil(TemperaRetryPolicy.parseRetryAfter("-1"))
        XCTAssertNil(TemperaRetryPolicy.parseRetryAfter("soon"))

        let now = Date(timeIntervalSince1970: 1_760_000_000)
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(identifier: "GMT")
        formatter.dateFormat = "EEE, dd MMM yyyy HH:mm:ss zzz"
        let header = formatter.string(from: now.addingTimeInterval(12))
        XCTAssertEqual(TemperaRetryPolicy.parseRetryAfter(header, now: now) ?? 0, 12, accuracy: 1)
        // A date in the past is zero, never negative.
        let past = formatter.string(from: now.addingTimeInterval(-60))
        XCTAssertEqual(TemperaRetryPolicy.parseRetryAfter(past, now: now), 0)
    }

    func testOnlyIdempotentMethodsGetAnAttemptBudget() {
        let policy = TemperaRetryPolicy()
        XCTAssertEqual(policy.attemptBudget(safeRetry: "read"), 3)
        XCTAssertEqual(policy.attemptBudget(safeRetry: "idempotent"), 3)
        XCTAssertEqual(policy.attemptBudget(safeRetry: "none"), 1)
        for method in ["GET", "HEAD", "PUT", "DELETE", "OPTIONS"] {
            XCTAssertEqual(TemperaRetryPolicy.safeRetry(forMethod: method), "read", method)
        }
        for method in ["POST", "PATCH", "post"] {
            XCTAssertEqual(TemperaRetryPolicy.safeRetry(forMethod: method), "none", method)
        }
    }

    // MARK: - Retrying real dispatches

    private func failing(_ status: Int, times: Int, retryAfter: String? = nil) -> StubTransport {
        StubTransport(responder: { _, attempt in
            if attempt <= times {
                var headers = [TemperaKeyValue(key: "content-type", value: "application/json")]
                if let retryAfter {
                    headers.append(TemperaKeyValue(key: "retry-after", value: retryAfter))
                }
                return TemperaHTTPResponse(
                    status: status,
                    headers: headers,
                    body: Data(#"{"error":{"status":"UNAVAILABLE","message":"try later"}}"#.utf8)
                )
            }
            return TemperaHTTPResponse(
                status: 200,
                headers: [TemperaKeyValue(key: "content-type", value: "application/json")],
                body: Data(#"{"ok":true}"#.utf8)
            )
        })
    }

    func testReadOperationsRetryTheDocumentedStatuses() async throws {
        for status in [408, 429, 500, 502, 503, 504] {
            let transport = failing(status, times: 2)
            let recorder = DelayRecorder()
            let client = try TestFixtures.client(
                transport: transport, sleeper: recorder.makeSleeper(), random: { 1.0 })
            let result = try await client.palette.call("listTraces", ["tenantId": "acme"])
            XCTAssertEqual(result["ok"], .bool(true), "status \(status)")
            let attempts = await transport.attempts
            XCTAssertEqual(attempts, 3, "status \(status)")
            let delays = await recorder.delays
            XCTAssertEqual(delays, [0.25, 0.5], "status \(status)")
        }
    }

    func testNonRetryableStatusesAreSurfacedImmediately() async throws {
        for status in [400, 401, 403, 404, 409, 422, 501] {
            let transport = failing(status, times: 5)
            let client = try TestFixtures.client(transport: transport)
            do {
                try await client.palette.call("listTraces", ["tenantId": "acme"])
                XCTFail("expected \(status) to be surfaced")
            } catch let error as TemperaApiError {
                XCTAssertEqual(error.status, status)
            }
            let attempts = await transport.attempts
            XCTAssertEqual(attempts, 1, "status \(status)")
        }
    }

    func testNonIdempotentOperationsAreSentExactlyOnce() async throws {
        let transport = failing(503, times: 5)
        let client = try TestFixtures.client(transport: transport)
        let op = try XCTUnwrap(
            TemperaSurface.findOperation(product: "controlPlane", id: "createHostedSession"))
        XCTAssertEqual(op.safeRetry, "none")
        do {
            try await client.controlPlane.call(
                "createHostedSession", ["email": "dev@example.test", "password": "hunter2"])
            XCTFail("expected the 503 to be surfaced")
        } catch let error as TemperaApiError {
            XCTAssertEqual(error.status, 503)
        }
        let attempts = await transport.attempts
        XCTAssertEqual(attempts, 1)
    }

    func testIdempotencyKeyedWritesRetryWithTheIdenticalBody() async throws {
        let transport = failing(503, times: 1)
        let client = try TestFixtures.client(transport: transport)
        let op = try XCTUnwrap(
            TemperaSurface.findOperation(product: "controlPlane", id: "createCreditTopup"))
        XCTAssertEqual(op.safeRetry, "idempotent")

        try await client.controlPlane.call(
            "createCreditTopup", ["packId": "pack_1", "idempotencyKey": "topup-1"])
        let requests = await transport.requests
        XCTAssertEqual(requests.count, 2)
        // The retry resends the very same bytes: the key is never re-minted.
        XCTAssertEqual(requests[0].body, requests[1].body)
        XCTAssertEqual(RequestParts(requests[1]).body?["idempotencyKey"], .string("topup-1"))
    }

    func testRetriesAreBoundedAndSurfaceTheLastFailure() async throws {
        let transport = failing(503, times: 99)
        let client = try TestFixtures.client(transport: transport)
        do {
            try await client.palette.call("listTraces", ["tenantId": "acme"])
            XCTFail("expected the retries to run out")
        } catch let error as TemperaApiError {
            XCTAssertEqual(error.status, 503)
            XCTAssertEqual(error.code, "UNAVAILABLE")
        }
        let attempts = await transport.attempts
        XCTAssertEqual(attempts, 3)
    }

    func testServerNamedRetryAfterIsHonoured() async throws {
        let transport = failing(429, times: 1, retryAfter: "2")
        let recorder = DelayRecorder()
        let client = try TestFixtures.client(
            transport: transport, sleeper: recorder.makeSleeper(), random: { 1.0 })
        try await client.palette.call("listTraces", ["tenantId": "acme"])
        let delays = await recorder.delays
        XCTAssertEqual(delays, [2.0])
    }

    func testConnectionFailuresRetryOnlyForSafeOperations() async throws {
        let flaky = StubTransport(responder: { _, attempt in
            guard attempt > 1 else { throw TemperaTransportError("connection reset") }
            return TemperaHTTPResponse(
                status: 200,
                headers: [TemperaKeyValue(key: "content-type", value: "application/json")],
                body: Data(#"{"ok":true}"#.utf8)
            )
        })
        let client = try TestFixtures.client(transport: flaky)
        try await client.palette.call("listTraces", ["tenantId": "acme"])
        let attempts = await flaky.attempts
        XCTAssertEqual(attempts, 2)

        let alwaysDown = StubTransport(responder: { _, _ in
            throw TemperaTransportError("connection reset")
        })
        let writer = try TestFixtures.client(transport: alwaysDown)
        do {
            try await writer.controlPlane.call(
                "createHostedSession", ["email": "dev@example.test", "password": "hunter2"])
            XCTFail("expected the connection failure to surface")
        } catch is TemperaTransportError {
            let attempts = await alwaysDown.attempts
            XCTAssertEqual(attempts, 1)
        }
    }

    func testPassthroughRetriesFollowTheHttpMethod() async throws {
        let get = failing(503, times: 1)
        let client = try TestFixtures.client(transport: get)
        try await client.tempo.request("/custom")
        let getAttempts = await get.attempts
        XCTAssertEqual(getAttempts, 2)

        let post = failing(503, times: 1)
        let writer = try TestFixtures.client(transport: post)
        do {
            try await writer.tempo.request("/custom", method: "POST", body: ["a": 1])
            XCTFail("expected the 503 to surface")
        } catch is TemperaApiError {
            let postAttempts = await post.attempts
            XCTAssertEqual(postAttempts, 1)
        }
    }

    func testRetryCanBeDisabledEntirely() async throws {
        let transport = failing(503, times: 5)
        let client = try TestFixtures.client(
            transport: transport,
            configuration: TemperaClientConfiguration(retry: .none)
        )
        do {
            try await client.palette.call("listTraces", ["tenantId": "acme"])
            XCTFail("expected the 503 to surface")
        } catch is TemperaApiError {
            let attempts = await transport.attempts
            XCTAssertEqual(attempts, 1)
        }
    }

    // MARK: - Timeout

    func testTheDefaultTimeoutIsThirtySecondsAndIsConfigurable() async throws {
        XCTAssertEqual(TemperaClientConfiguration.defaultTimeout, 30)
        XCTAssertEqual(TemperaClientConfiguration().timeout, 30)

        let transport = StubTransport()
        let client = try TestFixtures.client(transport: transport)
        try await client.palette.call("listTraces", ["tenantId": "acme"])
        var request = try await lastRequest(transport)
        XCTAssertEqual(request.timeout, 30)

        let impatient = StubTransport()
        let quick = try TestFixtures.client(
            transport: impatient,
            configuration: TemperaClientConfiguration(timeout: 2.5)
        )
        try await quick.palette.call("listTraces", ["tenantId": "acme"])
        request = try await lastRequest(impatient)
        XCTAssertEqual(request.timeout, 2.5)
    }

    // MARK: - Idempotency key rule

    func testCanonicalIdempotencyKeyIsExactAsciiGraphicBytes() {
        XCTAssertEqual(temperaCanonicalIdempotencyKey("Request-1._~"), "Request-1._~")
        for invalid in ["", "has space", "has\nnewline", "snowman-\u{2603}"] {
            XCTAssertNil(temperaCanonicalIdempotencyKey(invalid), invalid)
        }
        XCTAssertNotNil(temperaCanonicalIdempotencyKey(String(repeating: "x", count: 256)))
        XCTAssertNil(temperaCanonicalIdempotencyKey(String(repeating: "x", count: 257)))
    }
}
