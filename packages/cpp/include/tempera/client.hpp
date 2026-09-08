// The unified Tempera client, HTTP-less: it resolves an operation from the
// generated surface tables (tempera/surface.hpp) and builds a fully-described
// RequestSpec (method, URL, query, headers, JSON body) for the caller's own
// HTTP client to send.
//
// Mirrors the Rust TemperaClient dispatch semantics exactly:
//  - Typed operations by product key + snake_case operation id. Parameters
//    accept canonical wire names and snake_case aliases; requests always emit
//    the producer's canonical wire names.
//  - Declared query keys route to the query string; declared body keys plus
//    body defaults form the JSON body.
//  - Forward compatibility: undeclared parameters flow to the query string on
//    GET/DELETE and into the JSON body otherwise, so a new server field is
//    usable before the surface tables catch up.
//  - Auth kinds: none, account, introspectionSecret, oauthResource (an
//    operation-pinned audience) and product (the product's audience through
//    Auth, with unified tp_ API-key fallback).

#ifndef TEMPERA_CLIENT_HPP
#define TEMPERA_CLIENT_HPP

#include <cstdint>
#include <cstdlib>
#include <optional>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <variant>
#include <vector>

#include "tempera/auth.hpp"
#include "tempera/error.hpp"
#include "tempera/surface.hpp"

namespace tempera {

/// Maximum wire length of an idempotency key, in bytes.
inline constexpr std::size_t MAX_IDEMPOTENCY_KEY_BYTES = 256;

/// Request-body field names that carry a client-minted idempotency key.
inline constexpr std::array<std::string_view, 2> IDEMPOTENCY_KEY_FIELDS = {"idempotencyKey",
                                                                          "idempotency_key"};

/// One request parameter value, carrying enough type information to serialize
/// into either the query string or a JSON body member.
class ParamValue {
public:
    ParamValue(std::string value) : value_(std::move(value)) {}      // NOLINT(*-explicit-*)
    ParamValue(const char *value) : value_(std::string(value)) {}    // NOLINT(*-explicit-*)
    ParamValue(std::string_view value) : value_(std::string(value)) {}  // NOLINT(*-explicit-*)
    ParamValue(bool value) : value_(value) {}                        // NOLINT(*-explicit-*)

    template <class T, std::enable_if_t<std::is_integral_v<T> && !std::is_same_v<T, bool>, int> = 0>
    ParamValue(T value) : value_(static_cast<std::int64_t>(value)) {}  // NOLINT(*-explicit-*)

    /// A pre-serialized JSON fragment, spliced verbatim into the body (use for
    /// objects, arrays, floats, or nulls).
    static ParamValue raw_json(std::string fragment) {
        ParamValue param{std::string()};
        param.value_ = RawJson{std::move(fragment)};
        return param;
    }

    /// Plain-text form, used for path substitution and query-string values.
    [[nodiscard]] std::string plain_string() const {
        if (const auto *text = std::get_if<std::string>(&value_)) {
            return *text;
        }
        if (const auto *number = std::get_if<std::int64_t>(&value_)) {
            return std::to_string(*number);
        }
        if (const auto *boolean = std::get_if<bool>(&value_)) {
            return *boolean ? "true" : "false";
        }
        return std::get<RawJson>(value_).text;
    }

    /// JSON form, used for body members.
    [[nodiscard]] std::string json_fragment() const {
        if (const auto *text = std::get_if<std::string>(&value_)) {
            return "\"" + json_escape(*text) + "\"";
        }
        if (const auto *number = std::get_if<std::int64_t>(&value_)) {
            return std::to_string(*number);
        }
        if (const auto *boolean = std::get_if<bool>(&value_)) {
            return *boolean ? "true" : "false";
        }
        return std::get<RawJson>(value_).text;
    }

    [[nodiscard]] bool is_string() const noexcept {
        return std::holds_alternative<std::string>(value_);
    }

private:
    struct RawJson {
        std::string text;
    };

    std::variant<std::string, std::int64_t, bool, RawJson> value_;
};

/// Parameters for one operation: canonical wire names or snake_case aliases.
using Params = std::vector<std::pair<std::string, ParamValue>>;

/// A fully-described HTTP request for the caller's HTTP client to send.
struct RequestSpec {
    /// HTTP method, borrowed from the generated operation table.
    std::string_view method;
    /// Base URL plus the substituted path, WITHOUT the query string.
    std::string url;
    /// Query parameters as unencoded key/value pairs.
    std::vector<std::pair<std::string, std::string>> query;
    /// accept, content-type (when a body is present), authorization.
    std::vector<std::pair<std::string, std::string>> headers;
    /// Serialized JSON body, when the operation carries one.
    std::optional<std::string> body_json;
    /// Raw binary body for upload operations.
    std::optional<std::vector<unsigned char>> body_bytes;

    /// The complete URL: url plus the urlencoded query string.
    [[nodiscard]] std::string full_url() const {
        if (query.empty()) {
            return url;
        }
        std::string encoded;
        for (const auto &[name, value] : query) {
            if (!encoded.empty()) {
                encoded += '&';
            }
            encoded += url_encode(name);
            encoded += '=';
            encoded += url_encode(value);
        }
        return url + "?" + encoded;
    }

    [[nodiscard]] const std::string *header(std::string_view name) const noexcept {
        for (const auto &entry : headers) {
            if (entry.first == name) {
                return &entry.second;
            }
        }
        return nullptr;
    }

    [[nodiscard]] const std::string *query_value(std::string_view name) const noexcept {
        for (const auto &entry : query) {
            if (entry.first == name) {
                return &entry.second;
            }
        }
        return nullptr;
    }
};

/// Every way a request can fail before it exists. These mirror the Rust
/// BuildError variants one-for-one.
enum class ErrorCode {
    /// No operation with this product key and operation id exists.
    UnknownOperation,
    /// A {placeholder} in the operation path had no matching parameter.
    MissingPathParam,
    /// A producer-required query parameter was absent or empty.
    MissingQueryParam,
    /// A path parameter did not match its declared AIP resource pattern.
    InvalidPathParam,
    /// A field the producer derives from the principal was supplied.
    ForbiddenBodyField,
    /// Both a canonical wire name and its snake_case alias were supplied.
    DuplicateParameterAlias,
    /// An idempotency key was not exact ASCII-graphic bytes within bounds.
    InvalidIdempotencyKey,
    /// The operation needs an account-session token and none is configured.
    MissingAccountToken,
    /// The operation needs the introspection secret and none is configured.
    MissingIntrospectionSecret,
    /// No credential resolves for the operation's token audience.
    MissingCredential,
    /// A generated operation is missing required static contract metadata.
    InvalidOperationContract,
    /// No base URL is configured for the product and its env var is unset.
    MissingBaseUrl,
    /// A required argument was empty or otherwise unusable.
    InvalidArgument
};

/// Stable one-line description of an error code.
inline constexpr std::string_view error_message(ErrorCode code) noexcept {
    switch (code) {
    case ErrorCode::UnknownOperation:
        return "unknown Tempera operation";
    case ErrorCode::MissingPathParam:
        return "missing required path parameter";
    case ErrorCode::MissingQueryParam:
        return "missing required query parameter";
    case ErrorCode::InvalidPathParam:
        return "path parameter does not match its AIP resource pattern";
    case ErrorCode::ForbiddenBodyField:
        return "parameter is derived from the authenticated principal";
    case ErrorCode::DuplicateParameterAlias:
        return "pass either the wire name or its snake_case alias, not both";
    case ErrorCode::InvalidIdempotencyKey:
        return "idempotency key must be 1-256 ASCII-graphic bytes";
    case ErrorCode::MissingAccountToken:
        return "an account token is required";
    case ErrorCode::MissingIntrospectionSecret:
        return "the introspection secret is required";
    case ErrorCode::MissingCredential:
        return "no credential for the operation's token audience";
    case ErrorCode::InvalidOperationContract:
        return "generated operation contract is invalid for this call";
    case ErrorCode::MissingBaseUrl:
        return "missing base URL for the product";
    case ErrorCode::InvalidArgument:
        return "invalid argument";
    }
    return "unknown Tempera status";
}

/// A configuration or usage mistake, caught before any request is sent.
struct BuildError {
    ErrorCode code = ErrorCode::InvalidArgument;
    std::string product;
    std::string operation;
    /// Parameter, audience, env var, or AIP pattern this failure is about.
    std::string name;
    /// Self-contained human-readable message.
    std::string detail;

    [[nodiscard]] const std::string &message() const noexcept { return detail; }
};

/// The result of a build: either the request or the error that prevented it.
template <class T>
class Result {
public:
    Result(T value) : value_(std::move(value)) {}          // NOLINT(*-explicit-*)
    Result(BuildError error) : value_(std::move(error)) {}  // NOLINT(*-explicit-*)

    [[nodiscard]] bool has_value() const noexcept { return std::holds_alternative<T>(value_); }
    explicit operator bool() const noexcept { return has_value(); }

    [[nodiscard]] const T &value() const { return std::get<T>(value_); }
    [[nodiscard]] T &value() { return std::get<T>(value_); }
    [[nodiscard]] const BuildError &error() const { return std::get<BuildError>(value_); }

private:
    std::variant<T, BuildError> value_;
};

namespace detail {

inline std::string snake_case(std::string_view value) {
    std::string out;
    out.reserve(value.size() + 4);
    for (std::size_t index = 0; index < value.size(); ++index) {
        const char character = value[index];
        if (character >= 'A' && character <= 'Z') {
            if (index > 0) {
                out += '_';
            }
            out += static_cast<char>(character - 'A' + 'a');
        } else {
            out += character;
        }
    }
    return out;
}

inline bool contains(std::span<const std::string_view> values, std::string_view needle) noexcept {
    for (std::string_view value : values) {
        if (value == needle) {
            return true;
        }
    }
    return false;
}

/// Validate one path parameter against its declared AIP resource pattern and
/// percent-encode only the wildcard segments, so the pattern's structural
/// slashes survive. Rejects empty, "." and ".." segments.
inline std::optional<std::string> expand_aip_path_param(std::string_view value,
                                                        std::string_view pattern) {
    std::vector<std::string_view> expected;
    std::vector<std::string_view> observed;
    for (std::size_t start = 0;;) {
        const std::size_t hit = pattern.find('/', start);
        expected.push_back(pattern.substr(start, hit - start));
        if (hit == std::string_view::npos) {
            break;
        }
        start = hit + 1;
    }
    for (std::size_t start = 0;;) {
        const std::size_t hit = value.find('/', start);
        observed.push_back(value.substr(start, hit - start));
        if (hit == std::string_view::npos) {
            break;
        }
        start = hit + 1;
    }
    if (expected.size() != observed.size()) {
        return std::nullopt;
    }
    std::string out;
    for (std::size_t index = 0; index < expected.size(); ++index) {
        if (index > 0) {
            out += '/';
        }
        if (expected[index] == "*") {
            if (observed[index].empty() || observed[index] == "." || observed[index] == "..") {
                return std::nullopt;
            }
            out += url_encode(observed[index]);
        } else if (expected[index] == observed[index]) {
            out += expected[index];
        } else {
            return std::nullopt;
        }
    }
    return out;
}

inline std::string substitute_path(std::string_view path, std::string_view name,
                                   std::string_view replacement) {
    const std::string needle = "{" + std::string(name) + "}";
    std::string out;
    std::size_t cursor = 0;
    while (true) {
        const std::size_t hit = path.find(needle, cursor);
        if (hit == std::string_view::npos) {
            out += path.substr(cursor);
            return out;
        }
        out += path.substr(cursor, hit - cursor);
        out += replacement;
        cursor = hit + needle.size();
    }
}

/// The canonical tempera-mcp rule: exact ASCII-graphic bytes, 1..=256 of them.
inline bool valid_idempotency_key(const ParamValue &value) {
    if (!value.is_string()) {
        return false;
    }
    const std::string key = value.plain_string();
    if (key.empty() || key.size() > MAX_IDEMPOTENCY_KEY_BYTES) {
        return false;
    }
    for (unsigned char byte : key) {
        if (byte <= 0x20 || byte >= 0x7f) {
            return false;
        }
    }
    return true;
}

inline void set_body_member(std::vector<std::pair<std::string, std::string>> &members,
                            std::string_view key, std::string value) {
    for (auto &member : members) {
        if (member.first == key) {
            member.second = std::move(value);
            return;
        }
    }
    members.emplace_back(std::string(key), std::move(value));
}

}  // namespace detail

/// The unified Tempera client: one credential set, every product, no HTTP.
class Client {
public:
    Client() = default;

    /// Attach the unified credential used by product and oauthResource
    /// operations. The client keeps its own copy.
    Client &with_auth(Auth auth) {
        auth_ = std::move(auth);
        return *this;
    }

    /// Attach an account-session token for control-plane endpoints.
    Client &with_account_token(std::string token) {
        account_token_ = std::move(token);
        return *this;
    }

    /// Attach the introspection secret for introspect_token.
    Client &with_introspection_secret(std::string secret) {
        introspection_secret_ = std::move(secret);
        return *this;
    }

    /// Set the base URL for one product, overriding its env var.
    Client &with_base_url(std::string product, std::string url) {
        for (auto &entry : base_urls_) {
            if (entry.first == product) {
                entry.second = std::move(url);
                return *this;
            }
        }
        base_urls_.emplace_back(std::move(product), std::move(url));
        return *this;
    }

    /// Build the RequestSpec for one typed operation.
    ///
    /// `product` is a snake_case product key and `operation` a snake_case
    /// operation id from the surface tables (for example "palette",
    /// "get_trace"). Parameters accept canonical wire names or snake_case
    /// aliases. Path parameters substitute into the URL (percent-encoded),
    /// declared query keys go to the query string, declared body keys plus the
    /// operation's body defaults form the JSON body, and undeclared extras go
    /// to the query on GET/DELETE and to the body otherwise. Emitted names are
    /// always canonical producer wire names.
    [[nodiscard]] Result<RequestSpec> build_request(std::string_view product,
                                                    std::string_view operation,
                                                    const Params &params = {}) const {
        const surface::OperationSpec *op = surface::find_operation(product, operation);
        const surface::ProductSpec *product_spec = surface::find_product(product);
        if (op == nullptr || product_spec == nullptr) {
            return BuildError{ErrorCode::UnknownOperation, std::string(product),
                              std::string(operation), std::string(),
                              "unknown Tempera operation: " + std::string(product) + "." +
                                  std::string(operation)};
        }
        return build_request(*op, *product_spec, params);
    }

    /// Build a request from an already-resolved operation and product spec,
    /// skipping the table lookup. Identical in every other respect; this is
    /// also the seam the test suite uses to exercise contract rules (such as
    /// forbiddenBody) that no shipped operation exercises yet.
    [[nodiscard]] Result<RequestSpec> build_request(const surface::OperationSpec &op,
                                                    const surface::ProductSpec &product_spec,
                                                    const Params &params = {}) const {
        const std::string product(product_spec.key);
        const std::string operation(op.id);
        const std::string label = product + "." + operation;
        std::vector<bool> consumed(params.size(), false);

        // Fields the producer derives from the authenticated principal.
        for (std::string_view name : op.forbidden_body) {
            const Result<std::optional<std::size_t>> found =
                declared_param(params, name, product, operation);
            if (!found.has_value()) {
                return found.error();
            }
            if (found.value().has_value()) {
                return BuildError{ErrorCode::ForbiddenBodyField, product, operation,
                                  std::string(name),
                                  label + ": " + std::string(name) +
                                      " is derived from the authenticated principal"};
            }
        }

        // Path substitution. Ordinary values are percent-encoded. A producer
        // may declare an AIP resource pattern; its structural slashes are
        // preserved only after exact template validation.
        std::string path(op.path);
        for (std::string_view name : op.path_params) {
            const Result<std::optional<std::size_t>> found =
                declared_param(params, name, product, operation);
            if (!found.has_value()) {
                return found.error();
            }
            const std::string value = found.value().has_value()
                                          ? params[*found.value()].second.plain_string()
                                          : std::string();
            if (!found.value().has_value() || value.empty()) {
                return BuildError{ErrorCode::MissingPathParam, product, operation,
                                  std::string(name),
                                  label + ": missing required path parameter \"" +
                                      std::string(name) + "\""};
            }
            consumed[*found.value()] = true;
            std::optional<std::string_view> pattern;
            for (const surface::StrPair &entry : op.path_param_templates) {
                if (entry.key == name) {
                    pattern = entry.value;
                    break;
                }
            }
            std::string replacement;
            if (pattern.has_value()) {
                const std::optional<std::string> expanded =
                    detail::expand_aip_path_param(value, *pattern);
                if (!expanded.has_value()) {
                    return BuildError{ErrorCode::InvalidPathParam, product, operation,
                                      std::string(name),
                                      label + ": path parameter \"" + std::string(name) +
                                          "\" must match AIP resource pattern \"" +
                                          std::string(*pattern) + "\""};
                }
                replacement = *expanded;
            } else {
                replacement = url_encode(value);
            }
            path = detail::substitute_path(path, name, replacement);
        }

        // Declared query keys.
        std::vector<std::pair<std::string, std::string>> query;
        for (std::string_view key : op.query) {
            const bool required = detail::contains(op.required_query, key);
            const Result<std::optional<std::size_t>> found =
                declared_param(params, key, product, operation);
            if (!found.has_value()) {
                return found.error();
            }
            if (!found.value().has_value()) {
                if (required) {
                    return BuildError{ErrorCode::MissingQueryParam, product, operation,
                                      std::string(key),
                                      label + ": missing required query parameter \"" +
                                          std::string(key) + "\""};
                }
                continue;
            }
            const std::string value = params[*found.value()].second.plain_string();
            consumed[*found.value()] = true;
            if (value.empty() && required) {
                return BuildError{ErrorCode::MissingQueryParam, product, operation,
                                  std::string(key),
                                  label + ": missing required query parameter \"" +
                                      std::string(key) + "\""};
            }
            query.emplace_back(std::string(key), value);
        }

        // Declared body keys plus body defaults (defaults are JSON strings).
        std::optional<std::vector<std::pair<std::string, std::string>>> body;
        if (!op.body.empty() || !op.body_defaults.empty()) {
            std::vector<std::pair<std::string, std::string>> members;
            for (const surface::StrPair &entry : op.body_defaults) {
                members.emplace_back(std::string(entry.key),
                                     "\"" + json_escape(entry.value) + "\"");
            }
            for (std::string_view key : op.body) {
                const Result<std::optional<std::size_t>> found =
                    declared_param(params, key, product, operation);
                if (!found.has_value()) {
                    return found.error();
                }
                if (!found.value().has_value()) {
                    continue;
                }
                const ParamValue &value = params[*found.value()].second;
                if (detail::contains(IDEMPOTENCY_KEY_FIELDS, key) &&
                    !detail::valid_idempotency_key(value)) {
                    return BuildError{ErrorCode::InvalidIdempotencyKey, product, operation,
                                      std::string(key),
                                      label + ": " + std::string(key) + " must be 1-" +
                                          std::to_string(MAX_IDEMPOTENCY_KEY_BYTES) +
                                          " ASCII-graphic bytes"};
                }
                detail::set_body_member(members, key, value.json_fragment());
                consumed[*found.value()] = true;
            }
            body = std::move(members);
        }

        // Forward compatibility: undeclared parameters flow to the query
        // string on GET/DELETE and into the JSON body otherwise.
        for (std::size_t index = 0; index < params.size(); ++index) {
            if (consumed[index]) {
                continue;
            }
            const auto &[key, value] = params[index];
            if (op.method == "GET" || op.method == "DELETE") {
                query.emplace_back(key, value.plain_string());
            } else {
                if (detail::contains(IDEMPOTENCY_KEY_FIELDS, key) &&
                    !detail::valid_idempotency_key(value)) {
                    return BuildError{ErrorCode::InvalidIdempotencyKey, product, operation, key,
                                      label + ": " + key + " must be 1-" +
                                          std::to_string(MAX_IDEMPOTENCY_KEY_BYTES) +
                                          " ASCII-graphic bytes"};
                }
                if (!body.has_value()) {
                    body = std::vector<std::pair<std::string, std::string>>();
                }
                detail::set_body_member(*body, key, value.json_fragment());
            }
        }

        // Bearer per the operation's auth kind.
        std::optional<std::string> bearer;
        if (op.auth == "none") {
            // No credential is presented.
        } else if (op.auth == "account") {
            if (!account_token_.has_value()) {
                return BuildError{ErrorCode::MissingAccountToken, product, operation, std::string(),
                                  product +
                                      ": an account token is required; call "
                                      "create_hosted_session first or pass "
                                      "with_account_token(...)"};
            }
            bearer = *account_token_;
        } else if (op.auth == "introspectionSecret") {
            if (!introspection_secret_.has_value()) {
                return BuildError{ErrorCode::MissingIntrospectionSecret, product, operation,
                                  std::string(),
                                  product +
                                      ": introspect_token requires the introspection secret; "
                                      "pass with_introspection_secret(...)"};
            }
            bearer = *introspection_secret_;
        } else {
            std::string audience;
            if (op.auth == "oauthResource") {
                if (!op.auth_audience.has_value()) {
                    return BuildError{ErrorCode::InvalidOperationContract, product, operation,
                                      std::string(),
                                      label + ": generated operation auth contract is invalid"};
                }
                audience = std::string(*op.auth_audience);
            } else {
                // "product": the product's audience, or the default audience.
                audience = std::string(product_spec.audience.value_or(surface::DEFAULT_AUDIENCE));
            }
            std::optional<std::string_view> resolved;
            if (auth_.has_value()) {
                resolved = auth_->bearer_for(audience);
            }
            if (!resolved.has_value()) {
                return BuildError{ErrorCode::MissingCredential, product, operation, audience,
                                  product + ": no credential for audience " + audience +
                                      "; pass an Auth with credentials permitted by this "
                                      "operation"};
            }
            bearer = std::string(*resolved);
        }

        // Base URL: explicit override, then the product's env var.
        std::optional<std::string> base_url;
        for (const auto &entry : base_urls_) {
            if (entry.first == product) {
                base_url = entry.second;
                break;
            }
        }
        if (!base_url.has_value()) {
            const std::string env_var(product_spec.env_var);
            if (const char *from_env = std::getenv(env_var.c_str());
                from_env != nullptr && from_env[0] != '\0') {
                base_url = std::string(from_env);
            }
        }
        if (!base_url.has_value()) {
            return BuildError{ErrorCode::MissingBaseUrl, product, operation,
                              std::string(product_spec.env_var),
                              "missing base URL for " + product + "; set " +
                                  std::string(product_spec.env_var) + " or pass with_base_url(\"" +
                                  product + "\", ...)"};
        }
        while (!base_url->empty() && base_url->back() == '/') {
            base_url->pop_back();
        }

        RequestSpec request;
        request.method = op.method;
        request.url = *base_url + path;
        request.query = std::move(query);
        if (body.has_value()) {
            std::string serialized = "{";
            for (std::size_t index = 0; index < body->size(); ++index) {
                if (index > 0) {
                    serialized += ',';
                }
                serialized += "\"" + json_escape((*body)[index].first) + "\":";
                serialized += (*body)[index].second;
            }
            serialized += "}";
            request.body_json = std::move(serialized);
        }
        request.headers.emplace_back("accept", "application/json");
        if (request.body_json.has_value()) {
            request.headers.emplace_back("content-type", "application/json");
        }
        if (bearer.has_value()) {
            request.headers.emplace_back("authorization", "Bearer " + *bearer);
        }
        return request;
    }

    /// Build a request for a producer-declared binary upload operation.
    [[nodiscard]] Result<RequestSpec> build_binary(std::string_view product,
                                                   std::string_view operation,
                                                   const Params &params,
                                                   std::vector<unsigned char> content) const {
        const surface::OperationSpec *op = surface::find_operation(product, operation);
        if (op == nullptr) {
            return BuildError{ErrorCode::UnknownOperation, std::string(product),
                              std::string(operation), std::string(),
                              "unknown Tempera operation: " + std::string(product) + "." +
                                  std::string(operation)};
        }
        if (op->request_body_kind != "binary") {
            return BuildError{ErrorCode::InvalidOperationContract, std::string(product),
                              std::string(operation), std::string(),
                              std::string(product) + "." + std::string(operation) +
                                  ": operation does not declare a binary request body"};
        }
        Result<RequestSpec> built = build_request(product, operation, params);
        if (!built.has_value()) {
            return built;
        }
        RequestSpec request = built.value();
        request.body_bytes = std::move(content);
        if (op->request_content_type.has_value()) {
            request.headers.emplace_back("content-type", std::string(*op->request_content_type));
        }
        return request;
    }

private:
    /// Find the parameter a declared wire name refers to: the canonical name,
    /// or its snake_case alias. Supplying both is an error.
    [[nodiscard]] static Result<std::optional<std::size_t>> declared_param(
        const Params &params, std::string_view wire_name, const std::string &product,
        const std::string &operation) {
        std::optional<std::size_t> wire_index;
        std::optional<std::size_t> alias_index;
        for (std::size_t index = 0; index < params.size(); ++index) {
            if (params[index].first == wire_name) {
                wire_index = index;
                break;
            }
        }
        const std::string alias = detail::snake_case(wire_name);
        if (alias == wire_name) {
            return wire_index;
        }
        for (std::size_t index = 0; index < params.size(); ++index) {
            if (params[index].first == alias) {
                alias_index = index;
                break;
            }
        }
        if (wire_index.has_value() && alias_index.has_value()) {
            return BuildError{ErrorCode::DuplicateParameterAlias, product, operation,
                              std::string(wire_name),
                              product + "." + operation + ": pass either \"" +
                                  std::string(wire_name) + "\" or its snake_case alias \"" +
                                  alias + "\", not both"};
        }
        return wire_index.has_value() ? wire_index : alias_index;
    }

    std::optional<Auth> auth_;
    std::optional<std::string> account_token_;
    std::optional<std::string> introspection_secret_;
    std::vector<std::pair<std::string, std::string>> base_urls_;
};

}  // namespace tempera

#endif  // TEMPERA_CLIENT_HPP
