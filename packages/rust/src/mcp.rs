//! Stable Streamable HTTP client and JSON-RPC body builders for the unified
//! Tempera MCP gateway (`${issuer}/mcp`).
//!
//! [`TemperaMcpClient`] is a complete session-aware client backed by the
//! official Rust SDK. [`McpRequestBuilder`] remains available for environments
//! that provide their own HTTP transport.

use std::{collections::BTreeSet, sync::Arc, time::Duration};

use rmcp::{
    RoleClient, ServiceExt,
    model::{
        CallToolRequestParams, CallToolResult, ClientCapabilities, ClientInfo, ClientRequest,
        GetPromptRequestParams, GetPromptResult, Implementation, JsonObject,
        PaginatedRequestParams, PingRequest, Prompt, ReadResourceRequestParams, ReadResourceResult,
        Resource, ServerInfo, ServerResult, Tool,
    },
    service::RunningService,
    transport::{
        StreamableHttpClientTransport, streamable_http_client::StreamableHttpClientTransportConfig,
    },
};
use serde_json::Value;

use crate::error::{Json, json_escape, parse_json};

/// MCP protocol revision sent in `initialize` requests.
pub const MCP_PROTOCOL_VERSION: &str = "2025-11-25";

/// The initialized official MCP client service used by [`TemperaMcpClient`].
pub type McpService = RunningService<RoleClient, ClientInfo>;

/// Connection options for the unified gateway.
#[derive(Clone)]
pub struct McpClientOptions {
    /// Streamable HTTP endpoint.
    pub url: String,
    /// Bearer token without the `Bearer ` prefix.
    pub bearer: String,
    /// Client implementation name sent during initialization.
    pub client_name: String,
    /// Client implementation version sent during initialization.
    pub client_version: String,
    /// HTTP operation deadline.
    pub request_timeout: Duration,
    /// Maximum pages accepted from one list operation.
    pub max_pages: usize,
    /// Maximum items accumulated by one list operation.
    pub max_items: usize,
}

impl std::fmt::Debug for McpClientOptions {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter
            .debug_struct("McpClientOptions")
            .field("url", &self.url)
            .field("bearer", &"<redacted>")
            .field("client_name", &self.client_name)
            .field("client_version", &self.client_version)
            .field("request_timeout", &self.request_timeout)
            .field("max_pages", &self.max_pages)
            .field("max_items", &self.max_items)
            .finish()
    }
}

impl McpClientOptions {
    /// Create options with production-safe defaults.
    pub fn new(url: impl Into<String>, bearer: impl Into<String>) -> Self {
        Self {
            url: url.into(),
            bearer: bearer.into(),
            client_name: "tempera-sdk".into(),
            client_version: "0.4.0".into(),
            request_timeout: Duration::from_secs(120),
            max_pages: 100,
            max_items: 10_000,
        }
    }
}

/// Transport, initialization, or protocol failure from the MCP client.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct McpClientError {
    message: String,
}

impl McpClientError {
    fn new(error: impl std::fmt::Display) -> Self {
        Self {
            message: error.to_string(),
        }
    }
}

impl std::fmt::Display for McpClientError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(&self.message)
    }
}

impl std::error::Error for McpClientError {}

/// Result returned by the live MCP client.
pub type McpClientResult<T> = Result<T, McpClientError>;

/// Initialized, session-aware client backed by the pinned official Rust SDK.
pub struct TemperaMcpClient {
    service: McpService,
    max_pages: usize,
    max_items: usize,
}

impl TemperaMcpClient {
    /// Connect, negotiate the latest stable protocol, and send `notifications/initialized`.
    pub async fn connect(
        url: impl Into<String>,
        bearer: impl Into<String>,
    ) -> McpClientResult<Self> {
        Self::connect_with(McpClientOptions::new(url, bearer)).await
    }

    /// Connect with explicit client identity and timeout settings.
    pub async fn connect_with(options: McpClientOptions) -> McpClientResult<Self> {
        if options.max_pages == 0 || options.max_items == 0 {
            return Err(McpClientError::new(
                "MCP pagination limits must be greater than zero",
            ));
        }
        if options.request_timeout.is_zero() {
            return Err(McpClientError::new(
                "MCP request timeout must be greater than zero",
            ));
        }
        let max_pages = options.max_pages;
        let max_items = options.max_items;
        let http = reqwest::Client::builder()
            .connect_timeout(Duration::from_secs(10))
            .timeout(options.request_timeout)
            .redirect(reqwest::redirect::Policy::none())
            .build()
            .map_err(McpClientError::new)?;
        let transport_config = StreamableHttpClientTransportConfig::with_uri(options.url)
            .auth_header(options.bearer)
            .reinit_on_expired_session(true);
        let transport = StreamableHttpClientTransport::with_client(http, transport_config);
        let info = ClientInfo::new(
            ClientCapabilities::default(),
            Implementation::new(options.client_name, options.client_version),
        );
        let service = info.serve(transport).await.map_err(McpClientError::new)?;
        Ok(Self {
            service,
            max_pages,
            max_items,
        })
    }

    /// Server capabilities and implementation metadata from initialization.
    pub fn server_info(&self) -> Option<Arc<ServerInfo>> {
        self.service.peer_info()
    }

    /// Access the official initialized service for advanced protocol operations.
    pub fn service(&self) -> &McpService {
        &self.service
    }

    /// Check protocol liveness.
    pub async fn ping(&self) -> McpClientResult<()> {
        match self
            .service
            .send_request(ClientRequest::PingRequest(PingRequest::default()))
            .await
            .map_err(McpClientError::new)?
        {
            ServerResult::EmptyResult(_) => Ok(()),
            _ => Err(McpClientError::new(
                "ping returned an unexpected response type",
            )),
        }
    }

    /// List the currently exposed tools with bounded, repeated-cursor-safe pagination.
    pub async fn list_tools(&self) -> McpClientResult<Vec<Tool>> {
        let mut values = Vec::new();
        let mut cursor = None;
        let mut seen = BTreeSet::new();
        for _ in 0..self.max_pages {
            let result = self
                .service
                .list_tools(
                    cursor.map(|value| PaginatedRequestParams::default().with_cursor(Some(value))),
                )
                .await
                .map_err(McpClientError::new)?;
            extend_bounded(&mut values, result.tools, self.max_items, "tools/list")?;
            match next_page_cursor(result.next_cursor, &mut seen, "tools/list")? {
                None => return Ok(values),
                Some(next) => cursor = Some(next),
            }
        }
        Err(McpClientError::new(format!(
            "tools/list exceeded {} pages",
            self.max_pages
        )))
    }

    /// Invoke any direct gateway tool.
    pub async fn call_tool(
        &self,
        name: impl Into<String>,
        arguments: JsonObject,
    ) -> McpClientResult<CallToolResult> {
        self.service
            .call_tool(CallToolRequestParams::new(name.into()).with_arguments(arguments))
            .await
            .map_err(McpClientError::new)
    }

    /// Search the progressive catalog without exposing every schema to the model.
    pub async fn search_tools(
        &self,
        query: impl Into<String>,
        server: Option<&str>,
        limit: Option<u64>,
        include_schema: bool,
    ) -> McpClientResult<CallToolResult> {
        let mut arguments = JsonObject::new();
        arguments.insert("query".into(), Value::String(query.into()));
        arguments.insert("includeSchema".into(), Value::Bool(include_schema));
        if let Some(server) = server {
            arguments.insert("server".into(), Value::String(server.into()));
        }
        if let Some(limit) = limit {
            arguments.insert("limit".into(), Value::from(limit));
        }
        self.call_tool("tempera_search_tools", arguments).await
    }

    /// Fetch one discovered tool's full schema and surface hash.
    pub async fn describe_tool(&self, name: impl Into<String>) -> McpClientResult<CallToolResult> {
        let mut arguments = JsonObject::new();
        arguments.insert("name".into(), Value::String(name.into()));
        self.call_tool("tempera_describe_tool", arguments).await
    }

    /// Invoke a progressively discovered tool by its namespaced name.
    pub async fn call_discovered_tool(
        &self,
        name: impl Into<String>,
        arguments: JsonObject,
    ) -> McpClientResult<CallToolResult> {
        let mut envelope = JsonObject::new();
        envelope.insert("name".into(), Value::String(name.into()));
        envelope.insert("arguments".into(), Value::Object(arguments));
        self.call_tool("tempera_call", envelope).await
    }

    /// List all resources with bounded pagination.
    pub async fn list_resources(&self) -> McpClientResult<Vec<Resource>> {
        let mut values = Vec::new();
        let mut cursor = None;
        let mut seen = BTreeSet::new();
        for _ in 0..self.max_pages {
            let result = self
                .service
                .list_resources(
                    cursor.map(|value| PaginatedRequestParams::default().with_cursor(Some(value))),
                )
                .await
                .map_err(McpClientError::new)?;
            extend_bounded(
                &mut values,
                result.resources,
                self.max_items,
                "resources/list",
            )?;
            match next_page_cursor(result.next_cursor, &mut seen, "resources/list")? {
                None => return Ok(values),
                Some(next) => cursor = Some(next),
            }
        }
        Err(McpClientError::new(format!(
            "resources/list exceeded {} pages",
            self.max_pages
        )))
    }

    /// Read a composed resource URI.
    pub async fn read_resource(
        &self,
        uri: impl Into<String>,
    ) -> McpClientResult<ReadResourceResult> {
        self.service
            .read_resource(ReadResourceRequestParams::new(uri))
            .await
            .map_err(McpClientError::new)
    }

    /// List all prompts with bounded pagination.
    pub async fn list_prompts(&self) -> McpClientResult<Vec<Prompt>> {
        let mut values = Vec::new();
        let mut cursor = None;
        let mut seen = BTreeSet::new();
        for _ in 0..self.max_pages {
            let result = self
                .service
                .list_prompts(
                    cursor.map(|value| PaginatedRequestParams::default().with_cursor(Some(value))),
                )
                .await
                .map_err(McpClientError::new)?;
            extend_bounded(&mut values, result.prompts, self.max_items, "prompts/list")?;
            match next_page_cursor(result.next_cursor, &mut seen, "prompts/list")? {
                None => return Ok(values),
                Some(next) => cursor = Some(next),
            }
        }
        Err(McpClientError::new(format!(
            "prompts/list exceeded {} pages",
            self.max_pages
        )))
    }

    /// Resolve a prompt by name.
    pub async fn get_prompt(
        &self,
        name: impl Into<String>,
        arguments: JsonObject,
    ) -> McpClientResult<GetPromptResult> {
        self.service
            .get_prompt(GetPromptRequestParams::new(name).with_arguments(arguments))
            .await
            .map_err(McpClientError::new)
    }

    /// Fetch identity and workspace claims through the gateway builtin.
    pub async fn whoami(&self) -> McpClientResult<CallToolResult> {
        self.call_tool("tempera_whoami", JsonObject::new()).await
    }

    /// Fetch catalog hashes, token metrics, and upstream circuit state.
    pub async fn status(&self) -> McpClientResult<CallToolResult> {
        self.call_tool("tempera_status", JsonObject::new()).await
    }

    /// Close the MCP session and stop the transport worker.
    pub async fn close(self) -> McpClientResult<()> {
        self.service
            .cancel()
            .await
            .map(|_| ())
            .map_err(McpClientError::new)
    }
}

fn next_page_cursor(
    next_cursor: Option<String>,
    seen: &mut BTreeSet<String>,
    method: &str,
) -> McpClientResult<Option<String>> {
    match next_cursor {
        None => Ok(None),
        Some(next) if next.is_empty() => Err(McpClientError::new(format!(
            "{method} returned an invalid nextCursor"
        ))),
        Some(next) if !seen.insert(next.clone()) => Err(McpClientError::new(format!(
            "{method} repeated a pagination cursor"
        ))),
        Some(next) => Ok(Some(next)),
    }
}

fn extend_bounded<T>(
    values: &mut Vec<T>,
    page: Vec<T>,
    max_items: usize,
    method: &str,
) -> McpClientResult<()> {
    if page.len() > max_items.saturating_sub(values.len()) {
        return Err(McpClientError::new(format!(
            "{method} exceeded {max_items} items"
        )));
    }
    values.extend(page);
    Ok(())
}

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

    /// Body for `tools/list`: list the tools currently exposed by the gateway mode.
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
    fn pagination_rejects_empty_and_repeated_cursors() {
        let mut seen = BTreeSet::new();
        assert!(next_page_cursor(Some(String::new()), &mut seen, "tools/list").is_err());
        assert_eq!(
            next_page_cursor(Some("next".into()), &mut seen, "tools/list").expect("first cursor"),
            Some("next".into())
        );
        assert!(next_page_cursor(Some("next".into()), &mut seen, "tools/list").is_err());
    }

    #[test]
    fn client_options_debug_redacts_the_bearer() {
        let options = McpClientOptions::new("https://api.tempera.dev/mcp", "secret-token");
        let rendered = format!("{options:?}");
        assert!(rendered.contains("<redacted>"));
        assert!(!rendered.contains("secret-token"));
    }

    #[test]
    fn initialize_and_ping_bodies_are_exact_and_ids_increment() {
        let mut builder = McpRequestBuilder::new();

        let (id, body) = builder.initialize_body("tempera-sdk", "0.4.0");
        assert_eq!(id, 1);
        assert_eq!(
            body,
            "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-11-25\",\"capabilities\":{},\"clientInfo\":{\"name\":\"tempera-sdk\",\"version\":\"0.4.0\"}}}"
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

    #[test]
    fn live_client_defaults_bound_pagination() {
        let options = McpClientOptions::new("https://api.tempera.dev/mcp", "token");
        assert_eq!(options.max_pages, 100);
        assert_eq!(options.max_items, 10_000);
    }

    #[test]
    fn bounded_extension_rejects_catalog_overflow() {
        let mut values = vec![1_u8];
        let error = extend_bounded(&mut values, vec![2, 3], 2, "tools/list")
            .expect_err("catalog must be bounded");
        assert_eq!(error.to_string(), "tools/list exceeded 2 items");
        assert_eq!(values, vec![1]);
    }
}
