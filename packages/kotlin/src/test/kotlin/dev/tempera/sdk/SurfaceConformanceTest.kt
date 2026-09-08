package dev.tempera.sdk

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

/**
 * The conformance loop: every generated operation is dispatched against a
 * stubbed transport, and the request it produces is checked field by field.
 * This mirrors `packages/python/tests/test_client.py::ConformanceTest` and the
 * Rust `builds_every_operation_in_the_surface_tables` test.
 */
class SurfaceConformanceTest {

    @Test
    fun everySurfaceOperationDispatchesMethodPathAuthAndBody() {
        val transport = StubTransport()
        val client = TestFixtures.client(transport)

        for (op in TemperaSurface.operations) {
            val label = op.product + "." + op.id
            transport.clear()

            assertTrue(op.upstreamOperationId.isNotEmpty(), label + " producer operation id")

            val params = LinkedHashMap<String, Any?>()
            for (name in op.pathParams) {
                params[name] = TestFixtures.pathParam(op, name)
            }
            for (name in op.requiredQuery) {
                params[name] = TestFixtures.SAMPLE_QUERY_VALUE
            }
            val content = if (op.requestBodyKind == "binary") byteArrayOf(1, 2, 3) else null

            val result = client.call(op.product, op.id, params, content)
            assertEquals(TemperaJson.Bool(true), result["ok"], label + " result")

            assertEquals(1, transport.requests.size, label + " made one request")
            val parts = transport.lastParts()

            assertEquals(op.method, parts.method, label + " method")
            assertEquals(TestFixtures.baseUrl(op.product), parts.origin, label + " origin")
            assertEquals(TestFixtures.expectedPath(op), parts.path, label + " path")
            assertEquals("application/json", parts.headers["accept"], label + " accept")

            val authorization = parts.headers["authorization"]
            when (op.auth) {
                "none" -> assertNull(authorization, label + " sends no bearer")
                "account" ->
                    assertEquals(
                        "Bearer " + TestFixtures.ACCOUNT_TOKEN,
                        authorization,
                        label + " account bearer",
                    )
                "introspectionSecret" ->
                    assertEquals(
                        "Bearer " + TestFixtures.INTROSPECTION_SECRET,
                        authorization,
                        label + " introspection bearer",
                    )
                else ->
                    assertEquals(
                        "Bearer " + TestFixtures.API_KEY,
                        authorization,
                        label + " product bearer",
                    )
            }

            if (op.requestBodyKind == "binary") {
                assertEquals(
                    op.requestContentType,
                    parts.headers["content-type"],
                    label + " content type",
                )
                assertTrue(
                    byteArrayOf(1, 2, 3).contentEquals(parts.rawBody),
                    label + " binary body",
                )
            } else if (op.body.isEmpty() && op.bodyDefaults.isEmpty()) {
                assertNull(parts.rawBody, label + " sends no body")
                assertNull(parts.headers["content-type"], label + " declares no content type")
            } else {
                assertEquals(
                    "application/json",
                    parts.headers["content-type"],
                    label + " content type",
                )
                for (pair in op.bodyDefaults) {
                    assertEquals(
                        TemperaJson.Text(pair.value),
                        parts.body?.get(pair.key),
                        label + " body default " + pair.key,
                    )
                }
            }

            for (key in op.requiredQuery) {
                assertEquals(
                    TestFixtures.SAMPLE_QUERY_VALUE,
                    parts.query[key],
                    label + " required query " + key,
                )
            }
        }
    }

    @Test
    fun generatedTablesMatchTheManifestShape() {
        // Counts are deliberately not hard-coded: this table is regenerated
        // every time a producer publishes a route.
        assertTrue(TemperaSurface.operations.isNotEmpty())
        assertTrue(TemperaSurface.products.isNotEmpty())
        assertTrue(TemperaSurface.environments.isNotEmpty())
        assertFalse(TemperaSurface.audiences.isEmpty())
        assertTrue(TemperaSurface.audiences.contains(TemperaSurface.defaultAudience))
        assertEquals(TemperaSurface.version, TemperaSdk.SURFACE_VERSION)
        assertEquals("0.12.0", TemperaSdk.VERSION)

        for (op in TemperaSurface.operations) {
            assertNotNull(TemperaSurface.findProduct(op.product), op.product + " is registered")
            assertNotNull(
                TemperaSurface.findOperation(op.product, op.id),
                op.product + "." + op.id + " is findable",
            )
            val audience = op.authAudience
            if (audience != null) {
                assertTrue(
                    TemperaSurface.audiences.contains(audience),
                    op.product + "." + op.id + " audience " + audience,
                )
            }
            assertTrue(
                listOf("read", "idempotent", "none").contains(op.safeRetry),
                op.product + "." + op.id + " safeRetry",
            )
            assertTrue(
                listOf("none", "account", "product", "oauthResource", "introspectionSecret")
                    .contains(op.auth),
                op.product + "." + op.id + " auth",
            )
        }

        // The flat table is partitioned by product, exactly like the Rust one.
        var counted = 0
        for (product in TemperaSurface.products) {
            counted += TemperaSurface.operationsFor(product.key).size
        }
        assertEquals(TemperaSurface.operations.size, counted)
    }

    @Test
    fun productAccessorsCoverEveryRegisteredProduct() {
        val transport = StubTransport()
        val client = TestFixtures.client(transport)
        for (spec in TemperaSurface.products) {
            val product = client.product(spec.key)
            assertEquals(spec.key, product.key)
            assertEquals(spec.envVar, product.envVar)
            assertEquals(spec.audience, product.audience)
            assertEquals(spec.description, product.description)
            assertEquals(
                TemperaSurface.operationsFor(spec.key).size,
                product.operations.size,
            )
        }
        // The generated convenience accessors resolve to the same clients.
        assertEquals("palette", client.palette.key)
        assertEquals("controlPlane", client.controlPlane.key)
        assertEquals("dataEngine", client.dataEngine.key)
        assertEquals("tempOS", client.tempOS.key)
    }
}
