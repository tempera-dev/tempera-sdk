// Conformance and unit tests for the Tempera C++ SDK.
//
// No test framework: a handful of assertion macros, a plain main(), and a
// non-zero exit status when anything failed. The centrepiece mirrors the Rust
// and C suites' conformance loop -- every generated operation is built and
// checked -- and the rest pins the behaviours the other language packages also
// assert.
//
// setenv()/unsetenv() are POSIX rather than ISO C++, and glibc only declares
// them when a feature-test macro asks for POSIX; _DEFAULT_SOURCE has to be set
// before any header is pulled in. Nothing in the library itself needs them.
#ifndef _DEFAULT_SOURCE
#define _DEFAULT_SOURCE 1
#endif

#include <array>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <string_view>
#include <vector>

#include "tempera/tempera.hpp"

namespace {

int checks = 0;
int failures = 0;

void record(bool ok, const char *file, int line, const std::string &detail) {
    ++checks;
    if (!ok) {
        ++failures;
        (void)std::fprintf(stderr, "FAIL %s:%d: %s\n", file, line, detail.c_str());
    }
}

#define CHECK(condition, detail) record((condition), __FILE__, __LINE__, (detail))

#define CHECK_EQ(actual, expected)                                                            \
    do {                                                                                      \
        const auto &actual_value = (actual);                                                  \
        const auto &expected_value = (expected);                                              \
        record(actual_value == expected_value, __FILE__, __LINE__,                            \
               "expected \"" + std::string(expected_value) + "\", got \"" +                   \
                   std::string(actual_value) + "\"");                                         \
    } while (false)

using tempera::Auth;
using tempera::BuildError;
using tempera::Client;
using tempera::ErrorCode;
using tempera::Params;
using tempera::ParamValue;
using tempera::RequestSpec;
using tempera::Result;

std::string base_url_for(std::string_view product) {
    return "https://" + std::string(product) + ".example.test";
}

Auth test_auth() { return Auth("https://staging-api.tempera.dev").with_api_key("tp_key_1"); }

Client full_client(const Auth &auth) {
    Client client;
    client.with_auth(auth)
        .with_account_token("acct_token_1")
        .with_introspection_secret("intro_secret_1");
    for (const tempera::surface::ProductSpec &product : tempera::surface::PRODUCTS) {
        client.with_base_url(std::string(product.key), base_url_for(product.key));
    }
    return client;
}

std::string header_or_empty(const RequestSpec &request, std::string_view name) {
    const std::string *value = request.header(name);
    return value == nullptr ? std::string() : *value;
}

/// The sample value for one path parameter: a producer-declared AIP resource
/// pattern with every wildcard filled in, or "<name>_1".
std::string sample_path_param(const tempera::surface::OperationSpec &op, std::string_view name) {
    for (const tempera::surface::StrPair &entry : op.path_param_templates) {
        if (entry.key == name) {
            std::string out;
            for (char character : entry.value) {
                if (character == '*') {
                    out += std::string(name) + "_1";
                } else {
                    out += character;
                }
            }
            return out;
        }
    }
    return std::string(name) + "_1";
}

// -------------------------------------------------------------------------
// 1. Conformance: every generated operation builds
// -------------------------------------------------------------------------

void test_every_operation_builds(const Client &client) {
    std::size_t built = 0;

    CHECK(tempera::surface::OPERATIONS.size() > 400,
          "expected the full operation table, got " +
              std::to_string(tempera::surface::OPERATIONS.size()));

    for (const tempera::surface::OperationSpec &op : tempera::surface::OPERATIONS) {
        Params params;
        std::vector<std::string> samples;

        CHECK(!op.upstream_operation_id.empty(),
              std::string(op.product) + "." + std::string(op.id) + ": producer operation id");
        for (std::string_view name : op.path_params) {
            samples.push_back(sample_path_param(op, name));
            params.emplace_back(std::string(name), ParamValue(samples.back()));
        }
        for (std::string_view name : op.required_query) {
            params.emplace_back(std::string(name), ParamValue("sample-query"));
        }

        const Result<RequestSpec> built_request = client.build_request(op.product, op.id, params);
        const std::string label = std::string(op.product) + "." + std::string(op.id);
        if (!built_request.has_value()) {
            ++checks;
            ++failures;
            (void)std::fprintf(stderr, "FAIL %s failed to build: %s\n", label.c_str(),
                               built_request.error().message().c_str());
            continue;
        }
        ++built;
        const RequestSpec &request = built_request.value();

        CHECK_EQ(request.method, op.method);

        std::string path{op.path};
        for (std::size_t index = 0; index < samples.size(); ++index) {
            path = tempera::detail::substitute_path(path, op.path_params[index], samples[index]);
        }
        CHECK_EQ(request.url, base_url_for(op.product) + path);

        const std::string authorization = header_or_empty(request, "authorization");
        if (op.auth == "none") {
            CHECK(authorization.empty(), label + ": unauthenticated operation carries a bearer");
        } else if (op.auth == "account") {
            CHECK_EQ(authorization, std::string("Bearer acct_token_1"));
        } else if (op.auth == "introspectionSecret") {
            CHECK_EQ(authorization, std::string("Bearer intro_secret_1"));
        } else {
            // product and oauthResource both fall back to the tp_ API key.
            CHECK_EQ(authorization, std::string("Bearer tp_key_1"));
        }
        CHECK_EQ(header_or_empty(request, "accept"), std::string("application/json"));

        if (op.body.empty() && op.body_defaults.empty()) {
            CHECK(!request.body_json.has_value(), label + ": unexpected body");
            CHECK(request.header("content-type") == nullptr, label + ": unexpected content-type");
        } else {
            CHECK(request.body_json.has_value(), label + ": expected a body");
            for (const tempera::surface::StrPair &entry : op.body_defaults) {
                const std::string fragment =
                    "\"" + std::string(entry.key) + "\":\"" + std::string(entry.value) + "\"";
                CHECK(request.body_json.has_value() &&
                          request.body_json->find(fragment) != std::string::npos,
                      label + ": body missing default " + std::string(entry.key));
            }
            CHECK_EQ(header_or_empty(request, "content-type"), std::string("application/json"));
        }

        for (std::string_view name : op.required_query) {
            CHECK(request.query_value(name) != nullptr,
                  label + ": missing required query " + std::string(name));
        }
    }
    CHECK(built == tempera::surface::OPERATIONS.size(),
          "built " + std::to_string(built) + " of " +
              std::to_string(tempera::surface::OPERATIONS.size()) + " operations");
}

// -------------------------------------------------------------------------
// 2. Wire names, snake_case aliases, and ambiguity
// -------------------------------------------------------------------------

void test_alias_handling(const Client &client) {
    Result<RequestSpec> canonical = client.build_request(
        "palette", "get_trace", {{"tenantId", "tenant_1"}, {"traceId", "trace_1"}});
    CHECK(canonical.has_value(), "canonical wire names rejected");
    CHECK_EQ(canonical.value().url,
             std::string("https://palette.example.test/v1/traces/tenant_1/trace_1"));

    Result<RequestSpec> alias = client.build_request(
        "palette", "get_trace", {{"tenant_id", "tenant_1"}, {"trace_id", "trace_1"}});
    CHECK(alias.has_value(), "snake_case aliases rejected");
    CHECK_EQ(alias.value().url,
             std::string("https://palette.example.test/v1/traces/tenant_1/trace_1"));

    Result<RequestSpec> both = client.build_request(
        "palette", "get_trace",
        {{"tenantId", "tenant_1"}, {"tenant_id", "tenant_2"}, {"traceId", "trace_1"}});
    CHECK(!both.has_value(), "ambiguous alias accepted");
    if (!both.has_value()) {
        CHECK(both.error().code == ErrorCode::DuplicateParameterAlias, "wrong error code");
        CHECK(both.error().message().find("not both") != std::string::npos,
              "unhelpful alias detail: " + both.error().message());
    }

    // Declared query keys emit the producer's canonical name, not the alias.
    Result<RequestSpec> listed = client.build_request(
        "palette", "list_traces",
        {{"tenant_id", "tenant_1"}, {"pageSize", 25}, {"status", "error"}});
    CHECK(listed.has_value(), "list_traces failed");
    CHECK_EQ(listed.value().url, std::string("https://palette.example.test/v1/traces/tenant_1"));
    CHECK(listed.value().query_value("pageSize") != nullptr &&
              *listed.value().query_value("pageSize") == "25",
          "int parameter not stringified in the query");
    CHECK(listed.value().query_value("page_size") == nullptr, "alias leaked onto the wire");
}

// -------------------------------------------------------------------------
// 3. forbiddenBody: principal-derived fields are rejected
// -------------------------------------------------------------------------

void test_forbidden_body(const Client &client) {
    // No shipped operation declares forbiddenBody yet, so the rule is proven
    // against a synthetic contract through the spec-taking overload, and then
    // re-checked across the whole generated table so it arms itself the moment
    // a producer does declare one.
    static constexpr std::array<std::string_view, 1> forbidden = {"tenantId"};
    static constexpr std::array<std::string_view, 1> body = {"note"};
    static constexpr tempera::surface::ProductSpec product{
        .key = "palette",
        .name = "palette",
        .repository = "https://example.test/palette",
        .env_var = "TEMPERA_PALETTE_URL",
        .audience = "palette",
        .description = "Test."};
    static constexpr tempera::surface::OperationSpec op{
        .product = "palette",
        .id = "synthetic_write",
        .upstream_operation_id = "syntheticWrite",
        .method = "POST",
        .path = "/v1/synthetic",
        .auth = "product",
        .auth_audience = std::nullopt,
        .path_params = {},
        .path_param_templates = {},
        .query = {},
        .required_query = {},
        .headers = {},
        .required_headers = {},
        .body = body,
        .forbidden_body = forbidden,
        .required_body = {},
        .body_defaults = {},
        .request_body_kind = "json",
        .request_content_type = std::nullopt,
        .scope = std::nullopt,
        .physical_action = false,
        .prepare_commit_required = false,
        .safe_retry = "none",
        .description = "Synthetic test operation."};

    Result<RequestSpec> allowed = client.build_request(op, product, {{"note", "hello"}});
    CHECK(allowed.has_value(), "synthetic operation failed to build");
    if (allowed.has_value()) {
        CHECK(allowed.value().body_json.has_value() &&
                  *allowed.value().body_json == "{\"note\":\"hello\"}",
              "synthetic body is wrong");
    }

    Result<RequestSpec> refused =
        client.build_request(op, product, {{"note", "hello"}, {"tenantId", "tenant_1"}});
    CHECK(!refused.has_value(), "forbidden field accepted");
    if (!refused.has_value()) {
        CHECK(refused.error().code == ErrorCode::ForbiddenBodyField, "wrong error code");
        CHECK(refused.error().message().find("authenticated principal") != std::string::npos,
              "unhelpful detail: " + refused.error().message());
    }

    // The snake_case alias of a forbidden field is refused too.
    Result<RequestSpec> aliased =
        client.build_request(op, product, {{"note", "hello"}, {"tenant_id", "tenant_1"}});
    CHECK(!aliased.has_value() && aliased.error().code == ErrorCode::ForbiddenBodyField,
          "forbidden alias accepted");

    for (const tempera::surface::OperationSpec &generated : tempera::surface::OPERATIONS) {
        for (std::string_view name : generated.forbidden_body) {
            Result<RequestSpec> built = client.build_request(generated.product, generated.id,
                                                             {{std::string(name), "x"}});
            CHECK(!built.has_value() && built.error().code == ErrorCode::ForbiddenBodyField,
                  std::string(generated.product) + "." + std::string(generated.id) +
                      " accepted forbidden field " + std::string(name));
        }
    }
}

// -------------------------------------------------------------------------
// 4. AIP resource patterns
// -------------------------------------------------------------------------

void test_aip_path_patterns(const Client &client) {
    Result<RequestSpec> valid =
        client.build_request("data_engine", "list_use_cases", {{"parent", "projects/p_1"}});
    CHECK(valid.has_value(), "valid AIP parent rejected");
    CHECK_EQ(valid.value().url,
             std::string("https://data_engine.example.test/v1/projects/p_1/use-cases"));

    // Only the wildcard segment is percent-encoded; the literal slash stays.
    Result<RequestSpec> encoded =
        client.build_request("data_engine", "list_use_cases", {{"parent", "projects/p 1"}});
    CHECK(encoded.has_value(), "encodable parent rejected");
    CHECK_EQ(encoded.value().url,
             std::string("https://data_engine.example.test/v1/projects/p%201/use-cases"));

    for (std::string_view rejected : {"projects/", "projects/.", "projects/..", "tenants/p_1",
                                      "projects/a/b", "projects", "/projects/p_1"}) {
        Result<RequestSpec> built = client.build_request("data_engine", "list_use_cases",
                                                         {{"parent", std::string(rejected)}});
        CHECK(!built.has_value(), "AIP pattern accepted \"" + std::string(rejected) + "\"");
        if (!built.has_value()) {
            CHECK(built.error().code == ErrorCode::InvalidPathParam ||
                      built.error().code == ErrorCode::MissingPathParam,
                  "unexpected error for \"" + std::string(rejected) + "\"");
        }
    }

    // A path parameter without a template is simply percent-encoded.
    Result<RequestSpec> plain = client.build_request(
        "palette", "get_trace", {{"tenantId", "tenant/1"}, {"traceId", "trace 1"}});
    CHECK(plain.has_value(), "percent-encoded path rejected");
    CHECK_EQ(plain.value().url,
             std::string("https://palette.example.test/v1/traces/tenant%2F1/trace%201"));
}

// -------------------------------------------------------------------------
// 5. Forward compatibility: undeclared parameters spill
// -------------------------------------------------------------------------

void test_forward_compatible_spill(const Client &client) {
    Result<RequestSpec> read = client.build_request(
        "palette", "get_trace",
        {{"tenantId", "tenant_1"}, {"traceId", "trace_1"}, {"brandNewFilter", "yes"}});
    CHECK(read.has_value(), "GET spill failed");
    CHECK(read.value().query_value("brandNewFilter") != nullptr &&
              *read.value().query_value("brandNewFilter") == "yes",
          "GET extra did not reach the query string");
    CHECK(!read.value().body_json.has_value(), "GET spill produced a body");

    Result<RequestSpec> write = client.build_request(
        "control_plane", "create_hosted_session",
        {{"mode", "login"}, {"brandNewField", "yes"}, {"attempt", 2}, {"flagged", true}});
    CHECK(write.has_value(), "POST spill failed");
    const std::string &body = *write.value().body_json;
    CHECK(body.find("\"mode\":\"login\"") != std::string::npos, "declared member missing: " + body);
    CHECK(body.find("\"brandNewField\":\"yes\"") != std::string::npos,
          "undeclared string missing: " + body);
    CHECK(body.find("\"attempt\":2") != std::string::npos, "undeclared int missing: " + body);
    CHECK(body.find("\"flagged\":true") != std::string::npos, "undeclared bool missing: " + body);
    CHECK(write.value().query.empty(), "POST spill leaked into the query string");
    CHECK_EQ(header_or_empty(write.value(), "content-type"), std::string("application/json"));

    // DELETE behaves like GET.
    for (const tempera::surface::OperationSpec &op : tempera::surface::OPERATIONS) {
        if (op.method != "DELETE" || !op.path_params.empty()) {
            continue;
        }
        Result<RequestSpec> removed =
            client.build_request(op.product, op.id, {{"brandNewFlag", "1"}});
        CHECK(removed.has_value(), "DELETE spill failed");
        if (removed.has_value()) {
            CHECK(removed.value().query_value("brandNewFlag") != nullptr,
                  "DELETE extra did not reach the query string");
            CHECK(!removed.value().body_json.has_value(), "DELETE spill produced a body");
        }
        break;
    }
}

// -------------------------------------------------------------------------
// 6. Error normalization
// -------------------------------------------------------------------------

void test_error_normalization() {
    tempera::ApiError error = tempera::normalize_error_body(
        400, "Bad Request",
        R"({"error":{"code":400,"status":"INVALID_ARGUMENT","message":"bad field",)"
        R"("details":[{"@type":"type.googleapis.com/google.rpc.ErrorInfo",)"
        R"("reason":"FIELD_INVALID"}],"requestId":"req_1"}})");
    CHECK(error.status == 400, "status not carried");
    CHECK_EQ(error.code.value_or(""), std::string("INVALID_ARGUMENT"));
    CHECK_EQ(error.message, std::string("bad field"));
    CHECK_EQ(error.reason.value_or(""), std::string("FIELD_INVALID"));
    CHECK_EQ(error.request_id.value_or(""), std::string("req_1"));

    // error.code, when it is a string and error.status is not.
    error = tempera::normalize_error_body(
        404, "", R"({"error":{"code":"not_found","message":"trace not found"}})");
    CHECK_EQ(error.code.value_or(""), std::string("not_found"));
    CHECK_EQ(error.message, std::string("trace not found"));

    // A numeric code is not a code: neither member is a string.
    error = tempera::normalize_error_body(500, "Server Error",
                                          R"({"error":{"code":500,"message":"boom"}})");
    CHECK(!error.code.has_value(), "numeric code became a code");
    CHECK_EQ(error.message, std::string("boom"));

    // Message falls back to the HTTP status text.
    error = tempera::normalize_error_body(503, "Service Unavailable", R"({"error":{"code":503}})");
    CHECK_EQ(error.message, std::string("Service Unavailable"));

    // request_id is accepted in either spelling, requestId first.
    error = tempera::normalize_error_body(
        429, "", R"({"error":{"message":"slow down","request_id":"req_snake"}})");
    CHECK_EQ(error.request_id.value_or(""), std::string("req_snake"));
    error = tempera::normalize_error_body(
        429, "",
        R"({"error":{"message":"slow","requestId":"req_camel","request_id":"req_snake"}})");
    CHECK_EQ(error.request_id.value_or(""), std::string("req_camel"));

    // Legacy flat shape: a string error plus a top-level message.
    error = tempera::normalize_error_body(
        401, "", R"({"error":"invalid_token","message":"token expired"})");
    CHECK_EQ(error.code.value_or(""), std::string("invalid_token"));
    CHECK_EQ(error.message, std::string("token expired"));
    CHECK(!error.request_id.has_value(), "flat shape invented a request id");

    // Legacy message-only shape.
    error = tempera::normalize_error_body(400, "", R"({"error":"something went wrong"})");
    CHECK(!error.code.has_value(), "message-only shape invented a code");
    CHECK_EQ(error.message, std::string("something went wrong"));

    // Unparseable bodies fall back to the status text, then to a literal.
    error = tempera::normalize_error_body(502, "Bad Gateway", "<html>nope</html>");
    CHECK_EQ(error.message, std::string("Bad Gateway"));
    error = tempera::normalize_error_body(0, "", "");
    CHECK_EQ(error.message, std::string("request failed"));

    // Escapes and non-BMP payloads survive the scanner intact.
    error = tempera::normalize_error_body(
        400, "", R"({"error":"quota","message":"café 🚀 \"quoted\""})");
    CHECK_EQ(error.message, std::string("caf\xc3\xa9 \xf0\x9f\x9a\x80 \"quoted\""));

    CHECK(error.to_string().find("[code: quota]") != std::string::npos,
          "to_string omits the code: " + error.to_string());
}

// -------------------------------------------------------------------------
// 7. The error enum
// -------------------------------------------------------------------------

void test_error_enum(const Auth &auth) {
    const Client client = full_client(auth);
    Client bare;
    bare.with_base_url("control_plane", "https://control.example.test")
        .with_base_url("palette", "https://palette.example.test");

    for (ErrorCode code : {ErrorCode::UnknownOperation, ErrorCode::MissingPathParam,
                           ErrorCode::MissingQueryParam, ErrorCode::InvalidPathParam,
                           ErrorCode::ForbiddenBodyField, ErrorCode::DuplicateParameterAlias,
                           ErrorCode::InvalidIdempotencyKey, ErrorCode::MissingAccountToken,
                           ErrorCode::MissingIntrospectionSecret, ErrorCode::MissingCredential,
                           ErrorCode::InvalidOperationContract, ErrorCode::MissingBaseUrl,
                           ErrorCode::InvalidArgument}) {
        CHECK(!tempera::error_message(code).empty(), "an error code has no message");
    }

    Result<RequestSpec> unknown = client.build_request("palette", "does_not_exist");
    CHECK(!unknown.has_value() && unknown.error().code == ErrorCode::UnknownOperation,
          "unknown operation accepted");
    unknown = client.build_request("not_a_product", "health");
    CHECK(!unknown.has_value(), "unknown product accepted");
    CHECK_EQ(unknown.error().message(),
             std::string("unknown Tempera operation: not_a_product.health"));

    Result<RequestSpec> missing_path =
        client.build_request("palette", "get_trace", {{"tenant_id", "tenant_1"}});
    CHECK(!missing_path.has_value() && missing_path.error().code == ErrorCode::MissingPathParam,
          "missing path parameter accepted");
    CHECK(missing_path.error().message().find("missing required path parameter \"traceId\"") !=
              std::string::npos,
          "unhelpful detail: " + missing_path.error().message());
    missing_path =
        client.build_request("palette", "get_trace", {{"tenant_id", "t"}, {"trace_id", ""}});
    CHECK(!missing_path.has_value() && missing_path.error().code == ErrorCode::MissingPathParam,
          "empty path parameter accepted");

    Result<RequestSpec> missing_query = client.build_request(
        "tempera_payments", "get_payment_intent", {{"payment_intent_id", "pi_1"}});
    CHECK(!missing_query.has_value() && missing_query.error().code == ErrorCode::MissingQueryParam,
          "missing required query accepted");
    CHECK(missing_query.error().message().find("missing required query parameter") !=
              std::string::npos,
          "unhelpful detail: " + missing_query.error().message());

    Result<RequestSpec> no_account = bare.build_request("control_plane", "me");
    CHECK(!no_account.has_value() && no_account.error().code == ErrorCode::MissingAccountToken,
          "missing account token accepted");
    Result<RequestSpec> no_secret = bare.build_request("control_plane", "introspect_token");
    CHECK(!no_secret.has_value() &&
              no_secret.error().code == ErrorCode::MissingIntrospectionSecret,
          "missing introspection secret accepted");
    Result<RequestSpec> no_credential =
        bare.build_request("palette", "get_trace", {{"tenantId", "t"}, {"traceId", "tr"}});
    CHECK(!no_credential.has_value() &&
              no_credential.error().code == ErrorCode::MissingCredential,
          "missing credential accepted");
    CHECK_EQ(no_credential.error().name, std::string("palette"));

    Result<RequestSpec> not_binary = client.build_binary(
        "palette", "get_trace", {{"tenantId", "t"}, {"traceId", "tr"}}, {1, 2, 3});
    CHECK(!not_binary.has_value() &&
              not_binary.error().code == ErrorCode::InvalidOperationContract,
          "non-binary operation accepted a binary body");

    Result<RequestSpec> bad_key = client.build_request(
        "control_plane", "create_credit_topup",
        {{"packId", "pack_1"}, {"idempotencyKey", "not a graphic key"}});
    CHECK(!bad_key.has_value() && bad_key.error().code == ErrorCode::InvalidIdempotencyKey,
          "malformed idempotency key accepted");
    Result<RequestSpec> good_key = client.build_request(
        "control_plane", "create_credit_topup", {{"packId", "pack_1"}, {"idempotencyKey", "k-1"}});
    CHECK(good_key.has_value(), "well-formed idempotency key rejected");
}

// -------------------------------------------------------------------------
// 8. Base-URL precedence
// -------------------------------------------------------------------------

void test_base_url_precedence() {
    Client client;

    (void)::unsetenv("TEMPERA_TEMPO_URL");
    Result<RequestSpec> missing = client.build_request("tempo", "health");
    CHECK(!missing.has_value() && missing.error().code == ErrorCode::MissingBaseUrl,
          "missing base URL accepted");
    CHECK(missing.error().message().find("TEMPERA_TEMPO_URL") != std::string::npos,
          "detail omits the env var: " + missing.error().message());

    // The env var supplies the base URL when nothing is configured.
    (void)::setenv("TEMPERA_TEMPO_URL", "https://env.example.test", 1);
    Result<RequestSpec> from_env = client.build_request("tempo", "health");
    CHECK(from_env.has_value(), "env base URL rejected");
    CHECK_EQ(from_env.value().url, std::string("https://env.example.test/health"));

    // An explicit override wins over the env var.
    client.with_base_url("tempo", "https://override.example.test");
    Result<RequestSpec> overridden = client.build_request("tempo", "health");
    CHECK(overridden.has_value(), "override rejected");
    CHECK_EQ(overridden.value().url, std::string("https://override.example.test/health"));

    // An empty env var counts as unset.
    (void)::setenv("TEMPERA_TEMPO_URL", "", 1);
    Client empty_env;
    Result<RequestSpec> unset = empty_env.build_request("tempo", "health");
    CHECK(!unset.has_value() && unset.error().code == ErrorCode::MissingBaseUrl,
          "empty env var used as a base URL");
    (void)::unsetenv("TEMPERA_TEMPO_URL");

    // Trailing slashes are trimmed.
    client.with_base_url("tempo", "https://tempo.example.test///");
    Result<RequestSpec> trimmed = client.build_request("tempo", "health");
    CHECK(trimmed.has_value(), "trailing-slash base URL rejected");
    CHECK_EQ(trimmed.value().url, std::string("https://tempo.example.test/health"));
}

// -------------------------------------------------------------------------
// 9. Auth: PKCE, authorize URL, token bodies, rotation
// -------------------------------------------------------------------------

void test_auth_flows() {
    Auth auth("https://staging-api.tempera.dev/");
    CHECK_EQ(auth.issuer_url(), std::string_view("https://staging-api.tempera.dev"));

    // RFC 7636 appendix B reference vector.
    const std::string challenge =
        tempera::pkce_challenge_s256("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk");
    CHECK_EQ(challenge, std::string("E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"));
    CHECK(challenge.find('=') == std::string::npos, "PKCE challenge is padded");

    // RFC 4648 section 5 vectors, unpadded.
    const std::array<unsigned char, 6> foobar = {'f', 'o', 'o', 'b', 'a', 'r'};
    CHECK_EQ(tempera::base64url_no_pad(std::span(foobar).first(6)), std::string("Zm9vYmFy"));
    CHECK_EQ(tempera::base64url_no_pad(std::span(foobar).first(2)), std::string("Zm8"));
    const std::array<unsigned char, 3> high = {0xff, 0xfe, 0xfd};
    CHECK_EQ(tempera::base64url_no_pad(high), std::string("__79"));

    // PKCE from caller-supplied entropy: no RNG dependency.
    std::array<unsigned char, 32> entropy{};
    for (std::size_t index = 0; index < entropy.size(); ++index) {
        entropy[index] = static_cast<unsigned char>(index);
    }
    const tempera::PkcePair pair = tempera::pkce_pair_from_entropy(entropy);
    CHECK_EQ(pair.method, std::string_view("S256"));
    CHECK_EQ(pair.challenge, tempera::pkce_challenge_s256(pair.verifier));
    CHECK(pair.verifier.size() >= 43, "PKCE verifier shorter than RFC 7636 allows");

    auth.with_client_id("client_1");
    const std::string url = auth.authorize_url({.client_id = "client_1",
                                                .redirect_uri = "https://app.example.test/callback",
                                                .code_challenge = "challenge_1",
                                                .audience = "tempo",
                                                .scope = "trace:read trace:write",
                                                .state = "state_1"});
    CHECK(url.rfind("https://staging-api.tempera.dev/oauth/authorize?", 0) == 0,
          "authorize URL is wrong: " + url);
    CHECK(url.find("response_type=code") != std::string::npos, "no response_type: " + url);
    CHECK(url.find("resource=tempo") != std::string::npos, "no RFC 8707 resource: " + url);
    CHECK(url.find("code_challenge_method=S256") != std::string::npos, "no S256: " + url);
    CHECK(url.find("scope=trace%3Aread%20trace%3Awrite") != std::string::npos,
          "scope not form-encoded: " + url);
    CHECK(url.find("state=state_1") != std::string::npos, "no state: " + url);

    CHECK_EQ(auth.token_url(), std::string("https://staging-api.tempera.dev/oauth/token"));
    CHECK_EQ(auth.revoke_url(), std::string("https://staging-api.tempera.dev/oauth/revoke"));
    CHECK_EQ(auth.mcp_url(), std::string("https://staging-api.tempera.dev/mcp"));

    CHECK_EQ(auth.code_exchange_body("code_1", "verifier_1", "https://app.example.test/callback",
                                     "tempo"),
             std::string("grant_type=authorization_code&code=code_1&code_verifier=verifier_1&"
                         "redirect_uri=https%3A%2F%2Fapp.example.test%2Fcallback&resource=tempo&"
                         "client_id=client_1"));

    CHECK(!auth.refresh_body("tempo").has_value(), "refresh body without a token");
    auth.apply_token_response("tempo", "access_1", "refresh_1", 3600U, "trace:read");
    CHECK_EQ(auth.bearer_for("tempo").value_or(""), std::string_view("access_1"));
    CHECK_EQ(auth.refresh_body("tempo").value_or(""),
             std::string("grant_type=refresh_token&refresh_token=refresh_1&resource=tempo&"
                         "client_id=client_1"));

    // Rotation: a new refresh token replaces the old one.
    auth.apply_token_response("tempo", "access_2", "refresh_2");
    CHECK(auth.refresh_body("tempo")->find("refresh_token=refresh_2") != std::string::npos,
          "rotation kept the old token");

    // An omitted refresh token keeps the stored one.
    auth.apply_token_response("tempo", "access_3");
    CHECK_EQ(auth.bearer_for("tempo").value_or(""), std::string_view("access_3"));
    CHECK(auth.refresh_body("tempo")->find("refresh_token=refresh_2") != std::string::npos,
          "rotation dropped the token");

    // The API key is the fallback bearer for every other audience.
    CHECK(!auth.bearer_for("palette").has_value(), "unset API key resolved a bearer");
    auth.with_api_key("tp_key_1");
    CHECK_EQ(auth.bearer_for("palette").value_or(""), std::string_view("tp_key_1"));
    CHECK_EQ(auth.bearer_for("tempo").value_or(""), std::string_view("access_3"));
    CHECK_EQ(auth.authorization_header("palette").value_or(""), std::string("Bearer tp_key_1"));

    // Revoking returns the body and drops the stored token set.
    CHECK_EQ(auth.revoke_body("tempo").value_or(""),
             std::string("token=refresh_2&token_type_hint=refresh_token&client_id=client_1"));
    CHECK_EQ(auth.bearer_for("tempo").value_or(""), std::string_view("tp_key_1"));
    CHECK(!auth.revoke_body("tempo").has_value(), "revoke twice produced a body");
}

// An audience token is preferred over the unified API key.
void test_audience_token_precedence() {
    Auth auth("https://staging-api.tempera.dev");
    auth.with_api_key("tp_key_1");
    auth.apply_token_response("palette", "palette_access");
    const Client client = full_client(auth);
    Result<RequestSpec> request =
        client.build_request("palette", "get_trace", {{"tenantId", "t"}, {"traceId", "tr"}});
    CHECK(request.has_value(), "audience token build failed");
    CHECK_EQ(header_or_empty(request.value(), "authorization"),
             std::string("Bearer palette_access"));
}

// -------------------------------------------------------------------------
// 10. MCP JSON-RPC bodies
// -------------------------------------------------------------------------

void test_mcp() {
    tempera::McpRequestBuilder builder;

    auto [initialize_id, initialize] =
        builder.initialize_body("tempera-sdk", tempera::SDK_VERSION);
    CHECK(initialize_id == 1, "first request id is not 1");
    CHECK_EQ(initialize,
             std::string("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":"
                         "{\"protocolVersion\":\"2025-06-18\",\"capabilities\":{},\"clientInfo\":"
                         "{\"name\":\"tempera-sdk\",\"version\":\"0.12.0\"}}}"));

    auto [ping_id, ping] = builder.ping_body();
    CHECK(ping_id == 2, "ids do not increment");
    CHECK_EQ(ping, std::string("{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"ping\"}"));
    CHECK(ping.find("params") == std::string::npos, "ping carries params");

    auto [list_id, list] = builder.list_tools_body();
    CHECK(list_id == 3, "ids do not increment");
    CHECK_EQ(list, std::string("{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/list\"}"));

    auto [call_id, call] = builder.call_tool_body("tempera_search", R"({"query":"traces"})");
    CHECK(call_id == 4, "ids do not increment");
    CHECK_EQ(call, std::string("{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\""
                               ":{\"name\":\"tempera_search\",\"arguments\":{\"query\":\"traces\""
                               "}}}"));

    auto [whoami_id, whoami] = builder.whoami_body();
    CHECK(whoami_id == 5, "ids do not increment");
    CHECK_EQ(whoami, std::string("{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"tools/call\",\"param"
                                 "s\":{\"name\":\"tempera_whoami\",\"arguments\":{}}}"));

    auto [status_id, status] = builder.status_body();
    (void)status_id;
    CHECK(status.find("tempera_status") != std::string::npos, "status body is wrong: " + status);

    auto [escaped_id, escaped] = builder.call_tool_body("weird\"name");
    (void)escaped_id;
    CHECK(escaped.find(R"("name":"weird\"name")") != std::string::npos,
          "tool name not escaped: " + escaped);

    CHECK(!tempera::parse_mcp_error(R"({"jsonrpc":"2.0","id":1,"result":{}})").has_value(),
          "success response parsed as an error");
    CHECK(!tempera::parse_mcp_error("not json").has_value(),
          "unparseable body parsed as an error");
    CHECK(!tempera::parse_mcp_error(R"({"error":null})").has_value(),
          "null error parsed as an error");

    std::optional<tempera::McpError> error = tempera::parse_mcp_error(
        R"({"jsonrpc":"2.0","id":1,"error":{"code":-32002,"message":"plan limit","data":{}}})");
    CHECK(error.has_value(), "JSON-RPC error not parsed");
    CHECK(error->code == tempera::surface::MCP_ERROR_PLAN_LIMIT, "wrong MCP error code");
    CHECK_EQ(error->message, std::string("plan limit"));

    error = tempera::parse_mcp_error(R"({"error":{"code":-32601}})");
    CHECK(error.has_value() && error->code == tempera::surface::MCP_ERROR_METHOD_NOT_FOUND,
          "wrong code for a message-less error");
    CHECK_EQ(error->message, std::string("MCP error"));

    error = tempera::parse_mcp_error(R"({"error":"boom"})");
    CHECK(error.has_value() && error->code == 0, "non-conformant error got a code");
    CHECK_EQ(error->message, std::string("boom"));
}

// -------------------------------------------------------------------------
// 11. Binary uploads, full URLs, and body escaping
// -------------------------------------------------------------------------

void test_binary_and_serialization(const Client &client) {
    Result<RequestSpec> upload = client.build_binary(
        "tempera_document", "uploads_write",
        {{"project_id", "project_1"}, {"upload_id", "upload_1"}}, {1, 2, 3});
    CHECK(upload.has_value(), "binary upload failed");
    CHECK(!upload.value().body_json.has_value(), "binary upload carries a JSON body");
    CHECK(upload.value().body_bytes.has_value() && upload.value().body_bytes->size() == 3 &&
              (*upload.value().body_bytes)[2] == 3,
          "binary payload not carried");
    CHECK_EQ(header_or_empty(upload.value(), "content-type"),
             std::string("application/octet-stream"));
    CHECK_EQ(header_or_empty(upload.value(), "authorization"), std::string("Bearer tp_key_1"));

    // full_url appends the urlencoded query string.
    Result<RequestSpec> read = client.build_request(
        "palette", "get_trace",
        {{"tenantId", "tenant_1"}, {"traceId", "trace_1"}, {"reason", "audit review"}});
    CHECK(read.has_value(), "get_trace failed");
    CHECK_EQ(read.value().full_url(),
             std::string(
                 "https://palette.example.test/v1/traces/tenant_1/trace_1?reason=audit%20review"));

    // Body strings are JSON-escaped.
    Result<RequestSpec> escaped =
        client.build_request("control_plane", "create_hosted_session",
                             {{"mode", "login"},
                              {"email", "dev\"quote\\slash@example.test"},
                              {"password", "line\nbreak\ttab"}});
    CHECK(escaped.has_value(), "create_hosted_session failed");
    const std::string &body = *escaped.value().body_json;
    CHECK(body.find(R"("email":"dev\"quote\\slash@example.test")") != std::string::npos,
          "quotes/backslashes not escaped: " + body);
    CHECK(body.find(R"("password":"line\nbreak\ttab")") != std::string::npos,
          "controls not escaped: " + body);
    CHECK(body.front() == '{' && body.back() == '}', "body is not an object: " + body);

    // A declared member is serialized once, whichever spelling arrives.
    Result<RequestSpec> once = client.build_request(
        "control_plane", "create_hosted_session",
        {{"email", "dev@example.test"}, {"mode", "signup"}});
    CHECK(once.has_value(), "create_hosted_session failed");
    const std::string &once_body = *once.value().body_json;
    CHECK(once_body.find("\"mode\":") == once_body.rfind("\"mode\":"),
          "mode serialized twice: " + once_body);
    CHECK(once_body.find(R"("mode":"signup")") != std::string::npos, "wrong mode: " + once_body);

    // Raw JSON is spliced verbatim.
    Result<RequestSpec> raw = client.build_request(
        "control_plane", "create_hosted_session",
        {{"metadata", ParamValue::raw_json(R"({"a":[1,2]})")}, {"mode", "login"}});
    CHECK(raw.has_value(), "raw JSON parameter failed");
    CHECK(raw.value().body_json->find(R"("metadata":{"a":[1,2]})") != std::string::npos,
          "raw JSON not spliced: " + *raw.value().body_json);
}

// -------------------------------------------------------------------------
// 12. The generated tables themselves
// -------------------------------------------------------------------------

void test_surface_tables() {
    static_assert(tempera::surface::SURFACE_VERSION > 0);
    static_assert(tempera::surface::find_product("palette") != nullptr);
    static_assert(tempera::surface::find_product("nope") == nullptr);
    static_assert(tempera::surface::find_operation("palette", "get_trace") != nullptr);
    static_assert(tempera::surface::find_operation("palette", "nope") == nullptr);
    static_assert(tempera::surface::MCP_ERROR_PLAN_LIMIT == -32002);

    CHECK(tempera::surface::PRODUCTS.size() >= 14, "product table is short");
    CHECK(tempera::surface::ENVIRONMENTS.size() >= 4, "environment table is short");
    CHECK(!tempera::surface::MCP_METHODS.empty(), "MCP method table is empty");
    CHECK_EQ(tempera::surface::INTROSPECT_PATH, std::string_view("/v1/oauth/introspect"));
    CHECK_EQ(tempera::surface::MCP_PATH, std::string_view("/mcp"));

    bool found_default_audience = false;
    for (std::string_view audience : tempera::surface::AUDIENCES) {
        if (audience == tempera::surface::DEFAULT_AUDIENCE) {
            found_default_audience = true;
        }
    }
    CHECK(found_default_audience, "the default audience is not registered");
    CHECK(tempera::surface::find_product("temp_os") != nullptr, "temp_os is missing");
    CHECK_EQ(tempera::surface::find_product("palette")->audience.value_or(""),
             std::string_view("palette"));

    for (const tempera::surface::OperationSpec &op : tempera::surface::OPERATIONS) {
        const std::string label = std::string(op.product) + "." + std::string(op.id);
        CHECK(tempera::surface::find_product(op.product) != nullptr,
              label + ": unregistered product");
        CHECK(op.auth == "none" || op.auth == "account" || op.auth == "product" ||
                  op.auth == "oauthResource" || op.auth == "introspectionSecret",
              label + ": unknown auth kind");
        CHECK(op.auth != "oauthResource" || op.auth_audience.has_value(),
              label + ": oauthResource without an audience");
    }
}

}  // namespace

int main() {
    const Auth auth = test_auth();
    const Client client = full_client(auth);

    test_surface_tables();
    test_every_operation_builds(client);
    test_alias_handling(client);
    test_forbidden_body(client);
    test_aip_path_patterns(client);
    test_forward_compatible_spill(client);
    test_error_normalization();
    test_error_enum(auth);
    test_base_url_precedence();
    test_auth_flows();
    test_audience_token_precedence();
    test_mcp();
    test_binary_and_serialization(client);

    (void)std::printf("%d checks, %d failures\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
