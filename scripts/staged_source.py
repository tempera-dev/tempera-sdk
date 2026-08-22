#!/usr/bin/env python3
"""Fail-closed validation for exact clean unpublished producer inputs."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


SOURCE_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SOURCE_BRANCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
SOURCE_COMMIT = re.compile(r"^[0-9a-f]{40}$")


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise ValueError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def canonical_repository(remote: str) -> str | None:
    for pattern in (
        r"git@github\.com:([^/]+/[^/]+?)(?:\.git)?",
        r"ssh://git@github\.com/([^/]+/[^/]+?)(?:\.git)?/?",
        r"https://github\.com/([^/]+/[^/]+?)(?:\.git)?/?",
    ):
        match = re.fullmatch(pattern, remote)
        if match:
            return match.group(1)
    return None


def validate_exact_local_source(
    repo: Path,
    source_repo: str,
    source_branch: str,
    source_commit: str,
) -> str:
    """Require an exact SHA at both checked-out HEAD and named local branch."""

    if not SOURCE_REPO.fullmatch(source_repo):
        raise ValueError("source repo must be an owner/name GitHub repository")
    if not SOURCE_BRANCH.fullmatch(source_branch) or ".." in source_branch or "//" in source_branch:
        raise ValueError("source branch is unsafe")
    if not SOURCE_COMMIT.fullmatch(source_commit):
        raise ValueError("staged-local source commit must be an exact 40-character SHA")
    if git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("source repository is dirty")
    origin = canonical_repository(git(repo, "remote", "get-url", "origin"))
    if origin != source_repo:
        raise ValueError(f"source origin {origin!r} does not match {source_repo!r}")
    commit = git(repo, "rev-parse", f"{source_commit}^{{commit}}")
    branch_head = git(repo, "rev-parse", f"refs/heads/{source_branch}^{{commit}}")
    checkout_head = git(repo, "rev-parse", "HEAD^{commit}")
    if commit != branch_head or commit != checkout_head:
        raise ValueError(
            "staged-local source commit must equal both the local branch head "
            "and the checked-out HEAD"
        )
    return commit
