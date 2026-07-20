#!/usr/bin/env python3
"""Lock the data-engine OpenAPI operation index used by the SDK.

The SDK keeps language-specific request ergonomics in ``surface.json``, but
the REST method, path, and canonical operation ID belong to data-engine.  This
script extracts that authoritative operation index using only the standard
library and stores it in ``contracts/data-engine-openapi-operations.json``.

Usage:
  python3 scripts/sync-data-engine-openapi.py
  python3 scripts/sync-data-engine-openapi.py --check
  python3 scripts/sync-data-engine-openapi.py --source /path/to/openapi.yaml

The default source is the sibling data-engine checkout.  CI validates the
committed lock; integration jobs should additionally run ``--check`` with a
checked-out data-engine source (or TEMPERA_DATA_ENGINE_OPENAPI) to reject
cross-repository drift.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "contracts" / "data-engine-openapi-operations.json"
DEFAULT_SOURCE = ROOT.parent / "data-engine" / "api" / "openapi.yaml"
METHOD_RE = re.compile(r"^    (get|post|put|patch|delete):\s*$")
PATH_RE = re.compile(r"^  (/[^\s]*):\s*$")
OPERATION_ID_RE = re.compile(r"^      operationId:\s*([^\s#]+)\s*$")
GENERATOR_VERSION = "sync-data-engine-openapi.py@2"


def extract_operations_text(source_text: str, source_label: str) -> list[dict[str, str]]:
    """Extract the OpenAPI paths section's operation identity triples.

    The data-engine contract deliberately uses conventional block YAML for
    paths, methods, and operation IDs.  Parsing this narrow grammar avoids a
    runtime YAML dependency in all SDK language CI jobs.
    """
    operations: list[dict[str, str]] = []
    in_paths = False
    path: str | None = None
    method: str | None = None
    for raw in source_text.splitlines():
        if raw == "paths:":
            in_paths = True
            continue
        if in_paths and raw and not raw.startswith(" "):
            break
        if not in_paths:
            continue
        path_match = PATH_RE.match(raw)
        if path_match:
            path = path_match.group(1)
            method = None
            continue
        method_match = METHOD_RE.match(raw)
        if method_match and path is not None:
            method = method_match.group(1).upper()
            continue
        operation_match = OPERATION_ID_RE.match(raw)
        if operation_match and path is not None and method is not None:
            operations.append(
                {
                    "operationId": operation_match.group(1),
                    "method": method,
                    "path": path,
                }
            )
            method = None
    if not operations:
        raise ValueError(f"no OpenAPI operations found in {source_label}")
    seen: set[str] = set()
    for operation in operations:
        operation_id = operation["operationId"]
        if operation_id in seen:
            raise ValueError(f"duplicate operationId {operation_id!r} in {source_label}")
        seen.add(operation_id)
    return operations


def extract_operations(source: Path) -> list[dict[str, str]]:
    return extract_operations_text(source.read_text(encoding="utf-8"), str(source))


def route_identity(method: str, path: str) -> tuple[str, str]:
    """Match route templates structurally, independent of parameter spelling."""
    path = re.sub(r"^/v1/projects/\{[^}]+\}", "/v1/{parent}", path)
    return method, re.sub(r"\{[^}]+\}", "{}", path)


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise ValueError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def canonical_repository(remote: str) -> str:
    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", remote)
    if not match:
        raise ValueError(f"cannot derive canonical GitHub repository from {remote!r}")
    return match.group(1)


def committed_source(source: Path) -> tuple[bytes, dict[str, str]]:
    source = source.resolve()
    repo = Path(run_git(source.parent, "rev-parse", "--show-toplevel"))
    try:
        source_path = source.relative_to(repo).as_posix()
    except ValueError as error:
        raise ValueError(f"source {source} is outside Git repository {repo}") from error
    dirty = run_git(repo, "status", "--porcelain")
    if dirty:
        raise ValueError(f"source repository is dirty; refusing provenance from {repo}")
    commit = run_git(repo, "rev-parse", "HEAD")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError(f"source commit is not a 40-character SHA: {commit!r}")
    branch = run_git(repo, "symbolic-ref", "--quiet", "--short", "HEAD")
    remote_ref = f"refs/remotes/origin/{branch}"
    remote_commit = run_git(repo, "rev-parse", "--verify", remote_ref)
    reachable = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", commit, remote_commit],
        capture_output=True,
        check=False,
    )
    if reachable.returncode != 0:
        raise ValueError(
            f"source commit {commit} is not reachable from origin/{branch}; "
            "push the source commit before generating provenance"
        )
    blob = run_git(repo, "rev-parse", f"{commit}:{source_path}")
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{source_path}"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(
            f"git show {commit}:{source_path} failed: "
            + result.stderr.decode("utf-8", errors="replace").strip()
        )
    metadata = {
        "source_repo": canonical_repository(run_git(repo, "remote", "get-url", "origin")),
        "source_branch": branch,
        "source_commit": commit,
        "source_path": source_path,
        "source_blob_sha": blob,
        "source_sha256": hashlib.sha256(result.stdout).hexdigest(),
    }
    return result.stdout, metadata


def render(source_label: str, source_metadata: dict[str, str], operations: list[dict[str, str]]) -> str:
    surface = json.loads((ROOT / "surface.json").read_text(encoding="utf-8"))
    by_identity = {
        route_identity(operation["method"], operation["path"]): operation
        for operation in operations
    }
    if len(by_identity) != len(operations):
        raise ValueError(f"duplicate structural route identity in {source_label}")
    bindings: list[dict[str, str]] = []
    for sdk_operation in surface["operations"]["dataEngine"]:
        identity = route_identity(sdk_operation["method"], sdk_operation["path"])
        operation = by_identity.get(identity)
        if operation is None:
            raise ValueError(
                f"SDK operation {sdk_operation['id']!r} is absent from {source_label}: {identity}"
            )
        bindings.append({"sdkOperationId": sdk_operation["id"], **operation})
    # The MCP gateway is represented by the SDK's dedicated MCP client. Every
    # other data-engine OpenAPI operation must have a generated REST method;
    # otherwise regenerating this lock after an accidental surface deletion
    # could make a smaller SDK look valid.
    authoritative_rest = {
        operation["operationId"] for operation in operations if operation["operationId"] != "mcp.jsonrpc"
    }
    represented = {binding["operationId"] for binding in bindings}
    missing = sorted(authoritative_rest - represented)
    extra = sorted(represented - authoritative_rest)
    if missing or extra:
        raise ValueError(
            "data-engine SDK coverage differs from authoritative REST operations "
            f"(missing={missing}, extra={extra})"
        )
    generated_bytes = (json.dumps(bindings, sort_keys=True, separators=(",", ":")) + "\n").encode()
    lock = {
        "schema_version": 2,
        **source_metadata,
        "generated_with": GENERATOR_VERSION,
        "generated_sha256": hashlib.sha256(generated_bytes).hexdigest(),
        "operations": bindings,
    }
    return json.dumps(lock, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(os.environ.get("TEMPERA_DATA_ENGINE_OPENAPI", DEFAULT_SOURCE)),
    )
    args = parser.parse_args()
    if not args.source.is_file():
        print(
            f"data-engine OpenAPI source not found: {args.source}; "
            "set TEMPERA_DATA_ENGINE_OPENAPI or pass --source",
            file=sys.stderr,
        )
        return 2
    try:
        source_bytes, source_metadata = committed_source(args.source)
        source_text = source_bytes.decode("utf-8")
        operations = extract_operations_text(
            source_text,
            f"{source_metadata['source_repo']}@{source_metadata['source_commit']}:{source_metadata['source_path']}",
        )
        expected = render(str(args.source), source_metadata, operations)
    except ValueError as error:
        print(f"data-engine OpenAPI parse failed: {error}", file=sys.stderr)
        return 1
    if args.check:
        actual = LOCK.read_text(encoding="utf-8") if LOCK.exists() else ""
        if actual != expected:
            print(
                "data-engine OpenAPI lock is stale; run "
                "python3 scripts/sync-data-engine-openapi.py --source "
                f"{args.source}",
                file=sys.stderr,
            )
            return 1
        print(
            "data-engine OpenAPI lock passed "
            f"({len(operations)} authoritative operations at "
            f"{source_metadata['source_repo']}@{source_metadata['source_commit']})"
        )
        return 0
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(expected, encoding="utf-8")
    print(
        f"wrote {LOCK.relative_to(ROOT)} ({len(operations)} authoritative operations at "
        f"{source_metadata['source_repo']}@{source_metadata['source_commit']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
