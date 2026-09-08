package dev.tempera.sdk

import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.InterruptedIOException
import java.util.Locale
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference
import javax.net.ssl.HttpsURLConnection
import okhttp3.Authenticator
import okhttp3.Call
import okhttp3.Callback
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import okhttp3.ResponseBody
import okio.Buffer

/**
 * Android HTTP transport backed by OkHttp.
 *
 * It has a mobile-sized one MiB decoded-response limit by default. Callers may
 * choose a different positive limit up to [MAX_RESPONSE_BYTES]. Every request
 * has its own finite deadline, sends once at this layer, and keeps ordinary
 * platform TLS certificate and hostname checks enabled.
 */
public class OkHttpTemperaTransport private constructor(
    private val baseClient: OkHttpClient,
    /** Maximum decoded bytes returned in a successful or error response. */
    public val maxResponseBytes: Long,
    @Suppress("UNUSED_PARAMETER") private val constructionMarker: Unit,
) : TemperaTransport {
    /** Create a transport using the platform's ordinary, strict TLS defaults. */
    @JvmOverloads
    public constructor(
        maxResponseBytes: Long = DEFAULT_MAX_RESPONSE_BYTES,
    ) : this(OkHttpClient.Builder().build(), maxResponseBytes, Unit)

    /**
     * Test seam for a local TLS fixture. The supplied client may supply a test
     * trust store, but transport-level redirects, retries, and authenticators
     * are still disabled on the derived client.
     */
    internal constructor(
        baseClient: OkHttpClient,
        maxResponseBytes: Long = DEFAULT_MAX_RESPONSE_BYTES,
    ) : this(baseClient, maxResponseBytes, Unit)

    private val retryAfterRestorations = ConcurrentHashMap<Call, List<String>>()

    private val client: OkHttpClient =
        baseClient.newBuilder()
            .followRedirects(false)
            .followSslRedirects(false)
            .retryOnConnectionFailure(false)
            .authenticator(Authenticator.NONE)
            .proxyAuthenticator(Authenticator.NONE)
            .hostnameVerifier(HttpsURLConnection.getDefaultHostnameVerifier())
            // OkHttp 4 may follow a 503 with Retry-After: 0 even when connection
            // retries are off. The network interceptor changes that one internal
            // decision and the application interceptor restores only the changed
            // Retry-After values. It leaves BridgeInterceptor's decoded-body
            // header normalization intact.
            .addNetworkInterceptor { chain ->
                val response = chain.proceed(chain.request())
                val retryAfter = response.headers.values("Retry-After")
                if (response.code == 503 && isZeroRetryAfter(retryAfter.lastOrNull())) {
                    retryAfterRestorations[chain.call()] = retryAfter
                    response.newBuilder().header("Retry-After", "1").build()
                } else {
                    response
                }
            }
            .addInterceptor { chain ->
                val response = chain.proceed(chain.request())
                val retryAfter = retryAfterRestorations.remove(chain.call())
                if (retryAfter == null) {
                    response
                } else {
                    val headers = response.headers.newBuilder().removeAll("Retry-After")
                    for (value in retryAfter) headers.add("Retry-After", value)
                    response.newBuilder().headers(headers.build()).build()
                }
            }
            .build()

    init {
        require(maxResponseBytes in 1..MAX_RESPONSE_BYTES) {
            "maxResponseBytes must be between 1 and $MAX_RESPONSE_BYTES"
        }
    }

    override fun send(request: TemperaHttpRequest): TemperaHttpResponse {
        val timeoutNanos = timeoutNanos(request.timeoutSeconds)
        val startedAtNanos = System.nanoTime()
        val httpRequest = toOkHttpRequest(request)
        val call =
            try {
                client.newBuilder()
                    // This secondary timeout cancels a running exchange and its body
                    // read. The monotonic latch deadline below also covers dispatcher
                    // queueing, which OkHttp's call timeout begins after scheduling.
                    .callTimeout(timeoutNanos, TimeUnit.NANOSECONDS)
                    .build()
                    .newCall(httpRequest)
            } catch (error: RuntimeException) {
                throw transportFailure(error)
            }
        try {
            return await(call, startedAtNanos, timeoutNanos)
        } catch (error: RuntimeException) {
            throw transportFailure(error)
        } finally {
            // A cancelled call can fail before the application interceptor runs.
            retryAfterRestorations.remove(call)
        }
    }

    private fun toOkHttpRequest(request: TemperaHttpRequest): Request {
        try {
            val body = request.body?.let { RequestBodyFactory.bytes(it) }
            val builder = Request.Builder().url(request.url)
            for (header in request.headers) builder.addHeader(header.key, header.value)
            return builder.method(request.method.uppercase(Locale.US), body).build()
        } catch (error: RuntimeException) {
            throw transportFailure(error)
        }
    }

    private fun await(
        call: Call,
        startedAtNanos: Long,
        timeoutNanos: Long,
    ): TemperaHttpResponse {
        val done = CountDownLatch(1)
        val response = AtomicReference<TemperaHttpResponse?>()
        val failure = AtomicReference<Throwable?>()
        val activeResponse = AtomicReference<Response?>()

        call.enqueue(
            object : Callback {
                override fun onFailure(call: Call, error: IOException) {
                    failure.compareAndSet(null, error)
                    done.countDown()
                }

                override fun onResponse(call: Call, rawResponse: Response) {
                    activeResponse.set(rawResponse)
                    try {
                        if (call.isCanceled()) throw InterruptedIOException("cancelled")
                        response.compareAndSet(null, readResponse(rawResponse))
                    } catch (error: Throwable) {
                        failure.compareAndSet(null, error)
                    } finally {
                        activeResponse.compareAndSet(rawResponse, null)
                        rawResponse.body?.close()
                        done.countDown()
                    }
                }
            }
        )

        try {
            val remainingNanos = remainingNanos(startedAtNanos, timeoutNanos)
            if (remainingNanos <= 0L || !done.await(remainingNanos, TimeUnit.NANOSECONDS)) {
                cancel(call, activeResponse)
                throw TemperaTransportException("deadline exceeded; request outcome is unknown")
            }
        } catch (error: InterruptedException) {
            // The request may already have reached the peer. Do not imply it was
            // never sent and do not retry it here; authoritative reconciliation
            // decides a write's outcome.
            cancel(call, activeResponse)
            Thread.currentThread().interrupt()
            throw TemperaTransportException("interrupted; request outcome is unknown", error)
        }

        val error = failure.get()
        if (error != null) throw transportFailure(error)
        return response.get()
            ?: throw TemperaTransportException("call completed without a response")
    }

    private fun readResponse(response: Response): TemperaHttpResponse {
        val body = response.body?.let { readBody(it) } ?: ByteArray(0)
        val headers = ArrayList<TemperaKeyValue>(response.headers.size)
        for (index in 0 until response.headers.size) {
            headers.add(
                TemperaKeyValue(
                    response.headers.name(index).lowercase(Locale.US),
                    response.headers.value(index),
                )
            )
        }
        return TemperaHttpResponse(
            status = response.code,
            statusText = TemperaHttpResponse.reasonPhrase(response.code),
            headers = headers,
            body = body,
        )
    }

    private fun readBody(body: ResponseBody): ByteArray {
        val source = body.source()
        val buffer = Buffer()
        val output = ByteArrayOutputStream()
        var total = 0L
        while (true) {
            val read = source.read(buffer, READ_CHUNK_BYTES.toLong())
            if (read == -1L) break
            if (read > maxResponseBytes - total) {
                throw TemperaTransportException(
                    "response body exceeds configured limit of $maxResponseBytes bytes"
                )
            }
            output.write(buffer.readByteArray(read))
            total += read
        }
        return output.toByteArray()
    }

    private fun timeoutNanos(seconds: Double): Long {
        if (!seconds.isFinite() || seconds <= 0.0) {
            throw TemperaTransportException("timeoutSeconds must be finite and positive")
        }
        val nanos = Math.ceil(seconds * NANOS_PER_SECOND)
        if (!nanos.isFinite() || nanos > MAX_TIMEOUT_NANOS.toDouble()) {
            throw TemperaTransportException("timeoutSeconds is too large")
        }
        return nanos.toLong().coerceAtLeast(1L)
    }

    private fun remainingNanos(startedAtNanos: Long, timeoutNanos: Long): Long {
        val elapsedNanos = System.nanoTime() - startedAtNanos
        return if (elapsedNanos >= timeoutNanos) 0L else timeoutNanos - elapsedNanos
    }

    private fun transportFailure(error: Throwable): TemperaTransportException =
        if (error is TemperaTransportException) {
            error
        } else {
            TemperaTransportException(error.message ?: error.toString(), error)
        }

    private fun cancel(call: Call, activeResponse: AtomicReference<Response?>) {
        call.cancel()
        activeResponse.getAndSet(null)?.body?.close()
    }

    /** Same narrow numeric-zero case that OkHttp's 503 follow-up parser admits. */
    private fun isZeroRetryAfter(value: String?): Boolean =
        value != null && value.isNotEmpty() && value.all { it == '0' }

    private object RequestBodyFactory {
        fun bytes(bytes: ByteArray): okhttp3.RequestBody =
            bytes.toRequestBody(null)
    }

    public companion object {
        /** Default mobile decoded-response limit: one MiB. */
        public const val DEFAULT_MAX_RESPONSE_BYTES: Long = 1L * 1024L * 1024L

        /** Largest accepted decoded-response limit: 64 MiB. */
        public const val MAX_RESPONSE_BYTES: Long = 64L * 1024L * 1024L

        private const val READ_CHUNK_BYTES: Int = 8 * 1024
        private const val NANOS_PER_SECOND: Double = 1_000_000_000.0
        private const val MAX_TIMEOUT_NANOS: Long = Long.MAX_VALUE / 2L
    }
}
