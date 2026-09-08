package dev.tempera.sdk

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

/**
 * The five behaviours the per-language conformance suites assert, plus the auth
 * kinds and base-URL precedence.
 */
class ClientDispatchTest {

    // ------------------------------------------- 1. Parameter normalization

    @Test
    fun snakeCaseAliasesEmitOnlyCanonicalWireNames() {
        val transport = StubTransport()
        val client = TestFixtures.client(transport)
        client.temperaGym.call(
            "listRuns",
            mapOf(
                "environment_id" to "env-1",
                "page_size" to 8,
                "page_token" to "runs-token",
            ),
        )
        val parts = transport.lastParts()
        assertEquals("env-1", parts.query["environmentId"])
        assertEquals("8", parts.query["pageSize"])
        assertEquals("runs-token", parts.query["pageToken"])
        assertNull(parts.query["environment_id"])
        assertNull(parts.query["page_size"])
        assertNull(parts.query["page_token"])
    }

    @Test
    fun canonicalAndSnakeCaseSpellingsCannotBothBeSupplied() {
        val transport = StubTransport()
        val client = TestFixtures.client(transport)
        assertSdkError("not both") {
            client.temperaGym.call(
                "listRuns",
                mapOf("environmentId" to "env-1", "environment_id" to "env-1"),
            )
        }
        assertTrue(transport.requests.isEmpty(), "a rejected call never reaches the transport")
    }

    @Test
    fun snakeCaseRuleMatchesTheOtherPackages() {
        assertEquals("page_size", temperaSnakeCase("pageSize"))
        assertEquals("mcp_prepare_receipt_digest", temperaSnakeCase("mcpPrepareReceiptDigest"))
        assertEquals("tenant_id", temperaSnakeCase("tenantId"))
        assertEquals("parent", temperaSnakeCase("parent"))
        assertEquals("project_id", temperaSnakeCase("project_id"))
    }

    // ------------------------------------------- 2. forbiddenBody rejection

    /**
     * No shipped operation declares `forbiddenBody` yet, so the rule is
     * exercised against a spec built from the same generated type. The producer
     * contract for it is Remi's principal-derived identifiers.
     */
    private fun principalDerivedOperation(): TemperaOperationSpec =
        TemperaOperationSpec(
            product = "remi",
            id = "createMemory",
            upstreamOperationId = "memories.create",
            method = "POST",
            path = "/v1/memories",
            auth = "product",
            authAudience = null,
            pathParams = emptyList(),
            pathParamTemplates = emptyList(),
            query = emptyList(),
            requiredQuery = emptyList(),
            headers = emptyList(),
            requiredHeaders = emptyList(),
            body = listOf("content"),
            forbiddenBody = listOf("userId"),
            requiredBody = listOf("content"),
            bodyDefaults = listOf(TemperaKeyValue("source", "sdk")),
            requestBodyKind = "json",
            requestContentType = "application/json",
            scope = "memory:write",
            physicalAction = false,
            prepareCommitRequired = false,
            safeRetry = "none",
            description = "Create one memory.",
        )

    @Test
    fun forbiddenBodyParametersAreRejected() {
        val transport = StubTransport()
        val client = TestFixtures.client(transport)
        val op = principalDerivedOperation()

        assertSdkError("derived from the authenticated principal") {
            client.buildRequest(op, mapOf("content" to "hi", "userId" to "u_1"))
        }
        // The snake_case alias is the same parameter, so it is rejected too.
        assertSdkError("derived from the authenticated principal") {
            client.buildRequest(op, mapOf("content" to "hi", "user_id" to "u_1"))
        }

        // Without it, the request is built and the body default survives.
        val parts = RequestParts(client.buildRequest(op, mapOf("content" to "hi")))
        assertEquals(TemperaJson.Text("hi"), parts.body?.get("content"))
        assertEquals(TemperaJson.Text("sdk"), parts.body?.get("source"))
        assertEquals("application/json", parts.headers["content-type"])
    }

    // ---------------------------------------- 3. pathParamTemplates validation

    @Test
    fun aipResourcePatternsAreValidatedAndOnlyStarSegmentsAreEncoded() {
        val transport = StubTransport()
        val client = TestFixtures.client(transport)

        client.dataEngine.call("listUseCases", mapOf("parent" to "projects/project_1"))
        assertEquals("/v1/projects/project_1/use-cases", transport.lastParts().path)

        // Only the `*` segment is percent-encoded; the pattern's own slash is
        // structural and survives.
        transport.clear()
        client.dataEngine.call("listUseCases", mapOf("parent" to "projects/a b"))
        assertEquals("/v1/projects/a%20b/use-cases", transport.lastParts().path)

        val invalid =
            listOf(
                "project_1", // too few segments
                "projects/project_1/extra", // too many segments
                "folders/project_1", // wrong literal
                "projects/", // empty * segment
                "projects/.", // dot segment
                "projects/..", // dot-dot segment
            )
        for (value in invalid) {
            assertSdkError("must match AIP resource pattern \"projects/*\"") {
                client.dataEngine.call("listUseCases", mapOf("parent" to value))
            }
        }
    }

    @Test
    fun pathParametersWithoutATemplateArePercentEncodedWhole() {
        val transport = StubTransport()
        val client = TestFixtures.client(transport)
        client.palette.call("listTraces", mapOf("tenantId" to "acme/eu"))
        assertEquals("/v1/traces/acme%2Feu", transport.lastParts().path)
    }

    @Test
    fun missingPathParametersFailFast() {
        val transport = StubTransport()
        val client = TestFixtures.client(transport)
        assertSdkError("missing required path parameter \"tenantId\"") {
            client.palette.call("listTraces")
        }
        assertSdkError("missing required path parameter \"tenantId\"") {
            client.palette.call("listTraces", mapOf("tenantId" to ""))
        }
    }

    @Test
    fun requiredQueryParametersFailFastWithCanonicalNames() {
        val transport = StubTransport()
        val client = TestFixtures.client(transport)
        val located = mapOf("tenantId" to "acme", "projectId" to "p1")
        assertSdkError("missing required query parameter \"toolkit\"") {
            client.palette.call("connectorsGetSkills", located)
        }
        assertSdkError("missing required query parameter \"toolkit\"") {
            client.palette.call("connectorsGetSkills", located + mapOf("toolkit" to ""))
        }
        client.palette.call("connectorsGetSkills", located + mapOf("toolkit" to "slack"))
        assertEquals("slack", transport.lastParts().query["toolkit"])
    }

    // -------------------------------------------- 4. Forward-compatible spill

    @Test
    fun undeclaredParametersSpillToQueryOnReadsAndBodyOnWrites() {
        val transport = StubTransport()
        val client = TestFixtures.client(transport)

        // GET: undeclared parameters join the query string.
        client.palette.call(
            "listTraces",
            mapOf("tenantId" to "acme", "brandNewFilter" to "yes", "limitish" to 5),
        )
        var parts = transport.lastParts()
        assertEquals("yes", parts.query["brandNewFilter"])
        assertEquals("5", parts.query["limitish"])
        assertNull(parts.rawBody)

        // POST: undeclared parameters join the JSON body.
        transport.clear()
        client.controlPlane.call(
            "createHostedSession",
            mapOf(
                "email" to "dev@example.test",
                "password" to "hunter2",
                "brandNewField" to mapOf("nested" to true),
            ),
        )
        parts = transport.lastParts()
        assertEquals(TemperaJson.Text("dev@example.test"), parts.body?.get("email"))
        assertEquals(
            TemperaJson.Bool(true),
            parts.body?.get("brandNewField")?.get("nested"),
        )

        // DELETE behaves like GET.
        val deleteOp =
            TemperaSurface.operations.firstOrNull {
                it.method == "DELETE" && it.pathParams.isEmpty()
            }
                ?: TemperaSurface.operations.first { it.method == "DELETE" }
        val params = LinkedHashMap<String, Any?>()
        for (name in deleteOp.pathParams) params[name] = TestFixtures.pathParam(deleteOp, name)
        for (name in deleteOp.requiredQuery) params[name] = "x"
        params["brandNewFilter"] = "yes"
        val request = client.buildRequest(deleteOp, params)
        assertEquals("yes", RequestParts(request).query["brandNewFilter"])
    }

    @Test
    fun jsonRequestBodiesUseTheCompactWireShape() {
        val transport = StubTransport()
        val client = TestFixtures.client(transport)
        client.controlPlane.call(
            "createHostedSession",
            mapOf("mode" to "login", "email" to "dev@example.test", "password" to "hunter2"),
        )
        assertEquals(
            """{"mode":"login","email":"dev@example.test","password":"hunter2"}""",
            transport.lastBodyText(),
        )
    }

    @Test
    fun binaryOperationsSendRawContentWithTheProducerContentType() {
        val transport = StubTransport()
        val client = TestFixtures.client(transport)
        val op = TemperaSurface.operations.first { it.requestBodyKind == "binary" }
        val params = LinkedHashMap<String, Any?>()
        for (name in op.pathParams) params[name] = TestFixtures.pathParam(op, name)

        val request = client.buildRequest(op, params, byteArrayOf(9, 8, 7))
        assertTrue(byteArrayOf(9, 8, 7).contentEquals(request.body))
        assertEquals(op.requestContentType, request.header("content-type"))

        assertSdkError("missing binary content") { client.buildRequest(op, params) }
        params["brandNewField"] = "no"
        assertSdkError("binary operations only accept content") {
            client.buildRequest(op, params, byteArrayOf(1))
        }
    }

    // ------------------------------------------------------------ auth kinds

    @Test
    fun everyAuthKindResolvesItsOwnCredential() {
        val transport = StubTransport()
        val client = TestFixtures.client(transport)

        client.controlPlane.call("health")
        assertNull(transport.lastParts().headers["authorization"])

        transport.clear()
        client.controlPlane.call("me")
        assertEquals(
            "Bearer " + TestFixtures.ACCOUNT_TOKEN,
            transport.lastParts().headers["authorization"],
        )

        transport.clear()
        client.controlPlane.call("introspectToken", mapOf("token" to "tok"))
        assertEquals(
            "Bearer " + TestFixtures.INTROSPECTION_SECRET,
            transport.lastParts().headers["authorization"],
        )

        transport.clear()
        client.palette.call("listTraces", mapOf("tenantId" to "acme"))
        assertEquals(
            "Bearer " + TestFixtures.API_KEY,
            transport.lastParts().headers["authorization"],
        )

        transport.clear()
        client.temperaGym.call("listRuns")
        assertEquals(
            "Bearer " + TestFixtures.API_KEY,
            transport.lastParts().headers["authorization"],
        )
    }

    @Test
    fun audienceMatchedBearersWinOverTheApiKeyFallback() {
        val transport = StubTransport()
        val auth =
            TemperaAuth(
                TestFixtures.ISSUER,
                apiKey = TestFixtures.API_KEY,
                tokens = mapOf("tempera-gym" to TemperaTokenSet("at_gym")),
                transport = transport,
            )
        val client = TestFixtures.client(transport, auth = auth)

        client.temperaGym.call("listRuns")
        assertEquals("Bearer at_gym", transport.lastParts().headers["authorization"])

        transport.clear()
        client.palette.call("listTraces", mapOf("tenantId" to "acme"))
        assertEquals(
            "Bearer " + TestFixtures.API_KEY,
            transport.lastParts().headers["authorization"],
        )
    }

    @Test
    fun missingCredentialsFailWithGuidance() {
        val transport = StubTransport()
        val bare =
            TemperaClient(
                baseUrls = TestFixtures.baseUrls(),
                transport = transport,
                processEnvironment = emptyMap(),
            )
        assertSdkError("an account token is required") { bare.controlPlane.call("me") }
        assertSdkError("pass a TemperaAuth with credentials permitted for audience palette") {
            bare.palette.call("listTraces", mapOf("tenantId" to "acme"))
        }
        assertSdkError("introspectToken requires the introspectionSecret option") {
            bare.controlPlane.call("introspectToken", mapOf("token" to "tok"))
        }
        assertSdkError("pass a TemperaAuth with credentials permitted for audience tempera-gym") {
            bare.temperaGym.call("listRuns")
        }
    }

    @Test
    fun createHostedSessionStoresTheAccountTokenForLaterCalls() {
        val transport =
            StubTransport { request, _ ->
                if (request.url.endsWith("/v1/sessions")) {
                    StubTransport.json("""{"access_token":"acct_from_session"}""")
                } else {
                    StubTransport.json("""{"ok":true}""")
                }
            }
        val client = TestFixtures.client(transport, accountToken = null)

        assertSdkError("an account token is required") { client.controlPlane.call("me") }
        client.controlPlane.call(
            "createHostedSession",
            mapOf("email" to "dev@example.test", "password" to "hunter2"),
        )
        assertEquals("acct_from_session", client.accountToken)

        transport.clear()
        client.controlPlane.call("me")
        assertEquals(
            "Bearer acct_from_session",
            transport.lastParts().headers["authorization"],
        )
    }

    // --------------------------------------------------- base URL precedence

    @Test
    fun baseUrlPrecedenceIsOverrideThenEnvironmentVariableThenPreset() {
        val transport = StubTransport()
        val envVar = TemperaSurface.findProduct("palette")!!.envVar

        // 1. An explicit override wins over everything.
        val overridden =
            TemperaClient(
                baseUrls = mapOf("palette" to "https://override.example.test/"),
                environment = "staging",
                transport = transport,
                processEnvironment = mapOf(envVar to "https://from-env.example.test"),
            )
        assertEquals("https://override.example.test", overridden.baseUrl("palette"))

        // 2. Without an override, the product's environment variable wins over
        //    the environment preset.
        val fromEnv =
            TemperaClient(
                environment = "staging",
                transport = transport,
                processEnvironment = mapOf(envVar to "https://from-env.example.test"),
            )
        assertEquals("https://from-env.example.test", fromEnv.baseUrl("palette"))

        // 3. With neither, the environment preset supplies it.
        val preset = TemperaSurface.findEnvironment("staging")!!
        val fromPreset =
            TemperaClient(
                environment = "staging",
                transport = transport,
                processEnvironment = emptyMap(),
            )
        assertEquals(
            temperaTrimTrailingSlashes(preset.paletteApiUrl),
            fromPreset.baseUrl("palette"),
        )
        assertEquals(
            temperaTrimTrailingSlashes(preset.controlPlaneUrl),
            fromPreset.baseUrl("controlPlane"),
        )

        // 4. A product the preset does not cover still needs a URL.
        assertSdkError("missing base URL for arrha") { fromPreset.baseUrl("arrha") }
    }

    @Test
    fun unknownEnvironmentIsRejected() {
        assertSdkError("unknown Tempera environment: moon") { TemperaClient(environment = "moon") }
    }

    @Test
    fun unknownProductAndOperationAreRejected() {
        val transport = StubTransport()
        val client = TestFixtures.client(transport)
        assertSdkError("unknown Tempera operation: palette.nope") { client.palette.call("nope") }
        assertSdkError("unknown Tempera product: nope") { client.product("nope") }
    }

    // ----------------------------------------------------------- passthrough

    @Test
    fun passthroughRequestCarriesBearerQueryAndBody() {
        val transport = StubTransport()
        val client = TestFixtures.client(transport)
        client.tempo.request(
            "custom/echo",
            method = "POST",
            body = temperaJsonObject("hello" to "world"),
            query = listOf(TemperaKeyValue("dry", "true")),
            headers = mapOf("x-trace" to "t-1"),
        )
        val parts = transport.lastParts()
        assertEquals("POST", parts.method)
        assertEquals("/custom/echo", parts.path)
        assertEquals("true", parts.query["dry"])
        assertEquals("Bearer " + TestFixtures.API_KEY, parts.headers["authorization"])
        assertEquals("t-1", parts.headers["x-trace"])
        assertEquals(TemperaJson.Text("world"), parts.body?.get("hello"))
    }

    @Test
    fun callerHeadersOverrideGeneratedOnes() {
        val transport = StubTransport()
        val client = TestFixtures.client(transport)
        client.palette.call(
            "listTraces",
            mapOf("tenantId" to "acme"),
            headers = mapOf("authorization" to "Bearer explicit"),
        )
        assertEquals("Bearer explicit", transport.lastParts().headers["authorization"])
    }

    @Test
    fun explicitBearerOverridesTheResolvedCredential() {
        val transport = StubTransport()
        val client = TestFixtures.client(transport)
        client.palette.call("listTraces", mapOf("tenantId" to "acme"), bearer = "override_1")
        assertEquals("Bearer override_1", transport.lastParts().headers["authorization"])
    }

    // ------------------------------------------------------ idempotency keys

    @Test
    fun malformedIdempotencyKeysAreRejectedBeforeTheFirstAttempt() {
        val transport = StubTransport()
        val client = TestFixtures.client(transport)
        assertSdkError("must be 1-256 ASCII-graphic bytes") {
            client.controlPlane.call(
                "createCreditTopup",
                mapOf("packId" to "pack_1", "idempotencyKey" to "has space"),
            )
        }
        assertTrue(transport.requests.isEmpty())

        client.controlPlane.call(
            "createCreditTopup",
            mapOf("packId" to "pack_1", "idempotencyKey" to "Request-1._~"),
        )
        assertEquals(
            TemperaJson.Text("Request-1._~"),
            transport.lastParts().body?.get("idempotencyKey"),
        )
        assertNotNull(transport.lastRequest().body)
    }
}
