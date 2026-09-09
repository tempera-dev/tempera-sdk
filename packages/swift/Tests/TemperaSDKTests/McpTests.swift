import Foundation
import XCTest

@testable import TemperaSDK

final class McpTests: XCTestCase {
    private func gateway(
        _ body: String? = nil
    ) -> StubTransport {
        StubTransport(responder: { request, _ in
            let response = body ?? {
                let id = TemperaJSON.parse(request.body ?? Data())?["id"]?.intValue ?? -1
                return #"{"jsonrpc":"2.0","id":\#(id),"result":{"ok":true}}"#
            }()
            return TemperaHTTPResponse(
                status: 200,
                headers: [TemperaKeyValue(key: "content-type", value: "application/json")],
                body: Data(response.utf8)
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
                + #""io.modelcontextprotocol/clientInfo":{"name":"tempera-sdk","version":"0.12.0"},"#
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
            #"{"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"tempera_search","inputSchema":{}},{"name":"tempera_invoke","inputSchema":{}}]}}"#
        )
        let mcp = try client(transport)
        let tools = try await mcp.listTools()
        XCTAssertEqual(tools.count, 2)
        XCTAssertEqual(tools.first?["name"], .string("tempera_search"))

        let empty = try client(gateway(#"{"jsonrpc":"2.0","id":1,"result":{"tools":[]}}"#))
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

    func testRpcEnvelopeValidationFailsClosedAndAcceptsExplicitNullResult() async throws {
        await assertSdkError("jsonrpc must be exactly 2.0") {
            _ = try await self.client(self.gateway(#"{"jsonrpc":"1.0","id":1,"result":null}"#)).ping()
        }
        await assertSdkError("response id does not match request id") {
            _ = try await self.client(self.gateway(#"{"jsonrpc":"2.0","id":"1","result":null}"#)).ping()
        }
        for id in ["1.0", "true", "null"] {
            await assertSdkError("response id does not match request id") {
                _ = try await self.client(self.gateway(#"{"jsonrpc":"2.0","id":\#(id),"result":null}"#)).ping()
            }
        }
        await assertSdkError("response id does not match request id") { _ = try await self.client(self.gateway(#"{"jsonrpc":"2.0","id":9007199254740992,"result":null}"#)).ping() }
        await assertSdkError("response id does not match request id") {
            _ = try await self.client(self.gateway(#"{"jsonrpc":"2.0","id":1,"id":1,"result":null}"#)).ping()
        }
        await assertSdkError("exactly one result or error") {
            _ = try await self.client(self.gateway(#"{"jsonrpc":"2.0","id":1,"result":null,"result":null}"#)).ping()
        }
        await assertSdkError("exactly one result or error") {
            _ = try await self.client(self.gateway(#"{"jsonrpc":"2.0","id":1,"error":{"code":1,"message":"x"},"error":{"code":1,"message":"x"}}"#)).ping()
        }
        await assertSdkError("exactly one result or error") {
            _ = try await self.client(self.gateway(#"{"jsonrpc":"2.0","id":1,"result":null,"error":null}"#)).ping()
        }
        await assertSdkError("exactly one result or error") { _ = try await self.client(self.gateway(#"{"jsonrpc":"2.0","id":1}"#)).ping() }
        await assertSdkError("error code must be an integer") { _ = try await self.client(self.gateway(#"{"jsonrpc":"2.0","id":1,"error":{"code":1,"code":2,"message":"x"}}"#)).ping() }
        await assertSdkError("error code must be an integer") {
            _ = try await self.client(self.gateway(#"{"jsonrpc":"2.0","id":1,"error":{"code":"x","message":"m"}}"#)).ping()
        }
        await assertSdkError("jsonrpc must be exactly 2.0") {
            _ = try await self.client(self.gateway(#"{"jsonrpc":"2.0","jsonrpc":"2.0","id":1,"result":null}"#)).ping()
        }
        let result = try await client(gateway(#"{"jsonrpc":"2.0","id":1,"result":null}"#)).ping()
        XCTAssertEqual(result, .null)
    }

    func testListToolsFollowsOpaqueCursorsAndRejectsPartialCatalogs() async throws {
        let transport = StubTransport(responder: { request, attempt in
            let cursor = TemperaJSON.parse(request.body ?? Data())?["params"]?["cursor"]?.stringValue
            if attempt == 1 {
                XCTAssertNil(cursor)
                return TemperaHTTPResponse(
                    status: 200, headers: [],
                    body: Data(#"{"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"a","inputSchema":{}}],"nextCursor":"opaque-1"}}"#.utf8))
            }
            XCTAssertEqual(cursor, "opaque-1")
            return TemperaHTTPResponse(
                status: 200, headers: [],
                body: Data(#"{"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"b","inputSchema":{}}]}}"#.utf8))
        })
        let names = try await client(transport).listTools().compactMap { $0["name"]?.stringValue }
        XCTAssertEqual(names, ["a", "b"])

        let repeating = StubTransport(responder: { _, attempt in
            TemperaHTTPResponse(status: 200, headers: [], body: Data(
                #"{"jsonrpc":"2.0","id":\#(attempt),"result":{"tools":[],"nextCursor":"again"}}"#.utf8))
        })
        await assertSdkError("repeated or empty nextCursor") {
            _ = try await self.client(repeating).listTools()
        }
        let conflict = StubTransport(responder: { _, attempt in
            let result = attempt == 1
                ? #"{"tools":[{"name":"same","inputSchema":{}}],"nextCursor":"next"}"#
                : #"{"tools":[{"inputSchema":{},"name":"same"}]}"#
            return TemperaHTTPResponse(status: 200, headers: [], body: Data(
                #"{"jsonrpc":"2.0","id":\#(attempt),"result":\#(result)}"#.utf8))
        })
        await assertSdkError("duplicate tool name") {
            _ = try await self.client(conflict).listTools()
        }
        await assertSdkError("tools array") {
            _ = try await self.client(self.gateway(#"{"jsonrpc":"2.0","id":1,"result":{}}"#)).listTools()
        }
        await assertSdkError("tool must be an object") {
            _ = try await self.client(self.gateway(#"{"jsonrpc":"2.0","id":1,"result":{"tools":[true]}}"#)).listTools()
        }
        await assertSdkError("inputSchema must be an object") {
            _ = try await self.client(self.gateway(#"{"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"x"}]}}"#)).listTools()
        }
        await assertSdkError("invisible character") {
            _ = try await self.client(self.gateway(#"{"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"x\u202ey","inputSchema":{}}]}}"#)).listTools()
        }
        await assertSdkError("duplicate object key") {
            _ = try await self.client(self.gateway(#"{"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"x","inputSchema":{"a":[[{"x":1,"x":2}]]}}]}}"#)).listTools()
        }
    }

    func testListToolsBoundsEveryReceivedDescriptorIncludingDuplicates() async throws {
        func descriptors(_ count: Int, _ name: String) -> String {
            Array(repeating: #"{"name":"\#(name)","inputSchema":{}}"#, count: count).joined(separator: ",")
        }

        let overOnePage = descriptors(10_001, "same")
        let tenThousandUnique = (0..<10_000).map { #"{"name":"unique-\#($0)","inputSchema":{}}"# }.joined(separator: ",")
        await assertSdkError("response byte limit") {
            _ = try await self.client(self.gateway(String(repeating: "x", count: 1_048_577))).listTools()
        }
        await assertSdkError("exceeds item limit") {
            _ = try await self.client(self.gateway(
                #"{"jsonrpc":"2.0","id":1,"result":{"tools":[\#(overOnePage)]}}"#)).listTools()
        }
        let cumulative = StubTransport(responder: { _, attempt in
            let result = attempt == 1
                ? #"{"tools":[\#(tenThousandUnique)],"nextCursor":"more"}"#
                : #"{"tools":[{"name":"later","inputSchema":{}}]}"#
            return TemperaHTTPResponse(status: 200, headers: [], body: Data(
                #"{"jsonrpc":"2.0","id":\#(attempt),"result":\#(result)}"#.utf8))
        })
        await assertSdkError("exceeds item limit") {
            _ = try await self.client(cumulative).listTools()
        }

        let exact = (0..<10_000).map { #"{"name":"tool-\#($0)","inputSchema":{}}"# }.joined(separator: ",")
        let tools = try await client(gateway(
            #"{"jsonrpc":"2.0","id":1,"result":{"tools":[\#(exact)]}}"#)).listTools()
        XCTAssertEqual(tools.count, 10_000)

        let exactPages = StubTransport(responder: { _, attempt in
            let continuation = attempt < 100 ? ",\"nextCursor\":\"cursor-\(attempt)\"" : ""
            return TemperaHTTPResponse(status: 200, headers: [], body: Data(
                #"{"jsonrpc":"2.0","id":\#(attempt),"result":{"tools":[]\#(continuation)}}"#.utf8))
        })
        let completeCatalog = try await client(exactPages).listTools()
        XCTAssertTrue(completeCatalog.isEmpty)
        let overPages = StubTransport(responder: { _, attempt in
            TemperaHTTPResponse(status: 200, headers: [], body: Data(
                #"{"jsonrpc":"2.0","id":\#(attempt),"result":{"tools":[],"nextCursor":"cursor-\#(attempt)"}}"#.utf8))
        })
        await assertSdkError("exceeds page limit") {
            _ = try await self.client(overPages).listTools()
        }
    }

    func testListToolsAcceptsExactByteBudgetsAndRejectsBeforeParsing() async throws {
        @Sendable func page(_ bytes: Int, _ id: Int, _ name: String, _ next: String? = nil) -> String {
            let prefix = #"{"jsonrpc":"2.0","id":\#(id),"result":{"tools":[{"name":"\#(name)","description":""#
            let suffix = #"","inputSchema":{}}]"# + (next.map { ",\"nextCursor\":\"\($0)\"" } ?? "") + "}}"
            return prefix + String(repeating: "x", count: bytes - prefix.utf8.count - suffix.utf8.count) + suffix
        }
        let onePage = try await client(gateway(page(1_048_576, 1, "one"))).listTools()
        XCTAssertFalse(onePage.isEmpty)
        await assertSdkError("response byte limit") { _ = try await self.client(self.gateway(page(1_048_577, 1, "one"))).listTools() }
        let exact = StubTransport(responder: { _, attempt in TemperaHTTPResponse(status: 200, headers: [], body: Data(page(1_048_576, attempt, "p\(attempt)", attempt < 8 ? "c\(attempt)" : nil).utf8)) })
        let eightPages = try await client(exact).listTools()
        XCTAssertEqual(eightPages.count, 8)
        let over = StubTransport(responder: { _, attempt in TemperaHTTPResponse(status: 200, headers: [], body: Data(page(attempt <= 7 ? 1_048_576 : attempt == 8 ? 1_047_553 : 1_024, attempt, "p\(attempt)", attempt < 9 ? "c\(attempt)" : nil).utf8)) })
        await assertSdkError("response byte limit") { _ = try await self.client(over).listTools() }
        let error = StubTransport(responder: { _, _ in TemperaHTTPResponse(status: 500, headers: [], body: Data(String(repeating: "x", count: 1_048_577).utf8)) })
        await assertSdkError("response byte limit") { _ = try await self.client(error).listTools() }
    }

    func testConcurrentPingsUseUniqueCorrelatedIDs() async throws {
        let transport = StubTransport(responder: { request, _ in
            let id = TemperaJSON.parse(request.body ?? Data())?["id"]?.intValue ?? -1
            return TemperaHTTPResponse(status: 200, headers: [], body: Data(#"{"jsonrpc":"2.0","id":\#(id),"result":{"ok":true}}"#.utf8))
        })
        let mcp = try client(transport)
        try await withThrowingTaskGroup(of: TemperaJSON.self) { group in
            for _ in 0..<128 { group.addTask { try await mcp.ping() } }
            for try await _ in group {}
        }
        let ids = await transport.requests.compactMap { TemperaJSON.parse($0.body ?? Data())?["id"]?.intValue }
        XCTAssertEqual(Set(ids), Set(1...128))
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
        let attempts = await transport.attempts
        XCTAssertEqual(attempts, 1, "MCP POSTs are never automatically retried")
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
