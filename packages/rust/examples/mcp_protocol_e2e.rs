use std::env;
use std::io::{Read, Write};
use std::net::TcpStream;

use tempera_sdk::{
    MCP_PROTOCOL_VERSION, McpCallOutcome, McpRequest, McpRequestBuilder, classify_mcp_call_result,
};

fn endpoint_parts(endpoint: &str) -> Result<(String, u16, String), String> {
    let rest = endpoint
        .strip_prefix("http://")
        .ok_or_else(|| "the protocol E2E accepts only a disposable http:// endpoint".to_string())?;
    let (authority, path) = rest.split_once('/').unwrap_or((rest, ""));
    let (host, port) = authority
        .rsplit_once(':')
        .ok_or_else(|| "endpoint must include an explicit port".to_string())?;
    let port = port.parse::<u16>().map_err(|_| "invalid endpoint port")?;
    Ok((host.to_string(), port, format!("/{path}")))
}

fn decode_chunked(mut body: &[u8]) -> Result<Vec<u8>, String> {
    let mut decoded = Vec::new();
    loop {
        let line_end = body
            .windows(2)
            .position(|window| window == b"\r\n")
            .ok_or_else(|| "invalid chunked response".to_string())?;
        let size_text = std::str::from_utf8(&body[..line_end])
            .map_err(|_| "non-UTF-8 chunk size")?
            .split(';')
            .next()
            .unwrap_or("");
        let size = usize::from_str_radix(size_text, 16).map_err(|_| "invalid chunk size")?;
        body = &body[line_end + 2..];
        if size == 0 {
            return Ok(decoded);
        }
        if body.len() < size + 2 || &body[size..size + 2] != b"\r\n" {
            return Err("truncated chunked response".to_string());
        }
        decoded.extend_from_slice(&body[..size]);
        body = &body[size + 2..];
    }
}

fn send(endpoint: &str, bearer: &str, request: &McpRequest) -> Result<String, String> {
    let (host, port, path) = endpoint_parts(endpoint)?;
    let mut stream =
        TcpStream::connect((host.as_str(), port)).map_err(|error| error.to_string())?;
    let mut wire = format!("POST {path} HTTP/1.1\r\nHost: {host}:{port}\r\n");
    for (name, value) in request.headers().map_err(|error| error.to_string())? {
        wire.push_str(&format!("{name}: {value}\r\n"));
    }
    wire.push_str(&format!(
        "authorization: Bearer {bearer}\r\ncontent-length: {}\r\nconnection: close\r\n\r\n",
        request.body().len()
    ));
    wire.push_str(request.body());
    stream
        .write_all(wire.as_bytes())
        .map_err(|error| error.to_string())?;
    let mut response = Vec::new();
    stream
        .read_to_end(&mut response)
        .map_err(|error| error.to_string())?;
    let split = response
        .windows(4)
        .position(|window| window == b"\r\n\r\n")
        .ok_or_else(|| "HTTP response omitted the header terminator".to_string())?;
    let header = std::str::from_utf8(&response[..split]).map_err(|_| "non-UTF-8 HTTP header")?;
    let status = header
        .lines()
        .next()
        .and_then(|line| line.split_whitespace().nth(1))
        .and_then(|value| value.parse::<u16>().ok())
        .ok_or_else(|| "invalid HTTP status".to_string())?;
    if status != 200 {
        return Err(format!("MCP request returned HTTP {status}"));
    }
    let raw_body = &response[split + 4..];
    let body = if header
        .lines()
        .any(|line| line.eq_ignore_ascii_case("transfer-encoding: chunked"))
    {
        decode_chunked(raw_body)?
    } else {
        raw_body.to_vec()
    };
    String::from_utf8(body).map_err(|_| "non-UTF-8 MCP response".to_string())
}

fn run() -> Result<(), String> {
    let mut args = env::args().skip(1);
    let endpoint = args.next().ok_or_else(|| "missing endpoint".to_string())?;
    let bearer = args.next().ok_or_else(|| "missing bearer".to_string())?;
    if args.next().is_some() {
        return Err("unexpected extra argument".to_string());
    }
    if bearer != "local-e2e-placeholder" {
        return Err("the protocol E2E accepts only its non-secret placeholder bearer".to_string());
    }
    let (host, _, path) = endpoint_parts(&endpoint)?;
    if host != "127.0.0.1" || path != "/mcp" {
        return Err("the protocol E2E accepts only a disposable loopback /mcp URL".to_string());
    }

    let mut builder = McpRequestBuilder::new()
        .with_client_info("tempera-sdk-rust-e2e", env!("CARGO_PKG_VERSION"));
    let discover = builder.discover_request();
    let discovery = send(&endpoint, &bearer, &discover)?;
    for marker in [
        &format!("\"id\":{}", discover.id()),
        "\"resultType\":\"complete\"",
        &format!("\"supportedVersions\":[\"{MCP_PROTOCOL_VERSION}\"]"),
    ] {
        if !discovery.contains(marker) {
            return Err("discovery response omitted an exact protocol marker".to_string());
        }
    }

    let listed = builder.list_tools_request();
    let catalog = send(&endpoint, &bearer, &listed)?;
    for tool in [
        "tempera_capability_catalog",
        "tempera_children",
        "tempera_commit",
        "tempera_describe",
        "tempera_execute_plan",
        "tempera_invoke",
        "tempera_manage_connections",
        "tempera_prepare",
        "tempera_search",
        "tempera_status",
        "tempera_whoami",
    ] {
        if !catalog.contains(&format!("\"name\":\"{tool}\"")) {
            return Err("tool catalog omitted an exact fixed tool".to_string());
        }
    }
    if catalog.matches("\"name\":\"tempera_").count() != 11 {
        return Err("tool catalog contained an unexpected extra fixed tool".to_string());
    }

    let invalid = builder
        .call_tool_request(
            "tempera_commit",
            Some(r#"{"receipt":"rust-secret-argument-sentinel"}"#),
        )
        .map_err(|error| error.to_string())?;
    let outcome = send(&endpoint, &bearer, &invalid)?;
    if classify_mcp_call_result(&outcome, invalid.id()) != Some(McpCallOutcome::ToolError) {
        return Err("invalid commit was not classified as a terminal tool error".to_string());
    }
    Ok(())
}

fn main() {
    if let Err(error) = run() {
        eprintln!("Rust MCP protocol E2E failed: {error}");
        std::process::exit(1);
    }
    println!("exact MCP 2026-07-28 Rust SDK E2E passed");
}
