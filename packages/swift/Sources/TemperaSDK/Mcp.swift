// Client for the unified Tempera MCP gateway (`${issuer}/mcp`): stateless
// streamable-HTTP JSON-RPC 2.0 in front of every product MCP server.
//
// Mirrors `packages/python/src/tempera_sdk/mcp.py`, including the stateless
// discovery lifecycle: the gateway speaks `server/discover`, not `initialize`.
// Requires a bearer minted for audience `tempera-mcp` with scope `mcp:invoke`
// (or a central `tp_` API key).
//
// JSON-RPC calls are POSTs with side effects, so they are sent exactly once:
// the retry policy is not applied here.

import Foundation

/// JSON-RPC client for the unified Tempera MCP gateway.
public actor TemperaMcpClient {
    /// The gateway endpoint. Immutable, so reading it costs no actor hop.
    public nonisolated let url: String

    private let auth: TemperaAuth?
    private let bearer: String?
    private let transport: any TemperaTransport
    private let configuration: TemperaClientConfiguration
    private var nextId = 1

    private func requestID() throws -> Int {
        guard nextId <= Self.maximumRequestID else {
            throw TemperaSdkError("MCP request id limit reached")
        }
        let id = nextId
        nextId += 1
        return id
    }

    /// Create a gateway client. `url` defaults to the issuer's `/mcp` path.
    public init(
        url: String? = nil,
        auth: TemperaAuth? = nil,
        bearer: String? = nil,
        transport: (any TemperaTransport)? = nil,
        configuration: TemperaClientConfiguration = TemperaClientConfiguration()
    ) throws {
        guard let resolved = url ?? auth?.mcpUrl, !resolved.isEmpty else {
            throw TemperaSdkError("url is required (e.g. https://api.tempera.dev/mcp)")
        }
        self.url = resolved
        self.auth = auth
        self.bearer = bearer
        self.transport = transport ?? TemperaURLSessionTransport()
        self.configuration = configuration
    }

    private func resolveBearer() async throws -> String {
        if let bearer, !bearer.isEmpty { return bearer }
        if let auth { return try await auth.bearer(for: "tempera-mcp") }
        throw TemperaSdkError(
            "no MCP credential; pass bearer or a TemperaAuth with an apiKey or tempera-mcp tokens"
        )
    }

    /// Send one JSON-RPC request and return its result.
    ///
    /// Throws `TemperaMcpError` for a JSON-RPC error object and
    /// `TemperaApiError` for an HTTP failure.
    ///
    /// Compatibility: older releases coerced malformed JSON-RPC error values
    /// into code-0 MCP errors. This client deliberately rejects malformed
    /// envelopes so callers never mistake an invalid response for gateway data.
    @discardableResult
    public func rpc(_ method: String, _ params: [TemperaJSONMember] = []) async throws
        -> TemperaJSON
    {
        let sent = try await sendRpc(method, params)
        guard sent.response.isSuccess else {
            throw TemperaApiError.from(status: sent.response.status, statusText: sent.response.statusText, headers: sent.response.headers, body: sent.response.json, product: "mcpGateway", operation: method)
        }
        return try decodeEnvelope(sent.response.json, expectedID: sent.id)
    }

    private func sendRpc(_ method: String, _ params: [TemperaJSONMember]) async throws -> SentRpc {
        let id = try requestID()

        // Every request carries the protocol version and client capabilities in
        // `_meta`, merged into whatever `_meta` the caller supplied.
        var meta = params.first { $0.key == "_meta" }?.value.objectValue ?? []
        TemperaClient.setMember(
            &meta,
            "io.modelcontextprotocol/protocolVersion",
            .string(TemperaSurface.mcpProtocolVersion)
        )
        TemperaClient.setMember(&meta, "io.modelcontextprotocol/clientCapabilities", .object([]))
        var requestParams = params.filter { $0.key != "_meta" }
        requestParams.append(TemperaJSONMember("_meta", .object(meta)))

        let payload = TemperaJSON.object([
            TemperaJSONMember("jsonrpc", .string("2.0")),
            TemperaJSONMember("id", .int(id)),
            TemperaJSONMember("method", .string(method)),
            TemperaJSONMember("params", .object(requestParams)),
        ])

        let request = TemperaHTTPRequest(
            method: "POST",
            url: url,
            headers: [
                TemperaKeyValue(key: "accept", value: "application/json"),
                TemperaKeyValue(key: "content-type", value: "application/json"),
                TemperaKeyValue(key: "authorization", value: "Bearer \(try await resolveBearer())"),
                TemperaKeyValue(
                    key: "mcp-protocol-version", value: TemperaSurface.mcpProtocolVersion),
                TemperaKeyValue(key: "mcp-method", value: method),
            ],
            body: payload.serializedData(),
            timeout: configuration.timeout
        )

        return SentRpc(id: id, response: try await transport.send(request))
    }

    /// Discover the stateless MCP server's capabilities and instructions.
    @discardableResult
    public func initialize(
        name: String = "tempera-sdk",
        version: String = TemperaSDK.version
    ) async throws -> TemperaJSON {
        try await rpc(
            "server/discover",
            [
                TemperaJSONMember(
                    "_meta",
                    .object([
                        TemperaJSONMember(
                            "io.modelcontextprotocol/clientInfo",
                            .object([
                                TemperaJSONMember("name", .string(name)),
                                TemperaJSONMember("version", .string(version)),
                            ])
                        )
                    ])
                )
            ]
        )
    }

    /// Check gateway liveness over JSON-RPC.
    @discardableResult
    public func ping() async throws -> TemperaJSON {
        try await rpc("ping")
    }

    /// List every tool the gateway offers: builtins plus product capabilities.
    public func listTools() async throws -> [TemperaJSON] {
        var catalog: [TemperaJSON] = []
        var descriptors: [String: TemperaJSON] = [:]
        var seenCursors = Set<String>()
        var receivedItems = 0
        var receivedBytes = 0
        var cursor: String?
        for _ in 0..<Self.maximumToolPages {
            let params = cursor.map { [TemperaJSONMember("cursor", .string($0))] } ?? []
            let page = try await catalogRpc("tools/list", params, remainingBytes: Self.maximumCatalogBytes - receivedBytes)
            receivedBytes += page.bytes
            let result = page.result
            guard let tools = singleMember(result, "tools")?.arrayValue else {
                throw malformed("tools/list result must contain one tools array")
            }
            guard tools.count <= Self.maximumToolItems - receivedItems else {
                throw malformed("tools/list exceeds item limit")
            }
            receivedItems += tools.count
            for tool in tools {
                let name = try validateTool(tool)
                guard descriptors[name] == nil else { throw malformed("tools/list contains duplicate tool name \(name)") }
                descriptors[name] = tool
                catalog.append(tool)
            }
            switch try optionalSingleMember(result, "nextCursor") {
            case nil, .some(.null): return catalog
            case let .some(.string(next)):
                guard !next.isEmpty, seenCursors.insert(next).inserted else {
                    throw malformed("tools/list repeated or empty nextCursor")
                }
                cursor = next
            default:
                throw malformed("tools/list nextCursor must be a string or null")
            }
        }
        throw malformed("tools/list exceeds page limit")
    }

    /// Invoke a tool by name; product tool calls are metered as
    /// `mcp_invocations`.
    @discardableResult
    public func callTool(_ name: String, arguments: [TemperaJSONMember] = []) async throws
        -> TemperaJSON
    {
        try await rpc(
            "tools/call",
            [
                TemperaJSONMember("name", .string(name)),
                TemperaJSONMember("arguments", .object(arguments)),
            ]
        )
    }

    /// Fetch the caller's identity, workspace, and scopes as the gateway sees
    /// them.
    @discardableResult
    public func whoami() async throws -> TemperaJSON {
        try await callTool("tempera_whoami")
    }

    /// Fetch gateway upstream health for every connected product MCP server.
    @discardableResult
    public func status() async throws -> TemperaJSON {
        try await callTool("tempera_status")
    }

    private func decodeEnvelope(_ parsed: TemperaJSON?, expectedID: Int) throws -> TemperaJSON {
        guard let response = parsed, case .object = response else {
            throw malformed("response must be an object")
        }
        guard singleMember(response, "jsonrpc")?.stringValue == "2.0" else {
            throw malformed("jsonrpc must be exactly 2.0")
        }
        guard case let .int(responseID)? = singleMember(response, "id"), responseID == expectedID else {
            throw malformed("response id does not match request id")
        }
        let result = memberValues(response, "result")
        let errors = memberValues(response, "error")
        guard result.count + errors.count == 1, result.count <= 1, errors.count <= 1 else {
            throw malformed("response must contain exactly one result or error")
        }
        if let result = result.first { return result } // Explicit JSON null is a valid result.
        guard let error = errors.first, case .object = error else {
            throw malformed("error must be an object")
        }
        guard case let .int(code)? = singleMember(error, "code") else {
            throw malformed("error code must be an integer")
        }
        guard let message = singleMember(error, "message")?.stringValue else {
            throw malformed("error message must be a string")
        }
        throw TemperaMcpError(
            code: code,
            message: message,
            data: try optionalSingleMember(error, "data")
        )
    }

    private func catalogRpc(_ method: String, _ params: [TemperaJSONMember], remainingBytes: Int) async throws -> CatalogPage {
        let sent = try await sendRpc(method, params)
        let bytes = sent.response.body.count
        guard bytes <= Self.maximumCatalogPageBytes, bytes <= remainingBytes else {
            throw malformed("tools/list exceeds response byte limit")
        }
        guard sent.response.isSuccess else {
            throw TemperaApiError.from(status: sent.response.status, statusText: sent.response.statusText, headers: sent.response.headers, body: sent.response.json, product: "mcpGateway", operation: method)
        }
        return CatalogPage(result: try decodeEnvelope(sent.response.json, expectedID: sent.id), bytes: bytes)
    }

    private func validateTool(_ tool: TemperaJSON) throws -> String {
        guard case let .object(members) = tool else { throw malformed("tools/list tool must be an object") }
        guard !hasDuplicateKeys(.object(members)) else { throw malformed("tools/list tool contains duplicate object key") }
        guard let name = singleMember(tool, "name")?.stringValue, !name.isEmpty else { throw malformed("tools/list tool must contain one non-empty name") }
        guard !name.unicodeScalars.contains(where: { $0.properties.generalCategory == .control || $0.properties.generalCategory == .format }) else { throw malformed("tools/list tool name contains invisible character") }
        guard case .object? = singleMember(tool, "inputSchema") else { throw malformed("tools/list tool inputSchema must be an object") }
        if let description = try optionalSingleMember(tool, "description"), description.stringValue == nil { throw malformed("tools/list tool description must be a string") }
        return name
    }

    private func hasDuplicateKeys(_ value: TemperaJSON) -> Bool {
        var pending = [value]
        while let current = pending.popLast() {
            switch current {
            case let .object(members):
                var seen = Set<String>()
                for member in members {
                    guard seen.insert(member.key).inserted else { return true }
                    pending.append(member.value)
                }
            case let .array(items): pending.append(contentsOf: items)
            default: break
            }
        }
        return false
    }

    private func memberValues(_ value: TemperaJSON, _ key: String) -> [TemperaJSON] {
        value.objectValue?.filter { $0.key == key }.map(\.value) ?? []
    }

    private func singleMember(_ value: TemperaJSON, _ key: String) -> TemperaJSON? {
        let values = memberValues(value, key)
        return values.count == 1 ? values[0] : nil
    }

    private func optionalSingleMember(_ value: TemperaJSON, _ key: String) throws -> TemperaJSON? {
        let values = memberValues(value, key)
        guard values.count <= 1 else { throw malformed("duplicate \(key)") }
        return values.first
    }

    private func malformed(_ detail: String) -> TemperaSdkError {
        TemperaSdkError("invalid MCP JSON-RPC response: \(detail)")
    }

    private static let maximumRequestID = 9_007_199_254_740_991
    private static let maximumToolPages = 100
    private static let maximumToolItems = 10_000
    // These limits apply after the default transport has buffered a response.
    // Adapters need their own streaming limits to bound network memory.
    private static let maximumCatalogPageBytes = 1 * 1024 * 1024
    private static let maximumCatalogBytes = 8 * 1024 * 1024

    private struct SentRpc { let id: Int; let response: TemperaHTTPResponse }
    private struct CatalogPage { let result: TemperaJSON; let bytes: Int }
}
