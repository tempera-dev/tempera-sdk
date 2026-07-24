#!/usr/bin/env python3
"""The Tempera SDK uniformity gate.

Fails when the three language packages can drift apart:

1. surface.json invariants (validated by the generator).
2. The generated surface tables (TypeScript, TypeScript .d.ts, Python, Rust)
   must byte-match a fresh render of surface.json — so nobody hand-edits a
   generated file or forgets to regenerate after changing the manifest.
3. The generated Mintlify docs site (docs/site/, rendered by
   scripts/gen-sdk-docs.py from surface.json and docs/ROLLOUT.md) must
   byte-match a fresh render — stale docs fail the gate the same way.
4. The three package versions must be identical.
5. The hand-written mirror files must each define the uniform primitives
   (TemperaApiError, the unified client, the MCP client) so a package cannot
   quietly drop part of the surface.
6. No tracked file may mention a legacy product codename; the current
   product names (palette, tempo, cradle, remi, tempOS, temp.js) are the
   only ones allowed.
7. Every typed data-engine operation and scope must exactly match canonical
   OpenAPI metadata recorded in the committed contract lock.
8. Data Engine's exact MCP catalog must retain one reviewed expose/deny
   decision per authenticated operation without turning REST coverage into
   model exposure.
9. The signed Tempera evidence operations must exactly match the source-pinned
   Palette OpenAPI artifact and committed operation lock.
10. Every vendored producer contract must carry a complete immutable source
    lock whose generated digest matches the committed artifact.

Runtime conformance (every operation dispatching the right method, path, and
auth header) is asserted per-language by each package's own test suite, which
loops over the generated tables; `npm test` at the repo root runs all of it.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_ENGINE_OPERATION_LOCK = ROOT / "contracts" / "data-engine-openapi-operations.json"
DATA_ENGINE_MCP_ADMISSION = ROOT / "specs" / "data-engine-mcp-admission.json"
DATA_ENGINE_MCP_TOOLS = ROOT / "specs" / "data-engine-mcp-tools.json"

# Hand-written files must keep exposing the uniform primitives by these names.
REQUIRED_MARKERS = {
    "packages/typescript/src/errors.js": ["class TemperaApiError", "class TemperaMcpError", "normalizeErrorBody"],
    "packages/typescript/src/client.js": ["export function createTemperaClient"],
    "packages/typescript/src/mcp.js": ["class TemperaMcpClient", "MCP_PROTOCOL_VERSION"],
    "packages/typescript/src/auth.js": ["class TemperaAuth", "createPkcePair", "pkceChallengeS256"],
    "packages/python/src/tempera_sdk/errors.py": ["class TemperaApiError", "class TemperaMcpError", "def normalize_error_body"],
    "packages/python/src/tempera_sdk/client.py": ["class TemperaClient"],
    "packages/python/src/tempera_sdk/mcp.py": ["class TemperaMcpClient", "MCP_PROTOCOL_VERSION"],
    "packages/python/src/tempera_sdk/auth.py": ["class TemperaAuth", "def create_pkce_pair", "def pkce_challenge_s256"],
    "packages/rust/src/error.rs": ["pub struct TemperaApiError", "pub fn normalize_error_body"],
    "packages/rust/src/client.rs": ["pub struct TemperaClient", "pub struct RequestSpec"],
    "packages/rust/src/mcp.rs": ["MCP_PROTOCOL_VERSION"],
    "packages/rust/src/auth.rs": ["pub struct TemperaAuth", "pub fn pkce_challenge_s256"],
}

FORBIDDEN_README_EXAMPLES = [
    'issuerUrl: "https://api.tempera.dev"',
    'issuer_url="https://api.tempera.dev"',
    'TemperaAuth::new("https://api.tempera.dev")',
    'environment: "production"',
    'environment="production"',
]


def package_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    ts = json.loads((ROOT / "packages/typescript/package.json").read_text())
    versions["typescript"] = ts["version"]
    py = (ROOT / "packages/python/pyproject.toml").read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', py, re.MULTILINE)
    versions["python"] = match.group(1) if match else "?"
    cargo = (ROOT / "packages/rust/Cargo.toml").read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', cargo, re.MULTILINE)
    versions["rust"] = match.group(1) if match else "?"
    return versions


def validate_vendored_source_locks() -> list[str]:
    failures: list[str] = []
    for lock_path in sorted((ROOT / "specs").glob("*.source")):
        label = lock_path.relative_to(ROOT)
        try:
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            failures.append(f"{label}: invalid source lock: {error}")
            continue
        required = {
            "schema_version",
            "source_repo",
            "source_branch",
            "source_commit",
            "source_path",
            "source_blob_sha",
            "source_sha256",
            "generated_with",
            "generated_path",
            "generated_sha256",
        }
        missing = sorted(required - set(lock))
        if missing:
            failures.append(f"{label}: missing fields {missing}")
            continue
        if lock.get("schema_version") != 1:
            failures.append(f"{label}: schema_version must be 1")
        if lock.get("source_branch") != "main":
            failures.append(
                f"{label}: source_branch must be main, not "
                f"{lock.get('source_branch')!r}"
            )
        if re.fullmatch(r"[0-9a-f]{40}", str(lock.get("source_commit", ""))) is None:
            failures.append(f"{label}: source_commit is not a 40-character SHA")
        generated = ROOT / str(lock["generated_path"])
        try:
            digest = hashlib.sha256(generated.read_bytes()).hexdigest()
        except OSError as error:
            failures.append(f"{label}: cannot read generated artifact: {error}")
            continue
        if digest != lock.get("generated_sha256"):
            failures.append(
                f"{label}: generated_sha256 does not match {generated.relative_to(ROOT)}"
            )
    return failures


def route_identity(method: str, path: str) -> tuple[str, str]:
    """Match route templates structurally, independent of parameter spelling."""
    path = re.sub(r"^/v1/projects/\{[^}]+\}", "/v1/{parent}", path)
    return method, re.sub(r"\{[^}]+\}", "{}", path)


def validate_data_engine_openapi_bindings(surface: dict) -> list[str]:
    if not DATA_ENGINE_OPERATION_LOCK.exists():
        return ["missing contracts/data-engine-openapi-operations.json"]
    try:
        lock = json.loads(DATA_ENGINE_OPERATION_LOCK.read_text())
        operations = lock["operations"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        return [f"invalid data-engine OpenAPI operation lock: {error}"]
    indexed = {operation.get("sdkOperationId"): operation for operation in operations}
    if len(indexed) != len(operations):
        return ["data-engine OpenAPI operation lock has duplicate SDK operation IDs"]
    failures: list[str] = []
    required_provenance = {
        "source_repo",
        "source_branch",
        "source_commit",
        "source_path",
        "source_blob_sha",
        "source_sha256",
        "generated_with",
        "generated_sha256",
    }
    missing_provenance = sorted(required_provenance - set(lock))
    if missing_provenance:
        failures.append(
            "data-engine OpenAPI operation lock lacks provenance: "
            + ", ".join(missing_provenance)
        )
    expected_lock_values = {
        "schema_version": 3,
        "source_repo": "tempera-dev/data-engine",
        "source_branch": "main",
        "source_path": "api/openapi.yaml",
        "generated_with": "sync-data-engine-openapi.py@4",
    }
    for key, expected in expected_lock_values.items():
        if lock.get(key) != expected:
            failures.append(
                f"data-engine OpenAPI operation lock {key} {lock.get(key)!r} != {expected!r}"
            )
    if not re.fullmatch(r"[0-9a-f]{40}", str(lock.get("source_commit", ""))):
        failures.append("data-engine OpenAPI operation lock source_commit is not a 40-character SHA")
    if not re.fullmatch(r"[0-9a-f]{40,64}", str(lock.get("source_blob_sha", ""))):
        failures.append("data-engine OpenAPI operation lock source_blob_sha is not a Git object ID")
    for digest_key in ("source_sha256", "generated_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", str(lock.get(digest_key, ""))):
            failures.append(f"data-engine OpenAPI operation lock {digest_key} is not SHA-256")
    generated_bytes = (
        json.dumps(operations, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    if lock.get("generated_sha256") != hashlib.sha256(generated_bytes).hexdigest():
        failures.append("data-engine OpenAPI operation lock generated_sha256 does not match operations")
    surface_operations = surface.get("operations", {}).get("dataEngine", [])
    surface_ids = {operation.get("id") for operation in surface_operations}
    lock_ids = set(indexed)
    for missing in sorted(lock_ids - surface_ids):
        failures.append(f"dataEngine.{missing}: lock operation is missing from SDK surface")
    for operation in surface_operations:
        label = f"dataEngine.{operation.get('id', '?')}"
        authoritative = indexed.get(operation.get("id"))
        if authoritative is None:
            failures.append(f"{label}: absent from data-engine OpenAPI operation lock")
            continue
        if operation.get("method") != authoritative.get("method"):
            failures.append(f"{label}: method differs from {authoritative.get('operationId')}")
        if route_identity(operation.get("method", ""), operation.get("path", "")) != route_identity(
            authoritative.get("method", ""), authoritative.get("path", "")
        ):
            failures.append(f"{label}: path differs from {authoritative.get('operationId')}")
        expected_audience = None if operation.get("auth") == "none" else "data-engine"
        if authoritative.get("audience") != expected_audience:
            failures.append(
                f"{label}: audience {expected_audience!r} differs from canonical "
                f"{authoritative.get('audience')!r}"
            )
        if operation.get("scope") != authoritative.get("requiredScope"):
            failures.append(
                f"{label}: scope {operation.get('scope')!r} differs from canonical "
                f"{authoritative.get('requiredScope')!r}"
            )
    return failures


def validate_data_engine_mcp_contracts() -> list[str]:
    """Bind curated model exposure to exact producer artifacts and auth truth."""
    failures: list[str] = []
    try:
        operation_lock = json.loads(DATA_ENGINE_OPERATION_LOCK.read_text())
        admission_bytes = DATA_ENGINE_MCP_ADMISSION.read_bytes()
        tools_bytes = DATA_ENGINE_MCP_TOOLS.read_bytes()
        admission = json.loads(admission_bytes)
        tools = json.loads(tools_bytes)
    except (OSError, json.JSONDecodeError) as error:
        return [f"invalid Data Engine MCP contract artifact: {error}"]

    expected_sources = {
        DATA_ENGINE_MCP_ADMISSION: "api/mcp-admission.json",
        DATA_ENGINE_MCP_TOOLS: "api/mcp-tools.json",
    }
    for artifact, source_path in expected_sources.items():
        source_lock_path = artifact.with_name(artifact.name + ".source")
        try:
            source_lock = json.loads(source_lock_path.read_text())
        except (OSError, json.JSONDecodeError) as error:
            failures.append(f"invalid {source_lock_path.relative_to(ROOT)}: {error}")
            continue
        expected = {
            "schema_version": 1,
            "source_repo": "tempera-dev/data-engine",
            "source_branch": "main",
            "source_commit": operation_lock.get("source_commit"),
            "source_path": source_path,
            "generated_with": "sync-data-engine-mcp-contracts.py@1+verbatim",
            "generated_path": artifact.relative_to(ROOT).as_posix(),
        }
        for key, value in expected.items():
            if source_lock.get(key) != value:
                failures.append(
                    f"{source_lock_path.relative_to(ROOT)} {key} "
                    f"{source_lock.get(key)!r} != {value!r}"
                )
        content = artifact.read_bytes()
        content_digest = hashlib.sha256(content).hexdigest()
        if source_lock.get("source_sha256") != content_digest:
            failures.append(f"{artifact.relative_to(ROOT)} differs from source SHA-256")
        if source_lock.get("generated_sha256") != content_digest:
            failures.append(f"{artifact.relative_to(ROOT)} generated SHA-256 is stale")

    if admission.get("schema") != "data-engine.mcp-admission.v1":
        failures.append("Data Engine MCP admission schema is not v1")
    if tools.get("schema") != "data-engine.mcp-tools.v1":
        failures.append("Data Engine MCP tools schema is not v1")
    records = admission.get("operations")
    tool_list = tools.get("tools")
    if not isinstance(records, list) or not isinstance(tool_list, list):
        return [*failures, "Data Engine MCP artifacts lack operation/tool arrays"]
    by_operation = {record.get("operation_id"): record for record in records}
    by_tool = {tool.get("name"): tool for tool in tool_list}
    if len(by_operation) != len(records):
        failures.append("Data Engine MCP admission has duplicate operation IDs")
    if len(by_tool) != len(tool_list):
        failures.append("Data Engine MCP tools artifact has duplicate tool names")
    expected_operations = {
        operation.get("operationId"): operation
        for operation in operation_lock.get("operations", [])
        if operation.get("operationId") != "health.get"
    }
    if set(by_operation) != set(expected_operations):
        failures.append("Data Engine MCP decisions do not cover exact authenticated SDK operations")
    exposed = {
        operation_id
        for operation_id, record in by_operation.items()
        if record.get("decision") == "expose"
    }
    denied = {
        operation_id
        for operation_id, record in by_operation.items()
        if record.get("decision") == "deny"
    }
    if exposed != set(by_tool):
        failures.append("Data Engine exposed decisions differ from exact tools artifact")
    if len(exposed) != 36 or exposed | denied != set(by_operation) or exposed & denied:
        failures.append(
            "Data Engine MCP admission must classify every authenticated operation "
            "while preserving the reviewed 36-tool exposure boundary"
        )
    for operation_id, authoritative in expected_operations.items():
        record = by_operation.get(operation_id) or {}
        if record.get("required_scope") != authoritative.get("requiredScope"):
            failures.append(f"{operation_id}: MCP admission scope differs from OpenAPI auth metadata")
        if record.get("effect") not in {"safe", "read", "write", "destructive"}:
            failures.append(f"{operation_id}: MCP admission effect is invalid")
        fixtures = record.get("schema_fixtures") or {}
        for field in ("input_sha256", "output_sha256"):
            if re.fullmatch(r"[0-9a-f]{64}", str(fixtures.get(field, ""))) is None:
                failures.append(f"{operation_id}: missing {field} fixture digest")
    expected_tools_digest = admission.get("policy", {}).get("mcp_tools_artifact", {}).get("sha256")
    if expected_tools_digest != hashlib.sha256(tools_bytes).hexdigest():
        failures.append("Data Engine MCP admission does not bind the vendored tools artifact")
    return failures


def main() -> int:
    failures: list[str] = []

    # 1: every vendored route and request binding must reproduce from OpenAPI.
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/sync-openapi-surface.py"), "--check"],
        capture_output=True,
        text=True,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode != 0:
        failures.append("surface.json differs from vendored OpenAPI request bindings")

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check-upstream-drift.py")],
        capture_output=True,
        text=True,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode != 0:
        failures.append("vendored upstream operation coverage is not strict")

    # 2 + 3: manifest invariants and generated-table drift.
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/gen-sdk-surface.py"), "--check"],
        capture_output=True,
        text=True,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode != 0:
        failures.append("generated surface tables are stale or surface.json is invalid")

    # 3: generated docs-site drift (same regenerate-and-diff pattern).
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/gen-sdk-docs.py"), "--check"],
        capture_output=True,
        text=True,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode != 0:
        failures.append(
            "generated docs site (docs/site/) is stale (run python3 scripts/gen-sdk-docs.py)"
        )

    # 3b: signed evaluation evidence is a real Palette server surface. Its
    # operation lock binds the vendored generated OpenAPI bytes, source
    # revision, operation IDs, request/receipt schemas, and SDK methods.
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/sync-palette-eval-openapi.py"),
            "--check",
        ],
        capture_output=True,
        text=True,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode != 0:
        failures.append(
            "Palette evaluation OpenAPI lock is stale or differs from its source pin"
        )

    # 3c: reference data may retain reserved production targets, but public
    # quickstarts must not present those targets as generally available.
    readme = (ROOT / "README.md").read_text()
    for forbidden in FORBIDDEN_README_EXAMPLES:
        if forbidden in readme:
            failures.append(
                f"README.md: public example presents reserved production access: {forbidden!r}"
            )

    # 4: one SDK version across the three packages.
    versions = package_versions()
    if len(set(versions.values())) != 1:
        failures.append(f"package versions differ: {versions}")

    # 5: uniform primitives present in every hand-written mirror file.
    for rel_path, markers in REQUIRED_MARKERS.items():
        path = ROOT / rel_path
        if not path.exists():
            failures.append(f"missing file: {rel_path}")
            continue
        text = path.read_text()
        for marker in markers:
            if marker not in text:
                failures.append(f"{rel_path}: missing marker {marker!r}")

    # 5b: the hand-written TypeScript public type (index.d.ts) must expose a
    # typed client field for every product in the surface — this file is not
    # generated, so a new product can be wired into the runtime and surface.d.ts
    # yet silently dropped from the public TemperaClient type. Guard against it.
    surface = json.loads((ROOT / "surface.json").read_text())
    failures.extend(validate_vendored_source_locks())
    failures.extend(validate_data_engine_openapi_bindings(surface))
    failures.extend(validate_data_engine_mcp_contracts())
    index_dts = (ROOT / "packages/typescript/src/index.d.ts").read_text()
    client_type = re.search(r"export type TemperaClient = \{(.*?)\n\};", index_dts, re.DOTALL)
    if client_type is None:
        failures.append("packages/typescript/src/index.d.ts: TemperaClient type not found")
    else:
        for product_key in surface["products"]:
            if not re.search(rf"\n\s+{re.escape(product_key)}:\s", client_type.group(1)):
                failures.append(
                    f"packages/typescript/src/index.d.ts: TemperaClient type is missing "
                    f"the {product_key!r} product client field"
                )

    # 6: no legacy product codenames in any tracked file. The products are
    # palette, tempo, cradle, remi, tempOS, and temp.js — their pre-rename
    # codenames must not resurface in code, docs, or the manifest.
    legacy = re.compile(r"beater|beatbox", re.IGNORECASE)
    tracked = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, cwd=ROOT
    ).stdout.splitlines()
    for tracked_path in tracked:
        if tracked_path == "scripts/check-sdk-surface.py":
            continue  # this file necessarily spells the denied pattern
        path = ROOT / tracked_path
        try:
            text = path.read_text()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            if legacy.search(line):
                failures.append(
                    f"{tracked_path}:{line_number}: legacy product codename; use the current product names"
                )

    if failures:
        for failure in failures:
            print(f"SDK surface check failed: {failure}", file=sys.stderr)
        return 1
    print(f"SDK surface check passed (version {versions['typescript']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
