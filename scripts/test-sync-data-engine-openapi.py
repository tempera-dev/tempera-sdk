#!/usr/bin/env python3
"""Focused tests for committed Data Engine source locking."""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("sync-data-engine-openapi.py")
SPEC = importlib.util.spec_from_file_location("sync_data_engine_openapi", SCRIPT)
assert SPEC and SPEC.loader
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


class SourceLockTest(unittest.TestCase):
    def test_route_identity_ignores_parameter_spelling(self) -> None:
        self.assertEqual(
            sync.route_identity("GET", "/v1/projects/{project_id}/campaigns/{campaign_id}"),
            sync.route_identity("GET", "/v1/{parent}/campaigns/{campaignId}"),
        )

    def test_committed_source_uses_git_bytes_and_rejects_dirty_repo(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tempera-sdk-source-lock-") as directory:
            repo = Path(directory)
            git(repo, "init", "-b", "main")
            git(repo, "config", "user.name", "Tempera SDK test")
            git(repo, "config", "user.email", "sdk-test@tempera.invalid")
            git(repo, "remote", "add", "origin", "https://github.com/tempera-dev/data-engine.git")
            source = repo / "api" / "openapi.yaml"
            source.parent.mkdir()
            source.write_text("openapi: 3.1.0\npaths: {}\n", encoding="utf-8")
            git(repo, "add", "api/openapi.yaml")
            git(repo, "commit", "-m", "fixture")
            head = subprocess.check_output(
                ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
            ).strip()
            git(repo, "update-ref", "refs/remotes/origin/main", head)

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


if __name__ == "__main__":
    unittest.main()
