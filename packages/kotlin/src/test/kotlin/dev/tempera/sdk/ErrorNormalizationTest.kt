package dev.tempera.sdk

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows

/**
 * Behaviour 5: the `google.rpc.Status` cascade every product error folds into,
 * mirroring `packages/rust/src/error.rs::normalize_error_body` and
 * `test_http_errors_normalize_every_fleet_wire_shape` in the Python suite.
 */
class ErrorNormalizationTest {

    private fun normalize(body: String, statusText: String = ""): TemperaNormalizedError =
        TemperaApiException.normalize(TemperaJson.parse(body), statusText)

    @Test
    fun canonicalAip193EnvelopePrefersTheStringStatusOverTheIntegerCode() {
        val normalized =
            normalize(
                """
                {"error": {"code": 400, "status": "INVALID_ARGUMENT", "message": "Bad envelope.",
                 "requestId": "req-de-1",
                 "details": [{"@type": "type.googleapis.com/google.rpc.ErrorInfo",
                              "reason": "MALFORMED_ENVELOPE", "domain": "data-engine"}]}}
                """,
                "Bad Request",
            )
        assertEquals("INVALID_ARGUMENT", normalized.code)
        assertEquals("Bad envelope.", normalized.message)
        assertEquals("MALFORMED_ENVELOPE", normalized.reason)
        assertEquals("req-de-1", normalized.requestId)
    }

    @Test
    fun integerCodeAloneNeverBecomesTheCode() {
        // `error.code` counts only when it is a string; an integer code is the
        // HTTP status repeated, which callers must not branch on.
        val normalized = normalize("""{"error":{"code":404,"message":"gone"}}""", "Not Found")
        assertNull(normalized.code)
        assertEquals("gone", normalized.message)
    }

    @Test
    fun legacyNestedShapeExtractsCodeMessageAndRequestId() {
        val normalized =
            normalize(
                """
                {"error": {"code": "lane_unavailable", "message": "no python lane",
                 "status": 503, "request_id": "req_123", "retryable": true}}
                """,
                "Service Unavailable",
            )
        assertEquals("lane_unavailable", normalized.code)
        assertEquals("no python lane", normalized.message)
        assertEquals("req_123", normalized.requestId)
        assertNull(normalized.reason)
    }

    @Test
    fun legacyFlatShapeUsesErrorAsCodeAndMessageAsMessage() {
        val normalized = normalize("""{"error":"invalid_token","message":"token expired"}""")
        assertEquals("invalid_token", normalized.code)
        assertEquals("token expired", normalized.message)
        assertNull(normalized.requestId)
    }

    @Test
    fun legacyMessageOnlyShapeHasNoCode() {
        val normalized = normalize("""{"error":"session is drained"}""")
        assertNull(normalized.code)
        assertEquals("session is drained", normalized.message)
    }

    @Test
    fun errorObjectWithoutAMessageFallsBackToTheStatusText() {
        val normalized = normalize("""{"error":{"code":"opaque"}}""", "Internal Server Error")
        assertEquals("opaque", normalized.code)
        assertEquals("Internal Server Error", normalized.message)
    }

    @Test
    fun unparseableAndUnknownBodiesFallBackToTheStatusText() {
        for (body in listOf("<html>bad gateway</html>", """{"error":"boom""", "", "   \n ")) {
            val normalized = normalize(body, "Bad Gateway")
            assertNull(normalized.code, body)
            assertEquals("Bad Gateway", normalized.message, body)
        }
        assertEquals("Boom", normalize("""{"ok":false}""", "Boom").message)
        assertEquals("Boom", normalize("""{"error":42}""", "Boom").message)
        assertEquals("request failed", normalize("", "").message)
    }

    @Test
    fun surrogatePairsAndEscapesSurviveNormalization() {
        val normalized =
            normalize(
                """{"error":"bad_input","message":"field \"name\" is bad\n\ttab \\ slash \/ u: é 😀"}"""
            )
        assertEquals("bad_input", normalized.code)
        assertEquals(
            "field \"name\" is bad\n\ttab \\ slash / u: é 😀",
            normalized.message,
        )
    }

    @Test
    fun requestIdFallsBackToTheXRequestIdResponseHeader() {
        val error =
            TemperaApiException.from(
                status = 500,
                statusText = "Internal Server Error",
                headers = listOf(TemperaKeyValue("X-Request-Id", "req_from_header")),
                body = TemperaJson.parse("""{"error":{"code":"boom","message":"kaput"}}"""),
                product = "palette",
                operation = "listTraces",
            )
        assertEquals("req_from_header", error.requestId)
        assertEquals("boom", error.code)
        assertEquals("Tempera palette.listTraces failed (500): kaput", error.message)

        // A body request id wins over the header.
        val fromBody =
            TemperaApiException.from(
                status = 500,
                headers = listOf(TemperaKeyValue("x-request-id", "req_from_header")),
                body =
                    TemperaJson.parse(
                        """{"error":{"message":"kaput","request_id":"req_from_body"}}"""
                    ),
            )
        assertEquals("req_from_body", fromBody.requestId)
        assertEquals("Tempera request failed (500): kaput", fromBody.message)
    }

    @Test
    fun dispatchedErrorsCarryProductAndOperationContext() {
        val transport =
            StubTransport { _, _ ->
                TemperaHttpResponse(
                    status = 404,
                    headers =
                        listOf(
                            TemperaKeyValue("content-type", "application/json"),
                            TemperaKeyValue("x-request-id", "req_1"),
                        ),
                    body =
                        """{"error":{"status":"NOT_FOUND","message":"no such trace"}}"""
                            .toByteArray(Charsets.UTF_8),
                )
            }
        val client = TestFixtures.client(transport)
        val error =
            assertThrows<TemperaApiException> {
                client.palette.call("listTraces", mapOf("tenantId" to "acme"))
            }
        assertEquals(404, error.status)
        assertEquals("NOT_FOUND", error.code)
        assertEquals("palette", error.product)
        assertEquals("listTraces", error.operation)
        assertEquals("req_1", error.requestId)
        assertEquals("Tempera palette.listTraces failed (404): no such trace", error.message)
    }

    @Test
    fun transportFailuresSurfaceAsConnectionErrors() {
        val transport =
            StubTransport { _, _ -> throw TemperaTransportException("connection reset") }
        val client = TestFixtures.client(transport)
        val error =
            assertThrows<TemperaTransportException> {
                client.palette.call("listTraces", mapOf("tenantId" to "acme"))
            }
        assertEquals("Tempera connection failed: connection reset", error.message)
        assertEquals("connection reset", error.detail)
    }
}
