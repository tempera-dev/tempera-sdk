#!/usr/bin/env python3
"""Focused tests for committed Data Engine source locking."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("sync-data-engine-openapi.py")
SPEC = importlib.util.spec_from_file_location("sync_data_engine_openapi", SCRIPT)
assert SPEC and SPEC.loader
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)

CHECK_SCRIPT = Path(__file__).with_name("check-sdk-surface.py")
CHECK_SPEC = importlib.util.spec_from_file_location("check_sdk_surface", CHECK_SCRIPT)
assert CHECK_SPEC and CHECK_SPEC.loader
check_surface = importlib.util.module_from_spec(CHECK_SPEC)
CHECK_SPEC.loader.exec_module(check_surface)


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()


def create_source_repo(repo: Path) -> tuple[Path, str]:
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "Tempera SDK test")
    git(repo, "config", "user.email", "sdk-test@tempera.invalid")
    git(repo, "remote", "add", "origin", "https://github.com/tempera-dev/data-engine.git")
    source = repo / "api" / "openapi.yaml"
    source.parent.mkdir()
    source.write_text("openapi: 3.1.0\npaths: {}\n", encoding="utf-8")
    git(repo, "add", "api/openapi.yaml")
    git(repo, "commit", "-m", "fixture")
    commit = head(repo)
    git(repo, "update-ref", "refs/remotes/origin/main", commit)
    return source, commit


class SourceLockTest(unittest.TestCase):
    def test_route_identity_ignores_parameter_spelling(self) -> None:
        self.assertEqual(
            sync.route_identity("GET", "/v1/projects/{project_id}/campaigns/{campaign_id}"),
            sync.route_identity("GET", "/v1/{parent}/campaigns/{campaignId}"),
        )

    def test_committed_source_uses_git_bytes_and_rejects_dirty_repo(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tempera-sdk-source-lock-") as directory:
            repo = Path(directory)
            source, _ = create_source_repo(repo)

            source_bytes, metadata = sync.committed_source(source)
            self.assertEqual(source_bytes, b"openapi: 3.1.0\npaths: {}\n")
            self.assertEqual(metadata["source_repo"], "tempera-dev/data-engine")
            self.assertEqual(metadata["source_branch"], "main")
            self.assertRegex(metadata["source_commit"], r"^[0-9a-f]{40}$")
            self.assertRegex(metadata["source_blob_sha"], r"^[0-9a-f]{40}$")

            (repo / "dirty-marker").write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source repository is dirty"):
                sync.committed_source(source)
            (repo / "dirty-marker").unlink()

            source.write_text("openapi: 3.1.0\npaths:\n  /new: {}\n", encoding="utf-8")
            git(repo, "add", "api/openapi.yaml")
            git(repo, "commit", "-m", "unpushed fixture")
            with self.assertRaisesRegex(ValueError, "not reachable from origin/main"):
                sync.committed_source(source)

    def test_detached_exact_commit_is_supported(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tempera-sdk-source-lock-") as directory:
            repo = Path(directory)
            source, commit = create_source_repo(repo)
            git(repo, "checkout", "--detach", commit)

            source_bytes, metadata = sync.committed_source(
                source,
                source_commit=commit,
            )
            self.assertEqual(source_bytes, b"openapi: 3.1.0\npaths: {}\n")
            self.assertEqual(metadata["source_branch"], "main")
            self.assertEqual(metadata["source_commit"], commit)

    def test_exact_ancestor_reads_committed_bytes_not_current_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tempera-sdk-source-lock-") as directory:
            repo = Path(directory)
            source, first = create_source_repo(repo)
            source.write_text("openapi: 3.1.1\npaths: {}\n", encoding="utf-8")
            git(repo, "add", "api/openapi.yaml")
            git(repo, "commit", "-m", "newer fixture")
            git(repo, "update-ref", "refs/remotes/origin/main", head(repo))

            source_bytes, metadata = sync.committed_source(source, source_commit=first)
            self.assertEqual(source_bytes, b"openapi: 3.1.0\npaths: {}\n")
            self.assertEqual(metadata["source_commit"], first)

    def test_ambiguous_commit_and_wrong_origin_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tempera-sdk-source-lock-") as directory:
            repo = Path(directory)
            source, _ = create_source_repo(repo)
            with self.assertRaisesRegex(ValueError, "source commit must be HEAD or 40"):
                sync.committed_source(source, source_commit="main~1")
            git(repo, "remote", "set-url", "origin", "https://github.com/example/wrong.git")
            with self.assertRaisesRegex(ValueError, "source origin .* does not match"):
                sync.committed_source(source)

    def test_symlink_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tempera-sdk-source-lock-") as directory:
            repo = Path(directory)
            source, _ = create_source_repo(repo)
            alias = repo / "api" / "alias.yaml"
            alias.symlink_to("openapi.yaml")
            git(repo, "add", "api/alias.yaml")
            git(repo, "commit", "-m", "symlink fixture")
            git(repo, "update-ref", "refs/remotes/origin/main", head(repo))
            with self.assertRaisesRegex(ValueError, "not a symlink"):
                sync.committed_source(alias)

    def test_local_gate_rejects_noncanonical_lock_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tempera-sdk-source-lock-") as directory:
            lock_path = Path(directory) / "data-engine-lock.json"
            lock = json.loads(sync.LOCK.read_text())
            lock["source_repo"] = "example/wrong"
            lock_path.write_text(json.dumps(lock), encoding="utf-8")
            original = check_surface.DATA_ENGINE_OPERATION_LOCK
            check_surface.DATA_ENGINE_OPERATION_LOCK = lock_path
            try:
                surface = json.loads((sync.ROOT / "surface.json").read_text())
                failures = check_surface.validate_data_engine_openapi_bindings(surface)
            finally:
                check_surface.DATA_ENGINE_OPERATION_LOCK = original
            self.assertIn(
                "data-engine OpenAPI operation lock source_repo 'example/wrong' != "
                "'tempera-dev/data-engine'",
                failures,
            )


if __name__ == "__main__":
    unittest.main()
