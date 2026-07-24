#!/usr/bin/env python3
"""Vendor Tempo's exact committed tempod OpenAPI and source lock."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "specs/tempo.openapi.json"
LOCK = DESTINATION.with_name(DESTINATION.name + ".source")
SOURCE_PATH = "contracts/tempod.openapi.json"
SOURCE_REPO = "tempera-dev/tempo"
GENERATOR = "sync-tempo-openapi.py@1+verbatim"
SOURCE_LOCK_SCRIPT = ROOT / ".codex/skills/tempera-sync-contracts/scripts/source_lock.py"


def load_source_lock_module():
    sys.path.insert(0, str(SOURCE_LOCK_SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("tempera_source_lock", SOURCE_LOCK_SCRIPT)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load vendored source-lock implementation")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expected_files(
    repo: Path,
    source_branch: str,
    requested_commit: str,
    *,
    allow_unpublished_local: bool,
) -> tuple[bytes, bytes]:
    source_lock = load_source_lock_module()
    if allow_unpublished_local:
        status = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout
        if status:
            raise ValueError("unpublished Tempo source repository is dirty")
        origin = subprocess.run(
            ["git", "-C", str(repo), "remote", "get-url", "origin"],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        if origin not in {
            "git@github.com:tempera-dev/tempo.git",
            "https://github.com/tempera-dev/tempo.git",
            "ssh://git@github.com/tempera-dev/tempo.git",
        }:
            raise ValueError("unpublished Tempo source origin is not tempera-dev/tempo")
        current_branch = subprocess.run(
            ["git", "-C", str(repo), "branch", "--show-current"],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        if current_branch != source_branch:
            raise ValueError(
                "unpublished Tempo source branch does not match --source-branch"
            )
        commit = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", f"{requested_commit}^{{commit}}"],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        if commit != requested_commit:
            raise ValueError("unpublished Tempo source must use an exact commit")
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "merge-base",
                "--is-ancestor",
                commit,
                f"refs/heads/{source_branch}",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    else:
        commit = source_lock.validate_source(
            repo, SOURCE_REPO, source_branch, requested_commit
        )
    blob, mode, content = source_lock.committed_file(repo, commit, SOURCE_PATH)
    document = json.loads(content)
    if document.get("openapi") != "3.1.0" or not isinstance(
        document.get("paths"), dict
    ):
        raise ValueError("Tempo source is not the canonical OpenAPI 3.1 document")
    digest = hashlib.sha256(content).hexdigest()
    lock = {
        "generated_path": DESTINATION.relative_to(ROOT).as_posix(),
        "generated_sha256": digest,
        "generated_with": GENERATOR,
        "schema_version": 1,
        "source_blob_sha": blob,
        "source_branch": source_branch,
        "source_commit": commit,
        "source_mode": mode,
        "source_path": SOURCE_PATH,
        "source_repo": SOURCE_REPO,
        "source_sha256": digest,
    }
    if allow_unpublished_local:
        lock["source_state"] = "unpublished_local_review"
    return content, (json.dumps(lock, indent=2, sort_keys=True) + "\n").encode()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--source-repo-dir", type=Path, required=True)
    parser.add_argument("--source-branch", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument(
        "--allow-unpublished-local",
        action="store_true",
        help="Permit a clean exact local branch for pre-publication review only.",
    )
    args = parser.parse_args()
    if re.fullmatch(r"[0-9a-f]{40}", args.source_commit) is None:
        parser.error("--source-commit must be an exact 40-character SHA")
    if not args.source_branch or args.source_branch.startswith("-"):
        parser.error("--source-branch must name the exact reviewed producer branch")
    try:
        spec_bytes, lock_bytes = expected_files(
            args.source_repo_dir.resolve(),
            args.source_branch,
            args.source_commit,
            allow_unpublished_local=args.allow_unpublished_local,
        )
        expected = {DESTINATION: spec_bytes, LOCK: lock_bytes}
        if args.check:
            stale = [
                path
                for path, content in expected.items()
                if not path.is_file() or path.read_bytes() != content
            ]
            if stale:
                print(
                    "Tempo OpenAPI artifacts are stale: "
                    + ", ".join(
                        path.relative_to(ROOT).as_posix() for path in stale
                    ),
                    file=sys.stderr,
                )
                return 1
            print(
                f"Tempo OpenAPI matches {SOURCE_REPO}@{args.source_commit} "
                f"on {args.source_branch}."
            )
            return 0
        for path, content in expected.items():
            path.write_bytes(content)
            print(f"wrote {path.relative_to(ROOT)}")
        return 0
    except (
        OSError,
        ValueError,
        subprocess.CalledProcessError,
        json.JSONDecodeError,
    ) as error:
        print(f"Tempo OpenAPI sync failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
