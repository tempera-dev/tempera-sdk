#!/usr/bin/env python3
"""Vendor Auth Hub's exact committed control-plane OpenAPI and source lock."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "specs/control-plane.openapi.json"
LOCK = DESTINATION.with_name(DESTINATION.name + ".source")
SOURCE_PATH = "contracts/control-plane.openapi.json"
SOURCE_REPO = "tempera-dev/auth-hub"
SOURCE_BRANCH = "main"
GENERATOR = "sync-control-plane-openapi.py@1+verbatim"
SOURCE_LOCK_SCRIPT = (
    ROOT
    / ".codex/skills/tempera-sync-contracts/scripts/source_lock.py"
)


def load_source_lock_module():
    sys.path.insert(0, str(SOURCE_LOCK_SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("tempera_source_lock", SOURCE_LOCK_SCRIPT)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load vendored source-lock implementation")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expected_files(repo: Path, requested_commit: str) -> tuple[bytes, bytes]:
    source_lock = load_source_lock_module()
    commit = source_lock.validate_source(repo, SOURCE_REPO, SOURCE_BRANCH, requested_commit)
    blob, mode, content = source_lock.committed_file(repo, commit, SOURCE_PATH)
    document = json.loads(content)
    if document.get("openapi") != "3.1.0" or not isinstance(document.get("paths"), dict):
        raise ValueError("Auth Hub source is not the canonical OpenAPI 3.1 document")
    digest = hashlib.sha256(content).hexdigest()
    lock = {
        "generated_path": DESTINATION.relative_to(ROOT).as_posix(),
        "generated_sha256": digest,
        "generated_with": GENERATOR,
        "schema_version": 1,
        "source_blob_sha": blob,
        "source_branch": SOURCE_BRANCH,
        "source_commit": commit,
        "source_mode": mode,
        "source_path": SOURCE_PATH,
        "source_repo": SOURCE_REPO,
        "source_sha256": digest,
    }
    return content, (json.dumps(lock, indent=2, sort_keys=True) + "\n").encode()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--source-repo-dir", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    if re.fullmatch(r"[0-9a-f]{40}", args.source_commit) is None:
        parser.error("--source-commit must be an exact 40-character SHA")
    try:
        spec_bytes, lock_bytes = expected_files(args.source_repo_dir.resolve(), args.source_commit)
        expected = {DESTINATION: spec_bytes, LOCK: lock_bytes}
        if args.check:
            stale = [path for path, content in expected.items() if not path.is_file() or path.read_bytes() != content]
            if stale:
                print(
                    "Control Plane OpenAPI artifacts are stale: "
                    + ", ".join(path.relative_to(ROOT).as_posix() for path in stale),
                    file=sys.stderr,
                )
                return 1
            print(f"Control Plane OpenAPI matches {SOURCE_REPO}@{args.source_commit}.")
            return 0
        for path, content in expected.items():
            path.write_bytes(content)
            print(f"wrote {path.relative_to(ROOT)}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Control Plane OpenAPI sync failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
