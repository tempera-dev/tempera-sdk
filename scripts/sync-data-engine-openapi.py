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
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "contracts" / "data-engine-openapi-operations.json"
DEFAULT_SOURCE = ROOT.parent / "data-engine" / "api" / "openapi.yaml"
METHOD_RE = re.compile(r"^    (get|post|put|patch|delete):\s*$")
PATH_RE = re.compile(r"^  (/[^\s]*):\s*$")
OPERATION_ID_RE = re.compile(r"^      operationId:\s*([^\s#]+)\s*$")


def extract_operations(source: Path) -> list[dict[str, str]]:
    """Extract the OpenAPI paths section's operation identity triples.

    The data-engine contract deliberately uses conventional block YAML for
    paths, methods, and operation IDs.  Parsing this narrow grammar avoids a
    runtime YAML dependency in all SDK language CI jobs.
    """
    operations: list[dict[str, str]] = []
    in_paths = False
    path: str | None = None
    method: str | None = None
    for raw in source.read_text(encoding="utf-8").splitlines():
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
        raise ValueError(f"no OpenAPI operations found in {source}")
    seen: set[str] = set()
    for operation in operations:
        operation_id = operation["operationId"]
        if operation_id in seen:
            raise ValueError(f"duplicate operationId {operation_id!r} in {source}")
        seen.add(operation_id)
    return operations


def canonical_sdk_path(path: str) -> str:
    path = path.replace("/v1/projects/{project_id}", "/v1/{parent}")
    return re.sub(
        r"\{([a-z0-9_]+)\}",
        lambda match: "{" + re.sub(
            r"_([a-z0-9])", lambda part: part.group(1).upper(), match.group(1)
        ) + "}",
        path,
    )


def render(source: Path, operations: list[dict[str, str]]) -> str:
    surface = json.loads((ROOT / "surface.json").read_text(encoding="utf-8"))
    by_identity = {
        (operation["method"], operation["path"]): operation
        for operation in operations
    }
    bindings: list[dict[str, str]] = []
    for sdk_operation in surface["operations"]["dataEngine"]:
        identity = (sdk_operation["method"], canonical_sdk_path(sdk_operation["path"]))
        operation = by_identity.get(identity)
        if operation is None:
            raise ValueError(
                f"SDK operation {sdk_operation['id']!r} is absent from {source}: {identity}"
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
    lines = [
        "{",
        '  "schemaVersion": 1,',
        '  "source": "data-engine/api/openapi.yaml",',
        '  "sourceSha256": "' + hashlib.sha256(source.read_bytes()).hexdigest() + '",',
        '  "operations": [',
    ]
    lines.extend(
        "    " + json.dumps(binding, separators=(",", ":")) + ("," if index < len(bindings) - 1 else "")
        for index, binding in enumerate(bindings)
    )
    lines.extend(["  ]", "}"])
    return "\n".join(lines) + "\n"


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
        expected = render(args.source, extract_operations(args.source))
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
        print(f"data-engine OpenAPI lock passed ({len(extract_operations(args.source))} authoritative operations)")
        return 0
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(expected, encoding="utf-8")
    print(f"wrote {LOCK.relative_to(ROOT)} ({len(extract_operations(args.source))} authoritative operations)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
