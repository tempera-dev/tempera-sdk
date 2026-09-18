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

        // SEP-2243 routable headers: a middle box has to route without parsing
        // the body, so the method carries its subject in `Mcp-Name`. A gateway
        // that validates them (tempera-mcp does) refuses a request without one.
        var headers: [TemperaKeyValue] = [
                // Streamable HTTP requires both shapes on a POST: the gateway
                // chooses one JSON body or an SSE stream, and a spec-conformant
                // gateway answers 406 to a client that offers only one.
                TemperaKeyValue(key: "accept", value: "application/json, text/event-stream"),
                TemperaKeyValue(key: "content-type", value: "application/json"),
                TemperaKeyValue(key: "authorization", value: "Bearer \(try await resolveBearer())"),
                TemperaKeyValue(
                    key: "mcp-protocol-version", value: TemperaSurface.mcpProtocolVersion),
                TemperaKeyValue(key: "mcp-method", value: method),
        ]
        if let name = Self.mcpName(method: method, params: requestParams) {
            headers.append(TemperaKeyValue(key: "mcp-name", value: name))
        }

        let request = TemperaHTTPRequest(
            method: "POST",
            url: url,
            headers: headers,
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
    ///
    /// MCP revision 2026-07-28 removed `ping`; a gateway on that revision
    /// answers it with a method-not-found. This helper now sends
    /// `server/discover` so existing callers keep working, and will be
    /// removed in a future release.
    @available(*, deprecated, message: "MCP 2026-07-28 removed `ping`; use initialize() (server/discover)")
    @discardableResult
    public func ping() async throws -> TemperaJSON {
        try await initialize()
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

extension TemperaMcpClient {
    /// Which member of `params` the method's `Mcp-Name` is taken from.
    static let mcpNameSources: [String: String] = [
        "tools/call": "name",
        "prompts/get": "name",
        "resources/read": "uri",
        "resources/subscribe": "uri",
        "resources/unsubscribe": "uri",
        "tasks/get": "taskId",
        "tasks/update": "taskId",
        "tasks/cancel": "taskId",
    ]

    static func mcpName(method: String, params: [TemperaJSONMember]) -> String? {
        guard let key = mcpNameSources[method] else { return nil }
        guard let value = params.first(where: { $0.key == key })?.value.stringValue else {
            return nil
        }
        return headerSafe(value)
    }

    /// A header value, Base64-wrapped as `=?base64?...?=` when it could not
    /// survive as one: edge whitespace, anything outside printable ASCII, or a
    /// value that already looks like the sentinel.
    static func headerSafe(_ value: String) -> String {
        if value.isEmpty { return value }
        let sentinel = value.hasPrefix("=?base64?") && value.hasSuffix("?=")
        let edgeSpace = value.first == " " || value.first == "\t" || value.last == " "
            || value.last == "\t"
        let outsideAscii = value.unicodeScalars.contains { $0.value < 0x20 || $0.value > 0x7E }
        if !(sentinel || edgeSpace || outsideAscii) { return value }
        let encoded = Data(value.utf8).base64EncodedString()
        return "=?base64?" + encoded + "?="
    }
}
