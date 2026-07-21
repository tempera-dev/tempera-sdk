//! Dependency-free Tempera SDK for Rust.
//!
//! The crate is HTTP-less by design: it builds request URLs, headers, and
//! bodies for the caller's own HTTP client instead of sending them. Every
//! product, audience, scope, environment target, and typed operation comes
//! from the generated surface tables in [`surface`] (from `surface.json`),
//! shared verbatim with the TypeScript and Python packages.
//!
//! - [`surface`]: the generated tables (products, operations, environments,
//!   MCP methods, error-code constants). GENERATED — never edit by hand.
//! - [`auth`]: PKCE (S256) helpers, audience-aware OAuth request builders,
//!   and the unified per-audience credential store with tp_ API-key fallback.
//! - [`client`]: [`TemperaClient`] turns `(product, operation, params)` into
//!   a fully-described [`RequestSpec`].
//! - [`error`]: [`TemperaApiError`] and [`normalize_error_body`], folding the
//!   five fleet wire error shapes into one type.
//! - [`mcp`]: JSON-RPC 2.0 body builders for the unified MCP gateway.

pub mod auth;
pub mod client;
pub mod error;
pub mod mcp;
pub mod surface;

pub use auth::{
    AuthorizeUrlParams, PkcePair, TemperaAuth, TokenSet, base64url_no_pad, pkce_challenge_s256,
    pkce_pair_from_entropy, pkce_verifier_from_entropy,
};
pub use client::{BuildError, ParamValue, RequestSpec, TemperaClient};
pub use error::{TemperaApiError, normalize_error_body};
pub use mcp::{MCP_PROTOCOL_VERSION, McpError, McpRequestBuilder, parse_mcp_error};
pub use surface::{
    AUDIENCES, AUTHORIZE_PATH, DEFAULT_AUDIENCE, ENVIRONMENTS, EnvironmentTarget, INTROSPECT_PATH,
    MCP_ERROR_INTERNAL, MCP_ERROR_INVALID_PARAMS, MCP_ERROR_INVALID_REQUEST,
    MCP_ERROR_METHOD_NOT_FOUND, MCP_ERROR_PLAN_LIMIT, MCP_METHODS, MCP_PATH, McpMethodSpec,
    OPERATIONS, OperationSpec, PRODUCTS, ProductSpec, REVOKE_PATH, SCOPES, SURFACE_VERSION,
    TOKEN_PATH, find_operation, find_product,
};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn surface_tables_replace_the_legacy_hand_written_consts() {
        // Every legacy product is present in the generated table, by key.
        for key in [
            "control_plane",
            "palette",
            "tempo",
            "tempera_code",
            "tempera_llm",
            "tempera_workflows",
            "tempera_gym",
            "cradle",
            "remi",
            "data_engine",
            "human_data",
            "temp_js",
            "temp_o_s",
            "arrha",
        ] {
            assert!(find_product(key).is_some(), "missing product {key}");
        }
        assert_eq!(find_product("palette").unwrap().audience, Some("palette"));
        assert!(SCOPES.contains(&"mcp:invoke"));
        assert!(SCOPES.contains(&"model:read"));
        assert!(SCOPES.contains(&"model:invoke"));
        assert!(SCOPES.contains(&"training:publish"));
        assert!(SCOPES.contains(&"review:gold:manage"));
        assert!(SCOPES.contains(&"admin"));
        assert!(AUDIENCES.contains(&DEFAULT_AUDIENCE));
        assert!(AUDIENCES.contains(&"tempera-code"));
        assert!(AUDIENCES.contains(&"tempera-llm"));
        assert!(AUDIENCES.contains(&"tempera-workflows"));
        assert!(AUDIENCES.contains(&"tempera-gym"));
        assert!(SCOPES.contains(&"workflow:read"));
        assert!(SCOPES.contains(&"workflow:write"));
        assert!(SCOPES.contains(&"workflow:run"));

        // ENVIRONMENTS replaces PRODUCTION_TARGETS.
        let production = ENVIRONMENTS
            .iter()
            .find(|target| target.environment == "production")
            .unwrap();
        assert_eq!(production.control_plane_url, "https://api.tempera.dev");
        assert_eq!(production.palette_mcp_url, "https://mcp.tempera.dev/mcp");
        assert_eq!(production.tempo_api_url, "https://tempo.tempera.dev");
        assert_eq!(production.tempera_code_api_url, "https://code-api.tempera.dev");
        assert_eq!(production.tempera_llm_api_url, "https://llm.tempera.dev");
        assert_eq!(production.tempera_workflows_api_url, "https://workflows.tempera.dev");
        assert_eq!(production.tempera_gym_url, "https://gym.tempera.dev");
        assert_eq!(production.mcp_gateway_url, "https://api.tempera.dev/mcp");
    }

    #[test]
    fn re_exported_types_compose_end_to_end() {
        let auth = TemperaAuth::new("https://api.tempera.dev").with_api_key("tp_key_1");
        let client = TemperaClient::new()
            .with_auth(auth)
            .with_base_url("palette", "https://mcp.tempera.dev");
        let spec = client
            .build_request(
                "palette",
                "get_trace",
                &[("tenant_id", "t1".into()), ("trace_id", "tr1".into())],
            )
            .unwrap();
        assert_eq!(spec.method, "GET");
        assert_eq!(spec.full_url(), "https://mcp.tempera.dev/v1/traces/t1/tr1");

        let error = normalize_error_body(429, "Too Many Requests", "{\"error\":\"quota\",\"message\":\"limit\"}");
        assert_eq!(error.code.as_deref(), Some("quota"));

        let (id, body) = McpRequestBuilder::new().ping_body();
        assert_eq!(id, 1);
        assert!(parse_mcp_error(&body).is_none());
        assert_eq!(MCP_PROTOCOL_VERSION, "2025-06-18");
    }
}
