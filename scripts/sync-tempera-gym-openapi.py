#!/usr/bin/env python3
"""Vendor an exact committed tempera-gym OpenAPI document and source lock."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "specs/tempera-gym-api.json"
LOCK = DESTINATION.with_name(DESTINATION.name + ".source")
SOURCE_PATH = "contracts/gym-api.openapi.yaml"
SOURCE_REPO = "tempera-dev/tempera-gym"
GENERATOR = f"sync-tempera-gym-openapi.py@1+PyYAML@{yaml.__version__}+json.dumps-indent-2"
BRANCH_RE = re.compile(r"^(?!/)(?!.*(?:\.\.|//))[A-Za-z0-9._/-]+(?<!/)$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def git(repo: Path, *args: str, binary: bool = False) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=not binary,
    ).stdout
    return result if binary else result.strip()


def normalize_origin(value: str) -> str | None:
    patterns = (
        r"git@github\.com:([^/]+/[^/]+?)(?:\.git)?",
        r"ssh://git@github\.com/([^/]+/[^/]+?)(?:\.git)?/?",
        r"https://github\.com/([^/]+/[^/]+?)(?:\.git)?/?",
    )
    for pattern in patterns:
        match = re.fullmatch(pattern, value)
        if match:
            return match.group(1)
    return None


def committed_source(
    repo: Path, source_branch: str, requested_commit: str
) -> tuple[str, str, str, bytes]:
    if not BRANCH_RE.fullmatch(source_branch):
        raise ValueError("source branch is unsafe")
    if not COMMIT_RE.fullmatch(requested_commit):
        raise ValueError("source commit must be an exact 40-character SHA")
    if git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("source repository is dirty")
    origin = normalize_origin(str(git(repo, "remote", "get-url", "origin")))
    if origin != SOURCE_REPO:
        raise ValueError(f"source origin {origin!r} does not match {SOURCE_REPO!r}")
    commit = str(git(repo, "rev-parse", f"{requested_commit}^{{commit}}"))
    branch_commit = str(git(repo, "rev-parse", f"refs/heads/{source_branch}^{{commit}}"))
    subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", commit, branch_commit],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    entry = bytes(git(repo, "ls-tree", "-z", commit, "--", SOURCE_PATH, binary=True))
    entries = [item for item in entry.split(b"\0") if item]
    if len(entries) != 1 or b"\t" not in entries[0]:
        raise ValueError(f"source path does not resolve to one Git entry: {SOURCE_PATH}")
    metadata, path = entries[0].split(b"\t", 1)
    mode, object_type, blob = metadata.decode().split()
    if path.decode() != SOURCE_PATH or object_type != "blob" or mode not in {"100644", "100755"}:
        raise ValueError("source OpenAPI is not a regular Git blob")
    content = bytes(git(repo, "show", f"{commit}:{SOURCE_PATH}", binary=True))
    return commit, blob, mode, content


def expected_files(
    repo: Path, source_branch: str, requested_commit: str
) -> tuple[bytes, bytes]:
    commit, blob, mode, source = committed_source(repo, source_branch, requested_commit)
    document = yaml.safe_load(source)
    if (
        not isinstance(document, dict)
        or document.get("openapi") != "3.0.3"
        or not isinstance(document.get("paths"), dict)
    ):
        raise ValueError("Gym source is not the canonical OpenAPI 3.0.3 document")
    rendered = (json.dumps(document, indent=2) + "\n").encode()
    lock = {
        "generated_path": DESTINATION.relative_to(ROOT).as_posix(),
        "generated_sha256": hashlib.sha256(rendered).hexdigest(),
        "generated_with": GENERATOR,
        "schema_version": 1,
        "source_blob_sha": blob,
        "source_branch": source_branch,
        "source_commit": commit,
        "source_mode": mode,
        "source_path": SOURCE_PATH,
        "source_repo": SOURCE_REPO,
        "source_sha256": hashlib.sha256(source).hexdigest(),
    }
    return rendered, (json.dumps(lock, indent=2, sort_keys=True) + "\n").encode()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--source-repo-dir", type=Path, required=True)
    parser.add_argument("--source-branch", required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    try:
        expected = expected_files(
            args.source_repo_dir.resolve(), args.source_branch, args.source_commit
        )
        stale = [
            path
            for path, content in zip((DESTINATION, LOCK), expected)
            if not path.is_file() or path.read_bytes() != content
        ]
        if args.check:
            if stale:
                print(
                    "Tempera Gym OpenAPI artifacts are stale: "
                    + ", ".join(path.relative_to(ROOT).as_posix() for path in stale),
                    file=sys.stderr,
                )
                return 1
            print(f"Tempera Gym OpenAPI matches {SOURCE_REPO}@{args.source_commit}.")
            return 0
        for path, content in zip((DESTINATION, LOCK), expected):
            path.write_bytes(content)
            print(f"wrote {path.relative_to(ROOT)}")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError, yaml.YAMLError) as error:
        print(f"Tempera Gym OpenAPI sync failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
