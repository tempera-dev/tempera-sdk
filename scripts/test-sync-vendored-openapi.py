#!/usr/bin/env python3
"""Focused tests for branch-head content equivalence of vendored OpenAPI."""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("sync-vendored-openapi.py")
SPEC = importlib.util.spec_from_file_location("sync_vendored_openapi", SCRIPT)
assert SPEC and SPEC.loader
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)

SOURCE_REPO = "tempera-dev/tempera-workflows"
SOURCE_PATH = "sdks/openapi/tempera-workflows-api.json"


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args],
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()


def commit_all(repo: Path, message: str) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def create_source_repo(repo: Path) -> tuple[Path, str]:
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "Tempera SDK test")
    git(repo, "config", "user.email", "sdk-test@tempera.invalid")
    git(repo, "remote", "add", "origin", f"https://github.com/{SOURCE_REPO}.git")
    source = repo / SOURCE_PATH
    source.parent.mkdir(parents=True)
    source.write_text('{"openapi":"3.1.0","paths":{}}\n', encoding="utf-8")
    commit = commit_all(repo, "initial contract")
    git(repo, "update-ref", "refs/remotes/origin/main", commit)
    return source, commit


def verify(repo: Path, commit: str) -> tuple[str, str, str, bytes]:
    return sync.current_branch_equivalent_file(
        sync.load_source_lock_module(),
        repo,
        SOURCE_REPO,
        "main",
        commit,
        SOURCE_PATH,
    )


class CurrentBranchEquivalentFileTest(unittest.TestCase):
    def test_unrelated_descendant_keeps_exact_pinned_source_valid(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="tempera-sdk-content-equivalence-"
        ) as directory:
            repo = Path(directory)
            _, pinned = create_source_repo(repo)
            (repo / "README.md").write_text("implementation-only change\n")
            current = commit_all(repo, "change unrelated file")
            git(repo, "update-ref", "refs/remotes/origin/main", current)

            commit, blob, mode, content = verify(repo, pinned)

            self.assertEqual(commit, pinned)
            self.assertRegex(blob, r"^[0-9a-f]{40}$")
            self.assertEqual(mode, "100644")
            self.assertEqual(content, b'{"openapi":"3.1.0","paths":{}}\n')

    def test_source_content_drift_requires_revendor(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="tempera-sdk-content-equivalence-"
        ) as directory:
            repo = Path(directory)
            source, pinned = create_source_repo(repo)
            source.write_text(
                '{"openapi":"3.1.0","paths":{"/v1/new":{}}}\n',
                encoding="utf-8",
            )
            current = commit_all(repo, "change contract")
            git(repo, "update-ref", "refs/remotes/origin/main", current)

            with self.assertRaisesRegex(
                ValueError,
                rf"source tree entry drift for {SOURCE_PATH}.*re-vendor",
            ):
                verify(repo, pinned)

    def test_source_mode_drift_requires_revendor(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="tempera-sdk-content-equivalence-"
        ) as directory:
            repo = Path(directory)
            source, pinned = create_source_repo(repo)
            source.chmod(0o755)
            git(repo, "update-index", "--chmod=+x", SOURCE_PATH)
            git(repo, "commit", "-m", "change contract mode")
            current = git(repo, "rev-parse", "HEAD")
            git(repo, "update-ref", "refs/remotes/origin/main", current)

            with self.assertRaisesRegex(ValueError, "source tree entry drift"):
                verify(repo, pinned)

    def test_non_ancestor_pin_is_rejected_even_when_content_matches(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="tempera-sdk-content-equivalence-"
        ) as directory:
            repo = Path(directory)
            _, pinned = create_source_repo(repo)
            git(repo, "checkout", "-b", "side")
            (repo / "side.txt").write_text("side\n", encoding="utf-8")
            side = commit_all(repo, "side commit")
            git(repo, "checkout", "main")
            (repo / "main.txt").write_text("main\n", encoding="utf-8")
            current = commit_all(repo, "main commit")
            git(repo, "update-ref", "refs/remotes/origin/main", current)
            self.assertNotEqual(pinned, side)

            with self.assertRaises(subprocess.CalledProcessError):
                verify(repo, side)

    def test_dirty_checkout_and_wrong_origin_remain_rejected(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="tempera-sdk-content-equivalence-"
        ) as directory:
            repo = Path(directory)
            _, pinned = create_source_repo(repo)
            (repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source repository is dirty"):
                verify(repo, pinned)
            (repo / "dirty.txt").unlink()

            git(
                repo,
                "remote",
                "set-url",
                "origin",
                "https://github.com/example/wrong.git",
            )
            with self.assertRaisesRegex(ValueError, "source origin .* does not match"):
                verify(repo, pinned)


if __name__ == "__main__":
    unittest.main()
