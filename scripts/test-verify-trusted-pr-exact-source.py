#!/usr/bin/env python3
"""Adversarial tests for the trusted-base PR exact-source verifier."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("verify-trusted-pr-exact-source.py")
SPEC = importlib.util.spec_from_file_location("trusted_pr_exact_source", SCRIPT)
assert SPEC and SPEC.loader
trusted = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(trusted)


def git(repo: Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *arguments], text=True, stderr=subprocess.STDOUT
    ).strip()


def commit(repo: Path, message: str) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def source_lock(product_name: str, generated: bytes) -> dict[str, object]:
    product = trusted.PRODUCTS[product_name]
    digest = hashlib.sha256(generated).hexdigest()
    return {
        "schema_version": 1,
        "source_repo": product["repository"],
        "source_branch": product["source_branch"],
        "source_commit": "a" * 40,
        "source_path": product["source_path"],
        "source_blob_sha": "b" * 40,
        "source_mode": "100644",
        "source_sha256": digest,
        "generated_with": product["generated_with"],
        "generated_path": product["generated_path"],
        "generated_sha256": digest,
    }


def gap(repository: str) -> dict[str, str]:
    return {
        "repository": repository,
        "source_commit": "c" * 40,
        "blocker": "expired reader access",
        "owner": "Tempera",
        "remediation": "verify current source",
        "producer_ci_url": f"https://github.com/{repository}/actions/runs/1",
        "review_after": "2026-08-15",
    }


def write_candidate_inputs(repo: Path, ledger: list[dict[str, str]]) -> None:
    for product_name, product in trusted.PRODUCTS.items():
        generated = (f'{{"product":"{product_name}"}}\n').encode("utf-8")
        generated_path = repo / product["generated_path"]
        generated_path.parent.mkdir(parents=True, exist_ok=True)
        generated_path.write_bytes(generated)
        write_json(repo / product["lock_path"], source_lock(product_name, generated))
    write_json(repo / trusted.GAP_LEDGER_PATH, {"schema_version": 1, "gaps": ledger})


class TrustedPrExactSourceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(prefix="trusted-pr-source-")
        self.repo = Path(self.directory.name)
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.name", "Tempera SDK test")
        git(self.repo, "config", "user.email", "sdk-test@tempera.invalid")
        self.repositories = sorted(trusted.PRODUCT_BY_REPOSITORY)
        self.base_gaps = [gap(repository) for repository in self.repositories]
        write_candidate_inputs(self.repo, self.base_gaps)
        self.base = commit(self.repo, "trusted base")

    def tearDown(self) -> None:
        self.directory.cleanup()

    def candidate_removing(self, repository: str) -> str:
        retained = [entry for entry in self.base_gaps if entry["repository"] != repository]
        write_json(
            self.repo / trusted.GAP_LEDGER_PATH,
            {"schema_version": 1, "gaps": retained},
        )
        return commit(self.repo, f"remove verified gap for {repository}")

    def test_valid_candidate_outputs_only_the_removed_product(self) -> None:
        repository = "tempera-dev/tempera-bio"
        candidate = self.candidate_removing(repository)

        manifest = trusted.validate_candidate(self.repo, self.base, candidate)

        self.assertEqual(manifest["trusted_base_commit"], self.base)
        self.assertEqual(manifest["candidate_commit"], candidate)
        self.assertEqual(
            [product["repository"] for product in manifest["verified_products"]],
            [repository],
        )
        self.assertEqual(
            trusted.selected_installation_repositories(manifest), "tempera-bio"
        )

    def test_ledger_date_or_metadata_renewal_is_rejected(self) -> None:
        changed = copy.deepcopy(self.base_gaps)
        changed[0]["review_after"] = "2027-01-01"
        write_json(
            self.repo / trusted.GAP_LEDGER_PATH,
            {"schema_version": 1, "gaps": changed},
        )
        candidate = commit(self.repo, "renew expired review")

        with self.assertRaisesRegex(
            trusted.VerificationError, "may only remove exact existing entries"
        ):
            trusted.validate_candidate(self.repo, self.base, candidate)

    def test_ledger_top_level_metadata_is_rejected(self) -> None:
        candidate_ledger = {
            "schema_version": 1,
            "gaps": self.base_gaps[1:],
            "untrusted_note": "must not be smuggled into a ledger-removal PR",
        }
        write_json(self.repo / trusted.GAP_LEDGER_PATH, candidate_ledger)
        candidate = commit(self.repo, "smuggle top-level ledger metadata")

        with self.assertRaisesRegex(trusted.VerificationError, "unsupported schema"):
            trusted.validate_candidate(self.repo, self.base, candidate)

    def test_candidate_symlink_is_rejected_without_following_it(self) -> None:
        repository = "tempera-dev/tempera-bio"
        self.candidate_removing(repository)
        product = trusted.PRODUCTS[trusted.PRODUCT_BY_REPOSITORY[repository]]
        lock_path = self.repo / product["lock_path"]
        lock_path.unlink()
        os.symlink("/etc/passwd", lock_path)
        candidate = commit(self.repo, "replace lock with symlink")

        with self.assertRaisesRegex(trusted.VerificationError, "regular 100644 blob"):
            trusted.validate_candidate(self.repo, self.base, candidate)

    def test_candidate_oversized_generated_blob_is_rejected(self) -> None:
        repository = "tempera-dev/tempera-bio"
        self.candidate_removing(repository)
        product = trusted.PRODUCTS[trusted.PRODUCT_BY_REPOSITORY[repository]]
        generated_path = self.repo / product["generated_path"]
        generated_path.write_bytes(b"x" * (trusted.GENERATED_MAX_BYTES + 1))
        candidate = commit(self.repo, "oversize candidate generated input")

        with self.assertRaisesRegex(trusted.VerificationError, "exceeds the"):
            trusted.validate_candidate(self.repo, self.base, candidate)

    def test_candidate_workflow_and_script_tampering_is_not_read_or_executed(self) -> None:
        """Base helper uses no candidate workflow or script bytes at all."""

        repository = "tempera-dev/tempera-bio"
        self.candidate_removing(repository)
        workflow = self.repo / ".github/workflows/trusted-pr-exact-source.yml"
        workflow.parent.mkdir(parents=True, exist_ok=True)
        workflow.write_text("name: attacker workflow\n", encoding="utf-8")
        script = self.repo / "scripts/verify-trusted-pr-exact-source.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("raise SystemExit('candidate code must never run')\n", encoding="utf-8")
        candidate = commit(self.repo, "tamper untrusted workflow and script")

        manifest = trusted.validate_candidate(self.repo, self.base, candidate)

        self.assertEqual(
            [product["repository"] for product in manifest["verified_products"]],
            [repository],
        )

    def test_verify_one_source_requires_current_head_blob_and_digest(self) -> None:
        with tempfile.TemporaryDirectory(prefix="trusted-pr-source-repo-") as directory:
            source = Path(directory)
            git(source, "init", "-b", "main")
            git(source, "config", "user.name", "Tempera SDK test")
            git(source, "config", "user.email", "sdk-test@tempera.invalid")
            product_name = "temperaBio"
            product_config = trusted.PRODUCTS[product_name]
            source_path = source / product_config["source_path"]
            source_path.parent.mkdir(parents=True)
            payload = b'{"openapi":"3.1.0"}\n'
            source_path.write_bytes(payload)
            head = commit(source, "source contract")
            git(source, "update-ref", "refs/trusted/main", head)
            blob = git(source, "rev-parse", f"{head}:{product_config['source_path']}")
            product = {
                "product": product_name,
                "repository": product_config["repository"],
                "source_branch": "main",
                "source_path": product_config["source_path"],
                "source_commit": head,
                "source_blob_sha": blob,
                "source_sha256": hashlib.sha256(payload).hexdigest(),
                "generated_path": product_config["generated_path"],
                "generated_sha256": hashlib.sha256(payload).hexdigest(),
            }

            trusted.verify_one_source(source, product)
            source_path.write_bytes(b'{"openapi":"3.1.1"}\n')
            changed_head = commit(source, "source changed")
            git(source, "update-ref", "refs/trusted/main", changed_head)
            with self.assertRaisesRegex(trusted.VerificationError, "main is"):
                trusted.verify_one_source(source, product)

    def test_fetch_environment_never_passes_raw_reader_token_to_git(self) -> None:
        old = os.environ.get("CONTRACT_READER_TOKEN")
        os.environ["CONTRACT_READER_TOKEN"] = "reader-secret"
        try:
            environment = trusted.source_environment("reader-secret")
        finally:
            if old is None:
                del os.environ["CONTRACT_READER_TOKEN"]
            else:
                os.environ["CONTRACT_READER_TOKEN"] = old
        self.assertNotIn("CONTRACT_READER_TOKEN", environment)
        self.assertNotIn("reader-secret", "\n".join(environment.values()))
        self.assertEqual(environment["GIT_CONFIG_COUNT"], "1")

    def test_fetch_source_creates_ephemeral_bare_repository_before_git_calls(self) -> None:
        calls: list[tuple[Path, tuple[str, ...], object]] = []

        def fake_git(
            repo: Path, *arguments: str, env: object = None
        ) -> bytes:
            calls.append((repo, arguments, env))
            return b""

        with tempfile.TemporaryDirectory(prefix="trusted-pr-fetch-") as directory:
            destination = Path(directory) / "missing" / "source"
            with patch.object(trusted, "git", side_effect=fake_git):
                trusted.fetch_source(
                    "tempera-dev/tempera-bio", "main", destination, "reader-secret"
                )
            self.assertTrue(destination.is_dir())
        self.assertEqual(calls[0][1], ("init", "--bare"))
        self.assertEqual(calls[1][1][0:3], ("remote", "add", "origin"))
        self.assertEqual(calls[2][1][0:2], ("fetch", "--no-tags"))
        self.assertNotIn("CONTRACT_READER_TOKEN", calls[2][2])


if __name__ == "__main__":
    unittest.main()
