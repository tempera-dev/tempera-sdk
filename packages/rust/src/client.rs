//! The unified Tempera client, HTTP-less: it resolves an operation from the
//! generated surface tables (`crate::surface`) and builds a fully-described
//! [`RequestSpec`] (method, URL, query, headers, JSON body) for the caller's
//! own HTTP client to send.
//!
//! Mirrors the TypeScript `createTemperaClient` dispatch semantics:
//! - Typed operations by product key + snake_case operation id, with wire
//!   (snake_case) parameter names.
//! - Declared query keys route to the query string; declared body keys plus
//!   `body_defaults` form the JSON body.
//! - Forward compatibility: undeclared parameters flow to the query string on
//!   GET/DELETE and into the JSON body otherwise, so a new server field is
//!   usable before the surface tables catch up.
//! - Auth kinds: `none`, `account` (account-session token),
//!   `introspectionSecret`, and `product` (per-audience bearer through
//!   [`crate::auth::TemperaAuth`], with unified tp_ API-key fallback).

use crate::auth::{TemperaAuth, urlencode};
use crate::error::json_escape;
use crate::surface;

/// One request parameter value, carrying enough type information to serialize
/// into either the query string or a JSON body member.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ParamValue {
    /// A string value (JSON string in bodies, plain text in query/paths).
    Str(String),
    /// An integer value (JSON number literal in bodies).
    Int(i64),
    /// A boolean value (JSON `true`/`false` literal in bodies).
    Bool(bool),
    /// A pre-serialized JSON fragment, spliced verbatim into the body (use for
    /// objects, arrays, floats, or nulls).
    RawJson(String),
}

impl ParamValue {
    /// Plain-text form, used for path substitution and query-string values.
    fn as_plain_string(&self) -> String {
        match self {
            ParamValue::Str(value) => value.clone(),
            ParamValue::Int(value) => value.to_string(),
            ParamValue::Bool(value) => value.to_string(),
            ParamValue::RawJson(value) => value.clone(),
        }
    }

    /// JSON form, used for body members.
    fn to_json_fragment(&self) -> String {
        match self {
            ParamValue::Str(value) => format!("\"{}\"", json_escape(value)),
            ParamValue::Int(value) => value.to_string(),
            ParamValue::Bool(value) => value.to_string(),
            ParamValue::RawJson(value) => value.clone(),
        }
    }
}

impl From<&str> for ParamValue {
    fn from(value: &str) -> Self {
        ParamValue::Str(value.to_string())
    }
}

impl From<String> for ParamValue {
    fn from(value: String) -> Self {
        ParamValue::Str(value)
    }
}

impl From<i64> for ParamValue {
    fn from(value: i64) -> Self {
        ParamValue::Int(value)
    }
}

impl From<bool> for ParamValue {
    fn from(value: bool) -> Self {
        ParamValue::Bool(value)
    }
}

/// A fully-described HTTP request for the caller's HTTP client to send.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RequestSpec {
    /// HTTP method (`GET`, `POST`, `PATCH`, `DELETE`).
    pub method: &'static str,
    /// Base URL plus the substituted path, WITHOUT the query string.
    pub url: String,
    /// Query parameters as unencoded key/value pairs.
    pub query: Vec<(String, String)>,
    /// Request headers, including `accept`, `content-type` (when a body is
    /// present), and `authorization` (per the operation's auth kind).
    pub headers: Vec<(String, String)>,
    /// Serialized JSON body, when the operation carries one.
    pub body_json: Option<String>,
}

impl RequestSpec {
    /// The complete URL: [`RequestSpec::url`] plus the urlencoded query string.
    pub fn full_url(&self) -> String {
        if self.query.is_empty() {
            return self.url.clone();
        }
        let encoded = self
            .query
            .iter()
            .map(|(key, value)| format!("{}={}", urlencode(key), urlencode(value)))
            .collect::<Vec<_>>()
            .join("&");
        format!("{}?{}", self.url, encoded)
    }
}

/// An error building a [`RequestSpec`]: a configuration or usage mistake
/// caught before any request is sent.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BuildError {
    /// No operation with this product key and operation id exists in the
    /// surface tables.
    UnknownOperation {
        /// Product key that was requested.
        product: String,
        /// Operation id that was requested.
        operation: String,
    },
    /// A `{placeholder}` in the operation path had no matching parameter.
    MissingPathParam {
        /// Product key of the operation.
        product: String,
        /// Operation id.
        operation: String,
        /// Name of the missing path parameter.
        name: String,
    },
    /// The operation needs an account-session token and none is configured.
    MissingAccountToken {
        /// Product key of the operation.
        product: String,
    },
    /// The operation needs the introspection secret and none is configured.
    MissingIntrospectionSecret {
        /// Product key of the operation.
        product: String,
    },
    /// The operation needs a product bearer and no credential resolves for
    /// its audience.
    MissingCredential {
        /// Product key of the operation.
        product: String,
        /// Token audience the bearer would be minted for.
        audience: String,
    },
    /// No base URL is configured for the product and its env var is unset.
    MissingBaseUrl {
        /// Product key of the operation.
        product: String,
        /// Environment variable that would supply the base URL.
        env_var: String,
    },
}

impl std::fmt::Display for BuildError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            BuildError::UnknownOperation { product, operation } => {
                write!(f, "unknown Tempera operation: {product}.{operation}")
            }
            BuildError::MissingPathParam {
                product,
                operation,
                name,
            } => write!(
                f,
                "{product}.{operation}: missing required path parameter \"{name}\""
            ),
            BuildError::MissingAccountToken { product } => write!(
                f,
                "{product}: an account token is required; call login()/signup() first or pass with_account_token(...)"
            ),
            BuildError::MissingIntrospectionSecret { product } => write!(
                f,
                "{product}: introspect_token requires the introspection secret; pass with_introspection_secret(...)"
            ),
            BuildError::MissingCredential { product, audience } => write!(
                f,
                "{product}: no credential for audience {audience}; pass a TemperaAuth with an api_key or {audience} tokens to call product endpoints"
            ),
            BuildError::MissingBaseUrl { product, env_var } => write!(
                f,
                "missing base URL for {product}; set {env_var} or pass with_base_url(\"{product}\", ...)"
            ),
        }
    }
}

impl std::error::Error for BuildError {}

/// The unified Tempera client: one credential set, every product, no HTTP.
///
/// Configure it with builder methods, then call [`TemperaClient::build_request`]
/// to turn `(product, operation, params)` into a [`RequestSpec`] for your own
/// HTTP client.
#[derive(Debug, Clone, Default)]
pub struct TemperaClient {
    /// Unified credential (per-audience OAuth tokens with tp_ API-key
    /// fallback) used by `auth: "product"` operations.
    pub auth: Option<TemperaAuth>,
    /// Account-session token used by `auth: "account"` (control-plane)
    /// operations; returned by login/signup.
    pub account_token: Option<String>,
    /// Server-side introspection secret used by `auth: "introspectionSecret"`
    /// operations.
    pub introspection_secret: Option<String>,
    /// Product key -> base URL overrides; falls back to each product's env
    /// var (`ProductSpec::env_var`).
    pub base_urls: Vec<(String, String)>,
}

impl TemperaClient {
    /// Create an empty client; add credentials and base URLs with the
    /// `with_*` builder methods.
    pub fn new() -> Self {
        Self::default()
    }

    /// Attach the unified [`TemperaAuth`] credential for product endpoints.
    pub fn with_auth(mut self, auth: TemperaAuth) -> Self {
        self.auth = Some(auth);
        self
    }

    /// Attach an account-session token for control-plane endpoints.
    pub fn with_account_token(mut self, token: impl Into<String>) -> Self {
        self.account_token = Some(token.into());
        self
    }

    /// Attach the introspection secret for `introspect_token`.
    pub fn with_introspection_secret(mut self, secret: impl Into<String>) -> Self {
        self.introspection_secret = Some(secret.into());
        self
    }

    /// Set the base URL for one product (overrides its env var).
    pub fn with_base_url(mut self, product: impl Into<String>, url: impl Into<String>) -> Self {
        let product = product.into();
        let url = url.into();
        if let Some(entry) = self.base_urls.iter_mut().find(|(key, _)| *key == product) {
            entry.1 = url;
        } else {
            self.base_urls.push((product, url));
        }
        self
    }

    /// Build the [`RequestSpec`] for one typed operation.
    ///
    /// `product` is a snake_case product key and `operation` a snake_case
    /// operation id from the surface tables (e.g. `("palette", "get_trace")`).
    /// Parameters use wire names (snake_case): path parameters substitute into
    /// the URL (percent-encoded), declared query keys go to the query string,
    /// declared body keys (plus the operation's `body_defaults`) form the JSON
    /// body, and undeclared extras go to the query on GET/DELETE and to the
    /// body otherwise.
    pub fn build_request(
        &self,
        product: &str,
        operation: &str,
        params: &[(&str, ParamValue)],
    ) -> Result<RequestSpec, BuildError> {
        let op = surface::find_operation(product, operation).ok_or_else(|| {
            BuildError::UnknownOperation {
                product: product.to_string(),
                operation: operation.to_string(),
            }
        })?;
        // Every operation's product key exists in the product table.
        let product_spec =
            surface::find_product(product).ok_or_else(|| BuildError::UnknownOperation {
                product: product.to_string(),
                operation: operation.to_string(),
            })?;

        let get_param = |name: &str| params.iter().find(|(key, _)| *key == name).map(|(_, v)| v);

        // Path substitution (percent-encoded); empty values count as missing.
        let mut path = op.path.to_string();
        for name in op.path_params {
            let value = get_param(name)
                .map(ParamValue::as_plain_string)
                .filter(|value| !value.is_empty())
                .ok_or_else(|| BuildError::MissingPathParam {
                    product: product.to_string(),
                    operation: operation.to_string(),
                    name: name.to_string(),
                })?;
            path = path.replace(&format!("{{{name}}}"), &urlencode(&value));
        }

        let mut consumed: Vec<&str> = op.path_params.to_vec();

        // Declared query keys.
        let mut query: Vec<(String, String)> = Vec::new();
        for key in op.query {
            if let Some(value) = get_param(key) {
                query.push((key.to_string(), value.as_plain_string()));
                consumed.push(key);
            }
        }

        // Declared body keys plus body defaults (defaults are JSON strings).
        let mut body: Option<Vec<(String, String)>> = None;
        if !op.body.is_empty() || !op.body_defaults.is_empty() {
            let mut members: Vec<(String, String)> = Vec::new();
            for (key, value) in op.body_defaults {
                members.push((key.to_string(), format!("\"{}\"", json_escape(value))));
            }
            for key in op.body {
                if let Some(value) = get_param(key) {
                    set_body_member(&mut members, key, value.to_json_fragment());
                    consumed.push(key);
                }
            }
            body = Some(members);
        }

        // Forward compatibility: undeclared parameters flow to the query
        // string on GET/DELETE and into the JSON body otherwise.
        for (key, value) in params {
            if consumed.contains(key) {
                continue;
            }
            if op.method == "GET" || op.method == "DELETE" {
                query.push(((*key).to_string(), value.as_plain_string()));
            } else {
                set_body_member(
                    body.get_or_insert_with(Vec::new),
                    key,
                    value.to_json_fragment(),
                );
            }
        }

        // Bearer per the operation's auth kind.
        let bearer: Option<String> =
            match op.auth {
                "none" => None,
                "account" => Some(self.account_token.clone().ok_or_else(|| {
                    BuildError::MissingAccountToken {
                        product: product.to_string(),
                    }
                })?),
                "introspectionSecret" => {
                    Some(self.introspection_secret.clone().ok_or_else(|| {
                        BuildError::MissingIntrospectionSecret {
                            product: product.to_string(),
                        }
                    })?)
                }
                _ => {
                    // "product": bearer minted for the product's audience, with
                    // DEFAULT_AUDIENCE as the fallback for audience-less products.
                    let audience = product_spec.audience.unwrap_or(surface::DEFAULT_AUDIENCE);
                    let missing = || BuildError::MissingCredential {
                        product: product.to_string(),
                        audience: audience.to_string(),
                    };
                    let auth = self.auth.as_ref().ok_or_else(missing)?;
                    Some(auth.bearer_for(audience).ok_or_else(missing)?.to_string())
                }
            };

        // Base URL: explicit override, then the product's env var.
        let base_url = self
            .base_urls
            .iter()
            .find(|(key, _)| key == product)
            .map(|(_, url)| url.clone())
            .or_else(|| {
                std::env::var(product_spec.env_var)
                    .ok()
                    .filter(|v| !v.is_empty())
            })
            .ok_or_else(|| BuildError::MissingBaseUrl {
                product: product.to_string(),
                env_var: product_spec.env_var.to_string(),
            })?;
        let base_url = base_url.trim_end_matches('/').to_string();

        let body_json = body.map(|members| {
            let inner = members
                .iter()
                .map(|(key, value)| format!("\"{}\":{}", json_escape(key), value))
                .collect::<Vec<_>>()
                .join(",");
            format!("{{{inner}}}")
        });

        let mut headers: Vec<(String, String)> =
            vec![("accept".to_string(), "application/json".to_string())];
        if body_json.is_some() {
            headers.push(("content-type".to_string(), "application/json".to_string()));
        }
        if let Some(bearer) = bearer {
            headers.push(("authorization".to_string(), format!("Bearer {bearer}")));
        }

        Ok(RequestSpec {
            method: op.method,
            url: format!("{base_url}{path}"),
            query,
            headers,
            body_json,
        })
    }
}

/// Insert or replace one serialized JSON member, keeping keys unique.
fn set_body_member(members: &mut Vec<(String, String)>, key: &str, value: String) {
    if let Some(member) = members.iter_mut().find(|(existing, _)| existing == key) {
        member.1 = value;
    } else {
        members.push((key.to_string(), value));
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::auth::TokenSet;
    use crate::surface::{OPERATIONS, PRODUCTS};

    fn base_url_for(product: &str) -> String {
        format!("https://{product}.example.test")
    }

    fn full_client() -> TemperaClient {
        let mut client = TemperaClient::new()
            .with_auth(TemperaAuth::new("https://api.tempera.dev").with_api_key("tp_key_1"))
            .with_account_token("acct_token_1")
            .with_introspection_secret("intro_secret_1");
        for product in PRODUCTS {
            client = client.with_base_url(product.key, base_url_for(product.key));
        }
        client
    }

    fn header<'a>(spec: &'a RequestSpec, name: &str) -> Option<&'a str> {
        spec.headers
            .iter()
            .find(|(key, _)| key == name)
            .map(|(_, value)| value.as_str())
    }

    #[test]
    fn builds_every_operation_in_the_surface_tables() {
        let client = full_client();
        for op in OPERATIONS {
            let params: Vec<(&str, ParamValue)> = op
                .path_params
                .iter()
                .map(|name| (*name, ParamValue::from(format!("{name}_1"))))
                .collect();
            let spec = client
                .build_request(op.product, op.id, &params)
                .unwrap_or_else(|error| panic!("{}.{} failed: {error}", op.product, op.id));

            assert_eq!(spec.method, op.method, "{}.{}", op.product, op.id);

            let mut expected_path = op.path.to_string();
            for name in op.path_params {
                expected_path = expected_path.replace(&format!("{{{name}}}"), &format!("{name}_1"));
            }
            assert_eq!(
                spec.url,
                format!("{}{}", base_url_for(op.product), expected_path),
                "{}.{}",
                op.product,
                op.id
            );

            // Auth header per kind.
            let auth_header = header(&spec, "authorization");
            match op.auth {
                "none" => assert_eq!(auth_header, None, "{}.{}", op.product, op.id),
                "account" => assert_eq!(auth_header, Some("Bearer acct_token_1")),
                "introspectionSecret" => assert_eq!(auth_header, Some("Bearer intro_secret_1")),
                "product" => assert_eq!(auth_header, Some("Bearer tp_key_1")),
                other => panic!("unexpected auth kind {other}"),
            }
            assert_eq!(header(&spec, "accept"), Some("application/json"));

            // Body defaults are always present in the serialized body.
            if op.body.is_empty() && op.body_defaults.is_empty() {
                assert_eq!(spec.body_json, None, "{}.{}", op.product, op.id);
                assert_eq!(header(&spec, "content-type"), None);
            } else {
                let body = spec.body_json.as_deref().expect("body expected");
                for (key, value) in op.body_defaults {
                    assert!(
                        body.contains(&format!("\"{key}\":\"{value}\"")),
                        "{}.{} body {body} missing default {key}",
                        op.product,
                        op.id
                    );
                }
                assert_eq!(header(&spec, "content-type"), Some("application/json"));
            }
            assert!(spec.query.is_empty(), "{}.{}", op.product, op.id);
        }
    }

    #[test]
    fn login_body_carries_the_mode_default() {
        let client = full_client();
        let spec = client
            .build_request(
                "control_plane",
                "login",
                &[
                    ("email", "dev@example.test".into()),
                    ("password", "hunter2".into()),
                ],
            )
            .unwrap();
        let body = spec.body_json.unwrap();
        assert!(body.contains("\"mode\":\"login\""));
        assert!(body.contains("\"email\":\"dev@example.test\""));
        assert!(body.contains("\"password\":\"hunter2\""));
        assert!(body.starts_with('{') && body.ends_with('}'));
    }

    #[test]
    fn explicit_param_overrides_a_body_default_without_duplication() {
        let client = full_client();
        let spec = client
            .build_request(
                "control_plane",
                "signup",
                &[
                    ("email", "dev@example.test".into()),
                    ("password", "hunter2".into()),
                    ("mode", "signup_custom".into()),
                ],
            )
            .unwrap();
        let body = spec.body_json.unwrap();
        assert!(body.contains("\"mode\":\"signup_custom\""));
        assert_eq!(body.matches("\"mode\":").count(), 1);
    }

    #[test]
    fn declared_query_keys_route_to_the_query_string() {
        let client = full_client();
        let spec = client
            .build_request(
                "palette",
                "list_traces",
                &[
                    ("tenant_id", "tenant_1".into()),
                    ("limit", ParamValue::Int(25)),
                    ("status", "error".into()),
                ],
            )
            .unwrap();
        assert_eq!(spec.url, "https://palette.example.test/v1/traces/tenant_1");
        assert!(
            spec.query
                .contains(&("limit".to_string(), "25".to_string()))
        );
        assert!(
            spec.query
                .contains(&("status".to_string(), "error".to_string()))
        );
        assert_eq!(spec.body_json, None);
    }

    #[test]
    fn forward_compat_extras_go_to_query_on_get_and_body_on_post() {
        let client = full_client();

        let get_spec = client
            .build_request(
                "tempo",
                "list_runs",
                &[
                    ("new_filter", "on".into()),
                    ("flag", ParamValue::Bool(true)),
                ],
            )
            .unwrap();
        assert!(
            get_spec
                .query
                .contains(&("new_filter".to_string(), "on".to_string()))
        );
        assert!(
            get_spec
                .query
                .contains(&("flag".to_string(), "true".to_string()))
        );
        assert_eq!(get_spec.body_json, None);

        let post_spec = client
            .build_request(
                "remi",
                "project",
                &[
                    ("limit", ParamValue::Int(10)),
                    (
                        "new_option",
                        ParamValue::RawJson("{\"a\":[1,2]}".to_string()),
                    ),
                    ("dry_run", ParamValue::Bool(false)),
                ],
            )
            .unwrap();
        let body = post_spec.body_json.unwrap();
        assert!(body.contains("\"limit\":10"));
        assert!(body.contains("\"new_option\":{\"a\":[1,2]}"));
        assert!(body.contains("\"dry_run\":false"));
    }

    #[test]
    fn extras_create_a_body_on_post_operations_without_declared_body() {
        let client = full_client();
        let spec = client
            .build_request(
                "tempo",
                "adopt_session",
                &[("session_id", "sess_1".into()), ("surface", "ui".into())],
            )
            .unwrap();
        assert_eq!(spec.body_json.as_deref(), Some("{\"surface\":\"ui\"}"));
        assert_eq!(header(&spec, "content-type"), Some("application/json"));
    }

    #[test]
    fn missing_path_param_is_an_error() {
        let client = full_client();
        let error = client
            .build_request("palette", "get_trace", &[("tenant_id", "tenant_1".into())])
            .unwrap_err();
        assert_eq!(
            error,
            BuildError::MissingPathParam {
                product: "palette".to_string(),
                operation: "get_trace".to_string(),
                name: "trace_id".to_string(),
            }
        );
        assert!(
            error
                .to_string()
                .contains("missing required path parameter \"trace_id\"")
        );

        // Empty values count as missing, mirroring the TypeScript client.
        let error = client
            .build_request(
                "palette",
                "get_trace",
                &[("tenant_id", "tenant_1".into()), ("trace_id", "".into())],
            )
            .unwrap_err();
        assert!(matches!(error, BuildError::MissingPathParam { name, .. } if name == "trace_id"));
    }

    #[test]
    fn missing_credentials_are_errors() {
        let mut client = TemperaClient::new();
        for product in PRODUCTS {
            client = client.with_base_url(product.key, base_url_for(product.key));
        }

        let error = client
            .build_request("control_plane", "me", &[])
            .unwrap_err();
        assert_eq!(
            error,
            BuildError::MissingAccountToken {
                product: "control_plane".to_string()
            }
        );
        assert!(error.to_string().contains("account token"));

        let error = client
            .build_request(
                "control_plane",
                "introspect_token",
                &[("token", "tp_x".into())],
            )
            .unwrap_err();
        assert_eq!(
            error,
            BuildError::MissingIntrospectionSecret {
                product: "control_plane".to_string()
            }
        );

        let error = client.build_request("remi", "get_stats", &[]).unwrap_err();
        assert_eq!(
            error,
            BuildError::MissingCredential {
                product: "remi".to_string(),
                audience: "remi".to_string(),
            }
        );
        assert!(
            error
                .to_string()
                .contains("no credential for audience remi")
        );

        // An auth without any credential for the audience also fails.
        let client = client.with_auth(TemperaAuth::new("https://api.tempera.dev"));
        let error = client.build_request("remi", "get_stats", &[]).unwrap_err();
        assert!(matches!(error, BuildError::MissingCredential { .. }));
    }

    #[test]
    fn audience_token_is_preferred_over_the_api_key() {
        let auth = TemperaAuth::new("https://api.tempera.dev")
            .with_api_key("tp_key_1")
            .with_tokens(
                "tempo",
                TokenSet {
                    access_token: "at_tempo".into(),
                    ..TokenSet::default()
                },
            );
        let client = TemperaClient::new()
            .with_auth(auth)
            .with_base_url("tempo", base_url_for("tempo"))
            .with_base_url("cradle", base_url_for("cradle"));

        let spec = client.build_request("tempo", "list_sessions", &[]).unwrap();
        assert_eq!(header(&spec, "authorization"), Some("Bearer at_tempo"));

        // No cradle token: falls back to the unified API key.
        let spec = client
            .build_request("cradle", "get_capabilities", &[])
            .unwrap();
        assert_eq!(header(&spec, "authorization"), Some("Bearer tp_key_1"));
    }

    #[test]
    fn action_suffix_paths_keep_the_literal_colon_unencoded() {
        let client = full_client();
        let spec = client
            .build_request("data_engine", "ingest_artifact", &[("project_id", "p1".into())])
            .unwrap();
        assert_eq!(
            spec.url,
            "https://data_engine.example.test/v1/projects/p1/artifacts:ingest"
        );
        assert!(!spec.full_url().contains("%3A"), "colon must not be percent-encoded");

        // Colons inside a substituted path *value* are still encoded.
        let spec = client
            .build_request(
                "data_engine",
                "get_job",
                &[("project_id", "p1".into()), ("job_id", "job:1".into())],
            )
            .unwrap();
        assert_eq!(
            spec.url,
            "https://data_engine.example.test/v1/projects/p1/jobs/job%3A1"
        );
    }

    #[test]
    fn path_params_are_percent_encoded() {
        let client = full_client();
        let spec = client
            .build_request(
                "palette",
                "get_trace",
                &[
                    ("tenant_id", "acme corp/1".into()),
                    ("trace_id", "trace#9?x=1".into()),
                ],
            )
            .unwrap();
        assert_eq!(
            spec.url,
            "https://palette.example.test/v1/traces/acme%20corp%2F1/trace%239%3Fx%3D1"
        );
    }

    #[test]
    fn full_url_appends_the_urlencoded_query() {
        let client = full_client();
        let spec = client
            .build_request(
                "palette",
                "search_spans",
                &[
                    ("tenant_id", "tenant_1".into()),
                    ("q", "tool error & retry".into()),
                    ("limit", ParamValue::Int(5)),
                ],
            )
            .unwrap();
        assert_eq!(
            spec.full_url(),
            "https://palette.example.test/v1/search/tenant_1/spans?q=tool%20error%20%26%20retry&limit=5"
        );

        let plain = client.build_request("tempo", "health", &[]).unwrap();
        assert_eq!(plain.full_url(), plain.url);
    }

    #[test]
    fn base_url_trailing_slash_is_trimmed() {
        let client = TemperaClient::new().with_base_url("tempo", "https://tempo.example.test///");
        let spec = client.build_request("tempo", "health", &[]).unwrap();
        assert_eq!(spec.url, "https://tempo.example.test/health");
    }

    #[test]
    fn missing_base_url_mentions_the_env_var() {
        // Guard: only meaningful when the env var is not set in this process.
        if std::env::var("TEMPERA_CONTROL_PLANE_URL").is_ok() {
            return;
        }
        let client = TemperaClient::new();
        let error = client
            .build_request("control_plane", "health", &[])
            .unwrap_err();
        assert_eq!(
            error,
            BuildError::MissingBaseUrl {
                product: "control_plane".to_string(),
                env_var: "TEMPERA_CONTROL_PLANE_URL".to_string(),
            }
        );
        assert!(error.to_string().contains("TEMPERA_CONTROL_PLANE_URL"));
    }

    #[test]
    fn unknown_operation_is_an_error() {
        let client = full_client();
        let error = client
            .build_request("palette", "does_not_exist", &[])
            .unwrap_err();
        assert!(matches!(error, BuildError::UnknownOperation { .. }));
        let error = client
            .build_request("not_a_product", "health", &[])
            .unwrap_err();
        assert_eq!(
            error.to_string(),
            "unknown Tempera operation: not_a_product.health"
        );
    }

    #[test]
    fn body_strings_are_json_escaped() {
        let client = full_client();
        let spec = client
            .build_request(
                "remi",
                "remember",
                &[
                    ("tenant_id", "tenant_1".into()),
                    ("project_id", "proj_1".into()),
                    ("kind", "note".into()),
                    ("text", "line1\nline2 \"quoted\"".into()),
                ],
            )
            .unwrap();
        let body = spec.body_json.unwrap();
        assert!(body.contains("\"text\":\"line1\\nline2 \\\"quoted\\\"\""));
        // The serialized body parses back with the crate's own scanner.
        assert!(crate::error::parse_json(&body).is_some());
    }
}
