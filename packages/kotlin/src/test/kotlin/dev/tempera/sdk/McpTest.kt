package dev.tempera.sdk

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows

class McpTest {
    private val version = TemperaSurface.mcpProtocolVersion

    private fun gateway(
        body: String = """{"jsonrpc":"2.0","id":1,"result":{"ok":true}}"""
    ): StubTransport = StubTransport.always(body)

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
                """{"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"tempera_search"},{"name":"tempera_invoke"}]}}"""
            )
        val tools = client(transport).listTools()
        assertEquals(2, tools.size)
        assertEquals(TemperaJson.Text("tempera_search"), tools[0]["name"])

        val empty = client(gateway("""{"jsonrpc":"2.0","id":1,"result":{}}"""))
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
    fun nonConformantErrorsAreHandledUniformly() {
        // A string error becomes code 0 with its own text.
        var error = assertThrows<TemperaMcpException> { client(gateway("""{"error":"nope"}""")).ping() }
        assertEquals(0, error.code)
        assertEquals("nope", error.detail)

        // An object without an integer code keeps its message, code 0.
        error =
            assertThrows<TemperaMcpException> {
                client(gateway("""{"error":{"code":"x","message":"m"}}""")).ping()
            }
        assertEquals(0, error.code)
        assertEquals("m", error.detail)

        // An object with neither gets the shared label.
        error = assertThrows<TemperaMcpException> { client(gateway("""{"error":{}}""")).ping() }
        assertEquals("MCP error", error.detail)

        // A null error is not an error.
        val result = client(gateway("""{"error":null,"result":{"ok":true}}""")).ping()
        assertEquals(TemperaJson.Bool(true), result["ok"])
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
