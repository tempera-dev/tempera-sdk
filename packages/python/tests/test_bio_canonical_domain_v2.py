from __future__ import annotations

import ast
import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "packages/python/src/tempera_sdk/bio_canonical_domain_v2.py"
LOCK = ROOT / "contracts/bio-canonical-domain-v2-sdk.staging.lock.json"
FIXTURE = ROOT / "contracts/bio-canonical-domain-v2-mcp.producer.json"
EXPECTED = ROOT / "contracts/bio-canonical-domain-v2-sdk-consumer-verification.json"
SPEC = importlib.util.spec_from_file_location("bio_canonical_domain_v2", SCRIPT)
VERIFIER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(VERIFIER)


class BioCanonicalDomainV2SdkTests(unittest.TestCase):
    maxDiff = None

    @staticmethod
    def load(path):
        return json.loads(path.read_bytes())

    def assert_rejected(self, *, lock=None, fixture=None, lock_bytes=None, fixture_bytes=None):
        if lock_bytes is None:
            lock_bytes = LOCK.read_bytes() if lock is None else (json.dumps(lock, indent=2, sort_keys=True) + "\n").encode()
        if fixture_bytes is None:
            fixture_bytes = FIXTURE.read_bytes() if fixture is None else (json.dumps(fixture, indent=2, sort_keys=True) + "\n").encode()
        with self.assertRaises(VERIFIER.VerificationError):
            VERIFIER.verify_bytes(lock_bytes, fixture_bytes)

    def test_exact_mcp_receipt_replays_to_committed_sdk_receipt(self):
        receipt = VERIFIER.verify_paths(LOCK, FIXTURE)
        self.assertEqual(VERIFIER.pretty_json(receipt), EXPECTED.read_bytes())
        self.assertEqual(receipt["upstream"]["commit"], VERIFIER.MCP_COMMIT)
        self.assertEqual(receipt["result"], "staging_mcp_v2_receipt_conformant_not_exported")
        self.assertFalse(receipt["package_root_exported"])
        self.assertFalse(receipt["sdk_adapter_registered"])
        self.assertFalse(receipt["runtime_registered"])
        self.assertFalse(any(receipt["authority"].values()))

    def test_exact_six_mcp_artifacts_are_hardcoded_and_source_locked(self):
        lock = self.load(LOCK)
        self.assertEqual(lock["upstream"]["artifacts"], VERIFIER.MCP_ARTIFACTS)
        self.assertEqual(len(VERIFIER.MCP_ARTIFACTS), 6)
        self.assertEqual(lock["upstream"]["commit"], "15fae3667b2898c95b592caab16b55ed67b17638")
        fixture_pin = VERIFIER.MCP_ARTIFACTS[lock["fixture"]["producer_path"]]
        self.assertEqual(fixture_pin["sha256"], VERIFIER.sha256_hex(FIXTURE.read_bytes()))
        self.assertEqual(fixture_pin["git_blob"], VERIFIER.git_blob_hex(FIXTURE.read_bytes()))

    def test_three_domains_preserve_exact_entrypoint_and_result_bindings(self):
        fixture = self.load(FIXTURE)
        receipt = VERIFIER.verify_paths(LOCK, FIXTURE)
        self.assertEqual(set(receipt["verified_domains"]), set(VERIFIER.DOMAINS))
        for domain in VERIFIER.DOMAINS:
            self.assertEqual(
                receipt["verified_domains"][domain], fixture["verified_domains"][domain]
            )
            self.assertEqual(
                receipt["verified_domains"][domain]["entrypoint_ref"],
                VERIFIER.ENTRYPOINT_REFS[domain],
            )

    def test_all_scientific_experiment_receipts_remain_explicitly_absent(self):
        receipt = VERIFIER.verify_paths(LOCK, FIXTURE)
        for domain in VERIFIER.DOMAINS:
            fields = receipt["experiment_receipts_present"][domain]
            self.assertEqual(set(fields), set(VERIFIER.EXPERIMENT_FIELDS))
            self.assertTrue(all(value is False for value in fields.values()))

    def test_raw_fixture_byte_append_compaction_and_missing_file_fail_closed(self):
        self.assert_rejected(fixture_bytes=FIXTURE.read_bytes() + b" ")
        compact = VERIFIER.canonical_json(self.load(FIXTURE))
        self.assertNotEqual(compact, FIXTURE.read_bytes())
        self.assert_rejected(fixture_bytes=compact)
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.json"
            with self.assertRaises(FileNotFoundError):
                VERIFIER.verify_paths(missing, FIXTURE)
            with self.assertRaises(FileNotFoundError):
                VERIFIER.verify_paths(LOCK, missing)

    def test_resealed_upstream_commit_and_every_artifact_pin_drift_are_rejected(self):
        lock = self.load(LOCK)
        lock["upstream"]["commit"] = "0" * 40
        lock["content_digest"] = VERIFIER.content_digest(lock)
        self.assert_rejected(lock=lock)
        for path in VERIFIER.MCP_ARTIFACTS:
            for field, value in (("bytes", 1), ("git_blob", "0" * 40), ("sha256", "0" * 64)):
                lock = self.load(LOCK)
                lock["upstream"]["artifacts"][path][field] = value
                lock["content_digest"] = VERIFIER.content_digest(lock)
                with self.subTest(path=path, field=field):
                    self.assert_rejected(lock=lock)

    def test_domain_result_swap_unknown_domain_extra_field_and_digest_tamper_fail(self):
        fixture = self.load(FIXTURE)
        fixture["verified_domains"]["protein_variant"], fixture["verified_domains"]["metabolic_feasibility"] = (
            fixture["verified_domains"]["metabolic_feasibility"], fixture["verified_domains"]["protein_variant"]
        )
        fixture["content_digest"] = VERIFIER.content_digest(fixture)
        self.assert_rejected(fixture=fixture)

        fixture = self.load(FIXTURE)
        fixture["verified_domains"]["unknown"] = fixture["verified_domains"].pop("neuronal_response")
        fixture["content_digest"] = VERIFIER.content_digest(fixture)
        self.assert_rejected(fixture=fixture)

        fixture = self.load(FIXTURE)
        fixture["verified_domains"]["protein_variant"]["unexpected"] = False
        fixture["content_digest"] = VERIFIER.content_digest(fixture)
        self.assert_rejected(fixture=fixture)

        fixture = self.load(FIXTURE)
        fixture["verified_domains"]["protein_variant"]["v2_result_digest"] = "sha256:" + "0" * 64
        fixture["content_digest"] = VERIFIER.content_digest(fixture)
        self.assert_rejected(fixture=fixture)

    def test_experiment_receipt_presence_missing_fields_and_non_boolean_values_fail(self):
        for domain in VERIFIER.DOMAINS:
            for field in VERIFIER.EXPERIMENT_FIELDS:
                fixture = self.load(FIXTURE)
                fixture["experiment_receipts_present"][domain][field] = True
                fixture["content_digest"] = VERIFIER.content_digest(fixture)
                with self.subTest(domain=domain, field=field, value=True):
                    self.assert_rejected(fixture=fixture)
            fixture = self.load(FIXTURE)
            fixture["experiment_receipts_present"][domain]["compute_run"] = 0
            fixture["content_digest"] = VERIFIER.content_digest(fixture)
            with self.subTest(domain=domain, value=0):
                self.assert_rejected(fixture=fixture)

    def test_producer_and_lock_authority_escalation_are_rejected_field_by_field(self):
        for field in VERIFIER.AUTHORITY_FIELDS:
            fixture = self.load(FIXTURE)
            fixture["authority"][field] = True
            fixture["content_digest"] = VERIFIER.content_digest(fixture)
            with self.subTest(scope="producer", field=field):
                self.assert_rejected(fixture=fixture)
            lock = self.load(LOCK)
            lock["authority"][field] = True
            lock["content_digest"] = VERIFIER.content_digest(lock)
            with self.subTest(scope="lock", field=field):
                self.assert_rejected(lock=lock)

    def test_all_sdk_registration_admission_and_action_escalations_are_rejected(self):
        fields = (
            "package_root_export", "sdk_adapter_registered", "runtime_route_registered",
            "mcp_tool_registered", "workflow_registered", "source_admission",
            "graph_write", "proof_promotion", "physical_action",
        )
        for field in fields:
            lock = self.load(LOCK)
            lock["consumer"][field] = True
            lock["content_digest"] = VERIFIER.content_digest(lock)
            with self.subTest(field=field):
                self.assert_rejected(lock=lock)

    def test_producer_execution_registration_admission_graph_and_claim_drift_fail(self):
        for field in ("producer_reexecuted", "runtime_registered", "source_admitted", "graph_projection_eligible"):
            fixture = self.load(FIXTURE)
            fixture[field] = True
            fixture["content_digest"] = VERIFIER.content_digest(fixture)
            with self.subTest(field=field):
                self.assert_rejected(fixture=fixture)
        fixture = self.load(FIXTURE)
        fixture["claim_ceiling"] = "scientific_truth"
        fixture["content_digest"] = VERIFIER.content_digest(fixture)
        self.assert_rejected(fixture=fixture)

    def test_verifier_imports_only_stdlib_and_has_no_runtime_client_or_mock_path(self):
        source = SCRIPT.read_text()
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(ast.parse(source))
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        for forbidden in (
            "requests", "socket", "urllib", "httpx", "aiohttp", "subprocess",
            "tempera_bio", "tempera_mcp", "unittest.mock",
        ):
            self.assertNotIn(forbidden, imported)
        for forbidden in (
            "GraphEngine", "GraphImporter", "register_tool", "register_resource",
            "register_prompt", "MagicMock", "patch(", "urlopen(",
        ):
            self.assertNotIn(forbidden, source)

    def test_cli_is_byte_identical_across_five_hash_seeds(self):
        outputs = []
        for seed in ("1", "2", "97", "211", "99991"):
            env = os.environ.copy()
            env["PYTHONHASHSEED"] = seed
            outputs.append(subprocess.run([sys.executable, str(SCRIPT)], check=True, capture_output=True, env=env).stdout)
        self.assertEqual(len(set(outputs)), 1)
        self.assertEqual(outputs[0], EXPECTED.read_bytes())

    def test_malformed_nonfinite_and_non_object_json_fail_closed(self):
        for bad in (b"{bad", b'{"value":NaN}', b"[]", b"null"):
            with self.subTest(bad=bad):
                self.assert_rejected(fixture_bytes=bad)


if __name__ == "__main__":
    unittest.main()
