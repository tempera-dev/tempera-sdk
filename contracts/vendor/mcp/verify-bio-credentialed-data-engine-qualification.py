"""Verify Bio's credentialed Data Engine qualification without MCP registration."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

BIO_COMMIT = "bc246a48e8f9d1496db633735908037435396229"
DATA_ENGINE_COMMIT = "3794a95a4286532930ea248db7a0277a27edc0ea"
QUALIFICATION_RECEIPT_SHA256 = (
    "4daad130145368dca6ee401b2c813bdd35b124c3de1c58533d01232e6b9a9dd2"
)
BIO_VERIFICATION_SHA256 = (
    "f899db2bf3ecb9a047ce8e62ecd9dcfdc53dd0729abe440c4c7ac7c52babe00e"
)
DOMAINS = ("protein_variant", "metabolic_feasibility", "neuronal_response")
EXPERIMENT_RECEIPTS = (
    "admitted_source_snapshot",
    "pinned_model",
    "compute_run",
    "uncertainty_ood",
    "domain_evaluation",
    "independent_model_replay",
)
AUTHORITY_FIELDS = (
    "benchmark_release",
    "custody_created",
    "evaluation_execution",
    "graph_write",
    "merge",
    "physical_action",
    "proof_promotion",
    "scientific_truth",
    "source_admission",
    "training_eligibility",
)
PRODUCER_ARTIFACTS = {
    ".github/workflows/credentialed-data-engine-qualification-gate.yml": {
        "bytes": 1728,
        "git_blob": "4baff492823f00ba60d9d8fa80c992f92b8d6533",
        "sha256": "d35559d6c61886bf289b4105d260c4d81571dbbd85224670c00927ef1e8770ec",
    },
    "contracts/credentialed-data-engine-qualification-gate-verification.json": {
        "bytes": 6137,
        "git_blob": "12d7456cb9382da368ac16a2e9b7c071d4e7bf76",
        "sha256": BIO_VERIFICATION_SHA256,
    },
    "contracts/credentialed-data-engine-qualification-gate.lock.json": {
        "bytes": 3265,
        "git_blob": "fa9ed9cd2ac77f997c704e42f62d325b5034ff8e",
        "sha256": "19c4aa3a1b739f5d57dc3e9b40f3a1b32cc770af0e43f154008d19f4f66264d9",
    },
    "contracts/vendor/data-engine/.github/workflows/credentialed-connector-evidence-qualification.yml": {
        "bytes": 2833,
        "git_blob": "232e898de30e02eaeff157809caefabfa11dd134",
        "sha256": "b6680df80ee06274e3e7e26f4fa48b21e28b832334e48dd3e30d6a4aaa9c4243",
    },
    "contracts/vendor/data-engine/contracts/credentialed-connector-evidence-qualification-policy.conformance.json": {
        "bytes": 1467,
        "git_blob": "8853d7c0d5af65da2eeb6f82de0bf7cacce17be4",
        "sha256": "3631c958b77b05a60b530391f81223040807b1e11dc70af6c0596b214861144f",
    },
    "contracts/vendor/data-engine/contracts/credentialed-connector-evidence-qualification.lock.json": {
        "bytes": 3228,
        "git_blob": "8cebebcf263997f51a966ffc07705d3d94ce898d",
        "sha256": "d55c6338c36d3567627ec3df2f60ad0d65886a6fa66219458cc695316746bbdb",
    },
    "contracts/vendor/data-engine/contracts/credentialed-connector-evidence-qualification.receipt.json": {
        "bytes": 3009,
        "git_blob": "122514b8c51a58bdfd76143f6121097a623e4a14",
        "sha256": QUALIFICATION_RECEIPT_SHA256,
    },
    "contracts/vendor/data-engine/scripts/verify_credentialed_connector_handoff.py": {
        "bytes": 10742,
        "git_blob": "81ed0d150d43c4f3b64a6181ef62788b051c27ec",
        "sha256": "08347715ca96ac4aa7d91320fc50393770df4300f1c51b894796e0b16271eea0",
    },
    "contracts/vendor/data-engine/src/data_engine/credentialed_connector_evidence.py": {
        "bytes": 25693,
        "git_blob": "ebe9988ffa684f1bd5f120ff0edbb21832721b38",
        "sha256": "5812f9b0323c94c32ee8e62ed144c360dda5c3d24ab3ebd998219972b7cf2f63",
    },
    "contracts/vendor/data-engine/tests/test_credentialed_connector_evidence_qualification.py": {
        "bytes": 20795,
        "git_blob": "0f707563be9fe2c481316997e08e4f066c3edeca",
        "sha256": "aff42eade440bed94f17c61dc51ba081e3c6e154c0d3308194b8a249ef277c70",
    },
    "src/tempera_bio/credentialed_data_engine_qualification_gate.py": {
        "bytes": 16930,
        "git_blob": "634881d5d704d70baa1f249fd3b81897cdfae825",
        "sha256": "7b48cf877176cea4e83f1d75b6e884c13f4bb9d4b8b2e83af5cbed53cbb95656",
    },
    "tests/test_credentialed_data_engine_qualification_gate.py": {
        "bytes": 14900,
        "git_blob": "d100fd44595462ad8f108b0f0ed820a1fe95634e",
        "sha256": "a1363d6ede1b73ff8c957081a6110029ad30d7d7b13b31c0685162d8ddf72727",
    },
}
FIXTURES = {
    "contracts/credentialed-data-engine-qualification-gate-verification.json": (
        "contracts/vendor/bio/contracts/credentialed-data-engine-qualification-gate-verification.json"
    ),
    "contracts/credentialed-data-engine-qualification-gate.lock.json": (
        "contracts/vendor/bio/contracts/credentialed-data-engine-qualification-gate.lock.json"
    ),
    "src/tempera_bio/credentialed_data_engine_qualification_gate.py": (
        "contracts/vendor/bio/src/tempera_bio/credentialed_data_engine_qualification_gate.py"
    ),
}
_DIGEST = re.compile(r"^sha256:[a-f0-9]{64}$")


class VerificationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()


def pretty_json(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n"
    ).encode()


def content_digest(value: Mapping[str, Any]) -> str:
    body = dict(value)
    body.pop("content_digest", None)
    return "sha256:" + hashlib.sha256(canonical_json(body)).hexdigest()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_hex(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _exact_keys(value: Any, expected: set[str], label: str) -> None:
    require(isinstance(value, Mapping), f"{label}: expected object")
    require(set(value) == expected, f"{label}: fields do not match closed contract")


def _false_authority(value: Mapping[str, Any], label: str) -> None:
    require(set(value) == set(AUTHORITY_FIELDS), f"{label}: authority field drift")
    require(not any(value.values()), f"{label}: authority escalation")


def verify_mcp_lock(lock: Mapping[str, Any], root: Path) -> None:
    _exact_keys(
        lock,
        {
            "authority",
            "claim_ceiling",
            "consumer",
            "content_digest",
            "environment",
            "fixtures",
            "producer",
            "schema_version",
            "status",
        },
        "MCP lock",
    )
    require(
        lock["schema_version"]
        == "tempera.mcp.bio-credentialed-data-engine-qualification-staging-lock/v1",
        "MCP lock: schema drift",
    )
    require(
        lock["status"] == "staging_source_locked_not_registered",
        "MCP lock: status drift",
    )
    require(lock["environment"] == {"python": "3.12.13"}, "MCP lock: environment drift")
    require(
        lock["claim_ceiling"] == "software_source_lock_and_block_conformance",
        "MCP lock: claim ceiling drift",
    )
    require(
        lock["producer"]
        == {
            "repository": "tempera-dev/tempera-bio",
            "branch": "codex/scientific-problem-contract-v1",
            "commit": BIO_COMMIT,
            "artifacts": PRODUCER_ARTIFACTS,
            "hosted_step_execution_observed": False,
            "independent_review_observed": False,
        },
        "MCP lock: producer drift",
    )
    require(
        lock["consumer"]
        == {
            "implementation": "scripts/verify-bio-credentialed-data-engine-qualification.py",
            "producer_imported": False,
            "producer_executed": False,
            "runtime_catalog_entry": False,
            "server_discovery_entry": False,
            "tool_registered": False,
            "resource_registered": False,
            "prompt_registered": False,
            "network": False,
            "storage_or_custody": False,
            "source_admission": False,
            "inspector_dispatch": False,
            "graph_write": False,
        },
        "MCP lock: consumer drift",
    )
    _false_authority(lock["authority"], "MCP lock")
    require(lock["content_digest"] == content_digest(lock), "MCP lock: digest mismatch")
    require(set(lock["fixtures"]) == set(FIXTURES), "MCP lock: fixture registry drift")
    for producer_path, consumer_path in FIXTURES.items():
        pin = lock["fixtures"][producer_path]
        _exact_keys(
            pin,
            {"bytes", "consumer_path", "git_blob", "sha256"},
            f"MCP lock fixture {producer_path}",
        )
        require(
            pin["consumer_path"] == consumer_path,
            f"{producer_path}: consumer path drift",
        )
        data = (root / consumer_path).read_bytes()
        expected = PRODUCER_ARTIFACTS[producer_path]
        require(
            pin["bytes"] == len(data) == expected["bytes"],
            f"{producer_path}: byte drift",
        )
        require(
            pin["sha256"] == sha256_hex(data) == expected["sha256"],
            f"{producer_path}: SHA drift",
        )
        require(
            pin["git_blob"] == git_blob_hex(data) == expected["git_blob"],
            f"{producer_path}: blob drift",
        )


def verify_bio_lock(value: Mapping[str, Any]) -> None:
    _exact_keys(
        value,
        {
            "artifacts",
            "authority",
            "claim_ceiling",
            "consumer",
            "content_digest",
            "data_engine",
            "environment",
            "predecessor_bio_commit",
            "schema_version",
            "status",
        },
        "Bio lock",
    )
    require(
        value["schema_version"]
        == "tempera.bio-credentialed-data-engine-qualification-gate-lock/v1",
        "Bio lock: schema drift",
    )
    require(
        value["content_digest"] == content_digest(value), "Bio lock: digest mismatch"
    )
    require(value["status"] == "staging_fail_closed", "Bio lock: status drift")
    require(
        value["claim_ceiling"] == "credentialed_qualification_consumed_no_custody",
        "Bio lock: claim escalation",
    )
    _false_authority(value["authority"], "Bio lock")
    require(
        value["data_engine"]
        == {
            "repository": "tempera-dev/data-engine",
            "pull_request": 111,
            "commit": DATA_ENGINE_COMMIT,
            "qualification_receipt_sha256": QUALIFICATION_RECEIPT_SHA256,
            "callable": "data_engine.credentialed_connector_evidence.verify_credentialed_connector_evidence",
            "hosted_step_execution_observed": False,
            "independent_review_observed": False,
        },
        "Bio lock: Data Engine binding drift",
    )
    require(
        value["consumer"]
        == {
            "implementation": "src/tempera_bio/credentialed_data_engine_qualification_gate.py",
            "data_engine_verifier_imported": False,
            "data_engine_verifier_executed": False,
            "inspector_dispatch": False,
            "network": False,
            "runtime_registration": False,
            "source_admission": False,
            "storage_or_custody": False,
        },
        "Bio lock: consumer drift",
    )


def verify_bio_source(source: str) -> None:
    tree = ast.parse(source)
    functions = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    for required in (
        "verify_paths",
        "build_domain_gate",
        "verify_data_engine_receipt",
        "verify_data_engine_source_boundary",
    ):
        require(
            required in functions, f"Bio source: required callable missing: {required}"
        )
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    for forbidden in (
        "data_engine",
        "tempera_bio",
        "requests",
        "socket",
        "sqlite3",
        "urllib.request",
        "unittest.mock",
    ):
        require(forbidden not in imports, f"Bio source: forbidden import {forbidden}")
    for forbidden in (
        "verify_credentialed_connector_evidence(",
        "DataEngineStore(",
        "inspect_protein_variant",
        "inspect_metabolic_feasibility",
        "inspect_neuronal_response",
        "register_tool(",
        "GraphEngine(",
    ):
        require(forbidden not in source, f"Bio source: forbidden callable {forbidden}")


def verify_bio_verification(value: Mapping[str, Any], raw: bytes) -> None:
    _exact_keys(
        value,
        {
            "authority",
            "claim_ceiling",
            "content_digest",
            "data_engine_binding",
            "domain_gates",
            "experiment_receipt_slots",
            "experiment_receipts_present",
            "graph_projection_eligible",
            "inspector_dispatch_executed",
            "result",
            "runtime_registered",
            "schema_version",
            "source_admitted",
            "storage_or_custody_executed",
        },
        "Bio verification",
    )
    require(
        sha256_hex(raw) == BIO_VERIFICATION_SHA256,
        "Bio verification: raw digest mismatch",
    )
    require(
        value["schema_version"]
        == "tempera.bio-credentialed-data-engine-qualification-gate-verification/v1",
        "Bio verification: schema drift",
    )
    require(
        value["content_digest"] == content_digest(value),
        "Bio verification: digest mismatch",
    )
    require(
        value["result"] == "all_domains_blocked_before_credentialed_custody",
        "Bio verification: result drift",
    )
    require(
        value["claim_ceiling"] == "credentialed_qualification_consumed_no_custody",
        "Bio verification: claim escalation",
    )
    require(
        value["data_engine_binding"]
        == {
            "repository": "tempera-dev/data-engine",
            "pull_request": 111,
            "commit": DATA_ENGINE_COMMIT,
            "qualification_receipt_sha256": QUALIFICATION_RECEIPT_SHA256,
            "hosted_step_execution_observed": False,
            "independent_review_observed": False,
            "credentialed_custody_integration_observed": False,
        },
        "Bio verification: Data Engine binding drift",
    )
    require(
        value["experiment_receipt_slots"] == 18, "Bio verification: receipt slot drift"
    )
    require(
        value["experiment_receipts_present"] == 0,
        "Bio verification: receipt fabrication",
    )
    for field in (
        "graph_projection_eligible",
        "inspector_dispatch_executed",
        "runtime_registered",
        "source_admitted",
        "storage_or_custody_executed",
    ):
        require(value[field] is False, f"Bio verification: {field} escalation")
    _false_authority(value["authority"], "Bio verification")
    require(len(value["domain_gates"]) == 3, "Bio verification: domain count drift")
    for domain, gate in zip(DOMAINS, value["domain_gates"], strict=True):
        _exact_keys(
            gate,
            {
                "authority",
                "content_digest",
                "credentialed_qualification_receipt_sha256",
                "domain",
                "evaluation_eligible",
                "experiment_receipts",
                "graph_projection_eligible",
                "inspector_dispatch",
                "reason",
                "required_source_bindings",
                "schema_version",
                "source_admitted",
                "status",
                "training_eligible",
            },
            f"Bio verification {domain}",
        )
        require(gate["domain"] == domain, f"{domain}: domain order drift")
        require(
            gate["content_digest"] == content_digest(gate), f"{domain}: digest drift"
        )
        require(gate["status"] == "blocked", f"{domain}: status drift")
        require(
            gate["reason"] == "credentialed_data_engine_custody_not_integrated",
            f"{domain}: reason drift",
        )
        require(
            gate["credentialed_qualification_receipt_sha256"]
            == QUALIFICATION_RECEIPT_SHA256,
            f"{domain}: qualification drift",
        )
        require(
            set(gate["experiment_receipts"]) == set(EXPERIMENT_RECEIPTS),
            f"{domain}: experiment receipt fields drift",
        )
        require(
            all(item is None for item in gate["experiment_receipts"].values()),
            f"{domain}: experiment receipt fabricated",
        )
        require(
            set(gate["required_source_bindings"])
            == {
                "step_bearing_data_engine_hosted_check_digest",
                "independent_data_engine_review_digest",
                "production_credentialed_custody_receipt_digest",
                "bio_source_lock_digest",
                "bio_source_admission_review_digest",
                "normalized_manifest_digest",
            },
            f"{domain}: source binding fields drift",
        )
        require(
            all(item is None for item in gate["required_source_bindings"].values()),
            f"{domain}: source binding fabricated",
        )
        require(
            gate["inspector_dispatch"] == "prohibited",
            f"{domain}: inspector escalation",
        )
        for field in (
            "evaluation_eligible",
            "graph_projection_eligible",
            "source_admitted",
            "training_eligible",
        ):
            require(gate[field] is False, f"{domain}: {field} escalation")
        _false_authority(gate["authority"], f"Bio verification {domain}")


def verify_paths(root: Path) -> dict[str, Any]:
    lock = json.loads(
        (
            root
            / "contracts/bio-credentialed-data-engine-qualification.staging.lock.json"
        ).read_bytes()
    )
    verify_mcp_lock(lock, root)
    bio_lock = json.loads(
        (
            root
            / FIXTURES[
                "contracts/credentialed-data-engine-qualification-gate.lock.json"
            ]
        ).read_bytes()
    )
    bio_raw = (
        root
        / FIXTURES[
            "contracts/credentialed-data-engine-qualification-gate-verification.json"
        ]
    ).read_bytes()
    bio_verification = json.loads(bio_raw)
    bio_source = (
        root
        / FIXTURES["src/tempera_bio/credentialed_data_engine_qualification_gate.py"]
    ).read_text()
    verify_bio_lock(bio_lock)
    verify_bio_source(bio_source)
    verify_bio_verification(bio_verification, bio_raw)
    domain_receipts = {
        gate["domain"]: {
            "gate_digest": gate["content_digest"],
            "credentialed_qualification_receipt_sha256": gate[
                "credentialed_qualification_receipt_sha256"
            ],
            "status": gate["status"],
            "reason": gate["reason"],
            "experiment_receipts_present": {
                kind: False for kind in EXPERIMENT_RECEIPTS
            },
        }
        for gate in bio_verification["domain_gates"]
    }
    result = {
        "schema_version": "tempera.mcp.bio-credentialed-data-engine-qualification-consumer-verification/v1",
        "producer": {
            "repository": "tempera-dev/tempera-bio",
            "commit": BIO_COMMIT,
            "verification_sha256": BIO_VERIFICATION_SHA256,
            "verification_content_digest": bio_verification["content_digest"],
        },
        "source_lock_digest": lock["content_digest"],
        "data_engine_binding": bio_verification["data_engine_binding"],
        "verified_domains": domain_receipts,
        "experiment_receipt_slots": 18,
        "experiment_receipts_present": 0,
        "result": "staging_credentialed_qualification_source_locked_not_registered",
        "producer_imported": False,
        "producer_executed": False,
        "runtime_registered": False,
        "tool_registered": False,
        "resource_registered": False,
        "prompt_registered": False,
        "server_discovery_entry": False,
        "storage_or_custody_executed": False,
        "inspector_dispatch_executed": False,
        "source_admitted": False,
        "graph_projection_eligible": False,
        "authority": {field: False for field in AUTHORITY_FIELDS},
        "claim_ceiling": "software_source_lock_and_block_conformance",
    }
    result["content_digest"] = content_digest(result)
    return result


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=root)
    args = parser.parse_args()
    print(json.dumps(verify_paths(args.root.resolve()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
