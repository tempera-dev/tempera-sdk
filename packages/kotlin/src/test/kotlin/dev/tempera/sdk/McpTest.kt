package dev.tempera.sdk

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows

class McpTest {
    private val version = TemperaSurface.mcpProtocolVersion

    private fun gateway(
        body: String? = null
    ): StubTransport = StubTransport { request, _ ->
        val response = body ?: run {
            val id = (TemperaJson.parse(request.body!!)!!["id"] as TemperaJson.Int64).value
            """{"jsonrpc":"2.0","id":$id,"result":{"ok":true}}"""
        }
        StubTransport.json(response)
    }

    private fun client(transport: StubTransport): TemperaMcpClient =
        TemperaMcpClient(
            url = "https://api.tempera.dev/mcp",
            bearer = "mcp_token_1",
            transport = transport,
        )

    @Test
    fun theGatewayUrlDefaultsToTheIssuersMcpPath() {
        val auth =
            TemperaAuth(
                TestFixtures.ISSUER,
                apiKey = TestFixtures.API_KEY,
                transport = StubTransport(),
            )
        val mcp = TemperaMcpClient(auth = auth, transport = StubTransport())
        assertEquals(TestFixtures.ISSUER + "/mcp", mcp.url)
        assertSdkError("url is required") { TemperaMcpClient(transport = StubTransport()) }
    }

    @Test
    fun initializeUsesTheStatelessDiscoveryLifecycle() {
        val transport = gateway()
        client(transport).initialize()

        val request = transport.lastRequest()
        assertEquals("POST", request.method)
        assertEquals("https://api.tempera.dev/mcp", request.url)
        assertEquals("Bearer mcp_token_1", request.header("authorization"))
        assertEquals("application/json", request.header("content-type"))
        // The stateless gateway speaks server/discover, not initialize.
        assertEquals("server/discover", request.header("mcp-method"))
        assertEquals(version, request.header("mcp-protocol-version"))

        assertEquals(
            """{"jsonrpc":"2.0","id":1,"method":"server/discover","params":{"_meta":{""" +
                """"io.modelcontextprotocol/clientInfo":{"name":"tempera-sdk","version":"0.12.0"},""" +
                """"io.modelcontextprotocol/protocolVersion":"$version",""" +
                """"io.modelcontextprotocol/clientCapabilities":{}}}}""",
            transport.lastBodyText(),
        )
    }

    @Test
    fun requestIdsIncrementAndEveryCallCarriesTheMeta() {
        val transport = gateway()
        val mcp = client(transport)
        mcp.ping()
        mcp.ping()
        assertEquals(2, transport.requests.size)
        val first = TemperaJson.parse(transport.requests[0].body!!)
        val second = TemperaJson.parse(transport.requests[1].body!!)
        assertEquals(TemperaJson.Int64(1), first?.get("id"))
        assertEquals(TemperaJson.Int64(2), second?.get("id"))
        assertEquals(TemperaJson.Text("ping"), first?.get("method"))
        assertEquals(
            TemperaJson.Text(version),
            first?.get("params")?.get("_meta")?.get("io.modelcontextprotocol/protocolVersion"),
        )
        assertEquals(
            TemperaJson.Obj(emptyList()),
            first?.get("params")?.get("_meta")?.get("io.modelcontextprotocol/clientCapabilities"),
        )
    }

    @Test
    fun callToolNamesTheToolAndSplicesArguments() {
        val transport = gateway()
        client(transport)
            .callTool("palette_list_traces", mapOf("tenant_id" to "t1", "limit" to 5))
        assertEquals(
            """{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{""" +
                """"name":"palette_list_traces","arguments":{"tenant_id":"t1","limit":5},""" +
                """"_meta":{"io.modelcontextprotocol/protocolVersion":"$version",""" +
                """"io.modelcontextprotocol/clientCapabilities":{}}}}""",
            transport.lastBodyText(),
        )
        assertEquals("tools/call", transport.lastRequest().header("mcp-method"))
    }

    @Test
    fun builtinToolsTargetTheirGatewayNames() {
        val transport = gateway()
        val mcp = client(transport)
        mcp.whoami()
        var body = TemperaJson.parse(transport.lastBodyText())
        assertEquals(TemperaJson.Text("tempera_whoami"), body?.get("params")?.get("name"))
        assertEquals(TemperaJson.Obj(emptyList()), body?.get("params")?.get("arguments"))

        mcp.status()
        body = TemperaJson.parse(transport.lastBodyText())
        assertEquals(TemperaJson.Text("tempera_status"), body?.get("params")?.get("name"))
    }

    @Test
    fun listToolsReturnsTheToolsArray() {
        val transport =
            gateway(
                """{"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"tempera_search","inputSchema":{}},{"name":"tempera_invoke","inputSchema":{}}]}}"""
            )
        val tools = client(transport).listTools()
        assertEquals(2, tools.size)
        assertEquals(TemperaJson.Text("tempera_search"), tools[0]["name"])

        val empty = client(gateway("""{"jsonrpc":"2.0","id":1,"result":{"tools":[]}}"""))
        assertTrue(empty.listTools().isEmpty())
    }

    @Test
    fun jsonRpcErrorsBecomeMcpErrors() {
        val planLimit = TemperaSurface.mcpErrorCodes.planLimit
        val transport =
            gateway(
                """{"jsonrpc":"2.0","id":1,"error":{"code":$planLimit,"message":"plan limit reached","data":{"metric":"mcp_invocations"}}}"""
            )
        val error = assertThrows<TemperaMcpException> { client(transport).ping() }
        assertEquals(planLimit, error.code)
        assertEquals("plan limit reached", error.detail)
        assertEquals(TemperaJson.Text("mcp_invocations"), error.data?.get("metric"))
        assertEquals("MCP error " + planLimit + ": plan limit reached", error.message)
    }

    @Test
    fun rpcEnvelopeValidationFailsClosedAndAcceptsExplicitNullResult() {
        assertSdkError("jsonrpc must be exactly 2.0") {
            client(gateway("""{"jsonrpc":"1.0","id":1,"result":null}""")).ping()
        }
        assertSdkError("response id does not match request id") {
            client(gateway("""{"jsonrpc":"2.0","id":"1","result":null}""")).ping()
        }
        for (id in listOf("1.0", "true", "null")) {
            assertSdkError("response id does not match request id") {
                client(gateway("""{"jsonrpc":"2.0","id":$id,"result":null}""")).ping()
            }
        }
        assertSdkError("response id does not match request id") { client(gateway("""{"jsonrpc":"2.0","id":9007199254740992,"result":null}""")).ping() }
        assertSdkError("response id does not match request id") {
            client(gateway("""{"jsonrpc":"2.0","id":1,"id":1,"result":null}""")).ping()
        }
        assertSdkError("exactly one result or error") {
            client(gateway("""{"jsonrpc":"2.0","id":1,"result":null,"result":null}""")).ping()
        }
        assertSdkError("exactly one result or error") {
            client(gateway("""{"jsonrpc":"2.0","id":1,"error":{"code":1,"message":"x"},"error":{"code":1,"message":"x"}}""")).ping()
        }
        assertSdkError("exactly one result or error") {
            client(gateway("""{"jsonrpc":"2.0","id":1,"result":null,"error":null}""")).ping()
        }
        assertSdkError("exactly one result or error") { client(gateway("""{"jsonrpc":"2.0","id":1}""")).ping() }
        assertSdkError("error code must be an integer") { client(gateway("""{"jsonrpc":"2.0","id":1,"error":{"code":1,"code":2,"message":"x"}}""")).ping() }
        assertSdkError("error code must be an integer") {
            client(gateway("""{"jsonrpc":"2.0","id":1,"error":{"code":"x","message":"m"}}""")).ping()
        }
        assertSdkError("jsonrpc must be exactly 2.0") {
            client(gateway("""{"jsonrpc":"2.0","jsonrpc":"2.0","id":1,"result":null}""")).ping()
        }
        assertEquals(TemperaJson.Null, client(gateway("""{"jsonrpc":"2.0","id":1,"result":null}""")).ping())
    }

    @Test
    fun listToolsFollowsOpaqueCursorsAndRejectsPartialCatalogs() {
        val transport = StubTransport { request, attempt ->
            val cursor = TemperaJson.parse(request.body!!)?.get("params")?.get("cursor")?.asString()
            val result = if (attempt == 1) {
                assertEquals(null, cursor)
                """{"tools":[{"name":"a","inputSchema":{}}],"nextCursor":"opaque-1"}"""
            } else {
                assertEquals("opaque-1", cursor)
                """{"tools":[{"name":"b","inputSchema":{}}]}"""
            }
            StubTransport.json("""{"jsonrpc":"2.0","id":$attempt,"result":$result}""")
        }
        assertEquals(listOf("a", "b"), client(transport).listTools().map { it["name"]?.asString() })

        val repeating = StubTransport { _, attempt ->
            StubTransport.json("""{"jsonrpc":"2.0","id":$attempt,"result":{"tools":[],"nextCursor":"again"}}""")
        }
        assertSdkError("repeated or empty nextCursor") { client(repeating).listTools() }
        val conflict = StubTransport { _, attempt ->
            val result = if (attempt == 1) """{"tools":[{"name":"same","inputSchema":{}}],"nextCursor":"next"}""" else """{"tools":[{"inputSchema":{},"name":"same"}]}"""
            StubTransport.json("""{"jsonrpc":"2.0","id":$attempt,"result":$result}""")
        }
        assertSdkError("duplicate tool name") { client(conflict).listTools() }
        assertSdkError("tools array") {
            client(gateway("""{"jsonrpc":"2.0","id":1,"result":{}}""")).listTools()
        }
        assertSdkError("tool must be an object") {
            client(gateway("""{"jsonrpc":"2.0","id":1,"result":{"tools":[true]}}""")).listTools()
        }
        assertSdkError("inputSchema must be an object") {
            client(gateway("""{"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"x"}]}}""")).listTools()
        }
        assertSdkError("invisible character") {
            client(gateway("""{"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"x\u202ey","inputSchema":{}}]}}""")).listTools()
        }
        assertSdkError("duplicate object key") {
            client(gateway("""{"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"x","inputSchema":{"a":[[{"x":1,"x":2}]]}}]}}""")).listTools()
        }
    }

    @Test
    fun listToolsBoundsEveryReceivedDescriptorIncludingDuplicates() {
        fun descriptors(count: Int, name: String): String =
            List(count) { """{"name":"$name","inputSchema":{}}""" }.joinToString(",")

        val overOnePage = descriptors(10_001, "same")
        assertSdkError("response byte limit") {
            client(gateway("x".repeat(1_048_577))).listTools()
        }
        assertSdkError("exceeds item limit") {
            client(gateway("""{"jsonrpc":"2.0","id":1,"result":{"tools":[$overOnePage]}}""")).listTools()
        }
        val cumulative = StubTransport { _, attempt ->
            val result =
                if (attempt == 1) """{"tools":[${List(10_000) { index -> """{"name":"unique-$index","inputSchema":{}}""" }.joinToString(",")}],"nextCursor":"more"}"""
                else """{"tools":[{"name":"later","inputSchema":{}}]}"""
            StubTransport.json("""{"jsonrpc":"2.0","id":$attempt,"result":$result}""")
        }
        assertSdkError("exceeds item limit") { client(cumulative).listTools() }

        val exact = List(10_000) { index -> """{"name":"tool-$index","inputSchema":{}}""" }.joinToString(",")
        val tools = client(gateway("""{"jsonrpc":"2.0","id":1,"result":{"tools":[$exact]}}""")).listTools()
        assertEquals(10_000, tools.size)

        val exactPages = StubTransport { _, attempt ->
            val continuation = if (attempt < 100) ",\"nextCursor\":\"cursor-$attempt\"" else ""
            StubTransport.json("""{"jsonrpc":"2.0","id":$attempt,"result":{"tools":[]$continuation}}""")
        }
        assertTrue(client(exactPages).listTools().isEmpty())
        val overPages = StubTransport { _, attempt ->
            StubTransport.json("""{"jsonrpc":"2.0","id":$attempt,"result":{"tools":[],"nextCursor":"cursor-$attempt"}}""")
        }
        assertSdkError("exceeds page limit") { client(overPages).listTools() }
    }

    @Test
    fun listToolsAcceptsExactByteBudgetsAndRejectsBeforeParsing() {
        fun page(bytes: Int, id: Int, name: String, next: String? = null): String {
            val prefix = """{"jsonrpc":"2.0","id":$id,"result":{"tools":[{"name":"$name","description":""""
            val suffix = """","inputSchema":{}}]""" + (next?.let { ",\"nextCursor\":\"$it\"" } ?: "") + "}}"
            return prefix + "x".repeat(bytes - prefix.length - suffix.length) + suffix
        }
        assertTrue(client(gateway(page(1_048_576, 1, "one"))).listTools().isNotEmpty())
        assertSdkError("response byte limit") { client(gateway(page(1_048_577, 1, "one"))).listTools() }
        val exact = StubTransport { _, attempt -> StubTransport.json(page(1_048_576, attempt, "p$attempt", if (attempt < 8) "c$attempt" else null)) }
        assertEquals(8, client(exact).listTools().size)
        val over = StubTransport { _, attempt -> StubTransport.json(page(if (attempt <= 7) 1_048_576 else if (attempt == 8) 1_047_553 else 1_024, attempt, "p$attempt", if (attempt < 9) "c$attempt" else null)) }
        assertSdkError("response byte limit") { client(over).listTools() }
        val httpError = StubTransport.always("x".repeat(1_048_577), status = 500)
        assertSdkError("response byte limit") { client(httpError).listTools() }
    }

    @Test
    fun concurrentPingsUseUniqueCorrelatedIds() {
        val ids = java.util.concurrent.ConcurrentHashMap.newKeySet<Long>()
        val transport = object : TemperaTransport {
            override fun send(request: TemperaHttpRequest): TemperaHttpResponse {
                val id = (TemperaJson.parse(request.body!!)!!["id"] as TemperaJson.Int64).value
                ids.add(id)
                return StubTransport.json("""{"jsonrpc":"2.0","id":$id,"result":{"ok":true}}""")
            }
        }
        val client = TemperaMcpClient(url = "https://api.tempera.dev/mcp", bearer = "mcp_token_1", transport = transport)
        val executor = java.util.concurrent.Executors.newFixedThreadPool(8)
        try { executor.invokeAll(List(128) { java.util.concurrent.Callable { client.ping() } }).forEach { it.get() } } finally { executor.shutdownNow() }
        assertEquals((1L..128L).toSet(), ids)
    }

    @Test
    fun httpFailuresBecomeApiErrorsLabelledWithTheRpcMethod() {
        val transport =
            StubTransport.always(
                """{"error":{"status":"PERMISSION_DENIED","message":"no mcp:invoke"}}""",
                status = 403,
            )
        val error = assertThrows<TemperaApiException> { client(transport).listTools() }
        assertEquals(403, error.status)
        assertEquals("PERMISSION_DENIED", error.code)
        assertEquals("mcpGateway", error.product)
        assertEquals("tools/list", error.operation)
        assertEquals(1, transport.attempts, "MCP POSTs are never automatically retried")
    }

    @Test
    fun credentialResolutionPrefersAnExplicitBearerThenTheMcpAudience() {
        val transport = gateway()
        val auth =
            TemperaAuth(
                TestFixtures.ISSUER,
                apiKey = "tp_fallback",
                tokens = mapOf("tempera-mcp" to TemperaTokenSet("at_mcp")),
                transport = transport,
            )
        TemperaMcpClient(auth = auth, transport = transport).ping()
        assertEquals("Bearer at_mcp", transport.lastRequest().header("authorization"))

        val bare = TemperaMcpClient(url = "https://api.tempera.dev/mcp", transport = transport)
        assertSdkError("no MCP credential") { bare.ping() }
    }

    @Test
    fun theGeneratedGatewayTablesAreAvailable() {
        assertEquals("2026-07-28", TemperaSurface.mcpProtocolVersion)
        assertEquals(-32600, TemperaSurface.mcpErrorCodes.invalidRequest)
        assertEquals(-32601, TemperaSurface.mcpErrorCodes.methodNotFound)
        assertEquals(-32602, TemperaSurface.mcpErrorCodes.invalidParams)
        assertEquals(-32603, TemperaSurface.mcpErrorCodes.internalError)
        assertFalse(TemperaSurface.mcpMethods.isEmpty())
        assertEquals("tools/call", TemperaSurface.findMcpMethod("callTool")?.rpc)
        assertTrue(TemperaSurface.mcpDescription.contains("\${issuer}/mcp"))
    }
}
