import Foundation

@testable import TemperaMerchantSDK

// Qualification-only bridge: the production SDK still constructs HTTPS requests.
// This URLProtocol forwards only this synthetic Orders origin to the supplied
// loopback producer, and can discard a completed response to simulate lost delivery.
final class ProducerBridge: URLProtocol, @unchecked Sendable {
    struct State {
        var origin: URL?
        var dropNextSaleCreation = false
        var statuses: [Int] = []
    }
    static let lock = NSLock()
    nonisolated(unsafe) static var state = State()
    private var flight: Task<Void, Never>?

    static func configure(origin: URL, drop: Bool) {
        lock.lock()
        defer { lock.unlock() }
        state = State(origin: origin, dropNextSaleCreation: drop)
    }
    static func configuration() -> URL {
        lock.lock()
        defer { lock.unlock() }
        return state.origin!
    }
    static func record(status: Int, path: String) -> Bool {
        lock.lock()
        defer { lock.unlock() }
        state.statuses.append(status)
        if status == 201 && path.hasSuffix("/sale-orders") && state.dropNextSaleCreation {
            state.dropNextSaleCreation = false
            return true
        }
        return false
    }
    static func statuses() -> [Int] {
        lock.lock()
        defer { lock.unlock() }
        return state.statuses
    }

    override class func canInit(with request: URLRequest) -> Bool {
        request.url?.host == "orders.example.test"
    }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        flight = Task {
            do {
                guard let original = request.url, original.scheme == "https",
                    original.host == "orders.example.test"
                else {
                    throw URLError(.badURL)
                }
                var parts = URLComponents(
                    url: Self.configuration(), resolvingAgainstBaseURL: false)!
                parts.percentEncodedPath =
                    URLComponents(url: original, resolvingAgainstBaseURL: false)!.percentEncodedPath
                parts.query = original.query
                var forwarded = request
                forwarded.url = parts.url!
                if let stream = forwarded.httpBodyStream {
                    stream.open()
                    defer { stream.close() }
                    var body = Data()
                    var buffer = [UInt8](repeating: 0, count: 4096)
                    while stream.hasBytesAvailable {
                        let count = stream.read(&buffer, maxLength: buffer.count)
                        guard count >= 0 else { throw URLError(.cannotDecodeContentData) }
                        if count == 0 { break }
                        body.append(contentsOf: buffer.prefix(count))
                    }
                    forwarded.httpBodyStream = nil
                    forwarded.httpBody = body
                }
                let session = URLSession(configuration: .ephemeral)
                defer { session.invalidateAndCancel() }
                let (data, response) = try await session.data(for: forwarded)
                let http = response as! HTTPURLResponse
                // Deliberately consume the HTTP result without decoding the order ID.
                if Self.record(status: http.statusCode, path: original.path) {
                    throw URLError(.networkConnectionLost)
                }
                let responseHeaders = http.allHeaderFields.reduce(into: [String: String]()) {
                    result, pair in
                    if let name = pair.key as? String, let value = pair.value as? String {
                        result[name] = value
                    }
                }
                let rebound = HTTPURLResponse(
                    url: original, statusCode: http.statusCode, httpVersion: nil,
                    headerFields: responseHeaders)!
                client?.urlProtocol(self, didReceive: rebound, cacheStoragePolicy: .notAllowed)
                client?.urlProtocol(self, didLoad: data)
                client?.urlProtocolDidFinishLoading(self)
            } catch { client?.urlProtocol(self, didFailWithError: error) }
        }
    }
    override func stopLoading() { flight?.cancel() }
}

@main struct VerifySwiftCommerceCreation {
    static func main() async throws {
        let arguments = CommandLine.arguments
        guard arguments.count >= 3, let origin = URL(string: arguments[2]),
            origin.scheme == "http", origin.host == "127.0.0.1", origin.port != nil,
            origin.user == nil, origin.password == nil, origin.query == nil, origin.fragment == nil,
            origin.path.isEmpty || origin.path == "/"
        else { fatalError("explicit loopback producer required") }
        let prepare = arguments[1] == "prepare"
        precondition(prepare || arguments[1] == "recover")
        ProducerBridge.configure(origin: origin, drop: prepare)
        let scope = try OrdersWorkspaceScope(
            organizationID: "fixture-org", projectID: "fixture-project", environment: .test,
            siteID: "fixture-site")
        let client = try OrdersCommerceClient(
            origin: URL(string: "https://orders.example.test")!, scope: scope,
            merchantID: UUID(uuidString: "12345678-1234-4123-8123-123456789abc")!,
            bearerToken: { "swift-commerce-test-token" }, protocolClasses: [ProducerBridge.self])
        let orderKey = "swift-creation-order-replay-001"
        if prepare {
            let offer = try await client.createOffer(
                CreateCatalogOfferInput(
                    productClassification: .offlineServices,
                    name: "Swift service", description: "Actual Swift to Orders HTTP qualification",
                    unitAmountMinor: 1200),
                idempotencyKey: "swift-creation-offer-replay-001")
            do {
                _ = try await client.createSaleOrder(
                    CreateSaleOrderInput(offerID: offer.id, quantity: 3), idempotencyKey: orderKey)
                fatalError("expected discarded post-commit response")
            } catch let error as OrdersCommerceError { precondition(error == .unavailable) }
            precondition(ProducerBridge.statuses() == [201, 201], "no automatic retry permitted")
            try output(["offer_id": offer.id])
        } else {
            precondition(arguments.count == 4)
            let offerID = arguments[3]
            let recovered = try await client.createSaleOrder(
                CreateSaleOrderInput(offerID: offerID, quantity: 3), idempotencyKey: orderKey)
            let read = try await client.saleOrder(id: recovered.id)
            precondition(
                read == recovered && recovered.amountMinor == 3600
                    && recovered.unitAmountMinor == 1200 && recovered.quantity == 3)
            do {
                _ = try await client.createSaleOrder(
                    CreateSaleOrderInput(offerID: offerID, quantity: 4), idempotencyKey: orderKey)
                fatalError("changed retry body must conflict")
            } catch let error as OrdersCommerceError { precondition(error == .conflict) }
            precondition(ProducerBridge.statuses() == [200, 200, 409])
            try output(["order_id": recovered.id, "amount_minor": recovered.amountMinor])
        }
    }
    static func output(_ value: [String: Any]) throws {
        let data = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
        print(String(decoding: data, as: UTF8.self))
    }
}
