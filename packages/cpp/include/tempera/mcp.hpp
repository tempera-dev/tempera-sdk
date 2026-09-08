// JSON-RPC 2.0 body builders for the unified Tempera MCP gateway
// (${issuer}/mcp): stateless streamable-HTTP JSON-RPC over the fixed
// capability-fabric verb surface.
//
// The package is HTTP-less: McpRequestBuilder produces the exact request
// bodies the gateway expects. POST them at Auth::mcp_url() with an
// "authorization: Bearer <token>" header (a bearer minted for audience
// tempera-mcp with scope mcp:invoke, or a central tp_ API key), then feed error
// responses to parse_mcp_error().

#ifndef TEMPERA_MCP_HPP
#define TEMPERA_MCP_HPP

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <utility>

#include "tempera/error.hpp"
#include "tempera/surface.hpp"

namespace tempera {

/// MCP protocol revision sent in initialize requests.
inline constexpr std::string_view MCP_PROTOCOL_VERSION = "2025-06-18";

/// Builds JSON-RPC 2.0 request bodies for the MCP gateway with monotonically
/// increasing request ids. Each *_body method returns (id, body) so the caller
/// can correlate responses.
class McpRequestBuilder {
public:
    McpRequestBuilder() = default;

    /// Body for initialize: open an MCP session and fetch server capabilities
    /// and instructions.
    std::pair<std::int64_t, std::string> initialize_body(std::string_view client_name,
                                                         std::string_view client_version) {
        const std::int64_t id = take_id();
        std::string body = envelope(id, "initialize");
        body += ",\"params\":{\"protocolVersion\":\"";
        body += MCP_PROTOCOL_VERSION;
        body += "\",\"capabilities\":{},\"clientInfo\":{\"name\":\"";
        body += json_escape(client_name);
        body += "\",\"version\":\"";
        body += json_escape(client_version);
        body += "\"}}}";
        return {id, body};
    }

    /// Body for ping: check gateway liveness over JSON-RPC (no params).
    std::pair<std::int64_t, std::string> ping_body() { return simple_body("ping"); }

    /// Body for tools/list: list the fixed capability-fabric verb surface.
    std::pair<std::int64_t, std::string> list_tools_body() { return simple_body("tools/list"); }

    /// Body for tools/call: invoke a tool by name; product tool calls are
    /// metered. `arguments_json` must be a serialized JSON object, spliced
    /// verbatim; std::nullopt sends empty arguments ({}).
    std::pair<std::int64_t, std::string> call_tool_body(
        std::string_view tool_name,
        std::optional<std::string_view> arguments_json = std::nullopt) {
        const std::int64_t id = take_id();
        std::string body = envelope(id, "tools/call");
        body += ",\"params\":{\"name\":\"";
        body += json_escape(tool_name);
        body += "\",\"arguments\":";
        body += arguments_json.has_value() ? *arguments_json : std::string_view("{}");
        body += "}}";
        return {id, body};
    }

    /// Body for the tempera_whoami builtin tool.
    std::pair<std::int64_t, std::string> whoami_body() {
        return call_tool_body("tempera_whoami");
    }

    /// Body for the tempera_status builtin tool.
    std::pair<std::int64_t, std::string> status_body() {
        return call_tool_body("tempera_status");
    }

private:
    std::int64_t next_id_ = 1;

    std::int64_t take_id() noexcept { return next_id_++; }

    static std::string envelope(std::int64_t id, std::string_view method) {
        std::string body = "{\"jsonrpc\":\"2.0\",\"id\":";
        body += std::to_string(id);
        body += ",\"method\":\"";
        body += method;
        body += "\"";
        return body;
    }

    std::pair<std::int64_t, std::string> simple_body(std::string_view method) {
        const std::int64_t id = take_id();
        return {id, envelope(id, method) + "}"};
    }
};

/// A JSON-RPC error returned by an MCP endpoint. Gateway error codes are the
/// MCP_ERROR_* constants in tempera::surface.
struct McpError {
    /// JSON-RPC error code (for example -32002 for a plan limit); 0 when the
    /// response carried a non-conformant error without an integer code.
    std::int64_t code = 0;
    std::string message;

    [[nodiscard]] std::string to_string() const {
        return "MCP error " + std::to_string(code) + ": " + message;
    }
};

/// Extract the JSON-RPC error from an MCP response body, if any: a top-level
/// "error" object with a numeric code (any `data` member is ignored). Returns
/// std::nullopt for success responses and unparseable bodies.
inline std::optional<McpError> parse_mcp_error(std::string_view body) {
    const std::optional<detail::Json> root = detail::parse_json(body);
    if (!root.has_value()) {
        return std::nullopt;
    }
    const detail::Json *error = root->get("error");
    if (error == nullptr) {
        return std::nullopt;
    }
    // Uniform rule (same in TypeScript, Python, Rust, and C): a JSON-RPC error
    // object carries its integer code (0 when absent) and string message; a
    // non-conformant non-object error becomes code 0 with its string form.
    switch (error->kind) {
    case detail::Json::Kind::Object: {
        McpError result;
        if (const detail::Json *code = error->get("code"); code != nullptr) {
            result.code = code->as_int64().value_or(0);
        }
        if (const detail::Json *message = error->get("message"); message != nullptr) {
            result.message = message->as_string().value_or("MCP error");
        } else {
            result.message = "MCP error";
        }
        return result;
    }
    case detail::Json::Kind::String:
        return McpError{0, error->text};
    case detail::Json::Kind::Null:
        return std::nullopt;
    case detail::Json::Kind::Number:
        return McpError{0, error->text};
    case detail::Json::Kind::Bool:
        return McpError{0, error->boolean ? "true" : "false"};
    case detail::Json::Kind::Array:
        return McpError{0, std::string()};
    }
    return std::nullopt;
}

}  // namespace tempera

#endif  // TEMPERA_MCP_HPP
