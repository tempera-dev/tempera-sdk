package dev.tempera.sdk

import java.time.Instant
import java.time.ZoneOffset
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows

class RetryAndTimeoutTest {

    // ------------------------------------------------------ policy arithmetic

    @Test
    fun backoffIsExponentialFromTwoHundredFiftyMilliseconds() {
        val policy = TemperaRetryPolicy()
        // random = 1 is the top of the jitter band, i.e. the undiluted backoff.
        assertEquals(0.25, policy.delaySeconds(2, null, 1.0), 1e-9)
        assertEquals(0.5, policy.delaySeconds(3, null, 1.0), 1e-9)
        assertEquals(1.0, policy.delaySeconds(4, null, 1.0), 1e-9)
        // random = 0 is the bottom of the band: half the backoff at jitter 0.5.
        assertEquals(0.125, policy.delaySeconds(2, null, 0.0), 1e-9)
        assertEquals(0.375, policy.delaySeconds(3, null, 0.5), 1e-9)
        // The ceiling holds.
        assertEquals(policy.maxBackoffSeconds, policy.delaySeconds(20, null, 1.0), 1e-9)
    }

    @Test
    fun jitterAlwaysLandsInsideTheBand() {
        val policy = TemperaRetryPolicy()
        for (index in 0 until 200) {
            val delay = policy.delaySeconds(3, null, Math.random())
            assertTrue(delay >= 0.25, "delay " + delay)
            assertTrue(delay <= 0.5, "delay " + delay)
        }
    }

    @Test
    fun retryAfterOverridesTheBackoffAndIsClamped() {
        val policy = TemperaRetryPolicy()
        assertEquals(3.0, policy.delaySeconds(2, 3.0, 1.0), 1e-9)
        assertEquals(30.0, policy.delaySeconds(2, 600.0, 1.0), 1e-9)
        val ignoring = TemperaRetryPolicy(respectsRetryAfter = false)
        assertEquals(0.25, ignoring.delaySeconds(2, 3.0, 1.0), 1e-9)
    }

    @Test
    fun parseRetryAfterAcceptsSecondsAndHttpDates() {
        assertEquals(7.0, TemperaRetryPolicy.parseRetryAfter("7")!!)
        assertEquals(7.0, TemperaRetryPolicy.parseRetryAfter("  7 ")!!)
        assertNull(TemperaRetryPolicy.parseRetryAfter("-1"))
        assertNull(TemperaRetryPolicy.parseRetryAfter("soon"))

        val now = Instant.ofEpochSecond(1_760_000_000L)
        val header =
            DateTimeFormatter.RFC_1123_DATE_TIME.format(
                ZonedDateTime.ofInstant(now.plusSeconds(12), ZoneOffset.UTC)
            )
        val parsed = TemperaRetryPolicy.parseRetryAfter(header, now)
        assertNotNull(parsed)
        assertEquals(12.0, parsed!!, 1.0)
        // A date in the past is zero, never negative.
        val past =
            DateTimeFormatter.RFC_1123_DATE_TIME.format(
                ZonedDateTime.ofInstant(now.minusSeconds(60), ZoneOffset.UTC)
            )
        assertEquals(0.0, TemperaRetryPolicy.parseRetryAfter(past, now)!!)
    }

    @Test
    fun onlyIdempotentMethodsGetAnAttemptBudget() {
        val policy = TemperaRetryPolicy()
        assertEquals(3, policy.attemptBudget("read"))
        assertEquals(3, policy.attemptBudget("idempotent"))
        assertEquals(1, policy.attemptBudget("none"))
        for (method in listOf("GET", "HEAD", "PUT", "DELETE", "OPTIONS")) {
            assertEquals("read", TemperaRetryPolicy.safeRetryForMethod(method), method)
        }
        for (method in listOf("POST", "PATCH", "post")) {
            assertEquals("none", TemperaRetryPolicy.safeRetryForMethod(method), method)
        }
    }

    // ------------------------------------------------- retrying dispatches

    private fun failing(status: Int, times: Int, retryAfter: String? = null): StubTransport =
        StubTransport { _, attempt ->
            if (attempt <= times) {
                val headers = ArrayList<TemperaKeyValue>()
                headers.add(TemperaKeyValue("content-type", "application/json"))
                if (retryAfter != null) {
                    headers.add(TemperaKeyValue("retry-after", retryAfter))
                }
                TemperaHttpResponse(
                    status = status,
                    headers = headers,
                    body =
                        """{"error":{"status":"UNAVAILABLE","message":"try later"}}"""
                            .toByteArray(Charsets.UTF_8),
                )
            } else {
                StubTransport.json("""{"ok":true}""")
            }
        }

    @Test
    fun readOperationsRetryTheDocumentedStatuses() {
        for (status in listOf(408, 429, 500, 502, 503, 504)) {
            val transport = failing(status, 2)
            val delays = ArrayList<Double>()
            val client =
                TestFixtures.client(
                    transport,
                    sleeper = { seconds -> delays.add(seconds) },
                    random = { 1.0 },
                )
            val result = client.palette.call("listTraces", mapOf("tenantId" to "acme"))
            assertEquals(TemperaJson.Bool(true), result["ok"], "status " + status)
            assertEquals(3, transport.attempts, "status " + status)
            assertEquals(listOf(0.25, 0.5), delays, "status " + status)
        }
    }

    @Test
    fun nonRetryableStatusesAreSurfacedImmediately() {
        for (status in listOf(400, 401, 403, 404, 409, 422, 501)) {
            val transport = failing(status, 5)
            val client = TestFixtures.client(transport)
            val error =
                assertThrows<TemperaApiException> {
                    client.palette.call("listTraces", mapOf("tenantId" to "acme"))
                }
            assertEquals(status, error.status)
            assertEquals(1, transport.attempts, "status " + status)
        }
    }

    @Test
    fun nonIdempotentOperationsAreSentExactlyOnce() {
        val transport = failing(503, 5)
        val client = TestFixtures.client(transport)
        val op = TemperaSurface.findOperation("controlPlane", "createHostedSession")!!
        assertEquals("none", op.safeRetry)
        val error =
            assertThrows<TemperaApiException> {
                client.controlPlane.call(
                    "createHostedSession",
                    mapOf("email" to "dev@example.test", "password" to "hunter2"),
                )
            }
        assertEquals(503, error.status)
        assertEquals(1, transport.attempts)
    }

    @Test
    fun idempotencyKeyedWritesRetryWithTheIdenticalBody() {
        val transport = failing(503, 1)
        val client = TestFixtures.client(transport)
        val op = TemperaSurface.findOperation("controlPlane", "createCreditTopup")!!
        assertEquals("idempotent", op.safeRetry)

        client.controlPlane.call(
            "createCreditTopup",
            mapOf("packId" to "pack_1", "idempotencyKey" to "topup-1"),
        )
        assertEquals(2, transport.requests.size)
        // The retry resends the very same bytes: the key is never re-minted.
        assertTrue(transport.requests[0].body.contentEquals(transport.requests[1].body))
        assertEquals(
            TemperaJson.Text("topup-1"),
            RequestParts(transport.requests[1]).body?.get("idempotencyKey"),
        )
    }

    @Test
    fun retriesAreBoundedAndSurfaceTheLastFailure() {
        val transport = failing(503, 99)
        val client = TestFixtures.client(transport)
        val error =
            assertThrows<TemperaApiException> {
                client.palette.call("listTraces", mapOf("tenantId" to "acme"))
            }
        assertEquals(503, error.status)
        assertEquals("UNAVAILABLE", error.code)
        assertEquals(3, transport.attempts)
    }

    @Test
    fun serverNamedRetryAfterIsHonoured() {
        val transport = failing(429, 1, "2")
        val delays = ArrayList<Double>()
        val client =
            TestFixtures.client(
                transport,
                sleeper = { seconds -> delays.add(seconds) },
                random = { 1.0 },
            )
        client.palette.call("listTraces", mapOf("tenantId" to "acme"))
        assertEquals(listOf(2.0), delays)
    }

    @Test
    fun connectionFailuresRetryOnlyForSafeOperations() {
        val flaky =
            StubTransport { _, attempt ->
                if (attempt <= 1) {
                    throw TemperaTransportException("connection reset")
                }
                StubTransport.json("""{"ok":true}""")
            }
        val client = TestFixtures.client(flaky)
        client.palette.call("listTraces", mapOf("tenantId" to "acme"))
        assertEquals(2, flaky.attempts)

        val alwaysDown =
            StubTransport { _, _ -> throw TemperaTransportException("connection reset") }
        val writer = TestFixtures.client(alwaysDown)
        assertThrows<TemperaTransportException> {
            writer.controlPlane.call(
                "createHostedSession",
                mapOf("email" to "dev@example.test", "password" to "hunter2"),
            )
        }
        assertEquals(1, alwaysDown.attempts)
    }

    @Test
    fun passthroughRetriesFollowTheHttpMethod() {
        val get = failing(503, 1)
        val client = TestFixtures.client(get)
        client.tempo.request("/custom")
        assertEquals(2, get.attempts)

        val post = failing(503, 1)
        val writer = TestFixtures.client(post)
        assertThrows<TemperaApiException> {
            writer.tempo.request("/custom", method = "POST", body = temperaJsonObject("a" to 1))
        }
        assertEquals(1, post.attempts)
    }

    @Test
    fun retryCanBeDisabledEntirely() {
        val transport = failing(503, 5)
        val client =
            TestFixtures.client(
                transport,
                configuration = TemperaClientConfiguration(retry = TemperaRetryPolicy.NONE),
            )
        assertThrows<TemperaApiException> {
            client.palette.call("listTraces", mapOf("tenantId" to "acme"))
        }
        assertEquals(1, transport.attempts)
    }

    // ---------------------------------------------------------------- timeout

    @Test
    fun theDefaultTimeoutIsThirtySecondsAndIsConfigurable() {
        assertEquals(30.0, TemperaClientConfiguration.DEFAULT_TIMEOUT_SECONDS)
        assertEquals(30.0, TemperaClientConfiguration().timeoutSeconds)

        val transport = StubTransport()
        val client = TestFixtures.client(transport)
        client.palette.call("listTraces", mapOf("tenantId" to "acme"))
        assertEquals(30.0, transport.lastRequest().timeoutSeconds)

        val impatient = StubTransport()
        val quick =
            TestFixtures.client(
                impatient,
                configuration = TemperaClientConfiguration(timeoutSeconds = 2.5),
            )
        quick.palette.call("listTraces", mapOf("tenantId" to "acme"))
        assertEquals(2.5, impatient.lastRequest().timeoutSeconds)
    }

    // -------------------------------------------------- idempotency key rule

    @Test
    fun canonicalIdempotencyKeyIsExactAsciiGraphicBytes() {
        assertEquals("Request-1._~", temperaCanonicalIdempotencyKey("Request-1._~"))
        for (invalid in listOf("", "has space", "has\nnewline", "snowman-☃")) {
            assertNull(temperaCanonicalIdempotencyKey(invalid), invalid)
        }
        assertNotNull(temperaCanonicalIdempotencyKey("x".repeat(256)))
        assertNull(temperaCanonicalIdempotencyKey("x".repeat(257)))
    }
}
