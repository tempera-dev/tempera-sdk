#!/usr/bin/env python3
"""Vendor exact producer-owned Data Engine MCP contract artifacts."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPENAPI_SYNC = Path(__file__).with_name("sync-data-engine-openapi.py")
SPEC = importlib.util.spec_from_file_location("sync_data_engine_openapi", OPENAPI_SYNC)
assert SPEC and SPEC.loader
openapi_sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(openapi_sync)

ARTIFACTS = {
    "api/mcp-admission.json": ROOT / "specs" / "data-engine-mcp-admission.json",
    "api/mcp-tools.json": ROOT / "specs" / "data-engine-mcp-tools.json",
}
GENERATOR_VERSION = "sync-data-engine-mcp-contracts.py@1+verbatim"


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def lock_path(destination: Path) -> Path:
    return destination.with_name(destination.name + ".source")


def expected_files(
    source_repo_dir: Path, commit: str, source_branch: str = "main"
) -> dict[Path, bytes]:
    outputs: dict[Path, bytes] = {}
    documents: dict[str, dict] = {}
    commits: set[str] = set()
    for source_path, destination in ARTIFACTS.items():
        source_bytes, metadata = openapi_sync.committed_source(
            source_repo_dir / source_path,
            source_branch=source_branch,
            source_commit=commit,
        )
        try:
            document = json.loads(source_bytes)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid {source_path}: {error}") from error
        documents[source_path] = document
        commits.add(metadata["source_commit"])
        outputs[destination] = source_bytes
        lock = {
            "schema_version": 1,
            **metadata,
            "generated_with": GENERATOR_VERSION,
            "generated_path": destination.relative_to(ROOT).as_posix(),
            "generated_sha256": digest(source_bytes),
        }
        outputs[lock_path(destination)] = (
            json.dumps(lock, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
    if len(commits) != 1:
        raise ValueError(f"MCP artifacts resolved to different commits: {sorted(commits)}")

    openapi_bytes, openapi_metadata = openapi_sync.committed_source(
        source_repo_dir / "api/openapi.yaml",
        source_branch=source_branch,
        source_commit=commit,
    )
    openapi_operations = openapi_sync.extract_operations_text(
        openapi_bytes.decode("utf-8"),
        f"{openapi_metadata['source_repo']}@{openapi_metadata['source_commit']}:"
        f"{openapi_metadata['source_path']}",
    )

    admission = documents["api/mcp-admission.json"]
    tools = documents["api/mcp-tools.json"]
    if admission.get("schema") != "data-engine.mcp-admission.v1":
        raise ValueError("unexpected Data Engine MCP admission schema")
    if tools.get("schema") != "data-engine.mcp-tools.v1":
        raise ValueError("unexpected Data Engine MCP tools schema")
    if admission.get("producer") != "data-engine" or tools.get("producer") != "data-engine":
        raise ValueError("unexpected Data Engine MCP artifact producer")
    if admission.get("source") != tools.get("source"):
        raise ValueError("Data Engine MCP artifacts pin different generator source")
    policy = admission.get("policy") or {}
    tool_list = tools.get("tools")
    operations = admission.get("operations")
    if not isinstance(tool_list, list) or not isinstance(operations, list):
        raise ValueError("Data Engine MCP artifacts lack tool/operation arrays")
    expected_tool_digest = policy.get("mcp_tools_artifact", {}).get("sha256")
    if expected_tool_digest != digest(outputs[ARTIFACTS["api/mcp-tools.json"]]):
        raise ValueError("MCP admission does not bind the exact tools artifact")
    operation_ids = [operation.get("operation_id") for operation in operations]
    openapi_operation_ids = {
        operation["operationId"]
        for operation in openapi_operations
        if operation["operationId"] not in {"health.get", "mcp.jsonrpc"}
    }
    if len(operation_ids) != len(set(operation_ids)):
        raise ValueError("MCP admission contains duplicate operation decisions")
    if set(operation_ids) != openapi_operation_ids:
        raise ValueError(
            "MCP admission decisions differ from authenticated OpenAPI operations "
            f"(missing={sorted(openapi_operation_ids - set(operation_ids))}, "
            f"extra={sorted(set(operation_ids) - openapi_operation_ids)})"
        )
    decisions = [operation.get("decision") for operation in operations]
    invalid_decisions = sorted({decision for decision in decisions if decision not in {"expose", "deny"}})
    exposed_count = decisions.count("expose")
    if invalid_decisions:
        raise ValueError(f"unexpected MCP admission decisions: {invalid_decisions}")
    if len(tool_list) != 36 or exposed_count != len(tool_list):
        raise ValueError(
            "unexpected MCP exposure/tool counts: "
            f"{exposed_count} exposed decisions/{len(tool_list)} tools"
        )
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--source-repo-dir", type=Path, required=True)
    parser.add_argument("--source-branch", default="main")
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    if re.fullmatch(r"[0-9a-f]{40}", args.source_commit) is None:
        parser.error("--source-commit must be an exact 40-character SHA")
    try:
        outputs = expected_files(
            args.source_repo_dir.resolve(), args.source_commit, args.source_branch
        )
        if args.check:
            stale = [
                path
                for path, expected in outputs.items()
                if not path.is_file() or path.read_bytes() != expected
            ]
            if stale:
                print(
                    "Data Engine MCP contract artifacts are stale: "
                    + ", ".join(str(path.relative_to(ROOT)) for path in stale),
                    file=sys.stderr,
                )
                return 1
            print("Data Engine MCP contract artifacts match exact producer source.")
            return 0
        for path, content in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            print(f"wrote {path.relative_to(ROOT)}")
        return 0
    except (OSError, ValueError) as error:
        print(f"Data Engine MCP contract sync failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
