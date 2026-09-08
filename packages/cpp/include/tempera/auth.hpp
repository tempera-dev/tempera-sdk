// Unified Tempera auth: PKCE (S256) helpers, audience-aware OAuth request
// builders, and a credential store that yields the right bearer per audience.
//
// The package is dependency-free and HTTP-less, so SHA-256 lives here rather
// than being linked, token endpoint bodies are returned as
// application/x-www-form-urlencoded strings for the caller's HTTP client, and
// refresh-token rotation is applied through apply_token_response().

#ifndef TEMPERA_AUTH_HPP
#define TEMPERA_AUTH_HPP

#include <array>
#include <cstdint>
#include <map>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "tempera/surface.hpp"

namespace tempera {

/// Percent-encode one value (RFC 3986 unreserved set).
inline std::string url_encode(std::string_view value) {
    static const char *const HEX = "0123456789ABCDEF";
    std::string out;
    out.reserve(value.size());
    for (unsigned char byte : value) {
        const bool unreserved = (byte >= 'A' && byte <= 'Z') || (byte >= 'a' && byte <= 'z') ||
                                (byte >= '0' && byte <= '9') || byte == '-' || byte == '.' ||
                                byte == '_' || byte == '~';
        if (unreserved) {
            out += static_cast<char>(byte);
        } else {
            out += '%';
            out += HEX[(byte >> 4) & 0x0f];
            out += HEX[byte & 0x0f];
        }
    }
    return out;
}

namespace detail {

inline constexpr std::array<std::uint32_t, 64> SHA256_K = {
    0x428a2f98U, 0x71374491U, 0xb5c0fbcfU, 0xe9b5dba5U, 0x3956c25bU, 0x59f111f1U, 0x923f82a4U,
    0xab1c5ed5U, 0xd807aa98U, 0x12835b01U, 0x243185beU, 0x550c7dc3U, 0x72be5d74U, 0x80deb1feU,
    0x9bdc06a7U, 0xc19bf174U, 0xe49b69c1U, 0xefbe4786U, 0x0fc19dc6U, 0x240ca1ccU, 0x2de92c6fU,
    0x4a7484aaU, 0x5cb0a9dcU, 0x76f988daU, 0x983e5152U, 0xa831c66dU, 0xb00327c8U, 0xbf597fc7U,
    0xc6e00bf3U, 0xd5a79147U, 0x06ca6351U, 0x14292967U, 0x27b70a85U, 0x2e1b2138U, 0x4d2c6dfcU,
    0x53380d13U, 0x650a7354U, 0x766a0abbU, 0x81c2c92eU, 0x92722c85U, 0xa2bfe8a1U, 0xa81a664bU,
    0xc24b8b70U, 0xc76c51a3U, 0xd192e819U, 0xd6990624U, 0xf40e3585U, 0x106aa070U, 0x19a4c116U,
    0x1e376c08U, 0x2748774cU, 0x34b0bcb5U, 0x391c0cb3U, 0x4ed8aa4aU, 0x5b9cca4fU, 0x682e6ff3U,
    0x748f82eeU, 0x78a5636fU, 0x84c87814U, 0x8cc70208U, 0x90befffaU, 0xa4506cebU, 0xbef9a3f7U,
    0xc67178f2U};

constexpr std::uint32_t rotate_right(std::uint32_t value, unsigned int bits) noexcept {
    return (value >> bits) | (value << (32 - bits));
}

inline void sha256_block(std::array<std::uint32_t, 8> &hash, const unsigned char *chunk) {
    std::array<std::uint32_t, 64> w{};
    for (std::size_t index = 0; index < 16; ++index) {
        w[index] = (static_cast<std::uint32_t>(chunk[4 * index]) << 24) |
                   (static_cast<std::uint32_t>(chunk[4 * index + 1]) << 16) |
                   (static_cast<std::uint32_t>(chunk[4 * index + 2]) << 8) |
                   static_cast<std::uint32_t>(chunk[4 * index + 3]);
    }
    for (std::size_t index = 16; index < 64; ++index) {
        const std::uint32_t s0 = rotate_right(w[index - 15], 7) ^ rotate_right(w[index - 15], 18) ^
                                 (w[index - 15] >> 3);
        const std::uint32_t s1 = rotate_right(w[index - 2], 17) ^ rotate_right(w[index - 2], 19) ^
                                 (w[index - 2] >> 10);
        w[index] = w[index - 16] + s0 + w[index - 7] + s1;
    }
    std::uint32_t a = hash[0];
    std::uint32_t b = hash[1];
    std::uint32_t c = hash[2];
    std::uint32_t d = hash[3];
    std::uint32_t e = hash[4];
    std::uint32_t f = hash[5];
    std::uint32_t g = hash[6];
    std::uint32_t h = hash[7];
    for (std::size_t index = 0; index < 64; ++index) {
        const std::uint32_t s1 = rotate_right(e, 6) ^ rotate_right(e, 11) ^ rotate_right(e, 25);
        const std::uint32_t ch = (e & f) ^ (~e & g);
        const std::uint32_t temp1 = h + s1 + ch + SHA256_K[index] + w[index];
        const std::uint32_t s0 = rotate_right(a, 2) ^ rotate_right(a, 13) ^ rotate_right(a, 22);
        const std::uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
        const std::uint32_t temp2 = s0 + maj;
        h = g;
        g = f;
        f = e;
        e = d + temp1;
        d = c;
        c = b;
        b = a;
        a = temp1 + temp2;
    }
    hash[0] += a;
    hash[1] += b;
    hash[2] += c;
    hash[3] += d;
    hash[4] += e;
    hash[5] += f;
    hash[6] += g;
    hash[7] += h;
}

inline std::array<unsigned char, 32> sha256(std::span<const unsigned char> data) {
    std::array<std::uint32_t, 8> hash = {0x6a09e667U, 0xbb67ae85U, 0x3c6ef372U, 0xa54ff53aU,
                                         0x510e527fU, 0x9b05688cU, 0x1f83d9abU, 0x5be0cd19U};
    std::size_t offset = 0;
    for (; offset + 64 <= data.size(); offset += 64) {
        sha256_block(hash, data.data() + offset);
    }
    std::vector<unsigned char> tail(data.begin() + static_cast<std::ptrdiff_t>(offset),
                                    data.end());
    const std::uint64_t bit_length = static_cast<std::uint64_t>(data.size()) * 8U;
    tail.push_back(0x80);
    while (tail.size() % 64 != 56) {
        tail.push_back(0);
    }
    for (int index = 0; index < 8; ++index) {
        tail.push_back(static_cast<unsigned char>((bit_length >> (56 - 8 * index)) & 0xffU));
    }
    for (std::size_t chunk = 0; chunk < tail.size(); chunk += 64) {
        sha256_block(hash, tail.data() + chunk);
    }
    std::array<unsigned char, 32> out{};
    for (std::size_t index = 0; index < 8; ++index) {
        out[4 * index] = static_cast<unsigned char>((hash[index] >> 24) & 0xffU);
        out[4 * index + 1] = static_cast<unsigned char>((hash[index] >> 16) & 0xffU);
        out[4 * index + 2] = static_cast<unsigned char>((hash[index] >> 8) & 0xffU);
        out[4 * index + 3] = static_cast<unsigned char>(hash[index] & 0xffU);
    }
    return out;
}

inline std::string form_encode(
    const std::vector<std::pair<std::string_view, std::string_view>> &params) {
    std::string out;
    for (const auto &[key, value] : params) {
        if (!out.empty()) {
            out += '&';
        }
        out += url_encode(key);
        out += '=';
        out += url_encode(value);
    }
    return out;
}

}  // namespace detail

/// Base64url without padding (RFC 4648 section 5), as PKCE requires.
inline std::string base64url_no_pad(std::span<const unsigned char> data) {
    static constexpr std::string_view ALPHABET =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
    std::string out;
    out.reserve((data.size() + 2) / 3 * 4);
    for (std::size_t offset = 0; offset < data.size(); offset += 3) {
        const std::size_t remaining = data.size() - offset;
        const std::uint32_t b0 = data[offset];
        const std::uint32_t b1 = remaining > 1 ? data[offset + 1] : 0U;
        const std::uint32_t b2 = remaining > 2 ? data[offset + 2] : 0U;
        const std::uint32_t triple = (b0 << 16) | (b1 << 8) | b2;
        out += ALPHABET[(triple >> 18) & 0x3fU];
        out += ALPHABET[(triple >> 12) & 0x3fU];
        if (remaining > 1) {
            out += ALPHABET[(triple >> 6) & 0x3fU];
        }
        if (remaining > 2) {
            out += ALPHABET[triple & 0x3fU];
        }
    }
    return out;
}

/// S256 code challenge: base64url(SHA-256(verifier)), no padding.
inline std::string pkce_challenge_s256(std::string_view verifier) {
    const std::span<const unsigned char> bytes(
        reinterpret_cast<const unsigned char *>(verifier.data()), verifier.size());
    const std::array<unsigned char, 32> digest = detail::sha256(bytes);
    return base64url_no_pad(digest);
}

/// Build a PKCE code verifier from CALLER-SUPPLIED entropy: the unpadded
/// base64url encoding of the bytes (RFC 7636 section 4.1).
///
/// The package is dependency-free and has no RNG, so callers MUST supply at
/// least 32 cryptographically random bytes (for example from the OS CSPRNG).
inline std::string pkce_verifier_from_entropy(std::span<const unsigned char> entropy) {
    return base64url_no_pad(entropy);
}

/// A PKCE verifier/challenge pair (always S256).
struct PkcePair {
    std::string verifier;
    std::string challenge;
    std::string_view method = "S256";
};

inline PkcePair pkce_pair_from_entropy(std::span<const unsigned char> entropy) {
    PkcePair pair;
    pair.verifier = pkce_verifier_from_entropy(entropy);
    pair.challenge = pkce_challenge_s256(pair.verifier);
    return pair;
}

/// Inputs to Auth::authorize_url().
struct AuthorizeUrlParams {
    std::string_view client_id;
    std::string_view redirect_uri;
    /// PKCE S256 code challenge (see pkce_pair_from_entropy).
    std::string_view code_challenge;
    /// Token audience, sent as the RFC 8707 `resource` parameter.
    std::string_view audience;
    /// Optional space-separated scope list.
    std::optional<std::string_view> scope;
    /// Optional opaque state echoed back on the redirect.
    std::optional<std::string_view> state;
};

/// One audience's stored OAuth tokens, as parsed from an /oauth/token response.
struct TokenSet {
    std::string access_token;
    std::optional<std::string> refresh_token;
    std::optional<std::uint64_t> expires_in;
    std::optional<std::string> scope;
};

/// One unified credential (API key or per-audience OAuth tokens) against one
/// issuer. Copyable value type: a Client holds its own copy.
class Auth {
public:
    /// Create a credential store against one issuer (for example the
    /// onboarding-provisioned staging issuer URL); a trailing slash is trimmed.
    explicit Auth(std::string issuer_url) : issuer_url_(std::move(issuer_url)) {
        while (!issuer_url_.empty() && issuer_url_.back() == '/') {
            issuer_url_.pop_back();
        }
    }

    Auth &with_client_id(std::string client_id) {
        client_id_ = std::move(client_id);
        return *this;
    }

    /// Set the central tp_ API key: the fallback bearer for every audience.
    Auth &with_api_key(std::string api_key) {
        api_key_ = std::move(api_key);
        return *this;
    }

    Auth &with_tokens(std::string audience, TokenSet tokens) {
        tokens_[std::move(audience)] = std::move(tokens);
        return *this;
    }

    [[nodiscard]] std::string_view issuer_url() const noexcept { return issuer_url_; }
    [[nodiscard]] const std::optional<std::string> &client_id() const noexcept {
        return client_id_;
    }
    [[nodiscard]] const std::optional<std::string> &api_key() const noexcept { return api_key_; }

    /// Unified MCP gateway (streamable HTTP MCP, audience tempera-mcp).
    [[nodiscard]] std::string mcp_url() const {
        return issuer_url_ + std::string(surface::MCP_PATH);
    }
    [[nodiscard]] std::string token_url() const {
        return issuer_url_ + std::string(surface::TOKEN_PATH);
    }
    [[nodiscard]] std::string revoke_url() const {
        return issuer_url_ + std::string(surface::REVOKE_PATH);
    }

    /// Authorize URL with PKCE (S256) and the RFC 8707 resource selector.
    [[nodiscard]] std::string authorize_url(const AuthorizeUrlParams &params) const {
        std::vector<std::pair<std::string_view, std::string_view>> query = {
            {"response_type", "code"},
            {"client_id", params.client_id},
            {"redirect_uri", params.redirect_uri},
            {"code_challenge", params.code_challenge},
            {"code_challenge_method", "S256"},
            {"resource", params.audience}};
        if (params.scope.has_value()) {
            query.emplace_back("scope", *params.scope);
        }
        if (params.state.has_value()) {
            query.emplace_back("state", *params.state);
        }
        return issuer_url_ + std::string(surface::AUTHORIZE_PATH) + "?" +
               detail::form_encode(query);
    }

    /// Form body to POST at token_url() to exchange an authorization code.
    [[nodiscard]] std::string code_exchange_body(std::string_view code,
                                                 std::string_view code_verifier,
                                                 std::string_view redirect_uri,
                                                 std::string_view audience) const {
        std::vector<std::pair<std::string_view, std::string_view>> params = {
            {"grant_type", "authorization_code"},
            {"code", code},
            {"code_verifier", code_verifier},
            {"redirect_uri", redirect_uri},
            {"resource", audience}};
        if (client_id_.has_value()) {
            params.emplace_back("client_id", *client_id_);
        }
        return detail::form_encode(params);
    }

    /// Form body to POST at token_url() to refresh the audience's tokens;
    /// std::nullopt when no refresh token is stored for the audience.
    [[nodiscard]] std::optional<std::string> refresh_body(std::string_view audience) const {
        const auto entry = tokens_.find(std::string(audience));
        if (entry == tokens_.end() || !entry->second.refresh_token.has_value()) {
            return std::nullopt;
        }
        std::vector<std::pair<std::string_view, std::string_view>> params = {
            {"grant_type", "refresh_token"},
            {"refresh_token", *entry->second.refresh_token},
            {"resource", audience}};
        if (client_id_.has_value()) {
            params.emplace_back("client_id", *client_id_);
        }
        return detail::form_encode(params);
    }

    /// Form body to POST at revoke_url(); also drops the stored token set.
    std::optional<std::string> revoke_body(std::string_view audience) {
        const auto entry = tokens_.find(std::string(audience));
        if (entry == tokens_.end()) {
            return std::nullopt;
        }
        const std::string token = entry->second.refresh_token.has_value()
                                      ? *entry->second.refresh_token
                                      : entry->second.access_token;
        std::vector<std::pair<std::string_view, std::string_view>> params = {
            {"token", token}, {"token_type_hint", "refresh_token"}};
        if (client_id_.has_value()) {
            params.emplace_back("client_id", *client_id_);
        }
        std::string body = detail::form_encode(params);
        tokens_.erase(entry);
        return body;
    }

    /// Store a parsed /oauth/token response for an audience. Refresh-token
    /// rotation: a newly issued refresh token replaces the old one; if the
    /// response omitted it, the previous refresh token is kept.
    const TokenSet &apply_token_response(std::string audience, std::string access_token,
                                         std::optional<std::string> refresh_token = std::nullopt,
                                         std::optional<std::uint64_t> expires_in = std::nullopt,
                                         std::optional<std::string> scope = std::nullopt) {
        TokenSet &slot = tokens_[audience];
        std::optional<std::string> previous_refresh = slot.refresh_token;
        slot.access_token = std::move(access_token);
        slot.refresh_token =
            refresh_token.has_value() ? std::move(refresh_token) : std::move(previous_refresh);
        slot.expires_in = expires_in;
        slot.scope = std::move(scope);
        return slot;
    }

    /// The bearer to present at a product server for the given audience: the
    /// audience's access token, falling back to the unified API key.
    [[nodiscard]] std::optional<std::string_view> bearer_for(std::string_view audience) const {
        const auto entry = tokens_.find(std::string(audience));
        if (entry != tokens_.end()) {
            return std::string_view(entry->second.access_token);
        }
        if (api_key_.has_value()) {
            return std::string_view(*api_key_);
        }
        return std::nullopt;
    }

    /// Authorization header value for the given audience.
    [[nodiscard]] std::optional<std::string> authorization_header(
        std::string_view audience) const {
        const std::optional<std::string_view> bearer = bearer_for(audience);
        if (!bearer.has_value()) {
            return std::nullopt;
        }
        return "Bearer " + std::string(*bearer);
    }

private:
    std::string issuer_url_;
    std::optional<std::string> client_id_;
    std::optional<std::string> api_key_;
    std::map<std::string, TokenSet> tokens_;
};

}  // namespace tempera

#endif  // TEMPERA_AUTH_HPP
