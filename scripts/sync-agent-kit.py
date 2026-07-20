#!/usr/bin/env python3
"""Synchronize the committed Tempera agent kit into one consumer repository."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any


BEGIN = "<!-- TEMPERA-AGENT-KIT:BEGIN -->"
END = "<!-- TEMPERA-AGENT-KIT:END -->"
GENERATOR_NAME = "sync-agent-kit.py"
GENERATOR_VERSION = "1"
LOCK_SCHEMA_VERSION = 1
SOURCE_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SOURCE_BRANCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
SOURCE_COMMIT = re.compile(r"^(?:HEAD|[0-9a-f]{40})$")


def run_git(repo: Path, *args: str, binary: bool = False) -> bytes | str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout if binary else result.stdout.decode().strip()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_relative(value: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("paths must be non-empty strings")
    if "\\" in value or any(ord(character) < 32 for character in value):
        raise ValueError(f"unsafe relative path: {value}")
    posix = PurePosixPath(value)
    if posix.is_absolute() or ".." in posix.parts or "." in posix.parts:
        raise ValueError(f"unsafe relative path: {value}")
    return Path(*posix.parts)


def ensure_no_symlink_components(root: Path, relative: Path) -> None:
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"refusing symlink destination component: {current}")


def regular_mode(path: Path) -> str:
    return "100755" if path.stat().st_mode & 0o111 else "100644"


def atomic_write(path: Path, data: bytes, mode: str = "100644") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError(f"refusing symlink destination: {path}")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.chmod(temporary, 0o755 if mode == "100755" else 0o644)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def replace_managed(existing: str, managed: str) -> str:
    block = f"{BEGIN}\n{managed.rstrip()}\n{END}"
    begin_count = existing.count(BEGIN)
    end_count = existing.count(END)
    if begin_count == 0 and end_count == 0:
        prefix = existing.rstrip()
        return f"{prefix}\n\n{block}\n" if prefix else f"{block}\n"
    if begin_count != 1 or end_count != 1 or existing.index(BEGIN) > existing.index(END):
        raise ValueError("AGENTS.md has malformed managed markers")
    before = existing.split(BEGIN, 1)[0].rstrip()
    after = existing.split(END, 1)[1].lstrip().rstrip()
    return "\n\n".join(part for part in (before, block, after) if part) + "\n"


def normalize_github_remote(value: str) -> str | None:
    match = re.fullmatch(r"git@github\.com:([^/]+/[^/]+?)(?:\.git)?", value)
    if match:
        return match.group(1)
    match = re.fullmatch(r"ssh://git@github\.com/([^/]+/[^/]+?)(?:\.git)?/?", value)
    if match:
        return match.group(1)
    match = re.fullmatch(r"https://github\.com/([^/]+/[^/]+?)(?:\.git)?/?", value)
    return match.group(1) if match else None


def validate_source(source_root: Path, source_repo: str, source_branch: str, commitish: str) -> str:
    if not SOURCE_REPO.fullmatch(source_repo):
        raise ValueError("source repo must be an owner/name GitHub repository")
    if not SOURCE_BRANCH.fullmatch(source_branch) or ".." in source_branch or "//" in source_branch:
        raise ValueError("source branch is unsafe")
    if not SOURCE_COMMIT.fullmatch(commitish):
        raise ValueError("source commit must be HEAD or 40 lowercase hexadecimal characters")
    if run_git(source_root, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("source repository is dirty")
    origin = normalize_github_remote(str(run_git(source_root, "remote", "get-url", "origin")))
    if origin != source_repo:
        raise ValueError(f"source origin {origin!r} does not match {source_repo!r}")
    commit = str(run_git(source_root, "rev-parse", f"{commitish}^{{commit}}"))
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("source commit must resolve to 40 lowercase hexadecimal characters")
    remote_ref = f"refs/remotes/origin/{source_branch}"
    run_git(source_root, "rev-parse", f"{remote_ref}^{{commit}}")
    subprocess.run(
        ["git", "-C", str(source_root), "merge-base", "--is-ancestor", commit, remote_ref],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return commit


def committed_file(source_root: Path, commit: str, path: str) -> tuple[str, str, bytes]:
    tree_entry = run_git(source_root, "ls-tree", "-z", commit, "--", path, binary=True)
    assert isinstance(tree_entry, bytes)
    entries = [entry for entry in tree_entry.split(b"\0") if entry]
    if len(entries) != 1 or b"\t" not in entries[0]:
        raise ValueError(f"source path does not resolve to one Git entry: {path}")
    metadata, recorded_path = entries[0].split(b"\t", 1)
    mode, object_type, blob = metadata.decode().split()
    if recorded_path.decode() != path or object_type != "blob" or mode not in {"100644", "100755"}:
        raise ValueError(f"source is not a regular Git file: {path}")
    content = run_git(source_root, "show", f"{commit}:{path}", binary=True)
    assert isinstance(content, bytes)
    return blob, mode, content


def require_keys(value: dict[str, Any], expected: set[str], context: str) -> None:
    actual = set(value)
    if actual != expected:
        raise ValueError(
            f"{context} keys differ (missing={sorted(expected - actual)}, unknown={sorted(actual - expected)})"
        )


def load_manifest(data: bytes) -> dict[str, Any]:
    value = json.loads(data)
    if not isinstance(value, dict):
        raise ValueError("agent-kit manifest must be an object")
    require_keys(value, {"schema_version", "kit_version", "files", "managed_agents_block"}, "manifest")
    if value["schema_version"] != 1:
        raise ValueError("unsupported agent-kit manifest schema")
    if not isinstance(value["kit_version"], str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", value["kit_version"]):
        raise ValueError("kit_version must be a semantic version")
    if not isinstance(value["files"], list) or not value["files"]:
        raise ValueError("manifest files must be a non-empty array")
    if not isinstance(value["managed_agents_block"], str) or not value["managed_agents_block"]:
        raise ValueError("managed_agents_block must be a non-empty path")
    destinations: set[str] = set()
    for index, item in enumerate(value["files"]):
        if not isinstance(item, dict):
            raise ValueError(f"files[{index}] must be an object")
        require_keys(item, {"source", "destination"}, f"files[{index}]")
        safe_relative(item["source"])
        destination = safe_relative(item["destination"]).as_posix()
        folded_destination = destination.casefold()
        allowed_destination = (
            folded_destination.startswith(".codex/skills/tempera-")
            or folded_destination.startswith(".tempera/agent-kit/")
            or folded_destination == "scripts/sync-agent-kit.py"
        )
        if not allowed_destination:
            raise ValueError(f"destination is outside the agent-kit allowlist: {destination}")
        if folded_destination in destinations or folded_destination in {
            "agents.md",
            ".tempera/agent-kit.lock.json",
        }:
            raise ValueError(f"duplicate or reserved destination: {destination}")
        destinations.add(folded_destination)
    safe_relative(value["managed_agents_block"])
    return value


def synchronize(args: argparse.Namespace) -> tuple[str, list[str]]:
    source_dir = args.source_dir.resolve()
    source_root = Path(str(run_git(source_dir, "rev-parse", "--show-toplevel")))
    commit = validate_source(source_root, args.source_repo, args.source_branch, args.source_commit)
    source_prefix = source_dir.relative_to(source_root).as_posix()

    def source_path(relative: str) -> str:
        safe = safe_relative(relative).as_posix()
        return f"{source_prefix}/{safe}" if source_prefix != "." else safe

    def committed(relative: str) -> tuple[str, str, str, bytes]:
        path = source_path(relative)
        blob, mode, content = committed_file(source_root, commit, path)
        return path, blob, mode, content

    manifest_path, manifest_blob, manifest_mode, manifest_bytes = committed("agent-kit-manifest.json")
    manifest = load_manifest(manifest_bytes)
    repo_root = args.repo_root.resolve()
    actual_root = Path(str(run_git(repo_root, "rev-parse", "--show-toplevel"))).resolve()
    if actual_root != repo_root:
        raise ValueError("repo root must be a Git worktree")
    mismatches: list[str] = []
    locked_files: list[dict[str, str]] = []

    for item in manifest["files"]:
        path, blob, mode, content = committed(item["source"])
        destination = safe_relative(item["destination"])
        target = repo_root / destination
        ensure_no_symlink_components(repo_root, destination)
        if (
            not target.exists()
            or not target.is_file()
            or target.read_bytes() != content
            or regular_mode(target) != mode
        ):
            mismatches.append(destination.as_posix())
            if args.mode == "sync":
                atomic_write(target, content, mode)
        locked_files.append(
            {
                "source_path": path,
                "source_blob_sha": blob,
                "source_mode": mode,
                "source_sha256": digest(content),
                "destination": destination.as_posix(),
                "output_sha256": digest(content),
                "output_mode": mode,
            }
        )

    managed_path, managed_blob, managed_mode, managed_bytes = committed(manifest["managed_agents_block"])
    managed = managed_bytes.decode()
    if BEGIN in managed or END in managed:
        raise ValueError("managed source must not contain synchronization markers")
    agents_path = repo_root / "AGENTS.md"
    ensure_no_symlink_components(repo_root, Path("AGENTS.md"))
    existing = agents_path.read_text() if agents_path.exists() else ""
    agents_mode = regular_mode(agents_path) if agents_path.exists() and agents_path.is_file() else "100644"
    desired = replace_managed(existing, managed)
    if existing != desired:
        mismatches.append("AGENTS.md#managed")
        if args.mode == "sync":
            atomic_write(agents_path, desired.encode(), agents_mode)

    lock = {
        "schema_version": LOCK_SCHEMA_VERSION,
        "kit_version": manifest["kit_version"],
        "generator": {"name": GENERATOR_NAME, "version": GENERATOR_VERSION},
        "source": {
            "repo": args.source_repo,
            "branch": args.source_branch,
            "commit": commit,
            "manifest_path": manifest_path,
            "manifest_blob_sha": manifest_blob,
            "manifest_mode": manifest_mode,
            "manifest_sha256": digest(manifest_bytes),
        },
        "files": sorted(locked_files, key=lambda item: item["destination"]),
        "managed_agents": {
            "source_path": managed_path,
            "source_blob_sha": managed_blob,
            "source_mode": managed_mode,
            "source_sha256": digest(managed_bytes),
            "destination": "AGENTS.md#managed",
            "output_sha256": digest(desired.encode()),
            "output_mode": agents_mode,
        },
    }
    lock_path = repo_root / ".tempera" / "agent-kit.lock.json"
    lock_bytes = (json.dumps(lock, indent=2, sort_keys=True) + "\n").encode()
    ensure_no_symlink_components(repo_root, Path(".tempera/agent-kit.lock.json"))
    if (
        not lock_path.exists()
        or not lock_path.is_file()
        or lock_path.read_bytes() != lock_bytes
        or regular_mode(lock_path) != "100644"
    ):
        mismatches.append(".tempera/agent-kit.lock.json")
        if args.mode == "sync":
            atomic_write(lock_path, lock_bytes)
    return commit, sorted(set(mismatches))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("sync", "check"), required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--source-repo", required=True)
    parser.add_argument("--source-branch", required=True)
    parser.add_argument("--source-commit", default="HEAD")
    args = parser.parse_args()
    try:
        commit, mismatches = synchronize(args)
        if args.mode == "check" and mismatches:
            print("agent-kit drift: " + ", ".join(mismatches), file=sys.stderr)
            return 1
        action = "synchronized" if args.mode == "sync" else "verified"
        print(f"{action} agent kit {args.source_repo}@{commit}")
        return 0
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"agent-kit error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
