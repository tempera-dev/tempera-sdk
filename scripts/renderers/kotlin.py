"""Kotlin renderer for the generated SDK surface tables.

Emits `packages/kotlin/src/main/kotlin/dev/tempera/sdk/Surface.kt`: the same
tables the Rust renderer emits (surface version, audiences, default audience,
scopes, issuer paths, environments, products, one flat operations array
carrying its `product`, MCP methods, MCP error codes, and the MCP protocol
version), in Kotlin's own naming and escaping dialect.

Three Kotlin-specific rules govern this module:

- Property names stay lowerCamelCase, exactly as `surface.json` declares them.
  Kotlin is a lowerCamel language, so unlike the Rust renderer nothing here is
  snake_cased -- neither the data-class properties nor the product keys and
  operation ids the runtime looks operations up by.
- `$` starts a template expression inside a Kotlin `"..."` literal, so
  `kotlin_literal` escapes it. `json.dumps` does not, and `surface.json`
  really does contain `${issuer}` (the MCP gateway description), which would
  otherwise be a compile error or a silent substitution.
- Kotlin's only numeric escape is `\\uXXXX`, a single UTF-16 code unit: there
  is no `\\f`, no `\\xNN`, and no astral escape. Control characters therefore
  use `\\uXXXX`, astral characters are emitted verbatim as UTF-8, and lone
  surrogates are rejected outright.

The operations table is emitted as fixed-size private objects rather than one
489-element list: every JVM method is capped at 64 KiB of bytecode and every
class at 65535 constant-pool entries, and one initializer holding 489
twenty-four-field constructions would risk both.
"""
from __future__ import annotations

from typing import Any

HEADER = "GENERATED FROM surface.json by scripts/gen-sdk-surface.py -- DO NOT EDIT BY HAND."

#: MCP protocol revision the runtimes speak. `surface.json` does not carry it,
#: so it is mirrored from the hand-written `packages/rust/src/mcp.rs` and
#: `packages/python/src/tempera_sdk/mcp.py`; a test asserts they agree.
MCP_PROTOCOL_VERSION = "2026-07-28"

#: Operations per generated private chunk object (see the module docstring).
OPERATIONS_PER_CHUNK = 25


def kotlin_literal(value: str) -> str:
    """Render one string as a Kotlin literal without rewriting source characters."""
    escaped: list[str] = []
    for character in value:
        if character == "\\":
            escaped.append("\\\\")
        elif character == '"':
            escaped.append('\\"')
        elif character == "$":
            # Unescaped, `$name` and `${expr}` are string templates.
            escaped.append("\\$")
        elif character == "\n":
            escaped.append("\\n")
        elif character == "\r":
            escaped.append("\\r")
        elif character == "\t":
            escaped.append("\\t")
        elif 0xD800 <= ord(character) <= 0xDFFF:
            raise ValueError("Kotlin literals cannot contain surrogate code points")
        elif ord(character) < 0x20 or ord(character) == 0x7F:
            escaped.append(f"\\u{ord(character):04x}")
        else:
            escaped.append(character)
    return '"' + "".join(escaped) + '"'


def kotlin_optional(value: str | None) -> str:
    return "null" if value is None else kotlin_literal(value)


def kotlin_strings(values: list[str]) -> str:
    if not values:
        return "emptyList()"
    return "listOf(" + ", ".join(kotlin_literal(value) for value in values) + ")"


def kotlin_pairs(values: dict[str, Any]) -> str:
    if not values:
        return "emptyList()"
    rendered = ", ".join(
        f"TemperaKeyValue({kotlin_literal(key)}, {kotlin_literal(str(value))})"
        for key, value in values.items()
    )
    return f"listOf({rendered})"


def _operation_literal(product_key: str, op: dict[str, Any]) -> list[str]:
    return [
        "        TemperaOperationSpec(",
        f"            product = {kotlin_literal(product_key)},",
        f"            id = {kotlin_literal(op['id'])},",
        f"            upstreamOperationId = {kotlin_literal(op['upstreamOperationId'])},",
        f"            method = {kotlin_literal(op['method'])},",
        f"            path = {kotlin_literal(op['path'])},",
        f"            auth = {kotlin_literal(op['auth'])},",
        f"            authAudience = {kotlin_optional(op.get('authAudience'))},",
        f"            pathParams = {kotlin_strings(op.get('pathParams', []))},",
        f"            pathParamTemplates = {kotlin_pairs(op.get('pathParamTemplates', {}))},",
        f"            query = {kotlin_strings(op.get('query', []))},",
        f"            requiredQuery = {kotlin_strings(op.get('requiredQuery', []))},",
        f"            headers = {kotlin_strings(op.get('headers', []))},",
        f"            requiredHeaders = {kotlin_strings(op.get('requiredHeaders', []))},",
        f"            body = {kotlin_strings(op.get('body', []))},",
        f"            forbiddenBody = {kotlin_strings(op.get('forbiddenBody', []))},",
        f"            requiredBody = {kotlin_strings(op.get('requiredBody', []))},",
        f"            bodyDefaults = {kotlin_pairs(op.get('bodyDefaults', {}))},",
        f"            requestBodyKind = {kotlin_literal(op.get('requestBodyKind', 'none'))},",
        f"            requestContentType = {kotlin_optional(op.get('requestContentType'))},",
        f"            scope = {kotlin_optional(op.get('scope'))},",
        f"            physicalAction = {str(op.get('physicalAction', False)).lower()},",
        f"            prepareCommitRequired = {str(op.get('prepareCommitRequired', False)).lower()},",
        f"            safeRetry = {kotlin_literal(op['safeRetry'])},",
        f"            description = {kotlin_literal(op['description'])},",
        "        ),",
    ]


def render(surface: dict[str, Any]) -> str:
    lines = [
        f"// {HEADER}",
        "// The SDK surface tables: products, audiences, scopes, environments,",
        "// the error contract, and every typed operation, shared verbatim with",
        "// the TypeScript, Python, Rust, and Swift packages.",
        "",
        "package dev.tempera.sdk",
        "",
        "/** One ordered [key]/[value] pair from a generated table. */",
        "public data class TemperaKeyValue(",
        "    public val key: String,",
        "    public val value: String,",
        ")",
        "",
        "/** One environment preset's base URLs. */",
        "public data class TemperaEnvironmentTarget(",
        "    /** The preset's name (`local`, `preview`, `staging`, `production`). */",
        "    public val environment: String,",
    ]
    env_fields = sorted(next(iter(surface["environments"].values())).keys())
    for field in env_fields:
        lines.append(f"    /** The `{field}` target for this environment. */")
        lines.append(f"    public val {field}: String,")
    lines.append(")")
    lines.append("")
    lines.append("/** One Tempera product's registry metadata. */")
    lines.append("public data class TemperaProductSpec(")
    lines.append("    /** lowerCamelCase registry key (e.g. `controlPlane`). */")
    lines.append("    public val key: String,")
    lines.append("    /** Human-readable product name. */")
    lines.append("    public val name: String,")
    lines.append("    /** Source repository. */")
    lines.append("    public val repository: String,")
    lines.append("    /** Environment variable carrying this product's base URL. */")
    lines.append("    public val envVar: String,")
    lines.append("    /** Token audience, when the product mints its own. */")
    lines.append("    public val audience: String?,")
    lines.append("    /** One-sentence product description. */")
    lines.append("    public val description: String,")
    lines.append(")")
    lines.append("")
    lines.append("/** One typed operation from `surface.json`. */")
    lines.append("public data class TemperaOperationSpec(")
    lines.append("    /** Owning product's registry key. */")
    lines.append("    public val product: String,")
    lines.append("    /** lowerCamelCase operation id, unique within the product. */")
    lines.append("    public val id: String,")
    lines.append("    /** Producer-side operation id this was generated from. */")
    lines.append("    public val upstreamOperationId: String,")
    lines.append("    /** HTTP method. */")
    lines.append("    public val method: String,")
    lines.append("    /** Path template, with `{placeholder}` path parameters. */")
    lines.append("    public val path: String,")
    lines.append(
        "    /** Auth kind: `none`, `account`, `product`, `oauthResource`, `introspectionSecret`. */"
    )
    lines.append("    public val auth: String,")
    lines.append("    /** Operation-pinned audience, for `oauthResource` auth. */")
    lines.append("    public val authAudience: String?,")
    lines.append("    /** Path parameter names, in no particular order. */")
    lines.append("    public val pathParams: List<String>,")
    lines.append("    /** AIP resource patterns a path parameter must match. */")
    lines.append("    public val pathParamTemplates: List<TemperaKeyValue>,")
    lines.append("    /** Declared query parameter names. */")
    lines.append("    public val query: List<String>,")
    lines.append("    /** Query parameters the producer requires. */")
    lines.append("    public val requiredQuery: List<String>,")
    lines.append("    /** Declared request header names. */")
    lines.append("    public val headers: List<String>,")
    lines.append("    /** Request headers the producer requires. */")
    lines.append("    public val requiredHeaders: List<String>,")
    lines.append("    /** Declared request-body field names. */")
    lines.append("    public val body: List<String>,")
    lines.append(
        "    /** Fields derived from the authenticated principal, which callers may not send. */"
    )
    lines.append("    public val forbiddenBody: List<String>,")
    lines.append("    /** Request-body fields the producer requires. */")
    lines.append("    public val requiredBody: List<String>,")
    lines.append("    /** Request-body defaults applied before caller values. */")
    lines.append("    public val bodyDefaults: List<TemperaKeyValue>,")
    lines.append("    /** Request body kind: `none`, `json`, or `binary`. */")
    lines.append("    public val requestBodyKind: String,")
    lines.append("    /** Content type for a `binary` request body. */")
    lines.append("    public val requestContentType: String?,")
    lines.append("    /** OAuth scope the operation requires. */")
    lines.append("    public val scope: String?,")
    lines.append("    /** Whether the operation drives a physical action. */")
    lines.append("    public val physicalAction: Boolean,")
    lines.append("    /** Whether the operation requires an MCP prepare/commit receipt pair. */")
    lines.append("    public val prepareCommitRequired: Boolean,")
    lines.append("    /** Retry classification: `read`, `idempotent`, or `none`. */")
    lines.append("    public val safeRetry: String,")
    lines.append("    /** One-sentence operation description. */")
    lines.append("    public val description: String,")
    lines.append(")")
    lines.append("")
    lines.append("/** One MCP gateway method. */")
    lines.append("public data class TemperaMcpMethodSpec(")
    lines.append("    /** lowerCamelCase method id. */")
    lines.append("    public val id: String,")
    lines.append("    /** JSON-RPC method name on the wire. */")
    lines.append("    public val rpc: String,")
    lines.append("    /** Builtin tool name, for tool-call methods. */")
    lines.append("    public val tool: String?,")
    lines.append("    /** One-sentence method description. */")
    lines.append("    public val description: String,")
    lines.append(")")
    lines.append("")
    lines.append("/** The MCP gateway's JSON-RPC error codes. */")
    lines.append("public data class TemperaMcpErrorCodes(")
    for code_name in (
        "planLimit",
        "invalidRequest",
        "methodNotFound",
        "invalidParams",
        "internalError",
    ):
        lines.append(f"    /** The `{code_name}` JSON-RPC error code. */")
        lines.append(f"    public val {code_name}: Int,")
    lines.append(")")
    lines.append("")
    lines.append("/** The generated Tempera SDK surface: one namespace for every table. */")
    lines.append("public object TemperaSurface {")
    lines.append("    /** `surface.json` schema version this table was generated from. */")
    lines.append(f"    public const val version: Int = {surface['version']}")
    lines.append("")
    lines.append("    /** Every registered token audience. */")
    lines.append(
        f"    public val audiences: List<String> = {kotlin_strings(surface['audiences'])}"
    )
    lines.append("    /** The audience used when a product declares none. */")
    lines.append(
        f"    public const val defaultAudience: String = {kotlin_literal(surface['defaultAudience'])}"
    )
    lines.append("    /** Every registered OAuth scope. */")
    lines.append(f"    public val scopes: List<String> = {kotlin_strings(surface['scopes'])}")
    lines.append("")
    issuer = surface["issuer"]
    lines.append("    /** The issuer's authorization endpoint path. */")
    lines.append(
        f"    public const val authorizePath: String = {kotlin_literal(issuer['authorizePath'])}"
    )
    lines.append("    /** The issuer's token endpoint path. */")
    lines.append(f"    public const val tokenPath: String = {kotlin_literal(issuer['tokenPath'])}")
    lines.append("    /** The issuer's revocation endpoint path. */")
    lines.append(
        f"    public const val revokePath: String = {kotlin_literal(issuer['revokePath'])}"
    )
    lines.append("    /** The issuer's introspection endpoint path. */")
    lines.append(
        f"    public const val introspectPath: String = {kotlin_literal(issuer['introspectPath'])}"
    )
    lines.append("    /** The unified MCP gateway path. */")
    lines.append(f"    public const val mcpPath: String = {kotlin_literal(issuer['mcpPath'])}")
    lines.append("")
    lines.append("    /** Every environment preset's base URLs. */")
    lines.append("    public val environments: List<TemperaEnvironmentTarget> = listOf(")
    for env_name, target in surface["environments"].items():
        lines.append("        TemperaEnvironmentTarget(")
        lines.append(f"            environment = {kotlin_literal(env_name)},")
        for field in env_fields:
            lines.append(f"            {field} = {kotlin_literal(target[field])},")
        lines.append("        ),")
    lines.append("    )")
    lines.append("")
    lines.append("    /** Every Tempera product's registry metadata. */")
    lines.append("    public val products: List<TemperaProductSpec> = listOf(")
    for key, product in surface["products"].items():
        lines.append("        TemperaProductSpec(")
        lines.append(f"            key = {kotlin_literal(key)},")
        lines.append(f"            name = {kotlin_literal(product['name'])},")
        lines.append(f"            repository = {kotlin_literal(product['repository'])},")
        lines.append(f"            envVar = {kotlin_literal(product['envVar'])},")
        lines.append(f"            audience = {kotlin_optional(product['audience'])},")
        lines.append(f"            description = {kotlin_literal(product['description'])},")
        lines.append("        ),")
    lines.append("    )")
    lines.append("")
    flat_operations = [
        (product_key, op)
        for product_key, ops in surface["operations"].items()
        for op in ops
    ]
    chunk_count = (len(flat_operations) + OPERATIONS_PER_CHUNK - 1) // OPERATIONS_PER_CHUNK
    lines.append("    /** Every typed operation, flattened across products. */")
    lines.append("    public val operations: List<TemperaOperationSpec> = buildOperations()")
    lines.append("")
    lines.append("    /** Every MCP gateway method. */")
    lines.append("    public val mcpMethods: List<TemperaMcpMethodSpec> = listOf(")
    for method in surface["mcpGateway"]["methods"]:
        lines.append("        TemperaMcpMethodSpec(")
        lines.append(f"            id = {kotlin_literal(method['id'])},")
        lines.append(f"            rpc = {kotlin_literal(method['rpc'])},")
        lines.append(f"            tool = {kotlin_optional(method.get('tool'))},")
        lines.append(f"            description = {kotlin_literal(method['description'])},")
        lines.append("        ),")
    lines.append("    )")
    lines.append("")
    codes = surface["mcpGateway"]["errorCodes"]
    lines.append("    /** The MCP gateway's JSON-RPC error codes. */")
    lines.append("    public val mcpErrorCodes: TemperaMcpErrorCodes = TemperaMcpErrorCodes(")
    lines.append(f"        planLimit = {codes['planLimit']},")
    lines.append(f"        invalidRequest = {codes['invalidRequest']},")
    lines.append(f"        methodNotFound = {codes['methodNotFound']},")
    lines.append(f"        invalidParams = {codes['invalidParams']},")
    lines.append(f"        internalError = {codes['internalError']},")
    lines.append("    )")
    lines.append("")
    lines.append("    /** MCP protocol revision the gateway and this SDK speak. */")
    lines.append(
        f"    public const val mcpProtocolVersion: String = {kotlin_literal(MCP_PROTOCOL_VERSION)}"
    )
    lines.append("    /** What the unified MCP gateway is. */")
    lines.append(
        f"    public const val mcpDescription: String = {kotlin_literal(surface['mcpGateway']['description'])}"
    )
    lines.append("")
    lines.append("    /** Look up one operation by product key and operation id. */")
    lines.append(
        "    public fun findOperation(product: String, id: String): TemperaOperationSpec? ="
    )
    lines.append("        operations.firstOrNull { it.product == product && it.id == id }")
    lines.append("")
    lines.append("    /** Every operation belonging to one product, in declaration order. */")
    lines.append(
        "    public fun operationsFor(product: String): List<TemperaOperationSpec> ="
    )
    lines.append("        operations.filter { it.product == product }")
    lines.append("")
    lines.append("    /** Look up one product by registry key. */")
    lines.append("    public fun findProduct(key: String): TemperaProductSpec? =")
    lines.append("        products.firstOrNull { it.key == key }")
    lines.append("")
    lines.append("    /** Look up one environment preset by name. */")
    lines.append(
        "    public fun findEnvironment(environment: String): TemperaEnvironmentTarget? ="
    )
    lines.append("        environments.firstOrNull { it.environment == environment }")
    lines.append("")
    lines.append("    /** Look up one MCP gateway method by id. */")
    lines.append("    public fun findMcpMethod(id: String): TemperaMcpMethodSpec? =")
    lines.append("        mcpMethods.firstOrNull { it.id == id }")
    lines.append("}")
    lines.append("")
    lines.append("// The operations table is split across private objects: every JVM method is")
    lines.append("// capped at 64 KiB of bytecode and every class at 65535 constant-pool")
    lines.append("// entries, and one 489-element initializer would risk both.")
    lines.append("private fun buildOperations(): List<TemperaOperationSpec> {")
    lines.append(
        f"    val all = ArrayList<TemperaOperationSpec>({len(flat_operations)})"
    )
    for index in range(chunk_count):
        lines.append(f"    all.addAll(TemperaOperationChunk{index}.items)")
    lines.append("    return all")
    lines.append("}")
    for index in range(chunk_count):
        chunk = flat_operations[
            index * OPERATIONS_PER_CHUNK : (index + 1) * OPERATIONS_PER_CHUNK
        ]
        lines.append("")
        lines.append(f"private object TemperaOperationChunk{index} {{")
        lines.append("    val items: List<TemperaOperationSpec> = listOf(")
        for product_key, op in chunk:
            lines.extend(_operation_literal(product_key, op))
        lines.append("    )")
        lines.append("}")
    lines.append("")
    return "\n".join(lines)


TARGETS = {"packages/kotlin/src/main/kotlin/dev/tempera/sdk/Surface.kt": render}
