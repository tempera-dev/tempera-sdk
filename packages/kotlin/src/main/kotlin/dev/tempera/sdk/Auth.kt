// Unified Tempera auth: PKCE (S256) helpers, audience-aware OAuth flows, and
// one credential store that yields the right bearer per product.
//
// The flows mirror `packages/python/src/tempera_sdk/auth.py`:
// authorization-code + PKCE with the RFC 8707 `resource` parameter selecting
// the audience, refresh-token rotation, and a central `tp_` API key that works
// as a bearer everywhere. SHA-256, base64url, and the CSPRNG come from the
// JDK, so the package still has no external dependencies.

package dev.tempera.sdk

import java.security.MessageDigest
import java.security.SecureRandom
import java.util.Base64

/** One audience's stored OAuth tokens, as parsed from an `/oauth/token` response. */
public data class TemperaTokenSet(
    /** The bearer access token for the audience. */
    public val accessToken: String,
    /** The refresh token, when the issuer granted one. */
    public val refreshToken: String? = null,
    /** Access-token lifetime in seconds, when the response carried one. */
    public val expiresInSeconds: Long? = null,
    /** Granted scope, when the response carried one. */
    public val scope: String? = null,
)

/** A PKCE verifier/challenge pair (always `S256`). */
public data class TemperaPkcePair(
    /** The code verifier to send with the token request. */
    public val verifier: String,
    /** The S256 code challenge to send with the authorize request. */
    public val challenge: String,
) {
    /** The challenge method; always `S256`. */
    public val method: String = "S256"
}

/**
 * Percent-encode one component, escaping everything outside the RFC 3986
 * unreserved set. Matches `urlencode` in the Rust crate and
 * `urllib.parse.quote(safe="")` in the Python package.
 */
public fun temperaPercentEncode(value: String): String {
    val out = StringBuilder(value.length)
    for (byte in value.toByteArray(Charsets.UTF_8)) {
        val code = byte.toInt() and 0xFF
        val unreserved =
            (code in 0x41..0x5A) ||
                (code in 0x61..0x7A) ||
                (code in 0x30..0x39) ||
                code == 0x2D ||
                code == 0x2E ||
                code == 0x5F ||
                code == 0x7E
        if (unreserved) {
            out.append(Char(code))
        } else {
            out.append(String.format("%%%02X", code))
        }
    }
    return out.toString()
}

/** Encode `application/x-www-form-urlencoded` pairs, in order. */
public fun temperaFormEncode(pairs: List<Pair<String, String>>): String =
    pairs.joinToString("&") { pair ->
        // Percent-encoding already escaped a literal `+` as %2B, so the
        // space-to-plus rewrite is unambiguous.
        val key = temperaPercentEncode(pair.first).replace("%20", "+")
        val value = temperaPercentEncode(pair.second).replace("%20", "+")
        key + "=" + value
    }

/** Base64url without padding (RFC 4648 section 5), as PKCE requires. */
public fun temperaBase64UrlNoPad(data: ByteArray): String =
    Base64.getUrlEncoder().withoutPadding().encodeToString(data)

/** SHA-256 of the given bytes. */
public fun temperaSha256(data: ByteArray): ByteArray =
    MessageDigest.getInstance("SHA-256").digest(data)

/** A PKCE code verifier built from fresh system entropy (RFC 7636 section 4.1). */
public fun temperaGeneratePkceVerifier(byteLength: Int = 32): String {
    val bytes = ByteArray(maxOf(32, byteLength))
    SecureRandom().nextBytes(bytes)
    return temperaBase64UrlNoPad(bytes)
}

/** S256 code challenge: base64url(SHA-256(verifier)), no padding. */
public fun temperaPkceChallengeS256(verifier: String): String =
    temperaBase64UrlNoPad(temperaSha256(verifier.toByteArray(Charsets.US_ASCII)))

/** Create a `(verifier, challenge, S256)` PKCE pair from system entropy. */
public fun temperaCreatePkcePair(): TemperaPkcePair {
    val verifier = temperaGeneratePkceVerifier()
    return TemperaPkcePair(verifier, temperaPkceChallengeS256(verifier))
}

/** Trim any trailing slashes from a base URL. */
public fun temperaTrimTrailingSlashes(url: String): String = url.trimEnd('/')

/**
 * Build the `/oauth/authorize` URL with PKCE and the RFC 8707 `resource`
 * audience selector.
 */
public fun temperaAuthorizeUrl(
    issuerUrl: String,
    clientId: String,
    redirectUri: String,
    codeChallenge: String,
    audience: String = TemperaSurface.defaultAudience,
    scope: List<String> = emptyList(),
    state: String? = null,
): String {
    val query = ArrayList<Pair<String, String>>()
    query.add("response_type" to "code")
    query.add("client_id" to clientId)
    query.add("redirect_uri" to redirectUri)
    query.add("code_challenge" to codeChallenge)
    query.add("code_challenge_method" to "S256")
    query.add("resource" to audience)
    if (scope.isNotEmpty()) query.add("scope" to scope.joinToString(" "))
    if (state != null) query.add("state" to state)
    return temperaTrimTrailingSlashes(issuerUrl) +
        TemperaSurface.authorizePath +
        "?" +
        temperaFormEncode(query)
}

/**
 * One unified credential (a central `tp_` API key, per-audience OAuth tokens,
 * or both) against one issuer.
 *
 * The token store mutates on refresh and rotation and one credential is
 * routinely shared across threads, so every access to it is synchronized.
 */
public class TemperaAuth(
    issuerUrl: String,
    /** OAuth client id used in authorize, token, and revoke requests. */
    public val clientId: String? = null,
    /** Central `tp_` API key; the fallback bearer for every audience. */
    public val apiKey: String? = null,
    tokens: Map<String, TemperaTokenSet> = emptyMap(),
    private val transport: TemperaTransport = defaultTemperaTransport(),
    private val configuration: TemperaClientConfiguration = TemperaClientConfiguration(),
) {
    /** The issuer this credential targets (no trailing slash). */
    public val issuerUrl: String = temperaTrimTrailingSlashes(issuerUrl)

    private val tokens: MutableMap<String, TemperaTokenSet> = LinkedHashMap(tokens)

    init {
        if (this.issuerUrl.isEmpty()) {
            throw TemperaSdkException("issuerUrl is required (e.g. https://api.tempera.dev)")
        }
    }

    /** Unified MCP gateway URL (streamable-HTTP MCP, audience `tempera-mcp`). */
    public val mcpUrl: String
        get() = issuerUrl + TemperaSurface.mcpPath

    /** The issuer's `/oauth/token` endpoint. */
    public val tokenUrl: String
        get() = issuerUrl + TemperaSurface.tokenPath

    /** The issuer's `/oauth/revoke` endpoint. */
    public val revokeUrl: String
        get() = issuerUrl + TemperaSurface.revokePath

    /**
     * The bearer for an audience: its access token, falling back to the `tp_`
     * API key.
     */
    @Synchronized
    public fun bearerFor(audience: String = TemperaSurface.defaultAudience): String {
        val token = tokens[audience]?.accessToken
        if (token != null && token.isNotEmpty()) return token
        if (apiKey != null && apiKey.isNotEmpty()) return apiKey
        throw TemperaSdkException(
            "no credential for audience " +
                audience +
                "; provide an apiKey or tokens[\"" +
                audience +
                "\"]"
        )
    }

    /** One audience's stored tokens. */
    @Synchronized
    public fun tokenSetFor(audience: String): TemperaTokenSet? = tokens[audience]

    /** Replace one audience's stored tokens. */
    @Synchronized
    public fun setTokenSet(audience: String, tokenSet: TemperaTokenSet) {
        tokens[audience] = tokenSet
    }

    /** Build the authorize URL for this issuer and client. */
    public fun authorizeUrl(
        redirectUri: String,
        codeChallenge: String,
        audience: String = TemperaSurface.defaultAudience,
        scope: List<String> = emptyList(),
        state: String? = null,
        clientId: String? = null,
    ): String {
        val client =
            clientId
                ?: this.clientId
                ?: throw TemperaSdkException("clientId is required to build an authorize URL")
        return temperaAuthorizeUrl(
            issuerUrl = issuerUrl,
            clientId = client,
            redirectUri = redirectUri,
            codeChallenge = codeChallenge,
            audience = audience,
            scope = scope,
            state = state,
        )
    }

    /** Exchange an authorization code (PKCE) for the audience's token set. */
    public fun exchangeCode(
        code: String,
        codeVerifier: String,
        redirectUri: String,
        audience: String = TemperaSurface.defaultAudience,
    ): TemperaTokenSet {
        val params = ArrayList<Pair<String, String>>()
        params.add("grant_type" to "authorization_code")
        params.add("code" to code)
        params.add("code_verifier" to codeVerifier)
        params.add("redirect_uri" to redirectUri)
        params.add("resource" to audience)
        if (clientId != null) params.add("client_id" to clientId)
        return store(audience, post(TemperaSurface.tokenPath, params))
    }

    /**
     * Refresh the audience's tokens; rotation stores the newly issued refresh
     * token.
     */
    public fun refresh(audience: String = TemperaSurface.defaultAudience): TemperaTokenSet {
        val current = tokenSetFor(audience)
        val refreshToken = current?.refreshToken
        if (refreshToken == null || refreshToken.isEmpty()) {
            throw TemperaSdkException("no refresh token for audience " + audience)
        }
        val params = ArrayList<Pair<String, String>>()
        params.add("grant_type" to "refresh_token")
        params.add("refresh_token" to refreshToken)
        params.add("resource" to audience)
        if (clientId != null) params.add("client_id" to clientId)
        return store(audience, post(TemperaSurface.tokenPath, params))
    }

    /** Revoke the audience's token at the issuer and drop it from the store. */
    public fun revoke(
        audience: String = TemperaSurface.defaultAudience,
        tokenTypeHint: String = "refresh_token",
    ) {
        val current = tokenSetFor(audience)
        val token =
            if (tokenTypeHint == "access_token") {
                current?.accessToken
            } else {
                current?.refreshToken ?: current?.accessToken
            }
        if (token == null || token.isEmpty()) {
            throw TemperaSdkException("no token to revoke for audience " + audience)
        }
        val params = ArrayList<Pair<String, String>>()
        params.add("token" to token)
        params.add("token_type_hint" to tokenTypeHint)
        if (clientId != null) params.add("client_id" to clientId)
        post(TemperaSurface.revokePath, params)
        forget(audience)
    }

    @Synchronized
    private fun forget(audience: String) {
        tokens.remove(audience)
    }

    @Synchronized
    private fun store(audience: String, token: TemperaJson?): TemperaTokenSet {
        val previous = tokens[audience]
        val tokenSet =
            TemperaTokenSet(
                accessToken = token?.get("access_token")?.asString() ?: "",
                // Refresh-token rotation: a newly issued refresh token replaces
                // the old one, and its absence keeps the old one.
                refreshToken =
                    token?.get("refresh_token")?.asString() ?: previous?.refreshToken,
                expiresInSeconds = token?.get("expires_in")?.asLong(),
                scope = token?.get("scope")?.asString(),
            )
        tokens[audience] = tokenSet
        return tokenSet
    }

    private fun post(path: String, params: List<Pair<String, String>>): TemperaJson? {
        val request =
            TemperaHttpRequest(
                method = "POST",
                url = issuerUrl + path,
                headers =
                    listOf(
                        TemperaKeyValue("accept", "application/json"),
                        TemperaKeyValue("content-type", "application/x-www-form-urlencoded"),
                    ),
                body = temperaFormEncode(params).toByteArray(Charsets.UTF_8),
                timeoutSeconds = configuration.timeoutSeconds,
            )
        val response = transport.send(request)
        if (!response.isSuccess()) {
            throw TemperaApiException.from(
                status = response.status,
                statusText = response.statusText,
                headers = response.headers,
                body = response.json(),
                product = "controlPlane",
                operation = path,
            )
        }
        return response.json()
    }
}
