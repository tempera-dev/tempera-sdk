//! MCP 2026-07-28 request builders for the unified Tempera gateway.
//!
//! The crate is HTTP-less: [`McpRequestBuilder`] produces the exact stateless
//! request body and [`McpRequest::headers`] produces the required protocol and
//! routing headers. Callers add authorization and POST at
//! `TemperaAuth::mcp_url()`. There is no session or legacy initialize wire.

use crate::error::{Json, json_escape, parse_json};

/// Strict stateless protocol revision accepted by Tempera MCP.
pub const MCP_PROTOCOL_VERSION: &str = "2026-07-28";
/// Protocol negotiation header required on every request.
pub const MCP_PROTOCOL_VERSION_HEADER: &str = "mcp-protocol-version";
/// Method-routing header required on every request.
pub const MCP_METHOD_HEADER: &str = "mcp-method";
/// Tool-routing header required on `tools/call`.
pub const MCP_NAME_HEADER: &str = "mcp-name";
/// Accept value required by streamable HTTP clients.
pub const MCP_ACCEPT: &str = "application/json, text/event-stream";

/// One complete HTTP-less MCP request.
#[derive(Clone, PartialEq, Eq)]
pub struct McpRequest {
    /// JSON-RPC request id.
    id: i64,
    /// MCP method mirrored into the routing header.
    method: &'static str,
    /// Tool name mirrored into `mcp-name` for `tools/call`.
    tool_name: Option<String>,
    /// Compact JSON-RPC request body.
    body: String,
}

impl std::fmt::Debug for McpRequest {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("McpRequest")
            .field("id", &self.id)
            .field("method", &self.method)
            .field("tool_name", &self.tool_name)
            .field("body", &"<redacted>")
            .finish()
    }
}

impl McpRequest {
    /// Correlation id that the response must echo exactly.
    pub fn id(&self) -> i64 {
        self.id
    }

    /// MCP method mirrored into the routing header.
    pub fn method(&self) -> &'static str {
        self.method
    }

    /// Tool name mirrored into `mcp-name`, when this is `tools/call`.
    pub fn tool_name(&self) -> Option<&str> {
        self.tool_name.as_deref()
    }

    /// Serialized request body. Debug output intentionally omits these bytes.
    pub fn body(&self) -> &str {
        &self.body
    }

    /// Required non-authorization HTTP headers for this exact request.
    pub fn headers(&self) -> Result<Vec<(&'static str, String)>, McpHeaderError> {
        if !routing_value_is_safe(self.method) {
            return Err(McpHeaderError("method"));
        }
        let mut headers = vec![
            ("accept", MCP_ACCEPT.to_string()),
            ("content-type", "application/json".to_string()),
            (
                MCP_PROTOCOL_VERSION_HEADER,
                MCP_PROTOCOL_VERSION.to_string(),
            ),
            (MCP_METHOD_HEADER, self.method.to_string()),
        ];
        if let Some(name) = self.tool_name.as_deref() {
            if !routing_value_is_safe(name) {
                return Err(McpHeaderError("tool name"));
            }
            headers.push((MCP_NAME_HEADER, name.to_string()));
        }
        Ok(headers)
    }

    fn into_body(self) -> (i64, String) {
        (self.id, self.body)
    }
}

fn routing_value_is_safe(value: &str) -> bool {
    !value.is_empty() && value.bytes().all(|byte| (0x21..=0x7e).contains(&byte))
}

/// A dynamic method or tool name could not be represented as an HTTP header.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct McpHeaderError(&'static str);

impl std::fmt::Display for McpHeaderError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "MCP {} contains an unsafe routing-header value", self.0)
    }
}

impl std::error::Error for McpHeaderError {}

/// A dynamic `tools/call` field could not be encoded as the required JSON
/// object wire shape.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum McpBuildError {
    /// A method/tool name is unsafe to mirror into an HTTP header.
    UnsafeRoutingValue(&'static str),
    /// A caller-supplied raw JSON value is not an object.
    InvalidJsonObject(&'static str),
}

impl std::fmt::Display for McpBuildError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::UnsafeRoutingValue(field) => {
                write!(f, "MCP {field} contains an unsafe routing-header value")
            }
            Self::InvalidJsonObject(field) => {
                write!(f, "MCP {field} must be a valid JSON object")
            }
        }
    }
}

impl std::error::Error for McpBuildError {}

/// Builds JSON-RPC 2.0 request bodies for the MCP gateway with monotonically
/// increasing request ids. Each `*_body` method returns `(id, body)` so the
/// caller can correlate responses.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct McpRequestBuilder {
    next_id: i64,
    client_name: String,
    client_version: String,
}

impl Default for McpRequestBuilder {
    fn default() -> Self {
        Self::new()
    }
}

impl McpRequestBuilder {
    /// Create a builder whose first request id is 1.
    pub fn new() -> Self {
        Self {
            next_id: 1,
            client_name: "tempera-sdk".to_string(),
            client_version: env!("CARGO_PKG_VERSION").to_string(),
        }
    }

    /// Set the client implementation included in every request's `_meta`.
    #[must_use]
    pub fn with_client_info(mut self, name: impl Into<String>, version: impl Into<String>) -> Self {
        self.client_name = name.into();
        self.client_version = version.into();
        self
    }

    fn take_id(&mut self) -> i64 {
        let id = self.next_id;
        self.next_id += 1;
        id
    }

    fn meta_json(&self) -> String {
        format!(
            "{{\"io.modelcontextprotocol/protocolVersion\":\"{MCP_PROTOCOL_VERSION}\",\"io.modelcontextprotocol/clientInfo\":{{\"name\":\"{}\",\"version\":\"{}\"}},\"io.modelcontextprotocol/clientCapabilities\":{{}}}}",
            json_escape(&self.client_name),
            json_escape(&self.client_version)
        )
    }

    fn request(
        &mut self,
        method: &'static str,
        tool_name: Option<&str>,
        params_fields: &str,
    ) -> McpRequest {
        let id = self.take_id();
        let separator = if params_fields.is_empty() { "" } else { "," };
        let body = format!(
            "{{\"jsonrpc\":\"2.0\",\"id\":{id},\"method\":\"{method}\",\"params\":{{{params_fields}{separator}\"_meta\":{}}}}}",
            self.meta_json()
        );
        McpRequest {
            id,
            method,
            tool_name: tool_name.map(str::to_owned),
            body,
        }
    }

    /// Request for stateless `server/discover`.
    pub fn discover_request(&mut self) -> McpRequest {
        self.request("server/discover", None, "")
    }

    /// Legacy tuple view of [`Self::discover_request`].
    #[deprecated(note = "body-only view omits mandatory MCP 2026 headers; use discover_request")]
    pub fn discover_body(&mut self) -> (i64, String) {
        self.discover_request().into_body()
    }

    /// Request for `server/discover` with updated client implementation info.
    /// This compatibility name does not send the removed `initialize` method.
    pub fn initialize_request(&mut self, client_name: &str, client_version: &str) -> McpRequest {
        self.client_name = client_name.to_string();
        self.client_version = client_version.to_string();
        self.discover_request()
    }

    /// Legacy tuple wrapper over [`Self::initialize_request`].
    #[deprecated(note = "body-only view omits mandatory MCP 2026 headers; use initialize_request")]
    pub fn initialize_body(&mut self, client_name: &str, client_version: &str) -> (i64, String) {
        self.initialize_request(client_name, client_version)
            .into_body()
    }

    /// Request for `ping`.
    pub fn ping_request(&mut self) -> McpRequest {
        self.request("ping", None, "")
    }

    /// Legacy tuple wrapper over [`Self::ping_request`].
    #[deprecated(note = "body-only view omits mandatory MCP 2026 headers; use ping_request")]
    pub fn ping_body(&mut self) -> (i64, String) {
        self.ping_request().into_body()
    }

    /// Request for `tools/list`.
    pub fn list_tools_request(&mut self) -> McpRequest {
        self.request("tools/list", None, "")
    }

    /// Legacy tuple wrapper over [`Self::list_tools_request`].
    #[deprecated(note = "body-only view omits mandatory MCP 2026 headers; use list_tools_request")]
    pub fn list_tools_body(&mut self) -> (i64, String) {
        self.list_tools_request().into_body()
    }

    /// Request for `tools/call`: invoke a tool by name; product tool calls are
    /// metered as `mcp_invocations`. `arguments_json` must be a serialized
    /// JSON object (spliced verbatim); `None` sends empty arguments (`{}`).
    pub fn call_tool_request(
        &mut self,
        tool_name: &str,
        arguments_json: Option<&str>,
    ) -> Result<McpRequest, McpBuildError> {
        self.call_tool_continuation_request(tool_name, arguments_json, None, None)
    }

    /// Request for `tools/call` with MCP 2026 multi-round-trip input.
    /// `input_responses_json`, when present, must be a serialized JSON object;
    /// `request_state` is opaque and is escaped before it is echoed.
    pub fn call_tool_continuation_request(
        &mut self,
        tool_name: &str,
        arguments_json: Option<&str>,
        input_responses_json: Option<&str>,
        request_state: Option<&str>,
    ) -> Result<McpRequest, McpBuildError> {
        if !routing_value_is_safe(tool_name) {
            return Err(McpBuildError::UnsafeRoutingValue("tool name"));
        }
        if arguments_json.is_some_and(|value| !matches!(parse_json(value), Some(Json::Obj(_)))) {
            return Err(McpBuildError::InvalidJsonObject("arguments"));
        }
        if input_responses_json
            .is_some_and(|value| !matches!(parse_json(value), Some(Json::Obj(_))))
        {
            return Err(McpBuildError::InvalidJsonObject("input responses"));
        }
        let fields = format!(
            "\"name\":\"{}\",\"arguments\":{}{}{}",
            json_escape(tool_name),
            arguments_json.unwrap_or("{}"),
            input_responses_json
                .map(|value| format!(",\"inputResponses\":{value}"))
                .unwrap_or_default(),
            request_state
                .map(|value| format!(",\"requestState\":\"{}\"", json_escape(value)))
                .unwrap_or_default(),
        );
        Ok(self.request("tools/call", Some(tool_name), &fields))
    }

    /// Legacy tuple wrapper over [`Self::call_tool_request`].
    #[deprecated(note = "body-only view omits mandatory MCP 2026 headers; use call_tool_request")]
    pub fn call_tool_body(
        &mut self,
        tool_name: &str,
        arguments_json: Option<&str>,
    ) -> Result<(i64, String), McpBuildError> {
        self.call_tool_request(tool_name, arguments_json)
            .map(McpRequest::into_body)
    }

    /// Request for the `tempera_whoami` builtin tool.
    pub fn whoami_request(&mut self) -> McpRequest {
        self.request(
            "tools/call",
            Some("tempera_whoami"),
            "\"name\":\"tempera_whoami\",\"arguments\":{}",
        )
    }

    /// Legacy tuple wrapper over [`Self::whoami_request`].
    #[deprecated(note = "body-only view omits mandatory MCP 2026 headers; use whoami_request")]
    pub fn whoami_body(&mut self) -> (i64, String) {
        self.whoami_request().into_body()
    }

    /// Request for the `tempera_status` builtin tool.
    pub fn status_request(&mut self) -> McpRequest {
        self.request(
            "tools/call",
            Some("tempera_status"),
            "\"name\":\"tempera_status\",\"arguments\":{}",
        )
    }

    /// Legacy tuple wrapper over [`Self::status_request`].
    #[deprecated(note = "body-only view omits mandatory MCP 2026 headers; use status_request")]
    pub fn status_body(&mut self) -> (i64, String) {
        self.status_request().into_body()
    }
}

/// A JSON-RPC error returned by an MCP endpoint. Gateway error codes are the
/// `MCP_ERROR_*` constants in [`crate::surface`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct McpError {
    /// JSON-RPC error code (e.g. -32002 for a plan limit).
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

/// A JSON-RPC response was not a conformant, correlated MCP envelope.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct McpProtocolError(&'static str);

impl std::fmt::Display for McpProtocolError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "malformed MCP response: {}", self.0)
    }
}

impl std::error::Error for McpProtocolError {}

/// Extract a conformant JSON-RPC error from the response correlated to
/// `expected_id`. A valid success envelope returns `Ok(None)`; malformed,
/// ambiguous, uncorrelated, or non-object errors fail closed as `Err`.
pub fn parse_mcp_error(body: &str, expected_id: i64) -> Result<Option<McpError>, McpProtocolError> {
    let root = parse_json(body).ok_or(McpProtocolError("invalid JSON"))?;
    if !matches!(root, Json::Obj(_))
        || root.get("jsonrpc").and_then(Json::as_str) != Some("2.0")
        || root.get("method").is_some()
        || !matches!(root.get("id"), Some(Json::Num(raw)) if raw.parse::<i64>().ok() == Some(expected_id))
    {
        return Err(McpProtocolError("invalid JSON-RPC correlation"));
    }
    let has_result = root.get("result").is_some();
    let error = root.get("error");
    if has_result == error.is_some() {
        return Err(McpProtocolError("expected exactly one of result or error"));
    }
    let Some(error) = error else {
        return Ok(None);
    };
    let Json::Obj(_) = error else {
        return Err(McpProtocolError("error must be an object"));
    };
    let code = error
        .get("code")
        .and_then(Json::as_i64)
        .ok_or(McpProtocolError("error code must be an integer"))?;
    let message = error
        .get("message")
        .and_then(Json::as_str)
        .ok_or(McpProtocolError("error message must be a string"))?;
    Ok(Some(McpError {
        code,
        message: message.to_string(),
    }))
}

/// Terminality classification for a successful JSON-RPC `tools/call`
/// response. Callers must not record `InputRequired` or `ToolError` as a
/// completed tool execution.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum McpCallOutcome {
    /// The call produced a terminal non-error result.
    Complete,
    /// The caller must provide another input and resume the operation.
    InputRequired(McpInputRequired),
    /// The tool returned an MCP `isError: true` outcome.
    ToolError,
}

/// Validated continuation data for an MCP multi-round-trip tool call.
#[derive(Clone, PartialEq, Eq)]
pub struct McpInputRequired {
    /// Full validated JSON-RPC response for callers that deserialize the
    /// heterogeneous `inputRequests` map with their chosen JSON stack.
    pub response_body: String,
    /// Opaque state that must be echoed on the continuation request, if any.
    pub request_state: Option<String>,
    /// Whether the response carries an `inputRequests` map to fulfill.
    pub has_input_requests: bool,
}

impl std::fmt::Debug for McpInputRequired {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("McpInputRequired")
            .field("response_body", &"<redacted>")
            .field("has_request_state", &self.request_state.is_some())
            .field("has_input_requests", &self.has_input_requests)
            .finish()
    }
}

fn input_requests_are_valid(value: &Json) -> bool {
    let Json::Obj(requests) = value else {
        return false;
    };
    requests.iter().all(
        |(_, request)| match request.get("method").and_then(Json::as_str) {
            Some("roots/list") => matches!(request.get("params"), None | Some(Json::Obj(_))),
            Some("sampling/createMessage" | "elicitation/create") => {
                matches!(request.get("params"), Some(Json::Obj(_)))
            }
            _ => false,
        },
    )
}

fn content_block_is_valid(value: &Json) -> bool {
    let Json::Obj(_) = value else {
        return false;
    };
    if !matches!(value.get("_meta"), None | Some(Json::Obj(_)))
        || !matches!(value.get("annotations"), None | Some(Json::Obj(_)))
    {
        return false;
    }
    match value.get("type").and_then(Json::as_str) {
        Some("text") => matches!(value.get("text"), Some(Json::Str(_))),
        Some("image" | "audio") => {
            matches!(value.get("data"), Some(Json::Str(_)))
                && matches!(value.get("mimeType"), Some(Json::Str(_)))
        }
        Some("resource_link") => {
            matches!(value.get("uri"), Some(Json::Str(_)))
                && matches!(value.get("name"), Some(Json::Str(_)))
        }
        Some("resource") => {
            let Some(resource) = value.get("resource") else {
                return false;
            };
            matches!(resource.get("uri"), Some(Json::Str(_)))
                && matches!(resource.get("_meta"), None | Some(Json::Obj(_)))
                && (matches!(resource.get("text"), Some(Json::Str(_)))
                    || matches!(resource.get("blob"), Some(Json::Str(_))))
        }
        _ => false,
    }
}

/// Classify the result of a correlated `tools/call` response.
///
/// Returns `None` for malformed bodies, JSON-RPC error responses, or bodies
/// without a result object so transport adapters can fail closed separately.
pub fn classify_mcp_call_result(body: &str, expected_id: i64) -> Option<McpCallOutcome> {
    let root = parse_json(body)?;
    if !matches!(root, Json::Obj(_))
        || root.get("jsonrpc").and_then(Json::as_str) != Some("2.0")
        || root.get("method").is_some()
        || !matches!(root.get("id"), Some(Json::Num(raw)) if raw.parse::<i64>().ok() == Some(expected_id))
        || root.get("error").is_some()
    {
        return None;
    }
    let result = root.get("result")?;
    if !matches!(result, Json::Obj(_)) {
        return None;
    }
    match result.get("resultType").and_then(Json::as_str) {
        Some("input_required") => {
            let input_requests_valid = result
                .get("inputRequests")
                .is_some_and(input_requests_are_valid);
            let request_state_valid = matches!(result.get("requestState"), Some(Json::Str(_)));
            if (!input_requests_valid && !request_state_valid)
                || (result.get("inputRequests").is_some() && !input_requests_valid)
                || (result.get("requestState").is_some() && !request_state_valid)
            {
                return None;
            }
            return Some(McpCallOutcome::InputRequired(McpInputRequired {
                response_body: body.to_string(),
                request_state: result
                    .get("requestState")
                    .and_then(Json::as_str)
                    .map(str::to_string),
                has_input_requests: result.get("inputRequests").is_some(),
            }));
        }
        Some("complete") => {}
        _ => return None,
    }
    let known_result = result.get("content").is_some()
        || result.get("structuredContent").is_some()
        || result.get("isError").is_some()
        || result.get("_meta").is_some();
    if !known_result
        || !match result.get("content") {
            None => true,
            Some(Json::Arr(blocks)) => blocks.iter().all(content_block_is_valid),
            Some(_) => false,
        }
        || !matches!(result.get("structuredContent"), None | Some(Json::Obj(_)))
        || !matches!(result.get("_meta"), None | Some(Json::Obj(_)))
    {
        return None;
    }
    if let Some(is_error) = result.get("isError") {
        match is_error.as_bool() {
            Some(true) => return Some(McpCallOutcome::ToolError),
            Some(false) => {}
            None => return None,
        }
    }
    Some(McpCallOutcome::Complete)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::surface::MCP_ERROR_PLAN_LIMIT;

    #[test]
    fn discovery_and_every_request_use_exact_stateless_metadata_and_headers() {
        let mut builder = McpRequestBuilder::new();

        let discover = builder.initialize_request("tempera-voice", "0.1.0");
        assert_eq!(discover.id, 1);
        assert_eq!(discover.method, "server/discover");
        assert!(!discover.body.contains("\"method\":\"initialize\""));
        assert!(
            discover
                .body
                .contains("\"io.modelcontextprotocol/protocolVersion\":\"2026-07-28\"")
        );
        assert!(discover.body.contains("\"name\":\"tempera-voice\""));
        assert!(discover.body.contains("\"version\":\"0.1.0\""));
        assert!(
            discover
                .body
                .contains("\"io.modelcontextprotocol/clientCapabilities\":{}")
        );
        assert_eq!(
            discover.headers().unwrap(),
            vec![
                ("accept", "application/json, text/event-stream".to_string()),
                ("content-type", "application/json".to_string()),
                ("mcp-protocol-version", "2026-07-28".to_string()),
                ("mcp-method", "server/discover".to_string()),
            ]
        );

        let ping = builder.ping_request();
        assert_eq!(ping.id, 2);
        assert_eq!(ping.method, "ping");
        assert!(ping.body.contains("\"params\":{\"_meta\":"));

        let listed = builder.list_tools_request();
        assert_eq!(listed.id, 3);
        assert_eq!(listed.method, "tools/list");
        assert!(crate::error::parse_json(&listed.body).is_some());
    }

    #[test]
    fn call_tool_body_splices_arguments_and_defaults_to_empty_object() {
        let mut builder = McpRequestBuilder::new();

        let request = builder
            .call_tool_request(
                "tempera_search",
                Some("{\"query\":\"browser capability\",\"limit\":5}"),
            )
            .unwrap();
        assert_eq!(request.id, 1);
        assert!(request.body.contains("\"name\":\"tempera_search\""));
        assert!(
            request
                .body
                .contains("\"arguments\":{\"query\":\"browser capability\",\"limit\":5}")
        );
        assert!(request.body.contains("\"_meta\":"));
        assert_eq!(
            request.headers().unwrap().last().unwrap(),
            &("mcp-name", "tempera_search".to_string())
        );

        let body = builder
            .call_tool_request("tempera_status", None)
            .unwrap()
            .body;
        assert!(body.contains("\"arguments\":{}"));
        assert!(body.contains("\"_meta\":"));

        // Tool names with quotes are escaped, and every body parses back.
        let body = builder.call_tool_request("weird\"name", None).unwrap().body;
        assert!(body.contains("\"name\":\"weird\\\"name\""));
        assert!(crate::error::parse_json(&body).is_some());
        assert!(
            builder
                .call_tool_request("tempera_status", Some("[]"))
                .is_err()
        );
        assert!(
            builder
                .call_tool_request("tempera_status", Some("{bad"))
                .is_err()
        );
    }

    #[test]
    fn continuation_request_echoes_exact_mrtr_fields_and_redacts_debug() {
        let request = McpRequestBuilder::new()
            .call_tool_continuation_request(
                "tempera_execute_plan",
                Some("{\"plan\":\"secret-sentinel\"}"),
                Some("{\"approval\":{\"accepted\":true}}"),
                Some("opaque\"state"),
            )
            .unwrap();
        assert!(
            request
                .body
                .contains("\"inputResponses\":{\"approval\":{\"accepted\":true}}")
        );
        assert!(
            request
                .body
                .contains("\"requestState\":\"opaque\\\"state\"")
        );
        let debug = format!("{request:?}");
        assert!(debug.contains("body: \"<redacted>\""));
        assert!(!debug.contains("secret-sentinel"));
        assert!(!debug.contains("opaque"));
    }

    #[test]
    fn unsafe_dynamic_tool_names_fail_before_header_construction() {
        let request = McpRequestBuilder::new().call_tool_request("bad\r\nheader", None);
        assert_eq!(request, Err(McpBuildError::UnsafeRoutingValue("tool name")));
    }

    #[test]
    fn whoami_and_status_bodies_target_the_builtin_tools() {
        let mut builder = McpRequestBuilder::new();
        let whoami = builder.whoami_request();
        assert_eq!(whoami.id, 1);
        assert!(whoami.body.contains("\"name\":\"tempera_whoami\""));
        assert!(whoami.body.contains("\"_meta\":"));
        let status = builder.status_request();
        assert_eq!(status.id, 2);
        assert!(status.body.contains("\"name\":\"tempera_status\""));
        assert!(status.body.contains("\"_meta\":"));
    }

    #[test]
    fn parse_mcp_error_reads_plan_limit_and_ignores_data() {
        let body = r#"{"jsonrpc":"2.0","id":7,"error":{"code":-32002,"message":"plan limit reached","data":{"metric":"mcp_invocations","limit":100}}}"#;
        let error = parse_mcp_error(body, 7).unwrap().unwrap();
        assert_eq!(error.code, MCP_ERROR_PLAN_LIMIT);
        assert_eq!(error.message, "plan limit reached");
        assert_eq!(error.to_string(), "MCP error -32002: plan limit reached");
    }

    #[test]
    fn parse_mcp_error_returns_none_on_success_and_rejects_malformed_envelopes() {
        assert_eq!(
            parse_mcp_error(r#"{"jsonrpc":"2.0","id":1,"result":{"tools":[]}}"#, 1),
            Ok(None)
        );
        assert!(parse_mcp_error("not json", 1).is_err());
        assert!(parse_mcp_error(r#"{"jsonrpc":"2.0","id":1,"error":null}"#, 1).is_err());
        assert!(
            parse_mcp_error(
                r#"{"jsonrpc":"2.0","id":1,"result":{},"error":{"code":-1,"message":"bad"}}"#,
                1,
            )
            .is_err()
        );
    }

    #[test]
    fn parse_mcp_error_rejects_non_conformant_errors_uniformly() {
        for body in [
            r#"{"jsonrpc":"2.0","id":1,"error":"nope"}"#,
            r#"{"jsonrpc":"2.0","id":1,"error":{"code":"x","message":"m"}}"#,
            r#"{"jsonrpc":"2.0","id":1,"error":{"code":-32002.9,"message":"m"}}"#,
            r#"{"jsonrpc":"2.0","id":1,"error":{}}"#,
            r#"{"jsonrpc":"2.0","id":2,"error":{"code":-1,"message":"wrong id"}}"#,
        ] {
            assert!(parse_mcp_error(body, 1).is_err(), "{body}");
        }
    }

    #[test]
    fn tool_outcome_classification_prevents_false_success() {
        assert_eq!(
            classify_mcp_call_result(
                r#"{"jsonrpc":"2.0","id":1,"result":{"resultType":"complete","isError":true,"content":[]}}"#,
                1,
            ),
            Some(McpCallOutcome::ToolError)
        );
        let input_required = classify_mcp_call_result(
            r#"{"jsonrpc":"2.0","id":1,"result":{"resultType":"input_required","requestState":"opaque"}}"#,
            1,
        );
        assert!(matches!(
            input_required,
            Some(McpCallOutcome::InputRequired(McpInputRequired {
                request_state: Some(ref state),
                has_input_requests: false,
                ..
            })) if state == "opaque"
        ));
        let debug = format!("{input_required:?}");
        assert!(!debug.contains("opaque"));
        assert!(debug.contains("response_body: \"<redacted>\""));
        assert_eq!(
            classify_mcp_call_result(
                r#"{"jsonrpc":"2.0","id":1,"result":{"resultType":"complete","isError":false,"content":[]}}"#,
                1,
            ),
            Some(McpCallOutcome::Complete)
        );
        assert_eq!(
            classify_mcp_call_result(r#"{"jsonrpc":"2.0","id":1,"error":{"code":-1}}"#, 1,),
            None
        );
        assert_eq!(
            classify_mcp_call_result(
                r#"{"jsonrpc":"2.0","id":1,"result":{"resultType":"futureOutcome"}}"#,
                1,
            ),
            None
        );
        assert_eq!(
            classify_mcp_call_result(r#"{"jsonrpc":"2.0","id":1,"result":"not-an-object"}"#, 1,),
            None
        );
        for body in [
            r#"{"jsonrpc":"1.0","id":1,"result":{"resultType":"complete","content":[]}}"#,
            r#"{"jsonrpc":"2.0","id":2,"result":{"resultType":"complete","content":[]}}"#,
            r#"{"jsonrpc":"2.0","id":1,"method":"sampling/createMessage","result":{"resultType":"complete","content":[]}}"#,
            r#"{"jsonrpc":"2.0","id":1,"result":{"resultType":"input_required"}}"#,
            r#"{"jsonrpc":"2.0","id":1,"result":{"resultType":"complete"}}"#,
            r#"{"jsonrpc":"2.0","id":1,"result":{"resultType":"complete","content":{}}}"#,
            r#"{"jsonrpc":"2.0","id":01,"result":{"resultType":"complete","content":[]}}"#,
            r#"{"jsonrpc":"2.0","jsonrpc":"2.0","id":1,"result":{"resultType":"complete","content":[]}}"#,
            r#"{"jsonrpc":"2.0","id":1,"id":1,"result":{"resultType":"complete","content":[]}}"#,
            r#"{"jsonrpc":"2.0","id":1,"result":{"resultType":"complete","content":[]},"result":{"resultType":"complete","content":[]}}"#,
            r#"{"jsonrpc":"2.0","id":1,"result":{"resultType":"complete","content":[1]}}"#,
            r#"{"jsonrpc":"2.0","id":1,"result":{"resultType":"complete","content":[{"type":"text","text":"x","_meta":[]}]}}"#,
        ] {
            assert_eq!(classify_mcp_call_result(body, 1), None, "{body}");
        }
    }
}
