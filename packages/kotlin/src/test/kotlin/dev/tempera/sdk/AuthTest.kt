package dev.tempera.sdk

import java.net.URI
import java.net.URLDecoder
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows

class AuthTest {

    // ------------------------------------------------------------------ PKCE

    @Test
    fun sha256MatchesKnownVectors() {
        assertEquals(
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            hex(temperaSha256("abc".toByteArray(Charsets.UTF_8))),
        )
        assertEquals(
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            hex(temperaSha256(ByteArray(0))),
        )
    }

    @Test
    fun pkceChallengeMatchesRfc7636AppendixB() {
        // The RFC's own worked example.
        assertEquals(
            "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
            temperaPkceChallengeS256("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"),
        )
    }

    @Test
    fun generatedPkcePairsAreFreshUrlSafeAndSelfConsistent() {
        val first = temperaCreatePkcePair()
        val second = temperaCreatePkcePair()
        assertNotEquals(first.verifier, second.verifier)
        assertEquals("S256", first.method)
        assertEquals(temperaPkceChallengeS256(first.verifier), first.challenge)
        assertTrue(first.verifier.length >= 43)
        val allowed = Regex("^[A-Za-z0-9_-]+$")
        assertTrue(allowed.matches(first.verifier), first.verifier)
        assertTrue(allowed.matches(first.challenge), first.challenge)
    }

    @Test
    fun base64UrlIsUnpaddedAndUrlSafe() {
        assertEquals("Zg", temperaBase64UrlNoPad("f".toByteArray(Charsets.UTF_8)))
        assertEquals("Zm8", temperaBase64UrlNoPad("fo".toByteArray(Charsets.UTF_8)))
        assertEquals("Zm9v", temperaBase64UrlNoPad("foo".toByteArray(Charsets.UTF_8)))
        assertEquals(
            "-_8",
            temperaBase64UrlNoPad(byteArrayOf(0xFB.toByte(), 0xFF.toByte())),
        )
    }

    // --------------------------------------------------------- authorize URL

    @Test
    fun authorizeUrlCarriesPkceAndTheRfc8707ResourceParameter() {
        val auth =
            TemperaAuth(
                TestFixtures.ISSUER + "/",
                clientId = "client_1",
                apiKey = TestFixtures.API_KEY,
                transport = StubTransport(),
            )
        val url =
            auth.authorizeUrl(
                redirectUri = "https://app.example.test/callback",
                codeChallenge = "challenge_1",
                audience = "tempera-gym",
                scope = listOf("eval:run", "dataset:read"),
                state = "state 1",
            )
        assertTrue(url.startsWith(TestFixtures.ISSUER + "/oauth/authorize?"), url)
        val values = queryOf(url)
        assertEquals("code", values["response_type"])
        assertEquals("client_1", values["client_id"])
        assertEquals("https://app.example.test/callback", values["redirect_uri"])
        assertEquals("challenge_1", values["code_challenge"])
        assertEquals("S256", values["code_challenge_method"])
        assertEquals("tempera-gym", values["resource"])
        // Form encoding spells a space as `+`, exactly as the Python package's
        // urlencode does.
        assertEquals("eval:run dataset:read", values["scope"])
        assertEquals("state 1", values["state"])
        assertTrue(url.contains("scope=eval%3Arun+dataset%3Aread"), url)
    }

    @Test
    fun authorizeUrlNeedsAClientId() {
        val auth =
            TemperaAuth(TestFixtures.ISSUER, apiKey = TestFixtures.API_KEY, transport = StubTransport())
        assertSdkError("clientId is required") {
            auth.authorizeUrl(redirectUri = "https://x.test", codeChallenge = "c")
        }
    }

    @Test
    fun anEmptyIssuerIsRejected() {
        assertSdkError("issuerUrl is required") { TemperaAuth("") }
    }

    // ----------------------------------------------------------- token flows

    @Test
    fun exchangeCodePostsTheFormAndStoresTheAudiencesTokens() {
        val transport =
            StubTransport.always(
                """{"access_token":"at_1","refresh_token":"rt_1","expires_in":3600,"scope":"eval:run"}"""
            )
        val auth = TemperaAuth(TestFixtures.ISSUER, clientId = "client_1", transport = transport)

        val tokens =
            auth.exchangeCode(
                code = "code_1",
                codeVerifier = "verifier_1",
                redirectUri = "https://app.example.test/callback",
                audience = "tempera-gym",
            )
        assertEquals("at_1", tokens.accessToken)
        assertEquals("rt_1", tokens.refreshToken)
        assertEquals(3600L, tokens.expiresInSeconds)
        assertEquals("eval:run", tokens.scope)

        val request = transport.lastRequest()
        assertEquals("POST", request.method)
        assertEquals(TestFixtures.ISSUER + "/oauth/token", request.url)
        assertEquals("application/x-www-form-urlencoded", request.header("content-type"))
        assertEquals(
            "grant_type=authorization_code&code=code_1&code_verifier=verifier_1" +
                "&redirect_uri=https%3A%2F%2Fapp.example.test%2Fcallback" +
                "&resource=tempera-gym&client_id=client_1",
            transport.lastBodyText(),
        )
        assertEquals("at_1", auth.bearerFor("tempera-gym"))
    }

    @Test
    fun refreshRotatesTheRefreshTokenAndKeepsTheOldOneWhenAbsent() {
        val rotating = StubTransport.always("""{"access_token":"at_2","refresh_token":"rt_2"}""")
        val auth =
            TemperaAuth(
                TestFixtures.ISSUER,
                tokens = mapOf("palette" to TemperaTokenSet("at_1", "rt_1")),
                transport = rotating,
            )
        val rotated = auth.refresh("palette")
        assertEquals("at_2", rotated.accessToken)
        assertEquals("rt_2", rotated.refreshToken)
        assertEquals(
            "grant_type=refresh_token&refresh_token=rt_1&resource=palette",
            rotating.lastBodyText(),
        )

        val silent = StubTransport.always("""{"access_token":"at_3"}""")
        val kept =
            TemperaAuth(
                TestFixtures.ISSUER,
                tokens = mapOf("palette" to TemperaTokenSet("at_1", "rt_1")),
                transport = silent,
            )
        assertEquals("rt_1", kept.refresh("palette").refreshToken)
    }

    @Test
    fun refreshWithoutATokenFails() {
        val auth = TemperaAuth(TestFixtures.ISSUER, transport = StubTransport())
        assertSdkError("no refresh token for audience palette") { auth.refresh("palette") }
    }

    @Test
    fun revokeDropsTheAudienceFromTheStore() {
        val transport = StubTransport.always("{}")
        val auth =
            TemperaAuth(
                TestFixtures.ISSUER,
                tokens = mapOf("palette" to TemperaTokenSet("at_1", "rt_1")),
                transport = transport,
            )
        auth.revoke("palette")
        assertEquals(TestFixtures.ISSUER + "/oauth/revoke", transport.lastRequest().url)
        assertEquals("token=rt_1&token_type_hint=refresh_token", transport.lastBodyText())
        assertNull(auth.tokenSetFor("palette"))
    }

    @Test
    fun tokenEndpointErrorsBecomeApiErrors() {
        val transport =
            StubTransport.always(
                """{"error":"invalid_grant","message":"code expired"}""",
                status = 401,
            )
        val auth = TemperaAuth(TestFixtures.ISSUER, transport = transport)
        val error =
            assertThrows<TemperaApiException> {
                auth.exchangeCode(code = "c", codeVerifier = "v", redirectUri = "https://x.test")
            }
        assertEquals(401, error.status)
        assertEquals("invalid_grant", error.code)
        assertEquals("controlPlane", error.product)
    }

    // ------------------------------------------------------ bearer resolution

    @Test
    fun bearerPrefersTheAudienceTokenThenFallsBackToTheApiKey() {
        val auth =
            TemperaAuth(
                TestFixtures.ISSUER,
                apiKey = "tp_fallback",
                tokens = mapOf("palette" to TemperaTokenSet("at_palette")),
                transport = StubTransport(),
            )
        assertEquals("at_palette", auth.bearerFor("palette"))
        assertEquals("tp_fallback", auth.bearerFor("tempo"))

        val bare = TemperaAuth(TestFixtures.ISSUER, transport = StubTransport())
        assertSdkError("no credential for audience tempo") { bare.bearerFor("tempo") }
    }

    @Test
    fun issuerDerivedUrlsUseTheGeneratedPaths() {
        val auth = TemperaAuth("https://api.tempera.dev///", transport = StubTransport())
        assertEquals("https://api.tempera.dev", auth.issuerUrl)
        assertEquals("https://api.tempera.dev" + TemperaSurface.mcpPath, auth.mcpUrl)
        assertEquals("https://api.tempera.dev" + TemperaSurface.tokenPath, auth.tokenUrl)
        assertEquals("https://api.tempera.dev" + TemperaSurface.revokePath, auth.revokeUrl)
    }

    private fun hex(bytes: ByteArray): String {
        val out = StringBuilder(bytes.size * 2)
        for (byte in bytes) {
            out.append(String.format("%02x", byte.toInt() and 0xFF))
        }
        return out.toString()
    }

    private fun queryOf(url: String): Map<String, String> {
        val values = LinkedHashMap<String, String>()
        val raw = URI(url).rawQuery ?: return values
        for (item in raw.split("&")) {
            val separator = item.indexOf('=')
            values[URLDecoder.decode(item.substring(0, separator), "UTF-8")] =
                URLDecoder.decode(item.substring(separator + 1), "UTF-8")
        }
        return values
    }
}
