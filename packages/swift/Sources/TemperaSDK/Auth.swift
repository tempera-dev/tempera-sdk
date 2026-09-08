// Unified Tempera auth: PKCE (S256) helpers, audience-aware OAuth flows, and
// one credential store that yields the right bearer per product.
//
// The package has no external dependencies, so SHA-256 and base64url are
// implemented here rather than pulled from CryptoKit (Apple-only) or
// swift-crypto (a package dependency). The flows mirror
// `packages/python/src/tempera_sdk/auth.py`: authorization-code + PKCE with
// the RFC 8707 `resource` parameter selecting the audience, refresh-token
// rotation, and a central `tp_` API key that works as a bearer everywhere.

import Foundation

/// One audience's stored OAuth tokens, as parsed from an `/oauth/token`
/// response.
public struct TemperaTokenSet: Sendable, Equatable {
    /// The bearer access token for the audience.
    public var accessToken: String
    /// The refresh token, when the issuer granted one.
    public var refreshToken: String?
    /// Access-token lifetime in seconds, when the response carried one.
    public var expiresIn: Int?
    /// Granted scope, when the response carried one.
    public var scope: String?

    /// Create one token set.
    public init(
        accessToken: String,
        refreshToken: String? = nil,
        expiresIn: Int? = nil,
        scope: String? = nil
    ) {
        self.accessToken = accessToken
        self.refreshToken = refreshToken
        self.expiresIn = expiresIn
        self.scope = scope
    }
}

/// A PKCE verifier/challenge pair (always `S256`).
public struct TemperaPkcePair: Sendable, Equatable {
    /// The code verifier to send with the token request.
    public let verifier: String
    /// The S256 code challenge to send with the authorize request.
    public let challenge: String
    /// The challenge method; always `S256`.
    public let method: String = "S256"

    /// Create one pair.
    public init(verifier: String, challenge: String) {
        self.verifier = verifier
        self.challenge = challenge
    }
}

/// Percent-encode one component, escaping everything outside the RFC 3986
/// unreserved set. Matches `urlencode` in the Rust crate and
/// `urllib.parse.quote(safe="")` in the Python package.
public func temperaPercentEncode(_ value: String) -> String {
    var out = String()
    out.reserveCapacity(value.utf8.count)
    for byte in value.utf8 {
        switch byte {
        case 0x41...0x5A, 0x61...0x7A, 0x30...0x39, 0x2D, 0x2E, 0x5F, 0x7E:
            out.append(Character(Unicode.Scalar(byte)))
        default:
            out += String(format: "%%%02X", byte)
        }
    }
    return out
}

/// Encode `application/x-www-form-urlencoded` pairs, in order.
public func temperaFormEncode(_ pairs: [(String, String)]) -> String {
    pairs
        .map { key, value in
            // Percent-encoding already escaped a literal `+` as %2B, so the
            // space-to-plus rewrite is unambiguous.
            let encodedKey = temperaPercentEncode(key).replacingOccurrences(of: "%20", with: "+")
            let encodedValue = temperaPercentEncode(value)
                .replacingOccurrences(of: "%20", with: "+")
            return "\(encodedKey)=\(encodedValue)"
        }
        .joined(separator: "&")
}

/// Base64url without padding (RFC 4648 section 5), as PKCE requires.
public func temperaBase64UrlNoPad(_ data: [UInt8]) -> String {
    let alphabet = Array("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
    var out = String()
    out.reserveCapacity((data.count + 2) / 3 * 4)
    var index = 0
    while index < data.count {
        let b0 = UInt32(data[index])
        let b1 = index + 1 < data.count ? UInt32(data[index + 1]) : 0
        let b2 = index + 2 < data.count ? UInt32(data[index + 2]) : 0
        let triple = (b0 << 16) | (b1 << 8) | b2
        out.append(alphabet[Int((triple >> 18) & 0x3F)])
        out.append(alphabet[Int((triple >> 12) & 0x3F)])
        if index + 1 < data.count { out.append(alphabet[Int((triple >> 6) & 0x3F)]) }
        if index + 2 < data.count { out.append(alphabet[Int(triple & 0x3F)]) }
        index += 3
    }
    return out
}

private let sha256K: [UInt32] = [
    0x428a_2f98, 0x7137_4491, 0xb5c0_fbcf, 0xe9b5_dba5, 0x3956_c25b, 0x59f1_11f1, 0x923f_82a4,
    0xab1c_5ed5, 0xd807_aa98, 0x1283_5b01, 0x2431_85be, 0x550c_7dc3, 0x72be_5d74, 0x80de_b1fe,
    0x9bdc_06a7, 0xc19b_f174, 0xe49b_69c1, 0xefbe_4786, 0x0fc1_9dc6, 0x240c_a1cc, 0x2de9_2c6f,
    0x4a74_84aa, 0x5cb0_a9dc, 0x76f9_88da, 0x983e_5152, 0xa831_c66d, 0xb003_27c8, 0xbf59_7fc7,
    0xc6e0_0bf3, 0xd5a7_9147, 0x06ca_6351, 0x1429_2967, 0x27b7_0a85, 0x2e1b_2138, 0x4d2c_6dfc,
    0x5338_0d13, 0x650a_7354, 0x766a_0abb, 0x81c2_c92e, 0x9272_2c85, 0xa2bf_e8a1, 0xa81a_664b,
    0xc24b_8b70, 0xc76c_51a3, 0xd192_e819, 0xd699_0624, 0xf40e_3585, 0x106a_a070, 0x19a4_c116,
    0x1e37_6c08, 0x2748_774c, 0x34b0_bcb5, 0x391c_0cb3, 0x4ed8_aa4a, 0x5b9c_ca4f, 0x682e_6ff3,
    0x748f_82ee, 0x78a5_636f, 0x84c8_7814, 0x8cc7_0208, 0x90be_fffa, 0xa450_6ceb, 0xbef9_a3f7,
    0xc671_78f2,
]

/// SHA-256, dependency-free; the Swift counterpart of the one in
/// `packages/rust/src/auth.rs`.
public func temperaSha256(_ input: [UInt8]) -> [UInt8] {
    var hash: [UInt32] = [
        0x6a09_e667, 0xbb67_ae85, 0x3c6e_f372, 0xa54f_f53a, 0x510e_527f, 0x9b05_688c, 0x1f83_d9ab,
        0x5be0_cd19,
    ]
    var message = input
    let bitLength = UInt64(input.count) * 8
    message.append(0x80)
    while message.count % 64 != 56 { message.append(0) }
    for shift in stride(from: 56, through: 0, by: -8) {
        message.append(UInt8((bitLength >> UInt64(shift)) & 0xFF))
    }

    var chunkStart = 0
    while chunkStart < message.count {
        var w = [UInt32](repeating: 0, count: 64)
        for index in 0..<16 {
            let base = chunkStart + index * 4
            w[index] =
                (UInt32(message[base]) << 24) | (UInt32(message[base + 1]) << 16)
                | (UInt32(message[base + 2]) << 8) | UInt32(message[base + 3])
        }
        for index in 16..<64 {
            let s0 =
                rotateRight(w[index - 15], 7) ^ rotateRight(w[index - 15], 18) ^ (w[index - 15] >> 3)
            let s1 =
                rotateRight(w[index - 2], 17) ^ rotateRight(w[index - 2], 19) ^ (w[index - 2] >> 10)
            w[index] = w[index - 16] &+ s0 &+ w[index - 7] &+ s1
        }

        var a = hash[0], b = hash[1], c = hash[2], d = hash[3]
        var e = hash[4], f = hash[5], g = hash[6], h = hash[7]
        for index in 0..<64 {
            let s1 = rotateRight(e, 6) ^ rotateRight(e, 11) ^ rotateRight(e, 25)
            let ch = (e & f) ^ (~e & g)
            let temp1 = h &+ s1 &+ ch &+ sha256K[index] &+ w[index]
            let s0 = rotateRight(a, 2) ^ rotateRight(a, 13) ^ rotateRight(a, 22)
            let maj = (a & b) ^ (a & c) ^ (b & c)
            let temp2 = s0 &+ maj
            h = g
            g = f
            f = e
            e = d &+ temp1
            d = c
            c = b
            b = a
            a = temp1 &+ temp2
        }
        hash[0] = hash[0] &+ a
        hash[1] = hash[1] &+ b
        hash[2] = hash[2] &+ c
        hash[3] = hash[3] &+ d
        hash[4] = hash[4] &+ e
        hash[5] = hash[5] &+ f
        hash[6] = hash[6] &+ g
        hash[7] = hash[7] &+ h
        chunkStart += 64
    }

    var out = [UInt8]()
    out.reserveCapacity(32)
    for word in hash {
        out.append(UInt8((word >> 24) & 0xFF))
        out.append(UInt8((word >> 16) & 0xFF))
        out.append(UInt8((word >> 8) & 0xFF))
        out.append(UInt8(word & 0xFF))
    }
    return out
}

private func rotateRight(_ value: UInt32, _ amount: UInt32) -> UInt32 {
    (value >> amount) | (value << (32 - amount))
}

/// A PKCE code verifier built from fresh system entropy (RFC 7636 §4.1).
public func temperaGeneratePkceVerifier(byteLength: Int = 32) -> String {
    var generator = SystemRandomNumberGenerator()
    let bytes = (0..<max(32, byteLength)).map { _ in UInt8.random(in: 0...255, using: &generator) }
    return temperaBase64UrlNoPad(bytes)
}

/// S256 code challenge: base64url(SHA-256(verifier)), no padding.
public func temperaPkceChallengeS256(_ verifier: String) -> String {
    temperaBase64UrlNoPad(temperaSha256(Array(verifier.utf8)))
}

/// Create a `(verifier, challenge, S256)` PKCE pair from system entropy.
public func temperaCreatePkcePair() -> TemperaPkcePair {
    let verifier = temperaGeneratePkceVerifier()
    return TemperaPkcePair(verifier: verifier, challenge: temperaPkceChallengeS256(verifier))
}

/// Build the `/oauth/authorize` URL with PKCE and the RFC 8707 `resource`
/// audience selector.
public func temperaAuthorizeUrl(
    issuerUrl: String,
    clientId: String,
    redirectUri: String,
    codeChallenge: String,
    audience: String = TemperaSurface.defaultAudience,
    scope: [String] = [],
    state: String? = nil
) -> String {
    var query: [(String, String)] = [
        ("response_type", "code"),
        ("client_id", clientId),
        ("redirect_uri", redirectUri),
        ("code_challenge", codeChallenge),
        ("code_challenge_method", "S256"),
        ("resource", audience),
    ]
    if !scope.isEmpty { query.append(("scope", scope.joined(separator: " "))) }
    if let state { query.append(("state", state)) }
    let issuer = temperaTrimTrailingSlashes(issuerUrl)
    return "\(issuer)\(TemperaSurface.authorizePath)?\(temperaFormEncode(query))"
}

/// Trim any trailing slashes from a base URL.
public func temperaTrimTrailingSlashes(_ url: String) -> String {
    var trimmed = Substring(url)
    while trimmed.hasSuffix("/") { trimmed = trimmed.dropLast() }
    return String(trimmed)
}

/// One unified credential (a central `tp_` API key, per-audience OAuth tokens,
/// or both) against one issuer.
///
/// An actor: the token store mutates on refresh and rotation, and a client is
/// routinely shared across concurrent requests.
public actor TemperaAuth {
    /// The issuer this credential targets (no trailing slash).
    ///
    /// The three configuration properties are `nonisolated`: they never change
    /// after `init`, so reading them costs no actor hop.
    public nonisolated let issuerUrl: String
    /// OAuth client id used in authorize, token, and revoke requests.
    public nonisolated let clientId: String?
    /// Central `tp_` API key; the fallback bearer for every audience.
    public nonisolated let apiKey: String?

    private var tokens: [String: TemperaTokenSet]
    private let transport: any TemperaTransport
    private let configuration: TemperaClientConfiguration

    /// Create a credential store against one issuer (e.g.
    /// `https://api.tempera.dev`); a trailing slash is trimmed.
    public init(
        issuerUrl: String,
        clientId: String? = nil,
        apiKey: String? = nil,
        tokens: [String: TemperaTokenSet] = [:],
        transport: (any TemperaTransport)? = nil,
        configuration: TemperaClientConfiguration = TemperaClientConfiguration()
    ) throws {
        guard !issuerUrl.isEmpty else {
            throw TemperaSdkError("issuerUrl is required (e.g. https://api.tempera.dev)")
        }
        self.issuerUrl = temperaTrimTrailingSlashes(issuerUrl)
        self.clientId = clientId
        self.apiKey = apiKey
        self.tokens = tokens
        self.transport = transport ?? TemperaURLSessionTransport()
        self.configuration = configuration
    }

    /// Unified MCP gateway URL (streamable-HTTP MCP, audience `tempera-mcp`).
    public nonisolated var mcpUrl: String { "\(issuerUrl)\(TemperaSurface.mcpPath)" }

    /// The issuer's `/oauth/token` endpoint.
    public nonisolated var tokenUrl: String { "\(issuerUrl)\(TemperaSurface.tokenPath)" }

    /// The issuer's `/oauth/revoke` endpoint.
    public nonisolated var revokeUrl: String { "\(issuerUrl)\(TemperaSurface.revokePath)" }

    /// The bearer for an audience: its access token, falling back to the `tp_`
    /// API key.
    public func bearer(for audience: String = TemperaSurface.defaultAudience) throws -> String {
        if let token = tokens[audience]?.accessToken, !token.isEmpty { return token }
        if let apiKey, !apiKey.isEmpty { return apiKey }
        throw TemperaSdkError(
            "no credential for audience \(audience); provide an apiKey or tokens[\"\(audience)\"]"
        )
    }

    /// One audience's stored tokens.
    public func tokenSet(for audience: String) -> TemperaTokenSet? { tokens[audience] }

    /// Replace one audience's stored tokens.
    public func setTokenSet(_ tokenSet: TemperaTokenSet, for audience: String) {
        tokens[audience] = tokenSet
    }

    /// Build the authorize URL for this issuer and client.
    public nonisolated func authorizeUrl(
        redirectUri: String,
        codeChallenge: String,
        audience: String = TemperaSurface.defaultAudience,
        scope: [String] = [],
        state: String? = nil,
        clientId overrideClientId: String? = nil
    ) throws -> String {
        guard let client = overrideClientId ?? clientId else {
            throw TemperaSdkError("clientId is required to build an authorize URL")
        }
        return temperaAuthorizeUrl(
            issuerUrl: issuerUrl,
            clientId: client,
            redirectUri: redirectUri,
            codeChallenge: codeChallenge,
            audience: audience,
            scope: scope,
            state: state
        )
    }

    /// Exchange an authorization code (PKCE) for the audience's token set.
    public func exchangeCode(
        code: String,
        codeVerifier: String,
        redirectUri: String,
        audience: String = TemperaSurface.defaultAudience
    ) async throws -> TemperaTokenSet {
        var params: [(String, String)] = [
            ("grant_type", "authorization_code"),
            ("code", code),
            ("code_verifier", codeVerifier),
            ("redirect_uri", redirectUri),
            ("resource", audience),
        ]
        if let clientId { params.append(("client_id", clientId)) }
        let response = try await post(path: TemperaSurface.tokenPath, params: params)
        return store(audience: audience, token: response)
    }

    /// Refresh the audience's tokens; rotation stores the newly issued refresh
    /// token.
    public func refresh(audience: String = TemperaSurface.defaultAudience) async throws
        -> TemperaTokenSet
    {
        guard let refreshToken = tokens[audience]?.refreshToken, !refreshToken.isEmpty else {
            throw TemperaSdkError("no refresh token for audience \(audience)")
        }
        var params: [(String, String)] = [
            ("grant_type", "refresh_token"),
            ("refresh_token", refreshToken),
            ("resource", audience),
        ]
        if let clientId { params.append(("client_id", clientId)) }
        let response = try await post(path: TemperaSurface.tokenPath, params: params)
        return store(audience: audience, token: response)
    }

    /// Revoke the audience's token at the issuer and drop it from the store.
    public func revoke(
        audience: String = TemperaSurface.defaultAudience,
        tokenTypeHint: String = "refresh_token"
    ) async throws {
        let current = tokens[audience]
        let token =
            tokenTypeHint == "access_token"
            ? current?.accessToken
            : (current?.refreshToken ?? current?.accessToken)
        guard let token, !token.isEmpty else {
            throw TemperaSdkError("no token to revoke for audience \(audience)")
        }
        var params: [(String, String)] = [("token", token), ("token_type_hint", tokenTypeHint)]
        if let clientId { params.append(("client_id", clientId)) }
        _ = try await post(path: TemperaSurface.revokePath, params: params)
        tokens.removeValue(forKey: audience)
    }

    private func store(audience: String, token: TemperaJSON?) -> TemperaTokenSet {
        let previous = tokens[audience]
        let tokenSet = TemperaTokenSet(
            accessToken: token?["access_token"]?.stringValue ?? "",
            // Refresh-token rotation: a newly issued refresh token replaces the
            // old one, and its absence keeps the old one.
            refreshToken: token?["refresh_token"]?.stringValue ?? previous?.refreshToken,
            expiresIn: token?["expires_in"]?.intValue,
            scope: token?["scope"]?.stringValue
        )
        tokens[audience] = tokenSet
        return tokenSet
    }

    private func post(path: String, params: [(String, String)]) async throws -> TemperaJSON? {
        let request = TemperaHTTPRequest(
            method: "POST",
            url: "\(issuerUrl)\(path)",
            headers: [
                TemperaKeyValue(key: "accept", value: "application/json"),
                TemperaKeyValue(key: "content-type", value: "application/x-www-form-urlencoded"),
            ],
            body: Data(temperaFormEncode(params).utf8),
            timeout: configuration.timeout
        )
        let response = try await transport.send(request)
        guard response.isSuccess else {
            throw TemperaApiError.from(
                status: response.status,
                statusText: response.statusText,
                headers: response.headers,
                body: response.json,
                product: "controlPlane",
                operation: path
            )
        }
        return response.json
    }
}
