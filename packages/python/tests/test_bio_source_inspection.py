import ast
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import tempera_sdk
from tempera_sdk import bio_source_inspection as verifier


ROOT = Path(__file__).resolve().parents[3]
LOCK_PATH = ROOT / "contracts/bio-source-inspection-sdk-consumer.staging.lock.json"
FIXTURE_PATH = ROOT / "contracts/bio-source-inspection-sdk-consumer-fixtures.json"
RECEIPT_PATH = ROOT / "contracts/bio-source-inspection-sdk-consumer-verification.json"


class BioSourceInspectionSdkConsumerTests(unittest.TestCase):
    maxDiff = None

    def load_lock(self):
        return json.loads(LOCK_PATH.read_text())

    def load_fixture(self):
        return json.loads(FIXTURE_PATH.read_text())

    def assert_rejected(self, *, lock=None, fixture=None, lock_bytes=None, fixture_bytes=None):
        if lock_bytes is None:
            if lock is None:
                lock_bytes = LOCK_PATH.read_bytes()
            else:
                lock_bytes = (json.dumps(lock, indent=2, sort_keys=True) + "\n").encode()
        if fixture_bytes is None:
            if fixture is None:
                fixture_bytes = FIXTURE_PATH.read_bytes()
            else:
                fixture_bytes = (json.dumps(fixture, indent=2, sort_keys=True) + "\n").encode()
        with self.assertRaises(verifier.VerificationError):
            verifier.verify_bytes(lock_bytes, fixture_bytes)

    def test_exact_cross_repo_fixture_verifies_without_authority(self):
        receipt = verifier.verify_paths(LOCK_PATH, FIXTURE_PATH)
        self.assertEqual(tuple(receipt["verified_domains"]), verifier.DOMAINS)
        self.assertEqual(
            receipt["upstream_commits"],
            {"bio": verifier.BIO_COMMIT, "mcp": verifier.MCP_COMMIT},
        )
        self.assertEqual(
            receipt["result"], "staging_cross_consumer_conformant_not_admitted"
        )
        self.assertFalse(receipt["runtime_registration"])
        self.assertFalse(any(receipt["authority"].values()))
        self.assertEqual(receipt["content_digest"], verifier.content_digest(receipt))
        self.assertEqual(
            verifier.receipt_bytes(receipt),
            verifier.canonical_json(receipt),
        )

    def test_committed_handoff_receipt_is_exactly_regenerated(self):
        receipt = verifier.verify_paths(LOCK_PATH, FIXTURE_PATH)
        expected = verifier.receipt_bytes(receipt) + b"\n"
        self.assertEqual(RECEIPT_PATH.read_bytes(), expected)
        committed = json.loads(RECEIPT_PATH.read_bytes())
        self.assertEqual(committed, receipt)
        self.assertEqual(
            committed["content_digest"],
            "sha256:8534bd1d7823e34d3d0d2489c337bb6bbe0063a3c36066071abdadf129b75132",
        )
        self.assertEqual(
            committed["result"],
            "staging_cross_consumer_conformant_not_admitted",
        )
        self.assertFalse(any(committed["authority"].values()))

    def test_calls_the_unexported_sdk_verifier_and_no_network_stack(self):
        expected = (
            ROOT
            / "packages/python/src/tempera_sdk/bio_source_inspection.py"
        ).resolve()
        self.assertEqual(Path(verifier.__file__).resolve(), expected)
        self.assertNotIn("bio_source_inspection", tempera_sdk.__all__)
        self.assertNotIn("verify_paths", tempera_sdk.__all__)
        self.assertNotIn("bio_source_inspection", tempera_sdk._LAZY_EXPORTS)
        source = expected.read_text()
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(ast.parse(source))
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertTrue({"hashlib", "json", "re"}.issubset(imported))
        self.assertTrue(
            imported.isdisjoint(
                {"http", "requests", "socket", "subprocess", "urllib", "aiohttp"}
            )
        )
        lock = self.load_lock()
        self.assertEqual(
            lock["consumer"]["implementation"],
            "packages/python/src/tempera_sdk/bio_source_inspection.py",
        )
        self.assertFalse(lock["consumer"]["package_root_export"])
        self.assertFalse(lock["consumer"]["mcp_tool_registered"])
        self.assertFalse(lock["consumer"]["workflow_registered"])

    def test_rejects_all_upstream_commit_and_artifact_pin_drift(self):
        for upstream in ("bio", "mcp"):
            with self.subTest(upstream=upstream, field="commit"):
                lock = self.load_lock()
                lock["upstreams"][upstream]["commit"] = "0" * 40
                lock["content_digest"] = verifier.content_digest(lock)
                self.assert_rejected(lock=lock)
            artifacts = self.load_lock()["upstreams"][upstream]["artifacts"]
            for path in artifacts:
                for field, replacement in (
                    ("git_blob", "0" * 40),
                    ("sha256", "0" * 64),
                ):
                    with self.subTest(upstream=upstream, path=path, field=field):
                        lock = self.load_lock()
                        lock["upstreams"][upstream]["artifacts"][path][field] = replacement
                        lock["content_digest"] = verifier.content_digest(lock)
                        self.assert_rejected(lock=lock)

    def test_rejects_every_consumer_authority_or_admission_drift(self):
        mutations = (
            ("status", "admitted"),
            ("claim_ceiling", "scientific_truth"),
            ("consumer.package_root_export", True),
            ("consumer.mcp_tool_registered", True),
            ("consumer.workflow_registered", True),
            ("consumer.network", "allowed"),
            ("consumer.source_admission", True),
            ("consumer.evidence_stage_promotion", True),
            ("consumer.graph_write", True),
            ("consumer.proof_promotion", True),
            ("consumer.physical_action", True),
            ("compatibility.rollout", "production"),
        )
        for dotted, replacement in mutations:
            with self.subTest(field=dotted):
                lock = self.load_lock()
                target = lock
                parts = dotted.split(".")
                for part in parts[:-1]:
                    target = target[part]
                target[parts[-1]] = replacement
                lock["content_digest"] = verifier.content_digest(lock)
                self.assert_rejected(lock=lock)

    def test_rejects_every_domain_status_registration_authority_and_binding_drift(self):
        for index, domain in enumerate(verifier.DOMAINS):
            mutations = (
                (("workflow_receipt", "status"), "admitted"),
                (("workflow_receipt", "eligibility", "training"), True),
                (("workflow_receipt", "eligibility", "evaluation"), True),
                (("workflow_receipt", "boundaries", "graph_authority"), "write"),
                (("workflow_receipt", "boundaries", "proof_promotion"), "allowed"),
                (("consumer_verification", "result", "source_admitted"), True),
                (("consumer_verification", "consumer_registration", "sdk_adapter"), True),
                (("consumer_verification", "consumer_registration", "mcp_tool"), True),
                (("consumer_verification", "authority", "graph_write"), True),
                (("consumer_verification", "authority", "physical_action"), True),
            )
            for path, replacement in mutations:
                with self.subTest(domain=domain, path=path):
                    fixture = self.load_fixture()
                    target = fixture["fixtures"][index]
                    for part in path[:-1]:
                        target = target[part]
                    target[path[-1]] = replacement
                    target_receipt = fixture["fixtures"][index][path[0]]
                    target_receipt["content_digest"] = verifier.content_digest(target_receipt)
                    fixture["content_digest"] = verifier.content_digest(fixture)
                    self.assert_rejected(fixture=fixture)

    def test_rejects_ood_domain_order_count_shape_and_noncanonical_values(self):
        fixture = self.load_fixture()
        fixture["fixtures"].reverse()
        fixture["content_digest"] = verifier.content_digest(fixture)
        self.assert_rejected(fixture=fixture)

        fixture = self.load_fixture()
        fixture["fixtures"].append(copy.deepcopy(fixture["fixtures"][0]))
        fixture["content_digest"] = verifier.content_digest(fixture)
        self.assert_rejected(fixture=fixture)

        fixture = self.load_fixture()
        fixture["fixtures"][0]["domain"] = "unknown_domain"
        fixture["content_digest"] = verifier.content_digest(fixture)
        self.assert_rejected(fixture=fixture)

        fixture = self.load_fixture()
        fixture["fixtures"][0]["unexpected"] = False
        fixture["content_digest"] = verifier.content_digest(fixture)
        self.assert_rejected(fixture=fixture)

        self.assert_rejected(lock_bytes=b"{not-json", fixture_bytes=FIXTURE_PATH.read_bytes())
        self.assert_rejected(
            lock_bytes=LOCK_PATH.read_bytes(),
            fixture_bytes=b'{"value":NaN}',
        )

    def test_rejects_semantically_equal_fixture_with_different_bytes(self):
        fixture = self.load_fixture()
        compact = verifier.canonical_json(fixture)
        self.assertEqual(json.loads(compact), fixture)
        self.assertNotEqual(compact, FIXTURE_PATH.read_bytes())
        self.assert_rejected(fixture_bytes=compact)

    def test_receipt_bytes_are_identical_across_independent_hash_seeds(self):
        program = (
            "from pathlib import Path;"
            "from tempera_sdk.bio_source_inspection import verify_paths,receipt_bytes;"
            f"print(receipt_bytes(verify_paths(Path({str(LOCK_PATH)!r}),"
            f"Path({str(FIXTURE_PATH)!r}))).decode())"
        )
        outputs = []
        for seed in ("1", "2", "97", "211", "99991"):
            env = os.environ.copy()
            env["PYTHONHASHSEED"] = seed
            env["PYTHONPATH"] = str(ROOT / "packages/python/src")
            completed = subprocess.run(
                [sys.executable, "-c", program],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            outputs.append(completed.stdout)
        self.assertEqual(len(set(outputs)), 1)
        self.assertEqual(
            json.loads(outputs[0])["content_digest"],
            verifier.verify_paths(LOCK_PATH, FIXTURE_PATH)["content_digest"],
        )

    def test_verify_paths_performs_real_local_file_io_and_propagates_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.json"
            with self.assertRaises(FileNotFoundError):
                verifier.verify_paths(missing, FIXTURE_PATH)


if __name__ == "__main__":
    unittest.main()
