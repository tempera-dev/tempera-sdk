"""Unexported SDK verifier for MCP's credentialed Bio qualification receipt."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

MCP_COMMIT = "8d47cdcf807a60cc7ee535de0df0f9641dff6efe"
BIO_COMMIT = "bc246a48e8f9d1496db633735908037435396229"
DATA_ENGINE_COMMIT = "3794a95a4286532930ea248db7a0277a27edc0ea"
MCP_RECEIPT_SHA256 = "46c3873e694906bf21fa50526fe43b4d8af7310a21ebda8a01dee1f88fcac1da"
QUALIFICATION_RECEIPT_SHA256 = (
    "4daad130145368dca6ee401b2c813bdd35b124c3de1c58533d01232e6b9a9dd2"
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
MCP_ARTIFACTS = {
    ".github/workflows/bio-credentialed-data-engine-qualification-consumer.yml": {
        "bytes": 1648,
        "git_blob": "aa90bbfb29430930b58d60347db631677761aa8b",
        "sha256": "3354381c2531571003ef7662005028185a90d3d931f7b09308debe6bf82b0539",
    },
    "contracts/bio-credentialed-data-engine-qualification-consumer-verification.json": {
        "bytes": 3779,
        "git_blob": "95b1eaceb65cef9bc8f093674e990e2b183ca984",
        "sha256": MCP_RECEIPT_SHA256,
    },
    "contracts/bio-credentialed-data-engine-qualification.staging.lock.json": {
        "bytes": 5835,
        "git_blob": "d8e2996b20437876cf23d621ee9928ad14218262",
        "sha256": "ac7cbb1d1429226dbe15b91af6c9953d83f0f0b897393402c0c7ec1a57a69be4",
    },
    "contracts/vendor/bio/contracts/credentialed-data-engine-qualification-gate-verification.json": {
        "bytes": 6137,
        "git_blob": "12d7456cb9382da368ac16a2e9b7c071d4e7bf76",
        "sha256": "f899db2bf3ecb9a047ce8e62ecd9dcfdc53dd0729abe440c4c7ac7c52babe00e",
    },
    "contracts/vendor/bio/contracts/credentialed-data-engine-qualification-gate.lock.json": {
        "bytes": 3265,
        "git_blob": "fa9ed9cd2ac77f997c704e42f62d325b5034ff8e",
        "sha256": "19c4aa3a1b739f5d57dc3e9b40f3a1b32cc770af0e43f154008d19f4f66264d9",
    },
    "contracts/vendor/bio/src/tempera_bio/credentialed_data_engine_qualification_gate.py": {
        "bytes": 16930,
        "git_blob": "634881d5d704d70baa1f249fd3b81897cdfae825",
        "sha256": "7b48cf877176cea4e83f1d75b6e884c13f4bb9d4b8b2e83af5cbed53cbb95656",
    },
    "scripts/test-verify-bio-credentialed-data-engine-qualification.py": {
        "bytes": 14748,
        "git_blob": "65469caa12cf0bd7d5e5bc8b6516b936a9e5e148",
        "sha256": "72c5816e2821637d16738361b9148a4c9213fca02c3ba6880223ace6e2d8be37",
    },
    "scripts/verify-bio-credentialed-data-engine-qualification.py": {
        "bytes": 21018,
        "git_blob": "888fb6a11424eed273c95549bf68eca87ad58c71",
        "sha256": "69d940edf3f5ded91c413a81ea83074d6d6733c1c86b3524109002cd01e008ac",
    },
}
VENDORED = {
    "contracts/bio-credentialed-data-engine-qualification-consumer-verification.json": (
        "contracts/vendor/mcp/bio-credentialed-data-engine-qualification-consumer-verification.json"
    ),
    "contracts/bio-credentialed-data-engine-qualification.staging.lock.json": (
        "contracts/vendor/mcp/bio-credentialed-data-engine-qualification.staging.lock.json"
    ),
    "scripts/verify-bio-credentialed-data-engine-qualification.py": (
        "contracts/vendor/mcp/verify-bio-credentialed-data-engine-qualification.py"
    ),
}


class VerificationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    except (TypeError, ValueError) as error:
        raise VerificationError("value is not canonical JSON") from error


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


def exact_keys(value: Any, expected: set[str], label: str) -> None:
    require(isinstance(value, Mapping), f"{label}: expected object")
    require(set(value) == expected, f"{label}: fields do not match closed contract")


def false_authority(value: Mapping[str, Any], label: str) -> None:
    require(set(value) == set(AUTHORITY_FIELDS), f"{label}: authority field drift")
    require(all(item is False for item in value.values()), f"{label}: escalation")


def verify_sdk_lock(lock: Mapping[str, Any], root: Path) -> None:
    exact_keys(
        lock,
        {
            "schema_version",
            "status",
            "environment",
            "producer",
            "fixtures",
            "consumer",
            "authority",
            "claim_ceiling",
            "content_digest",
        },
        "SDK lock",
    )
    require(
        lock["schema_version"]
        == "tempera.sdk.bio-credentialed-data-engine-qualification-staging-lock/v1",
        "SDK lock: schema drift",
    )
    require(lock["status"] == "staging_mcp_locked_not_exported", "SDK lock: status")
    require(lock["environment"] == {"python": "3.12.13"}, "SDK lock: environment")
    require(
        lock["producer"]
        == {
            "repository": "tempera-dev/tempera-mcp",
            "branch": "codex/bio-source-inspection-consumer-v1",
            "commit": MCP_COMMIT,
            "artifacts": MCP_ARTIFACTS,
            "hosted_step_execution_observed": False,
            "independent_review_observed": False,
        },
        "SDK lock: producer drift",
    )
    require(
        lock["consumer"]
        == {
            "implementation": "packages/python/src/tempera_sdk/bio_credentialed_data_engine_qualification.py",
            "package_root_export": False,
            "sdk_adapter_registered": False,
            "runtime_route_registered": False,
            "producer_imported": False,
            "producer_executed": False,
            "network": False,
            "storage_or_custody": False,
            "source_admission": False,
            "inspector_dispatch": False,
            "graph_write": False,
        },
        "SDK lock: consumer drift",
    )
    require(
        lock["claim_ceiling"] == "independent_mcp_receipt_conformance",
        "SDK lock: claim ceiling",
    )
    false_authority(lock["authority"], "SDK lock")
    require(lock["content_digest"] == content_digest(lock), "SDK lock: digest")
    require(set(lock["fixtures"]) == set(VENDORED), "SDK lock: fixture registry")
    for producer_path, consumer_path in VENDORED.items():
        pin = lock["fixtures"][producer_path]
        exact_keys(pin, {"bytes", "consumer_path", "git_blob", "sha256"}, producer_path)
        require(pin["consumer_path"] == consumer_path, f"{producer_path}: path drift")
        data = (root / consumer_path).read_bytes()
        expected = MCP_ARTIFACTS[producer_path]
        require(
            pin["bytes"] == len(data) == expected["bytes"], f"{producer_path}: bytes"
        )
        require(
            pin["sha256"] == sha256_hex(data) == expected["sha256"],
            f"{producer_path}: SHA",
        )
        require(
            pin["git_blob"] == git_blob_hex(data) == expected["git_blob"],
            f"{producer_path}: blob",
        )


def verify_mcp_lock(lock: Mapping[str, Any]) -> None:
    exact_keys(
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
        lock["status"] == "staging_source_locked_not_registered", "MCP lock: status"
    )
    require(lock["environment"] == {"python": "3.12.13"}, "MCP lock: environment")
    require(lock["content_digest"] == content_digest(lock), "MCP lock: digest")
    require(
        lock["content_digest"]
        == "sha256:b84411b47beffe065a165969f918c4da83353d0fbd166b3611ee45b8efb7242c",
        "MCP lock: exact digest drift",
    )
    require(lock["producer"]["commit"] == BIO_COMMIT, "MCP lock: Bio commit")
    require(
        lock["producer"]["hosted_step_execution_observed"] is False, "MCP lock: hosted"
    )
    require(
        lock["producer"]["independent_review_observed"] is False, "MCP lock: review"
    )
    for field in (
        "producer_imported",
        "producer_executed",
        "runtime_catalog_entry",
        "server_discovery_entry",
        "tool_registered",
        "resource_registered",
        "prompt_registered",
        "network",
        "storage_or_custody",
        "source_admission",
        "inspector_dispatch",
        "graph_write",
    ):
        require(lock["consumer"][field] is False, f"MCP lock: {field}")
    false_authority(lock["authority"], "MCP lock")
    require(
        lock["claim_ceiling"] == "software_source_lock_and_block_conformance",
        "MCP lock: claim ceiling",
    )


def verify_mcp_receipt(receipt: Mapping[str, Any], raw: bytes) -> None:
    exact_keys(
        receipt,
        {
            "authority",
            "claim_ceiling",
            "content_digest",
            "data_engine_binding",
            "experiment_receipt_slots",
            "experiment_receipts_present",
            "graph_projection_eligible",
            "inspector_dispatch_executed",
            "producer",
            "producer_executed",
            "producer_imported",
            "prompt_registered",
            "resource_registered",
            "result",
            "runtime_registered",
            "schema_version",
            "server_discovery_entry",
            "source_admitted",
            "source_lock_digest",
            "storage_or_custody_executed",
            "tool_registered",
            "verified_domains",
        },
        "MCP receipt",
    )
    require(sha256_hex(raw) == MCP_RECEIPT_SHA256, "MCP receipt: raw digest")
    require(receipt["content_digest"] == content_digest(receipt), "MCP receipt: digest")
    require(
        receipt["content_digest"]
        == "sha256:df272a772f9faef425ae4d19b7eee5fa1d6bad41721e04f288f2836757fa29e9",
        "MCP receipt: exact content digest",
    )
    require(
        receipt["schema_version"]
        == "tempera.mcp.bio-credentialed-data-engine-qualification-consumer-verification/v1",
        "MCP receipt: schema",
    )
    require(
        receipt["result"]
        == "staging_credentialed_qualification_source_locked_not_registered",
        "MCP receipt: result",
    )
    require(
        receipt["producer"]
        == {
            "repository": "tempera-dev/tempera-bio",
            "commit": BIO_COMMIT,
            "verification_content_digest": "sha256:633096eedf1b3acd7d44c8f43ee94f507ff57ecb77bbb725006fb331459857f9",
            "verification_sha256": "f899db2bf3ecb9a047ce8e62ecd9dcfdc53dd0729abe440c4c7ac7c52babe00e",
        },
        "MCP receipt: producer",
    )
    require(
        receipt["data_engine_binding"]
        == {
            "repository": "tempera-dev/data-engine",
            "pull_request": 111,
            "commit": DATA_ENGINE_COMMIT,
            "qualification_receipt_sha256": QUALIFICATION_RECEIPT_SHA256,
            "hosted_step_execution_observed": False,
            "independent_review_observed": False,
            "credentialed_custody_integration_observed": False,
        },
        "MCP receipt: Data Engine binding",
    )
    require(receipt["experiment_receipt_slots"] == 18, "MCP receipt: slots")
    require(receipt["experiment_receipts_present"] == 0, "MCP receipt: presence")
    require(set(receipt["verified_domains"]) == set(DOMAINS), "MCP receipt: domains")
    for domain in DOMAINS:
        gate = receipt["verified_domains"][domain]
        exact_keys(
            gate,
            {
                "credentialed_qualification_receipt_sha256",
                "experiment_receipts_present",
                "gate_digest",
                "reason",
                "status",
            },
            domain,
        )
        require(gate["status"] == "blocked", f"{domain}: status")
        require(
            gate["reason"] == "credentialed_data_engine_custody_not_integrated",
            f"{domain}: reason",
        )
        require(
            gate["credentialed_qualification_receipt_sha256"]
            == QUALIFICATION_RECEIPT_SHA256,
            f"{domain}: qualification receipt",
        )
        require(
            gate["experiment_receipts_present"]
            == {field: False for field in EXPERIMENT_RECEIPTS},
            f"{domain}: experiment receipts",
        )
        require(
            isinstance(gate["gate_digest"], str)
            and gate["gate_digest"].startswith("sha256:")
            and len(gate["gate_digest"]) == 71,
            f"{domain}: gate digest",
        )
    for field in (
        "producer_executed",
        "producer_imported",
        "prompt_registered",
        "resource_registered",
        "runtime_registered",
        "server_discovery_entry",
        "source_admitted",
        "storage_or_custody_executed",
        "tool_registered",
        "graph_projection_eligible",
        "inspector_dispatch_executed",
    ):
        require(receipt[field] is False, f"MCP receipt: {field}")
    false_authority(receipt["authority"], "MCP receipt")
    require(
        receipt["claim_ceiling"] == "software_source_lock_and_block_conformance",
        "MCP receipt: claim ceiling",
    )


def verify_mcp_source(source: str) -> None:
    tree = ast.parse(source)
    functions = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    for required in (
        "verify_paths",
        "verify_mcp_lock",
        "verify_bio_lock",
        "verify_bio_verification",
        "verify_bio_source",
    ):
        require(required in functions, f"MCP source: missing callable {required}")
    imports = {
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
        "tempera_mcp",
        "tempera_bio",
        "data_engine",
        "unittest",
    ):
        require(forbidden not in imports, f"MCP source: forbidden import {forbidden}")
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
        require(forbidden not in calls, f"MCP source: forbidden call {forbidden}")


def verify_paths(root: Path) -> dict[str, Any]:
    sdk_lock = json.loads(
        (
            root
            / "contracts/bio-credentialed-data-engine-qualification-sdk.staging.lock.json"
        ).read_bytes()
    )
    verify_sdk_lock(sdk_lock, root)
    mcp_lock_path = (
        root
        / VENDORED[
            "contracts/bio-credentialed-data-engine-qualification.staging.lock.json"
        ]
    )
    mcp_receipt_path = (
        root
        / VENDORED[
            "contracts/bio-credentialed-data-engine-qualification-consumer-verification.json"
        ]
    )
    mcp_source_path = (
        root / VENDORED["scripts/verify-bio-credentialed-data-engine-qualification.py"]
    )
    mcp_lock = json.loads(mcp_lock_path.read_bytes())
    mcp_raw = mcp_receipt_path.read_bytes()
    mcp_receipt = json.loads(mcp_raw)
    verify_mcp_lock(mcp_lock)
    verify_mcp_receipt(mcp_receipt, mcp_raw)
    verify_mcp_source(mcp_source_path.read_text())
    require(
        mcp_receipt["source_lock_digest"] == mcp_lock["content_digest"],
        "MCP receipt: lock binding",
    )
    result = {
        "schema_version": "tempera.sdk.bio-credentialed-data-engine-qualification-consumer-verification/v1",
        "upstream": {
            "repository": "tempera-dev/tempera-mcp",
            "commit": MCP_COMMIT,
            "receipt_sha256": MCP_RECEIPT_SHA256,
            "receipt_content_digest": mcp_receipt["content_digest"],
            "source_lock_digest": mcp_receipt["source_lock_digest"],
            "hosted_step_execution_observed": False,
            "independent_review_observed": False,
        },
        "data_engine_binding": dict(mcp_receipt["data_engine_binding"]),
        "verified_domains": {
            domain: dict(mcp_receipt["verified_domains"][domain]) for domain in DOMAINS
        },
        "experiment_receipt_slots": 18,
        "experiment_receipts_present": 0,
        "result": "staging_credentialed_qualification_receipt_conformant_not_exported",
        "producer_imported": False,
        "producer_executed": False,
        "package_root_exported": False,
        "sdk_adapter_registered": False,
        "runtime_registered": False,
        "source_admitted": False,
        "storage_or_custody_executed": False,
        "inspector_dispatch_executed": False,
        "graph_projection_eligible": False,
        "authority": {field: False for field in AUTHORITY_FIELDS},
        "claim_ceiling": "independent_mcp_receipt_conformance",
    }
    result["content_digest"] = content_digest(result)
    return result


def main() -> int:
    root = Path(__file__).resolve().parents[4]
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=root)
    args = parser.parse_args()
    print(json.dumps(verify_paths(args.root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "AUTHORITY_FIELDS",
    "DOMAINS",
    "EXPERIMENT_RECEIPTS",
    "MCP_ARTIFACTS",
    "MCP_COMMIT",
    "VerificationError",
    "content_digest",
    "git_blob_hex",
    "pretty_json",
    "sha256_hex",
    "verify_mcp_lock",
    "verify_mcp_receipt",
    "verify_mcp_source",
    "verify_paths",
    "verify_sdk_lock",
]
