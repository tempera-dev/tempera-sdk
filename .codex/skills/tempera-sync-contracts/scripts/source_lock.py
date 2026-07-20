#!/usr/bin/env python3
"""Create or verify an exact committed-source lock without reading dirty bytes."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from sync_agent_kit import committed_file, digest, safe_relative, validate_source


def build_lock(args: argparse.Namespace) -> dict[str, object]:
    repo = args.repo_dir.resolve()
    commit = validate_source(repo, args.source_repo, args.source_branch, args.commit)
    source_path = safe_relative(args.source_path).as_posix()
    blob, mode, content = committed_file(repo, commit, source_path)
    lock: dict[str, object] = {
        "schema_version": 1,
        "source_repo": args.source_repo,
        "source_branch": args.source_branch,
        "source_commit": commit,
        "source_path": source_path,
        "source_blob_sha": blob,
        "source_mode": mode,
        "source_sha256": digest(content),
        "generated_with": args.generated_with,
    }
    if (args.generated_file is None) != (args.generated_path is None):
        raise ValueError("generated-file and generated-path must be provided together")
    if args.generated_file is not None:
        if args.generated_file.is_symlink() or not args.generated_file.is_file():
            raise ValueError("generated-file must be a regular file, not a symlink")
        generated_path = safe_relative(args.generated_path).as_posix()
        lock["generated_path"] = generated_path
        lock["generated_sha256"] = digest(args.generated_file.resolve().read_bytes())
    return lock


def configure(command: argparse.ArgumentParser, *, checking: bool) -> None:
    command.add_argument("--repo-dir", type=Path, required=True)
    command.add_argument("--source-repo", required=True)
    command.add_argument("--source-branch", required=True)
    command.add_argument("--commit", default="HEAD")
    command.add_argument("--source-path", required=True)
    command.add_argument("--generated-with", required=True)
    command.add_argument("--generated-file", type=Path)
    command.add_argument("--generated-path")
    if checking:
        command.add_argument("--lock", type=Path, required=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)
    configure(subcommands.add_parser("create"), checking=False)
    configure(subcommands.add_parser("check"), checking=True)
    args = parser.parse_args()
    try:
        expected = build_lock(args)
        if args.command == "create":
            json.dump(expected, sys.stdout, indent=2, sort_keys=True)
            sys.stdout.write("\n")
            return 0
        if args.lock.is_symlink() or not args.lock.is_file():
            raise ValueError("lock must be a regular file, not a symlink")
        actual = json.loads(args.lock.read_text())
        if actual != expected:
            print(json.dumps({"expected": expected, "actual": actual}, indent=2, sort_keys=True), file=sys.stderr)
            return 1
        print("source lock verified")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"source lock error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
