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
    @discardableResult
    public func rpc(_ method: String, _ params: [TemperaJSONMember] = []) async throws
        -> TemperaJSON
    {
        let id = nextId
        nextId += 1

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

        let response = try await transport.send(request)
        guard response.isSuccess else {
            throw TemperaApiError.from(
                status: response.status,
                statusText: response.statusText,
                headers: response.headers,
                body: response.json,
                product: "mcpGateway",
                operation: method
            )
        }
        let parsed = response.json
        if let error = parsed?["error"], !error.isNull {
            // Uniform rule (same in TypeScript, Python, and Rust): a JSON-RPC
            // error object carries its integer code (0 when absent) and string
            // message; a non-conformant non-object error becomes code 0 with
            // its string form.
            if case .object = error {
                throw TemperaMcpError(
                    code: error["code"]?.intValue ?? 0,
                    message: error["message"]?.stringValue ?? "MCP error",
                    data: error["data"]
                )
            }
            throw TemperaMcpError(code: 0, message: error.plainText, data: nil)
        }
        return parsed?["result"] ?? .null
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
        let result = try await rpc("tools/list")
        return result["tools"]?.arrayValue ?? []
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
}
