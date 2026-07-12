//! Uniform Tempera API errors, shared in shape with the TypeScript and Python
//! packages (see `surface.json` `errorContract`).
//!
//! The crate is dependency-free, so this module carries a small private JSON
//! scanner ([`parse_json`]) sufficient for the five wire error shapes in the
//! Tempera fleet, plus [`normalize_error_body`], which folds any of them into
//! one [`TemperaApiError`].

use std::fmt;

/// Minimal JSON value model produced by the private scanner. Numbers keep
/// their raw source text so integer JSON-RPC codes round-trip exactly.
#[derive(Debug, Clone, PartialEq)]
pub(crate) enum Json {
    Null,
    Bool(bool),
    Num(String),
    Str(String),
    Arr(Vec<Json>),
    Obj(Vec<(String, Json)>),
}

impl Json {
    /// Look up a member of an object by key; `None` for non-objects.
    pub(crate) fn get(&self, key: &str) -> Option<&Json> {
        match self {
            Json::Obj(members) => members.iter().find(|(k, _)| k == key).map(|(_, v)| v),
            _ => None,
        }
    }

    /// The string payload, when this value is a JSON string.
    pub(crate) fn as_str(&self) -> Option<&str> {
        match self {
            Json::Str(value) => Some(value.as_str()),
            _ => None,
        }
    }

    /// The integer payload, when this value is a JSON number.
    pub(crate) fn as_i64(&self) -> Option<i64> {
        match self {
            Json::Num(raw) => raw
                .parse::<i64>()
                .ok()
                .or_else(|| raw.parse::<f64>().ok().map(|value| value as i64)),
            _ => None,
        }
    }
}

/// Parse a complete JSON document. Returns `None` on any syntax error or
/// trailing garbage, which callers treat as "unparseable body".
pub(crate) fn parse_json(input: &str) -> Option<Json> {
    let mut parser = Parser {
        bytes: input.as_bytes(),
        pos: 0,
    };
    parser.skip_ws();
    let value = parser.parse_value()?;
    parser.skip_ws();
    if parser.pos == parser.bytes.len() {
        Some(value)
    } else {
        None
    }
}

/// Escape a string for inclusion inside a JSON string literal (without the
/// surrounding quotes).
pub(crate) fn json_escape(value: &str) -> String {
    let mut out = String::with_capacity(value.len());
    for ch in value.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            ch if (ch as u32) < 0x20 => {
                out.push_str(&format!("\\u{:04x}", ch as u32));
            }
            ch => out.push(ch),
        }
    }
    out
}

struct Parser<'a> {
    bytes: &'a [u8],
    pos: usize,
}

impl Parser<'_> {
    fn peek(&self) -> Option<u8> {
        self.bytes.get(self.pos).copied()
    }

    fn bump(&mut self) -> Option<u8> {
        let byte = self.peek()?;
        self.pos += 1;
        Some(byte)
    }

    fn skip_ws(&mut self) {
        while matches!(self.peek(), Some(b' ' | b'\t' | b'\n' | b'\r')) {
            self.pos += 1;
        }
    }

    fn eat(&mut self, token: &str) -> bool {
        if self.bytes[self.pos..].starts_with(token.as_bytes()) {
            self.pos += token.len();
            true
        } else {
            false
        }
    }

    fn parse_value(&mut self) -> Option<Json> {
        match self.peek()? {
            b'{' => self.parse_object(),
            b'[' => self.parse_array(),
            b'"' => self.parse_string().map(Json::Str),
            b't' => self.eat("true").then_some(Json::Bool(true)),
            b'f' => self.eat("false").then_some(Json::Bool(false)),
            b'n' => self.eat("null").then_some(Json::Null),
            b'-' | b'0'..=b'9' => self.parse_number(),
            _ => None,
        }
    }

    fn parse_object(&mut self) -> Option<Json> {
        self.bump(); // consume '{'
        let mut members = Vec::new();
        self.skip_ws();
        if self.peek() == Some(b'}') {
            self.bump();
            return Some(Json::Obj(members));
        }
        loop {
            self.skip_ws();
            if self.peek()? != b'"' {
                return None;
            }
            let key = self.parse_string()?;
            self.skip_ws();
            if self.bump()? != b':' {
                return None;
            }
            self.skip_ws();
            let value = self.parse_value()?;
            members.push((key, value));
            self.skip_ws();
            match self.bump()? {
                b',' => continue,
                b'}' => return Some(Json::Obj(members)),
                _ => return None,
            }
        }
    }

    fn parse_array(&mut self) -> Option<Json> {
        self.bump(); // consume '['
        let mut items = Vec::new();
        self.skip_ws();
        if self.peek() == Some(b']') {
            self.bump();
            return Some(Json::Arr(items));
        }
        loop {
            self.skip_ws();
            items.push(self.parse_value()?);
            self.skip_ws();
            match self.bump()? {
                b',' => continue,
                b']' => return Some(Json::Arr(items)),
                _ => return None,
            }
        }
    }

    fn parse_string(&mut self) -> Option<String> {
        self.bump(); // consume opening '"'
        let mut out = String::new();
        loop {
            // Copy the run of plain bytes up to the next quote, backslash, or
            // raw control character; the delimiters are ASCII so the slice
            // always lands on a UTF-8 char boundary.
            let start = self.pos;
            while let Some(byte) = self.peek() {
                if byte == b'"' || byte == b'\\' || byte < 0x20 {
                    break;
                }
                self.pos += 1;
            }
            out.push_str(std::str::from_utf8(&self.bytes[start..self.pos]).ok()?);
            match self.bump()? {
                b'"' => return Some(out),
                b'\\' => match self.bump()? {
                    b'"' => out.push('"'),
                    b'\\' => out.push('\\'),
                    b'/' => out.push('/'),
                    b'b' => out.push('\u{0008}'),
                    b'f' => out.push('\u{000C}'),
                    b'n' => out.push('\n'),
                    b'r' => out.push('\r'),
                    b't' => out.push('\t'),
                    b'u' => {
                        let unit = self.parse_hex4()?;
                        let ch = if (0xD800..0xDC00).contains(&unit) {
                            // High surrogate: a \uXXXX low surrogate must follow.
                            if self.bump()? != b'\\' || self.bump()? != b'u' {
                                return None;
                            }
                            let low = self.parse_hex4()?;
                            if !(0xDC00..0xE000).contains(&low) {
                                return None;
                            }
                            let combined = 0x10000
                                + ((u32::from(unit) - 0xD800) << 10)
                                + (u32::from(low) - 0xDC00);
                            char::from_u32(combined)?
                        } else {
                            char::from_u32(u32::from(unit))?
                        };
                        out.push(ch);
                    }
                    _ => return None,
                },
                _ => return None, // raw control character inside a string
            }
        }
    }

    fn parse_hex4(&mut self) -> Option<u16> {
        let mut value: u16 = 0;
        for _ in 0..4 {
            let digit = (self.bump()? as char).to_digit(16)? as u16;
            value = (value << 4) | digit;
        }
        Some(value)
    }

    fn parse_number(&mut self) -> Option<Json> {
        let start = self.pos;
        if self.peek() == Some(b'-') {
            self.pos += 1;
        }
        if !self.eat_digits() {
            return None;
        }
        if self.peek() == Some(b'.') {
            self.pos += 1;
            if !self.eat_digits() {
                return None;
            }
        }
        if matches!(self.peek(), Some(b'e' | b'E')) {
            self.pos += 1;
            if matches!(self.peek(), Some(b'+' | b'-')) {
                self.pos += 1;
            }
            if !self.eat_digits() {
                return None;
            }
        }
        let raw = std::str::from_utf8(&self.bytes[start..self.pos]).ok()?;
        Some(Json::Num(raw.to_string()))
    }

    fn eat_digits(&mut self) -> bool {
        let start = self.pos;
        while matches!(self.peek(), Some(b'0'..=b'9')) {
            self.pos += 1;
        }
        self.pos > start
    }
}

/// An HTTP error response from any Tempera product, normalized from the five
/// wire error shapes in the fleet (see `surface.json` `errorContract`) so
/// callers always read the same fields.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TemperaApiError {
    /// HTTP status code of the failed response.
    pub status: u16,
    /// Machine-readable error code, when the wire shape carried one.
    pub code: Option<String>,
    /// Human-readable error message; never empty.
    pub message: String,
    /// Server request id (`request_id`), when the wire shape carried one.
    pub request_id: Option<String>,
}

impl fmt::Display for TemperaApiError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "Tempera request failed ({}): {}",
            self.status, self.message
        )?;
        if let Some(code) = &self.code {
            write!(f, " [code: {code}]")?;
        }
        if let Some(request_id) = &self.request_id {
            write!(f, " [request_id: {request_id}]")?;
        }
        Ok(())
    }
}

impl std::error::Error for TemperaApiError {}

/// Normalize any Tempera product error body into a [`TemperaApiError`].
///
/// Wire shapes handled (see `surface.json` `errorContract.wireShapes`):
/// - control plane / palette: `{"error": "<code>", "message": "<text>"}`
/// - tempo:                   `{"error": "<human message>"}`
/// - cradle / remi / data-engine: `{"error": {"code", "message", "request_id"?, ...}}`
/// - anything unparseable:    `message` is `status_text`, or `"request failed"`
///   when the status text is empty — the same fallback rule as the TypeScript
///   and Python packages, so one wire response yields one message everywhere.
pub fn normalize_error_body(status: u16, status_text: &str, body: &str) -> TemperaApiError {
    if let Some(root) = parse_json(body)
        && let Some(error) = root.get("error")
    {
        match error {
            Json::Obj(_) => {
                return TemperaApiError {
                    status,
                    code: error.get("code").and_then(Json::as_str).map(str::to_string),
                    message: error
                        .get("message")
                        .and_then(Json::as_str)
                        .unwrap_or(status_text)
                        .to_string(),
                    request_id: error
                        .get("request_id")
                        .and_then(Json::as_str)
                        .map(str::to_string),
                };
            }
            Json::Str(error_text) => {
                if let Some(message) = root.get("message").and_then(Json::as_str) {
                    return TemperaApiError {
                        status,
                        code: Some(error_text.clone()),
                        message: message.to_string(),
                        request_id: None,
                    };
                }
                return TemperaApiError {
                    status,
                    code: None,
                    message: error_text.clone(),
                    request_id: None,
                };
            }
            _ => {}
        }
    }

    TemperaApiError {
        status,
        code: None,
        message: if status_text.is_empty() {
            "request failed".to_string()
        } else {
            status_text.to_string()
        },
        request_id: None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn control_plane_shape_yields_code_and_message() {
        let error = normalize_error_body(401, "", r#"{"error":"invalid_token","message":"token expired"}"#,
        );
        assert_eq!(error.status, 401);
        assert_eq!(error.code.as_deref(), Some("invalid_token"));
        assert_eq!(error.message, "token expired");
        assert_eq!(error.request_id, None);
    }

    #[test]
    fn palette_shape_ignores_extra_status_member() {
        let error = normalize_error_body(404, "", r#"{"error":"not_found","message":"trace not found","status":404}"#,
        );
        assert_eq!(error.code.as_deref(), Some("not_found"));
        assert_eq!(error.message, "trace not found");
    }

    #[test]
    fn tempo_shape_is_message_only() {
        let error = normalize_error_body(400, "", r#"{"error":"session is drained"}"#);
        assert_eq!(error.code, None);
        assert_eq!(error.message, "session is drained");
        assert_eq!(error.request_id, None);
    }

    #[test]
    fn cradle_shape_extracts_all_three_and_skips_nested_extras() {
        let body = r#"{
            "error": {
                "code": "lane_unavailable",
                "message": "no python lane",
                "status": 503,
                "request_id": "req_123",
                "retryable": true,
                "details": {"lanes": ["js", "wasm"], "nested": {"depth": 2, "none": null}}
            }
        }"#;
        let error = normalize_error_body(503, "Service Unavailable", body);
        assert_eq!(error.code.as_deref(), Some("lane_unavailable"));
        assert_eq!(error.message, "no python lane");
        assert_eq!(error.request_id.as_deref(), Some("req_123"));
    }

    #[test]
    fn data_engine_shape_matches_the_cradle_normalization_path() {
        let body = r#"{
            "error": {
                "code": "INVALID_ARGUMENT",
                "message": "Bad envelope.",
                "status": 400,
                "request_id": "req-de-1",
                "retryable": false,
                "details": [{"field": "envelopes", "description": "must not be empty"}]
            }
        }"#;
        let error = normalize_error_body(400, "Bad Request", body);
        assert_eq!(error.code.as_deref(), Some("INVALID_ARGUMENT"));
        assert_eq!(error.message, "Bad envelope.");
        assert_eq!(error.request_id.as_deref(), Some("req-de-1"));
    }

    #[test]
    fn remi_shape_without_request_id() {
        let error = normalize_error_body(422, "", r#"{"error":{"code":"bad_scope","message":"scope is malformed"}}"#,
        );
        assert_eq!(error.code.as_deref(), Some("bad_scope"));
        assert_eq!(error.message, "scope is malformed");
        assert_eq!(error.request_id, None);
    }

    #[test]
    fn escaped_quotes_and_escapes_inside_messages_survive() {
        let error = normalize_error_body(400, "", r#"{"error":"bad_input","message":"field \"name\" is bad\n\ttab \\ slash \/ u: é"}"#,
        );
        assert_eq!(error.code.as_deref(), Some("bad_input"));
        assert_eq!(
            error.message,
            "field \"name\" is bad\n\ttab \\ slash / u: \u{e9}"
        );
    }

    #[test]
    fn surrogate_pair_escapes_decode() {
        let error = normalize_error_body(400, "", r#"{"error":"emoji 😀 done"}"#);
        assert_eq!(error.message, "emoji \u{1F600} done");
    }

    #[test]
    fn unknown_extra_fields_before_and_after_and_whitespace() {
        let body = "  \n\t{ \"trace\": [1, 2.5, -3e2, true, null], \"error\" : \"quota\" , \"message\": \"limit hit\", \"hint\": {\"docs\": \"https://x\"} }  \n";
        let error = normalize_error_body(429, "Too Many Requests", body);
        assert_eq!(error.code.as_deref(), Some("quota"));
        assert_eq!(error.message, "limit hit");
    }

    #[test]
    fn garbage_body_falls_back_to_status_text() {
        // Same rule as TS/Python: unparseable bodies surface the HTTP status
        // text, never the raw body (which may be a whole HTML error page).
        let error = normalize_error_body(502, "Bad Gateway", "  <html>bad gateway</html>  ");
        assert_eq!(error.code, None);
        assert_eq!(error.message, "Bad Gateway");
        assert_eq!(error.request_id, None);
    }

    #[test]
    fn truncated_json_falls_back_to_status_text() {
        let error = normalize_error_body(500, "Internal Server Error", r#"{"error":"boom"#);
        assert_eq!(error.code, None);
        assert_eq!(error.message, "Internal Server Error");
    }

    #[test]
    fn empty_status_text_falls_back_to_request_failed() {
        let error = normalize_error_body(500, "", "");
        assert_eq!(error.message, "request failed");
        let error = normalize_error_body(500, "", "   \n ");
        assert_eq!(error.message, "request failed");
    }

    #[test]
    fn object_without_error_member_falls_back() {
        let error = normalize_error_body(500, "Internal Server Error", r#"{"ok":false}"#);
        assert_eq!(error.code, None);
        assert_eq!(error.message, "Internal Server Error");
    }

    #[test]
    fn error_object_without_message_uses_status_text() {
        let error = normalize_error_body(500, "Internal Server Error", r#"{"error":{"code":"opaque"}}"#);
        assert_eq!(error.code.as_deref(), Some("opaque"));
        assert_eq!(error.message, "Internal Server Error");
    }

    #[test]
    fn non_string_error_member_falls_back() {
        let error = normalize_error_body(500, "Internal Server Error", r#"{"error":42}"#);
        assert_eq!(error.code, None);
        assert_eq!(error.message, "Internal Server Error");
    }

    #[test]
    fn display_carries_status_code_and_request_id() {
        let error = TemperaApiError {
            status: 429,
            code: Some("quota".to_string()),
            message: "limit hit".to_string(),
            request_id: Some("req_9".to_string()),
        };
        assert_eq!(
            error.to_string(),
            "Tempera request failed (429): limit hit [code: quota] [request_id: req_9]"
        );
        let source: &dyn std::error::Error = &error;
        assert!(source.to_string().contains("limit hit"));
    }

    #[test]
    fn scanner_rejects_trailing_garbage_and_control_chars() {
        assert!(parse_json("{\"a\":1} extra").is_none());
        assert!(parse_json("{\"a\":\"line\nbreak\"}").is_none());
        assert!(parse_json("").is_none());
        assert_eq!(
            parse_json("[0, -1, 2.5, 1e3]"),
            Some(Json::Arr(vec![
                Json::Num("0".into()),
                Json::Num("-1".into()),
                Json::Num("2.5".into()),
                Json::Num("1e3".into()),
            ]))
        );
    }
}
