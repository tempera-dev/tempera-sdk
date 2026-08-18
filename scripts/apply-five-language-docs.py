#!/usr/bin/env python3
"""Apply the five-language documentation and canonical-gate migration once."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one replacement, found {count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    old_example = '''def operation_example(surface: dict, product_key: str, op: dict) -> list[str]:
    names = example_param_names(op)
    ts_attr = product_key
    py_attr = snake_attr(product_key)
    rust_product = snake(product_key)
    op_snake = snake(op["id"])

    if names:
        ts_args = "{\\n" + "".join(f'  {name}: "<{name}>",\\n' for name in names) + "}"
        ts_code = f"const result = await client.{ts_attr}.{op['id']}({ts_args});"
        py_args = "{\\n" + "".join(f'    "{name}": "<{name}>",\\n' for name in names) + "}"
        py_code = f"result = client.{py_attr}.{op_snake}({py_args})"
        rust_args = "&[\\n" + "".join(f'    ("{name}", "<{name}>".into()),\\n' for name in names) + "]"
    else:
        ts_code = f"const result = await client.{ts_attr}.{op['id']}();"
        py_code = f"result = client.{py_attr}.{op_snake}()"
        rust_args = "&[]"
    rust_code = (
        f'let spec = client.build_request("{rust_product}", "{op_snake}", {rust_args})?;\\n'
        "// Send spec.method / spec.full_url() / spec.headers / spec.body_json\\n"
        "// with your own HTTP client."
    )
    return code_group(
        [
            ("typescript", "TypeScript", ts_code),
            ("python", "Python", py_code),
            ("rust", "Rust", rust_code),
        ]
    )
'''
    new_example = '''def operation_example(surface: dict, product_key: str, op: dict) -> list[str]:
    names = example_param_names(op)
    ts_attr = product_key
    py_attr = snake_attr(product_key)
    rust_product = snake(product_key)
    op_snake = snake(op["id"])
    path_names = [name for name in op.get("pathParams", []) if name in names]
    query_names = [name for name in op.get("query", []) if name in names]
    body_names = [name for name in op.get("body", []) if name in names]

    if names:
        ts_args = "{\\n" + "".join(f'  {name}: "<{name}>",\\n' for name in names) + "}"
        ts_code = f"const result = await client.{ts_attr}.{op['id']}({ts_args});"
        py_args = "{\\n" + "".join(f'    "{name}": "<{name}>",\\n' for name in names) + "}"
        py_code = f"result = client.{py_attr}.{op_snake}({py_args})"
        rust_args = "&[\\n" + "".join(f'    ("{name}", "<{name}>".into()),\\n' for name in names) + "]"
        go_params = "map[string]any{\\n" + "".join(
            f'    "{name}": "<{name}>",\\n' for name in names
        ) + "}"
    else:
        ts_code = f"const result = await client.{ts_attr}.{op['id']}();"
        py_code = f"result = client.{py_attr}.{op_snake}()"
        rust_args = "&[]"
        go_params = "map[string]any{}"
    rust_code = (
        f'let spec = client.build_request("{rust_product}", "{op_snake}", {rust_args})?;\\n'
        "// Send spec.method / spec.full_url() / spec.headers / spec.body_json\\n"
        "// with your own HTTP client."
    )
    go_code = (
        f'spec, err := client.BuildRequest("{product_key}", "{op["id"]}", {go_params})\\n'
        "if err != nil {\\n"
        "    return err\\n"
        "}\\n"
        "_ = spec // Or call client.Do with the same product, operation, and params."
    )

    if path_names:
        c_path = "const tempera_param path_params[] = {\\n" + "".join(
            f'    {{"{name}", "<{name}>"}},\\n' for name in path_names
        ) + "};\\nconst size_t path_param_count = sizeof(path_params) / sizeof(path_params[0]);"
        c_path_ref = "path_params"
    else:
        c_path = "const tempera_param *path_params = NULL;\\nconst size_t path_param_count = 0;"
        c_path_ref = "path_params"
    query_value = "&".join(f"{name}=<{name}>" for name in query_names)
    query_literal = json.dumps(query_value) if query_value else "NULL"
    body_value = json.dumps(
        {name: f"<{name}>" for name in body_names},
        separators=(",", ":"),
    ) if body_names else None
    body_literal = json.dumps(body_value) if body_value is not None else "NULL"
    c_code = (
        f"{c_path}\\n"
        f"const char *query_string = {query_literal};\\n"
        f"const char *body_json = {body_literal};\\n"
        "tempera_request_spec request;\\n"
        "int rc = tempera_build_request(\\n"
        "    base_url, bearer,\\n"
        f'    "{product_key}", "{op["id"]}",\\n'
        f"    {c_path_ref}, path_param_count,\\n"
        "    query_string, body_json, &request);\\n"
        "if (rc != TEMPERA_OK) {\\n"
        "    /* Handle bounded request-construction failure. */\\n"
        "}"
    )
    return code_group(
        [
            ("typescript", "TypeScript", ts_code),
            ("python", "Python", py_code),
            ("rust", "Rust", rust_code),
            ("go", "Go", go_code),
            ("c", "C", c_code),
        ]
    )
'''
    replace_once("scripts/gen-sdk-docs.py", old_example, new_example)

    replace_once(
        "scripts/gen-sdk-docs.py",
        '''    lines.append(
        f"- **Call as:** TypeScript `client.{product_key}.{op['id']}()` · "
        f"Python `client.{snake_attr(product_key)}.{op_snake}()` · "
        f'Rust `build_request("{rust_product}", "{op_snake}", params)`'
    )
''',
        '''    lines.append(
        f"- **Call as:** TypeScript `client.{product_key}.{op['id']}()` · "
        f"Python `client.{snake_attr(product_key)}.{op_snake}()` · "
        f'Rust `build_request("{rust_product}", "{op_snake}", params)` · '
        f'Go `BuildRequest("{product_key}", "{op["id"]}", params)` · '
        f'C `tempera_build_request(..., "{product_key}", "{op["id"]}", ...)`'
    )
''',
    )

    replace_once(
        "scripts/gen-sdk-docs.py",
        '''        "The Tempera SDK exposes **one uniform surface in three languages** — TypeScript",
        "(`@tempera/sdk`), Python (`tempera-sdk`), and Rust (`tempera-sdk`). The primary",
''',
        '''        "The Tempera SDK exposes **one contract in five languages** — TypeScript",
        "(`@tempera/sdk`), Python and Rust (`tempera-sdk`), Go (`tempera.dev/sdk-go`),",
        "and a transport-neutral C11 ABI. The primary",
''',
    )

    old_index_group = '''    lines += code_group(
        [
            ("typescript", "TypeScript", ts_code),
            ("python", "Python", py_code),
            ("rust", "Rust", rust_code),
        ]
    )
    lines += [
        "Method naming is mechanical across the languages: the SDK's lowerCamelCase",
        "method id in TypeScript (`listTraces`), snake_case in Python (`list_traces`),",
        'and `build_request(product, "list_traces", params)` in Rust. Parameters use wire',
        "names (snake_case) in every language.",
'''
    new_index_group = '''    go_code = (
        "// Module access and environment values are supplied during onboarding.\\n"
        'import ("context"; "os"; tempera "tempera.dev/sdk-go")\\n'
        "ctx := context.Background()\\n"
        "apiKey := os.Getenv(\"TEMPERA_API_KEY\")\\n"
        "client := tempera.NewClient()\\n"
        "client.BaseURLs[\"controlPlane\"] = os.Getenv(\"TEMPERA_CONTROL_PLANE_URL\")\\n"
        "client.BaseURLs[\"tempo\"] = os.Getenv(\"TEMPERA_TEMPO_URL\")\\n"
        "client.BaseURLs[\"palette\"] = os.Getenv(\"TEMPERA_PALETTE_URL\")\\n"
        "client.Bearers[\"tempo\"] = apiKey\\n"
        "client.Bearers[\"palette\"] = apiKey\\n"
        "var session map[string]any\\n"
        'err := client.Do(ctx, "tempo", "createSession", map[string]any{"url": "https://example.com"}, &session)\\n'
        "if err != nil { return err }"
    )
    c_code = (
        "/* The C11 SDK builds bounded request specs; supply your HTTP transport. */\\n"
        "const tempera_param params[] = {{\"url\", \"https://example.com\"}};\\n"
        "tempera_request_spec request;\\n"
        "int rc = tempera_build_request(\\n"
        "    tempo_url, api_key, \"tempo\", \"createSession\",\\n"
        "    NULL, 0, NULL, \"{\\\"url\\\":\\\"https://example.com\\\"}\", &request);\\n"
        "if (rc != TEMPERA_OK) { /* handle fail-closed build error */ }"
    )
    lines += code_group(
        [
            ("typescript", "TypeScript", ts_code),
            ("python", "Python", py_code),
            ("rust", "Rust", rust_code),
            ("go", "Go", go_code),
            ("c", "C", c_code),
        ]
    )
    lines += [
        "Method naming is mechanical: lowerCamelCase in TypeScript and Go",
        "(`listTraces`), snake_case in Python and Rust (`list_traces`), and the",
        "canonical manifest operation id in C. Requests always emit producer wire names;",
        "Go/C callers supply already-provisioned bearer credentials to their transport layer.",
'''
    replace_once("scripts/gen-sdk-docs.py", old_index_group, new_index_group)

    replace_once(
        "scripts/gen-sdk-docs.py",
        '''        "1. **Explicit override** — `baseUrls.<product>` (TypeScript),",
        "   `base_urls[\\\"<product>\\\"]` (Python), or `with_base_url(\\\"<product>\\\", url)` (Rust).",
''',
        '''        "1. **Explicit override** — `baseUrls.<product>` (TypeScript),",
        "   `base_urls[\\\"<product>\\\"]` (Python), `with_base_url(\\\"<product>\\\", url)` (Rust),",
        "   `BaseURLs[\\\"<product>\\\"]` (Go), or the `base_url` argument (C).",
''',
    )
    replace_once(
        "scripts/gen-sdk-docs.py",
        '''        "Trailing slashes on configured base URLs are trimmed in every language.",
''',
        '''        "Trailing slashes are trimmed by the TypeScript, Python, Rust, and Go clients;",
        "C callers pass the base URL to each bounded request build.",
''',
    )

    replace_once(
        "README.md",
        "One versioned SDK contract in TypeScript, Python, and Rust.",
        "One versioned SDK contract in TypeScript, Python, Rust, Go, and C.",
    )
    replace_once(
        "README.md",
        '''Python is the same surface in snake_case (`client.control_plane.discovery()`,
`client.palette.list_traces(...)`); Rust builds `RequestSpec`s for your HTTP
client (`client.build_request("palette", "list_traces", &params)`) since the
crate ships no HTTP stack. Parameters use wire names (snake_case) in every
language.
''',
        '''Python exposes snake_case methods (`client.palette.list_traces(...)`). Rust and C
are transport-neutral request builders; Go provides both `BuildRequest` and a
standard-library HTTP executor. TypeScript and Go use lowerCamel operation ids,
Python and Rust use snake_case method ids, and C accepts the canonical manifest
operation id. Every request emits the producer's canonical wire names.
''',
    )
    replace_once(
        "README.md",
        "all three languages. MCP JSON-RPC errors raise `TemperaMcpError`",
        "TypeScript, Python, Rust, and Go; the transport-neutral C ABI returns bounded build codes. MCP JSON-RPC errors raise `TemperaMcpError`",
    )
    replace_once(
        "README.md",
        "typed product covering every operation with tabbed TS/Python/Rust examples.",
        "typed product covering every operation with tabbed TypeScript/Python/Rust/Go/C examples.",
    )
    replace_once(
        "README.md",
        "diff (surface tables and docs site), one version across the three packages,",
        "diff (surface tables and docs site), one version across all five packages,",
    )

    replace_once(
        "surface.json",
        "Every product, audience, scope, environment target, error-normalization rule, and typed operation in the TypeScript, Python, and Rust packages is generated from this file.",
        "Every product, audience, scope, environment target, error-normalization rule, and typed operation in the TypeScript, Python, Rust, Go, and C packages is generated from this file.",
    )

    replace_once(
        "scripts/check-sdk-surface.py",
        "Fails when the three language packages can drift apart:",
        "Fails when the five language packages can drift apart:",
    )
    replace_once(
        "scripts/check-sdk-surface.py",
        "2. The generated surface tables (TypeScript, TypeScript .d.ts, Python, Rust)",
        "2. The generated surface tables (TypeScript, TypeScript .d.ts, Python, Rust, Go, C)",
    )
    replace_once(
        "scripts/check-sdk-surface.py",
        "4. The three package versions must be identical.",
        "4. The five package versions must be identical.",
    )
    replace_once(
        "scripts/check-sdk-surface.py",
        '''    "packages/rust/src/auth.rs": ["pub struct TemperaAuth", "pub fn pkce_challenge_s256"],
}
''',
        '''    "packages/rust/src/auth.rs": ["pub struct TemperaAuth", "pub fn pkce_challenge_s256"],
    "packages/go/client.go": ["type APIError struct", "func NewClient", "func (c *Client) BuildRequest"],
    "packages/go/browser.go": ["type BrowserTask struct", "func CreateBrowserTask"],
    "packages/c/include/tempera/tempera.h": ["tempera_request_spec", "tempera_browser_task"],
    "packages/c/src/tempera.c": ["tempera_build_request", "tempera_browser_task_attach"],
}
''',
    )
    replace_once(
        "scripts/check-sdk-surface.py",
        '''    versions["rust"] = match.group(1) if match else "?"
    return versions
''',
        '''    versions["rust"] = match.group(1) if match else "?"
    go = (ROOT / "packages/go/client.go").read_text()
    match = re.search(r'const Version = "([^"]+)"', go)
    versions["go"] = match.group(1) if match else "?"
    c_header = (ROOT / "packages/c/include/tempera/surface_gen.h").read_text()
    match = re.search(r'#define TEMPERA_SDK_VERSION "([^"]+)"', c_header)
    versions["c"] = match.group(1) if match else "?"
    return versions
''',
    )
    replace_once(
        "scripts/check-sdk-surface.py",
        '''    # 3: generated docs-site drift (same regenerate-and-diff pattern).
''',
        '''    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/gen-sdk-go-c.py"), "--check"],
        capture_output=True,
        text=True,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode != 0:
        failures.append("generated Go/C surface tables are stale")

    # 3: generated docs-site drift (same regenerate-and-diff pattern).
''',
    )
    replace_once(
        "scripts/check-sdk-surface.py",
        "# 4: one SDK version across the three packages.",
        "# 4: one SDK version across all five packages.",
    )

    package = ROOT / "package.json"
    package_text = package.read_text(encoding="utf-8")
    package_text = package_text.replace(
        "python3 scripts/test-aip-conformance.py &&",
        "python3 scripts/test-aip-conformance.py && python3 scripts/test-five-language-docs.py &&",
        1,
    )
    package.write_text(package_text, encoding="utf-8")


if __name__ == "__main__":
    main()
