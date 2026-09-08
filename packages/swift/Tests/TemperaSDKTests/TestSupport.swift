import Foundation
import XCTest

@testable import TemperaSDK

/// A transport that records every request and answers from a caller-supplied
/// responder, so the whole client is exercised without a socket -- the same
/// seam the Python package's `FakeTransport` and the TypeScript package's
/// injected `fetch` provide.
actor StubTransport: TemperaTransport {
    /// `(request, attempt)` in, response or thrown failure out.
    typealias Responder = @Sendable (TemperaHTTPRequest, Int) throws -> TemperaHTTPResponse

    private(set) var requests: [TemperaHTTPRequest] = []
    private var attempt = 0
    private let responder: Responder

    init(responder: @escaping Responder = StubTransport.ok) {
        self.responder = responder
    }

    /// The default answer: `{"ok": true}`.
    static let ok: Responder = { _, _ in
        TemperaHTTPResponse(
            status: 200,
            headers: [TemperaKeyValue(key: "content-type", value: "application/json")],
            body: Data(#"{"ok":true}"#.utf8)
        )
    }

    func send(_ request: TemperaHTTPRequest) async throws -> TemperaHTTPResponse {
        requests.append(request)
        attempt += 1
        return try responder(request, attempt)
    }

    var attempts: Int { attempt }

    var lastRequest: TemperaHTTPRequest? { requests.last }

    func clear() {
        requests.removeAll()
        attempt = 0
    }
}

/// One recorded request, split the way the assertions read it.
struct RequestParts {
    let method: String
    let origin: String
    let path: String
    let query: [String: String]
    let headers: [String: String]
    let body: TemperaJSON?
    let rawBody: Data?
    let url: String

    init(_ request: TemperaHTTPRequest) {
        method = request.method
        url = request.url
        let components = URLComponents(string: request.url)
        origin = "\(components?.scheme ?? "")://\(components?.host ?? "")"
        path = components?.percentEncodedPath ?? ""
        var pairs: [String: String] = [:]
        for item in components?.queryItems ?? [] {
            pairs[item.name] = item.value ?? ""
        }
        query = pairs
        var names: [String: String] = [:]
        for header in request.headers { names[header.key.lowercased()] = header.value }
        headers = names
        rawBody = request.body
        body = request.body.flatMap { TemperaJSON.parse($0) }
    }
}

enum TestFixtures {
    static let issuer = "https://api.tempera.dev"
    static let apiKey = "tp_key_1"
    static let accountToken = "account_token_1"
    static let introspectionSecret = "introspect_secret_1"
    static let samplePathParam = "sample-value"
    static let sampleQueryValue = "sample-query"

    /// A base URL per product, so a wrong product key shows up as a wrong host.
    static func baseUrls() -> [String: String] {
        var urls: [String: String] = [:]
        for product in TemperaSurface.products {
            urls[product.key] = "https://\(product.key.lowercased()).example.test"
        }
        return urls
    }

    static func baseUrl(_ product: String) -> String {
        "https://\(product.lowercased()).example.test"
    }

    /// A client wired to a stub transport, with every credential kind present.
    static func client(
        transport: StubTransport,
        auth: TemperaAuth? = nil,
        accountToken: String? = TestFixtures.accountToken,
        environment: String? = nil,
        baseUrls: [String: String]? = nil,
        configuration: TemperaClientConfiguration = TemperaClientConfiguration(),
        processEnvironment: [String: String] = [:],
        sleeper: (@Sendable (TimeInterval) async throws -> Void)? = { _ in },
        random: (@Sendable () -> Double)? = { 1.0 }
    ) throws -> TemperaClient {
        try TemperaClient(
            auth: auth ?? (try TemperaAuth(issuerUrl: issuer, apiKey: apiKey, transport: transport)),
            accountToken: accountToken,
            introspectionSecret: introspectionSecret,
            baseUrls: baseUrls ?? TestFixtures.baseUrls(),
            environment: environment,
            transport: transport,
            configuration: configuration,
            processEnvironment: processEnvironment,
            sleeper: sleeper,
            random: random
        )
    }

    /// A path-parameter value that satisfies the operation's AIP pattern.
    static func pathParam(_ op: TemperaOperationSpec, _ name: String) -> String {
        guard let pattern = op.pathParamTemplates.first(where: { $0.key == name })?.value else {
            return samplePathParam
        }
        return pattern.replacingOccurrences(of: "*", with: samplePathParam)
    }

    /// The path the operation should produce for `pathParam` values.
    static func expectedPath(_ op: TemperaOperationSpec) -> String {
        var path = op.path
        for name in op.pathParams {
            path = path.replacingOccurrences(of: "{\(name)}", with: pathParam(op, name))
        }
        return path
    }
}

/// Assert that an async expression throws a `TemperaSdkError` whose message
/// contains `substring`.
func assertSdkError(
    _ substring: String,
    file: StaticString = #filePath,
    line: UInt = #line,
    _ body: () async throws -> Void
) async {
    do {
        try await body()
        XCTFail("expected a TemperaSdkError containing \(substring)", file: file, line: line)
    } catch let error as TemperaSdkError {
        XCTAssertTrue(
            error.message.contains(substring),
            "\(error.message) does not contain \(substring)",
            file: file,
            line: line
        )
    } catch {
        XCTFail("expected a TemperaSdkError, got \(error)", file: file, line: line)
    }
}

/// The last request a stub recorded, unwrapped for assertions. XCTUnwrap takes
/// a non-async autoclosure, so the actor read happens first.
func lastRequest(
    _ transport: StubTransport,
    file: StaticString = #filePath,
    line: UInt = #line
) async throws -> TemperaHTTPRequest {
    let recorded = await transport.lastRequest
    return try XCTUnwrap(recorded, "no request was recorded", file: file, line: line)
}

/// The last recorded request, split into the parts the assertions read.
func lastParts(
    _ transport: StubTransport,
    file: StaticString = #filePath,
    line: UInt = #line
) async throws -> RequestParts {
    RequestParts(try await lastRequest(transport, file: file, line: line))
}

/// The last recorded request body, as UTF-8 text.
func lastBodyText(
    _ transport: StubTransport,
    file: StaticString = #filePath,
    line: UInt = #line
) async throws -> String {
    let request = try await lastRequest(transport, file: file, line: line)
    let body = try XCTUnwrap(request.body, "the request carried no body", file: file, line: line)
    return try XCTUnwrap(String(data: body, encoding: .utf8), file: file, line: line)
}
