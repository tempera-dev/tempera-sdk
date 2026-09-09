package dev.tempera.sdk

import java.net.InetSocketAddress
import java.net.Proxy
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicReference
import okhttp3.Call
import okhttp3.Connection
import okhttp3.Dispatcher
import okhttp3.EventListener
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.tls.HandshakeCertificates
import okhttp3.tls.HeldCertificate
import okio.Buffer
import okio.GzipSink
import okio.buffer
import org.junit.After
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.SocketPolicy

class OkHttpTemperaTransportTest {
    private lateinit var server: MockWebServer

    @Before
    fun startServer() {
        server = MockWebServer()
        server.start()
    }

    @After
    fun stopServer() {
        server.shutdown()
    }

    @Test
    fun androidFactoryUsesTheOkHttpTransport() {
        assertTrue(defaultTemperaTransport() is OkHttpTemperaTransport)
    }

    @Test
    fun sendsOneRequestWithMethodBodyAndRepeatedHeaders() {
        server.enqueue(MockResponse().setBody("ok").addHeader("X-Reply", "a").addHeader("X-Reply", "b"))

        val response =
            transport().send(
                request(
                    method = "PATCH",
                    body = "payload".toByteArray(),
                    headers =
                        listOf(
                            TemperaKeyValue("X-Repeat", "one"),
                            TemperaKeyValue("X-Repeat", "two"),
                        ),
                )
            )

        val recorded = requireNotNull(server.takeRequest(1, TimeUnit.SECONDS))
        assertEquals("PATCH", recorded.method)
        assertEquals("payload", recorded.body.readUtf8())
        assertEquals(listOf("one", "two"), recorded.headers.values("X-Repeat"))
        assertEquals(listOf("a", "b"), response.headers.filter { it.key == "x-reply" }.map { it.value })
        assertEquals(1, server.requestCount)
    }

    @Test
    fun doesNotFollowRedirectsOrStatusFollowups() {
        val statuses = listOf(301, 302, 303, 307, 308, 401, 408, 429, 503)
        for (status in statuses) {
            val reply = MockResponse().setResponseCode(status).setBody("status-$status")
            if (status in setOf(301, 302, 303, 307, 308)) reply.addHeader("Location", "/next")
            server.enqueue(reply)
        }

        for (status in statuses) {
            val response = transport().send(request())
            assertEquals(status, response.status)
        }

        assertEquals(statuses.size, server.requestCount)
    }

    @Test
    fun directOriginProxyAuthenticationResponseIsATypedFailureWithNoResend() {
        server.enqueue(MockResponse().setResponseCode(407).setBody("origin proxy authentication"))
        server.enqueue(MockResponse().setBody("must not be requested"))

        assertThrows(TemperaTransportException::class.java) { transport().send(request()) }

        assertEquals(1, server.requestCount)
    }

    @Test
    fun actualHttpProxyReturns407WithoutAuthenticatorFollowup() {
        server.enqueue(
            MockResponse()
                .setResponseCode(407)
                .addHeader("Proxy-Authenticate", "Basic realm=local")
                .setBody("proxy authentication required")
        )
        server.enqueue(MockResponse().setBody("must not be requested"))
        val authenticatorCalls = AtomicInteger()
        val proxyClient =
            OkHttpClient.Builder()
                .proxy(Proxy(Proxy.Type.HTTP, InetSocketAddress("127.0.0.1", server.port)))
                .proxyAuthenticator { _, response ->
                    authenticatorCalls.incrementAndGet()
                    response.request.newBuilder().header("Proxy-Authorization", "test-only").build()
                }
                .build()
        val transport = OkHttpTemperaTransport(proxyClient)

        val response =
            transport.send(
                TemperaHttpRequest(
                    method = "GET",
                    url = "http://origin.example.test/resource",
                    timeoutSeconds = 2.0,
                )
            )

        val recorded = requireNotNull(server.takeRequest(1, TimeUnit.SECONDS))
        assertEquals(407, response.status)
        assertArrayEquals("proxy authentication required".toByteArray(), response.body)
        assertEquals("Basic realm=local", response.header("proxy-authenticate"))
        assertTrue(recorded.requestLine.startsWith("GET http://origin.example.test/resource "))
        assertEquals(null, recorded.getHeader("Proxy-Authorization"))
        assertEquals(0, authenticatorCalls.get())
        assertEquals(1, server.requestCount)
    }

    @Test
    fun restoresOnlyRetryAfterValuesWhileSuppressingOkHttpRetryAfterZeroFollowup() {
        server.enqueue(
            gzipResponse("unavailable")
                .setResponseCode(503)
                .addHeader("Retry-After", "5")
                .addHeader("Retry-After", "00")
                .addHeader("X-Server-Value", "unchanged")
        )
        server.enqueue(MockResponse().setBody("must not be requested"))

        val response = transport().send(request())

        assertEquals(503, response.status)
        assertEquals(listOf("5", "00"), response.headers.filter { it.key == "retry-after" }.map { it.value })
        assertEquals("unchanged", response.header("x-server-value"))
        assertArrayEquals("unavailable".toByteArray(), response.body)
        assertFalse(response.headers.any { it.key == "content-encoding" })
        assertFalse(response.headers.any { it.key == "content-length" })
        assertEquals(1, server.requestCount)
    }

    @Test
    fun transparentGzipExposesDecodedBodyAndDecodedResponseHeaders() {
        server.enqueue(gzipResponse("decoded").addHeader("X-Gzip-Reply", "present"))

        val response = transport().send(request())

        assertArrayEquals("decoded".toByteArray(), response.body)
        assertEquals("present", response.header("x-gzip-reply"))
        assertFalse(response.headers.any { it.key == "content-encoding" })
        assertFalse(response.headers.any { it.key == "content-length" })
    }

    @Test
    fun capsDecodedChunkedAndGzipBodiesWithoutReturningPartialSuccess() {
        server.enqueue(MockResponse().setChunkedBody("1234", 2))
        server.enqueue(MockResponse().setChunkedBody("12345", 2))
        server.enqueue(gzipResponse("1234"))
        server.enqueue(gzipResponse("12345"))
        val bounded = transport(maxResponseBytes = 4)

        assertArrayEquals("1234".toByteArray(), bounded.send(request()).body)
        assertThrows(TemperaTransportException::class.java) { bounded.send(request()) }
        assertArrayEquals("1234".toByteArray(), bounded.send(request()).body)
        assertThrows(TemperaTransportException::class.java) { bounded.send(request()) }
        assertEquals(4, server.requestCount)
    }

    @Test
    fun rejectsInvalidLimitAndDeadlineBeforeSending() {
        assertThrows(IllegalArgumentException::class.java) { transport(maxResponseBytes = 0) }
        assertThrows(IllegalArgumentException::class.java) {
            transport(maxResponseBytes = OkHttpTemperaTransport.MAX_RESPONSE_BYTES + 1)
        }
        assertThrows(TemperaTransportException::class.java) {
            transport().send(request(timeoutSeconds = Double.NaN))
        }
        assertThrows(TemperaTransportException::class.java) {
            transport().send(request(timeoutSeconds = 0.0))
        }
        assertThrows(TemperaTransportException::class.java) {
            transport().send(request(timeoutSeconds = Double.MAX_VALUE))
        }
        assertEquals(0, server.requestCount)
    }

    @Test
    fun tinyAndLongDeadlinesAlwaysReturnTypedTransportFailures() {
        server.enqueue(MockResponse().setSocketPolicy(SocketPolicy.NO_RESPONSE))
        assertThrows(TemperaTransportException::class.java) {
            transport().send(request(timeoutSeconds = 0.000000000001))
        }

        server.enqueue(MockResponse().setSocketPolicy(SocketPolicy.NO_RESPONSE))
        val result = AtomicReference<Throwable?>()
        val finished = CountDownLatch(1)
        val beyondIntMillis = (Int.MAX_VALUE.toDouble() / 1_000.0) + 1.0
        val worker =
            Thread {
                try {
                    transport().send(request(timeoutSeconds = beyondIntMillis))
                } catch (error: Throwable) {
                    result.set(error)
                } finally {
                    finished.countDown()
                }
            }
        worker.start()
        if (!finished.await(100, TimeUnit.MILLISECONDS)) worker.interrupt()
        assertTrue(finished.await(1, TimeUnit.SECONDS))
        assertTrue(result.get() is TemperaTransportException)
    }

    @Test
    fun deadlineAndPrematureBodyDisconnectAreTypedFailuresWithNoResend() {
        server.enqueue(MockResponse().setSocketPolicy(SocketPolicy.NO_RESPONSE))
        assertThrows(TemperaTransportException::class.java) {
            transport().send(request(timeoutSeconds = 0.05))
        }
        assertEquals(1, server.requestCount)

        server.enqueue(
            MockResponse()
                .setBody("will be cut short")
                .setSocketPolicy(SocketPolicy.DISCONNECT_DURING_RESPONSE_BODY)
        )
        assertThrows(TemperaTransportException::class.java) { transport().send(request()) }
        assertEquals(2, server.requestCount)
    }

    @Test
    fun deadlineIncludesTimeWaitingInTheOkHttpDispatcher() {
        val dispatcher = Dispatcher().apply {
            maxRequests = 1
            maxRequestsPerHost = 1
        }
        val queuedTransport = OkHttpTemperaTransport(OkHttpClient.Builder().dispatcher(dispatcher).build())
        server.enqueue(MockResponse().setSocketPolicy(SocketPolicy.NO_RESPONSE))
        val firstFinished = CountDownLatch(1)
        val first =
            Thread {
                try {
                    queuedTransport.send(request(timeoutSeconds = 2.0))
                } catch (_: Throwable) {
                    // The test interrupts this intentionally blocked first call.
                } finally {
                    firstFinished.countDown()
                }
            }
        first.start()
        assertNotNull(server.takeRequest(1, TimeUnit.SECONDS))

        val queuedAtNanos = System.nanoTime()
        assertThrows(TemperaTransportException::class.java) {
            queuedTransport.send(request(timeoutSeconds = 0.05))
        }
        assertTrue(TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - queuedAtNanos) < 1_000L)
        assertEquals(1, server.requestCount)
        first.interrupt()
        assertTrue(firstFinished.await(1, TimeUnit.SECONDS))
    }

    @Test
    fun interruptionCancelsTheWaitingCallAndDoesNotClaimTheWriteWasNeverSent() {
        server.enqueue(MockResponse().setSocketPolicy(SocketPolicy.NO_RESPONSE))
        val result = AtomicReference<Throwable?>()
        val interrupted = AtomicBoolean(false)
        val finished = CountDownLatch(1)
        val worker =
            Thread {
                try {
                    transport().send(request(method = "POST", body = "write".toByteArray()))
                } catch (error: Throwable) {
                    result.set(error)
                } finally {
                    interrupted.set(Thread.currentThread().isInterrupted)
                    finished.countDown()
                }
            }
        worker.start()
        assertNotNull(server.takeRequest(1, TimeUnit.SECONDS))
        worker.interrupt()

        assertTrue(finished.await(1, TimeUnit.SECONDS))
        val error = result.get()
        assertTrue(error is TemperaTransportException)
        assertTrue(error!!.message!!.contains("outcome is unknown"))
        assertFalse(error.message!!.contains("never sent"))
        assertTrue(interrupted.get())
        assertEquals(1, server.requestCount)
    }

    @Test
    fun internalTlsFixtureConstructorUsesStrictHostnameVerificationAndRejectsUnknownCa() {
        server.shutdown()
        val certificate = HeldCertificate.Builder().addSubjectAlternativeName("localhost").build()
        val serverCertificates = HandshakeCertificates.Builder().heldCertificate(certificate).build()
        val clientCertificates = HandshakeCertificates.Builder().addTrustedCertificate(certificate.certificate).build()
        server = MockWebServer()
        server.useHttps(serverCertificates.sslSocketFactory(), false)
        server.start()
        server.enqueue(MockResponse().setBody("secure"))

        val fixtureClient =
            OkHttpClient.Builder()
                .sslSocketFactory(clientCertificates.sslSocketFactory(), clientCertificates.trustManager)
                .hostnameVerifier { _, _ -> true }
                .build()
        val transport = OkHttpTemperaTransport(fixtureClient)
        val response = transport.send(request())

        assertEquals(200, response.status)
        assertArrayEquals("secure".toByteArray(), response.body)
        assertThrows(TemperaTransportException::class.java) {
            transport.send(
                TemperaHttpRequest(
                    method = "GET",
                    url = server.url("/resource").toString().replace("localhost", "127.0.0.1"),
                    timeoutSeconds = 2.0,
                )
            )
        }
        assertThrows(TemperaTransportException::class.java) {
            OkHttpTemperaTransport(OkHttpClient()).send(request())
        }
        assertEquals(1, server.requestCount)
    }

    @Test
    fun strictVerifierKeepsSameHostHttp2ReuseAndPreventsCrossHostCoalescing() {
        server.shutdown()
        val certificate =
            HeldCertificate.Builder()
                .addSubjectAlternativeName("localhost")
                .addSubjectAlternativeName("127.0.0.1")
                .build()
        val serverCertificates = HandshakeCertificates.Builder().heldCertificate(certificate).build()
        val clientCertificates = HandshakeCertificates.Builder().addTrustedCertificate(certificate.certificate).build()
        server = MockWebServer()
        server.protocols = listOf(Protocol.HTTP_2, Protocol.HTTP_1_1)
        server.useHttps(serverCertificates.sslSocketFactory(), false)
        server.start()
        server.enqueue(MockResponse().setBody("same-host-first"))
        server.enqueue(MockResponse().setBody("same-host-second"))
        server.enqueue(MockResponse().setResponseCode(421).setBody("cross-host"))
        val acquiredConnections = ConcurrentLinkedQueue<Connection>()
        val acquiredProtocols = ConcurrentLinkedQueue<Protocol>()
        val fixtureClient =
            OkHttpClient.Builder()
                .sslSocketFactory(clientCertificates.sslSocketFactory(), clientCertificates.trustManager)
                .eventListener(
                    object : EventListener() {
                        override fun connectionAcquired(call: Call, connection: Connection) {
                            acquiredConnections.add(connection)
                            acquiredProtocols.add(connection.protocol())
                        }
                    }
                )
                .build()
        val transport = OkHttpTemperaTransport(fixtureClient)

        assertEquals(200, transport.send(request()).status)
        assertEquals(200, transport.send(request()).status)
        val crossHostResponse =
            transport.send(
                TemperaHttpRequest(
                    method = "GET",
                    url = server.url("/cross-host").toString().replace("localhost", "127.0.0.1"),
                    timeoutSeconds = 2.0,
                )
            )

        val first = requireNotNull(server.takeRequest(1, TimeUnit.SECONDS))
        val second = requireNotNull(server.takeRequest(1, TimeUnit.SECONDS))
        val crossHost = requireNotNull(server.takeRequest(1, TimeUnit.SECONDS))
        assertEquals(0, first.sequenceNumber)
        assertEquals(1, second.sequenceNumber)
        assertEquals(0, crossHost.sequenceNumber)
        assertEquals(listOf(Protocol.HTTP_2, Protocol.HTTP_2, Protocol.HTTP_2), acquiredProtocols.toList())
        val connections = acquiredConnections.toList()
        assertEquals(3, connections.size)
        assertTrue(connections[0] === connections[1])
        assertFalse(connections[1] === connections[2])
        assertEquals(421, crossHostResponse.status)
        assertEquals(3, server.requestCount)
    }

    private fun transport(
        maxResponseBytes: Long = OkHttpTemperaTransport.DEFAULT_MAX_RESPONSE_BYTES,
    ): OkHttpTemperaTransport = OkHttpTemperaTransport(maxResponseBytes)

    private fun request(
        method: String = "GET",
        body: ByteArray? = null,
        headers: List<TemperaKeyValue> = emptyList(),
        timeoutSeconds: Double = 2.0,
    ): TemperaHttpRequest =
        TemperaHttpRequest(
            method = method,
            url = server.url("/resource").toString(),
            headers = headers,
            body = body,
            timeoutSeconds = timeoutSeconds,
        )

    private fun gzipResponse(value: String): MockResponse {
        val compressed = Buffer()
        GzipSink(compressed).buffer().use { it.writeUtf8(value) }
        return MockResponse()
            .addHeader("Content-Encoding", "gzip")
            .setBody(compressed)
    }
}
