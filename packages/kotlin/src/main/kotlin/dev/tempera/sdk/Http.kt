// The transport seam: one request value, one response value, one interface.
//
// Everything above this file (dispatch, auth, MCP) builds a
// TemperaHttpRequest and reads a TemperaHttpResponse, so tests drive the whole
// client through a stub without a socket, exactly as the TypeScript package
// injects `fetch` and the Python package injects `transport`.
//
// The default implementation is the JDK 17 HttpClient. Calls block: the
// package has no external dependencies, so it cannot use coroutines, and a
// blocking client composes with whatever concurrency the caller already has.

package dev.tempera.sdk

import java.io.IOException
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.time.Duration

/** One outbound HTTP request. */
public class TemperaHttpRequest(
    /** HTTP method (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`). */
    public val method: String,
    /** Absolute URL, including any query string. */
    public val url: String,
    /** Request headers, lowercase-named, in emission order. */
    public val headers: List<TemperaKeyValue> = emptyList(),
    /** Request body bytes, when the request carries one. */
    public val body: ByteArray? = null,
    /** How long to wait for the complete response. */
    public val timeoutSeconds: Double = TemperaClientConfiguration.DEFAULT_TIMEOUT_SECONDS,
) {
    /** One header's value, matched case-insensitively. */
    public fun header(name: String): String? {
        val wanted = name.lowercase()
        return headers.firstOrNull { it.key.lowercase() == wanted }?.value
    }

    /** The request body as UTF-8 text, or `null` when there is none. */
    public fun bodyText(): String? = body?.toString(Charsets.UTF_8)
}

/** One inbound HTTP response. */
public class TemperaHttpResponse(
    /** HTTP status code. */
    public val status: Int,
    statusText: String = "",
    /** Response headers. */
    public val headers: List<TemperaKeyValue> = emptyList(),
    /** Response body bytes. */
    public val body: ByteArray = ByteArray(0),
) {
    /** HTTP status text (reason phrase). */
    public val statusText: String =
        if (statusText.isEmpty()) reasonPhrase(status) else statusText

    /** One header's value, matched case-insensitively. */
    public fun header(name: String): String? {
        val wanted = name.lowercase()
        return headers.firstOrNull { it.key.lowercase() == wanted }?.value
    }

    /** Whether the status is 2xx. */
    public fun isSuccess(): Boolean = status in 200..299

    /** The body parsed as JSON, or `null` when it is empty or not JSON. */
    public fun json(): TemperaJson? = if (body.isEmpty()) null else TemperaJson.parse(body)

    public companion object {
        /**
         * The standard reason phrase for a status code.
         *
         * `java.net.http` does not surface the server's reason phrase, and the
         * uniform error contract wants the same text the TypeScript and Python
         * packages report.
         */
        public fun reasonPhrase(status: Int): String =
            when (status) {
                200 -> "OK"
                201 -> "Created"
                202 -> "Accepted"
                204 -> "No Content"
                301 -> "Moved Permanently"
                302 -> "Found"
                304 -> "Not Modified"
                400 -> "Bad Request"
                401 -> "Unauthorized"
                403 -> "Forbidden"
                404 -> "Not Found"
                405 -> "Method Not Allowed"
                408 -> "Request Timeout"
                409 -> "Conflict"
                410 -> "Gone"
                413 -> "Payload Too Large"
                415 -> "Unsupported Media Type"
                422 -> "Unprocessable Entity"
                429 -> "Too Many Requests"
                500 -> "Internal Server Error"
                501 -> "Not Implemented"
                502 -> "Bad Gateway"
                503 -> "Service Unavailable"
                504 -> "Gateway Timeout"
                else -> "HTTP " + status
            }
    }
}

/**
 * Sends one request and returns one response. Non-2xx statuses are responses,
 * not errors: only a failure to obtain a response throws.
 */
public fun interface TemperaTransport {
    /** Send one request. */
    public fun send(request: TemperaHttpRequest): TemperaHttpResponse
}

/** The default transport: JDK 17 `java.net.http.HttpClient`. */
public class JdkHttpTransport(
    private val client: HttpClient =
        HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .followRedirects(HttpClient.Redirect.NORMAL)
            .build()
) : TemperaTransport {

    override fun send(request: TemperaHttpRequest): TemperaHttpResponse {
        val builder =
            HttpRequest.newBuilder()
                .uri(URI.create(request.url))
                .timeout(Duration.ofMillis((request.timeoutSeconds * 1000).toLong()))
        val payload =
            if (request.body == null) {
                HttpRequest.BodyPublishers.noBody()
            } else {
                HttpRequest.BodyPublishers.ofByteArray(request.body)
            }
        builder.method(request.method.uppercase(), payload)
        for (header in request.headers) {
            builder.header(header.key, header.value)
        }
        try {
            val response = client.send(builder.build(), HttpResponse.BodyHandlers.ofByteArray())
            val headers = ArrayList<TemperaKeyValue>()
            for (entry in response.headers().map()) {
                for (value in entry.value) {
                    headers.add(TemperaKeyValue(entry.key.lowercase(), value))
                }
            }
            return TemperaHttpResponse(
                status = response.statusCode(),
                statusText = TemperaHttpResponse.reasonPhrase(response.statusCode()),
                headers = headers,
                body = response.body(),
            )
        } catch (error: IOException) {
            // No HTTP response existed, which is what the retry policy treats
            // as a transient connection failure.
            throw TemperaTransportException(error.message ?: error.toString(), error)
        } catch (error: InterruptedException) {
            Thread.currentThread().interrupt()
            throw TemperaTransportException("interrupted", error)
        }
    }
}
