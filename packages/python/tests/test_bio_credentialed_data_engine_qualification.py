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
SCRIPT = (
    ROOT
    / "packages/python/src/tempera_sdk/bio_credentialed_data_engine_qualification.py"
)
LOCK = (
    ROOT / "contracts/bio-credentialed-data-engine-qualification-sdk.staging.lock.json"
)
EXPECTED = (
    ROOT
    / "contracts/bio-credentialed-data-engine-qualification-sdk-consumer-verification.json"
)
MCP_LOCK = (
    ROOT
    / "contracts/vendor/mcp/bio-credentialed-data-engine-qualification.staging.lock.json"
)
MCP_RECEIPT = (
    ROOT
    / "contracts/vendor/mcp/bio-credentialed-data-engine-qualification-consumer-verification.json"
)
MCP_SOURCE = (
    ROOT / "contracts/vendor/mcp/verify-bio-credentialed-data-engine-qualification.py"
)
SPEC = importlib.util.spec_from_file_location("bio_credentialed_sdk_consumer", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class BioCredentialedQualificationSdkTests(unittest.TestCase):
    maxDiff = None

    @staticmethod
    def load(path: Path):
        return json.loads(path.read_bytes())

    def test_exact_snapshot_replays_to_committed_sdk_receipt(self):
        receipt = MODULE.verify_paths(ROOT)
        self.assertEqual(MODULE.pretty_json(receipt), EXPECTED.read_bytes())
        self.assertEqual(receipt["upstream"]["commit"], MODULE.MCP_COMMIT)
        self.assertEqual(receipt["experiment_receipt_slots"], 18)
        self.assertEqual(receipt["experiment_receipts_present"], 0)
        self.assertFalse(receipt["package_root_exported"])
        self.assertFalse(receipt["sdk_adapter_registered"])
        self.assertFalse(receipt["runtime_registered"])
        self.assertFalse(any(receipt["authority"].values()))

    def test_all_eight_mcp_artifact_pins_are_exact_and_closed(self):
        lock = self.load(LOCK)
        self.assertEqual(lock["producer"]["artifacts"], MODULE.MCP_ARTIFACTS)
        self.assertEqual(len(MODULE.MCP_ARTIFACTS), 8)
        self.assertEqual(lock["producer"]["commit"], MODULE.MCP_COMMIT)
        for path, pin in MODULE.MCP_ARTIFACTS.items():
            self.assertEqual(set(pin), {"bytes", "git_blob", "sha256"}, path)
            self.assertGreater(pin["bytes"], 0, path)

    def test_three_vendored_files_match_upstream_byte_sha_and_blob(self):
        lock = self.load(LOCK)
        MODULE.verify_sdk_lock(lock, ROOT)
        for upstream, local in MODULE.VENDORED.items():
            data = (ROOT / local).read_bytes()
            pin = lock["fixtures"][upstream]
            self.assertEqual(pin["bytes"], len(data))
            self.assertEqual(pin["sha256"], MODULE.sha256_hex(data))
            self.assertEqual(pin["git_blob"], MODULE.git_blob_hex(data))

    def test_vendored_byte_tamper_fails_before_consumption(self):
        lock = self.load(LOCK)
        for upstream, local in MODULE.VENDORED.items():
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for source_path in MODULE.VENDORED.values():
                    source = ROOT / source_path
                    target = root / source_path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(source.read_bytes())
                target = root / local
                target.write_bytes(target.read_bytes() + b" ")
                with (
                    self.subTest(upstream=upstream),
                    self.assertRaises(MODULE.VerificationError),
                ):
                    MODULE.verify_sdk_lock(lock, root)

    def test_sdk_lock_rejects_commit_hosted_review_registration_and_authority(self):
        mutations = (
            lambda value: value["producer"].update(commit="0" * 40),
            lambda value: value["producer"].update(hosted_step_execution_observed=True),
            lambda value: value["producer"].update(independent_review_observed=True),
            lambda value: value["consumer"].update(package_root_export=True),
            lambda value: value["consumer"].update(sdk_adapter_registered=True),
            lambda value: value["consumer"].update(runtime_route_registered=True),
            lambda value: value["consumer"].update(storage_or_custody=True),
            lambda value: value["authority"].update(source_admission=True),
            lambda value: value.update(claim_ceiling="scientific_truth"),
        )
        for mutate in mutations:
            changed = self.load(LOCK)
            mutate(changed)
            changed["content_digest"] = MODULE.content_digest(changed)
            with (
                self.subTest(mutate=mutate),
                self.assertRaises(MODULE.VerificationError),
            ):
                MODULE.verify_sdk_lock(changed, ROOT)

    def test_sdk_lock_rejects_artifact_fixture_and_environment_drift(self):
        mutations = (
            lambda value: value["producer"]["artifacts"].pop(
                ".github/workflows/bio-credentialed-data-engine-qualification-consumer.yml"
            ),
            lambda value: value["producer"]["artifacts"][
                "scripts/verify-bio-credentialed-data-engine-qualification.py"
            ].update(bytes=1),
            lambda value: value["fixtures"][
                "contracts/bio-credentialed-data-engine-qualification-consumer-verification.json"
            ].update(sha256="0" * 64),
            lambda value: value["fixtures"][
                "contracts/bio-credentialed-data-engine-qualification.staging.lock.json"
            ].update(consumer_path="other.json"),
            lambda value: value["environment"].update(python="3.13"),
        )
        for mutate in mutations:
            changed = self.load(LOCK)
            mutate(changed)
            changed["content_digest"] = MODULE.content_digest(changed)
            with (
                self.subTest(mutate=mutate),
                self.assertRaises(MODULE.VerificationError),
            ):
                MODULE.verify_sdk_lock(changed, ROOT)

    def test_mcp_lock_rejects_hosted_review_registration_and_authority_fabrication(
        self,
    ):
        mutations = (
            lambda value: value["producer"].update(hosted_step_execution_observed=True),
            lambda value: value["producer"].update(independent_review_observed=True),
            lambda value: value["consumer"].update(producer_executed=True),
            lambda value: value["consumer"].update(tool_registered=True),
            lambda value: value["consumer"].update(storage_or_custody=True),
            lambda value: value["authority"].update(custody_created=True),
        )
        for mutate in mutations:
            changed = self.load(MCP_LOCK)
            mutate(changed)
            changed["content_digest"] = MODULE.content_digest(changed)
            with (
                self.subTest(mutate=mutate),
                self.assertRaises(MODULE.VerificationError),
            ):
                MODULE.verify_mcp_lock(changed)

    def test_mcp_receipt_rejects_root_authority_and_custody_fabrication(self):
        raw = MCP_RECEIPT.read_bytes()
        mutations = (
            lambda value: value["authority"].update(scientific_truth=True),
            lambda value: value.update(storage_or_custody_executed=True),
            lambda value: value.update(inspector_dispatch_executed=True),
            lambda value: value.update(runtime_registered=True),
            lambda value: value.update(source_admitted=True),
            lambda value: value.update(experiment_receipts_present=1),
            lambda value: value["data_engine_binding"].update(
                credentialed_custody_integration_observed=True
            ),
        )
        for mutate in mutations:
            changed = self.load(MCP_RECEIPT)
            mutate(changed)
            changed["content_digest"] = MODULE.content_digest(changed)
            with (
                self.subTest(mutate=mutate),
                self.assertRaises(MODULE.VerificationError),
            ):
                MODULE.verify_mcp_receipt(changed, raw)

    def test_mcp_receipt_requires_exact_raw_bytes(self):
        with self.assertRaisesRegex(MODULE.VerificationError, "raw digest"):
            MODULE.verify_mcp_receipt(
                self.load(MCP_RECEIPT), MCP_RECEIPT.read_bytes() + b" "
            )

    def test_each_domain_rejects_receipt_presence_dispatch_and_eligibility(self):
        for domain in MODULE.DOMAINS:
            mutations = (
                lambda gate: gate["experiment_receipts_present"].update(
                    compute_run=True
                ),
                lambda gate: gate.update(status="ready"),
                lambda gate: gate.update(reason="custody_integrated"),
                lambda gate: gate.update(
                    credentialed_qualification_receipt_sha256="0" * 64
                ),
            )
            for mutate in mutations:
                changed = self.load(MCP_RECEIPT)
                mutate(changed["verified_domains"][domain])
                changed["content_digest"] = MODULE.content_digest(changed)
                changed_raw = MODULE.pretty_json(changed)
                with (
                    self.subTest(domain=domain, mutate=mutate),
                    self.assertRaises(MODULE.VerificationError),
                ):
                    MODULE.verify_mcp_receipt(changed, changed_raw)

    def test_domain_order_duplicate_and_cross_domain_swap_fail_closed(self):
        receipt = self.load(MCP_RECEIPT)
        changed = copy.deepcopy(receipt)
        changed["verified_domains"]["metabolic_feasibility"] = copy.deepcopy(
            changed["verified_domains"]["protein_variant"]
        )
        changed["content_digest"] = MODULE.content_digest(changed)
        with self.assertRaises(MODULE.VerificationError):
            MODULE.verify_mcp_receipt(changed, MODULE.pretty_json(changed))
        changed = copy.deepcopy(receipt)
        changed["verified_domains"]["unknown"] = changed["verified_domains"].pop(
            "neuronal_response"
        )
        changed["content_digest"] = MODULE.content_digest(changed)
        with self.assertRaises(MODULE.VerificationError):
            MODULE.verify_mcp_receipt(changed, MODULE.pretty_json(changed))

    def test_mcp_source_has_required_callables_and_no_runtime_path(self):
        source = MCP_SOURCE.read_text()
        MODULE.verify_mcp_source(source)
        functions = {
            node.name
            for node in ast.parse(source).body
            if isinstance(node, ast.FunctionDef)
        }
        for required in (
            "verify_paths",
            "verify_mcp_lock",
            "verify_bio_lock",
            "verify_bio_verification",
            "verify_bio_source",
        ):
            self.assertIn(required, functions)

    def test_mcp_source_rejects_missing_callable_network_storage_and_registration(self):
        source = MCP_SOURCE.read_text()
        mutations = (
            source.replace("def verify_paths(", "def other(", 1),
            source + "\nimport socket\n",
            source + "\ndef storage():\n    DataEngineStore()\n",
            source + "\ndef register():\n    register_tool()\n",
        )
        for changed in mutations:
            with (
                self.subTest(suffix=changed[-60:]),
                self.assertRaises(MODULE.VerificationError),
            ):
                MODULE.verify_mcp_source(changed)

    def test_sdk_verifier_is_stdlib_only_unexported_and_has_no_action_calls(self):
        source = SCRIPT.read_text()
        tree = ast.parse(source)
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        for forbidden in (
            "socket",
            "requests",
            "urllib",
            "httpx",
            "subprocess",
            "sqlite3",
            "unittest",
            "tempera_mcp",
            "tempera_bio",
            "data_engine",
        ):
            self.assertNotIn(forbidden, imported)
        package_root = ROOT / "packages/python/src/tempera_sdk/__init__.py"
        self.assertNotIn(
            "bio_credentialed_data_engine_qualification", package_root.read_text()
        )
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        } | {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        for forbidden in (
            "register_tool",
            "register_resource",
            "register_prompt",
            "DataEngineStore",
            "GraphEngine",
            "urlopen",
        ):
            self.assertNotIn(forbidden, calls)

    def test_cli_is_byte_identical_across_five_hash_seeds(self):
        outputs = []
        for seed in ("1", "2", "97", "211", "99991"):
            env = os.environ.copy()
            env["PYTHONHASHSEED"] = seed
            outputs.append(
                subprocess.run(
                    [sys.executable, str(SCRIPT), "--root", str(ROOT)],
                    check=True,
                    capture_output=True,
                    env=env,
                ).stdout
            )
        self.assertEqual(len(set(outputs)), 1)
        self.assertEqual(outputs[0], EXPECTED.read_bytes())

    def test_missing_root_and_malformed_json_fail_without_fallback(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaises(FileNotFoundError),
        ):
            MODULE.verify_paths(Path(directory))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = (
                root
                / "contracts/bio-credentialed-data-engine-qualification-sdk.staging.lock.json"
            )
            path.parent.mkdir(parents=True)
            path.write_bytes(b"{bad")
            with self.assertRaises(json.JSONDecodeError):
                MODULE.verify_paths(root)


if __name__ == "__main__":
    unittest.main()
