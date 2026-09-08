import Foundation
import XCTest

@testable import TemperaMerchantSDK

@MainActor
final class OrdersCommerceClientTests: XCTestCase {
    private let merchant = UUID(uuidString: "12345678-1234-4123-8123-123456789abc")!
    private let offerID = "00000000-0000-4000-8000-000000000001"
    private let orderID = "00000000-0000-4000-8000-000000000002"

    private func client(
        token: String = "process-only-test-token", organization: String = "fixture-org"
    ) throws -> OrdersCommerceClient {
        try OrdersCommerceClient(
            origin: URL(string: "https://orders.example")!,
            scope: OrdersWorkspaceScope(
                organizationID: organization, projectID: "fixture-project", environment: .test,
                siteID: "fixture-site"),
            merchantID: merchant, bearerToken: { token }, protocolClasses: [MockURLProtocol.self])
    }

    private func fixture(_ name: String) throws -> [String: Any] {
        let data = try Data(
            contentsOf: Bundle.module.url(
                forResource: "orders-commerce", withExtension: "json", subdirectory: "Fixtures")!)
        let bundle = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        // Compare fixture provenance to the actual vendored lock, not duplicated test constants.
        var root = URL(fileURLWithPath: #filePath)
        for _ in 0..<5 { root.deleteLastPathComponent() }
        let lock = try XCTUnwrap(
            JSONSerialization.jsonObject(
                with: Data(
                    contentsOf: root.appendingPathComponent(
                        "specs/tempera-dropshipping-api.json.source"))) as? [String: Any])
        XCTAssertEqual(bundle["source_commit"] as? String, lock["source_commit"] as? String)
        XCTAssertEqual(bundle["source_sha256"] as? String, lock["source_sha256"] as? String)
        return try XCTUnwrap((bundle["responses"] as? [String: Any])?[name] as? [String: Any])
    }

    private func respond(
        _ body: [String: Any], status: Int = 200, type: String = "application/json"
    ) throws {
        let data = try JSONSerialization.data(withJSONObject: body)
        MockURLProtocol.configure { request, protocolObject in
            protocolObject.deliver(
                HTTPURLResponse(
                    url: request.url!, statusCode: status,
                    httpVersion: nil, headerFields: ["Content-Type": type])!, body: data)
        }
    }

    func testActualProducerResponsesAndAllFourReadRoutes() async throws {
        let client = try client()
        let prefix =
            "/v1/organizations/fixture-org/projects/fixture-project/environments/test/sites/fixture-site"
        try respond(fixture("offer"))
        let offer = try await client.offer(id: offerID)
        XCTAssertEqual(offer.unitAmountMinor, 1200)
        XCTAssertEqual(
            MockURLProtocol.requests.last?.url?.path, prefix + "/catalog/offers/" + offerID)
        try respond(fixture("order"))
        let order = try await client.saleOrder(id: orderID)
        XCTAssertEqual(order.amountMinor, 3600)
        XCTAssertEqual(MockURLProtocol.requests.last?.url?.path, prefix + "/sale-orders/" + orderID)
        try respond(fixture("offers"))
        let offers = try await client.offers(pageToken: "previous-offer", pageSize: 10)
        XCTAssertEqual(offers.items.count, 1)
        XCTAssertEqual(MockURLProtocol.requests.last?.url?.path, prefix + "/catalog/offers")
        let query = URLComponents(
            url: MockURLProtocol.requests.last!.url!, resolvingAgainstBaseURL: false)?.queryItems
        XCTAssertEqual(
            query,
            [
                URLQueryItem(name: "pageSize", value: "10"),
                URLQueryItem(name: "pageToken", value: "previous-offer"),
            ])
        try respond(fixture("orders"))
        let orders = try await client.saleOrders()
        XCTAssertEqual(orders.items.first?.id, orderID)
        let request = try XCTUnwrap(MockURLProtocol.requests.last)
        XCTAssertEqual(request.url?.path, prefix + "/sale-orders")
        XCTAssertEqual(request.httpMethod, "GET")
        XCTAssertEqual(
            request.value(forHTTPHeaderField: "Authorization"), "Bearer process-only-test-token")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Accept"), "application/json")
        XCTAssertNil(request.httpBody)
        XCTAssertNil(request.value(forHTTPHeaderField: "Idempotency-Key"))
    }

    func testScopeMerchantAndResourceMismatchesFailClosed() async throws {
        for field in ["scope", "merchantId", "id"] {
            var body = try fixture("offer")
            if field == "scope" {
                var scope = body[field] as! [String: Any]
                scope["siteId"] = "another-site"
                body[field] = scope
            } else {
                body[field] = field == "id" ? "other-offer" : "12345678-1234-4123-8123-123456789abd"
            }
            try respond(body)
            do {
                _ = try await client().offer(id: offerID)
                XCTFail("accepted \(field) mismatch")
            } catch { XCTAssertEqual(error as? OrdersCommerceError, .invalidResponse) }
        }
    }

    func testPageDuplicateAndLimitViolationsRejected() async throws {
        var page = try fixture("offers")
        let item = try fixture("offer")
        page["items"] = [item, item]
        for pageSize in [1, 10] {
            try respond(page)
            do {
                _ = try await client().offers(pageSize: pageSize)
                XCTFail("accepted invalid page")
            } catch { XCTAssertEqual(error as? OrdersCommerceError, .invalidResponse) }
        }
    }

    func testInvalidInputsDoNotSendRequests() async throws {
        try respond(fixture("offer"))
        for id in ["", "../escape", "id?query", "valid\n", String(repeating: "x", count: 129)] {
            do {
                _ = try await client().offer(id: id)
                XCTFail("accepted invalid ID")
            } catch { XCTAssertEqual(error as? OrdersCommerceError, .invalidRequest) }
        }
        for pageSize in [0, 101] {
            do {
                _ = try await client().offers(pageSize: pageSize)
                XCTFail("accepted invalid pageSize")
            } catch { XCTAssertEqual(error as? OrdersCommerceError, .invalidRequest) }
        }
        for token in ["", "bad\rheader", "nonascii-é", String(repeating: "a", count: 4097)] {
            do {
                _ = try await client(token: token).offers()
                XCTFail("accepted invalid token")
            } catch { XCTAssertEqual(error as? OrdersCommerceError, .authorizationRequired) }
        }
        XCTAssertTrue(MockURLProtocol.requests.isEmpty)
    }

    func testScopeSegmentsAreEncodedWithoutChangingOrigin() async throws {
        var page = try fixture("offers")
        page["items"] = []
        try respond(page)
        _ = try await client(organization: "org@one:two").offers()
        let url = try XCTUnwrap(MockURLProtocol.requests.last?.url)
        XCTAssertEqual(url.host, "orders.example")
        XCTAssertTrue(url.absoluteString.contains("/organizations/org%40one%3Atwo/projects/"))
    }

    func testResponseStatusAndContentTypeRecovery() async throws {
        for (status, expected) in [
            (401, OrdersCommerceError.authorizationRequired), (403, .authorizationRequired),
            (404, .notFound), (503, .server(503)), (201, .server(201)), (302, .server(302)),
        ] {
            try respond([:], status: status)
            do {
                _ = try await client().offers()
                XCTFail("accepted status \(status)")
            } catch { XCTAssertEqual(error as? OrdersCommerceError, expected) }
        }
        try respond(fixture("offers"), type: "text/html")
        do {
            _ = try await client().offers()
            XCTFail("accepted HTML")
        } catch { XCTAssertEqual(error as? OrdersCommerceError, .invalidResponse) }
    }

    func testStreamIsBoundedWithoutContentLength() async throws {
        MockURLProtocol.configure { request, protocolObject in
            protocolObject.deliver(
                HTTPURLResponse(
                    url: request.url!, statusCode: 200, httpVersion: nil,
                    headerFields: ["Content-Type": "application/json"])!,
                body: Data(repeating: 32, count: 256 * 1024 + 1))
        }
        do {
            _ = try await client().offers()
            XCTFail("accepted oversized response")
        } catch { XCTAssertEqual(error as? OrdersCommerceError, .responseTooLarge) }
    }

    func testCancellationDuringTokenRecoverySendsNoRequest() async throws {
        try respond(fixture("offers"))
        let scope = try OrdersWorkspaceScope(
            organizationID: "fixture-org", projectID: "fixture-project", environment: .test,
            siteID: "fixture-site")
        let client = try OrdersCommerceClient(
            origin: URL(string: "https://orders.example")!, scope: scope, merchantID: merchant,
            bearerToken: {
                try await Task.sleep(for: .seconds(30))
                return "unused"
            }, protocolClasses: [MockURLProtocol.self])
        let task = Task { try await client.offers() }
        await Task.yield()
        task.cancel()
        do {
            _ = try await task.value
            XCTFail("accepted cancelled request")
        } catch { XCTAssertEqual(error as? OrdersCommerceError, .cancelled) }
        XCTAssertTrue(MockURLProtocol.requests.isEmpty)
    }
    private func offerInput() throws -> CreateCatalogOfferInput {
        try CreateCatalogOfferInput(
            productClassification: .offlineServices, name: "Fixture service",
            description: "An actual local declaration", unitAmountMinor: 1200)
    }

    private func requestBody(_ request: URLRequest) throws -> Data {
        if let body = request.httpBody { return body }
        let stream = try XCTUnwrap(request.httpBodyStream)
        stream.open()
        defer { stream.close() }
        var bytes = Data()
        var buffer = [UInt8](repeating: 0, count: 4096)
        while stream.hasBytesAvailable {
            let count = stream.read(&buffer, maxLength: buffer.count)
            guard count >= 0 else { throw OrdersCommerceError.invalidRequest }
            if count == 0 { break }
            bytes.append(contentsOf: buffer.prefix(count))
        }
        return bytes
    }

    func testCreationWireBindingsAndBothSuccessStatuses() async throws {
        let client = try client()
        let input = try offerInput()
        let key = "create-offer-request-0001"
        for status in [201, 200] {
            try respond(fixture("offer"), status: status)
            let offer = try await client.createOffer(input, idempotencyKey: key)
            XCTAssertEqual(offer.id, offerID)
            let request = try XCTUnwrap(MockURLProtocol.requests.last)
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(
                request.url?.path,
                "/v1/organizations/fixture-org/projects/fixture-project/environments/test/sites/fixture-site/catalog/offers"
            )
            XCTAssertEqual(
                request.value(forHTTPHeaderField: "Authorization"), "Bearer process-only-test-token"
            )
            XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "application/json")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Idempotency-Key"), key)
            let body = try XCTUnwrap(
                JSONSerialization.jsonObject(with: requestBody(request)) as? [String: Any])
            XCTAssertEqual(body["merchantId"] as? String, merchant.uuidString.lowercased())
            XCTAssertEqual(body["unitAmountMinor"] as? Int, 1200)
            XCTAssertEqual(body["currency"] as? String, "USD")
        }
        try respond(fixture("order"), status: 201)
        let order = try await client.createSaleOrder(
            CreateSaleOrderInput(offerID: offerID, quantity: 3),
            idempotencyKey: "create-order-request-0001")
        XCTAssertEqual(order.amountMinor, 3600)
        let request = try XCTUnwrap(MockURLProtocol.requests.last)
        let body = try XCTUnwrap(
            JSONSerialization.jsonObject(with: requestBody(request)) as? [String: Any])
        XCTAssertEqual(Set(body.keys), ["offerId", "offerRevision", "quantity"])
        XCTAssertEqual(body["offerId"] as? String, offerID)
        XCTAssertEqual(body["quantity"] as? Int, 3)
        XCTAssertTrue(request.url!.path.hasSuffix("/sale-orders"))
    }

    func testInvalidCreationKeysNeverDispatch() async throws {
        for key in [
            "", "short", String(repeating: "a", count: 129), "request-key-with space",
            "request-key-with\n", "request-key-ümlaut",
        ] {
            MockURLProtocol.configure { _, _ in XCTFail("invalid key dispatched") }
            do {
                _ = try await client().createOffer(offerInput(), idempotencyKey: key)
                XCTFail("accepted invalid key")
            } catch { XCTAssertEqual(error as? OrdersCommerceError, .invalidRequest) }
            do {
                _ = try await client().createSaleOrder(
                    CreateSaleOrderInput(offerID: offerID, quantity: 1), idempotencyKey: key)
                XCTFail("accepted invalid key")
            } catch { XCTAssertEqual(error as? OrdersCommerceError, .invalidRequest) }
            XCTAssertTrue(MockURLProtocol.requests.isEmpty)
        }
    }

    func testCreationRefusesUnrelatedOrMutatedResponse() async throws {
        for field in [
            "merchantId", "name", "description", "unitAmountMinor", "productClassification",
        ] {
            var response = try fixture("offer")
            switch field {
            case "merchantId": response[field] = "12345678-1234-4123-8123-123456789abd"
            case "unitAmountMinor": response[field] = 1201
            case "productClassification": response[field] = "physical_goods"
            default: response[field] = "different"
            }
            try respond(response, status: 201)
            do {
                _ = try await client().createOffer(
                    offerInput(), idempotencyKey: "mutated-response-key-001")
                XCTFail("accepted changed \(field)")
            } catch { XCTAssertEqual(error as? OrdersCommerceError, .invalidResponse) }
        }
        var response = try fixture("order")
        response["offerId"] = "different-offer"
        response["variantId"] = "different-offer"
        try respond(response, status: 200)
        do {
            _ = try await client().createSaleOrder(
                CreateSaleOrderInput(offerID: offerID, quantity: 3),
                idempotencyKey: "wrong-sale-response-001")
            XCTFail("accepted different offer")
        } catch { XCTAssertEqual(error as? OrdersCommerceError, .invalidResponse) }
    }

    func testCreationFailureDoesNotAutomaticallyRetryAndManualRetryRetainsBody() async throws {
        let client = try client()
        let input = try offerInput()
        let key = "interrupted-offer-key-001"
        MockURLProtocol.configure { _, transport in
            transport.client?.urlProtocol(
                transport, didFailWithError: URLError(.networkConnectionLost))
        }
        do {
            _ = try await client.createOffer(input, idempotencyKey: key)
            XCTFail("accepted connection loss")
        } catch { XCTAssertEqual(error as? OrdersCommerceError, .unavailable) }
        XCTAssertEqual(MockURLProtocol.requests.count, 1)
        let original = try XCTUnwrap(MockURLProtocol.requests.first)
        let originalBody = try requestBody(original)
        try respond(fixture("offer"), status: 200)
        _ = try await client.createOffer(input, idempotencyKey: key)
        XCTAssertEqual(MockURLProtocol.requests.count, 1)
        let retry = try XCTUnwrap(MockURLProtocol.requests.first)
        XCTAssertEqual(try requestBody(retry), originalBody)
        XCTAssertEqual(retry.value(forHTTPHeaderField: "Idempotency-Key"), key)
        for (status, expected) in [
            (409, OrdersCommerceError.conflict), (422, .invalidRequest),
            (403, .authorizationRequired),
        ] {
            try respond([:], status: status)
            do {
                _ = try await client.createOffer(input, idempotencyKey: key)
                XCTFail("accepted \(status)")
            } catch { XCTAssertEqual(error as? OrdersCommerceError, expected) }
            XCTAssertEqual(MockURLProtocol.requests.count, 1)
        }
    }

}
