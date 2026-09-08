"""Render the C++20 SDK surface tables from surface.json.

Header-only: one ``constexpr`` table per section, in the same order and with
the same content as ``render_rust`` in ``scripts/gen-sdk-surface.py`` — surface
version, audiences, default audience, scopes, issuer paths, environments,
products, the flat operations table carrying a ``product`` field, MCP methods,
MCP error codes, the protocol version, and the ``find_operation`` /
``find_product`` lookups.

String literals reuse :func:`renderers.c.c_literal`: the escaping hazards are
the same in C++ (greedy ``\\x``, trigraphs in pre-C++17 modes, no ordinary
escape for a non-BMP code point), and sharing one escaper keeps the two
generated tables byte-comparable.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Tuple

from sdk_names import snake_case

from .c import HEADER, c_literal

_OPERATION_FIELDS: List[Tuple[str, str]] = [
    ("product", "std::string_view"),
    ("id", "std::string_view"),
    ("upstream_operation_id", "std::string_view"),
    ("method", "std::string_view"),
    ("path", "std::string_view"),
    ("auth", "std::string_view"),
    ("auth_audience", "std::optional<std::string_view>"),
    ("path_params", "std::span<const std::string_view>"),
    ("path_param_templates", "std::span<const StrPair>"),
    ("query", "std::span<const std::string_view>"),
    ("required_query", "std::span<const std::string_view>"),
    ("headers", "std::span<const std::string_view>"),
    ("required_headers", "std::span<const std::string_view>"),
    ("body", "std::span<const std::string_view>"),
    ("forbidden_body", "std::span<const std::string_view>"),
    ("required_body", "std::span<const std::string_view>"),
    ("body_defaults", "std::span<const StrPair>"),
    ("request_body_kind", "std::string_view"),
    ("request_content_type", "std::optional<std::string_view>"),
    ("scope", "std::optional<std::string_view>"),
    ("physical_action", "bool"),
    ("prepare_commit_required", "bool"),
    ("safe_retry", "std::string_view"),
    ("description", "std::string_view"),
]


def cpp_literal(value: str) -> str:
    """Render one string as a portable, pure-ASCII C++ string literal."""

    return c_literal(value)


def cpp_optional_literal(value: Optional[str]) -> str:
    return "std::nullopt" if value is None else cpp_literal(value)


class _Interner:
    """Deduplicate the repeated ``constexpr`` arrays the operations share."""

    def __init__(self, prefix: str, element: str) -> None:
        self.prefix = prefix
        self.element = element
        self._names: Dict[str, str] = {}
        self._definitions: List[str] = []

    def intern(self, values) -> str:
        if not values:
            return "{}"
        key = json.dumps(values, sort_keys=False)
        name = self._names.get(key)
        if name is None:
            name = f"{self.prefix}{len(self._names)}"
            self._names[key] = name
            if self.element == "std::string_view":
                body = ", ".join(cpp_literal(value) for value in values)
            else:
                body = ", ".join(
                    "StrPair{%s, %s}" % (cpp_literal(k), cpp_literal(v)) for k, v in values
                )
            self._definitions.append(
                f"inline constexpr {self.element} {name}[] = {{{body}}};"
            )
        return f"detail::{name}"

    def definitions(self) -> List[str]:
        return list(self._definitions)


def _pairs(mapping: Dict[str, object]) -> List[Tuple[str, str]]:
    return [(key, str(value)) for key, value in mapping.items()]


def render_cpp_header(surface: dict) -> str:
    lines = [
        f"// {HEADER}",
        "// The SDK surface tables: products, audiences, scopes, environments,",
        "// the error contract, and every typed operation, shared verbatim with",
        "// the TypeScript, Python, Rust, and C packages.",
        "",
        "#ifndef TEMPERA_SURFACE_HPP",
        "#define TEMPERA_SURFACE_HPP",
        "",
        "#include <array>",
        "#include <cstddef>",
        "#include <cstdint>",
        "#include <optional>",
        "#include <span>",
        "#include <string_view>",
        "",
        "namespace tempera::surface {",
        "",
        "/// surface.json manifest revision these tables were generated from.",
        f"inline constexpr int SURFACE_VERSION = {surface['version']};",
        "",
        "/// One (key, value) entry of a generated string table.",
        "struct StrPair {",
        "    std::string_view key;",
        "    std::string_view value;",
        "};",
        "",
    ]

    audiences = ", ".join(cpp_literal(value) for value in surface["audiences"])
    lines += [
        "/// Registered token audiences.",
        "inline constexpr std::array<std::string_view, "
        f"{len(surface['audiences'])}> AUDIENCES{{{{{audiences}}}}};",
        "inline constexpr std::string_view DEFAULT_AUDIENCE = "
        + cpp_literal(surface["defaultAudience"])
        + ";",
        "",
    ]
    scopes = ", ".join(cpp_literal(value) for value in surface["scopes"])
    lines += [
        "/// Registered OAuth scopes.",
        "inline constexpr std::array<std::string_view, "
        f"{len(surface['scopes'])}> SCOPES{{{{{scopes}}}}};",
        "",
        "/// Issuer paths, relative to the control-plane issuer URL.",
        "inline constexpr std::string_view AUTHORIZE_PATH = "
        + cpp_literal(surface["issuer"]["authorizePath"])
        + ";",
        "inline constexpr std::string_view TOKEN_PATH = "
        + cpp_literal(surface["issuer"]["tokenPath"])
        + ";",
        "inline constexpr std::string_view REVOKE_PATH = "
        + cpp_literal(surface["issuer"]["revokePath"])
        + ";",
        "inline constexpr std::string_view INTROSPECT_PATH = "
        + cpp_literal(surface["issuer"]["introspectPath"])
        + ";",
        "inline constexpr std::string_view MCP_PATH = "
        + cpp_literal(surface["issuer"]["mcpPath"])
        + ";",
        "",
        "/// One environment preset.",
        "struct EnvironmentTarget {",
        "    std::string_view environment;",
    ]
    env_fields = sorted(next(iter(surface["environments"].values())).keys())
    for field in env_fields:
        lines.append(f"    std::string_view {snake_case(field)};")
    lines += [
        "};",
        "",
        "inline constexpr std::array<EnvironmentTarget, "
        f"{len(surface['environments'])}> ENVIRONMENTS{{{{",
    ]
    for env_name, target in surface["environments"].items():
        lines.append("    EnvironmentTarget{")
        lines.append(f"        .environment = {cpp_literal(env_name)},")
        for field in env_fields:
            lines.append(f"        .{snake_case(field)} = {cpp_literal(target[field])},")
        lines.append("    },")
    lines += [
        "}};",
        "",
        "/// One product in the registry.",
        "struct ProductSpec {",
        "    std::string_view key;",
        "    std::string_view name;",
        "    std::string_view repository;",
        "    std::string_view env_var;",
        "    /// Empty when the product has no pinned token audience.",
        "    std::optional<std::string_view> audience;",
        "    std::string_view description;",
        "};",
        "",
        "inline constexpr std::array<ProductSpec, "
        f"{len(surface['products'])}> PRODUCTS{{{{",
    ]
    for key, product in surface["products"].items():
        lines.append("    ProductSpec{")
        lines.append(f"        .key = {cpp_literal(snake_case(key))},")
        lines.append(f"        .name = {cpp_literal(product['name'])},")
        lines.append(f"        .repository = {cpp_literal(product['repository'])},")
        lines.append(f"        .env_var = {cpp_literal(product['envVar'])},")
        lines.append(f"        .audience = {cpp_optional_literal(product['audience'])},")
        lines.append(f"        .description = {cpp_literal(product['description'])},")
        lines.append("    },")
    lines += [
        "}};",
        "",
        "/// One typed operation. Span members are empty when the operation",
        "/// declares no entries of that kind.",
        "struct OperationSpec {",
    ]
    for field, field_type in _OPERATION_FIELDS:
        if field == "auth_audience":
            lines.append('    /// Empty unless auth is "oauthResource".')
        if field == "request_content_type":
            lines.append('    /// Empty unless request_body_kind is "binary".')
        if field == "scope":
            lines.append("    /// Empty when the operation requires no scope.")
        lines.append(f"    {field_type} {field};")
    lines += [
        "};",
        "",
    ]

    strings = _Interner("kStrings", "std::string_view")
    pairs = _Interner("kPairs", "StrPair")
    operations: List[str] = []
    total = 0
    for product_key, product_ops in surface["operations"].items():
        for op in product_ops:
            total += 1
            values = {
                "product": cpp_literal(snake_case(product_key)),
                "id": cpp_literal(snake_case(op["id"])),
                "upstream_operation_id": cpp_literal(op["upstreamOperationId"]),
                "method": cpp_literal(op["method"]),
                "path": cpp_literal(op["path"]),
                "auth": cpp_literal(op["auth"]),
                "auth_audience": cpp_optional_literal(op.get("authAudience")),
                "path_params": strings.intern(op.get("pathParams", [])),
                "path_param_templates": pairs.intern(_pairs(op.get("pathParamTemplates", {}))),
                "query": strings.intern(op.get("query", [])),
                "required_query": strings.intern(op.get("requiredQuery", [])),
                "headers": strings.intern(op.get("headers", [])),
                "required_headers": strings.intern(op.get("requiredHeaders", [])),
                "body": strings.intern(op.get("body", [])),
                "forbidden_body": strings.intern(op.get("forbiddenBody", [])),
                "required_body": strings.intern(op.get("requiredBody", [])),
                "body_defaults": pairs.intern(_pairs(op.get("bodyDefaults", {}))),
                "request_body_kind": cpp_literal(op.get("requestBodyKind", "none")),
                "request_content_type": cpp_optional_literal(op.get("requestContentType")),
                "scope": cpp_optional_literal(op.get("scope")),
                "physical_action": "true" if op.get("physicalAction", False) else "false",
                "prepare_commit_required": (
                    "true" if op.get("prepareCommitRequired", False) else "false"
                ),
                "safe_retry": cpp_literal(op["safeRetry"]),
                "description": cpp_literal(op["description"]),
            }
            operations.append("    OperationSpec{")
            for field, _ in _OPERATION_FIELDS:
                operations.append(f"        .{field} = {values[field]},")
            operations.append("    },")

    lines.append("namespace detail {")
    lines.append("")
    lines.append("// Interned parameter-name tables shared by the operations below.")
    lines += strings.definitions()
    lines.append("")
    lines += pairs.definitions()
    lines.append("")
    lines.append("}  // namespace detail")
    lines.append("")
    lines.append("/// Every operation of every product, flat, carrying its product key.")
    lines.append(f"inline constexpr std::array<OperationSpec, {total}> OPERATIONS{{{{")
    lines += operations
    lines += [
        "}};",
        "",
        "/// One JSON-RPC method of the unified MCP gateway.",
        "struct McpMethodSpec {",
        "    std::string_view id;",
        "    std::string_view rpc;",
        "    /// Empty when the method is not a tool call.",
        "    std::optional<std::string_view> tool;",
        "    std::string_view description;",
        "};",
        "",
        "inline constexpr std::array<McpMethodSpec, "
        f"{len(surface['mcpGateway']['methods'])}> MCP_METHODS{{{{",
    ]
    for method in surface["mcpGateway"]["methods"]:
        lines.append("    McpMethodSpec{")
        lines.append(f"        .id = {cpp_literal(snake_case(method['id']))},")
        lines.append(f"        .rpc = {cpp_literal(method['rpc'])},")
        lines.append(f"        .tool = {cpp_optional_literal(method.get('tool'))},")
        lines.append(f"        .description = {cpp_literal(method['description'])},")
        lines.append("    },")
    codes = surface["mcpGateway"]["errorCodes"]
    lines += [
        "}};",
        "",
        "/// MCP gateway JSON-RPC error codes.",
        f"inline constexpr std::int64_t MCP_ERROR_PLAN_LIMIT = {codes['planLimit']};",
        f"inline constexpr std::int64_t MCP_ERROR_INVALID_REQUEST = {codes['invalidRequest']};",
        f"inline constexpr std::int64_t MCP_ERROR_METHOD_NOT_FOUND = {codes['methodNotFound']};",
        f"inline constexpr std::int64_t MCP_ERROR_INVALID_PARAMS = {codes['invalidParams']};",
        f"inline constexpr std::int64_t MCP_ERROR_INTERNAL = {codes['internalError']};",
        "",
        "/// Look up one operation by product key and snake_case operation id.",
        "constexpr const OperationSpec *find_operation(std::string_view product,",
        "                                             std::string_view id) noexcept {",
        "    for (const OperationSpec &op : OPERATIONS) {",
        "        if (op.product == product && op.id == id) {",
        "            return &op;",
        "        }",
        "    }",
        "    return nullptr;",
        "}",
        "",
        "/// Look up one product by snake_case key.",
        "constexpr const ProductSpec *find_product(std::string_view key) noexcept {",
        "    for (const ProductSpec &product : PRODUCTS) {",
        "        if (product.key == key) {",
        "            return &product;",
        "        }",
        "    }",
        "    return nullptr;",
        "}",
        "",
        "}  // namespace tempera::surface",
        "",
        "#endif  // TEMPERA_SURFACE_HPP",
        "",
    ]
    return "\n".join(lines)


TARGETS = {
    "packages/cpp/include/tempera/surface.hpp": render_cpp_header,
}
