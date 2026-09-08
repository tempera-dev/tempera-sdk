import Foundation
import XCTest

@testable import TemperaSDK

final class AuthTests: XCTestCase {

    // MARK: - PKCE

    func testSha256MatchesKnownVectors() {
        let digest = temperaSha256(Array("abc".utf8))
        XCTAssertEqual(
            digest.map { String(format: "%02x", $0) }.joined(),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        )
        let empty = temperaSha256([])
        XCTAssertEqual(
            empty.map { String(format: "%02x", $0) }.joined(),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
        // Longer than one 64-byte block, to exercise the message schedule.
        let long = temperaSha256(Array(String(repeating: "a", count: 200).utf8))
        XCTAssertEqual(long.count, 32)
    }

    func testPkceChallengeMatchesRfc7636AppendixB() {
        // The RFC's own worked example.
        let verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        XCTAssertEqual(
            temperaPkceChallengeS256(verifier), "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM")
    }

    func testGeneratedPkcePairsAreFreshUrlSafeAndSelfConsistent() {
        let first = temperaCreatePkcePair()
        let second = temperaCreatePkcePair()
        XCTAssertNotEqual(first.verifier, second.verifier)
        XCTAssertEqual(first.method, "S256")
        XCTAssertEqual(first.challenge, temperaPkceChallengeS256(first.verifier))
        XCTAssertGreaterThanOrEqual(first.verifier.count, 43)
        let allowed = CharacterSet(charactersIn: "-_").union(.alphanumerics)
        XCTAssertTrue(first.verifier.unicodeScalars.allSatisfy(allowed.contains))
        XCTAssertTrue(first.challenge.unicodeScalars.allSatisfy(allowed.contains))
    }

    func testBase64UrlIsUnpaddedAndUrlSafe() {
        XCTAssertEqual(temperaBase64UrlNoPad(Array("f".utf8)), "Zg")
        XCTAssertEqual(temperaBase64UrlNoPad(Array("fo".utf8)), "Zm8")
        XCTAssertEqual(temperaBase64UrlNoPad(Array("foo".utf8)), "Zm9v")
        XCTAssertEqual(temperaBase64UrlNoPad([0xFB, 0xFF]), "-_8")
    }

    // MARK: - Authorize URL

    func testAuthorizeUrlCarriesPkceAndTheRfc8707ResourceParameter() throws {
        let auth = try TemperaAuth(
            issuerUrl: "\(TestFixtures.issuer)/", clientId: "client_1", apiKey: TestFixtures.apiKey)
        let url = try auth.authorizeUrl(
            redirectUri: "https://app.example.test/callback",
            codeChallenge: "challenge_1",
            audience: "tempera-gym",
            scope: ["eval:run", "dataset:read"],
            state: "state 1"
        )
        XCTAssertTrue(url.hasPrefix("\(TestFixtures.issuer)/oauth/authorize?"))
        let query = URLComponents(string: url)?.queryItems ?? []
        var values: [String: String] = [:]
        for item in query { values[item.name] = item.value }
        XCTAssertEqual(values["response_type"], "code")
        XCTAssertEqual(values["client_id"], "client_1")
        XCTAssertEqual(values["redirect_uri"], "https://app.example.test/callback")
        XCTAssertEqual(values["code_challenge"], "challenge_1")
        XCTAssertEqual(values["code_challenge_method"], "S256")
        XCTAssertEqual(values["resource"], "tempera-gym")
        // Form encoding spells a space as `+`, exactly as the Python package's
        // urlencode does, so URLComponents reports it verbatim.
        XCTAssertEqual(values["scope"], "eval:run+dataset:read")
        XCTAssertEqual(values["state"], "state+1")
        XCTAssertTrue(url.contains("scope=eval%3Arun+dataset%3Aread"), url)
    }

    func testAuthorizeUrlNeedsAClientId() throws {
        let auth = try TemperaAuth(issuerUrl: TestFixtures.issuer, apiKey: TestFixtures.apiKey)
        XCTAssertThrowsError(
            try auth.authorizeUrl(redirectUri: "https://x.test", codeChallenge: "c"))
    }

    func testAnEmptyIssuerIsRejected() {
        XCTAssertThrowsError(try TemperaAuth(issuerUrl: "")) { error in
            XCTAssertTrue((error as? TemperaSdkError)?.message.contains("issuerUrl") ?? false)
        }
    }

    // MARK: - Token flows

    private func tokenTransport(_ body: String) -> StubTransport {
        StubTransport(responder: { _, _ in
            TemperaHTTPResponse(
                status: 200,
                headers: [TemperaKeyValue(key: "content-type", value: "application/json")],
                body: Data(body.utf8)
            )
        })
    }

    func testExchangeCodePostsTheFormAndStoresTheAudiencesTokens() async throws {
        let transport = tokenTransport(
            #"{"access_token":"at_1","refresh_token":"rt_1","expires_in":3600,"scope":"eval:run"}"#)
        let auth = try TemperaAuth(
            issuerUrl: TestFixtures.issuer, clientId: "client_1", transport: transport)

        let tokens = try await auth.exchangeCode(
            code: "code_1",
            codeVerifier: "verifier_1",
            redirectUri: "https://app.example.test/callback",
            audience: "tempera-gym"
        )
        XCTAssertEqual(tokens.accessToken, "at_1")
        XCTAssertEqual(tokens.refreshToken, "rt_1")
        XCTAssertEqual(tokens.expiresIn, 3600)
        XCTAssertEqual(tokens.scope, "eval:run")

        let request = try await lastRequest(transport)
        XCTAssertEqual(request.method, "POST")
        XCTAssertEqual(request.url, "\(TestFixtures.issuer)/oauth/token")
        XCTAssertEqual(request.header("content-type"), "application/x-www-form-urlencoded")
        let form = String(data: try XCTUnwrap(request.body), encoding: .utf8)
        XCTAssertEqual(
            form,
            "grant_type=authorization_code&code=code_1&code_verifier=verifier_1"
                + "&redirect_uri=https%3A%2F%2Fapp.example.test%2Fcallback"
                + "&resource=tempera-gym&client_id=client_1"
        )

        let bearer = try await auth.bearer(for: "tempera-gym")
        XCTAssertEqual(bearer, "at_1")
    }

    func testRefreshRotatesTheRefreshTokenAndKeepsTheOldOneWhenAbsent() async throws {
        let rotating = tokenTransport(#"{"access_token":"at_2","refresh_token":"rt_2"}"#)
        let auth = try TemperaAuth(
            issuerUrl: TestFixtures.issuer,
            tokens: ["palette": TemperaTokenSet(accessToken: "at_1", refreshToken: "rt_1")],
            transport: rotating
        )
        let rotated = try await auth.refresh(audience: "palette")
        XCTAssertEqual(rotated.accessToken, "at_2")
        XCTAssertEqual(rotated.refreshToken, "rt_2")
        let form = try await lastBodyText(rotating)
        XCTAssertEqual(form, "grant_type=refresh_token&refresh_token=rt_1&resource=palette")

        let silent = tokenTransport(#"{"access_token":"at_3"}"#)
        let kept = try TemperaAuth(
            issuerUrl: TestFixtures.issuer,
            tokens: ["palette": TemperaTokenSet(accessToken: "at_1", refreshToken: "rt_1")],
            transport: silent
        )
        let refreshed = try await kept.refresh(audience: "palette")
        XCTAssertEqual(refreshed.refreshToken, "rt_1")
    }

    func testRefreshWithoutATokenFails() async throws {
        let auth = try TemperaAuth(issuerUrl: TestFixtures.issuer, transport: StubTransport())
        await assertSdkError("no refresh token for audience palette") {
            _ = try await auth.refresh(audience: "palette")
        }
    }

    func testRevokeDropsTheAudienceFromTheStore() async throws {
        let transport = tokenTransport("{}")
        let auth = try TemperaAuth(
            issuerUrl: TestFixtures.issuer,
            tokens: ["palette": TemperaTokenSet(accessToken: "at_1", refreshToken: "rt_1")],
            transport: transport
        )
        try await auth.revoke(audience: "palette")
        let request = try await lastRequest(transport)
        XCTAssertEqual(request.url, "\(TestFixtures.issuer)/oauth/revoke")
        XCTAssertEqual(
            String(data: try XCTUnwrap(request.body), encoding: .utf8),
            "token=rt_1&token_type_hint=refresh_token"
        )
        let stored = await auth.tokenSet(for: "palette")
        XCTAssertNil(stored)
    }

    func testTokenEndpointErrorsBecomeApiErrors() async throws {
        let transport = StubTransport(responder: { _, _ in
            TemperaHTTPResponse(
                status: 401,
                headers: [TemperaKeyValue(key: "content-type", value: "application/json")],
                body: Data(#"{"error":"invalid_grant","message":"code expired"}"#.utf8)
            )
        })
        let auth = try TemperaAuth(issuerUrl: TestFixtures.issuer, transport: transport)
        do {
            _ = try await auth.exchangeCode(
                code: "c", codeVerifier: "v", redirectUri: "https://x.test")
            XCTFail("expected a TemperaApiError")
        } catch let error as TemperaApiError {
            XCTAssertEqual(error.status, 401)
            XCTAssertEqual(error.code, "invalid_grant")
            XCTAssertEqual(error.product, "controlPlane")
        }
    }

    // MARK: - Bearer resolution

    func testBearerPrefersTheAudienceTokenThenFallsBackToTheApiKey() async throws {
        let auth = try TemperaAuth(
            issuerUrl: TestFixtures.issuer,
            apiKey: "tp_fallback",
            tokens: ["palette": TemperaTokenSet(accessToken: "at_palette")],
            transport: StubTransport()
        )
        let palette = try await auth.bearer(for: "palette")
        XCTAssertEqual(palette, "at_palette")
        let other = try await auth.bearer(for: "tempo")
        XCTAssertEqual(other, "tp_fallback")

        let bare = try TemperaAuth(issuerUrl: TestFixtures.issuer, transport: StubTransport())
        await assertSdkError("no credential for audience tempo") {
            _ = try await bare.bearer(for: "tempo")
        }
    }

    func testIssuerDerivedUrlsUseTheGeneratedPaths() throws {
        let auth = try TemperaAuth(issuerUrl: "https://api.tempera.dev///")
        XCTAssertEqual(auth.issuerUrl, "https://api.tempera.dev")
        XCTAssertEqual(auth.mcpUrl, "https://api.tempera.dev\(TemperaSurface.mcpPath)")
        XCTAssertEqual(auth.tokenUrl, "https://api.tempera.dev\(TemperaSurface.tokenPath)")
        XCTAssertEqual(auth.revokeUrl, "https://api.tempera.dev\(TemperaSurface.revokePath)")
    }
}
