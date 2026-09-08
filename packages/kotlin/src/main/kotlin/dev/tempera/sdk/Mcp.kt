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

import java.util.concurrent.atomic.AtomicLong

/** JSON-RPC client for the unified Tempera MCP gateway. */
public class TemperaMcpClient(
    url: String? = null,
    private val auth: TemperaAuth? = null,
    private val bearer: String? = null,
    private val transport: TemperaTransport = defaultTemperaTransport(),
    private val configuration: TemperaClientConfiguration = TemperaClientConfiguration(),
) {
    /** The gateway endpoint. */
    public val url: String = url ?: auth?.mcpUrl ?: ""

    private val nextId = AtomicLong(1)

    private fun requestId(): Long {
        val id = nextId.getAndUpdate { current ->
            when {
                current > MAX_REQUEST_ID -> throw TemperaSdkException("MCP request id limit reached")
                current == MAX_REQUEST_ID -> MAX_REQUEST_ID + 1
                else -> current + 1
            }
        }
        if (id > MAX_REQUEST_ID) throw TemperaSdkException("MCP request id limit reached")
        return id
    }

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
     *
     * Compatibility: older releases coerced malformed JSON-RPC error values
     * into code-0 MCP errors. This client deliberately rejects malformed
     * envelopes so callers never mistake an invalid response for gateway data.
     */
    public fun rpc(
        method: String,
        params: List<TemperaJsonMember> = emptyList(),
    ): TemperaJson {
        val sent = sendRpc(method, params)
        if (!sent.response.isSuccess()) {
            throw TemperaApiException.from(sent.response.status, sent.response.statusText, sent.response.headers, sent.response.json(), "mcpGateway", method)
        }
        return decodeEnvelope(sent.response.json(), sent.id)
    }

    private fun sendRpc(method: String, params: List<TemperaJsonMember>): SentRpc {
        val id = requestId()
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

        val request =
            TemperaHttpRequest(
                method = "POST",
                url = url,
                headers =
                    listOf(
                        TemperaKeyValue("accept", "application/json"),
                        TemperaKeyValue("content-type", "application/json"),
                        TemperaKeyValue("authorization", "Bearer " + resolveBearer()),
                        TemperaKeyValue(
                            "mcp-protocol-version",
                            TemperaSurface.mcpProtocolVersion,
                        ),
                        TemperaKeyValue("mcp-method", method),
                    ),
                body = payload.serializedBytes(),
                timeoutSeconds = configuration.timeoutSeconds,
            )

        return SentRpc(id, transport.send(request))
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

    /** Check gateway liveness over JSON-RPC. */
    public fun ping(): TemperaJson = rpc("ping")

    /** List every tool the gateway offers: builtins plus product capabilities. */
    public fun listTools(): List<TemperaJson> {
        val catalog = ArrayList<TemperaJson>()
        val descriptors = LinkedHashMap<String, TemperaJson>()
        val seenCursors = HashSet<String>()
        var receivedItems = 0
        var receivedBytes = 0
        var cursor: String? = null
        repeat(MAX_TOOL_PAGES) {
            val params =
                cursor?.let { listOf(TemperaJsonMember("cursor", TemperaJson.Text(it))) } ?: emptyList()
            val page = catalogRpc("tools/list", params, MAX_CATALOG_BYTES - receivedBytes)
            receivedBytes += page.bytes
            val result = page.result
            val tools = singleMember(result, "tools")?.asArray()
                ?: malformed("tools/list result must contain one tools array")
            if (tools.size > MAX_TOOL_ITEMS - receivedItems) {
                malformed("tools/list exceeds item limit")
            }
            receivedItems += tools.size
            for (tool in tools) {
                val name = validateTool(tool)
                if (descriptors.putIfAbsent(name, tool) != null) malformed("tools/list contains duplicate tool name " + name)
                catalog.add(tool)
            }
            val next = optionalSingleMember(result, "nextCursor")
            when (next) {
                null, TemperaJson.Null -> return catalog
                is TemperaJson.Text -> {
                    if (next.value.isEmpty() || !seenCursors.add(next.value)) {
                        malformed("tools/list repeated or empty nextCursor")
                    }
                    cursor = next.value
                }
                else -> malformed("tools/list nextCursor must be a string or null")
            }
        }
        malformed("tools/list exceeds page limit")
    }

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

    private fun decodeEnvelope(parsed: TemperaJson?, expectedId: Long): TemperaJson {
        val response = parsed as? TemperaJson.Obj ?: malformed("response must be an object")
        val version = singleMember(response, "jsonrpc")?.asString()
        if (version != "2.0") malformed("jsonrpc must be exactly 2.0")
        val responseId = singleMember(response, "id")
        if (responseId !is TemperaJson.Int64 || responseId.value != expectedId) {
            malformed("response id does not match request id")
        }
        val result = memberValues(response, "result")
        val errors = memberValues(response, "error")
        if (result.size + errors.size != 1 || result.size > 1 || errors.size > 1) {
            malformed("response must contain exactly one result or error")
        }
        if (result.size == 1) return result.single() // explicit JSON null is a valid result.
        val error = errors.single() as? TemperaJson.Obj ?: malformed("error must be an object")
        val codeValue = singleMember(error, "code")
        val code = (codeValue as? TemperaJson.Int64)?.value
        if (code == null || code !in Int.MIN_VALUE.toLong()..Int.MAX_VALUE.toLong()) {
            malformed("error code must be an integer")
        }
        val message = singleMember(error, "message")?.asString()
            ?: malformed("error message must be a string")
        throw TemperaMcpException(code.toInt(), message, optionalSingleMember(error, "data"))
    }

    private fun catalogRpc(method: String, params: List<TemperaJsonMember>, remainingBytes: Int): CatalogPage {
        val sent = sendRpc(method, params)
        val bytes = sent.response.body.size
        if (bytes > MAX_CATALOG_PAGE_BYTES || bytes > remainingBytes) malformed("tools/list exceeds response byte limit")
        if (!sent.response.isSuccess()) {
            throw TemperaApiException.from(sent.response.status, sent.response.statusText, sent.response.headers, sent.response.json(), "mcpGateway", method)
        }
        return CatalogPage(decodeEnvelope(sent.response.json(), sent.id), bytes)
    }

    private fun validateTool(tool: TemperaJson): String {
        val objectValue = tool as? TemperaJson.Obj ?: malformed("tools/list tool must be an object")
        if (hasDuplicateKeys(objectValue)) malformed("tools/list tool contains duplicate object key")
        val name = singleMember(tool, "name")?.asString()?.takeIf { it.isNotEmpty() }
            ?: malformed("tools/list tool must contain one non-empty name")
        if (name.codePoints().anyMatch { code -> Character.getType(code) == Character.CONTROL.toInt() || Character.getType(code) == Character.FORMAT.toInt() }) malformed("tools/list tool name contains invisible character")
        if (singleMember(tool, "inputSchema") !is TemperaJson.Obj) malformed("tools/list tool inputSchema must be an object")
        val description = optionalSingleMember(tool, "description")
        if (description != null && description !is TemperaJson.Text) malformed("tools/list tool description must be a string")
        return name
    }

    private fun hasDuplicateKeys(value: TemperaJson.Obj): Boolean {
        val pending = ArrayDeque<TemperaJson>()
        pending.add(value)
        while (pending.isNotEmpty()) {
            when (val current = pending.removeLast()) {
                is TemperaJson.Obj -> {
                    val seen = HashSet<String>()
                    for (member in current.members) {
                        if (!seen.add(member.key)) return true
                        pending.add(member.value)
                    }
                }
                is TemperaJson.Arr -> pending.addAll(current.values)
                else -> Unit
            }
        }
        return false
    }

    private fun memberValues(value: TemperaJson, key: String): List<TemperaJson> =
        (value as? TemperaJson.Obj)?.members.orEmpty().filter { it.key == key }.map { it.value }

    private fun singleMember(value: TemperaJson, key: String): TemperaJson? =
        memberValues(value, key).singleOrNull()

    private fun optionalSingleMember(value: TemperaJson, key: String): TemperaJson? {
        val values = memberValues(value, key)
        if (values.size > 1) malformed("duplicate " + key)
        return values.singleOrNull()
    }

    private fun malformed(detail: String): Nothing =
        throw TemperaSdkException("invalid MCP JSON-RPC response: " + detail)

    private companion object {
        const val MAX_REQUEST_ID: Long = 9_007_199_254_740_991L
        const val MAX_TOOL_PAGES: Int = 100
        const val MAX_TOOL_ITEMS: Int = 10_000
        // These limits apply after the default transport has buffered a response.
        // Adapters need their own streaming limits to bound network memory.
        const val MAX_CATALOG_PAGE_BYTES: Int = 1 * 1024 * 1024
        const val MAX_CATALOG_BYTES: Int = 8 * 1024 * 1024
    }

    private data class SentRpc(val id: Long, val response: TemperaHttpResponse)
    private data class CatalogPage(val result: TemperaJson, val bytes: Int)
}
