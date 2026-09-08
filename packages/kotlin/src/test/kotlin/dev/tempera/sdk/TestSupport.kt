package dev.tempera.sdk

import java.net.URI
import java.net.URLDecoder
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.assertThrows

/**
 * A transport that records every request and answers from a caller-supplied
 * responder, so the whole client is exercised without a socket -- the same seam
 * the Python package's `FakeTransport` and the TypeScript package's injected
 * `fetch` provide.
 */
class StubTransport(
    private val responder: (TemperaHttpRequest, Int) -> TemperaHttpResponse = OK
) : TemperaTransport {

    val requests: MutableList<TemperaHttpRequest> = ArrayList()

    var attempts: Int = 0
        private set

    override fun send(request: TemperaHttpRequest): TemperaHttpResponse {
        requests.add(request)
        attempts += 1
        return responder(request, attempts)
    }

    fun lastRequest(): TemperaHttpRequest = requests[requests.size - 1]

    fun lastParts(): RequestParts = RequestParts(lastRequest())

    fun lastBodyText(): String = String(lastRequest().body!!, Charsets.UTF_8)

    fun clear() {
        requests.clear()
        attempts = 0
    }

    companion object {
        /** The default answer: `{"ok": true}`. */
        val OK: (TemperaHttpRequest, Int) -> TemperaHttpResponse = { _, _ -> json("""{"ok":true}""") }

        /** A 200 response carrying one JSON body. */
        fun json(body: String, status: Int = 200): TemperaHttpResponse =
            TemperaHttpResponse(
                status = status,
                headers = listOf(TemperaKeyValue("content-type", "application/json")),
                body = body.toByteArray(Charsets.UTF_8),
            )

        /** A transport that always answers with one JSON body. */
        fun always(body: String, status: Int = 200): StubTransport =
            StubTransport { _, _ -> json(body, status) }
    }
}

/** One recorded request, split the way the assertions read it. */
class RequestParts(request: TemperaHttpRequest) {
    val method: String = request.method
    val url: String = request.url
    val origin: String
    val path: String
    val query: Map<String, String>
    val headers: Map<String, String> =
        request.headers.associate { it.key.lowercase() to it.value }
    val rawBody: ByteArray? = request.body
    val body: TemperaJson? = request.body?.let { TemperaJson.parse(it) }

    init {
        val uri = URI(request.url)
        origin = uri.scheme + "://" + uri.host + (if (uri.port > 0) ":" + uri.port else "")
        path = uri.rawPath ?: ""
        val pairs = LinkedHashMap<String, String>()
        val raw = uri.rawQuery
        if (raw != null && raw.isNotEmpty()) {
            for (item in raw.split("&")) {
                val separator = item.indexOf('=')
                if (separator < 0) {
                    pairs[decode(item)] = ""
                } else {
                    pairs[decode(item.substring(0, separator))] =
                        decode(item.substring(separator + 1))
                }
            }
        }
        query = pairs
    }

    private fun decode(value: String): String = URLDecoder.decode(value, "UTF-8")
}

object TestFixtures {
    const val ISSUER: String = "https://api.tempera.dev"
    const val API_KEY: String = "tp_key_1"
    const val ACCOUNT_TOKEN: String = "account_token_1"
    const val INTROSPECTION_SECRET: String = "introspect_secret_1"
    const val SAMPLE_PATH_PARAM: String = "sample-value"
    const val SAMPLE_QUERY_VALUE: String = "sample-query"

    /** A base URL per product, so a wrong product key shows up as a wrong host. */
    fun baseUrls(): Map<String, String> {
        val urls = LinkedHashMap<String, String>()
        for (product in TemperaSurface.products) {
            urls[product.key] = baseUrl(product.key)
        }
        return urls
    }

    fun baseUrl(product: String): String = "https://" + product.lowercase() + ".example.test"

    /** A client wired to a stub transport, with every credential kind present. */
    fun client(
        transport: StubTransport,
        auth: TemperaAuth? = null,
        accountToken: String? = ACCOUNT_TOKEN,
        environment: String? = null,
        baseUrls: Map<String, String>? = null,
        configuration: TemperaClientConfiguration = TemperaClientConfiguration(),
        processEnvironment: Map<String, String> = emptyMap(),
        sleeper: (Double) -> Unit = {},
        random: () -> Double = { 1.0 },
    ): TemperaClient =
        TemperaClient(
            auth = auth ?: TemperaAuth(ISSUER, apiKey = API_KEY, transport = transport),
            accountToken = accountToken,
            introspectionSecret = INTROSPECTION_SECRET,
            baseUrls = baseUrls ?: baseUrls(),
            environment = environment,
            transport = transport,
            configuration = configuration,
            processEnvironment = processEnvironment,
            sleeper = sleeper,
            random = random,
        )

    /** A path-parameter value that satisfies the operation's AIP pattern. */
    fun pathParam(op: TemperaOperationSpec, name: String): String {
        val pattern = op.pathParamTemplates.firstOrNull { it.key == name }?.value
            ?: return SAMPLE_PATH_PARAM
        return pattern.replace("*", SAMPLE_PATH_PARAM)
    }

    /** The path the operation should produce for [pathParam] values. */
    fun expectedPath(op: TemperaOperationSpec): String {
        var path = op.path
        for (name in op.pathParams) {
            path = path.replace("{" + name + "}", pathParam(op, name))
        }
        return path
    }
}

/** Assert that [block] throws a [TemperaSdkException] whose message contains [substring]. */
fun assertSdkError(substring: String, block: () -> Unit) {
    val error = assertThrows<TemperaSdkException> { block() }
    val message = error.message ?: ""
    assertTrue(message.contains(substring), message + " does not contain " + substring)
}
