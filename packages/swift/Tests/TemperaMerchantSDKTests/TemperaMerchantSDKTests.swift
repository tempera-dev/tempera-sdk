import Foundation
import XCTest
@testable import TemperaMerchantSDK

final class MockURLProtocol: URLProtocol, @unchecked Sendable {
    static let lock = NSLock()
    // These test fixtures are guarded by `lock`; URLProtocol invokes them off-main.
    nonisolated(unsafe) static var requests: [URLRequest] = []
    nonisolated(unsafe) static var stopCount = 0
    nonisolated(unsafe) static var responder: ((URLRequest, MockURLProtocol) -> Void)!

    override class func canInit(with request: URLRequest) -> Bool {
        true
    }

    override class func canonicalRequest(for request: URLRequest) -> URLRequest {
        request
    }

    override func startLoading() {
        Self.lock.lock()
        Self.requests.append(request)
        let responder = Self.responder
        Self.lock.unlock()
        responder!(request, self)
    }

    override func stopLoading() {
        Self.lock.lock()
        Self.stopCount += 1
        Self.lock.unlock()
    }

    func deliver(_ response: HTTPURLResponse, body: Data) {
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: body)
        client?.urlProtocolDidFinishLoading(self)
    }

    func deliverHeader(_ response: HTTPURLResponse) {
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
    }

    func deliverBody(_ body: Data) {
        client?.urlProtocol(self, didLoad: body)
        client?.urlProtocolDidFinishLoading(self)
    }

    func deliver(after delay: TimeInterval, response: HTTPURLResponse, body: Data) {
        DispatchQueue.global().asyncAfter(deadline: .now() + delay) { [weak self] in
            self?.deliver(response, body: body)
        }
    }

    static func configure(_ responder: @escaping (URLRequest, MockURLProtocol) -> Void) {
        lock.lock()
        requests = []
        stopCount = 0
        self.responder = responder
        lock.unlock()
    }

    static var stoppedRequests: Int {
        lock.lock()
        defer { lock.unlock() }
        return stopCount
    }
}

private final class LockedCounter: @unchecked Sendable {
    private let lock = NSLock()
    private var storage = 0

    func next() -> Int {
        lock.lock()
        defer { lock.unlock() }
        storage += 1
        return storage
    }

    var value: Int {
        lock.lock()
        defer { lock.unlock() }
        return storage
    }
}

final class TemperaMerchantSDKTests: XCTestCase {
    private let merchantID = UUID(uuidString: "018f3b2a-cc59-7b60-9c18-836c07d1f9d9")!

    private func client(token: String = "human-token") throws -> MerchantClient {
        try MerchantClient(
            origin: URL(string: "https://payments.example")!,
            bearerToken: { token },
            protocolClasses: [MockURLProtocol.self]
        )
    }

    private func response(
        _ body: Data,
        status: Int = 200,
        contentLength: Int? = nil
    ) -> HTTPURLResponse {
        var headers = ["Content-Type": "application/json"]
        if let contentLength {
            headers["Content-Length"] = String(contentLength)
        }
        return HTTPURLResponse(
            url: URL(string: "https://payments.example")!,
            statusCode: status,
            httpVersion: nil,
            headerFields: headers
        )!
    }

    private func merchantJSON(
        tenantID: String = "tenant-a",
        observedAt: Int? = nil,
        country: String = "US",
        currency: String = "usd"
    ) -> Data {
        let observed = observedAt ?? Int(Date().timeIntervalSince1970)
        return Data("""
        {"id":"\(merchantID.uuidString.lowercased())","tenantId":"\(tenantID)","country":"\(country)","currency":"\(currency)","category":"physical_goods","workspaceReady":true,"paymentsEnabled":true,"payoutsEnabled":true,"actionRequired":false,"requirementsCurrent":true,"currentlyDue":[],"pastDue":[],"pendingVerification":[],"disabledReason":null,"nextAction":"ready","providerObservedAt":\(observed)}
        """.utf8)
    }

    override func setUp() {
        MockURLProtocol.configure { _, protocolInstance in
            let body = self.merchantJSON()
            protocolInstance.deliver(
                self.response(body, contentLength: body.count),
                body: body
            )
        }
    }

    func testCreateWire() async throws {
        MockURLProtocol.configure { request, protocolInstance in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(request.url?.path, "/v1/merchants")
            XCTAssertNil(request.url?.query)
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer human-token")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Idempotency-Key"), "key-1")
            XCTAssertEqual(request.timeoutInterval, 15)
            XCTAssertEqual(
                String(data: bodyData(request), encoding: .utf8),
                "{\"category\":\"physical_goods\",\"country\":\"US\",\"currency\":\"usd\",\"tenantId\":\"tenant-a\"}"
            )
            let body = self.merchantJSON()
            protocolInstance.deliver(self.response(body, contentLength: body.count), body: body)
        }

        _ = try await client().create(
            CreateMerchantRequest(tenantID: "tenant-a", category: .physicalGoods),
            idempotencyKey: "key-1"
        )
    }

    func testWorkspaceReadWire() async throws {
        MockURLProtocol.configure { request, protocolInstance in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(request.url?.path, "/v1/merchants")
            XCTAssertEqual(request.url?.query, "tenantId=tenant-a")
            XCTAssertNil(request.httpBody)
            let body = self.merchantJSON()
            protocolInstance.deliver(self.response(body, contentLength: body.count), body: body)
        }

        _ = try await client().workspaceMerchant(tenantID: "tenant-a")
    }

    func testMerchantReadWire() async throws {
        MockURLProtocol.configure { request, protocolInstance in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(request.url?.path, "/v1/merchants/\(self.merchantID.uuidString.lowercased())")
            XCTAssertEqual(request.url?.query, "tenantId=tenant-a")
            let body = self.merchantJSON()
            protocolInstance.deliver(self.response(body, contentLength: body.count), body: body)
        }

        _ = try await client().merchant(id: merchantID, tenantID: "tenant-a")
    }

    func testRefreshWire() async throws {
        MockURLProtocol.configure { request, protocolInstance in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(request.url?.path, "/v1/merchants/\(self.merchantID.uuidString.lowercased())/refresh")
            XCTAssertNil(request.url?.query)
            XCTAssertEqual(String(data: bodyData(request), encoding: .utf8), "{\"tenantId\":\"tenant-a\"}")
            let body = self.merchantJSON()
            protocolInstance.deliver(self.response(body, contentLength: body.count), body: body)
        }

        _ = try await client().refresh(id: merchantID, tenantID: "tenant-a")
    }

    func testOnboardingWire() async throws {
        MockURLProtocol.configure { request, protocolInstance in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(request.url?.path, "/v1/merchants/\(self.merchantID.uuidString.lowercased())/onboarding")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Idempotency-Key"), "key-2")
            XCTAssertEqual(String(data: bodyData(request), encoding: .utf8), "{\"tenantId\":\"tenant-a\"}")
            let body = Data("{\"merchantId\":\"\(self.merchantID.uuidString.lowercased())\",\"url\":\"https://connect.stripe.com/onboard\",\"expiresAt\":\(Int(Date().timeIntervalSince1970) + 60)}".utf8)
            protocolInstance.deliver(self.response(body, contentLength: body.count), body: body)
        }

        _ = try await client().onboarding(
            id: merchantID,
            tenantID: "tenant-a",
            idempotencyKey: "key-2"
        )
    }

    func testBearerTokenIsObtainedForEachRequest() async throws {
        let tokenCalls = LockedCounter()
        let requests = LockedCounter()
        MockURLProtocol.configure { request, protocolInstance in
            XCTAssertEqual(
                request.value(forHTTPHeaderField: "Authorization"),
                "Bearer human-token-\(requests.next())"
            )
            let body = self.merchantJSON()
            protocolInstance.deliver(self.response(body, contentLength: body.count), body: body)
        }
        let client = try MerchantClient(
            origin: URL(string: "https://payments.example")!,
            bearerToken: { "human-token-\(tokenCalls.next())" },
            protocolClasses: [MockURLProtocol.self]
        )

        _ = try await client.workspaceMerchant(tenantID: "tenant-a")
        _ = try await client.workspaceMerchant(tenantID: "tenant-a")
        XCTAssertEqual(tokenCalls.value, 2)
    }

    func testExactResponseLimitIsAcceptedAndLimitPlusOneIsRejected() async throws {
        let exact = Data(repeating: 0x20, count: 256 * 1024)
        MockURLProtocol.configure { _, protocolInstance in
            protocolInstance.deliver(self.response(exact, contentLength: exact.count), body: exact)
        }
        do {
            _ = try await client().workspaceMerchant(tenantID: "tenant-a")
            XCTFail("Expected decode failure for non-JSON exact-limit response.")
        } catch let error as MerchantClientError {
            guard case .invalidResponse = error else {
                return XCTFail("Exact limit must not be classified as too large.")
            }
        }

        let oversized = Data(repeating: 0x20, count: 256 * 1024 + 1)
        MockURLProtocol.configure { _, protocolInstance in
            protocolInstance.deliver(self.response(oversized, contentLength: oversized.count), body: oversized)
        }
        do {
            _ = try await client().workspaceMerchant(tenantID: "tenant-a")
            XCTFail("Expected response limit rejection.")
        } catch let error as MerchantClientError {
            XCTAssertEqual(error, .responseTooLarge)
        }
    }

    func testOversizedDeclaredLengthCancelsUnderlyingRequest() async throws {
        let stopped = expectation(description: "underlying task cancelled")
        MockURLProtocol.configure { _, protocolInstance in
            let response = self.response(Data(), contentLength: 256 * 1024 + 1)
            protocolInstance.deliverHeader(response)
            DispatchQueue.global().asyncAfter(deadline: .now() + 0.05) {
                if MockURLProtocol.stoppedRequests > 0 {
                    stopped.fulfill()
                }
            }
        }

        do {
            _ = try await client().workspaceMerchant(tenantID: "tenant-a")
            XCTFail("Expected declared-length rejection.")
        } catch let error as MerchantClientError {
            XCTAssertEqual(error, .responseTooLarge)
        }
        await fulfillment(of: [stopped], timeout: 1)
    }

    func testChunkedOversizedResponseCancelsUnderlyingRequest() async throws {
        let stopped = expectation(description: "chunked underlying task cancelled")
        let oversized = Data(repeating: 0x20, count: 256 * 1024 + 1)
        MockURLProtocol.configure { _, protocolInstance in
            protocolInstance.deliverHeader(self.response(Data()))
            protocolInstance.deliverBody(oversized)
            DispatchQueue.global().asyncAfter(deadline: .now() + 0.05) {
                if MockURLProtocol.stoppedRequests > 0 {
                    stopped.fulfill()
                }
            }
        }

        do {
            _ = try await client().workspaceMerchant(tenantID: "tenant-a")
            XCTFail("Expected streamed response rejection.")
        } catch let error as MerchantClientError {
            XCTAssertEqual(error, .responseTooLarge)
        }
        await fulfillment(of: [stopped], timeout: 1)
    }

    func testServerErrorPreservesStatusAndProviderCode() async throws {
        let body = Data("{\"error\":{\"code\":\"merchant_unavailable\",\"message\":\"Try again later.\"}}".utf8)
        MockURLProtocol.configure { _, protocolInstance in
            protocolInstance.deliver(self.response(body, status: 503, contentLength: body.count), body: body)
        }

        do {
            _ = try await client().workspaceMerchant(tenantID: "tenant-a")
            XCTFail("Expected server error.")
        } catch let error as MerchantClientError {
            XCTAssertEqual(
                error,
                .server(statusCode: 503, code: "merchant_unavailable", message: "Try again later.")
            )
        }
    }

    func testResponseBindingConstantsAndStrictFreshness() async throws {
        let now = Int(Date().timeIntervalSince1970)
        MockURLProtocol.configure { _, protocolInstance in
            let body = self.merchantJSON(observedAt: now - 300)
            protocolInstance.deliver(self.response(body, contentLength: body.count), body: body)
        }
        let atTTL = try await client().workspaceMerchant(tenantID: "tenant-a")
        XCTAssertFalse(atTTL.isReady(now: Date(timeIntervalSince1970: TimeInterval(now))))

        MockURLProtocol.configure { _, protocolInstance in
            let body = self.merchantJSON(observedAt: now - 299)
            protocolInstance.deliver(self.response(body, contentLength: body.count), body: body)
        }
        let beforeTTL = try await client().workspaceMerchant(tenantID: "tenant-a")
        XCTAssertTrue(beforeTTL.isReady(now: Date(timeIntervalSince1970: TimeInterval(now))))

        MockURLProtocol.configure { _, protocolInstance in
            let body = self.merchantJSON(country: "CA")
            protocolInstance.deliver(self.response(body, contentLength: body.count), body: body)
        }
        do {
            _ = try await client().workspaceMerchant(tenantID: "tenant-a")
            XCTFail("Expected country validation.")
        } catch let error as MerchantClientError {
            guard case .invalidResponse = error else {
                return XCTFail("Wrong error for response constants.")
            }
        }
    }

    func testOnboardingLinkRejectsWrongHostAndExpiredLink() async throws {
        MockURLProtocol.configure { _, protocolInstance in
            let body = Data("{\"merchantId\":\"\(self.merchantID.uuidString.lowercased())\",\"url\":\"https://evil.example/x\",\"expiresAt\":\(Int(Date().timeIntervalSince1970) + 60)}".utf8)
            protocolInstance.deliver(self.response(body, contentLength: body.count), body: body)
        }
        do {
            _ = try await client().onboarding(id: merchantID, tenantID: "tenant-a", idempotencyKey: "key-2")
            XCTFail("Expected link host validation.")
        } catch let error as MerchantClientError {
            guard case .invalidResponse = error else { return XCTFail("Wrong error") }
        }

        MockURLProtocol.configure { _, protocolInstance in
            let body = Data("{\"merchantId\":\"\(self.merchantID.uuidString.lowercased())\",\"url\":\"https://connect.stripe.com/onboard\",\"expiresAt\":1}".utf8)
            protocolInstance.deliver(self.response(body, contentLength: body.count), body: body)
        }
        do {
            _ = try await client().onboarding(id: merchantID, tenantID: "tenant-a", idempotencyKey: "key-3")
            XCTFail("Expected expiry validation.")
        } catch let error as MerchantClientError {
            guard case .invalidResponse = error else { return XCTFail("Wrong error") }
        }
    }

    func testRedirectDelegateRejectsRedirect() {
        let delegate = RedirectDenyingDelegate()
        let task = URLSession.shared.dataTask(with: URL(string: "https://payments.example")!)
        let response = HTTPURLResponse(
            url: URL(string: "https://payments.example")!,
            statusCode: 302,
            httpVersion: nil,
            headerFields: ["Location": "https://evil.example/"]
        )!
        let completion = expectation(description: "redirect denied")
        delegate.urlSession(
            .shared,
            task: task,
            willPerformHTTPRedirection: response,
            newRequest: URLRequest(url: URL(string: "https://evil.example/")!)
        ) { redirectedRequest in
            XCTAssertNil(redirectedRequest)
            completion.fulfill()
        }
        wait(for: [completion], timeout: 1)
    }

    func testCancellingOneRequestDoesNotCancelAnother() async throws {
        let slowStarted = expectation(description: "slow request started")
        MockURLProtocol.configure { request, protocolInstance in
            if request.url?.query == "tenantId=tenant-slow" {
                slowStarted.fulfill()
                let body = self.merchantJSON(tenantID: "tenant-slow")
                protocolInstance.deliver(after: 0.2, response: self.response(body, contentLength: body.count), body: body)
                return
            }
            let body = self.merchantJSON(tenantID: "tenant-good")
            protocolInstance.deliver(self.response(body, contentLength: body.count), body: body)
        }

        let client = try client()
        let slow = Task { try await client.workspaceMerchant(tenantID: "tenant-slow") }
        await fulfillment(of: [slowStarted], timeout: 1)
        let good = try await client.workspaceMerchant(tenantID: "tenant-good")
        slow.cancel()
        do {
            _ = try await slow.value
            XCTFail("Expected cancelled request.")
        } catch let error as MerchantClientError {
            XCTAssertEqual(error, .cancelled)
        }
        XCTAssertEqual(good.tenantID, "tenant-good")
    }

    func testCancellationBeforeRequestIsRecoverable() async throws {
        let client = try client()
        let task = Task { try await client.workspaceMerchant(tenantID: "tenant-a") }
        task.cancel()
        do {
            _ = try await task.value
            XCTFail("Expected cancellation")
        } catch let error as MerchantClientError {
            XCTAssertEqual(error, .cancelled)
        }
    }
}

private func bodyData(_ request: URLRequest) -> Data {
    if let body = request.httpBody {
        return body
    }
    guard let stream = request.httpBodyStream else {
        return Data()
    }
    stream.open()
    defer { stream.close() }
    var output = Data()
    var buffer = [UInt8](repeating: 0, count: 4096)
    while stream.hasBytesAvailable {
        let count = stream.read(&buffer, maxLength: buffer.count)
        guard count > 0 else { break }
        output.append(buffer, count: count)
    }
    return output
}

extension TemperaMerchantSDKTests {
    func testMerchantWorkspaceWireAndNull() async throws {
        MockURLProtocol.configure { request, protocolInstance in
            XCTAssertEqual(request.url?.path, "/v1/merchants/workspace"); XCTAssertNil(request.url?.query)
            let body = Data("{\"tenantId\":\"tenant-a\",\"merchant\":null}".utf8)
            protocolInstance.deliver(self.response(body, contentLength: body.count), body: body)
        }
        let workspace = try await client().workspace()
        XCTAssertNil(workspace.merchant)
    }
    func testMerchantWorkspaceNestedMismatchRejected() async throws {
        MockURLProtocol.configure { _, p in let m=String(data:self.merchantJSON(tenantID:"tenant-b"),encoding:.utf8)!; let body=Data("{\"tenantId\":\"tenant-a\",\"merchant\":\(m)}".utf8); p.deliver(self.response(body,contentLength:body.count),body:body) }
        await XCTAssertThrowsErrorAsync { _ = try await self.client().workspace() }
    }
    func testMerchantWorkspaceMissingMerchantRejected() async throws {
        MockURLProtocol.configure { _, p in let body=Data("{\"tenantId\":\"tenant-a\"}".utf8); p.deliver(self.response(body,contentLength:body.count),body:body) }
        await XCTAssertThrowsErrorAsync { _ = try await self.client().workspace() }
    }
    func testMerchantWorkspaceBadTenantRejected() async throws {
        MockURLProtocol.configure { _, p in let body=Data("{\"tenantId\":\"\",\"merchant\":null}".utf8); p.deliver(self.response(body,contentLength:body.count),body:body) }
        await XCTAssertThrowsErrorAsync { _ = try await self.client().workspace() }
    }
}

private func XCTAssertThrowsErrorAsync(_ operation: () async throws -> Void) async {
    do { try await operation(); XCTFail("Expected error") } catch { }
}
