//! Retry-rule conformance for the Rust client, proven against a REAL local
//! HTTP server.
//!
//! Nothing here monkeypatches a transport: a `std::net::TcpListener` is bound
//! to an ephemeral port, the sender below speaks HTTP/1.1 over a real socket,
//! and every assertion is made from what the server actually received.

use std::collections::HashMap;
use std::io::{BufRead, BufReader, Read, Write};
use std::net::{Shutdown, SocketAddr, TcpListener, TcpStream};
use std::sync::mpsc;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

use tempera_sdk::client::{ParamValue, RequestSpec, TemperaClient};
use tempera_sdk::error::normalize_error_body;
use tempera_sdk::retry::{
    INITIAL_BACKOFF_MS, MAX_ATTEMPTS, SendError, canonical_idempotency_key, retry_delay,
    send_with_retry,
};
use tempera_sdk::{BuildError, TemperaAuth};

const IDEMPOTENCY_KEY: &str = "a4-intake-key-0000000001";

/// One request as the server received it off the wire.
#[derive(Debug, Clone)]
#[allow(dead_code)]
struct Received {
    method: String,
    target: String,
    body: String,
}

/// A real HTTP server that answers with a scripted (status, body) per attempt.
struct LiveServer {
    address: SocketAddr,
    received: Arc<Mutex<Vec<Received>>>,
    shutdown: mpsc::Sender<()>,
    handle: Option<thread::JoinHandle<()>>,
}

impl LiveServer {
    fn start(script: Vec<(u16, String)>) -> LiveServer {
        let listener = TcpListener::bind("127.0.0.1:0").expect("bind");
        let address = listener.local_addr().expect("addr");
        let received = Arc::new(Mutex::new(Vec::new()));
        let log = Arc::clone(&received);
        let (shutdown, stop) = mpsc::channel::<()>();
        let handle = thread::spawn(move || {
            for stream in listener.incoming() {
                if stop.try_recv().is_ok() {
                    break;
                }
                let Ok(mut stream) = stream else { break };
                let request = read_request(&mut stream);
                let attempt = {
                    let mut log = log.lock().expect("log");
                    log.push(request);
                    log.len()
                };
                let (status, body) = script
                    .get(attempt - 1)
                    .cloned()
                    .unwrap_or_else(|| script.last().cloned().expect("script"));
                let response = format!(
                    "HTTP/1.1 {status} X\r\ncontent-type: application/json\r\n\
                     content-length: {}\r\nconnection: close\r\n\r\n{body}",
                    body.len()
                );
                let _ = stream.write_all(response.as_bytes());
                let _ = stream.flush();
                let _ = stream.shutdown(Shutdown::Both);
            }
        });
        LiveServer {
            address,
            received,
            shutdown,
            handle: Some(handle),
        }
    }

    fn base_url(&self) -> String {
        format!("http://{}", self.address)
    }

    fn received(&self) -> Vec<Received> {
        self.received.lock().expect("log").clone()
    }

    fn stop(mut self) {
        let _ = self.shutdown.send(());
        // Unblock the accept loop with one final connection.
        let _ = TcpStream::connect(self.address);
        if let Some(handle) = self.handle.take() {
            let _ = handle.join();
        }
    }
}

fn read_request(stream: &mut TcpStream) -> Received {
    let mut reader = BufReader::new(stream.try_clone().expect("clone"));
    let mut start = String::new();
    reader.read_line(&mut start).expect("start line");
    let mut parts = start.split_whitespace();
    let method = parts.next().unwrap_or_default().to_string();
    let target = parts.next().unwrap_or_default().to_string();
    let mut headers: HashMap<String, String> = HashMap::new();
    loop {
        let mut line = String::new();
        if reader.read_line(&mut line).expect("header") == 0 {
            break;
        }
        let trimmed = line.trim_end();
        if trimmed.is_empty() {
            break;
        }
        if let Some((name, value)) = trimmed.split_once(':') {
            headers.insert(name.trim().to_ascii_lowercase(), value.trim().to_string());
        }
    }
    let length: usize = headers
        .get("content-length")
        .and_then(|value| value.parse().ok())
        .unwrap_or(0);
    let mut body = vec![0u8; length];
    if length > 0 {
        reader.read_exact(&mut body).expect("body");
    }
    Received {
        method,
        target,
        body: String::from_utf8_lossy(&body).to_string(),
    }
}

/// Send one RequestSpec over a real socket. The spec is never rebuilt, so
/// every attempt puts identical bytes — and the identical idempotency key —
/// on the wire.
fn send(spec: &RequestSpec, _attempt: u32) -> Result<String, SendError> {
    let full = spec.full_url();
    let rest = full.strip_prefix("http://").expect("http url");
    let (authority, path) = match rest.find('/') {
        Some(index) => (&rest[..index], &rest[index..]),
        None => (rest, "/"),
    };
    let mut stream = TcpStream::connect(authority)
        .map_err(|error| SendError::Connection(error.to_string()))?;
    let mut request = format!("{} {} HTTP/1.1\r\nhost: {}\r\n", spec.method, path, authority);
    for (name, value) in &spec.headers {
        request.push_str(&format!("{name}: {value}\r\n"));
    }
    let body = spec.body_json.clone().unwrap_or_default();
    request.push_str(&format!("content-length: {}\r\n", body.len()));
    request.push_str("connection: close\r\n\r\n");
    request.push_str(&body);
    stream
        .write_all(request.as_bytes())
        .map_err(|error| SendError::Connection(error.to_string()))?;
    let mut raw = String::new();
    stream
        .read_to_string(&mut raw)
        .map_err(|error| SendError::Connection(error.to_string()))?;
    let (head, payload) = raw.split_once("\r\n\r\n").unwrap_or((raw.as_str(), ""));
    let status: u16 = head
        .split_whitespace()
        .nth(1)
        .and_then(|code| code.parse().ok())
        .unwrap_or(0);
    if (200..300).contains(&status) {
        return Ok(payload.to_string());
    }
    Err(SendError::Api(normalize_error_body(status, "", payload)))
}

fn client(base_url: &str) -> TemperaClient {
    TemperaClient::new()
        .with_auth(TemperaAuth::new("https://issuer.example.test").with_api_key("tp_test_key"))
        .with_base_url("tempera_business", base_url)
        .with_base_url("tempera_dropshipping", base_url)
}

fn review_draft(base_url: &str) -> RequestSpec {
    client(base_url)
        .build_request(
            "tempera_business",
            "business_cases_review_draft",
            &[
                ("case_id", ParamValue::from("case-1")),
                ("idempotency_key", ParamValue::from(IDEMPOTENCY_KEY)),
                ("expected_revision", ParamValue::from(1i64)),
                ("decision", ParamValue::from("ready_for_owner_review")),
            ],
        )
        .expect("build review draft")
}

fn safe_retry_of(product: &str, operation: &str) -> &'static str {
    tempera_sdk::find_operation(product, operation)
        .expect("operation")
        .safe_retry
}

fn unavailable() -> String {
    r#"{"error":{"status":"UNAVAILABLE","message":"cold"}}"#.to_string()
}

#[test]
fn retry_reuses_original_idempotency_key() {
    let server = LiveServer::start(vec![
        (503, unavailable()),
        (503, unavailable()),
        (200, r#"{"ok":true}"#.to_string()),
    ]);
    let spec = review_draft(&server.base_url());
    let mut slept: Vec<Duration> = Vec::new();
    let body = send_with_retry(
        &spec,
        safe_retry_of("tempera_business", "business_cases_review_draft"),
        send,
        |delay| slept.push(delay),
    )
    .expect("succeeds on the third attempt");
    assert_eq!(body, r#"{"ok":true}"#);

    let received = server.received();
    server.stop();
    assert_eq!(received.len(), 3, "three real requests reached the server");
    let first = &received[0].body;
    for request in &received {
        assert_eq!(&request.body, first, "byte-identical body on every attempt");
        assert!(
            request
                .body
                .contains(&format!("\"idempotency_key\":\"{IDEMPOTENCY_KEY}\"")),
            "identical idempotency key resent: {}",
            request.body
        );
        assert_eq!(request.method, "POST");
    }
    assert_eq!(
        slept,
        vec![
            Duration::from_millis(INITIAL_BACKOFF_MS),
            Duration::from_millis(INITIAL_BACKOFF_MS * 2)
        ]
    );
}

#[test]
fn unsafe_operation_is_never_retried() {
    let server = LiveServer::start(vec![(503, unavailable())]);
    // prepare_proposal carries no idempotency key, so the generated surface
    // classifies it safe_retry "none".
    let safe_retry = safe_retry_of("tempera_dropshipping", "prepare_proposal");
    assert_eq!(safe_retry, "none");
    let spec = client(&server.base_url())
        .build_request(
            "tempera_dropshipping",
            "prepare_proposal",
            &[
                ("organization", ParamValue::from("org")),
                ("project", ParamValue::from("proj")),
                ("environment", ParamValue::from("env")),
                ("site", ParamValue::from("site")),
                ("order_id", ParamValue::from("order-1")),
                ("expected_revision", ParamValue::from(1i64)),
            ],
        )
        .expect("build prepare proposal");
    let mut slept: Vec<Duration> = Vec::new();
    let error = send_with_retry(&spec, safe_retry, send, |delay| slept.push(delay))
        .expect_err("503 surfaces");
    match error {
        SendError::Api(api) => assert_eq!(api.status, 503),
        other => panic!("expected an API error, got {other:?}"),
    }
    let received = server.received();
    server.stop();
    assert_eq!(received.len(), 1, "an unsafe write is sent exactly once");
    assert!(slept.is_empty());
}

#[test]
fn retry_gives_up_after_three_attempts() {
    let server = LiveServer::start(vec![(
        500,
        r#"{"error":{"status":"INTERNAL","message":"boom"}}"#.to_string(),
    )]);
    let spec = review_draft(&server.base_url());
    let mut slept: Vec<Duration> = Vec::new();
    let error = send_with_retry(
        &spec,
        safe_retry_of("tempera_business", "business_cases_review_draft"),
        send,
        |delay| slept.push(delay),
    )
    .expect_err("still failing");
    match error {
        SendError::Api(api) => assert_eq!(api.status, 500),
        other => panic!("expected an API error, got {other:?}"),
    }
    let received = server.received();
    server.stop();
    assert_eq!(received.len(), MAX_ATTEMPTS as usize);
    assert_eq!(slept.len(), MAX_ATTEMPTS as usize - 1);
}

#[test]
fn reason_is_parsed_from_details() {
    let payload = r#"{"error":{"code":409,"status":"ABORTED","message":"revision moved","details":[{"@type":"type.googleapis.com/google.rpc.RequestInfo","requestId":"req-1"},{"@type":"type.googleapis.com/google.rpc.ErrorInfo","reason":"REVISION_CONFLICT","domain":"tempera-business"}]}}"#;
    let server = LiveServer::start(vec![(409, payload.to_string())]);
    let spec = review_draft(&server.base_url());
    let error = send_with_retry(
        &spec,
        safe_retry_of("tempera_business", "business_cases_review_draft"),
        send,
        |_| {},
    )
    .expect_err("409 surfaces");
    server.stop();
    match error {
        SendError::Api(api) => {
            assert_eq!(api.reason.as_deref(), Some("REVISION_CONFLICT"));
            assert_eq!(api.code.as_deref(), Some("ABORTED"));
        }
        other => panic!("expected an API error, got {other:?}"),
    }
}

#[test]
fn a_4xx_is_not_retried() {
    let server = LiveServer::start(vec![(
        422,
        r#"{"error":{"status":"INVALID_ARGUMENT","message":"bad intake"}}"#.to_string(),
    )]);
    let spec = review_draft(&server.base_url());
    let mut slept: Vec<Duration> = Vec::new();
    let error = send_with_retry(
        &spec,
        safe_retry_of("tempera_business", "business_cases_review_draft"),
        send,
        |delay| slept.push(delay),
    )
    .expect_err("422 surfaces");
    match error {
        SendError::Api(api) => assert_eq!(api.status, 422),
        other => panic!("expected an API error, got {other:?}"),
    }
    let received = server.received();
    server.stop();
    assert_eq!(received.len(), 1, "a caller error is surfaced immediately");
    assert!(slept.is_empty());
}

#[test]
fn a_connection_failure_is_retried_for_a_safe_operation() {
    let server = LiveServer::start(vec![(200, r#"{"ok":true}"#.to_string())]);
    let base_url = server.base_url();
    let spec = review_draft(&base_url);
    server.stop();
    let mut slept: Vec<Duration> = Vec::new();
    let error = send_with_retry(
        &spec,
        safe_retry_of("tempera_business", "business_cases_review_draft"),
        send,
        |delay| slept.push(delay),
    )
    .expect_err("no listener");
    assert!(matches!(error, SendError::Connection(_)));
    assert_eq!(slept.len(), MAX_ATTEMPTS as usize - 1);
}

#[test]
fn a_non_canonical_idempotency_key_never_reaches_the_wire() {
    let server = LiveServer::start(vec![(200, r#"{"ok":true}"#.to_string())]);
    let base_url = server.base_url();
    for invalid in ["", "has space", "has\nnewline", "snowman-\u{2603}"] {
        let error = client(&base_url)
            .build_request(
                "tempera_business",
                "business_cases_review_draft",
                &[
                    ("case_id", ParamValue::from("case-1")),
                    ("idempotency_key", ParamValue::from(invalid)),
                    ("expected_revision", ParamValue::from(1i64)),
                    ("decision", ParamValue::from("ready_for_owner_review")),
                ],
            )
            .expect_err("rejected before the request exists");
        assert!(matches!(error, BuildError::InvalidIdempotencyKey { .. }));
    }
    let received = server.received();
    server.stop();
    assert!(received.is_empty(), "no malformed key ever reached the wire");
}

#[test]
fn canonical_key_and_backoff_match_the_shared_rules() {
    assert_eq!(
        canonical_idempotency_key("Request-1._~"),
        Some("Request-1._~")
    );
    assert!(canonical_idempotency_key(&"x".repeat(257)).is_none());
    assert_eq!(retry_delay(2), Duration::from_millis(250));
    assert_eq!(retry_delay(3), Duration::from_millis(500));
}
