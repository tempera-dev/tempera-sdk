// Uniform Tempera API errors, shared in shape with the TypeScript, Python,
// Rust, and C packages (see surface.json errorContract).
//
// The package is dependency-free, so this header carries a small JSON scanner
// (tempera::detail::parse_json) sufficient for the canonical AIP-193 envelope,
// the supported compatibility shapes, and JSON-RPC error objects, plus
// normalize_error_body(), which folds any of them into one ApiError.

#ifndef TEMPERA_ERROR_HPP
#define TEMPERA_ERROR_HPP

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace tempera {

/// Escape a string for inclusion inside a JSON string literal, without the
/// surrounding quotes.
inline std::string json_escape(std::string_view value) {
    std::string out;
    out.reserve(value.size());
    for (unsigned char byte : value) {
        switch (byte) {
        case '"':
            out += "\\\"";
            break;
        case '\\':
            out += "\\\\";
            break;
        case '\n':
            out += "\\n";
            break;
        case '\r':
            out += "\\r";
            break;
        case '\t':
            out += "\\t";
            break;
        default:
            if (byte < 0x20) {
                static const char *const HEX = "0123456789abcdef";
                out += "\\u00";
                out += HEX[(byte >> 4) & 0x0f];
                out += HEX[byte & 0x0f];
            } else {
                out += static_cast<char>(byte);
            }
            break;
        }
    }
    return out;
}

namespace detail {

/// Minimal JSON value model produced by the scanner below. Numbers keep their
/// raw source text so integer JSON-RPC codes round-trip exactly.
class Json {
public:
    enum class Kind { Null, Bool, Number, String, Array, Object };

    Kind kind = Kind::Null;
    bool boolean = false;
    /// String payload, or the raw source text of a number.
    std::string text;
    std::vector<Json> items;
    std::vector<std::string> keys;

    /// Member of an object by key; nullptr for non-objects and missing keys.
    [[nodiscard]] const Json *get(std::string_view key) const noexcept {
        if (kind != Kind::Object) {
            return nullptr;
        }
        for (std::size_t index = 0; index < keys.size(); ++index) {
            if (keys[index] == key) {
                return &items[index];
            }
        }
        return nullptr;
    }

    /// The string payload, when this value is a JSON string.
    [[nodiscard]] std::optional<std::string> as_string() const {
        if (kind != Kind::String) {
            return std::nullopt;
        }
        return text;
    }

    /// The integer payload, when this value is a JSON number.
    [[nodiscard]] std::optional<std::int64_t> as_int64() const {
        if (kind != Kind::Number) {
            return std::nullopt;
        }
        try {
            std::size_t consumed = 0;
            const long long parsed = std::stoll(text, &consumed);
            if (consumed == text.size()) {
                return static_cast<std::int64_t>(parsed);
            }
            return static_cast<std::int64_t>(std::stod(text));
        } catch (...) {
            return std::nullopt;
        }
    }
};

/// Recursive-descent scanner. Strict on purpose: raw control bytes inside
/// strings, unpaired surrogates, and trailing garbage make the whole document
/// unparseable, exactly as in the Rust and C packages.
class JsonParser {
public:
    explicit JsonParser(std::string_view input) noexcept : input_(input) {}

    std::optional<Json> parse_document() {
        skip_whitespace();
        std::optional<Json> value = parse_value();
        if (!value.has_value()) {
            return std::nullopt;
        }
        skip_whitespace();
        if (position_ != input_.size()) {
            return std::nullopt;
        }
        return value;
    }

private:
    std::string_view input_;
    std::size_t position_ = 0;

    [[nodiscard]] int peek() const noexcept {
        if (position_ >= input_.size()) {
            return -1;
        }
        return static_cast<unsigned char>(input_[position_]);
    }

    int bump() noexcept {
        const int byte = peek();
        if (byte >= 0) {
            ++position_;
        }
        return byte;
    }

    void skip_whitespace() noexcept {
        while (true) {
            const int byte = peek();
            if (byte == ' ' || byte == '\t' || byte == '\n' || byte == '\r') {
                ++position_;
            } else {
                return;
            }
        }
    }

    bool eat(std::string_view token) noexcept {
        if (input_.substr(position_).rfind(token, 0) != 0) {
            return false;
        }
        position_ += token.size();
        return true;
    }

    static void append_utf8(std::string &out, std::uint32_t code_point) {
        if (code_point < 0x80U) {
            out += static_cast<char>(code_point);
        } else if (code_point < 0x800U) {
            out += static_cast<char>(0xC0U | (code_point >> 6));
            out += static_cast<char>(0x80U | (code_point & 0x3FU));
        } else if (code_point < 0x10000U) {
            out += static_cast<char>(0xE0U | (code_point >> 12));
            out += static_cast<char>(0x80U | ((code_point >> 6) & 0x3FU));
            out += static_cast<char>(0x80U | (code_point & 0x3FU));
        } else {
            out += static_cast<char>(0xF0U | (code_point >> 18));
            out += static_cast<char>(0x80U | ((code_point >> 12) & 0x3FU));
            out += static_cast<char>(0x80U | ((code_point >> 6) & 0x3FU));
            out += static_cast<char>(0x80U | (code_point & 0x3FU));
        }
    }

    std::optional<std::uint32_t> parse_hex4() {
        std::uint32_t value = 0;
        for (int index = 0; index < 4; ++index) {
            const int byte = bump();
            std::uint32_t digit = 0;
            if (byte >= '0' && byte <= '9') {
                digit = static_cast<std::uint32_t>(byte - '0');
            } else if (byte >= 'a' && byte <= 'f') {
                digit = static_cast<std::uint32_t>(byte - 'a' + 10);
            } else if (byte >= 'A' && byte <= 'F') {
                digit = static_cast<std::uint32_t>(byte - 'A' + 10);
            } else {
                return std::nullopt;
            }
            value = (value << 4) | digit;
        }
        return value;
    }

    std::optional<std::string> parse_string() {
        std::string out;
        bump();  // consume the opening quote
        while (true) {
            const std::size_t start = position_;
            while (true) {
                const int byte = peek();
                if (byte < 0 || byte == '"' || byte == '\\' || byte < 0x20) {
                    break;
                }
                ++position_;
            }
            out.append(input_.substr(start, position_ - start));
            const int byte = bump();
            if (byte == '"') {
                return out;
            }
            if (byte != '\\') {
                // End of input, or a raw control character inside the string.
                return std::nullopt;
            }
            switch (bump()) {
            case '"':
                out += '"';
                break;
            case '\\':
                out += '\\';
                break;
            case '/':
                out += '/';
                break;
            case 'b':
                out += '\b';
                break;
            case 'f':
                out += '\f';
                break;
            case 'n':
                out += '\n';
                break;
            case 'r':
                out += '\r';
                break;
            case 't':
                out += '\t';
                break;
            case 'u': {
                const std::optional<std::uint32_t> unit = parse_hex4();
                if (!unit.has_value()) {
                    return std::nullopt;
                }
                std::uint32_t code_point = *unit;
                if (code_point >= 0xD800U && code_point < 0xDC00U) {
                    if (bump() != '\\' || bump() != 'u') {
                        return std::nullopt;
                    }
                    const std::optional<std::uint32_t> low = parse_hex4();
                    if (!low.has_value() || *low < 0xDC00U || *low >= 0xE000U) {
                        return std::nullopt;
                    }
                    code_point = 0x10000U + ((code_point - 0xD800U) << 10) + (*low - 0xDC00U);
                } else if (code_point >= 0xDC00U && code_point < 0xE000U) {
                    // An unpaired low surrogate is not a code point.
                    return std::nullopt;
                }
                append_utf8(out, code_point);
                break;
            }
            default:
                return std::nullopt;
            }
        }
    }

    bool eat_digits() noexcept {
        const std::size_t start = position_;
        while (peek() >= '0' && peek() <= '9') {
            ++position_;
        }
        return position_ > start;
    }

    std::optional<Json> parse_number() {
        const std::size_t start = position_;
        if (peek() == '-') {
            ++position_;
        }
        if (!eat_digits()) {
            return std::nullopt;
        }
        if (peek() == '.') {
            ++position_;
            if (!eat_digits()) {
                return std::nullopt;
            }
        }
        if (peek() == 'e' || peek() == 'E') {
            ++position_;
            if (peek() == '+' || peek() == '-') {
                ++position_;
            }
            if (!eat_digits()) {
                return std::nullopt;
            }
        }
        Json node;
        node.kind = Json::Kind::Number;
        node.text = std::string(input_.substr(start, position_ - start));
        return node;
    }

    std::optional<Json> parse_object() {
        Json node;
        node.kind = Json::Kind::Object;
        bump();  // consume '{'
        skip_whitespace();
        if (peek() == '}') {
            bump();
            return node;
        }
        while (true) {
            skip_whitespace();
            if (peek() != '"') {
                return std::nullopt;
            }
            std::optional<std::string> key = parse_string();
            if (!key.has_value()) {
                return std::nullopt;
            }
            skip_whitespace();
            if (bump() != ':') {
                return std::nullopt;
            }
            skip_whitespace();
            std::optional<Json> value = parse_value();
            if (!value.has_value()) {
                return std::nullopt;
            }
            node.keys.push_back(std::move(*key));
            node.items.push_back(std::move(*value));
            skip_whitespace();
            const int byte = bump();
            if (byte == ',') {
                continue;
            }
            if (byte == '}') {
                return node;
            }
            return std::nullopt;
        }
    }

    std::optional<Json> parse_array() {
        Json node;
        node.kind = Json::Kind::Array;
        bump();  // consume '['
        skip_whitespace();
        if (peek() == ']') {
            bump();
            return node;
        }
        while (true) {
            skip_whitespace();
            std::optional<Json> value = parse_value();
            if (!value.has_value()) {
                return std::nullopt;
            }
            node.items.push_back(std::move(*value));
            skip_whitespace();
            const int byte = bump();
            if (byte == ',') {
                continue;
            }
            if (byte == ']') {
                return node;
            }
            return std::nullopt;
        }
    }

    std::optional<Json> parse_value() {
        const int byte = peek();
        switch (byte) {
        case '{':
            return parse_object();
        case '[':
            return parse_array();
        case '"': {
            std::optional<std::string> text = parse_string();
            if (!text.has_value()) {
                return std::nullopt;
            }
            Json node;
            node.kind = Json::Kind::String;
            node.text = std::move(*text);
            return node;
        }
        case 't': {
            if (!eat("true")) {
                return std::nullopt;
            }
            Json node;
            node.kind = Json::Kind::Bool;
            node.boolean = true;
            return node;
        }
        case 'f': {
            if (!eat("false")) {
                return std::nullopt;
            }
            Json node;
            node.kind = Json::Kind::Bool;
            node.boolean = false;
            return node;
        }
        case 'n': {
            if (!eat("null")) {
                return std::nullopt;
            }
            return Json{};
        }
        default:
            if (byte == '-' || (byte >= '0' && byte <= '9')) {
                return parse_number();
            }
            return std::nullopt;
        }
    }
};

/// Parse a complete JSON document; std::nullopt on any syntax error or
/// trailing garbage, which callers treat as "unparseable body".
inline std::optional<Json> parse_json(std::string_view input) {
    return JsonParser(input).parse_document();
}

/// The AIP-193 google.rpc.ErrorInfo reason from an error's details[]. The
/// first detail carrying a string `reason` wins.
inline std::optional<std::string> error_info_reason(const Json &error) {
    const Json *details = error.get("details");
    if (details == nullptr || details->kind != Json::Kind::Array) {
        return std::nullopt;
    }
    for (const Json &detail : details->items) {
        const Json *reason = detail.get("reason");
        if (reason != nullptr) {
            if (std::optional<std::string> text = reason->as_string(); text.has_value()) {
                return text;
            }
        }
    }
    return std::nullopt;
}

}  // namespace detail

/// An HTTP error response from any Tempera product, normalized from the
/// canonical AIP-193 envelope and the supported compatibility shapes so callers
/// always read the same fields.
struct ApiError {
    /// HTTP status code of the failed response.
    int status = 0;
    /// Machine-readable error code, when the wire shape carried one.
    std::optional<std::string> code;
    /// Human-readable error message; never empty.
    std::string message;
    /// google.rpc.ErrorInfo reason from error.details[], when one is present.
    std::optional<std::string> reason;
    /// Server request id, when the wire shape carried one.
    std::optional<std::string> request_id;

    [[nodiscard]] std::string to_string() const {
        std::string out = "Tempera request failed (" + std::to_string(status) + "): " + message;
        if (code.has_value()) {
            out += " [code: " + *code + "]";
        }
        if (reason.has_value()) {
            out += " [reason: " + *reason + "]";
        }
        if (request_id.has_value()) {
            out += " [request_id: " + *request_id + "]";
        }
        return out;
    }
};

/// Normalize any Tempera product error body into an ApiError.
///
/// Wire shapes handled (see surface.json errorContract.wireShapes):
///  - canonical resource API: {"error": {"code": 400, "status":
///    "INVALID_ARGUMENT", "message": "...", "details": []}}
///  - legacy flat:            {"error": "<code>", "message": "<text>"}
///  - legacy message-only:    {"error": "<human message>"}
///  - legacy nested:          {"error": {"code", "message", "request_id"?, ...}}
///  - anything unparseable:   message is status_text, or "request failed" when
///    the status text is empty -- the same fallback rule as every other
///    package, so one wire response yields one message everywhere.
inline ApiError normalize_error_body(int status, std::string_view status_text,
                                     std::string_view body) {
    ApiError result;
    result.status = status;

    if (std::optional<detail::Json> root = detail::parse_json(body); root.has_value()) {
        if (const detail::Json *error = root->get("error"); error != nullptr) {
            if (error->kind == detail::Json::Kind::Object) {
                std::optional<std::string> code;
                if (const detail::Json *member = error->get("status"); member != nullptr) {
                    code = member->as_string();
                }
                if (!code.has_value()) {
                    if (const detail::Json *member = error->get("code"); member != nullptr) {
                        code = member->as_string();
                    }
                }
                std::optional<std::string> message;
                if (const detail::Json *member = error->get("message"); member != nullptr) {
                    message = member->as_string();
                }
                std::optional<std::string> request_id;
                if (const detail::Json *member = error->get("requestId"); member != nullptr) {
                    request_id = member->as_string();
                }
                if (!request_id.has_value()) {
                    if (const detail::Json *member = error->get("request_id"); member != nullptr) {
                        request_id = member->as_string();
                    }
                }
                result.code = std::move(code);
                result.message =
                    message.has_value() ? *message : std::string(status_text);
                result.reason = detail::error_info_reason(*error);
                result.request_id = std::move(request_id);
                return result;
            }
            if (error->kind == detail::Json::Kind::String) {
                if (const detail::Json *message = root->get("message"); message != nullptr) {
                    if (std::optional<std::string> text = message->as_string(); text.has_value()) {
                        result.code = error->text;
                        result.message = *text;
                        return result;
                    }
                }
                result.message = error->text;
                return result;
            }
        }
    }

    result.message = status_text.empty() ? std::string("request failed") : std::string(status_text);
    return result;
}

}  // namespace tempera

#endif  // TEMPERA_ERROR_HPP
