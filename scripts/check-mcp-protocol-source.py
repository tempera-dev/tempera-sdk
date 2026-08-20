#!/usr/bin/env python3
"""Verify the exact producer-owned MCP protocol receipt and SDK projection."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "contracts" / "mcp-protocol.source.json"
PROTOCOL_VERSION = "2026-07-28"
PACKAGE_VERSION = "0.13.0"
SOURCE_REPO = "tempera-dev/tempera-mcp"
SOURCE_BRANCH = "main"
SOURCE_COMMIT = "99ac544fcfbc500f212906a61cf6c72c2cc16723"
SOURCE_TREE = "d5abd3b96268e9e2d5cc8db091eb302e7c434dc2"
OFFICIAL_SDK_COMMIT = "830e088d733c7964c806a2305760dd8deb30dff9"
OFFICIAL_SDK_REPO = "modelcontextprotocol/rust-sdk"
OFFICIAL_SDK_TREE = "3a48da49ebd214faa55c22add021cc6d76568759"
REQUIRED_HEADERS = ["accept", "content-type", "mcp-protocol-version", "mcp-method"]
REQUIRED_META = [
    "io.modelcontextprotocol/protocolVersion",
    "io.modelcontextprotocol/clientInfo",
    "io.modelcontextprotocol/clientCapabilities",
]
HEX40 = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")
SOURCE_FILES = {
    "Cargo.lock": {
        "blob": "b6e12d291192a2572b0867058fa4eb0eae4750cd",
        "sha256": "29709ac905c0aa69c2450a4575a828bdd5f4213a4140cbac2fdb80eb51d52fdd",
    },
    "Cargo.toml": {
        "blob": "a2ca4d7deefbe05db66f40eae88dd4301cd79eb4",
        "sha256": "2b1f8dc35713eb92776e2a2302a74e30ad9f07e6d69d339c91076d8220c12dc3",
    },
    "rust-toolchain.toml": {
        "blob": "bf5eb1a847a7af9c1eca62a7a0b68796dded2812",
        "sha256": "5a357c16adbb4740c3264b315c59c4882c286072146d7198757096197b498c52",
    },
    "contracts/mcp-tools-v1.json": {
        "blob": "094200abdebb27756e4ff7221831d8dc19af37ca",
        "sha256": "d01cee7c8d00b10287b514c9183d22aeb27abd52432ef950f5bafaa2df0aa7c4",
    },
    "docs/protocol-compatibility.md": {
        "blob": "d3cae178a10883a33326975a3a02b8aa69f93cdb",
        "sha256": "f638d38077fcb8fb6569708f780f43c19d9a922dede15e2bc129692774d1657f",
    },
    "scripts/framework-comparison.mjs": {
        "blob": "782e75ee98cff658894807a93b282dba53b3b663",
        "sha256": "b693d651286eab2d7ff13297cabe5a597ba6b0d9a0a3bf93cb32add0f7fb2b9b",
    },
    "src/app.rs": {
        "blob": "0e4a05e3e914f5c501454c3f6b5f99650f94cc9b",
        "sha256": "9166ea219b33890b5d1728e79a58c4f3abe02eeed3d8c9d0b341b433c912e7a0",
    },
    "src/client.rs": {
        "blob": "929ce9d9984a817cff9f3fba1544c6eb4cef637e",
        "sha256": "ed86069465cd5d9a0f7bdf7085db8cd211b21edb0329f5212823cd6f4c786c93",
    },
}
OFFICIAL_SDK_FILES = {
    "crates/rmcp/src/model.rs": {
        "blob": "7ee93d82db807f4a02186eea6f8354be20de9654",
        "sha256": "678226c7217ab232bdcef3207caca9a71939f6294efd4e2d977bca3385ea912a",
    },
    "crates/rmcp/src/model/mrtr.rs": {
        "blob": "8dac9a39137d4178c83a4c3549165aefd50dce29",
        "sha256": "462fc966dd35ce4a1deba3812fca4b2a2a7e614e50617acde0ab98c665d5612a",
    },
    "crates/rmcp/tests/test_deserialization.rs": {
        "blob": "8570770153f48265f012f57139a0d6b11e4915fa",
        "sha256": "f24700d7ba3a5c96679f20c2bbc73529ce496acb9ed61a7bed94a3d9da31cf46",
    },
    "crates/rmcp/tests/test_result_type_wire.rs": {
        "blob": "d5f201532c62fc39c396751a7f164adb2acd28b6",
        "sha256": "24ab645b42604fd8dae5fe8824089821a880a37ee1eb14725650bf0647f497e0",
    },
}


def fail(message: str) -> None:
    raise ValueError(message)


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        fail(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def normalized_repo(url: str) -> str:
    value = url.removesuffix(".git").rstrip("/")
    if value.startswith("git@github.com:"):
        value = "https://github.com/" + value.removeprefix("git@github.com:")
    return value.removeprefix("https://github.com/")


def load_lock(path: Path = LOCK_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail("MCP protocol receipt must be an object")
    return value


def validate_lock(lock: dict[str, Any]) -> None:
    expected = {
        "schema_version": "tempera.sdk-mcp-protocol-source.v1",
        "source_repo": SOURCE_REPO,
        "source_branch": SOURCE_BRANCH,
        "source_commit": SOURCE_COMMIT,
        "source_tree": SOURCE_TREE,
        "protocol_version": PROTOCOL_VERSION,
        "lifecycle": "stateless-server-discover",
        "official_rust_sdk_repo": OFFICIAL_SDK_REPO,
        "official_rust_sdk_commit": OFFICIAL_SDK_COMMIT,
        "official_rust_sdk_tree": OFFICIAL_SDK_TREE,
        "required_headers": REQUIRED_HEADERS,
        "conditional_headers": {"tools/call": ["mcp-name"]},
        "required_meta": REQUIRED_META,
        "tool_result_contract": {
            "complete_result_type": "complete",
            "input_required_result_type": "input_required",
            "tool_error_field": "isError",
        },
    }
    for field, value in expected.items():
        if lock.get(field) != value:
            fail(f"MCP protocol receipt has invalid {field}: {lock.get(field)!r}")
    for field in ("source_commit", "source_tree"):
        if HEX40.fullmatch(str(lock.get(field, ""))) is None:
            fail(f"MCP protocol receipt {field} must be a lowercase 40-character SHA")
    files = lock.get("source_files")
    if not isinstance(files, dict) or set(files) != set(SOURCE_FILES):
        fail("MCP protocol receipt source_files must equal the required producer set")
    for source_path, identity in files.items():
        if not isinstance(identity, dict):
            fail(f"MCP protocol receipt identity for {source_path} must be an object")
        if HEX40.fullmatch(str(identity.get("blob", ""))) is None:
            fail(f"MCP protocol receipt blob for {source_path} is invalid")
        if HEX64.fullmatch(str(identity.get("sha256", ""))) is None:
            fail(f"MCP protocol receipt SHA-256 for {source_path} is invalid")
    if files != SOURCE_FILES:
        fail("MCP protocol receipt source file identities do not match the reviewed producer set")
    official_files = lock.get("official_rust_sdk_source_files")
    if official_files != OFFICIAL_SDK_FILES:
        fail("MCP protocol receipt official SDK identities do not match the reviewed source set")


def validate_sdk(root: Path = ROOT) -> None:
    python_manifest = tomllib.loads(
        (root / "packages/python/pyproject.toml").read_text(encoding="utf-8")
    )
    rust_manifest = tomllib.loads(
        (root / "packages/rust/Cargo.toml").read_text(encoding="utf-8")
    )
    typescript_manifest = json.loads(
        (root / "packages/typescript/package.json").read_text(encoding="utf-8")
    )
    python_lock = tomllib.loads(
        (root / "packages/python/uv.lock").read_text(encoding="utf-8")
    )
    rust_lock = tomllib.loads(
        (root / "packages/rust/Cargo.lock").read_text(encoding="utf-8")
    )

    def locked_version(lock: dict[str, Any]) -> str | None:
        for package in lock.get("package", []):
            if package.get("name") == "tempera-sdk":
                return package.get("version")
        return None

    versions = {
        "python": python_manifest.get("project", {}).get("version"),
        "python-lock": locked_version(python_lock),
        "rust": rust_manifest.get("package", {}).get("version"),
        "rust-lock": locked_version(rust_lock),
        "typescript": typescript_manifest.get("version"),
    }
    if set(versions.values()) != {PACKAGE_VERSION}:
        fail(f"SDK MCP package versions must all equal {PACKAGE_VERSION}: {versions}")

    surface = json.loads((root / "surface.json").read_text(encoding="utf-8"))
    gateway = surface.get("mcpGateway")
    if not isinstance(gateway, dict):
        fail("SDK surface omits mcpGateway")
    methods = gateway.get("methods")
    if not isinstance(methods, list):
        fail("SDK mcpGateway methods must be an array")
    wires = [(method.get("id"), method.get("rpc")) for method in methods]
    if wires != [
        ("discover", "server/discover"),
        ("ping", "ping"),
        ("listTools", "tools/list"),
        ("callTool", "tools/call"),
        ("whoami", "tools/call"),
        ("status", "tools/call"),
    ]:
        fail(f"SDK mcpGateway surface has stale methods: {wires!r}")
    if "eleven tempera_* fabric verbs" not in str(gateway.get("description", "")):
        fail("SDK mcpGateway surface does not declare the exact eleven-tool fabric")

    checks = {
        "packages/python/src/tempera_sdk/mcp.py": [
            'MCP_PROTOCOL_VERSION = "2026-07-28"',
            'client_version: str = "0.13.0"',
            'self.rpc("server/discover", {})',
            '"io.modelcontextprotocol/clientCapabilities"',
            "text/event-stream",
            "MCP_METHOD_HEADER",
            "MCP_NAME_HEADER",
            'result.get("resultType") == "input_required"',
            'result.get("isError") is True',
        ],
        "packages/typescript/src/mcp.js": [
            'MCP_PROTOCOL_VERSION = "2026-07-28"',
            'clientVersion = "0.13.0"',
            'this.rpc("server/discover", {})',
            '"io.modelcontextprotocol/clientCapabilities"',
            "text/event-stream",
            "MCP_METHOD_HEADER",
            "MCP_NAME_HEADER",
            'result.resultType === "input_required"',
            'result.isError === true',
        ],
        "packages/rust/src/mcp.rs": [
            'MCP_PROTOCOL_VERSION: &str = "2026-07-28"',
            'self.request("server/discover", None, "")',
            "io.modelcontextprotocol/clientCapabilities",
            "application/json, text/event-stream",
            "MCP_METHOD_HEADER",
            "MCP_NAME_HEADER",
            "McpCallOutcome::InputRequired",
            "McpCallOutcome::ToolError",
            "expected_id: i64",
        ],
        "packages/python/src/tempera_sdk/provider.py": [
            'MCP_PROVIDER_PROTOCOL_VERSION = "2026-07-28"',
            '"resultType": "complete"',
            "_ProviderExecutionError",
        ],
        "packages/python/src/tempera_sdk/provider_capabilities.py": [
            '"resultType": "complete"',
            'raise _ProviderExecutionError("resource execution failed")',
            'raise _ProviderExecutionError("prompt execution failed")',
        ],
        "packages/rust/examples/mcp_protocol_e2e.rs": [
            "McpRequestBuilder",
            "classify_mcp_call_result(&outcome, invalid.id())",
            'catalog.matches("\\\"name\\\":\\\"tempera_").count() != 11',
            "rust-secret-argument-sentinel",
            'bearer != "local-e2e-placeholder"',
            'host != "127.0.0.1" || path != "/mcp"',
        ],
        "packages/typescript/examples/mcp_protocol_e2e.mjs": [
            "TemperaMcpClient",
            "MCP_PROTOCOL_VERSION",
            'from "../src/index.js"',
            "tools.length !== expectedTools.length",
            "error instanceof TemperaMcpError",
            "error.code !== 0",
            'error.data?.resultType !== "complete"',
            "identity.structuredContent?.authenticated !== false",
            "typescript-secret-argument-sentinel",
            'bearer !== "local-e2e-placeholder"',
            'parsedEndpoint.hostname !== "127.0.0.1"',
            'clientVersion: "0.13.0"',
        ],
        "docs/COMPATIBILITY.md": [
            "stateless MCP 2026 client and terminal-outcome boundary",
            "package `0.13.0`",
            "call_tool_body",
            "parse_mcp_error",
        ],
    }
    for relative, markers in checks.items():
        text = (root / relative).read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(f"SDK MCP projection {relative} is missing {marker!r}")
        forbidden = [
            'rpc("initialize"',
            'rpc("initialize",',
            '\"method\":\"initialize\"',
            'MCP_PROTOCOL_VERSION = "2025-06-18"',
            'MCP_PROTOCOL_VERSION: &str = "2025-06-18"',
        ]
        for marker in forbidden:
            if marker in text:
                fail(f"SDK MCP projection {relative} retains forbidden wire marker {marker!r}")

    workflow = (root / ".github/workflows/mcp-protocol-exact-source.yml").read_text(
        encoding="utf-8"
    )
    orchestrator = (root / "scripts/mcp-protocol-e2e.py").read_text(encoding="utf-8")
    for marker in [
        "packages/typescript/examples/mcp_protocol_e2e.mjs",
        "node --check packages/typescript/examples/mcp_protocol_e2e.mjs",
        "--typescript-client-script packages/typescript/examples/mcp_protocol_e2e.mjs",
    ]:
        if marker not in workflow:
            fail(f"MCP exact-source workflow is missing {marker!r}")
    for authority_path in [
        "packages/python/pyproject.toml",
        "packages/python/uv.lock",
        "packages/rust/Cargo.toml",
        "packages/rust/Cargo.lock",
        "packages/typescript/package.json",
    ]:
        if workflow.count(f'\"{authority_path}\"') != 2:
            fail(
                "MCP exact-source workflow must watch version authority in both "
                f"pull_request and main push filters: {authority_path}"
            )
    for marker in [
        'parser.add_argument("--typescript-client-script", type=Path, required=True)',
        '"TypeScript MCP E2E client must be the reviewed example',
        '"Rust MCP E2E client must be the reviewed example',
        '"exact MCP 2026-07-28 TypeScript SDK E2E passed"',
        '"typescript-secret-argument-sentinel"',
        'env={"PATH": os.environ.get("PATH", ""), "RUST_LOG": "warn"}',
        'env={"PATH": os.environ.get("PATH", "")}',
    ]:
        if marker not in orchestrator:
            fail(f"MCP wire orchestrator is missing {marker!r}")


def validate_source(lock: dict[str, Any], source_root: Path) -> None:
    if run_git(source_root, "status", "--porcelain"):
        fail("MCP source checkout is dirty")
    head = run_git(source_root, "rev-parse", "HEAD")
    if head != lock["source_commit"]:
        fail(f"MCP source HEAD {head} does not equal receipt {lock['source_commit']}")
    tree = run_git(source_root, "rev-parse", "HEAD^{tree}")
    if tree != lock["source_tree"]:
        fail(f"MCP source tree {tree} does not equal receipt {lock['source_tree']}")
    origin = normalized_repo(run_git(source_root, "remote", "get-url", "origin"))
    if origin != SOURCE_REPO:
        fail(f"MCP source origin is not {SOURCE_REPO}: {origin}")
    remote_main = run_git(source_root, "rev-parse", "refs/remotes/origin/main")
    if remote_main != head:
        fail(f"MCP receipt is not current trusted main: source={head}, origin/main={remote_main}")

    for source_path, identity in lock["source_files"].items():
        entry = run_git(source_root, "ls-tree", "HEAD", "--", source_path).split()
        if len(entry) < 4 or entry[1] != "blob":
            fail(f"MCP source path is not a committed blob: {source_path}")
        if entry[2] != identity["blob"]:
            fail(f"MCP source blob drift for {source_path}")
        committed = subprocess.run(
            ["git", "-C", str(source_root), "show", f"HEAD:{source_path}"],
            check=True,
            capture_output=True,
        ).stdout
        if hashlib.sha256(committed).hexdigest() != identity["sha256"]:
            fail(f"MCP source SHA-256 drift for {source_path}")
        if (source_root / source_path).read_bytes() != committed:
            fail(f"MCP source worktree bytes differ from committed bytes for {source_path}")

    cargo = (source_root / "Cargo.toml").read_text(encoding="utf-8")
    docs = (source_root / "docs/protocol-compatibility.md").read_text(encoding="utf-8")
    fixture = (source_root / "scripts/framework-comparison.mjs").read_text(encoding="utf-8")
    app = (source_root / "src/app.rs").read_text(encoding="utf-8")
    client = (source_root / "src/client.rs").read_text(encoding="utf-8")
    tools = json.loads(
        (source_root / "contracts/mcp-tools-v1.json").read_text(encoding="utf-8")
    )
    toolchain = (source_root / "rust-toolchain.toml").read_text(encoding="utf-8")
    semantic_markers = [
        (cargo, f'rev = "{OFFICIAL_SDK_COMMIT}"'),
        (toolchain, 'channel = "1.96.1"'),
        (docs, "no `initialize`"),
        (docs, "`server/discover`"),
        (docs, "`MCP-Protocol-Version`"),
        (docs, "`inputRequired`"),
        (fixture, '"mcp-protocol-version": "2026-07-28"'),
        (fixture, '"mcp-method": method'),
        (fixture, '"io.modelcontextprotocol/clientCapabilities"'),
        (app, "ProtocolVersion::V_2026_07_28"),
        (client, "ClientLifecycleMode::Discover"),
        (client, "ProtocolVersion::V_2026_07_28"),
    ]
    for text, marker in semantic_markers:
        if marker not in text:
            fail(f"MCP exact source no longer proves required marker {marker!r}")
    tool_names = sorted(tool["name"] for tool in tools.get("tools", []))
    expected_tools = sorted(
        [
            "tempera_capability_catalog",
            "tempera_children",
            "tempera_commit",
            "tempera_describe",
            "tempera_execute_plan",
            "tempera_invoke",
            "tempera_manage_connections",
            "tempera_prepare",
            "tempera_search",
            "tempera_status",
            "tempera_whoami",
        ]
    )
    if tools.get("contractVersion") != "tempera.mcp-tools/v1" or tool_names != expected_tools:
        fail("MCP exact source fixed tool contract is not the expected 11-tool surface")


def validate_official_sdk(lock: dict[str, Any], source_root: Path) -> None:
    if run_git(source_root, "status", "--porcelain"):
        fail("official MCP SDK source checkout is dirty")
    head = run_git(source_root, "rev-parse", "HEAD")
    if head != lock["official_rust_sdk_commit"]:
        fail("official MCP SDK HEAD does not equal the receipt")
    tree = run_git(source_root, "rev-parse", "HEAD^{tree}")
    if tree != lock["official_rust_sdk_tree"]:
        fail("official MCP SDK tree does not equal the receipt")
    origin = normalized_repo(run_git(source_root, "remote", "get-url", "origin"))
    if origin != lock["official_rust_sdk_repo"]:
        fail(f"official MCP SDK origin is not {OFFICIAL_SDK_REPO}: {origin}")

    for source_path, identity in lock["official_rust_sdk_source_files"].items():
        entry = run_git(source_root, "ls-tree", "HEAD", "--", source_path).split()
        if len(entry) < 4 or entry[1] != "blob" or entry[2] != identity["blob"]:
            fail(f"official MCP SDK blob drift for {source_path}")
        committed = subprocess.run(
            ["git", "-C", str(source_root), "show", f"HEAD:{source_path}"],
            check=True,
            capture_output=True,
        ).stdout
        if hashlib.sha256(committed).hexdigest() != identity["sha256"]:
            fail(f"official MCP SDK SHA-256 drift for {source_path}")
        if (source_root / source_path).read_bytes() != committed:
            fail(f"official MCP SDK worktree bytes differ for {source_path}")

    model = (source_root / "crates/rmcp/src/model.rs").read_text(encoding="utf-8")
    mrtr = (source_root / "crates/rmcp/src/model/mrtr.rs").read_text(encoding="utf-8")
    deserialization = (
        source_root / "crates/rmcp/tests/test_deserialization.rs"
    ).read_text(encoding="utf-8")
    wire_tests = (source_root / "crates/rmcp/tests/test_result_type_wire.rs").read_text(
        encoding="utf-8"
    )
    markers = [
        (model, 'Self(Cow::Borrowed("input_required"))'),
        (model, "ResultType::is_input_required"),
        (mrtr, "InputRequiredResult requires resultType"),
        (deserialization, '"resultType": "input_required"'),
        (wire_tests, 'assert_eq!(value["resultType"], "complete");'),
    ]
    for text, marker in markers:
        if marker not in text:
            fail(f"official MCP SDK source no longer proves {marker!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--official-sdk-root", type=Path)
    args = parser.parse_args()
    lock = load_lock()
    validate_lock(lock)
    validate_sdk()
    if args.source_root is not None:
        validate_source(lock, args.source_root.resolve())
    if args.official_sdk_root is not None:
        validate_official_sdk(lock, args.official_sdk_root.resolve())
    print(
        "MCP protocol receipt and SDK projection verified: "
        f"{lock['source_commit']} / {PROTOCOL_VERSION}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
