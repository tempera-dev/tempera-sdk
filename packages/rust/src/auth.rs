//! Unified Tempera auth: PKCE (S256) helpers, audience-aware OAuth request
//! builders, and a unified credential store that yields the right bearer per
//! product. The crate stays dependency-free, so token endpoint bodies are
//! returned as `application/x-www-form-urlencoded` strings for the caller's
//! HTTP client, and refresh-token rotation is applied via
//! [`TemperaAuth::apply_token_response`].

use std::collections::HashMap;

use crate::surface::{AUTHORIZE_PATH, MCP_PATH, REVOKE_PATH, TOKEN_PATH};

// Compat re-exports: these constants moved to the generated surface tables.
pub use crate::surface::{AUDIENCES, DEFAULT_AUDIENCE};

/// Compat table: product key -> (token audience, base-URL env var) for the
/// audience-bearing core products. The authoritative source is
/// [`crate::surface::PRODUCTS`] (`ProductSpec::audience` / `env_var`), which
/// also covers `human-data` and the passthrough products; prefer
/// [`crate::surface::find_product`].
pub const PRODUCT_AUDIENCES: &[(&str, &str, &str)] = &[
    ("palette", "palette", "TEMPERA_PALETTE_URL"),
    ("tempo", "tempo", "TEMPERA_TEMPO_URL"),
    ("tempera_llm", "tempera-llm", "TEMPERA_LLM_URL"),
    (
        "tempera_workflows",
        "tempera-workflows",
        "TEMPERA_WORKFLOWS_URL",
    ),
    ("tempera_gym", "tempera-gym", "TEMPERA_GYM_URL"),
    ("tempera_bio", "tempera-bio", "TEMPERA_BIO_URL"),
    ("cradle", "cradle", "TEMPERA_CRADLE_URL"),
    ("remi", "remi", "TEMPERA_REMI_URL"),
];

const SHA256_K: [u32; 64] = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

fn sha256(data: &[u8]) -> [u8; 32] {
    let mut hash: [u32; 8] = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab,
        0x5be0cd19,
    ];
    let mut message = data.to_vec();
    let bit_len = (data.len() as u64) * 8;
    message.push(0x80);
    while message.len() % 64 != 56 {
        message.push(0);
    }
    message.extend_from_slice(&bit_len.to_be_bytes());

    for chunk in message.chunks_exact(64) {
        let mut w = [0u32; 64];
        for (index, word) in w.iter_mut().take(16).enumerate() {
            *word = u32::from_be_bytes([
                chunk[4 * index],
                chunk[4 * index + 1],
                chunk[4 * index + 2],
                chunk[4 * index + 3],
            ]);
        }
        for index in 16..64 {
            let s0 = w[index - 15].rotate_right(7)
                ^ w[index - 15].rotate_right(18)
                ^ (w[index - 15] >> 3);
            let s1 = w[index - 2].rotate_right(17)
                ^ w[index - 2].rotate_right(19)
                ^ (w[index - 2] >> 10);
            w[index] = w[index - 16]
                .wrapping_add(s0)
                .wrapping_add(w[index - 7])
                .wrapping_add(s1);
        }

        let [mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut h] = hash;
        for index in 0..64 {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ ((!e) & g);
            let temp1 = h
                .wrapping_add(s1)
                .wrapping_add(ch)
                .wrapping_add(SHA256_K[index])
                .wrapping_add(w[index]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let temp2 = s0.wrapping_add(maj);
            h = g;
            g = f;
            f = e;
            e = d.wrapping_add(temp1);
            d = c;
            c = b;
            b = a;
            a = temp1.wrapping_add(temp2);
        }
        for (state, value) in hash.iter_mut().zip([a, b, c, d, e, f, g, h]) {
            *state = state.wrapping_add(value);
        }
    }

    let mut out = [0u8; 32];
    for (index, word) in hash.iter().enumerate() {
        out[4 * index..4 * index + 4].copy_from_slice(&word.to_be_bytes());
    }
    out
}

const BASE64URL_ALPHABET: &[u8; 64] =
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";

/// Base64url without padding (RFC 4648 section 5), as PKCE requires.
pub fn base64url_no_pad(data: &[u8]) -> String {
    let mut out = String::with_capacity(data.len().div_ceil(3) * 4);
    for chunk in data.chunks(3) {
        let b0 = chunk[0] as u32;
        let b1 = chunk.get(1).copied().unwrap_or(0) as u32;
        let b2 = chunk.get(2).copied().unwrap_or(0) as u32;
        let triple = (b0 << 16) | (b1 << 8) | b2;
        out.push(BASE64URL_ALPHABET[(triple >> 18) as usize & 0x3f] as char);
        out.push(BASE64URL_ALPHABET[(triple >> 12) as usize & 0x3f] as char);
        if chunk.len() > 1 {
            out.push(BASE64URL_ALPHABET[(triple >> 6) as usize & 0x3f] as char);
        }
        if chunk.len() > 2 {
            out.push(BASE64URL_ALPHABET[triple as usize & 0x3f] as char);
        }
    }
    out
}

/// S256 code challenge: base64url(SHA-256(verifier)), no padding.
pub fn pkce_challenge_s256(verifier: &str) -> String {
    base64url_no_pad(&sha256(verifier.as_bytes()))
}

/// Build a PKCE code verifier from caller-supplied entropy: the unpadded
/// base64url encoding of the bytes (RFC 7636 section 4.1).
///
/// The crate is dependency-free and has no RNG, so callers MUST supply at
/// least 32 cryptographically random bytes (e.g. from the OS CSPRNG).
pub fn pkce_verifier_from_entropy(entropy: &[u8]) -> String {
    base64url_no_pad(entropy)
}

/// A PKCE verifier/challenge pair (always `S256`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PkcePair {
    /// The code verifier to send with the token request.
    pub verifier: String,
    /// The S256 code challenge to send with the authorize request.
    pub challenge: String,
    /// The challenge method; always `"S256"`.
    pub method: &'static str,
}

/// Build a full PKCE pair from caller-supplied entropy (see
/// [`pkce_verifier_from_entropy`]; supply at least 32 cryptographically
/// random bytes).
pub fn pkce_pair_from_entropy(entropy: &[u8]) -> PkcePair {
    let verifier = pkce_verifier_from_entropy(entropy);
    let challenge = pkce_challenge_s256(&verifier);
    PkcePair {
        verifier,
        challenge,
        method: "S256",
    }
}

pub(crate) fn urlencode(value: &str) -> String {
    let mut out = String::with_capacity(value.len());
    for byte in value.bytes() {
        match byte {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'.' | b'_' | b'~' => {
                out.push(byte as char)
            }
            _ => out.push_str(&format!("%{byte:02X}")),
        }
    }
    out
}

fn form_encode(params: &[(&str, &str)]) -> String {
    params
        .iter()
        .map(|(key, value)| format!("{}={}", urlencode(key), urlencode(value)))
        .collect::<Vec<_>>()
        .join("&")
}

/// Inputs to [`TemperaAuth::authorize_url`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AuthorizeUrlParams<'a> {
    /// OAuth client id registered at the issuer.
    pub client_id: &'a str,
    /// Redirect URI; must match the token request exactly.
    pub redirect_uri: &'a str,
    /// PKCE S256 code challenge (see [`pkce_pair_from_entropy`]).
    pub code_challenge: &'a str,
    /// Token audience (RFC 8707 `resource` parameter).
    pub audience: &'a str,
    /// Optional space-separated scope list.
    pub scope: Option<&'a str>,
    /// Optional opaque state echoed back on the redirect.
    pub state: Option<&'a str>,
}

/// One audience's stored OAuth tokens, as parsed from an `/oauth/token`
/// response.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct TokenSet {
    /// The bearer access token for the audience.
    pub access_token: String,
    /// The refresh token, when the issuer granted one.
    pub refresh_token: Option<String>,
    /// Access-token lifetime in seconds, when the response carried one.
    pub expires_in: Option<u64>,
    /// Granted scope, when the response carried one.
    pub scope: Option<String>,
}

/// One unified credential (API key or per-audience OAuth tokens) against one issuer.
#[derive(Debug, Clone, Default)]
pub struct TemperaAuth {
    issuer_url: String,
    /// OAuth client id used in authorize/token/revoke requests.
    pub client_id: Option<String>,
    /// Central tp_ API key; the fallback bearer for every audience.
    pub api_key: Option<String>,
    tokens: HashMap<String, TokenSet>,
}

impl TemperaAuth {
    /// Create a credential store against one issuer (e.g.
    /// `https://api.tempera.dev`); a trailing slash is trimmed.
    pub fn new(issuer_url: impl Into<String>) -> Self {
        Self {
            issuer_url: issuer_url.into().trim_end_matches('/').to_string(),
            ..Self::default()
        }
    }

    /// Set the OAuth client id.
    pub fn with_client_id(mut self, client_id: impl Into<String>) -> Self {
        self.client_id = Some(client_id.into());
        self
    }

    /// Set the central tp_ API key (fallback bearer for every audience).
    pub fn with_api_key(mut self, api_key: impl Into<String>) -> Self {
        self.api_key = Some(api_key.into());
        self
    }

    /// Seed the store with a token set for one audience.
    pub fn with_tokens(mut self, audience: impl Into<String>, tokens: TokenSet) -> Self {
        self.tokens.insert(audience.into(), tokens);
        self
    }

    /// The issuer URL this credential targets (no trailing slash).
    pub fn issuer_url(&self) -> &str {
        &self.issuer_url
    }

    /// Unified MCP gateway (streamable HTTP MCP, audience `tempera-mcp`).
    pub fn mcp_url(&self) -> String {
        format!("{}{}", self.issuer_url, MCP_PATH)
    }

    /// The issuer's `/oauth/token` endpoint.
    pub fn token_url(&self) -> String {
        format!("{}{}", self.issuer_url, TOKEN_PATH)
    }

    /// The issuer's `/oauth/revoke` endpoint.
    pub fn revoke_url(&self) -> String {
        format!("{}{}", self.issuer_url, REVOKE_PATH)
    }

    /// Authorize URL with PKCE (S256) and the RFC 8707 `resource` audience selector.
    pub fn authorize_url(&self, params: &AuthorizeUrlParams<'_>) -> String {
        let mut query = vec![
            ("response_type", "code"),
            ("client_id", params.client_id),
            ("redirect_uri", params.redirect_uri),
            ("code_challenge", params.code_challenge),
            ("code_challenge_method", "S256"),
            ("resource", params.audience),
        ];
        if let Some(scope) = params.scope {
            query.push(("scope", scope));
        }
        if let Some(state) = params.state {
            query.push(("state", state));
        }
        format!(
            "{}{}?{}",
            self.issuer_url,
            AUTHORIZE_PATH,
            form_encode(&query)
        )
    }

    /// Form body to POST at [`Self::token_url`] to exchange an authorization code.
    pub fn code_exchange_body(
        &self,
        code: &str,
        code_verifier: &str,
        redirect_uri: &str,
        audience: &str,
    ) -> String {
        let mut params = vec![
            ("grant_type", "authorization_code"),
            ("code", code),
            ("code_verifier", code_verifier),
            ("redirect_uri", redirect_uri),
            ("resource", audience),
        ];
        if let Some(client_id) = self.client_id.as_deref() {
            params.push(("client_id", client_id));
        }
        form_encode(&params)
    }

    /// Form body to POST at [`Self::token_url`] to refresh the audience's tokens.
    /// Returns `None` when no refresh token is stored for the audience.
    pub fn refresh_body(&self, audience: &str) -> Option<String> {
        let refresh_token = self.tokens.get(audience)?.refresh_token.as_deref()?;
        let mut params = vec![
            ("grant_type", "refresh_token"),
            ("refresh_token", refresh_token),
            ("resource", audience),
        ];
        if let Some(client_id) = self.client_id.as_deref() {
            params.push(("client_id", client_id));
        }
        Some(form_encode(&params))
    }

    /// Form body to POST at [`Self::revoke_url`]; also drops the stored token set.
    pub fn revoke_body(&mut self, audience: &str) -> Option<String> {
        let tokens = self.tokens.remove(audience)?;
        let token = tokens.refresh_token.unwrap_or(tokens.access_token);
        let mut params = vec![
            ("token", token.as_str()),
            ("token_type_hint", "refresh_token"),
        ];
        if let Some(client_id) = self.client_id.as_deref() {
            params.push(("client_id", client_id));
        }
        Some(form_encode(&params))
    }

    /// Store a parsed `/oauth/token` response for an audience. Refresh-token
    /// rotation: a newly issued refresh token replaces the old one; if the
    /// response omitted it, the previous refresh token is kept. Use
    /// [`Self::apply_token_response_full`] to also record `expires_in` and
    /// `scope`.
    pub fn apply_token_response(
        &mut self,
        audience: impl Into<String>,
        access_token: impl Into<String>,
        refresh_token: Option<String>,
    ) -> &TokenSet {
        self.apply_token_response_full(audience, access_token, refresh_token, None, None)
    }

    /// Store a parsed `/oauth/token` response including its `expires_in` and
    /// `scope` members. Same refresh-token rotation as
    /// [`Self::apply_token_response`].
    pub fn apply_token_response_full(
        &mut self,
        audience: impl Into<String>,
        access_token: impl Into<String>,
        refresh_token: Option<String>,
        expires_in: Option<u64>,
        scope: Option<String>,
    ) -> &TokenSet {
        let audience = audience.into();
        let previous_refresh = self
            .tokens
            .get(&audience)
            .and_then(|tokens| tokens.refresh_token.clone());
        self.tokens.insert(
            audience.clone(),
            TokenSet {
                access_token: access_token.into(),
                refresh_token: refresh_token.or(previous_refresh),
                expires_in,
                scope,
            },
        );
        &self.tokens[&audience]
    }

    /// The bearer to present at a product server for the given audience:
    /// the audience's access token, falling back to the unified API key.
    pub fn bearer_for(&self, audience: &str) -> Option<&str> {
        self.tokens
            .get(audience)
            .map(|tokens| tokens.access_token.as_str())
            .or(self.api_key.as_deref())
    }

    /// `Authorization` header value for the given audience.
    pub fn authorization_header(&self, audience: &str) -> Option<String> {
        self.bearer_for(audience)
            .map(|token| format!("Bearer {token}"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pkce_challenge_matches_rfc7636_vector() {
        // RFC 7636 appendix B reference vector.
        let challenge = pkce_challenge_s256("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk");
        assert_eq!(challenge, "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM");
        assert!(!challenge.contains('='));
    }

    #[test]
    fn authorize_url_carries_resource_audience_and_s256_challenge() {
        let auth = TemperaAuth::new("https://api.tempera.dev/");
        let url = auth.authorize_url(&AuthorizeUrlParams {
            client_id: "client_1",
            redirect_uri: "https://app.example.test/callback",
            code_challenge: "challenge_1",
            audience: "tempo",
            scope: Some("trace:read trace:write"),
            state: Some("state_1"),
        });
        assert!(url.starts_with("https://api.tempera.dev/oauth/authorize?"));
        assert!(url.contains("response_type=code"));
        assert!(url.contains("resource=tempo"));
        assert!(url.contains("code_challenge=challenge_1"));
        assert!(url.contains("code_challenge_method=S256"));
        assert!(url.contains("scope=trace%3Aread%20trace%3Awrite"));
        assert!(AUDIENCES.contains(&DEFAULT_AUDIENCE));
    }

    #[test]
    fn token_bodies_propagate_resource_and_refresh_rotation_replaces_old_token() {
        let mut auth = TemperaAuth::new("https://api.tempera.dev").with_client_id("client_1");
        assert_eq!(auth.token_url(), "https://api.tempera.dev/oauth/token");

        let exchange = auth.code_exchange_body(
            "code_1",
            "verifier_1",
            "https://app.example.test/callback",
            "tempo",
        );
        assert!(exchange.contains("grant_type=authorization_code"));
        assert!(exchange.contains("resource=tempo"));
        assert!(exchange.contains("code_verifier=verifier_1"));

        auth.apply_token_response("tempo", "at_1", Some("rt_1".to_string()));
        assert!(
            auth.refresh_body("tempo")
                .unwrap()
                .contains("refresh_token=rt_1")
        );

        // Rotation: the newly issued refresh token replaces the old one.
        auth.apply_token_response("tempo", "at_2", Some("rt_2".to_string()));
        let body = auth.refresh_body("tempo").unwrap();
        assert!(body.contains("refresh_token=rt_2"));
        assert!(!body.contains("rt_1"));
        assert!(body.contains("resource=tempo"));

        // A response without a refresh token keeps the previous one.
        auth.apply_token_response("tempo", "at_3", None);
        assert!(
            auth.refresh_body("tempo")
                .unwrap()
                .contains("refresh_token=rt_2")
        );
        assert_eq!(auth.bearer_for("tempo"), Some("at_3"));

        let revoke = auth.revoke_body("tempo").unwrap();
        assert!(revoke.contains("token=rt_2"));
        assert!(auth.refresh_body("tempo").is_none());
    }

    #[test]
    fn bearer_matches_audience_with_api_key_fallback() {
        let auth = TemperaAuth::new("https://api.tempera.dev")
            .with_api_key("tp_key_1")
            .with_tokens(
                "tempo",
                TokenSet {
                    access_token: "at_tempo".into(),
                    ..TokenSet::default()
                },
            )
            .with_tokens(
                "remi",
                TokenSet {
                    access_token: "at_remi".into(),
                    ..TokenSet::default()
                },
            );
        assert_eq!(
            auth.authorization_header("tempo").as_deref(),
            Some("Bearer at_tempo")
        );
        assert_eq!(
            auth.authorization_header("remi").as_deref(),
            Some("Bearer at_remi")
        );
        // No cradle token: the unified API key is the fallback bearer.
        assert_eq!(
            auth.authorization_header("cradle").as_deref(),
            Some("Bearer tp_key_1")
        );
        assert_eq!(auth.mcp_url(), "https://api.tempera.dev/mcp");
        assert!(
            TemperaAuth::new("https://api.tempera.dev")
                .bearer_for("palette")
                .is_none()
        );
    }

    #[test]
    fn pkce_pair_from_entropy_matches_the_rfc7636_vector() {
        // RFC 7636 appendix B: the verifier's underlying octet sequence.
        let entropy: [u8; 32] = [
            116, 24, 223, 180, 151, 153, 224, 37, 79, 250, 96, 125, 216, 173, 187, 186, 22, 212,
            37, 77, 105, 214, 191, 240, 91, 88, 5, 88, 83, 132, 141, 121,
        ];
        assert_eq!(
            pkce_verifier_from_entropy(&entropy),
            "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        );
        let pair = pkce_pair_from_entropy(&entropy);
        assert_eq!(pair.verifier, "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk");
        assert_eq!(
            pair.challenge,
            "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
        );
        assert_eq!(pair.challenge, pkce_challenge_s256(&pair.verifier));
        assert_eq!(pair.method, "S256");
    }

    #[test]
    fn full_token_response_records_expiry_and_scope() {
        let mut auth = TemperaAuth::new("https://api.tempera.dev");
        let tokens = auth.apply_token_response_full(
            "palette",
            "at_1",
            Some("rt_1".to_string()),
            Some(3600),
            Some("trace:read trace:write".to_string()),
        );
        assert_eq!(tokens.expires_in, Some(3600));
        assert_eq!(tokens.scope.as_deref(), Some("trace:read trace:write"));
        // The two-token compat helper leaves the optional metadata unset.
        let tokens = auth.apply_token_response("palette", "at_2", None);
        assert_eq!(tokens.refresh_token.as_deref(), Some("rt_1"));
        assert_eq!(tokens.expires_in, None);
        assert_eq!(tokens.scope, None);
    }

    #[test]
    fn compat_product_audiences_agree_with_the_surface_tables() {
        for (product, audience, env_var) in PRODUCT_AUDIENCES {
            let spec = crate::surface::find_product(product).expect("product exists");
            assert_eq!(spec.audience, Some(*audience));
            assert_eq!(spec.env_var, *env_var);
        }
    }
}
