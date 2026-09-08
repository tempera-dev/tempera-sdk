import Foundation
import XCTest

@testable import TemperaSDK

/// The five behaviours the per-language conformance suites assert, plus the
/// auth kinds and base-URL precedence.
final class ClientDispatchTests: XCTestCase {

    // MARK: - 1. Parameter normalization

    func testSnakeCaseAliasesEmitOnlyCanonicalWireNames() async throws {
        let transport = StubTransport()
        let client = try TestFixtures.client(transport: transport)
        try await client.temperaGym.call(
            "listRuns",
            [
                "environment_id": "env-1",
                "page_size": 8,
                "page_token": "runs-token",
            ]
        )
        let parts = try await lastParts(transport)
        XCTAssertEqual(parts.query["environmentId"], "env-1")
        XCTAssertEqual(parts.query["pageSize"], "8")
        XCTAssertEqual(parts.query["pageToken"], "runs-token")
        XCTAssertNil(parts.query["environment_id"])
        XCTAssertNil(parts.query["page_size"])
        XCTAssertNil(parts.query["page_token"])
    }

    func testCanonicalAndSnakeCaseSpellingsCannotBothBeSupplied() async throws {
        let transport = StubTransport()
        let client = try TestFixtures.client(transport: transport)
        await assertSdkError("not both") {
            try await client.temperaGym.call(
                "listRuns", ["environmentId": "env-1", "environment_id": "env-1"])
        }
        let requests = await transport.requests
        XCTAssertTrue(requests.isEmpty, "a rejected call never reaches the transport")
    }

    func testSnakeCaseRuleMatchesTheOtherPackages() {
        XCTAssertEqual(temperaSnakeCase("pageSize"), "page_size")
        XCTAssertEqual(temperaSnakeCase("mcpPrepareReceiptDigest"), "mcp_prepare_receipt_digest")
        XCTAssertEqual(temperaSnakeCase("tenantId"), "tenant_id")
        XCTAssertEqual(temperaSnakeCase("parent"), "parent")
        XCTAssertEqual(temperaSnakeCase("project_id"), "project_id")
    }

    // MARK: - 2. forbiddenBody rejection

    /// No shipped operation declares `forbiddenBody` yet, so the rule is
    /// exercised against a spec built from the same generated type. The
    /// producer contract for it is Remi's principal-derived identifiers.
    private func principalDerivedOperation() -> TemperaOperationSpec {
        TemperaOperationSpec(
            product: "remi",
            id: "createMemory",
            upstreamOperationId: "memories.create",
            method: "POST",
            path: "/v1/memories",
            auth: "product",
            authAudience: nil,
            pathParams: [],
            pathParamTemplates: [],
            query: [],
            requiredQuery: [],
            headers: [],
            requiredHeaders: [],
            body: ["content"],
            forbiddenBody: ["userId"],
            requiredBody: ["content"],
            bodyDefaults: [TemperaKeyValue(key: "source", value: "sdk")],
            requestBodyKind: "json",
            requestContentType: "application/json",
            scope: "memory:write",
            physicalAction: false,
            prepareCommitRequired: false,
            safeRetry: "none",
            description: "Create one memory."
        )
    }

    func testForbiddenBodyParametersAreRejected() async throws {
        let transport = StubTransport()
        let client = try TestFixtures.client(transport: transport)
        let op = principalDerivedOperation()

        await assertSdkError("derived from the authenticated principal") {
            _ = try await client.buildRequest(op, params: ["content": "hi", "userId": "u_1"])
        }
        // The snake_case alias is the same parameter, so it is rejected too.
        await assertSdkError("derived from the authenticated principal") {
            _ = try await client.buildRequest(op, params: ["content": "hi", "user_id": "u_1"])
        }

        // Without it, the request is built and the body default survives.
        let request = try await client.buildRequest(op, params: ["content": "hi"])
        let parts = RequestParts(request)
        XCTAssertEqual(parts.body?["content"], .string("hi"))
        XCTAssertEqual(parts.body?["source"], .string("sdk"))
        XCTAssertEqual(parts.headers["content-type"], "application/json")
    }

    // MARK: - 3. pathParamTemplates validation

    func testAipResourcePatternsAreValidatedAndOnlyStarSegmentsAreEncoded() async throws {
        let transport = StubTransport()
        let client = try TestFixtures.client(transport: transport)

        try await client.dataEngine.call("listUseCases", ["parent": "projects/project_1"])
        var parts = try await lastParts(transport)
        XCTAssertEqual(parts.path, "/v1/projects/project_1/use-cases")

        // Only the `*` segment is percent-encoded; the pattern's own slash is
        // structural and survives.
        await transport.clear()
        try await client.dataEngine.call("listUseCases", ["parent": "projects/a b"])
        parts = try await lastParts(transport)
        XCTAssertEqual(parts.path, "/v1/projects/a%20b/use-cases")

        for invalid in [
            "project_1",  // too few segments
            "projects/project_1/extra",  // too many segments
            "folders/project_1",  // wrong literal
            "projects/",  // empty * segment
            "projects/.",  // dot segment
            "projects/..",  // dot-dot segment
        ] {
            await assertSdkError("must match AIP resource pattern \"projects/*\"") {
                try await client.dataEngine.call("listUseCases", ["parent": .string(invalid)])
            }
        }
    }

    func testPathParametersWithoutATemplateArePercentEncodedWhole() async throws {
        let transport = StubTransport()
        let client = try TestFixtures.client(transport: transport)
        try await client.palette.call("listTraces", ["tenantId": "acme/eu"])
        let parts = try await lastParts(transport)
        XCTAssertEqual(parts.path, "/v1/traces/acme%2Feu")
    }

    func testMissingPathParametersFailFast() async throws {
        let transport = StubTransport()
        let client = try TestFixtures.client(transport: transport)
        await assertSdkError("missing required path parameter \"tenantId\"") {
            try await client.palette.call("listTraces")
        }
        await assertSdkError("missing required path parameter \"tenantId\"") {
            try await client.palette.call("listTraces", ["tenantId": ""])
        }
    }

    func testRequiredQueryParametersFailFastWithCanonicalNames() async throws {
        let transport = StubTransport()
        let client = try TestFixtures.client(transport: transport)
        let located: TemperaParams = ["tenantId": "acme", "projectId": "p1"]
        var missing = located
        await assertSdkError("missing required query parameter \"toolkit\"") {
            try await client.palette.call("connectorsGetSkills", located)
        }
        missing.set("toolkit", "")
        await assertSdkError("missing required query parameter \"toolkit\"") {
            try await client.palette.call("connectorsGetSkills", missing)
        }
        var supplied = located
        supplied.set("toolkit", "slack")
        try await client.palette.call("connectorsGetSkills", supplied)
        let parts = try await lastParts(transport)
        XCTAssertEqual(parts.query["toolkit"], "slack")
    }

    // MARK: - 4. Forward-compatible spill

    func testUndeclaredParametersSpillToQueryOnReadsAndBodyOnWrites() async throws {
        let transport = StubTransport()
        let client = try TestFixtures.client(transport: transport)

        // GET: undeclared parameters join the query string.
        try await client.palette.call(
            "listTraces", ["tenantId": "acme", "brandNewFilter": "yes", "limitish": 5])
        var parts = try await lastParts(transport)
        XCTAssertEqual(parts.query["brandNewFilter"], "yes")
        XCTAssertEqual(parts.query["limitish"], "5")
        XCTAssertNil(parts.rawBody)

        // POST: undeclared parameters join the JSON body.
        await transport.clear()
        try await client.controlPlane.call(
            "createHostedSession",
            [
                "email": "dev@example.test",
                "password": "hunter2",
                "brandNewField": ["nested": true],
            ]
        )
        parts = try await lastParts(transport)
        XCTAssertEqual(parts.body?["email"], .string("dev@example.test"))
        XCTAssertEqual(parts.body?["brandNewField"]?["nested"], .bool(true))

        // DELETE behaves like GET.
        await transport.clear()
        let deleteOp = try XCTUnwrap(
            TemperaSurface.operations.first { $0.method == "DELETE" && $0.pathParams.isEmpty }
                ?? TemperaSurface.operations.first { $0.method == "DELETE" })
        var params = TemperaParams()
        for name in deleteOp.pathParams {
            params.set(name, .string(TestFixtures.pathParam(deleteOp, name)))
        }
        for name in deleteOp.requiredQuery { params.set(name, "x") }
        params.set("brandNewFilter", "yes")
        let request = try await client.buildRequest(deleteOp, params: params)
        XCTAssertEqual(RequestParts(request).query["brandNewFilter"], "yes")
    }

    func testJsonRequestBodiesUseTheCompactWireShape() async throws {
        let transport = StubTransport()
        let client = try TestFixtures.client(transport: transport)
        try await client.controlPlane.call(
            "createHostedSession",
            ["mode": "login", "email": "dev@example.test", "password": "hunter2"]
        )
        let request = try await lastRequest(transport)
        let raw = String(data: try XCTUnwrap(request.body), encoding: .utf8)
        XCTAssertEqual(
            raw,
            #"{"mode":"login","email":"dev@example.test","password":"hunter2"}"#
        )
    }

    func testBinaryOperationsSendRawContentWithTheProducerContentType() async throws {
        let transport = StubTransport()
        let client = try TestFixtures.client(transport: transport)
        let op = try XCTUnwrap(
            TemperaSurface.operations.first { $0.requestBodyKind == "binary" })
        var params = TemperaParams()
        for name in op.pathParams { params.set(name, .string(TestFixtures.pathParam(op, name))) }

        let request = try await client.buildRequest(op, params: params, content: Data([9, 8, 7]))
        XCTAssertEqual(request.body, Data([9, 8, 7]))
        XCTAssertEqual(RequestParts(request).headers["content-type"], op.requestContentType)

        await assertSdkError("missing binary content") {
            _ = try await client.buildRequest(op, params: params)
        }
        params.set("brandNewField", "no")
        await assertSdkError("binary operations only accept content") {
            _ = try await client.buildRequest(op, params: params, content: Data([1]))
        }
    }

    // MARK: - Auth kinds

    func testEveryAuthKindResolvesItsOwnCredential() async throws {
        let transport = StubTransport()
        let client = try TestFixtures.client(transport: transport)

        // none
        try await client.controlPlane.call("health")
        var parts = try await lastParts(transport)
        XCTAssertNil(parts.headers["authorization"])

        // account
        await transport.clear()
        try await client.controlPlane.call("me")
        parts = try await lastParts(transport)
        XCTAssertEqual(parts.headers["authorization"], "Bearer \(TestFixtures.accountToken)")

        // introspectionSecret
        await transport.clear()
        try await client.controlPlane.call("introspectToken", ["token": "tok"])
        parts = try await lastParts(transport)
        XCTAssertEqual(
            parts.headers["authorization"], "Bearer \(TestFixtures.introspectionSecret)")

        // product and oauthResource both fall back to the tp_ API key.
        await transport.clear()
        try await client.palette.call("listTraces", ["tenantId": "acme"])
        parts = try await lastParts(transport)
        XCTAssertEqual(parts.headers["authorization"], "Bearer \(TestFixtures.apiKey)")

        await transport.clear()
        try await client.temperaGym.call("listRuns")
        parts = try await lastParts(transport)
        XCTAssertEqual(parts.headers["authorization"], "Bearer \(TestFixtures.apiKey)")
    }

    func testAudienceMatchedBearersWinOverTheApiKeyFallback() async throws {
        let transport = StubTransport()
        let auth = try TemperaAuth(
            issuerUrl: TestFixtures.issuer,
            apiKey: TestFixtures.apiKey,
            tokens: ["tempera-gym": TemperaTokenSet(accessToken: "at_gym")],
            transport: transport
        )
        let client = try TestFixtures.client(transport: transport, auth: auth)

        try await client.temperaGym.call("listRuns")
        var parts = try await lastParts(transport)
        XCTAssertEqual(parts.headers["authorization"], "Bearer at_gym")

        await transport.clear()
        try await client.palette.call("listTraces", ["tenantId": "acme"])
        parts = try await lastParts(transport)
        XCTAssertEqual(parts.headers["authorization"], "Bearer \(TestFixtures.apiKey)")
    }

    func testMissingCredentialsFailWithGuidance() async throws {
        let transport = StubTransport()
        let bare = try TemperaClient(
            baseUrls: TestFixtures.baseUrls(), transport: transport, processEnvironment: [:])
        await assertSdkError("an account token is required") {
            try await bare.controlPlane.call("me")
        }
        await assertSdkError("pass a TemperaAuth with credentials permitted for audience palette") {
            try await bare.palette.call("listTraces", ["tenantId": "acme"])
        }
        await assertSdkError("introspectToken requires the introspectionSecret option") {
            try await bare.controlPlane.call("introspectToken", ["token": "tok"])
        }
        await assertSdkError(
            "pass a TemperaAuth with credentials permitted for audience tempera-gym"
        ) {
            try await bare.temperaGym.call("listRuns")
        }
    }

    func testCreateHostedSessionStoresTheAccountTokenForLaterCalls() async throws {
        let transport = StubTransport(responder: { request, _ in
            if request.url.hasSuffix("/v1/sessions") {
                return TemperaHTTPResponse(
                    status: 200,
                    headers: [TemperaKeyValue(key: "content-type", value: "application/json")],
                    body: Data(#"{"access_token":"acct_from_session"}"#.utf8)
                )
            }
            return TemperaHTTPResponse(
                status: 200,
                headers: [TemperaKeyValue(key: "content-type", value: "application/json")],
                body: Data(#"{"ok":true}"#.utf8)
            )
        })
        let client = try TestFixtures.client(transport: transport, accountToken: nil)

        await assertSdkError("an account token is required") {
            try await client.controlPlane.call("me")
        }
        try await client.controlPlane.call(
            "createHostedSession", ["email": "dev@example.test", "password": "hunter2"])
        let stored = await client.accountToken
        XCTAssertEqual(stored, "acct_from_session")

        await transport.clear()
        try await client.controlPlane.call("me")
        let parts = try await lastParts(transport)
        XCTAssertEqual(parts.headers["authorization"], "Bearer acct_from_session")
    }

    // MARK: - Base URL precedence

    func testBaseUrlPrecedenceIsOverrideThenEnvironmentVariableThenPreset() async throws {
        let transport = StubTransport()
        let envVar = try XCTUnwrap(TemperaSurface.findProduct(key: "palette")?.envVar)

        // 1. An explicit override wins over everything.
        let overridden = try TemperaClient(
            auth: try TemperaAuth(issuerUrl: TestFixtures.issuer, apiKey: TestFixtures.apiKey),
            baseUrls: ["palette": "https://override.example.test/"],
            environment: "staging",
            transport: transport,
            processEnvironment: [envVar: "https://from-env.example.test"]
        )
        let overrideUrl = try await overridden.baseUrl(for: "palette")
        XCTAssertEqual(overrideUrl, "https://override.example.test")

        // 2. Without an override, the product's environment variable wins over
        //    the environment preset.
        let fromEnv = try TemperaClient(
            environment: "staging",
            transport: transport,
            processEnvironment: [envVar: "https://from-env.example.test"]
        )
        let envUrl = try await fromEnv.baseUrl(for: "palette")
        XCTAssertEqual(envUrl, "https://from-env.example.test")

        // 3. With neither, the environment preset supplies it.
        let preset = try XCTUnwrap(TemperaSurface.findEnvironment("staging"))
        let fromPreset = try TemperaClient(
            environment: "staging", transport: transport, processEnvironment: [:])
        let presetPalette = try await fromPreset.baseUrl(for: "palette")
        XCTAssertEqual(presetPalette, temperaTrimTrailingSlashes(preset.paletteApiUrl))
        let presetControlPlane = try await fromPreset.baseUrl(for: "controlPlane")
        XCTAssertEqual(presetControlPlane, temperaTrimTrailingSlashes(preset.controlPlaneUrl))

        // 4. A product the preset does not cover still needs a URL.
        let bare = try TemperaClient(
            environment: "staging", transport: transport, processEnvironment: [:])
        await assertSdkError("missing base URL for arrha") {
            _ = try await bare.baseUrl(for: "arrha")
        }
    }

    func testUnknownEnvironmentIsRejected() {
        XCTAssertThrowsError(try TemperaClient(environment: "moon")) { error in
            XCTAssertEqual(
                (error as? TemperaSdkError)?.message, "unknown Tempera environment: moon")
        }
    }

    func testUnknownProductAndOperationAreRejected() async throws {
        let transport = StubTransport()
        let client = try TestFixtures.client(transport: transport)
        await assertSdkError("unknown Tempera operation: palette.nope") {
            try await client.palette.call("nope")
        }
        await assertSdkError("unknown Tempera product: nope") {
            _ = try client.product("nope")
        }
    }

    // MARK: - Passthrough

    func testPassthroughRequestCarriesBearerQueryAndBody() async throws {
        let transport = StubTransport()
        let client = try TestFixtures.client(transport: transport)
        try await client.tempo.request(
            "custom/echo",
            method: "POST",
            body: ["hello": "world"],
            query: [TemperaKeyValue(key: "dry", value: "true")],
            headers: ["x-trace": "t-1"]
        )
        let parts = try await lastParts(transport)
        XCTAssertEqual(parts.method, "POST")
        XCTAssertEqual(parts.path, "/custom/echo")
        XCTAssertEqual(parts.query["dry"], "true")
        XCTAssertEqual(parts.headers["authorization"], "Bearer \(TestFixtures.apiKey)")
        XCTAssertEqual(parts.headers["x-trace"], "t-1")
        XCTAssertEqual(parts.body?["hello"], .string("world"))
    }

    func testCallerHeadersOverrideGeneratedOnes() async throws {
        let transport = StubTransport()
        let client = try TestFixtures.client(transport: transport)
        try await client.palette.call(
            "listTraces", ["tenantId": "acme"], headers: ["authorization": "Bearer explicit"])
        let parts = try await lastParts(transport)
        XCTAssertEqual(parts.headers["authorization"], "Bearer explicit")
    }

    func testExplicitBearerOverridesTheResolvedCredential() async throws {
        let transport = StubTransport()
        let client = try TestFixtures.client(transport: transport)
        try await client.palette.call("listTraces", ["tenantId": "acme"], bearer: "override_1")
        let parts = try await lastParts(transport)
        XCTAssertEqual(parts.headers["authorization"], "Bearer override_1")
    }

    // MARK: - Idempotency keys

    func testMalformedIdempotencyKeysAreRejectedBeforeTheFirstAttempt() async throws {
        let transport = StubTransport()
        let client = try TestFixtures.client(transport: transport)
        await assertSdkError("must be 1-256 ASCII-graphic bytes") {
            try await client.controlPlane.call(
                "createCreditTopup", ["packId": "pack_1", "idempotencyKey": "has space"])
        }
        let requests = await transport.requests
        XCTAssertTrue(requests.isEmpty)

        try await client.controlPlane.call(
            "createCreditTopup", ["packId": "pack_1", "idempotencyKey": "Request-1._~"])
        let parts = try await lastParts(transport)
        XCTAssertEqual(parts.body?["idempotencyKey"], .string("Request-1._~"))
    }
}
