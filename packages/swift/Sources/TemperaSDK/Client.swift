// The unified Tempera client: one credential set, every product.
//
// Built entirely from the generated surface tables (`Surface.swift`), so the
// TypeScript, Python, Rust, Kotlin, and Swift packages expose the same
// products, the same operation names, the same descriptions, and the same
// error shape.
//
// - Typed operations: `try await client.palette.call("getTrace", ["tenantId":
//   ..., "traceId": ...])` -- every operation in `surface.json` is reachable
//   by product key and operation id. Parameters accept canonical wire names
//   and snake_case aliases; requests always emit the producer's canonical wire
//   names.
// - Passthrough: `try await client.tempo.request("/custom", method: "POST",
//   body: ...)` for endpoints the surface tables do not cover yet.
// - Auth: audience products resolve their bearer through `TemperaAuth`
//   (per-audience OAuth token with unified `tp_` API-key fallback);
//   control-plane operations use the account-session token returned by
//   `createHostedSession`.
//
// An actor, because the account-session token mutates mid-flight and one
// client is routinely shared across concurrent requests.

import Foundation

/// Ordered request parameters. A dictionary literal keeps its source order, so
/// undeclared parameters spill to the wire in the order the caller wrote them.
public struct TemperaParams: Sendable, Equatable, ExpressibleByDictionaryLiteral {
    /// The parameters, in insertion order.
    public private(set) var members: [TemperaJSONMember]

    /// Create empty parameters.
    public init() { members = [] }

    /// Create parameters from ordered members.
    public init(_ members: [TemperaJSONMember]) { self.members = members }

    public init(dictionaryLiteral elements: (String, TemperaJSON)...) {
        members = elements.map { TemperaJSONMember($0.0, $0.1) }
    }

    /// Read or write one parameter, preserving insertion order.
    public subscript(key: String) -> TemperaJSON? {
        get { members.first { $0.key == key }?.value }
        set {
            guard let newValue else {
                members.removeAll { $0.key == key }
                return
            }
            set(key, newValue)
        }
    }

    /// Set one parameter, replacing it in place when it already exists.
    public mutating func set(_ key: String, _ value: TemperaJSON) {
        if let index = members.firstIndex(where: { $0.key == key }) {
            members[index] = TemperaJSONMember(key, value)
        } else {
            members.append(TemperaJSONMember(key, value))
        }
    }

    /// Whether one parameter was supplied at all (including as `null`).
    public func contains(_ key: String) -> Bool {
        members.contains { $0.key == key }
    }

    /// Every supplied parameter name, in insertion order.
    public var keys: [String] { members.map(\.key) }
}

/// lowerCamelCase to snake_case, matching the alias rule in the TypeScript and
/// Python clients: an underscore goes before an uppercase letter that follows
/// a lowercase letter or a digit.
public func temperaSnakeCase(_ value: String) -> String {
    var out = ""
    var previous: Character?
    for character in value {
        if character.isUppercase, let previous, previous.isLowercase || previous.isNumber {
            out.append("_")
        }
        out.append(contentsOf: character.lowercased())
        previous = character
    }
    return out
}

/// One product's client: registry metadata, typed operations, passthrough.
public struct TemperaProductClient: Sendable {
    /// lowerCamelCase registry key.
    public let key: String
    /// Human-readable product name.
    public let name: String
    /// Source repository.
    public let repository: String
    /// Environment variable carrying this product's base URL.
    public let envVar: String
    /// Token audience, when the product mints its own.
    public let audience: String?
    /// One-sentence product description.
    public let description: String

    private let client: TemperaClient

    init(spec: TemperaProductSpec, client: TemperaClient) {
        self.key = spec.key
        self.name = spec.name
        self.repository = spec.repository
        self.envVar = spec.envVar
        self.audience = spec.audience
        self.description = spec.description
        self.client = client
    }

    /// Every typed operation this product publishes.
    public var operations: [TemperaOperationSpec] {
        TemperaSurface.operationsFor(product: key)
    }

    /// Invoke one typed operation by its lowerCamelCase id.
    @discardableResult
    public func call(
        _ operation: String,
        _ params: TemperaParams = [:],
        headers: [String: String] = [:],
        bearer: String? = nil
    ) async throws -> TemperaJSON {
        try await client.call(key, operation, params, headers: headers, bearer: bearer)
    }

    /// Invoke one typed operation whose request body is a binary upload.
    @discardableResult
    public func upload(
        _ operation: String,
        _ params: TemperaParams = [:],
        content: Data,
        headers: [String: String] = [:],
        bearer: String? = nil
    ) async throws -> TemperaJSON {
        try await client.call(
            key, operation, params, content: content, headers: headers, bearer: bearer)
    }

    /// Raw request against this product, for endpoints without a typed
    /// operation.
    @discardableResult
    public func request(
        _ path: String,
        method: String = "GET",
        body: TemperaJSON? = nil,
        query: [TemperaKeyValue] = [],
        headers: [String: String] = [:],
        bearer: String? = nil
    ) async throws -> TemperaJSON {
        try await client.request(
            product: key,
            path: path,
            method: method,
            body: body,
            query: query,
            headers: headers,
            bearer: bearer
        )
    }
}

/// The unified Tempera client (see the file comment).
public actor TemperaClient {
    /// Account-session token used by `auth: "account"` (control-plane)
    /// operations; `createHostedSession` stores the one it returns.
    public private(set) var accountToken: String?
    /// Timeout and retry knobs for every request this client makes.
    /// Immutable, so reading it costs no actor hop.
    public nonisolated let configuration: TemperaClientConfiguration

    private let auth: TemperaAuth?
    private let introspectionSecret: String?
    private let baseUrls: [String: String]
    private let environmentTarget: TemperaEnvironmentTarget?
    private let processEnvironment: [String: String]
    private let transport: any TemperaTransport
    private let sleeper: @Sendable (TimeInterval) async throws -> Void
    private let random: @Sendable () -> Double

    /// Create a client.
    ///
    /// - Parameters:
    ///   - auth: unified credential for `product` and `oauthResource` operations.
    ///   - accountToken: account-session token for control-plane operations.
    ///   - introspectionSecret: server-side secret for `introspectToken`.
    ///   - baseUrls: per-product base URL overrides, by registry key.
    ///   - environment: a preset name (`local`, `preview`, `staging`, `production`).
    ///   - transport: the HTTP transport; `URLSession` by default.
    ///   - configuration: timeout and retry policy.
    ///   - processEnvironment: environment variables consulted for base URLs.
    ///   - sleeper: how retry backoff is spent; injected by tests.
    ///   - random: jitter source in `0..<1`; injected by tests.
    public init(
        auth: TemperaAuth? = nil,
        accountToken: String? = nil,
        introspectionSecret: String? = nil,
        baseUrls: [String: String] = [:],
        environment: String? = nil,
        transport: (any TemperaTransport)? = nil,
        configuration: TemperaClientConfiguration = TemperaClientConfiguration(),
        processEnvironment: [String: String] = ProcessInfo.processInfo.environment,
        sleeper: (@Sendable (TimeInterval) async throws -> Void)? = nil,
        random: (@Sendable () -> Double)? = nil
    ) throws {
        if let environment {
            guard let target = TemperaSurface.findEnvironment(environment) else {
                throw TemperaSdkError("unknown Tempera environment: \(environment)")
            }
            self.environmentTarget = target
        } else {
            self.environmentTarget = nil
        }
        self.auth = auth
        self.accountToken = accountToken
        self.introspectionSecret = introspectionSecret
        self.baseUrls = baseUrls
        self.processEnvironment = processEnvironment
        self.transport = transport ?? TemperaURLSessionTransport()
        self.configuration = configuration
        self.sleeper =
            sleeper ?? { seconds in
                guard seconds > 0 else { return }
                try await Task.sleep(nanoseconds: UInt64(seconds * 1_000_000_000))
            }
        self.random = random ?? { Double.random(in: 0..<1) }
    }

    /// Replace the account-session token.
    public func setAccountToken(_ token: String?) {
        accountToken = token
    }

    /// One product's client, by registry key.
    public nonisolated func product(_ key: String) throws -> TemperaProductClient {
        guard let spec = TemperaSurface.findProduct(key: key) else {
            throw TemperaSdkError("unknown Tempera product: \(key)")
        }
        return TemperaProductClient(spec: spec, client: self)
    }

    // MARK: - Typed operations

    /// Invoke one typed operation.
    @discardableResult
    public func call(
        _ product: String,
        _ operation: String,
        _ params: TemperaParams = [:],
        content: Data? = nil,
        headers: [String: String] = [:],
        bearer: String? = nil
    ) async throws -> TemperaJSON {
        let response = try await callResponse(
            product, operation, params, content: content, headers: headers, bearer: bearer)
        let value = TemperaClient.decode(response)
        // createHostedSession returns the account-session token pair; storing
        // it here is what makes later control-plane calls authenticated.
        if product == "controlPlane", operation == "createHostedSession",
            let token = value["access_token"]?.stringValue, !token.isEmpty
        {
            accountToken = token
        }
        return value
    }

    /// Invoke one typed operation and return the whole HTTP response, for
    /// operations whose response body is not JSON.
    public func callResponse(
        _ product: String,
        _ operation: String,
        _ params: TemperaParams = [:],
        content: Data? = nil,
        headers: [String: String] = [:],
        bearer: String? = nil
    ) async throws -> TemperaHTTPResponse {
        let (request, spec) = try await buildRequest(
            product: product,
            operation: operation,
            params: params,
            content: content,
            headers: headers,
            bearer: bearer
        )
        return try await perform(
            request,
            safeRetry: spec.safeRetry,
            product: product,
            operation: operation
        )
    }

    /// Build the HTTP request one typed operation would send, without sending
    /// it. Returns the request and the operation it was built from.
    public func buildRequest(
        product: String,
        operation: String,
        params: TemperaParams = [:],
        content: Data? = nil,
        headers: [String: String] = [:],
        bearer: String? = nil
    ) async throws -> (TemperaHTTPRequest, TemperaOperationSpec) {
        guard let op = TemperaSurface.findOperation(product: product, id: operation) else {
            throw TemperaSdkError("unknown Tempera operation: \(product).\(operation)")
        }
        let request = try await buildRequest(
            op, params: params, content: content, headers: headers, bearer: bearer)
        return (request, op)
    }

    /// Build the HTTP request one operation spec would send. Takes the spec
    /// directly, so a caller that already resolved it -- or a test exercising a
    /// contract feature no shipped operation uses yet -- does not look it up
    /// again.
    public func buildRequest(
        _ op: TemperaOperationSpec,
        params: TemperaParams = [:],
        content: Data? = nil,
        headers: [String: String] = [:],
        bearer: String? = nil
    ) async throws -> TemperaHTTPRequest {
        let product = op.product
        let label = "\(product).\(op.id)"

        // 1. Parameter normalization: a declared parameter may arrive under its
        //    canonical wire name or its snake_case alias, never both.
        var wire = params
        var consumed = Set<String>()
        let declared = op.pathParams + op.query + op.body + op.forbiddenBody
        for wireName in declared {
            let alias = temperaSnakeCase(wireName)
            guard alias != wireName else { continue }
            let hasWireName = params.contains(wireName)
            let hasAlias = params.contains(alias)
            if hasWireName, hasAlias {
                throw TemperaSdkError(
                    "\(label): pass either \"\(wireName)\" or its snake_case alias "
                        + "\"\(alias)\", not both"
                )
            }
            if hasAlias, let value = params[alias] {
                wire.set(wireName, value)
                consumed.insert(alias)
            }
        }

        // 2. Parameters the producer derives from the authenticated principal.
        for key in op.forbiddenBody where wire[key] != nil {
            throw TemperaSdkError("\(label): \(key) is derived from the authenticated principal")
        }

        // 3. Path substitution, with AIP resource-pattern validation.
        let path = try TemperaClient.substitutePath(op: op, params: wire, label: label)
        consumed.formUnion(op.pathParams)

        // 4. Declared query parameters.
        var query: [TemperaKeyValue] = []
        for key in op.query {
            guard let value = wire[key], !value.isNull else {
                if op.requiredQuery.contains(key) {
                    throw TemperaSdkError("\(label): missing required query parameter \"\(key)\"")
                }
                continue
            }
            let text = value.plainText
            if text.isEmpty, op.requiredQuery.contains(key) {
                throw TemperaSdkError("\(label): missing required query parameter \"\(key)\"")
            }
            query.append(TemperaKeyValue(key: key, value: text))
            consumed.insert(key)
        }

        // 5. Request body: declared fields over the operation's defaults, or a
        //    binary payload.
        let binary = op.requestBodyKind == "binary"
        var bodyMembers: [TemperaJSONMember]?
        var binaryContent: Data?
        if binary {
            consumed.insert("content")
            if let content {
                binaryContent = content
            } else if let inline = params["content"]?.stringValue {
                binaryContent = Data(inline.utf8)
            } else {
                throw TemperaSdkError("\(label): missing binary content")
            }
        } else if !op.body.isEmpty || !op.bodyDefaults.isEmpty {
            var members = op.bodyDefaults.map { TemperaJSONMember($0.key, .string($0.value)) }
            for key in op.body {
                guard let value = wire[key] else { continue }
                TemperaClient.setMember(&members, key, value)
                consumed.insert(key)
            }
            bodyMembers = members
        }

        // 6. Forward compatibility: undeclared parameters flow to the query
        //    string on GET/DELETE and into the JSON body otherwise, so a new
        //    server field is usable before the surface tables catch up.
        for member in params.members where !consumed.contains(member.key) {
            if op.method == "GET" || op.method == "DELETE" {
                query.append(TemperaKeyValue(key: member.key, value: member.value.plainText))
            } else if !binary {
                var members = bodyMembers ?? []
                TemperaClient.setMember(&members, member.key, member.value)
                bodyMembers = members
            } else {
                throw TemperaSdkError(
                    "\(label): binary operations only accept content plus declared "
                        + "path/query parameters"
                )
            }
        }

        if let bodyMembers {
            try temperaAssertCanonicalIdempotencyKeys(label, bodyMembers)
        }

        let resolvedBearer: String?
        if let bearer {
            resolvedBearer = bearer
        } else {
            resolvedBearer = try await bearerFor(
                product: product, authKind: op.auth, authAudience: op.authAudience)
        }

        var requestHeaders: [TemperaKeyValue] = [
            TemperaKeyValue(key: "accept", value: "application/json")
        ]
        if binary {
            requestHeaders.append(
                TemperaKeyValue(
                    key: "content-type", value: op.requestContentType ?? "application/octet-stream"))
        } else if bodyMembers != nil {
            requestHeaders.append(
                TemperaKeyValue(key: "content-type", value: "application/json"))
        }
        if let resolvedBearer {
            requestHeaders.append(
                TemperaKeyValue(key: "authorization", value: "Bearer \(resolvedBearer)"))
        }
        TemperaClient.applyHeaderOverrides(&requestHeaders, headers)

        return TemperaHTTPRequest(
            method: op.method,
            url: try baseUrl(for: product) + path + TemperaClient.queryString(query),
            headers: requestHeaders,
            body: binaryContent ?? bodyMembers.map { TemperaJSON.object($0).serializedData() },
            timeout: configuration.timeout
        )
    }

    // MARK: - Passthrough

    /// Raw request against one product, for endpoints without a typed
    /// operation.
    @discardableResult
    public func request(
        product: String,
        path: String,
        method: String = "GET",
        body: TemperaJSON? = nil,
        query: [TemperaKeyValue] = [],
        headers: [String: String] = [:],
        bearer: String? = nil
    ) async throws -> TemperaJSON {
        guard let spec = TemperaSurface.findProduct(key: product) else {
            throw TemperaSdkError("unknown Tempera product: \(product)")
        }
        let resolvedBearer: String?
        if let bearer {
            resolvedBearer = bearer
        } else if spec.audience != nil || product == "controlPlane" {
            resolvedBearer = try? await bearerFor(
                product: product,
                authKind: product == "controlPlane" ? "account" : "product",
                authAudience: nil
            )
        } else {
            resolvedBearer = nil
        }

        var requestHeaders: [TemperaKeyValue] = [
            TemperaKeyValue(key: "accept", value: "application/json")
        ]
        if body != nil {
            requestHeaders.append(TemperaKeyValue(key: "content-type", value: "application/json"))
        }
        if let resolvedBearer {
            requestHeaders.append(
                TemperaKeyValue(key: "authorization", value: "Bearer \(resolvedBearer)"))
        }
        TemperaClient.applyHeaderOverrides(&requestHeaders, headers)

        let request = TemperaHTTPRequest(
            method: method,
            url: try baseUrl(for: product) + (path.hasPrefix("/") ? path : "/\(path)")
                + TemperaClient.queryString(query),
            headers: requestHeaders,
            body: body.map { $0.serializedData() },
            timeout: configuration.timeout
        )
        let response = try await perform(
            request,
            safeRetry: TemperaRetryPolicy.safeRetry(forMethod: method),
            product: product,
            operation: nil
        )
        return TemperaClient.decode(response)
    }

    // MARK: - Sending

    /// Send one already-built request, retrying only when the operation's
    /// classification and the failure both allow it.
    public func perform(
        _ request: TemperaHTTPRequest,
        safeRetry: String,
        product: String?,
        operation: String?
    ) async throws -> TemperaHTTPResponse {
        let policy = configuration.retry
        let budget = policy.attemptBudget(safeRetry: safeRetry)
        var attempt = 1
        while true {
            var retryAfter: TimeInterval?
            var failure: (any Error)?
            do {
                // Every attempt sends the identical request value, so the body
                // and its idempotency key are byte-identical by construction.
                let response = try await transport.send(request)
                if response.isSuccess { return response }
                let error = TemperaApiError.from(
                    status: response.status,
                    statusText: response.statusText,
                    headers: response.headers,
                    body: response.json,
                    product: product,
                    operation: operation
                )
                guard policy.isRetryable(status: response.status) else { throw error }
                retryAfter = response.header("retry-after").flatMap {
                    TemperaRetryPolicy.parseRetryAfter($0)
                }
                failure = error
            } catch let error as TemperaTransportError {
                // No HTTP response existed, which is transient by definition.
                failure = error
            }
            guard failure != nil, attempt < budget else {
                throw failure ?? TemperaSdkError("unreachable retry state")
            }
            try await sleeper(
                policy.delay(beforeAttempt: attempt + 1, retryAfter: retryAfter, random: random())
            )
            attempt += 1
        }
    }

    // MARK: - Configuration

    /// The base URL for one product: an explicit override, then the product's
    /// environment variable, then the environment preset.
    public func baseUrl(for product: String) throws -> String {
        guard let spec = TemperaSurface.findProduct(key: product) else {
            throw TemperaSdkError("unknown Tempera product: \(product)")
        }
        let fromEnvironment = environmentTarget.flatMap {
            TemperaClient.environmentBaseUrl($0, product: product)
        }
        let candidates = [
            baseUrls[product],
            processEnvironment[spec.envVar],
            fromEnvironment,
        ]
        guard let base = candidates.compactMap({ $0 }).first(where: { !$0.isEmpty }) else {
            throw TemperaSdkError(
                "missing base URL for \(product); set \(spec.envVar) or pass "
                    + "baseUrls[\"\(product)\"]"
            )
        }
        return temperaTrimTrailingSlashes(base)
    }

    /// The bearer for one operation's auth kind.
    public func bearerFor(product: String, authKind: String, authAudience: String?) async throws
        -> String?
    {
        switch authKind {
        case "none":
            return nil
        case "introspectionSecret":
            guard let introspectionSecret, !introspectionSecret.isEmpty else {
                throw TemperaSdkError(
                    "\(product): introspectToken requires the introspectionSecret option")
            }
            return introspectionSecret
        case "account":
            guard let accountToken, !accountToken.isEmpty else {
                throw TemperaSdkError(
                    "\(product): an account token is required; call "
                        + "controlPlane.createHostedSession() first or pass accountToken"
                )
            }
            return accountToken
        case "oauthResource":
            let audience = authAudience ?? TemperaSurface.defaultAudience
            guard let auth else {
                throw TemperaSdkError(
                    "\(product): pass a TemperaAuth with credentials permitted for "
                        + "audience \(audience) by this operation"
                )
            }
            return try await auth.bearer(for: audience)
        default:
            let audience =
                TemperaSurface.findProduct(key: product)?.audience ?? TemperaSurface.defaultAudience
            guard let auth else {
                throw TemperaSdkError(
                    "\(product): pass a TemperaAuth with credentials permitted for "
                        + "audience \(audience) by this operation"
                )
            }
            return try await auth.bearer(for: audience)
        }
    }

    // MARK: - Helpers

    /// Environment presets only carry base URLs for these products.
    static func environmentBaseUrl(_ target: TemperaEnvironmentTarget, product: String) -> String? {
        switch product {
        case "controlPlane": return target.controlPlaneUrl
        case "palette": return target.paletteApiUrl
        case "tempo": return target.tempoApiUrl
        case "temperaLlm": return target.temperaLlmApiUrl
        case "temperaRisk": return target.temperaRiskApiUrl
        case "temperaWorkflows": return target.temperaWorkflowsApiUrl
        case "temperaGym": return target.temperaGymUrl
        case "dataEngine": return target.dataEngineApiUrl
        case "cradle": return target.cradleApiUrl
        default: return nil
        }
    }

    static func decode(_ response: TemperaHTTPResponse) -> TemperaJSON {
        guard !response.body.isEmpty else { return .null }
        if let json = response.json { return json }
        guard let text = String(data: response.body, encoding: .utf8) else { return .null }
        return .string(text)
    }

    static func setMember(_ members: inout [TemperaJSONMember], _ key: String, _ value: TemperaJSON)
    {
        if let index = members.firstIndex(where: { $0.key == key }) {
            members[index] = TemperaJSONMember(key, value)
        } else {
            members.append(TemperaJSONMember(key, value))
        }
    }

    static func applyHeaderOverrides(
        _ headers: inout [TemperaKeyValue], _ overrides: [String: String]
    ) {
        for key in overrides.keys.sorted() {
            guard let value = overrides[key] else { continue }
            if let index = headers.firstIndex(where: { $0.key.lowercased() == key.lowercased() }) {
                headers[index] = TemperaKeyValue(key: key, value: value)
            } else {
                headers.append(TemperaKeyValue(key: key, value: value))
            }
        }
    }

    static func queryString(_ query: [TemperaKeyValue]) -> String {
        guard !query.isEmpty else { return "" }
        let encoded = query
            .map { "\(temperaPercentEncode($0.key))=\(temperaPercentEncode($0.value))" }
            .joined(separator: "&")
        return "?\(encoded)"
    }

    /// Substitute `{placeholder}` path parameters, percent-encoding ordinary
    /// values and validating AIP resource patterns.
    static func substitutePath(
        op: TemperaOperationSpec,
        params: TemperaParams,
        label: String
    ) throws -> String {
        var out = ""
        var rest = Substring(op.path)
        while let open = rest.firstIndex(of: "{") {
            guard let close = rest[open...].firstIndex(of: "}") else { break }
            out += rest[rest.startIndex..<open]
            let name = String(rest[rest.index(after: open)..<close])
            guard let value = params[name], !value.isNull, !value.plainText.isEmpty else {
                throw TemperaSdkError("\(label): missing required path parameter \"\(name)\"")
            }
            let pattern = op.pathParamTemplates.first { $0.key == name }?.value
            out += try expandPathParameter(value.plainText, pattern: pattern, name: name, label: label)
            rest = rest[rest.index(after: close)...]
        }
        out += rest
        return out
    }

    /// Percent-encode one path parameter. A producer may declare an AIP
    /// resource pattern such as `projects/*`; its structural slashes survive
    /// only after the value matches the pattern exactly.
    static func expandPathParameter(
        _ value: String,
        pattern: String?,
        name: String,
        label: String
    ) throws -> String {
        guard let pattern else { return temperaPercentEncode(value) }
        let expected = pattern.split(separator: "/", omittingEmptySubsequences: false).map(String.init)
        let observed = value.split(separator: "/", omittingEmptySubsequences: false).map(String.init)
        let invalid = TemperaSdkError(
            "\(label): path parameter \"\(name)\" must match AIP resource pattern \"\(pattern)\""
        )
        guard expected.count == observed.count else { throw invalid }
        var expanded: [String] = []
        for (index, segment) in expected.enumerated() {
            let actual = observed[index]
            if segment == "*" {
                guard !actual.isEmpty, actual != ".", actual != ".." else { throw invalid }
                expanded.append(temperaPercentEncode(actual))
            } else {
                guard segment == actual else { throw invalid }
                expanded.append(segment)
            }
        }
        return expanded.joined(separator: "/")
    }
}
