//! JSON-RPC 2.0 body builders for the unified Tempera MCP gateway
//! (`${issuer}/mcp`): stateless streamable-HTTP JSON-RPC aggregating every
//! product MCP server behind namespaced tools (`palette_*`, `tempo_*`,
//! `cradle_*`, `remi_*`, `data_engine_*`).
//!
//! The crate is HTTP-less: [`McpRequestBuilder`] produces the exact request
//! bodies the gateway expects; POST them at `TemperaAuth::mcp_url()` with an
//! `authorization: Bearer <token>` header (a bearer minted for audience
//! `tempera-mcp` with scope `mcp:invoke`, or a central tp_ API key), then feed
//! error responses to [`parse_mcp_error`]. Mirrors `TemperaMcpClient` in the
//! TypeScript and Python packages.

use crate::error::{json_escape, parse_json, Json};

/// MCP protocol revision sent in `initialize` requests.
pub const MCP_PROTOCOL_VERSION: &str = "2025-06-18";

/// Builds JSON-RPC 2.0 request bodies for the MCP gateway with monotonically
/// increasing request ids. Each `*_body` method returns `(id, body)` so the
/// caller can correlate responses.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct McpRequestBuilder {
    next_id: i64,
}

impl Default for McpRequestBuilder {
    fn default() -> Self {
        Self::new()
    }
}

impl McpRequestBuilder {
    /// Create a builder whose first request id is 1.
    pub fn new() -> Self {
        Self { next_id: 1 }
    }

    fn take_id(&mut self) -> i64 {
        let id = self.next_id;
        self.next_id += 1;
        id
    }

    /// Body for `initialize`: open an MCP session and fetch server
    /// capabilities and instructions.
    pub fn initialize_body(&mut self, client_name: &str, client_version: &str) -> (i64, String) {
        let id = self.take_id();
        let body = format!(
            "{{\"jsonrpc\":\"2.0\",\"id\":{id},\"method\":\"initialize\",\"params\":{{\"protocolVersion\":\"{MCP_PROTOCOL_VERSION}\",\"capabilities\":{{}},\"clientInfo\":{{\"name\":\"{}\",\"version\":\"{}\"}}}}}}",
            json_escape(client_name),
            json_escape(client_version)
        );
        (id, body)
    }

    /// Body for `ping`: check gateway liveness over JSON-RPC (no params).
    pub fn ping_body(&mut self) -> (i64, String) {
        let id = self.take_id();
        (
            id,
            format!("{{\"jsonrpc\":\"2.0\",\"id\":{id},\"method\":\"ping\"}}"),
        )
    }

    /// Body for `tools/list`: list every tool the gateway offers, builtins
    /// plus namespaced product tools.
    pub fn list_tools_body(&mut self) -> (i64, String) {
        let id = self.take_id();
        (
            id,
            format!("{{\"jsonrpc\":\"2.0\",\"id\":{id},\"method\":\"tools/list\"}}"),
        )
    }

    /// Body for `tools/call`: invoke a tool by name; product tool calls are
    /// metered as `mcp_invocations`. `arguments_json` must be a serialized
    /// JSON object (spliced verbatim); `None` sends empty arguments (`{}`).
    pub fn call_tool_body(
        &mut self,
        tool_name: &str,
        arguments_json: Option<&str>,
    ) -> (i64, String) {
        let id = self.take_id();
        let body = format!(
            "{{\"jsonrpc\":\"2.0\",\"id\":{id},\"method\":\"tools/call\",\"params\":{{\"name\":\"{}\",\"arguments\":{}}}}}",
            json_escape(tool_name),
            arguments_json.unwrap_or("{}")
        );
        (id, body)
    }

    /// Body for the `tempera_whoami` builtin tool: fetch the caller's
    /// identity, workspace, and scopes as seen by the gateway.
    pub fn whoami_body(&mut self) -> (i64, String) {
        self.call_tool_body("tempera_whoami", None)
    }

    /// Body for the `tempera_status` builtin tool: fetch gateway upstream
    /// health for every connected product MCP server.
    pub fn status_body(&mut self) -> (i64, String) {
        self.call_tool_body("tempera_status", None)
    }
}

/// A JSON-RPC error returned by an MCP endpoint. Gateway error codes are the
/// `MCP_ERROR_*` constants in [`crate::surface`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct McpError {
    /// JSON-RPC error code (e.g. -32002 for a plan limit); 0 when the
    /// response carried a non-conformant error without an integer code.
    pub code: i64,
    /// Human-readable error message.
    pub message: String,
}

impl std::fmt::Display for McpError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "MCP error {}: {}", self.code, self.message)
    }
}

impl std::error::Error for McpError {}

/// Extract the JSON-RPC error from an MCP response body, if any: a top-level
/// `"error"` object with a numeric `code` (any `data` member is ignored).
/// Returns `None` for success responses and unparseable bodies.
pub fn parse_mcp_error(body: &str) -> Option<McpError> {
    let root = parse_json(body)?;
    let error = root.get("error")?;
    // Uniform rule (same in TypeScript and Python): a JSON-RPC error object
    // carries its integer code (0 when absent) and string message; a
    // non-conformant non-object error becomes code 0 with its string form.
    match error {
        Json::Obj(_) => Some(McpError {
            code: error.get("code").and_then(Json::as_i64).unwrap_or(0),
            message: error
                .get("message")
                .and_then(Json::as_str)
                .unwrap_or("MCP error")
                .to_string(),
        }),
        Json::Str(text) => Some(McpError {
            code: 0,
            message: text.clone(),
        }),
        Json::Null => None,
        other => Some(McpError {
            code: 0,
            message: match other {
                Json::Num(raw) => raw.clone(),
                Json::Bool(value) => value.to_string(),
                _ => String::new(),
            },
        }),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::surface::MCP_ERROR_PLAN_LIMIT;

    #[test]
    fn initialize_and_ping_bodies_are_exact_and_ids_increment() {
        let mut builder = McpRequestBuilder::new();

        let (id, body) = builder.initialize_body("tempera-sdk", "0.5.0");
        assert_eq!(id, 1);
        assert_eq!(
            body,
            "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-06-18\",\"capabilities\":{},\"clientInfo\":{\"name\":\"tempera-sdk\",\"version\":\"0.5.0\"}}}"
        );

        let (id, body) = builder.ping_body();
        assert_eq!(id, 2);
        assert_eq!(body, "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"ping\"}");
        assert!(!body.contains("params"));

        let (id, body) = builder.list_tools_body();
        assert_eq!(id, 3);
        assert_eq!(
            body,
            "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/list\"}"
        );
    }

    #[test]
    fn call_tool_body_splices_arguments_and_defaults_to_empty_object() {
        let mut builder = McpRequestBuilder::new();

        let (id, body) = builder.call_tool_body(
            "palette_list_traces",
            Some("{\"tenant_id\":\"t1\",\"limit\":5}"),
        );
        assert_eq!(id, 1);
        assert_eq!(
            body,
            "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"palette_list_traces\",\"arguments\":{\"tenant_id\":\"t1\",\"limit\":5}}}"
        );

        let (_, body) = builder.call_tool_body("tempo_observe", None);
        assert!(body.contains("\"arguments\":{}"));

        // Tool names with quotes are escaped, and every body parses back.
        let (_, body) = builder.call_tool_body("weird\"name", None);
        assert!(body.contains("\"name\":\"weird\\\"name\""));
        assert!(crate::error::parse_json(&body).is_some());
    }

    #[test]
    fn whoami_and_status_bodies_target_the_builtin_tools() {
        let mut builder = McpRequestBuilder::new();
        let (id, body) = builder.whoami_body();
        assert_eq!(id, 1);
        assert_eq!(
            body,
            "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"tempera_whoami\",\"arguments\":{}}}"
        );
        let (id, body) = builder.status_body();
        assert_eq!(id, 2);
        assert_eq!(
            body,
            "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"tempera_status\",\"arguments\":{}}}"
        );
    }

    #[test]
    fn parse_mcp_error_reads_plan_limit_and_ignores_data() {
        let body = r#"{"jsonrpc":"2.0","id":7,"error":{"code":-32002,"message":"plan limit reached","data":{"metric":"mcp_invocations","limit":100}}}"#;
        let error = parse_mcp_error(body).unwrap();
        assert_eq!(error.code, MCP_ERROR_PLAN_LIMIT);
        assert_eq!(error.message, "plan limit reached");
        assert_eq!(error.to_string(), "MCP error -32002: plan limit reached");
    }

    #[test]
    fn parse_mcp_error_returns_none_on_success_and_garbage() {
        assert_eq!(
            parse_mcp_error(r#"{"jsonrpc":"2.0","id":1,"result":{"tools":[]}}"#),
            None
        );
        assert_eq!(parse_mcp_error("not json"), None);
        assert_eq!(parse_mcp_error(r#"{"error":null}"#), None);
    }

    #[test]
    fn parse_mcp_error_handles_non_conformant_errors_uniformly() {
        // Same rule as TypeScript and Python: any present error member is an
        // error; non-object shapes become code 0 with their string form.
        assert_eq!(
            parse_mcp_error(r#"{"error":"nope"}"#),
            Some(McpError {
                code: 0,
                message: "nope".to_string()
            })
        );
        // An error object without an integer code keeps its message, code 0.
        assert_eq!(
            parse_mcp_error(r#"{"error":{"code":"x","message":"m"}}"#),
            Some(McpError {
                code: 0,
                message: "m".to_string()
            })
        );
        // An error object with neither code nor message gets the shared label.
        assert_eq!(
            parse_mcp_error(r#"{"error":{}}"#),
            Some(McpError {
                code: 0,
                message: "MCP error".to_string()
            })
        );
    }
}
