package dev.tempera.sdk

import java.io.IOException
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.time.Duration

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
