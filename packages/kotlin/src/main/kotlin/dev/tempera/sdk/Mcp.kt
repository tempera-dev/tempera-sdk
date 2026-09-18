// Client for the unified Tempera MCP gateway (`${'$'}{issuer}/mcp`): stateless
// streamable-HTTP JSON-RPC 2.0 in front of every product MCP server.
//
// Mirrors `packages/python/src/tempera_sdk/mcp.py`, including the stateless
// discovery lifecycle: the gateway speaks `server/discover`, not `initialize`.
// Requires a bearer minted for audience `tempera-mcp` with scope `mcp:invoke`
// (or a central `tp_` API key).
//
// JSON-RPC calls are POSTs with side effects, so they are sent exactly once:
// the retry policy is not applied here.

package dev.tempera.sdk

import java.util.concurrent.atomic.AtomicInteger

/** JSON-RPC client for the unified Tempera MCP gateway. */
public class TemperaMcpClient(
    url: String? = null,
    private val auth: TemperaAuth? = null,
    private val bearer: String? = null,
    private val transport: TemperaTransport = JdkHttpTransport(),
    private val configuration: TemperaClientConfiguration = TemperaClientConfiguration(),
) {
    /** The gateway endpoint. */
    public val url: String = url ?: auth?.mcpUrl ?: ""

    private val nextId = AtomicInteger(1)

    init {
        if (this.url.isEmpty()) {
            throw TemperaSdkException("url is required (e.g. https://api.tempera.dev/mcp)")
        }
    }

    private fun resolveBearer(): String {
        if (bearer != null && bearer.isNotEmpty()) return bearer
        if (auth != null) return auth.bearerFor("tempera-mcp")
        throw TemperaSdkException(
            "no MCP credential; pass bearer or a TemperaAuth with an apiKey or tempera-mcp tokens"
        )
    }

    /**
     * Send one JSON-RPC request and return its result.
     *
     * Throws [TemperaMcpException] for a JSON-RPC error object and
     * [TemperaApiException] for an HTTP failure.
     */
    public fun rpc(
        method: String,
        params: List<TemperaJsonMember> = emptyList(),
    ): TemperaJson {
        val id = nextId.getAndIncrement()

        // Every request carries the protocol version and client capabilities in
        // `_meta`, merged into whatever `_meta` the caller supplied.
        val meta = ArrayList<TemperaJsonMember>()
        val supplied = params.firstOrNull { it.key == "_meta" }?.value?.asObject()
        if (supplied != null) meta.addAll(supplied)
        TemperaClient.setMember(
            meta,
            "io.modelcontextprotocol/protocolVersion",
            TemperaJson.Text(TemperaSurface.mcpProtocolVersion),
        )
        TemperaClient.setMember(
            meta,
            "io.modelcontextprotocol/clientCapabilities",
            TemperaJson.Obj(emptyList()),
        )
        val requestParams = ArrayList<TemperaJsonMember>()
        requestParams.addAll(params.filter { it.key != "_meta" })
        requestParams.add(TemperaJsonMember("_meta", TemperaJson.Obj(meta)))

        val payload =
            TemperaJson.Obj(
                listOf(
                    TemperaJsonMember("jsonrpc", TemperaJson.Text("2.0")),
                    TemperaJsonMember("id", TemperaJson.Int64(id.toLong())),
                    TemperaJsonMember("method", TemperaJson.Text(method)),
                    TemperaJsonMember("params", TemperaJson.Obj(requestParams)),
                )
            )

        // SEP-2243 routable headers: a middle box has to route without parsing
        // the body, so the method carries its subject in `Mcp-Name`. A gateway
        // that validates them (tempera-mcp does) refuses a request without one.
        val headers =
            ArrayList<TemperaKeyValue>(
                listOf(
                        // Streamable HTTP requires both shapes on a POST: the
                        // gateway chooses one JSON body or an SSE stream, and a
                        // spec-conformant gateway answers 406 to a client that
                        // offers only one.
                        TemperaKeyValue("accept", "application/json, text/event-stream"),
                        TemperaKeyValue("content-type", "application/json"),
                        TemperaKeyValue("authorization", "Bearer " + resolveBearer()),
                        TemperaKeyValue(
                            "mcp-protocol-version",
                            TemperaSurface.mcpProtocolVersion,
                        ),
                        TemperaKeyValue("mcp-method", method),
                )
            )
        val name = mcpName(method, requestParams)
        if (name != null) {
            headers.add(TemperaKeyValue("mcp-name", name))
        }

        val request =
            TemperaHttpRequest(
                method = "POST",
                url = url,
                headers = headers,
                body = payload.serializedBytes(),
                timeoutSeconds = configuration.timeoutSeconds,
            )

        val response = transport.send(request)
        if (!response.isSuccess()) {
            throw TemperaApiException.from(
                status = response.status,
                statusText = response.statusText,
                headers = response.headers,
                body = response.json(),
                product = "mcpGateway",
                operation = method,
            )
        }
        val parsed = response.json()
        val error = parsed?.get("error")
        if (error != null && !error.isNull()) {
            // Uniform rule (same in TypeScript, Python, and Rust): a JSON-RPC
            // error object carries its integer code (0 when absent) and string
            // message; a non-conformant non-object error becomes code 0 with
            // its string form.
            if (error is TemperaJson.Obj) {
                throw TemperaMcpException(
                    code = error["code"]?.asInt() ?: 0,
                    detail = error["message"]?.asString() ?: "MCP error",
                    data = error["data"],
                )
            }
            throw TemperaMcpException(0, error.plainText(), null)
        }
        return parsed?.get("result") ?: TemperaJson.Null
    }

    /** Discover the stateless MCP server's capabilities and instructions. */
    public fun initialize(
        name: String = "tempera-sdk",
        version: String = TemperaSdk.VERSION,
    ): TemperaJson =
        rpc(
            "server/discover",
            listOf(
                TemperaJsonMember(
                    "_meta",
                    TemperaJson.Obj(
                        listOf(
                            TemperaJsonMember(
                                "io.modelcontextprotocol/clientInfo",
                                TemperaJson.Obj(
                                    listOf(
                                        TemperaJsonMember("name", TemperaJson.Text(name)),
                                        TemperaJsonMember("version", TemperaJson.Text(version)),
                                    )
                                ),
                            )
                        )
                    ),
                )
            ),
        )

    /**
     * Check gateway liveness over JSON-RPC.
     *
     * MCP revision 2026-07-28 removed `ping`; a gateway on that revision answers it with a
     * method-not-found. This helper now sends `server/discover` so existing callers keep
     * working, and will be removed in a future release.
     */
    @Deprecated(
        message = "MCP 2026-07-28 removed `ping`; use initialize() (server/discover)",
        replaceWith = ReplaceWith("initialize()"),
    )
    public fun ping(): TemperaJson = initialize()

    /** List every tool the gateway offers: builtins plus product capabilities. */
    public fun listTools(): List<TemperaJson> =
        rpc("tools/list")["tools"]?.asArray() ?: emptyList()

    /** Invoke a tool by name; product tool calls are metered as `mcp_invocations`. */
    public fun callTool(
        name: String,
        arguments: List<TemperaJsonMember> = emptyList(),
    ): TemperaJson =
        rpc(
            "tools/call",
            listOf(
                TemperaJsonMember("name", TemperaJson.Text(name)),
                TemperaJsonMember("arguments", TemperaJson.Obj(arguments)),
            ),
        )

    /** Invoke a tool by name with Kotlin values as its arguments. */
    public fun callTool(name: String, arguments: Map<String, Any?>): TemperaJson =
        callTool(
            name,
            arguments.entries.map { TemperaJsonMember(it.key, temperaJsonOf(it.value)) },
        )

    /** Fetch the caller's identity, workspace, and scopes as the gateway sees them. */
    public fun whoami(): TemperaJson = callTool("tempera_whoami")

    /** Fetch gateway upstream health for every connected product MCP server. */
    public fun status(): TemperaJson = callTool("tempera_status")

    private companion object {
        /** Which member of `params` the method's `Mcp-Name` is taken from. */
        val MCP_NAME_SOURCES: Map<String, String> =
            mapOf(
                "tools/call" to "name",
                "prompts/get" to "name",
                "resources/read" to "uri",
                "resources/subscribe" to "uri",
                "resources/unsubscribe" to "uri",
                "tasks/get" to "taskId",
                "tasks/update" to "taskId",
                "tasks/cancel" to "taskId",
            )

        fun mcpName(method: String, params: List<TemperaJsonMember>): String? {
            val key = MCP_NAME_SOURCES[method] ?: return null
            val value = params.firstOrNull { it.key == key }?.value?.asString() ?: return null
            return headerSafe(value)
        }

        /**
         * A header value, Base64-wrapped as `=?base64?...?=` when it could not
         * survive as one: edge whitespace, anything outside printable ASCII, or
         * a value that already looks like the sentinel.
         */
        fun headerSafe(value: String): String {
            if (value.isEmpty()) return value
            val sentinel = value.startsWith("=?base64?") && value.endsWith("?=")
            val edgeSpace =
                value.first() == ' ' || value.first() == '\t' ||
                    value.last() == ' ' || value.last() == '\t'
            val outsideAscii = value.any { it.code < 0x20 || it.code > 0x7E }
            if (!(sentinel || edgeSpace || outsideAscii)) return value
            val encoded =
                java.util.Base64.getEncoder().encodeToString(value.toByteArray(Charsets.UTF_8))
            return "=?base64?" + encoded + "?="
        }
    }
}
