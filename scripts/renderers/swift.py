"""Swift renderer for the generated SDK surface tables.

Emits `packages/swift/Sources/TemperaSDK/Surface.swift`: the same tables the
Rust renderer emits (surface version, audiences, default audience, scopes,
issuer paths, environments, products, one flat operations array carrying its
`product`, MCP methods, MCP error codes, and the MCP protocol version), in
Swift's own naming and escaping dialect.

Two Swift-specific rules govern this module:

- Property names stay lowerCamelCase, exactly as `surface.json` declares them.
  Swift is a lowerCamel language, so unlike the Rust renderer nothing here is
  snake_cased -- neither the struct fields nor the product keys and operation
  ids the runtime looks operations up by.
- String literals are escaped by `swift_literal`, never by `json.dumps`.
  `json.dumps` emits `\\uXXXX` surrogate pairs for astral characters, which
  Swift reads as two invalid Unicode scalars, and it does not reject lone
  surrogates. See `scripts/test-gen-sdk-surface-mobile.py` for the round-trip
  tests that hold this honest.

The operations table is emitted as fixed-size private chunks rather than one
489-element literal: Swift's type checker is superlinear in array-literal
size, and one literal that big turns a two-second build into a two-minute one.
"""
from __future__ import annotations

from typing import Any

HEADER = "GENERATED FROM surface.json by scripts/gen-sdk-surface.py -- DO NOT EDIT BY HAND."

#: MCP protocol revision the runtimes speak. `surface.json` does not carry it,
#: so it is mirrored from the hand-written `packages/rust/src/mcp.rs` and
#: `packages/python/src/tempera_sdk/mcp.py`; a test asserts they agree.
MCP_PROTOCOL_VERSION = "2026-07-28"

#: Operations per generated private chunk (see the module docstring).
OPERATIONS_PER_CHUNK = 40


def swift_literal(value: str) -> str:
    """Render one string as a Swift literal without rewriting source characters.

    Swift interpolates `\\(`, so escaping backslashes makes interpolation
    inert; `$` is an ordinary character in Swift and is left alone. Astral
    characters are emitted verbatim as UTF-8 rather than as surrogate escapes,
    because `\\u{...}` takes a Unicode scalar and a surrogate is not one.
    """
    escaped: list[str] = []
    for character in value:
        if character == "\\":
            escaped.append("\\\\")
        elif character == '"':
            escaped.append('\\"')
        elif character == "\n":
            escaped.append("\\n")
        elif character == "\r":
            escaped.append("\\r")
        elif character == "\t":
            escaped.append("\\t")
        elif 0xD800 <= ord(character) <= 0xDFFF:
            raise ValueError("Swift literals cannot contain surrogate code points")
        elif ord(character) < 0x20 or ord(character) == 0x7F:
            escaped.append(f"\\u{{{ord(character):x}}}")
        else:
            escaped.append(character)
    return '"' + "".join(escaped) + '"'


def swift_optional(value: str | None) -> str:
    return "nil" if value is None else swift_literal(value)


def swift_strings(values: list[str]) -> str:
    if not values:
        return "[]"
    return "[" + ", ".join(swift_literal(value) for value in values) + "]"


def swift_pairs(values: dict[str, Any]) -> str:
    if not values:
        return "[]"
    rendered = ", ".join(
        f"TemperaKeyValue(key: {swift_literal(key)}, value: {swift_literal(str(value))})"
        for key, value in values.items()
    )
    return f"[{rendered}]"


def swift_struct(name: str, doc: str, fields: list[tuple[str, str, str]]) -> list[str]:
    """Emit one public struct plus a public memberwise initializer.

    Swift synthesizes the memberwise initializer at `internal` visibility, so a
    public struct that consumers outside the package construct needs it spelled
    out.
    """
    lines = [f"/// {doc}", f"public struct {name}: Sendable, Equatable {{"]
    for field_name, field_type, field_doc in fields:
        lines.append(f"    /// {field_doc}")
        lines.append(f"    public let {field_name}: {field_type}")
    lines.append("")
    lines.append(f"    /// Create one `{name}`.")
    lines.append("    public init(")
    for index, (field_name, field_type, _) in enumerate(fields):
        comma = "," if index < len(fields) - 1 else ""
        lines.append(f"        {field_name}: {field_type}{comma}")
    lines.append("    ) {")
    for field_name, _, _ in fields:
        lines.append(f"        self.{field_name} = {field_name}")
    lines.append("    }")
    lines.append("}")
    lines.append("")
    return lines


OPERATION_FIELDS: list[tuple[str, str, str]] = [
    ("product", "String", "Owning product's registry key."),
    ("id", "String", "lowerCamelCase operation id, unique within the product."),
    ("upstreamOperationId", "String", "Producer-side operation id this was generated from."),
    ("method", "String", "HTTP method."),
    ("path", "String", "Path template, with `{placeholder}` path parameters."),
    (
        "auth",
        "String",
        "Auth kind: `none`, `account`, `product`, `oauthResource`, `introspectionSecret`.",
    ),
    ("authAudience", "String?", "Operation-pinned audience, for `oauthResource` auth."),
    ("pathParams", "[String]", "Path parameter names."),
    ("pathParamTemplates", "[TemperaKeyValue]", "AIP resource patterns a path parameter must match."),
    ("query", "[String]", "Declared query parameter names."),
    ("requiredQuery", "[String]", "Query parameters the producer requires."),
    ("headers", "[String]", "Declared request header names."),
    ("requiredHeaders", "[String]", "Request headers the producer requires."),
    ("body", "[String]", "Declared request-body field names."),
    (
        "forbiddenBody",
        "[String]",
        "Fields derived from the authenticated principal, which callers may not send.",
    ),
    ("requiredBody", "[String]", "Request-body fields the producer requires."),
    ("bodyDefaults", "[TemperaKeyValue]", "Request-body defaults applied before caller values."),
    ("requestBodyKind", "String", "Request body kind: `none`, `json`, or `binary`."),
    ("requestContentType", "String?", "Content type for a `binary` request body."),
    ("scope", "String?", "OAuth scope the operation requires."),
    ("physicalAction", "Bool", "Whether the operation drives a physical action."),
    (
        "prepareCommitRequired",
        "Bool",
        "Whether the operation requires an MCP prepare/commit receipt pair.",
    ),
    ("safeRetry", "String", "Retry classification: `read`, `idempotent`, or `none`."),
    ("description", "String", "One-sentence operation description."),
]

MCP_ERROR_CODE_FIELDS = (
    "planLimit",
    "invalidRequest",
    "methodNotFound",
    "invalidParams",
    "internalError",
)


def _operation_literal(product_key: str, op: dict[str, Any]) -> list[str]:
    return [
        "    TemperaOperationSpec(",
        f"        product: {swift_literal(product_key)},",
        f"        id: {swift_literal(op['id'])},",
        f"        upstreamOperationId: {swift_literal(op['upstreamOperationId'])},",
        f"        method: {swift_literal(op['method'])},",
        f"        path: {swift_literal(op['path'])},",
        f"        auth: {swift_literal(op['auth'])},",
        f"        authAudience: {swift_optional(op.get('authAudience'))},",
        f"        pathParams: {swift_strings(op.get('pathParams', []))},",
        f"        pathParamTemplates: {swift_pairs(op.get('pathParamTemplates', {}))},",
        f"        query: {swift_strings(op.get('query', []))},",
        f"        requiredQuery: {swift_strings(op.get('requiredQuery', []))},",
        f"        headers: {swift_strings(op.get('headers', []))},",
        f"        requiredHeaders: {swift_strings(op.get('requiredHeaders', []))},",
        f"        body: {swift_strings(op.get('body', []))},",
        f"        forbiddenBody: {swift_strings(op.get('forbiddenBody', []))},",
        f"        requiredBody: {swift_strings(op.get('requiredBody', []))},",
        f"        bodyDefaults: {swift_pairs(op.get('bodyDefaults', {}))},",
        f"        requestBodyKind: {swift_literal(op.get('requestBodyKind', 'none'))},",
        f"        requestContentType: {swift_optional(op.get('requestContentType'))},",
        f"        scope: {swift_optional(op.get('scope'))},",
        f"        physicalAction: {str(op.get('physicalAction', False)).lower()},",
        f"        prepareCommitRequired: {str(op.get('prepareCommitRequired', False)).lower()},",
        f"        safeRetry: {swift_literal(op['safeRetry'])},",
        f"        description: {swift_literal(op['description'])}",
        "    ),",
    ]


def render(surface: dict[str, Any]) -> str:
    env_fields = sorted(next(iter(surface["environments"].values())).keys())
    lines = [
        f"// {HEADER}",
        "// The SDK surface tables: products, audiences, scopes, environments,",
        "// the error contract, and every typed operation, shared verbatim with",
        "// the TypeScript, Python, Rust, and Kotlin packages.",
        "",
    ]
    lines += swift_struct(
        "TemperaKeyValue",
        "One ordered `key`/`value` pair from a generated table.",
        [("key", "String", "The pair's key."), ("value", "String", "The pair's value.")],
    )
    lines += swift_struct(
        "TemperaEnvironmentTarget",
        "One environment preset's base URLs.",
        [
            (
                "environment",
                "String",
                "The preset's name (`local`, `preview`, `staging`, `production`).",
            )
        ]
        + [
            (field, "String", f"The `{field}` target for this environment.")
            for field in env_fields
        ],
    )
    lines += swift_struct(
        "TemperaProductSpec",
        "One Tempera product's registry metadata.",
        [
            ("key", "String", "lowerCamelCase registry key (e.g. `controlPlane`)."),
            ("name", "String", "Human-readable product name."),
            ("repository", "String", "Source repository."),
            ("envVar", "String", "Environment variable carrying this product's base URL."),
            ("audience", "String?", "Token audience, when the product mints its own."),
            ("description", "String", "One-sentence product description."),
        ],
    )
    lines += swift_struct(
        "TemperaOperationSpec",
        "One typed operation from `surface.json`.",
        OPERATION_FIELDS,
    )
    lines += swift_struct(
        "TemperaMcpMethodSpec",
        "One MCP gateway method.",
        [
            ("id", "String", "lowerCamelCase method id."),
            ("rpc", "String", "JSON-RPC method name on the wire."),
            ("tool", "String?", "Builtin tool name, for tool-call methods."),
            ("description", "String", "One-sentence method description."),
        ],
    )
    lines += swift_struct(
        "TemperaMcpErrorCodes",
        "The MCP gateway's JSON-RPC error codes.",
        [(name, "Int", f"The `{name}` JSON-RPC error code.") for name in MCP_ERROR_CODE_FIELDS],
    )

    lines.append("/// The generated Tempera SDK surface: one namespace for every table.")
    lines.append("public enum TemperaSurface {")
    lines.append("    /// `surface.json` schema version this table was generated from.")
    lines.append(f"    public static let version: Int = {surface['version']}")
    lines.append("")
    lines.append("    /// Every registered token audience.")
    lines.append(f"    public static let audiences: [String] = {swift_strings(surface['audiences'])}")
    lines.append("    /// The audience used when a product declares none.")
    lines.append(
        f"    public static let defaultAudience: String = {swift_literal(surface['defaultAudience'])}"
    )
    lines.append("    /// Every registered OAuth scope.")
    lines.append(f"    public static let scopes: [String] = {swift_strings(surface['scopes'])}")
    lines.append("")
    issuer = surface["issuer"]
    lines.append("    /// The issuer's authorization endpoint path.")
    lines.append(
        f"    public static let authorizePath: String = {swift_literal(issuer['authorizePath'])}"
    )
    lines.append("    /// The issuer's token endpoint path.")
    lines.append(f"    public static let tokenPath: String = {swift_literal(issuer['tokenPath'])}")
    lines.append("    /// The issuer's revocation endpoint path.")
    lines.append(f"    public static let revokePath: String = {swift_literal(issuer['revokePath'])}")
    lines.append("    /// The issuer's introspection endpoint path.")
    lines.append(
        f"    public static let introspectPath: String = {swift_literal(issuer['introspectPath'])}"
    )
    lines.append("    /// The unified MCP gateway path.")
    lines.append(f"    public static let mcpPath: String = {swift_literal(issuer['mcpPath'])}")
    lines.append("")
    lines.append("    /// Every environment preset's base URLs.")
    lines.append("    public static let environments: [TemperaEnvironmentTarget] = [")
    for env_name, target in surface["environments"].items():
        lines.append("        TemperaEnvironmentTarget(")
        lines.append(f"            environment: {swift_literal(env_name)},")
        for index, field in enumerate(env_fields):
            comma = "," if index < len(env_fields) - 1 else ""
            lines.append(f"            {field}: {swift_literal(target[field])}{comma}")
        lines.append("        ),")
    lines.append("    ]")
    lines.append("")
    lines.append("    /// Every Tempera product's registry metadata.")
    lines.append("    public static let products: [TemperaProductSpec] = [")
    for key, product in surface["products"].items():
        lines.append("        TemperaProductSpec(")
        lines.append(f"            key: {swift_literal(key)},")
        lines.append(f"            name: {swift_literal(product['name'])},")
        lines.append(f"            repository: {swift_literal(product['repository'])},")
        lines.append(f"            envVar: {swift_literal(product['envVar'])},")
        lines.append(f"            audience: {swift_optional(product['audience'])},")
        lines.append(f"            description: {swift_literal(product['description'])}")
        lines.append("        ),")
    lines.append("    ]")
    lines.append("")
    flat_operations = [
        (product_key, op)
        for product_key, ops in surface["operations"].items()
        for op in ops
    ]
    chunk_count = (len(flat_operations) + OPERATIONS_PER_CHUNK - 1) // OPERATIONS_PER_CHUNK
    lines.append("    /// Every typed operation, flattened across products.")
    lines.append("    public static let operations: [TemperaOperationSpec] =")
    for index in range(chunk_count):
        joiner = "        " if index == 0 else "        + "
        lines.append(f"{joiner}temperaOperationChunk{index}")
    lines.append("")
    lines.append("    /// Every MCP gateway method.")
    lines.append("    public static let mcpMethods: [TemperaMcpMethodSpec] = [")
    for method in surface["mcpGateway"]["methods"]:
        lines.append("        TemperaMcpMethodSpec(")
        lines.append(f"            id: {swift_literal(method['id'])},")
        lines.append(f"            rpc: {swift_literal(method['rpc'])},")
        lines.append(f"            tool: {swift_optional(method.get('tool'))},")
        lines.append(f"            description: {swift_literal(method['description'])}")
        lines.append("        ),")
    lines.append("    ]")
    lines.append("")
    codes = surface["mcpGateway"]["errorCodes"]
    lines.append("    /// The MCP gateway's JSON-RPC error codes.")
    lines.append("    public static let mcpErrorCodes = TemperaMcpErrorCodes(")
    for index, name in enumerate(MCP_ERROR_CODE_FIELDS):
        comma = "," if index < len(MCP_ERROR_CODE_FIELDS) - 1 else ""
        lines.append(f"        {name}: {codes[name]}{comma}")
    lines.append("    )")
    lines.append("")
    lines.append("    /// MCP protocol revision the gateway and this SDK speak.")
    lines.append(
        f"    public static let mcpProtocolVersion: String = {swift_literal(MCP_PROTOCOL_VERSION)}"
    )
    lines.append("    /// What the unified MCP gateway is.")
    lines.append(
        "    public static let mcpDescription: String = "
        + swift_literal(surface["mcpGateway"]["description"])
    )
    lines.append("")
    lines.append("    /// Look up one operation by product key and operation id.")
    lines.append(
        "    public static func findOperation(product: String, id: String) -> TemperaOperationSpec? {"
    )
    lines.append("        operations.first { $0.product == product && $0.id == id }")
    lines.append("    }")
    lines.append("")
    lines.append("    /// Every operation belonging to one product, in declaration order.")
    lines.append("    public static func operationsFor(product: String) -> [TemperaOperationSpec] {")
    lines.append("        operations.filter { $0.product == product }")
    lines.append("    }")
    lines.append("")
    lines.append("    /// Look up one product by registry key.")
    lines.append("    public static func findProduct(key: String) -> TemperaProductSpec? {")
    lines.append("        products.first { $0.key == key }")
    lines.append("    }")
    lines.append("")
    lines.append("    /// Look up one environment preset by name.")
    lines.append(
        "    public static func findEnvironment(_ environment: String) -> TemperaEnvironmentTarget? {"
    )
    lines.append("        environments.first { $0.environment == environment }")
    lines.append("    }")
    lines.append("")
    lines.append("    /// Look up one MCP gateway method by id.")
    lines.append("    public static func findMcpMethod(id: String) -> TemperaMcpMethodSpec? {")
    lines.append("        mcpMethods.first { $0.id == id }")
    lines.append("    }")
    lines.append("}")
    lines.append("")
    lines.append("// The operations table is split into fixed-size chunks; one 489-element")
    lines.append("// array literal is superlinear for the Swift type checker.")
    for index in range(chunk_count):
        chunk = flat_operations[
            index * OPERATIONS_PER_CHUNK : (index + 1) * OPERATIONS_PER_CHUNK
        ]
        lines.append("")
        lines.append(f"private let temperaOperationChunk{index}: [TemperaOperationSpec] = [")
        for product_key, op in chunk:
            lines.extend(_operation_literal(product_key, op))
        lines.append("]")
    lines.append("")
    return "\n".join(lines)


TARGETS = {"packages/swift/Sources/TemperaSDK/Surface.swift": render}
