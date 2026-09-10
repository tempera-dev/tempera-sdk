import Foundation
import XCTest

@testable import TemperaSDK

final class McpTests: XCTestCase {
    private func gateway(
        _ body: String = #"{"jsonrpc":"2.0","id":1,"result":{"ok":true}}"#
    ) -> StubTransport {
        StubTransport(responder: { _, _ in
            TemperaHTTPResponse(
                status: 200,
                headers: [TemperaKeyValue(key: "content-type", value: "application/json")],
                body: Data(body.utf8)
            )
        })
    }

    private func client(_ transport: StubTransport) throws -> TemperaMcpClient {
        try TemperaMcpClient(
            url: "https://api.tempera.dev/mcp", bearer: "mcp_token_1", transport: transport)
    }

    func testTheGatewayUrlDefaultsToTheIssuersMcpPath() async throws {
        let auth = try TemperaAuth(issuerUrl: TestFixtures.issuer, apiKey: TestFixtures.apiKey)
        let mcp = try TemperaMcpClient(auth: auth, transport: StubTransport())
        XCTAssertEqual(mcp.url, "\(TestFixtures.issuer)/mcp")
        XCTAssertThrowsError(try TemperaMcpClient(transport: StubTransport()))
    }

    func testInitializeUsesTheStatelessDiscoveryLifecycle() async throws {
        let transport = gateway()
        let mcp = try client(transport)
        try await mcp.initialize()

        let request = try await lastRequest(transport)
        XCTAssertEqual(request.method, "POST")
        XCTAssertEqual(request.url, "https://api.tempera.dev/mcp")
        XCTAssertEqual(request.header("authorization"), "Bearer mcp_token_1")
        XCTAssertEqual(request.header("content-type"), "application/json")
        // The stateless gateway speaks server/discover, not initialize.
        XCTAssertEqual(request.header("mcp-method"), "server/discover")
        XCTAssertEqual(
            request.header("mcp-protocol-version"), TemperaSurface.mcpProtocolVersion)

        let body = String(data: try XCTUnwrap(request.body), encoding: .utf8)
        XCTAssertEqual(
            body,
            #"{"jsonrpc":"2.0","id":1,"method":"server/discover","params":{"_meta":{"#
                + #""io.modelcontextprotocol/clientInfo":{"name":"tempera-sdk","version":"0.13.0"},"#
                + #""io.modelcontextprotocol/protocolVersion":"\#(TemperaSurface.mcpProtocolVersion)","#
                + #""io.modelcontextprotocol/clientCapabilities":{}}}}"#
        )
    }

    func testRequestIdsIncrementAndEveryCallCarriesTheMeta() async throws {
        let transport = gateway()
        let mcp = try client(transport)
        try await mcp.ping()
        try await mcp.ping()
        let requests = await transport.requests
        XCTAssertEqual(requests.count, 2)
        let first = TemperaJSON.parse(try XCTUnwrap(requests[0].body))
        let second = TemperaJSON.parse(try XCTUnwrap(requests[1].body))
        XCTAssertEqual(first?["id"], .int(1))
        XCTAssertEqual(second?["id"], .int(2))
        XCTAssertEqual(first?["method"], .string("ping"))
        XCTAssertEqual(
            first?["params"]?["_meta"]?["io.modelcontextprotocol/protocolVersion"],
            .string(TemperaSurface.mcpProtocolVersion)
        )
        XCTAssertEqual(
            first?["params"]?["_meta"]?["io.modelcontextprotocol/clientCapabilities"],
            .object([])
        )
    }

    func testCallToolNamesTheToolAndSplicesArguments() async throws {
        let transport = gateway()
        let mcp = try client(transport)
        try await mcp.callTool(
            "palette_list_traces",
            arguments: [
                TemperaJSONMember("tenant_id", .string("t1")),
                TemperaJSONMember("limit", .int(5)),
            ]
        )
        let body = try await lastBodyText(transport)
        XCTAssertEqual(
            body,
            #"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"#
                + #""name":"palette_list_traces","arguments":{"tenant_id":"t1","limit":5},"#
                + #""_meta":{"io.modelcontextprotocol/protocolVersion":"\#(TemperaSurface.mcpProtocolVersion)","#
                + #""io.modelcontextprotocol/clientCapabilities":{}}}}"#
        )
        let recorded = try await lastRequest(transport)
        XCTAssertEqual(recorded.header("mcp-method"), "tools/call")
    }

    func testBuiltinToolsTargetTheirGatewayNames() async throws {
        let transport = gateway()
        let mcp = try client(transport)
        try await mcp.whoami()
        var body = TemperaJSON.parse(try await lastBodyText(transport))
        XCTAssertEqual(body?["params"]?["name"], .string("tempera_whoami"))
        XCTAssertEqual(body?["params"]?["arguments"], .object([]))

        try await mcp.status()
        body = TemperaJSON.parse(try await lastBodyText(transport))
        XCTAssertEqual(body?["params"]?["name"], .string("tempera_status"))
    }

    func testListToolsReturnsTheToolsArray() async throws {
        let transport = gateway(
            #"{"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"tempera_search"},{"name":"tempera_invoke"}]}}"#
        )
        let mcp = try client(transport)
        let tools = try await mcp.listTools()
        XCTAssertEqual(tools.count, 2)
        XCTAssertEqual(tools.first?["name"], .string("tempera_search"))

        let empty = try client(gateway(#"{"jsonrpc":"2.0","id":1,"result":{}}"#))
        let none = try await empty.listTools()
        XCTAssertTrue(none.isEmpty)
    }

    func testJsonRpcErrorsBecomeMcpErrors() async throws {
        let planLimit = TemperaSurface.mcpErrorCodes.planLimit
        let transport = gateway(
            #"{"jsonrpc":"2.0","id":1,"error":{"code":\#(planLimit),"message":"plan limit reached","data":{"metric":"mcp_invocations"}}}"#
        )
        let mcp = try client(transport)
        do {
            try await mcp.ping()
            XCTFail("expected a TemperaMcpError")
        } catch let error as TemperaMcpError {
            XCTAssertEqual(error.code, planLimit)
            XCTAssertEqual(error.message, "plan limit reached")
            XCTAssertEqual(error.data?["metric"], .string("mcp_invocations"))
            XCTAssertEqual(error.description, "MCP error \(planLimit): plan limit reached")
        }
    }

    func testNonConformantErrorsAreHandledUniformly() async throws {
        // A string error becomes code 0 with its own text.
        do {
            try await client(gateway(#"{"error":"nope"}"#)).ping()
            XCTFail("expected a TemperaMcpError")
        } catch let error as TemperaMcpError {
            XCTAssertEqual(error.code, 0)
            XCTAssertEqual(error.message, "nope")
        }
        // An object without an integer code keeps its message, code 0.
        do {
            try await client(gateway(#"{"error":{"code":"x","message":"m"}}"#)).ping()
            XCTFail("expected a TemperaMcpError")
        } catch let error as TemperaMcpError {
            XCTAssertEqual(error.code, 0)
            XCTAssertEqual(error.message, "m")
        }
        // An object with neither gets the shared label.
        do {
            try await client(gateway(#"{"error":{}}"#)).ping()
            XCTFail("expected a TemperaMcpError")
        } catch let error as TemperaMcpError {
            XCTAssertEqual(error.message, "MCP error")
        }
        // A null error is not an error.
        let result = try await client(gateway(#"{"error":null,"result":{"ok":true}}"#)).ping()
        XCTAssertEqual(result["ok"], .bool(true))
    }

    func testHttpFailuresBecomeApiErrorsLabelledWithTheRpcMethod() async throws {
        let transport = StubTransport(responder: { _, _ in
            TemperaHTTPResponse(
                status: 403,
                headers: [TemperaKeyValue(key: "content-type", value: "application/json")],
                body: Data(#"{"error":{"status":"PERMISSION_DENIED","message":"no mcp:invoke"}}"#.utf8)
            )
        })
        do {
            try await client(transport).listTools()
            XCTFail("expected a TemperaApiError")
        } catch let error as TemperaApiError {
            XCTAssertEqual(error.status, 403)
            XCTAssertEqual(error.code, "PERMISSION_DENIED")
            XCTAssertEqual(error.product, "mcpGateway")
            XCTAssertEqual(error.operation, "tools/list")
        }
    }

    func testCredentialResolutionPrefersAnExplicitBearerThenTheMcpAudience() async throws {
        let transport = gateway()
        let auth = try TemperaAuth(
            issuerUrl: TestFixtures.issuer,
            apiKey: "tp_fallback",
            tokens: ["tempera-mcp": TemperaTokenSet(accessToken: "at_mcp")],
            transport: transport
        )
        let fromAuth = try TemperaMcpClient(auth: auth, transport: transport)
        try await fromAuth.ping()
        let authorized = try await lastRequest(transport)
        XCTAssertEqual(authorized.header("authorization"), "Bearer at_mcp")

        let bare = try TemperaMcpClient(url: "https://api.tempera.dev/mcp", transport: transport)
        await assertSdkError("no MCP credential") {
            _ = try await bare.ping()
        }
    }

    func testTheGeneratedGatewayTablesAreAvailable() {
        XCTAssertEqual(TemperaSurface.mcpProtocolVersion, "2026-07-28")
        XCTAssertEqual(TemperaSurface.mcpErrorCodes.invalidRequest, -32600)
        XCTAssertEqual(TemperaSurface.mcpErrorCodes.methodNotFound, -32601)
        XCTAssertEqual(TemperaSurface.mcpErrorCodes.invalidParams, -32602)
        XCTAssertEqual(TemperaSurface.mcpErrorCodes.internalError, -32603)
        XCTAssertFalse(TemperaSurface.mcpMethods.isEmpty)
        XCTAssertEqual(TemperaSurface.findMcpMethod(id: "callTool")?.rpc, "tools/call")
        XCTAssertTrue(TemperaSurface.mcpDescription.contains("${issuer}/mcp"))
    }
}
