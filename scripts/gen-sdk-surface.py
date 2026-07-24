#!/usr/bin/env python3
"""Generate the per-language SDK surface tables from surface.json.

surface.json is the single source of truth for the Tempera SDK: products,
audiences, scopes, environment targets, the error contract, and every typed
operation. This script renders it into:

  packages/typescript/src/surface.js
  packages/python/src/tempera_sdk/surface.py
  packages/rust/src/surface.rs

The generated files are committed; scripts/check-sdk-surface.py regenerates
them and fails on any diff, so the three packages cannot drift from the
manifest or from each other. See docs/ROLLOUT.md for the workflow.

Usage:
  python3 scripts/gen-sdk-surface.py           # write the three files
  python3 scripts/gen-sdk-surface.py --check   # exit 1 if any file is stale
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "surface.json"

HEADER = "GENERATED FROM surface.json by scripts/gen-sdk-surface.py -- DO NOT EDIT BY HAND."

VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
ID_RE = re.compile(r"^[a-z][a-zA-Z0-9]*$")
PATH_PARAM_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
PATH_TEMPLATE_RE = re.compile(
    r"^[a-z][a-zA-Z0-9]*(?:/(?:[a-z][a-zA-Z0-9]*|\*))*$"
)


def snake(camel: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", camel).lower()


def validate(surface: dict) -> list[str]:
    problems: list[str] = []
    ops = surface.get("operations", {})
    for product_key, product_ops in ops.items():
        if product_key not in surface["products"]:
            problems.append(f"operations for unknown product {product_key!r}")
        seen: set[str] = set()
        for op in product_ops:
            label = f"{product_key}.{op.get('id', '?')}"
            if not ID_RE.match(op.get("id", "")):
                problems.append(f"{label}: id must be lowerCamelCase")
            if not isinstance(op.get("upstreamOperationId"), str) or not op[
                "upstreamOperationId"
            ]:
                problems.append(f"{label}: upstreamOperationId must be generated")
            if op["id"] in seen:
                problems.append(f"{label}: duplicate operation id")
            seen.add(op["id"])
            if op.get("method") not in VALID_METHODS:
                problems.append(f"{label}: invalid method {op.get('method')!r}")
            path = op.get("path", "")
            if not path.startswith("/"):
                problems.append(f"{label}: path must start with '/'")
            declared = set(op.get("pathParams", []))
            in_path = set(PATH_PARAM_RE.findall(path))
            if declared != in_path:
                problems.append(
                    f"{label}: pathParams {sorted(declared)} != placeholders {sorted(in_path)}"
                )
            path_param_templates = op.get("pathParamTemplates", {})
            if not isinstance(path_param_templates, dict):
                problems.append(f"{label}: pathParamTemplates must be an object")
            else:
                unknown_templates = set(path_param_templates) - declared
                if unknown_templates:
                    problems.append(
                        f"{label}: pathParamTemplates names undeclared parameters "
                        f"{sorted(unknown_templates)}"
                    )
                for name, template in path_param_templates.items():
                    if (
                        not isinstance(template, str)
                        or not PATH_TEMPLATE_RE.fullmatch(template)
                        or "*" not in template
                    ):
                        problems.append(
                            f"{label}: pathParamTemplates[{name!r}] is not a safe "
                            "AIP resource pattern"
                        )
            desc = op.get("description", "")
            if not desc or not desc[0].isupper() or not desc.endswith("."):
                problems.append(
                    f"{label}: description must be a capitalized sentence ending with a period"
                )
            if op.get("auth") not in {"none", "account", "product", "introspectionSecret"}:
                problems.append(f"{label}: invalid auth {op.get('auth')!r}")
            scope = op.get("scope")
            if scope and scope not in surface["scopes"] and scope not in surface.get("scopeGaps", {}):
                problems.append(f"{label}: unregistered scope {scope!r} lacks an explicit scopeGaps entry")
            required_body = set(op.get("requiredBody", []))
            body = set(op.get("body", []))
            if not required_body.issubset(body):
                problems.append(f"{label}: requiredBody must be a subset of body")
    for product_key, product in surface["products"].items():
        if not ID_RE.match(product_key):
            problems.append(f"product key {product_key!r} must be lowerCamelCase")
        aud = product.get("audience")
        if aud is not None and aud not in surface["audiences"]:
            problems.append(f"product {product_key}: unregistered audience {aud!r}")
        if not product.get("envVar", "").startswith("TEMPERA_"):
            problems.append(f"product {product_key}: envVar must start with TEMPERA_")
        desc = product.get("description", "")
        if not desc.endswith("."):
            problems.append(f"product {product_key}: description must end with a period")
    for method in surface["mcpGateway"]["methods"]:
        desc = method.get("description", "")
        if not desc or not desc.endswith("."):
            problems.append(f"mcp {method.get('id')}: description must end with a period")
    if surface["defaultAudience"] not in surface["audiences"]:
        problems.append("defaultAudience is not a registered audience")
    for scope, gap in surface.get("scopeGaps", {}).items():
        if scope in surface["scopes"]:
            problems.append(f"scope gap {scope!r} is already registered")
        for field in ("owner", "reportedDate", "status", "migration"):
            if not gap.get(field):
                problems.append(f"scope gap {scope!r} lacks {field}")
    env_keys = None
    for env_name, target in surface["environments"].items():
        keys = sorted(target)
        if env_keys is None:
            env_keys = keys
        elif keys != env_keys:
            problems.append(f"environment {env_name} keys differ from the others")
    return problems


def js_string(value: str) -> str:
    return json.dumps(value)


def render_typescript(surface: dict) -> str:
    lines = [
        f"// {HEADER}",
        "// The SDK surface tables: products, audiences, scopes, environments,",
        "// the error contract, and every typed operation, shared verbatim with",
        "// the Python and Rust packages.",
        "",
    ]
    lines.append(
        "export const TEMPERA_SURFACE_VERSION = " + str(surface["version"]) + ";"
    )
    lines.append("")
    lines.append(
        "export const TEMPERA_AUDIENCES = Object.freeze("
        + json.dumps(surface["audiences"])
        + ");"
    )
    lines.append(f'export const DEFAULT_AUDIENCE = {js_string(surface["defaultAudience"])};')
    lines.append(
        "export const TEMPERA_SCOPES = Object.freeze(" + json.dumps(surface["scopes"]) + ");"
    )
    lines.append("")
    lines.append(
        "export const TEMPERA_ISSUER_PATHS = Object.freeze("
        + json.dumps(
            {
                "authorize": surface["issuer"]["authorizePath"],
                "token": surface["issuer"]["tokenPath"],
                "revoke": surface["issuer"]["revokePath"],
                "introspect": surface["issuer"]["introspectPath"],
                "mcp": surface["issuer"]["mcpPath"],
            },
            indent=2,
        )
        + ");"
    )
    lines.append("")
    lines.append("export const TEMPERA_ENVIRONMENTS = Object.freeze(")
    lines.append(json.dumps(surface["environments"], indent=2))
    lines.append(");")
    lines.append("")
    products = {
        key: {
            "name": product["name"],
            "repository": product["repository"],
            "envVar": product["envVar"],
            "audience": product["audience"],
            "description": product["description"],
        }
        for key, product in surface["products"].items()
    }
    lines.append("export const TEMPERA_PRODUCTS = Object.freeze(")
    lines.append(json.dumps(products, indent=2))
    lines.append(");")
    lines.append("")
    operations = {
        product_key: [
            {
                "id": op["id"],
                "upstreamOperationId": op["upstreamOperationId"],
                "method": op["method"],
                "path": op["path"],
                "auth": op["auth"],
                "pathParams": op.get("pathParams", []),
                "pathParamTemplates": op.get("pathParamTemplates", {}),
                "query": op.get("query", []),
                "body": op.get("body", []),
                "forbiddenBody": op.get("forbiddenBody", []),
                "requiredBody": op.get("requiredBody", []),
                "bodyDefaults": op.get("bodyDefaults", {}),
                "scope": op.get("scope"),
                "description": op["description"],
            }
            for op in ops
        ]
        for product_key, ops in surface["operations"].items()
    }
    lines.append("export const TEMPERA_OPERATIONS = Object.freeze(")
    lines.append(json.dumps(operations, indent=2))
    lines.append(");")
    lines.append("")
    lines.append("export const TEMPERA_MCP_GATEWAY = Object.freeze(")
    lines.append(json.dumps(surface["mcpGateway"], indent=2))
    lines.append(");")
    lines.append("")
    return "\n".join(lines)


def render_typescript_dts(surface: dict) -> str:
    lines = [
        f"// {HEADER}",
        "// Type declarations for the generated surface tables plus the typed",
        "// product-client interfaces used by createTemperaClient().",
        "",
    ]
    audiences = " | ".join(json.dumps(a) for a in surface["audiences"])
    scopes = " | ".join(json.dumps(s) for s in surface["scopes"])
    environments = " | ".join(json.dumps(e) for e in surface["environments"])
    product_keys = " | ".join(json.dumps(k) for k in surface["products"])
    lines += [
        f"export type TemperaAudience = {audiences};",
        f"export type TemperaScope = {scopes};",
        f"export type TemperaEnvironment = {environments};",
        f"export type TemperaProductKey = {product_keys};",
        "",
        "export declare const TEMPERA_SURFACE_VERSION: number;",
        "export declare const TEMPERA_AUDIENCES: readonly TemperaAudience[];",
        f"export declare const DEFAULT_AUDIENCE: {json.dumps(surface['defaultAudience'])};",
        "export declare const TEMPERA_SCOPES: readonly TemperaScope[];",
        "",
        "export type TemperaIssuerPaths = {",
        "  authorize: string;",
        "  token: string;",
        "  revoke: string;",
        "  introspect: string;",
        "  mcp: string;",
        "};",
        "export declare const TEMPERA_ISSUER_PATHS: Readonly<TemperaIssuerPaths>;",
        "",
        "export type TemperaEnvironmentTargets = {",
    ]
    for field in sorted(next(iter(surface["environments"].values()))):
        lines.append(f"  {field}: string;")
    lines += [
        "};",
        "export declare const TEMPERA_ENVIRONMENTS: Readonly<Record<TemperaEnvironment, TemperaEnvironmentTargets>>;",
        "",
        "export type TemperaProduct = {",
        "  name: string;",
        "  repository: string;",
        "  envVar: string;",
        "  audience: TemperaAudience | null;",
        "  description: string;",
        "};",
        "export declare const TEMPERA_PRODUCTS: Readonly<Record<TemperaProductKey, TemperaProduct>>;",
        "",
        "export type TemperaOperationSpec = {",
        "  id: string;",
        "  upstreamOperationId: string;",
        "  method: \"GET\" | \"POST\" | \"PUT\" | \"PATCH\" | \"DELETE\";",
        "  path: string;",
        "  auth: \"none\" | \"account\" | \"product\" | \"introspectionSecret\";",
        "  pathParams: readonly string[];",
        "  pathParamTemplates: Readonly<Record<string, string>>;",
        "  query: readonly string[];",
        "  body: readonly string[];",
        "  forbiddenBody: readonly string[];",
        "  requiredBody: readonly string[];",
        "  bodyDefaults: Readonly<Record<string, unknown>>;",
        "  scope: TemperaScope | null;",
        "  description: string;",
        "};",
        "export declare const TEMPERA_OPERATIONS: Readonly<Record<TemperaProductKey, readonly TemperaOperationSpec[]>>;",
        "",
        "export type TemperaMcpMethodSpec = { id: string; rpc: string; tool?: string; description: string };",
        "export declare const TEMPERA_MCP_GATEWAY: Readonly<{",
        "  description: string;",
        "  methods: readonly TemperaMcpMethodSpec[];",
        "  errorCodes: Readonly<Record<string, number>>;",
        "}>;",
        "",
        "export type TemperaOperationParams = Record<string, unknown>;",
        "export type TemperaOperationOptions = { headers?: Record<string, string>; bearer?: string };",
        "export type TemperaPassthroughOptions = {",
        "  method?: string;",
        "  body?: unknown;",
        "  query?: Record<string, unknown>;",
        "  headers?: Record<string, string>;",
        "  bearer?: string;",
        "};",
        "",
        "export type TemperaProductClientBase = TemperaProduct & {",
        "  key: TemperaProductKey;",
        "  /** Passthrough request for endpoints the surface tables do not cover yet. */",
        "  request(path: string, options?: TemperaPassthroughOptions): Promise<unknown>;",
        "};",
        "",
    ]
    for product_key, ops in surface["operations"].items():
        interface = product_key[0].upper() + product_key[1:] + "Client"
        lines.append(f"export interface {interface} extends TemperaProductClientBase {{")
        for op in ops:
            lines.append(f"  /** {op['description']} */")
            lines.append(
                f"  {op['id']}(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;"
            )
        lines.append("}")
        lines.append("")
    lines.append("export type PassthroughClient = TemperaProductClientBase;")
    lines.append("")
    return "\n".join(lines)


def render_python(surface: dict) -> str:
    def py(value) -> str:
        return repr(value) if not isinstance(value, (dict, list)) else json.dumps(value)

    lines = [
        f'"""{HEADER}',
        "",
        "The SDK surface tables: products, audiences, scopes, environments, the",
        "error contract, and every typed operation, shared verbatim with the",
        "TypeScript and Rust packages.",
        '"""',
        "",
        "SURFACE_VERSION = " + str(surface["version"]),
        "",
        "AUDIENCES = " + repr(tuple(surface["audiences"])),
        "DEFAULT_AUDIENCE = " + repr(surface["defaultAudience"]),
        "SCOPES = " + repr(tuple(surface["scopes"])),
        "",
        "ISSUER_PATHS = "
        + repr(
            {
                "authorize": surface["issuer"]["authorizePath"],
                "token": surface["issuer"]["tokenPath"],
                "revoke": surface["issuer"]["revokePath"],
                "introspect": surface["issuer"]["introspectPath"],
                "mcp": surface["issuer"]["mcpPath"],
            }
        ),
        "",
        "ENVIRONMENTS = " + json.dumps(surface["environments"], indent=4),
        "",
    ]
    products = {
        key: {
            "name": product["name"],
            "repository": product["repository"],
            "env_var": product["envVar"],
            "audience": product["audience"],
            "description": product["description"],
        }
        for key, product in surface["products"].items()
    }
    lines.append("PRODUCTS = " + json.dumps(products, indent=4))
    lines.append("")
    operations = {
        product_key: [
            {
                "id": snake(op["id"]),
                "upstream_operation_id": op["upstreamOperationId"],
                "method": op["method"],
                "path": op["path"],
                "auth": op["auth"],
                "path_params": op.get("pathParams", []),
                "path_param_templates": op.get("pathParamTemplates", {}),
                "query": op.get("query", []),
                "body": op.get("body", []),
                "forbidden_body": op.get("forbiddenBody", []),
                "required_body": op.get("requiredBody", []),
                "body_defaults": op.get("bodyDefaults", {}),
                "scope": op.get("scope"),
                "description": op["description"],
            }
            for op in ops
        ]
        for product_key, ops in surface["operations"].items()
    }
    lines.append("OPERATIONS = " + json.dumps(operations, indent=4))
    lines.append("")
    mcp = dict(surface["mcpGateway"])
    mcp["methods"] = [
        {**method, "id": snake(method["id"])} for method in surface["mcpGateway"]["methods"]
    ]
    lines.append("MCP_GATEWAY = " + json.dumps(mcp, indent=4))
    lines.append("")
    # json.dumps renders JSON literals; translate them to Python ones.
    text = "\n".join(lines)
    return (
        text.replace(": true", ": True")
        .replace(": false", ": False")
        .replace(": null", ": None")
    )


def rust_str(value: str | None) -> str:
    if value is None:
        return "None"
    return "Some(" + json.dumps(value) + ")"


def rust_str_slice(values: list[str]) -> str:
    return "&[" + ", ".join(json.dumps(value) for value in values) + "]"


def rust_str_pairs(values: dict[str, str]) -> str:
    pairs = ", ".join(
        f"({json.dumps(key)}, {json.dumps(value)})" for key, value in values.items()
    )
    return f"&[{pairs}]"


def render_rust(surface: dict) -> str:
    lines = [
        f"// {HEADER}",
        "// The SDK surface tables: products, audiences, scopes, environments,",
        "// the error contract, and every typed operation, shared verbatim with",
        "// the TypeScript and Python packages.",
        "",
        "pub const SURFACE_VERSION: u32 = " + str(surface["version"]) + ";",
        "",
        "pub const AUDIENCES: &[&str] = " + rust_str_slice(surface["audiences"]) + ";",
        "pub const DEFAULT_AUDIENCE: &str = " + json.dumps(surface["defaultAudience"]) + ";",
        "pub const SCOPES: &[&str] = " + rust_str_slice(surface["scopes"]) + ";",
        "",
        "pub const AUTHORIZE_PATH: &str = " + json.dumps(surface["issuer"]["authorizePath"]) + ";",
        "pub const TOKEN_PATH: &str = " + json.dumps(surface["issuer"]["tokenPath"]) + ";",
        "pub const REVOKE_PATH: &str = " + json.dumps(surface["issuer"]["revokePath"]) + ";",
        "pub const INTROSPECT_PATH: &str = " + json.dumps(surface["issuer"]["introspectPath"]) + ";",
        "pub const MCP_PATH: &str = " + json.dumps(surface["issuer"]["mcpPath"]) + ";",
        "",
        "#[derive(Debug, Clone, Copy, PartialEq, Eq)]",
        "pub struct EnvironmentTarget {",
        "    pub environment: &'static str,",
    ]
    env_fields = sorted(next(iter(surface["environments"].values())).keys())
    for field in env_fields:
        lines.append(f"    pub {snake(field)}: &'static str,")
    lines.append("}")
    lines.append("")
    lines.append("pub const ENVIRONMENTS: &[EnvironmentTarget] = &[")
    for env_name, target in surface["environments"].items():
        lines.append("    EnvironmentTarget {")
        lines.append(f"        environment: {json.dumps(env_name)},")
        for field in env_fields:
            lines.append(f"        {snake(field)}: {json.dumps(target[field])},")
        lines.append("    },")
    lines.append("];")
    lines.append("")
    lines.append("#[derive(Debug, Clone, Copy, PartialEq, Eq)]")
    lines.append("pub struct ProductSpec {")
    lines.append("    pub key: &'static str,")
    lines.append("    pub name: &'static str,")
    lines.append("    pub repository: &'static str,")
    lines.append("    pub env_var: &'static str,")
    lines.append("    pub audience: Option<&'static str>,")
    lines.append("    pub description: &'static str,")
    lines.append("}")
    lines.append("")
    lines.append("pub const PRODUCTS: &[ProductSpec] = &[")
    for key, product in surface["products"].items():
        lines.append("    ProductSpec {")
        lines.append(f"        key: {json.dumps(snake(key))},")
        lines.append(f"        name: {json.dumps(product['name'])},")
        lines.append(f"        repository: {json.dumps(product['repository'])},")
        lines.append(f"        env_var: {json.dumps(product['envVar'])},")
        lines.append(f"        audience: {rust_str(product['audience'])},")
        lines.append(f"        description: {json.dumps(product['description'])},")
        lines.append("    },")
    lines.append("];")
    lines.append("")
    lines.append("#[derive(Debug, Clone, Copy, PartialEq, Eq)]")
    lines.append("pub struct OperationSpec {")
    lines.append("    pub product: &'static str,")
    lines.append("    pub id: &'static str,")
    lines.append("    pub upstream_operation_id: &'static str,")
    lines.append("    pub method: &'static str,")
    lines.append("    pub path: &'static str,")
    lines.append("    pub auth: &'static str,")
    lines.append("    pub path_params: &'static [&'static str],")
    lines.append(
        "    pub path_param_templates: &'static [(&'static str, &'static str)],"
    )
    lines.append("    pub query: &'static [&'static str],")
    lines.append("    pub body: &'static [&'static str],")
    lines.append("    pub forbidden_body: &'static [&'static str],")
    lines.append("    pub required_body: &'static [&'static str],")
    lines.append("    pub body_defaults: &'static [(&'static str, &'static str)],")
    lines.append("    pub scope: Option<&'static str>,")
    lines.append("    pub description: &'static str,")
    lines.append("}")
    lines.append("")
    lines.append("pub const OPERATIONS: &[OperationSpec] = &[")
    for product_key, ops in surface["operations"].items():
        for op in ops:
            lines.append("    OperationSpec {")
            lines.append(f"        product: {json.dumps(snake(product_key))},")
            lines.append(f"        id: {json.dumps(snake(op['id']))},")
            lines.append(
                f"        upstream_operation_id: {json.dumps(op['upstreamOperationId'])},"
            )
            lines.append(f"        method: {json.dumps(op['method'])},")
            lines.append(f"        path: {json.dumps(op['path'])},")
            lines.append(f"        auth: {json.dumps(op['auth'])},")
            lines.append(f"        path_params: {rust_str_slice(op.get('pathParams', []))},")
            lines.append(
                "        path_param_templates: "
                f"{rust_str_pairs(op.get('pathParamTemplates', {}))},"
            )
            lines.append(f"        query: {rust_str_slice(op.get('query', []))},")
            lines.append(f"        body: {rust_str_slice(op.get('body', []))},")
            lines.append(f"        forbidden_body: {rust_str_slice(op.get('forbiddenBody', []))},")
            lines.append(f"        required_body: {rust_str_slice(op.get('requiredBody', []))},")
            defaults = op.get("bodyDefaults", {})
            pairs = ", ".join(
                f"({json.dumps(key)}, {json.dumps(str(value))})" for key, value in defaults.items()
            )
            lines.append(f"        body_defaults: &[{pairs}],")
            lines.append(f"        scope: {rust_str(op.get('scope'))},")
            lines.append(f"        description: {json.dumps(op['description'])},")
            lines.append("    },")
    lines.append("];")
    lines.append("")
    lines.append("#[derive(Debug, Clone, Copy, PartialEq, Eq)]")
    lines.append("pub struct McpMethodSpec {")
    lines.append("    pub id: &'static str,")
    lines.append("    pub rpc: &'static str,")
    lines.append("    pub tool: Option<&'static str>,")
    lines.append("    pub description: &'static str,")
    lines.append("}")
    lines.append("")
    lines.append("pub const MCP_METHODS: &[McpMethodSpec] = &[")
    for method in surface["mcpGateway"]["methods"]:
        lines.append("    McpMethodSpec {")
        lines.append(f"        id: {json.dumps(snake(method['id']))},")
        lines.append(f"        rpc: {json.dumps(method['rpc'])},")
        lines.append(f"        tool: {rust_str(method.get('tool'))},")
        lines.append(f"        description: {json.dumps(method['description'])},")
        lines.append("    },")
    lines.append("];")
    lines.append("")
    codes = surface["mcpGateway"]["errorCodes"]
    lines.append(f"pub const MCP_ERROR_PLAN_LIMIT: i64 = {codes['planLimit']};")
    lines.append(f"pub const MCP_ERROR_INVALID_REQUEST: i64 = {codes['invalidRequest']};")
    lines.append(f"pub const MCP_ERROR_METHOD_NOT_FOUND: i64 = {codes['methodNotFound']};")
    lines.append(f"pub const MCP_ERROR_INVALID_PARAMS: i64 = {codes['invalidParams']};")
    lines.append(f"pub const MCP_ERROR_INTERNAL: i64 = {codes['internalError']};")
    lines.append("")
    lines.append("/// Look up one operation by product key and snake_case operation id.")
    lines.append("pub fn find_operation(product: &str, id: &str) -> Option<&'static OperationSpec> {")
    lines.append("    OPERATIONS.iter().find(|op| op.product == product && op.id == id)")
    lines.append("}")
    lines.append("")
    lines.append("/// Look up one product by snake_case key.")
    lines.append("pub fn find_product(key: &str) -> Option<&'static ProductSpec> {")
    lines.append("    PRODUCTS.iter().find(|product| product.key == key)")
    lines.append("}")
    lines.append("")
    rendered = "\n".join(lines)
    formatted = subprocess.run(
        ["rustfmt", "--emit", "stdout", "--edition", "2024"],
        input=rendered,
        capture_output=True,
        text=True,
    )
    if formatted.returncode != 0:
        raise RuntimeError(f"rustfmt failed while generating Rust SDK surface: {formatted.stderr}")
    return formatted.stdout


TARGETS = {
    "packages/typescript/src/surface.js": render_typescript,
    "packages/typescript/src/surface.d.ts": render_typescript_dts,
    "packages/python/src/tempera_sdk/surface.py": render_python,
    "packages/rust/src/surface.rs": render_rust,
}


def main() -> int:
    surface = json.loads(SURFACE.read_text())
    problems = validate(surface)
    if problems:
        for problem in problems:
            print(f"surface.json invalid: {problem}", file=sys.stderr)
        return 1
    check = "--check" in sys.argv
    stale: list[str] = []
    for rel_path, renderer in TARGETS.items():
        rendered = renderer(surface)
        target = ROOT / rel_path
        if check:
            if not target.exists() or target.read_text() != rendered:
                stale.append(rel_path)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(rendered)
            print(f"wrote {rel_path}")
    if check and stale:
        for rel_path in stale:
            print(
                f"stale generated surface: {rel_path} (run python3 scripts/gen-sdk-surface.py)",
                file=sys.stderr,
            )
        return 1
    if check:
        print("generated surface tables are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
