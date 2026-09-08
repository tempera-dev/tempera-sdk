package dev.tempera.sdk.fixture

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import android.os.Build
import android.os.Looper
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.net.SocketTimeoutException
import java.nio.charset.StandardCharsets
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference
import java.util.Locale
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class AndroidSdkRuntimeTest {
    @Test fun authMcpAndBaseJsonClassesLoadOnDevice() {
        assertExpectedDeviceApi()
        LoopbackServer().use { server ->
            // URL resolution and the blocking SDK boundary belong on the
            // instrumentation worker, never ActivityScenario's UI callback.
            assertNotEquals(Looper.getMainLooper(), Looper.myLooper())
            ActivityScenario.launch(MainActivity::class.java).use { scenario ->
                val activity = AtomicReference<MainActivity>()
                scenario.onActivity { activity.set(it) }
                assertEquals("true:true", requireNotNull(activity.get()).executeLoopback(server.baseUrl))
            }
            server.assertCompleted()
        }
    }

    private fun assertExpectedDeviceApi() {
        val expectedText =
            InstrumentationRegistry.getArguments().getString(EXPECTED_API_ARGUMENT) ?: return
        val expected =
            expectedText.toIntOrNull()
                ?: throw AssertionError("$EXPECTED_API_ARGUMENT must be an integer, was $expectedText")
        assertEquals(expected, Build.VERSION.SDK_INT)
    }

    private class LoopbackServer : AutoCloseable {
        private val server =
            ServerSocket(0, 1, InetAddress.getByName(LOOPBACK_HOST)).apply {
                soTimeout = ACCEPT_TIMEOUT_MILLIS
            }
        private val completed = CountDownLatch(1)
        private val failure = AtomicReference<Throwable?>()
        private val activeSocket = AtomicReference<Socket?>()
        @Volatile private var closing = false
        private val worker = Thread(::serve, "tempera-sdk-fixture-loopback")

        val baseUrl: String = "http://$LOOPBACK_HOST:" + server.localPort

        init {
            worker.start()
        }

        private fun serve() {
            try {
                respondToBaseRequest()
                respondToMcpRequest()
                rejectUnexpectedThirdRequest()
            } catch (error: Throwable) {
                if (!closing) failure.compareAndSet(null, error)
            } finally {
                runCatching { activeSocket.getAndSet(null)?.close() }
                runCatching { server.close() }
                completed.countDown()
            }
        }

        private fun respondToBaseRequest() {
            acceptRequest().use { socket ->
                val request = readRequest(socket)
                assertRequest(
                    request = request,
                    expectedMethod = "GET",
                    expectedPath = "/base",
                    expectedBody = false,
                )
                requireHeader(request, "accept", "application/json")
                requireHeader(request, "authorization", "Bearer fixture")
                writeJson(socket, "{\"ok\":true}")
            }
        }

        private fun respondToMcpRequest() {
            acceptRequest().use { socket ->
                val request = readRequest(socket)
                assertRequest(
                    request = request,
                    expectedMethod = "POST",
                    expectedPath = "/mcp",
                    expectedBody = true,
                )
                requireHeader(request, "accept", "application/json")
                requireHeader(request, "content-type", "application/json")
                requireHeader(request, "authorization", "Bearer fixture")
                requireHeader(request, "mcp-protocol-version", "2026-07-28")
                requireHeader(request, "mcp-method", "ping")
                val rpc = JSONObject(String(request.body, StandardCharsets.UTF_8))
                check(rpc.optString("jsonrpc") == "2.0") { "MCP JSON-RPC version was not 2.0" }
                check(rpc.optString("method") == "ping") { "MCP JSON-RPC method was not ping" }
                check(rpc.has("id") && !rpc.isNull("id")) { "MCP JSON-RPC request omitted id" }
                val id =
                    when (val value = rpc.get("id")) {
                        is Int -> value.toLong()
                        is Long -> value
                        else -> throw AssertionError("MCP JSON-RPC id was not an integer")
                    }
                check(id == 1L) { "MCP JSON-RPC id was not 1" }
                assertPingParams(rpc)
                writeJson(socket, "{\"jsonrpc\":\"2.0\",\"id\":" + id + ",\"result\":{\"ok\":true}}")
            }
        }

        private fun assertPingParams(rpc: JSONObject) {
            val params = rpc.getJSONObject("params")
            check(params.length() == 1 && params.has("_meta")) { "MCP ping params were not meta-only" }
            val meta = params.getJSONObject("_meta")
            check(meta.length() == 2) { "MCP ping meta shape was unexpected" }
            check(meta.getString("io.modelcontextprotocol/protocolVersion") == "2026-07-28") {
                "MCP ping protocol version was unexpected"
            }
            val capabilities = meta.get("io.modelcontextprotocol/clientCapabilities")
            check(capabilities is JSONObject && capabilities.length() == 0) {
                "MCP ping client capabilities were not an empty object"
            }
        }

        private fun rejectUnexpectedThirdRequest() {
            server.soTimeout = EXTRA_REQUEST_TIMEOUT_MILLIS
            try {
                acceptRequest().use {
                    throw AssertionError("SDK sent more than the expected two loopback requests")
                }
            } catch (_: SocketTimeoutException) {
                // This bounded quiet window observed no immediate third request; it
                // does not make a claim about requests attempted later.
            }
        }

        private fun acceptRequest(): Socket =
            server.accept().apply {
                activeSocket.set(this)
                soTimeout = SOCKET_TIMEOUT_MILLIS
            }

        private fun readRequest(socket: Socket): HttpRequest {
            val input = socket.getInputStream()
            val readStartedAtNanos = System.nanoTime()
            val lines = readHeaderLines(socket, input, readStartedAtNanos)
            val requestLine = lines.first()
            check(requestLine.length <= MAX_REQUEST_LINE_BYTES) { "request line exceeds byte limit" }
            val parts = requestLine.split(' ')
            check(parts.size == 3 && parts.all(String::isNotEmpty)) { "invalid HTTP request line" }
            check(parts[2] == "HTTP/1.1") { "unexpected HTTP version " + parts[2] }

            val headers = LinkedHashMap<String, String>()
            for (line in lines.drop(1)) {
                check(line.isNotEmpty() && !line.contains('\r') && !line.contains('\n')) { "invalid HTTP header line" }
                val separator = line.indexOf(':')
                check(separator > 0) { "invalid HTTP header" }
                val name = line.substring(0, separator).lowercase(Locale.US)
                check(name.all(::isHttpTokenCharacter)) { "invalid HTTP header name" }
                check(headers.put(name, line.substring(separator + 1).trim()) == null) {
                    "duplicate HTTP header $name"
                }
            }
            check(headers["transfer-encoding"] == null) { "chunked request framing is unsupported" }
            if (parts[0] == "POST") check(headers.containsKey("content-length")) { "POST lacked Content-Length" }
            val bodyLength =
                headers["content-length"]?.let(::contentLength)
                    ?: 0
            return HttpRequest(
                parts[0],
                parts[1],
                headers,
                readExactly(socket, input, bodyLength, readStartedAtNanos),
            )
        }

        private fun readHeaderLines(
            socket: Socket,
            input: InputStream,
            readStartedAtNanos: Long,
        ): List<String> {
            val output = ByteArrayOutputStream()
            var suffix = 0L
            while (output.size() < MAX_HEADER_BYTES) {
                val next = readByte(socket, input, readStartedAtNanos)
                check(next >= 0) { "unexpected end of stream before HTTP headers" }
                output.write(next)
                suffix = ((suffix shl 8) or next.toLong()) and 0xffff_ffffL
                if (suffix == HEADER_TERMINATOR) {
                    val headerBytes = output.toByteArray()
                    val text =
                        String(
                            headerBytes,
                            0,
                            headerBytes.size - HEADER_TERMINATOR_BYTES,
                            StandardCharsets.ISO_8859_1,
                        )
                    val lines = text.split("\r\n")
                    check(lines.isNotEmpty() && lines.first().isNotEmpty()) { "missing HTTP request line" }
                    return lines
                }
            }
            throw AssertionError("HTTP headers exceed byte limit")
        }

        private fun contentLength(value: String): Int {
            check(value.isNotEmpty() && value.all { it in '0'..'9' }) { "invalid Content-Length" }
            var length = 0
            for (character in value) {
                val digit = character - '0'
                check(length <= (MAX_BODY_BYTES - digit) / 10) { "Content-Length exceeds byte limit" }
                length = length * 10 + digit
            }
            return length
        }

        private fun readExactly(
            socket: Socket,
            input: InputStream,
            length: Int,
            readStartedAtNanos: Long,
        ): ByteArray {
            val body = ByteArray(length)
            var offset = 0
            while (offset < length) {
                configureReadTimeout(socket, readStartedAtNanos)
                val read = input.read(body, offset, length - offset)
                assertReadDeadline(readStartedAtNanos)
                check(read > 0) { "unexpected end of stream in HTTP request body" }
                offset += read
            }
            return body
        }

        private fun readByte(socket: Socket, input: InputStream, readStartedAtNanos: Long): Int {
            configureReadTimeout(socket, readStartedAtNanos)
            val read = input.read()
            assertReadDeadline(readStartedAtNanos)
            return read
        }

        private fun configureReadTimeout(socket: Socket, readStartedAtNanos: Long) {
            val remainingNanos = REQUEST_READ_TIMEOUT_NANOS - (System.nanoTime() - readStartedAtNanos)
            check(remainingNanos > 0L) { "HTTP request exceeded total read deadline" }
            val remainingMillis =
                ((remainingNanos + NANOS_PER_MILLISECOND - 1L) / NANOS_PER_MILLISECOND)
                    .coerceAtLeast(1L)
            socket.soTimeout = minOf(SOCKET_TIMEOUT_MILLIS.toLong(), remainingMillis).toInt()
        }

        private fun assertReadDeadline(readStartedAtNanos: Long) {
            check(System.nanoTime() - readStartedAtNanos <= REQUEST_READ_TIMEOUT_NANOS) {
                "HTTP request exceeded total read deadline"
            }
        }

        private fun assertRequest(
            request: HttpRequest,
            expectedMethod: String,
            expectedPath: String,
            expectedBody: Boolean,
        ) {
            check(request.method == expectedMethod) { "expected " + expectedMethod + " request, was " + request.method }
            check(request.path == expectedPath) { "expected " + expectedPath + " request, was " + request.path }
            check((request.body.isNotEmpty()) == expectedBody) { "unexpected HTTP request body" }
            if (expectedBody) check(request.headers.containsKey("content-length")) { "request body lacked Content-Length" }
        }

        private fun requireHeader(request: HttpRequest, name: String, expected: String) {
            check(request.headers[name] == expected) {
                "expected " + name + "=" + expected + ", was " + request.headers[name]
            }
        }

        private fun writeJson(socket: Socket, json: String) {
            val body = json.toByteArray(StandardCharsets.UTF_8)
            val response =
                "HTTP/1.1 200 OK\r\n" +
                    "Content-Type: application/json\r\n" +
                    "Content-Length: " + body.size + "\r\n" +
                    "Connection: close\r\n\r\n"
            socket.getOutputStream().use { output ->
                output.write(response.toByteArray(StandardCharsets.ISO_8859_1))
                output.write(body)
                output.flush()
            }
        }

        fun assertCompleted() {
            check(completed.await(SERVER_COMPLETION_TIMEOUT_MILLIS, TimeUnit.MILLISECONDS)) {
                "loopback server did not complete two requests before timeout"
            }
            worker.join(WORKER_JOIN_TIMEOUT_MILLIS)
            check(!worker.isAlive) { "loopback worker did not terminate" }
            failure.get()?.let { throw AssertionError("loopback server failed", it) }
        }

        override fun close() {
            closing = true
            runCatching { activeSocket.getAndSet(null)?.close() }
            runCatching { server.close() }
            worker.join(WORKER_JOIN_TIMEOUT_MILLIS)
            check(!worker.isAlive) { "loopback worker did not terminate during close" }
        }

        private data class HttpRequest(
            val method: String,
            val path: String,
            val headers: Map<String, String>,
            val body: ByteArray,
        )

        private companion object {
            const val LOOPBACK_HOST = "127.0.0.1"
            const val ACCEPT_TIMEOUT_MILLIS = 10_000
            const val SOCKET_TIMEOUT_MILLIS = 10_000
            const val EXTRA_REQUEST_TIMEOUT_MILLIS = 250
            const val SERVER_COMPLETION_TIMEOUT_MILLIS = 15_000L
            const val WORKER_JOIN_TIMEOUT_MILLIS = 1_000L
            const val REQUEST_READ_TIMEOUT_NANOS = 10_000_000_000L
            const val NANOS_PER_MILLISECOND = 1_000_000L
            const val MAX_REQUEST_LINE_BYTES = 4 * 1024
            const val MAX_HEADER_BYTES = 32 * 1024
            const val MAX_BODY_BYTES = 64 * 1024
            const val HEADER_TERMINATOR = 0x0d0a0d0aL
            const val HEADER_TERMINATOR_BYTES = 4

            fun isHttpTokenCharacter(character: Char): Boolean =
                character in 'a'..'z' ||
                    character in 'A'..'Z' ||
                    character in '0'..'9' ||
                    character in "!#$%&'*+-.^_|~" ||
                    character.code == 96
        }
    }

    private companion object {
        const val EXPECTED_API_ARGUMENT = "temperaExpectedApi"
    }
}
