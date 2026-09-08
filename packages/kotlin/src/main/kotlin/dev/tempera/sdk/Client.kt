// The unified Tempera client: one credential set, every product.
//
// Built entirely from the generated surface tables (`Surface.kt`), so the
// TypeScript, Python, Rust, Swift, and Kotlin packages expose the same
// products, the same operation names, the same descriptions, and the same
// error shape.
//
// - Typed operations: `client.palette.call("getTrace", mapOf("tenantId" to id))`
//   -- every operation in `surface.json` is reachable by product key and
//   operation id. Parameters accept canonical wire names and snake_case
//   aliases; requests always emit the producer's canonical wire names.
// - Passthrough: `client.tempo.request("/custom", method = "POST", body = ...)`
//   for endpoints the surface tables do not cover yet.
// - Auth: audience products resolve their bearer through TemperaAuth
//   (per-audience OAuth token with unified `tp_` API-key fallback);
//   control-plane operations use the account-session token returned by
//   `createHostedSession`.
//
// Calls block. The package has no external dependencies, so it cannot use
// coroutines, and a blocking client composes with whatever concurrency the
// caller already has.

package dev.tempera.sdk

import java.util.concurrent.ThreadLocalRandom

/** Request parameters: ordered by insertion, values converted by [temperaJsonOf]. */
public typealias TemperaParams = Map<String, Any?>

/**
 * lowerCamelCase to snake_case, matching the alias rule in the TypeScript and
 * Python clients: an underscore goes before an uppercase letter that follows a
 * lowercase letter or a digit.
 */
public fun temperaSnakeCase(value: String): String {
    val out = StringBuilder(value.length + 4)
    var previous: Char? = null
    for (character in value) {
        val earlier = previous
        if (character.isUpperCase() &&
            earlier != null &&
            (earlier.isLowerCase() || earlier.isDigit())
        ) {
            out.append('_')
        }
        out.append(character.lowercaseChar())
        previous = character
    }
    return out.toString()
}

/** One product's client: registry metadata, typed operations, passthrough. */
public class TemperaProductClient internal constructor(
    private val client: TemperaClient,
    spec: TemperaProductSpec,
) {
    /** lowerCamelCase registry key. */
    public val key: String = spec.key
    /** Human-readable product name. */
    public val name: String = spec.name
    /** Source repository. */
    public val repository: String = spec.repository
    /** Environment variable carrying this product's base URL. */
    public val envVar: String = spec.envVar
    /** Token audience, when the product mints its own. */
    public val audience: String? = spec.audience
    /** One-sentence product description. */
    public val description: String = spec.description

    /** Every typed operation this product publishes. */
    public val operations: List<TemperaOperationSpec>
        get() = TemperaSurface.operationsFor(key)

    /** Invoke one typed operation by its lowerCamelCase id. */
    public fun call(
        operation: String,
        params: TemperaParams = emptyMap(),
        content: ByteArray? = null,
        headers: Map<String, String> = emptyMap(),
        bearer: String? = null,
    ): TemperaJson = client.call(key, operation, params, content, headers, bearer)

    /** Raw request against this product, for endpoints without a typed operation. */
    public fun request(
        path: String,
        method: String = "GET",
        body: TemperaJson? = null,
        query: List<TemperaKeyValue> = emptyList(),
        headers: Map<String, String> = emptyMap(),
        bearer: String? = null,
    ): TemperaJson = client.request(key, path, method, body, query, headers, bearer)
}

/** The unified Tempera client (see the file comment). */
public class TemperaClient(
    private val auth: TemperaAuth? = null,
    accountToken: String? = null,
    private val introspectionSecret: String? = null,
    private val baseUrls: Map<String, String> = emptyMap(),
    environment: String? = null,
    private val transport: TemperaTransport = JdkHttpTransport(),
    /** Timeout and retry knobs for every request this client makes. */
    public val configuration: TemperaClientConfiguration = TemperaClientConfiguration(),
    private val processEnvironment: Map<String, String> = System.getenv(),
    private val sleeper: (Double) -> Unit = { seconds ->
        if (seconds > 0) Thread.sleep((seconds * 1000).toLong())
    },
    private val random: () -> Double = { ThreadLocalRandom.current().nextDouble() },
) {
    /**
     * Account-session token used by `auth: "account"` (control-plane)
     * operations; `createHostedSession` stores the one it returns.
     */
    @Volatile public var accountToken: String? = accountToken

    private val environmentTarget: TemperaEnvironmentTarget? =
        if (environment == null) {
            null
        } else {
            TemperaSurface.findEnvironment(environment)
                ?: throw TemperaSdkException("unknown Tempera environment: " + environment)
        }

    /** One product's client, by registry key. */
    public fun product(key: String): TemperaProductClient {
        val spec =
            TemperaSurface.findProduct(key)
                ?: throw TemperaSdkException("unknown Tempera product: " + key)
        return TemperaProductClient(this, spec)
    }

    // ---------------------------------------------------------------- typed

    /** Invoke one typed operation. */
    public fun call(
        product: String,
        operation: String,
        params: TemperaParams = emptyMap(),
        content: ByteArray? = null,
        headers: Map<String, String> = emptyMap(),
        bearer: String? = null,
    ): TemperaJson {
        val response = callResponse(product, operation, params, content, headers, bearer)
        val value = decode(response)
        // createHostedSession returns the account-session token pair; storing it
        // here is what makes later control-plane calls authenticated.
        if (product == "controlPlane" && operation == "createHostedSession") {
            val token = value["access_token"]?.asString()
            if (token != null && token.isNotEmpty()) accountToken = token
        }
        return value
    }

    /**
     * Invoke one typed operation and return the whole HTTP response, for
     * operations whose response body is not JSON.
     */
    public fun callResponse(
        product: String,
        operation: String,
        params: TemperaParams = emptyMap(),
        content: ByteArray? = null,
        headers: Map<String, String> = emptyMap(),
        bearer: String? = null,
    ): TemperaHttpResponse {
        val op =
            TemperaSurface.findOperation(product, operation)
                ?: throw TemperaSdkException(
                    "unknown Tempera operation: " + product + "." + operation
                )
        val request = buildRequest(op, params, content, headers, bearer)
        return perform(request, op.safeRetry, product, operation)
    }

    /**
     * Build the HTTP request one typed operation would send, without sending
     * it.
     */
    public fun buildRequest(
        product: String,
        operation: String,
        params: TemperaParams = emptyMap(),
        content: ByteArray? = null,
        headers: Map<String, String> = emptyMap(),
        bearer: String? = null,
    ): TemperaHttpRequest {
        val op =
            TemperaSurface.findOperation(product, operation)
                ?: throw TemperaSdkException(
                    "unknown Tempera operation: " + product + "." + operation
                )
        return buildRequest(op, params, content, headers, bearer)
    }

    /**
     * Build the HTTP request one operation spec would send. Takes the spec
     * directly, so a caller that already resolved it -- or a test exercising a
     * contract feature no shipped operation uses yet -- does not look it up
     * again.
     */
    public fun buildRequest(
        op: TemperaOperationSpec,
        params: TemperaParams = emptyMap(),
        content: ByteArray? = null,
        headers: Map<String, String> = emptyMap(),
        bearer: String? = null,
    ): TemperaHttpRequest {
        val product = op.product
        val label = product + "." + op.id

        // 1. Parameter normalization: a declared parameter may arrive under its
        //    canonical wire name or its snake_case alias, never both.
        val wire = LinkedHashMap<String, TemperaJson>()
        for (entry in params) {
            wire[entry.key] = temperaJsonOf(entry.value)
        }
        val consumed = HashSet<String>()
        val declared = ArrayList<String>()
        declared.addAll(op.pathParams)
        declared.addAll(op.query)
        declared.addAll(op.body)
        declared.addAll(op.forbiddenBody)
        for (wireName in declared) {
            val alias = temperaSnakeCase(wireName)
            if (alias == wireName) continue
            val hasWireName = params.containsKey(wireName)
            val hasAlias = params.containsKey(alias)
            if (hasWireName && hasAlias) {
                throw TemperaSdkException(
                    label +
                        ": pass either \"" +
                        wireName +
                        "\" or its snake_case alias \"" +
                        alias +
                        "\", not both"
                )
            }
            if (hasAlias) {
                wire[wireName] = temperaJsonOf(params[alias])
                consumed.add(alias)
            }
        }

        // 2. Parameters the producer derives from the authenticated principal.
        for (key in op.forbiddenBody) {
            if (wire.containsKey(key)) {
                throw TemperaSdkException(
                    label + ": " + key + " is derived from the authenticated principal"
                )
            }
        }

        // 3. Path substitution, with AIP resource-pattern validation.
        val path = substitutePath(op, wire, label)
        consumed.addAll(op.pathParams)

        // 4. Declared query parameters.
        val query = ArrayList<TemperaKeyValue>()
        for (key in op.query) {
            val value = wire[key]
            if (value == null || value.isNull()) {
                if (op.requiredQuery.contains(key)) {
                    throw TemperaSdkException(
                        label + ": missing required query parameter \"" + key + "\""
                    )
                }
                continue
            }
            val text = value.plainText()
            if (text.isEmpty() && op.requiredQuery.contains(key)) {
                throw TemperaSdkException(
                    label + ": missing required query parameter \"" + key + "\""
                )
            }
            query.add(TemperaKeyValue(key, text))
            consumed.add(key)
        }

        // 5. Request body: declared fields over the operation's defaults, or a
        //    binary payload.
        val binary = op.requestBodyKind == "binary"
        var bodyMembers: MutableList<TemperaJsonMember>? = null
        var binaryContent: ByteArray? = null
        if (binary) {
            consumed.add("content")
            val inline = wire["content"]?.asString()
            binaryContent =
                content
                    ?: inline?.toByteArray(Charsets.UTF_8)
                    ?: throw TemperaSdkException(label + ": missing binary content")
        } else if (op.body.isNotEmpty() || op.bodyDefaults.isNotEmpty()) {
            val members = ArrayList<TemperaJsonMember>()
            for (pair in op.bodyDefaults) {
                members.add(TemperaJsonMember(pair.key, TemperaJson.Text(pair.value)))
            }
            for (key in op.body) {
                val value = wire[key] ?: continue
                setMember(members, key, value)
                consumed.add(key)
            }
            bodyMembers = members
        }

        // 6. Forward compatibility: undeclared parameters flow to the query
        //    string on GET/DELETE and into the JSON body otherwise, so a new
        //    server field is usable before the surface tables catch up.
        for (entry in params) {
            if (consumed.contains(entry.key)) continue
            val value = temperaJsonOf(entry.value)
            if (op.method == "GET" || op.method == "DELETE") {
                query.add(TemperaKeyValue(entry.key, value.plainText()))
            } else if (!binary) {
                val members = bodyMembers ?: ArrayList<TemperaJsonMember>()
                setMember(members, entry.key, value)
                bodyMembers = members
            } else {
                throw TemperaSdkException(
                    label +
                        ": binary operations only accept content plus declared " +
                        "path/query parameters"
                )
            }
        }

        val members = bodyMembers
        if (members != null) {
            temperaAssertCanonicalIdempotencyKeys(label, members)
        }

        val resolvedBearer =
            bearer ?: bearerFor(product, op.auth, op.authAudience)

        val requestHeaders = ArrayList<TemperaKeyValue>()
        requestHeaders.add(TemperaKeyValue("accept", "application/json"))
        if (binary) {
            requestHeaders.add(
                TemperaKeyValue(
                    "content-type",
                    op.requestContentType ?: "application/octet-stream",
                )
            )
        } else if (members != null) {
            requestHeaders.add(TemperaKeyValue("content-type", "application/json"))
        }
        if (resolvedBearer != null) {
            requestHeaders.add(TemperaKeyValue("authorization", "Bearer " + resolvedBearer))
        }
        applyHeaderOverrides(requestHeaders, headers)

        val payload =
            binaryContent ?: members?.let { TemperaJson.Obj(it).serializedBytes() }
        return TemperaHttpRequest(
            method = op.method,
            url = baseUrl(product) + path + queryString(query),
            headers = requestHeaders,
            body = payload,
            timeoutSeconds = configuration.timeoutSeconds,
        )
    }

    // ---------------------------------------------------------- passthrough

    /** Raw request against one product, for endpoints without a typed operation. */
    public fun request(
        product: String,
        path: String,
        method: String = "GET",
        body: TemperaJson? = null,
        query: List<TemperaKeyValue> = emptyList(),
        headers: Map<String, String> = emptyMap(),
        bearer: String? = null,
    ): TemperaJson {
        val spec =
            TemperaSurface.findProduct(product)
                ?: throw TemperaSdkException("unknown Tempera product: " + product)
        var resolvedBearer = bearer
        if (resolvedBearer == null && (spec.audience != null || product == "controlPlane")) {
            resolvedBearer =
                try {
                    bearerFor(
                        product,
                        if (product == "controlPlane") "account" else "product",
                        null,
                    )
                } catch (error: TemperaSdkException) {
                    null
                }
        }

        val requestHeaders = ArrayList<TemperaKeyValue>()
        requestHeaders.add(TemperaKeyValue("accept", "application/json"))
        if (body != null) {
            requestHeaders.add(TemperaKeyValue("content-type", "application/json"))
        }
        if (resolvedBearer != null) {
            requestHeaders.add(TemperaKeyValue("authorization", "Bearer " + resolvedBearer))
        }
        applyHeaderOverrides(requestHeaders, headers)

        val request =
            TemperaHttpRequest(
                method = method,
                url =
                    baseUrl(product) +
                        (if (path.startsWith("/")) path else "/" + path) +
                        queryString(query),
                headers = requestHeaders,
                body = body?.serializedBytes(),
                timeoutSeconds = configuration.timeoutSeconds,
            )
        val response =
            perform(
                request,
                TemperaRetryPolicy.safeRetryForMethod(method),
                product,
                null,
            )
        return decode(response)
    }

    // -------------------------------------------------------------- sending

    /**
     * Send one already-built request, retrying only when the operation's
     * classification and the failure both allow it.
     */
    public fun perform(
        request: TemperaHttpRequest,
        safeRetry: String,
        product: String?,
        operation: String?,
    ): TemperaHttpResponse {
        val policy = configuration.retry
        val budget = policy.attemptBudget(safeRetry)
        var attempt = 1
        while (true) {
            var retryAfter: Double? = null
            // Nullable rather than a `val` assigned in both branches: Kotlin's
            // definite-assignment analysis does not see through a try/catch.
            var failure: TemperaSdkException? = null
            try {
                // Every attempt sends the identical request value, so the body
                // and its idempotency key are byte-identical by construction.
                val response = transport.send(request)
                if (response.isSuccess()) return response
                val error =
                    TemperaApiException.from(
                        status = response.status,
                        statusText = response.statusText,
                        headers = response.headers,
                        body = response.json(),
                        product = product,
                        operation = operation,
                    )
                if (!policy.isRetryable(response.status)) throw error
                val header = response.header("retry-after")
                if (header != null) retryAfter = TemperaRetryPolicy.parseRetryAfter(header)
                failure = error
            } catch (error: TemperaTransportException) {
                // No HTTP response existed, which is transient by definition.
                failure = error
            }
            val problem = failure ?: throw TemperaSdkException("unreachable retry state")
            if (attempt >= budget) throw problem
            sleeper(policy.delaySeconds(attempt + 1, retryAfter, random()))
            attempt += 1
        }
    }

    // -------------------------------------------------------- configuration

    /**
     * The base URL for one product: an explicit override, then the product's
     * environment variable, then the environment preset.
     */
    public fun baseUrl(product: String): String {
        val spec =
            TemperaSurface.findProduct(product)
                ?: throw TemperaSdkException("unknown Tempera product: " + product)
        val fromEnvironment =
            environmentTarget?.let { environmentBaseUrl(it, product) }
        val candidates =
            listOf(baseUrls[product], processEnvironment[spec.envVar], fromEnvironment)
        val base = candidates.firstOrNull { it != null && it.isNotEmpty() }
        if (base == null) {
            throw TemperaSdkException(
                "missing base URL for " +
                    product +
                    "; set " +
                    spec.envVar +
                    " or pass baseUrls[\"" +
                    product +
                    "\"]"
            )
        }
        return temperaTrimTrailingSlashes(base)
    }

    /** The bearer for one operation's auth kind. */
    public fun bearerFor(product: String, authKind: String, authAudience: String?): String? {
        when (authKind) {
            "none" -> return null
            "introspectionSecret" -> {
                val secret = introspectionSecret
                if (secret == null || secret.isEmpty()) {
                    throw TemperaSdkException(
                        product + ": introspectToken requires the introspectionSecret option"
                    )
                }
                return secret
            }
            "account" -> {
                val token = accountToken
                if (token == null || token.isEmpty()) {
                    throw TemperaSdkException(
                        product +
                            ": an account token is required; call " +
                            "controlPlane.createHostedSession() first or pass accountToken"
                    )
                }
                return token
            }
            "oauthResource" -> {
                val audience = authAudience ?: TemperaSurface.defaultAudience
                val credential =
                    auth
                        ?: throw TemperaSdkException(
                            product +
                                ": pass a TemperaAuth with credentials permitted for audience " +
                                audience +
                                " by this operation"
                        )
                return credential.bearerFor(audience)
            }
            else -> {
                val audience =
                    TemperaSurface.findProduct(product)?.audience
                        ?: TemperaSurface.defaultAudience
                val credential =
                    auth
                        ?: throw TemperaSdkException(
                            product +
                                ": pass a TemperaAuth with credentials permitted for audience " +
                                audience +
                                " by this operation"
                        )
                return credential.bearerFor(audience)
            }
        }
    }

    public companion object {
        /** Environment presets only carry base URLs for these products. */
        public fun environmentBaseUrl(
            target: TemperaEnvironmentTarget,
            product: String,
        ): String? =
            when (product) {
                "controlPlane" -> target.controlPlaneUrl
                "palette" -> target.paletteApiUrl
                "tempo" -> target.tempoApiUrl
                "temperaLlm" -> target.temperaLlmApiUrl
                "temperaRisk" -> target.temperaRiskApiUrl
                "temperaWorkflows" -> target.temperaWorkflowsApiUrl
                "temperaGym" -> target.temperaGymUrl
                "dataEngine" -> target.dataEngineApiUrl
                "cradle" -> target.cradleApiUrl
                else -> null
            }

        internal fun decode(response: TemperaHttpResponse): TemperaJson {
            if (response.body.isEmpty()) return TemperaJson.Null
            val json = response.json()
            if (json != null) return json
            return TemperaJson.Text(String(response.body, Charsets.UTF_8))
        }

        internal fun setMember(
            members: MutableList<TemperaJsonMember>,
            key: String,
            value: TemperaJson,
        ) {
            val index = members.indexOfFirst { it.key == key }
            if (index >= 0) {
                members[index] = TemperaJsonMember(key, value)
            } else {
                members.add(TemperaJsonMember(key, value))
            }
        }

        internal fun applyHeaderOverrides(
            headers: MutableList<TemperaKeyValue>,
            overrides: Map<String, String>,
        ) {
            for (key in overrides.keys.sorted()) {
                val value = overrides[key] ?: continue
                val index = headers.indexOfFirst { it.key.lowercase() == key.lowercase() }
                if (index >= 0) {
                    headers[index] = TemperaKeyValue(key, value)
                } else {
                    headers.add(TemperaKeyValue(key, value))
                }
            }
        }

        internal fun queryString(query: List<TemperaKeyValue>): String {
            if (query.isEmpty()) return ""
            return "?" +
                query.joinToString("&") {
                    temperaPercentEncode(it.key) + "=" + temperaPercentEncode(it.value)
                }
        }

        /**
         * Substitute `{placeholder}` path parameters, percent-encoding ordinary
         * values and validating AIP resource patterns.
         */
        internal fun substitutePath(
            op: TemperaOperationSpec,
            params: Map<String, TemperaJson>,
            label: String,
        ): String {
            val out = StringBuilder()
            var index = 0
            val template = op.path
            while (index < template.length) {
                val open = template.indexOf('{', index)
                if (open < 0) break
                val close = template.indexOf('}', open)
                if (close < 0) break
                out.append(template, index, open)
                val name = template.substring(open + 1, close)
                val value = params[name]
                if (value == null || value.isNull() || value.plainText().isEmpty()) {
                    throw TemperaSdkException(
                        label + ": missing required path parameter \"" + name + "\""
                    )
                }
                val pattern = op.pathParamTemplates.firstOrNull { it.key == name }?.value
                out.append(expandPathParameter(value.plainText(), pattern, name, label))
                index = close + 1
            }
            out.append(template, index, template.length)
            return out.toString()
        }

        /**
         * Percent-encode one path parameter. A producer may declare an AIP
         * resource pattern whose wildcard segments stand for a caller-supplied
         * identifier; the structural slashes between segments survive only
         * after the value matches the pattern exactly.
         *
         * The pattern is deliberately not written out here: Kotlin block
         * comments nest, so a literal slash-star inside KDoc opens a comment
         * that the closing marker does not end, and the rest of the file is
         * swallowed.
         */
        internal fun expandPathParameter(
            value: String,
            pattern: String?,
            name: String,
            label: String,
        ): String {
            if (pattern == null) return temperaPercentEncode(value)
            val expected = pattern.split("/")
            val observed = value.split("/")
            val invalid =
                TemperaSdkException(
                    label +
                        ": path parameter \"" +
                        name +
                        "\" must match AIP resource pattern \"" +
                        pattern +
                        "\""
                )
            if (expected.size != observed.size) throw invalid
            val expanded = ArrayList<String>(expected.size)
            for (position in expected.indices) {
                val segment = expected[position]
                val actual = observed[position]
                if (segment == "*") {
                    if (actual.isEmpty() || actual == "." || actual == "..") throw invalid
                    expanded.add(temperaPercentEncode(actual))
                } else {
                    if (segment != actual) throw invalid
                    expanded.add(segment)
                }
            }
            return expanded.joinToString("/")
        }
    }
}
