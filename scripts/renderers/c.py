"""Render the C99 SDK surface tables from surface.json.

Emits the same tables as ``render_rust`` in ``scripts/gen-sdk-surface.py``:
surface version, audiences, default audience, scopes, issuer paths,
environments, products, one flat operations array carrying a ``product`` field,
the MCP method table, the MCP error codes, the protocol version, and the
``tempera_find_operation`` / ``tempera_find_product`` lookups.

C is the strictest string-literal target in the repository, so
:func:`c_literal` does the escaping by hand instead of reusing ``json.dumps``:

* ``json.dumps`` emits ``\\uXXXX``. C99 spells universal character names the
  same way but forbids most of the range this manifest could carry, and the
  execution character set is implementation-defined; a non-BMP code point has
  no single-escape spelling at all. Every byte outside printable ASCII is
  therefore emitted as an explicit UTF-8 ``\\xNN`` byte escape, which keeps the
  generated source pure ASCII and byte-exact.
* ``\\x`` is greedy in C: it consumes every following hex digit. When an
  escaped byte is followed by a literal hex-digit character the literal is
  split with adjacent-string concatenation (``"\\xf0\\x9f\\x9a\\x80" "7"``) so
  the digit cannot be swallowed.
* Trigraphs (``??=``, ``??/``, ``??-`` and friends) are replaced in translation
  phase 1, before escape sequences are interpreted, so every ``?`` is written
  as ``\\?``. No two question marks can ever end up adjacent in the source.
* A NUL would silently truncate a ``const char *`` table entry, and a lone
  surrogate is not encodable as UTF-8; both are rejected loudly instead.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Sequence, Tuple

from sdk_names import snake_case

HEADER = "GENERATED FROM surface.json by scripts/gen-sdk-surface.py -- DO NOT EDIT BY HAND."

_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


def c_literal(value: str) -> str:
    """Render one string as a portable, pure-ASCII C (and C++) string literal."""

    if "\x00" in value:
        raise ValueError("C string literals cannot contain a NUL character")
    for character in value:
        if 0xD800 <= ord(character) <= 0xDFFF:
            raise ValueError("C literals cannot contain surrogate code points")
    pieces: List[str] = ['"']
    previous_was_hex = False
    for byte in value.encode("utf-8"):
        emitted_hex = False
        if byte == 0x22:
            token = '\\"'
        elif byte == 0x5C:
            token = "\\\\"
        elif byte == 0x3F:
            # Defuse every trigraph without inspecting adjacency.
            token = "\\?"
        elif byte == 0x0A:
            token = "\\n"
        elif byte == 0x0D:
            token = "\\r"
        elif byte == 0x09:
            token = "\\t"
        elif 0x20 <= byte < 0x7F:
            token = chr(byte)
            if previous_was_hex and token in _HEX_DIGITS:
                # \xNN is greedy; break the literal so the digit stays a digit.
                pieces.append('" "')
        else:
            token = "\\x%02x" % byte
            emitted_hex = True
        pieces.append(token)
        previous_was_hex = emitted_hex
    pieces.append('"')
    return "".join(pieces)


def c_optional_literal(value: Optional[str]) -> str:
    return "NULL" if value is None else c_literal(value)


def _banner(comment_lines: Sequence[str]) -> List[str]:
    return [f"/* {HEADER} */"] + [f"/* {line} */" for line in comment_lines] + [""]


class _Interner:
    """Deduplicate the repeated string / pair arrays the operations share."""

    def __init__(self, prefix: str, kind: str) -> None:
        self.prefix = prefix
        self.kind = kind
        self._names: Dict[str, str] = {}
        self._definitions: List[str] = []

    def intern(self, values) -> str:
        if not values:
            return "NULL"
        key = json.dumps(values, sort_keys=False)
        name = self._names.get(key)
        if name is None:
            name = f"{self.prefix}{len(self._names)}"
            self._names[key] = name
            if self.kind == "str":
                body = ", ".join(c_literal(value) for value in values)
                self._definitions.append(f"static const char *const {name}[] = {{{body}}};")
            else:
                body = ", ".join(
                    "{%s, %s}" % (c_literal(key_), c_literal(value_)) for key_, value_ in values
                )
                self._definitions.append(f"static const tempera_str_pair {name}[] = {{{body}}};")
        return name

    def definitions(self) -> List[str]:
        return list(self._definitions)


def _pairs(mapping: Dict[str, object]) -> List[Tuple[str, str]]:
    return [(key, str(value)) for key, value in mapping.items()]


def _env_fields(surface: dict) -> List[str]:
    return sorted(next(iter(surface["environments"].values())).keys())


def render_c_header(surface: dict) -> str:
    lines = _banner(
        [
            "The SDK surface tables: products, audiences, scopes, environments,",
            "the error contract, and every typed operation, shared verbatim with",
            "the TypeScript, Python, Rust, and C++ packages.",
        ]
    )
    lines += [
        "#ifndef TEMPERA_SURFACE_H",
        "#define TEMPERA_SURFACE_H",
        "",
        "#include <stdbool.h>",
        "#include <stddef.h>",
        "",
        "#ifdef __cplusplus",
        'extern "C" {',
        "#endif",
        "",
        "/* surface.json manifest revision these tables were generated from. */",
        f"#define TEMPERA_SURFACE_VERSION {surface['version']}",
        "",
        "/* One (key, value) entry of a generated string table. */",
        "typedef struct tempera_str_pair {",
        "    const char *key;",
        "    const char *value;",
        "} tempera_str_pair;",
        "",
        "/* Registered token audiences; TEMPERA_AUDIENCE_COUNT entries. */",
        "extern const char *const TEMPERA_AUDIENCES[];",
        "extern const size_t TEMPERA_AUDIENCE_COUNT;",
        "extern const char *const TEMPERA_DEFAULT_AUDIENCE;",
        "",
        "/* Registered OAuth scopes; TEMPERA_SCOPE_COUNT entries. */",
        "extern const char *const TEMPERA_SCOPES[];",
        "extern const size_t TEMPERA_SCOPE_COUNT;",
        "",
        "/* Issuer paths, relative to the control-plane issuer URL. */",
        "extern const char *const TEMPERA_AUTHORIZE_PATH;",
        "extern const char *const TEMPERA_TOKEN_PATH;",
        "extern const char *const TEMPERA_REVOKE_PATH;",
        "extern const char *const TEMPERA_INTROSPECT_PATH;",
        "extern const char *const TEMPERA_MCP_PATH;",
        "",
        "/* One environment preset. */",
        "typedef struct tempera_environment_target {",
        "    const char *environment;",
    ]
    env_fields = _env_fields(surface)
    for field in env_fields:
        lines.append(f"    const char *{snake_case(field)};")
    lines += [
        "} tempera_environment_target;",
        "",
        "extern const tempera_environment_target TEMPERA_ENVIRONMENTS[];",
        "extern const size_t TEMPERA_ENVIRONMENT_COUNT;",
        "",
        "/* One product in the registry. */",
        "typedef struct tempera_product_spec {",
        "    const char *key;",
        "    const char *name;",
        "    const char *repository;",
        "    const char *env_var;",
        "    /* NULL when the product has no pinned token audience. */",
        "    const char *audience;",
        "    const char *description;",
        "} tempera_product_spec;",
        "",
        "extern const tempera_product_spec TEMPERA_PRODUCTS[];",
        "extern const size_t TEMPERA_PRODUCT_COUNT;",
        "",
        "/* One typed operation. Array members are NULL when the count is 0. */",
        "typedef struct tempera_operation_spec {",
        "    const char *product;",
        "    const char *id;",
        "    const char *upstream_operation_id;",
        "    const char *method;",
        "    const char *path;",
        "    const char *auth;",
        "    /* NULL unless auth is \"oauthResource\". */",
        "    const char *auth_audience;",
        "    const char *const *path_params;",
        "    size_t path_param_count;",
        "    const tempera_str_pair *path_param_templates;",
        "    size_t path_param_template_count;",
        "    const char *const *query;",
        "    size_t query_count;",
        "    const char *const *required_query;",
        "    size_t required_query_count;",
        "    const char *const *headers;",
        "    size_t header_count;",
        "    const char *const *required_headers;",
        "    size_t required_header_count;",
        "    const char *const *body;",
        "    size_t body_count;",
        "    const char *const *forbidden_body;",
        "    size_t forbidden_body_count;",
        "    const char *const *required_body;",
        "    size_t required_body_count;",
        "    const tempera_str_pair *body_defaults;",
        "    size_t body_default_count;",
        "    const char *request_body_kind;",
        "    /* NULL unless request_body_kind is \"binary\". */",
        "    const char *request_content_type;",
        "    /* NULL when the operation requires no scope. */",
        "    const char *scope;",
        "    bool physical_action;",
        "    bool prepare_commit_required;",
        "    const char *safe_retry;",
        "    const char *description;",
        "} tempera_operation_spec;",
        "",
        "/* Every operation of every product, flat, carrying its product key. */",
        "extern const tempera_operation_spec TEMPERA_OPERATIONS[];",
        "extern const size_t TEMPERA_OPERATION_COUNT;",
        "",
        "/* One JSON-RPC method of the unified MCP gateway. */",
        "typedef struct tempera_mcp_method_spec {",
        "    const char *id;",
        "    const char *rpc;",
        "    /* NULL when the method is not a tool call. */",
        "    const char *tool;",
        "    const char *description;",
        "} tempera_mcp_method_spec;",
        "",
        "extern const tempera_mcp_method_spec TEMPERA_MCP_METHODS[];",
        "extern const size_t TEMPERA_MCP_METHOD_COUNT;",
        "",
        "/* MCP gateway JSON-RPC error codes. */",
    ]
    codes = surface["mcpGateway"]["errorCodes"]
    lines += [
        f"#define TEMPERA_MCP_ERROR_PLAN_LIMIT ({codes['planLimit']})",
        f"#define TEMPERA_MCP_ERROR_INVALID_REQUEST ({codes['invalidRequest']})",
        f"#define TEMPERA_MCP_ERROR_METHOD_NOT_FOUND ({codes['methodNotFound']})",
        f"#define TEMPERA_MCP_ERROR_INVALID_PARAMS ({codes['invalidParams']})",
        f"#define TEMPERA_MCP_ERROR_INTERNAL ({codes['internalError']})",
        "",
        "/* Look up one operation by product key and snake_case operation id. */",
        "const tempera_operation_spec *tempera_find_operation(const char *product,",
        "                                                    const char *id);",
        "",
        "/* Look up one product by snake_case key. */",
        "const tempera_product_spec *tempera_find_product(const char *key);",
        "",
        "#ifdef __cplusplus",
        "}",
        "#endif",
        "",
        "#endif /* TEMPERA_SURFACE_H */",
        "",
    ]
    return "\n".join(lines)


def render_c_source(surface: dict) -> str:
    lines = _banner(
        [
            "Definitions for the tables declared in include/tempera/surface.h.",
        ]
    )
    lines += [
        "#include <string.h>",
        "",
        '#include "tempera/surface.h"',
        "",
    ]

    audiences = ", ".join(c_literal(value) for value in surface["audiences"])
    lines += [
        f"const char *const TEMPERA_AUDIENCES[] = {{{audiences}}};",
        "const size_t TEMPERA_AUDIENCE_COUNT ="
        " sizeof(TEMPERA_AUDIENCES) / sizeof(TEMPERA_AUDIENCES[0]);",
        "const char *const TEMPERA_DEFAULT_AUDIENCE = "
        + c_literal(surface["defaultAudience"])
        + ";",
        "",
    ]
    scopes = ", ".join(c_literal(value) for value in surface["scopes"])
    lines += [
        f"const char *const TEMPERA_SCOPES[] = {{{scopes}}};",
        "const size_t TEMPERA_SCOPE_COUNT = sizeof(TEMPERA_SCOPES) / sizeof(TEMPERA_SCOPES[0]);",
        "",
        "const char *const TEMPERA_AUTHORIZE_PATH = "
        + c_literal(surface["issuer"]["authorizePath"])
        + ";",
        "const char *const TEMPERA_TOKEN_PATH = "
        + c_literal(surface["issuer"]["tokenPath"])
        + ";",
        "const char *const TEMPERA_REVOKE_PATH = "
        + c_literal(surface["issuer"]["revokePath"])
        + ";",
        "const char *const TEMPERA_INTROSPECT_PATH = "
        + c_literal(surface["issuer"]["introspectPath"])
        + ";",
        "const char *const TEMPERA_MCP_PATH = " + c_literal(surface["issuer"]["mcpPath"]) + ";",
        "",
    ]

    env_fields = _env_fields(surface)
    lines.append("const tempera_environment_target TEMPERA_ENVIRONMENTS[] = {")
    for env_name, target in surface["environments"].items():
        lines.append("    {")
        lines.append(f"        .environment = {c_literal(env_name)},")
        for field in env_fields:
            lines.append(f"        .{snake_case(field)} = {c_literal(target[field])},")
        lines.append("    },")
    lines += [
        "};",
        "const size_t TEMPERA_ENVIRONMENT_COUNT ="
        " sizeof(TEMPERA_ENVIRONMENTS) / sizeof(TEMPERA_ENVIRONMENTS[0]);",
        "",
    ]

    lines.append("const tempera_product_spec TEMPERA_PRODUCTS[] = {")
    for key, product in surface["products"].items():
        lines.append("    {")
        lines.append(f"        .key = {c_literal(snake_case(key))},")
        lines.append(f"        .name = {c_literal(product['name'])},")
        lines.append(f"        .repository = {c_literal(product['repository'])},")
        lines.append(f"        .env_var = {c_literal(product['envVar'])},")
        lines.append(f"        .audience = {c_optional_literal(product['audience'])},")
        lines.append(f"        .description = {c_literal(product['description'])},")
        lines.append("    },")
    lines += [
        "};",
        "const size_t TEMPERA_PRODUCT_COUNT ="
        " sizeof(TEMPERA_PRODUCTS) / sizeof(TEMPERA_PRODUCTS[0]);",
        "",
    ]

    strings = _Interner("tempera_strs_", "str")
    pairs = _Interner("tempera_pairs_", "pair")
    operations: List[str] = []
    for product_key, product_ops in surface["operations"].items():
        for op in product_ops:
            path_params = strings.intern(op.get("pathParams", []))
            templates = pairs.intern(_pairs(op.get("pathParamTemplates", {})))
            query = strings.intern(op.get("query", []))
            required_query = strings.intern(op.get("requiredQuery", []))
            headers = strings.intern(op.get("headers", []))
            required_headers = strings.intern(op.get("requiredHeaders", []))
            body = strings.intern(op.get("body", []))
            forbidden_body = strings.intern(op.get("forbiddenBody", []))
            required_body = strings.intern(op.get("requiredBody", []))
            body_defaults = pairs.intern(_pairs(op.get("bodyDefaults", {})))

            def count(name: str, values) -> str:
                return "0" if not values else f"sizeof({name}) / sizeof({name}[0])"

            operations.append("    {")
            operations.append(f"        .product = {c_literal(snake_case(product_key))},")
            operations.append(f"        .id = {c_literal(snake_case(op['id']))},")
            operations.append(
                f"        .upstream_operation_id = {c_literal(op['upstreamOperationId'])},"
            )
            operations.append(f"        .method = {c_literal(op['method'])},")
            operations.append(f"        .path = {c_literal(op['path'])},")
            operations.append(f"        .auth = {c_literal(op['auth'])},")
            operations.append(
                f"        .auth_audience = {c_optional_literal(op.get('authAudience'))},"
            )
            operations.append(f"        .path_params = {path_params},")
            operations.append(
                f"        .path_param_count = {count(path_params, op.get('pathParams', []))},"
            )
            operations.append(f"        .path_param_templates = {templates},")
            operations.append(
                "        .path_param_template_count = "
                f"{count(templates, op.get('pathParamTemplates', {}))},"
            )
            operations.append(f"        .query = {query},")
            operations.append(f"        .query_count = {count(query, op.get('query', []))},")
            operations.append(f"        .required_query = {required_query},")
            operations.append(
                "        .required_query_count = "
                f"{count(required_query, op.get('requiredQuery', []))},"
            )
            operations.append(f"        .headers = {headers},")
            operations.append(f"        .header_count = {count(headers, op.get('headers', []))},")
            operations.append(f"        .required_headers = {required_headers},")
            operations.append(
                "        .required_header_count = "
                f"{count(required_headers, op.get('requiredHeaders', []))},"
            )
            operations.append(f"        .body = {body},")
            operations.append(f"        .body_count = {count(body, op.get('body', []))},")
            operations.append(f"        .forbidden_body = {forbidden_body},")
            operations.append(
                "        .forbidden_body_count = "
                f"{count(forbidden_body, op.get('forbiddenBody', []))},"
            )
            operations.append(f"        .required_body = {required_body},")
            operations.append(
                "        .required_body_count = "
                f"{count(required_body, op.get('requiredBody', []))},"
            )
            operations.append(f"        .body_defaults = {body_defaults},")
            operations.append(
                "        .body_default_count = "
                f"{count(body_defaults, op.get('bodyDefaults', {}))},"
            )
            operations.append(
                f"        .request_body_kind = {c_literal(op.get('requestBodyKind', 'none'))},"
            )
            operations.append(
                "        .request_content_type = "
                f"{c_optional_literal(op.get('requestContentType'))},"
            )
            operations.append(f"        .scope = {c_optional_literal(op.get('scope'))},")
            operations.append(
                "        .physical_action = "
                f"{'true' if op.get('physicalAction', False) else 'false'},"
            )
            operations.append(
                "        .prepare_commit_required = "
                f"{'true' if op.get('prepareCommitRequired', False) else 'false'},"
            )
            operations.append(f"        .safe_retry = {c_literal(op['safeRetry'])},")
            operations.append(f"        .description = {c_literal(op['description'])},")
            operations.append("    },")

    lines.append("/* Interned parameter-name tables shared by the operations below. */")
    lines += strings.definitions()
    lines.append("")
    lines += pairs.definitions()
    lines.append("")
    lines.append("const tempera_operation_spec TEMPERA_OPERATIONS[] = {")
    lines += operations
    lines += [
        "};",
        "const size_t TEMPERA_OPERATION_COUNT ="
        " sizeof(TEMPERA_OPERATIONS) / sizeof(TEMPERA_OPERATIONS[0]);",
        "",
    ]

    lines.append("const tempera_mcp_method_spec TEMPERA_MCP_METHODS[] = {")
    for method in surface["mcpGateway"]["methods"]:
        lines.append("    {")
        lines.append(f"        .id = {c_literal(snake_case(method['id']))},")
        lines.append(f"        .rpc = {c_literal(method['rpc'])},")
        lines.append(f"        .tool = {c_optional_literal(method.get('tool'))},")
        lines.append(f"        .description = {c_literal(method['description'])},")
        lines.append("    },")
    lines += [
        "};",
        "const size_t TEMPERA_MCP_METHOD_COUNT ="
        " sizeof(TEMPERA_MCP_METHODS) / sizeof(TEMPERA_MCP_METHODS[0]);",
        "",
        "const tempera_operation_spec *tempera_find_operation(const char *product,",
        "                                                    const char *id)",
        "{",
        "    size_t index;",
        "",
        "    if (product == NULL || id == NULL) {",
        "        return NULL;",
        "    }",
        "    for (index = 0; index < TEMPERA_OPERATION_COUNT; index++) {",
        "        if (strcmp(TEMPERA_OPERATIONS[index].product, product) == 0 &&",
        "            strcmp(TEMPERA_OPERATIONS[index].id, id) == 0) {",
        "            return &TEMPERA_OPERATIONS[index];",
        "        }",
        "    }",
        "    return NULL;",
        "}",
        "",
        "const tempera_product_spec *tempera_find_product(const char *key)",
        "{",
        "    size_t index;",
        "",
        "    if (key == NULL) {",
        "        return NULL;",
        "    }",
        "    for (index = 0; index < TEMPERA_PRODUCT_COUNT; index++) {",
        "        if (strcmp(TEMPERA_PRODUCTS[index].key, key) == 0) {",
        "            return &TEMPERA_PRODUCTS[index];",
        "        }",
        "    }",
        "    return NULL;",
        "}",
        "",
    ]
    return "\n".join(lines)


TARGETS = {
    "packages/c/include/tempera/surface.h": render_c_header,
    "packages/c/src/surface.c": render_c_source,
}
