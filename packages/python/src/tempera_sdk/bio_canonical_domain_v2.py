"""Unexported SDK verifier for the sealed MCP Bio v2 source-lock receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any


LOCK_SCHEMA = "tempera.sdk.bio-canonical-domain-v2-staging-lock/v1"
MCP_SCHEMA = "tempera.mcp.bio-canonical-domain-inspector-v2-consumer-verification/v1"
BIO_COMMIT = "726ca0c6ae0e0d9ff8ecb671815e0bc4e3223dc9"
MCP_COMMIT = "15fae3667b2898c95b592caab16b55ed67b17638"
DOMAINS = ("protein_variant", "metabolic_feasibility", "neuronal_response")
ENTRYPOINT_REFS = {
    "protein_variant": "tempera_bio.canonical_domain_inspector_v2.inspect_protein_variant_from_data_engine_v2/v2",
    "metabolic_feasibility": "tempera_bio.canonical_domain_inspector_v2.inspect_metabolic_feasibility_from_data_engine_v2/v2",
    "neuronal_response": "tempera_bio.canonical_domain_inspector_v2.inspect_neuronal_response_from_data_engine_v2/v2",
}
AUTHORITY_FIELDS = (
    "benchmark_release", "evidence_stage_promotion", "graph_write", "merge",
    "physical_action", "proof_promotion", "scientific_truth", "source_admission",
)
EXPERIMENT_FIELDS = (
    "admitted_source", "pinned_model", "compute_run", "uncertainty_ood",
    "domain_evaluation", "independent_model_replay",
)
MCP_ARTIFACTS = {
    ".github/workflows/bio-canonical-domain-inspector-v2-consumer.yml": {
        "bytes": 2216,
        "git_blob": "b3cdc2e91072a0fc1b90ae526cb7b9171969b17c",
        "sha256": "0756280e940399dcaf469a0cfd6528a1a20bf9b99be5c86835448d617b9b04ee",
    },
    "contracts/bio-canonical-domain-inspector-v2.producer.json": {
        "bytes": 5763,
        "git_blob": "5b1c1f277168b7ef066906df5ce2298f4a000889",
        "sha256": "4b7d299dc19e7a9a06112d971bff95192b24c6d1560de4cd0176182b86be2586",
    },
    "contracts/bio-canonical-domain-inspector-v2.staging.lock.json": {
        "bytes": 3888,
        "git_blob": "b0b9f4124992863339cd4f110a843505167fd9d6",
        "sha256": "6f688e6fb165db794d1c8a43f0a1242b3a8384ceea98b318c9e13e1a26d1ddd4",
    },
    "contracts/bio-canonical-domain-inspector-v2-consumer-verification.json": {
        "bytes": 2870,
        "git_blob": "14061ffc59a66980824993c8d005fe130d0a832b",
        "sha256": "82543a8517408ef34ff47235f7322c786a308b7960b86e280129f63f83afb270",
    },
    "scripts/verify-bio-canonical-domain-inspector-v2.py": {
        "bytes": 13256,
        "git_blob": "19ea910e70e60bcff4c3c81d2dcae124b36c09a1",
        "sha256": "4a12d918636dc37c9024f630fb369d157b756f471534f8cc1dec1834a9d8a4db",
    },
    "scripts/test-verify-bio-canonical-domain-inspector-v2.py": {
        "bytes": 11129,
        "git_blob": "069e37adf5e4c3f6535956e432dfcb23418ba681",
        "sha256": "87a97a4ec99eaf18fde4d4bd168c203230b728e3834a4cc48bb1065aa9cdc50c",
    },
}
SHA256 = re.compile(r"^[a-f0-9]{64}$")
GIT_SHA = re.compile(r"^[a-f0-9]{40}$")


class VerificationError(ValueError):
    pass


def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    except (TypeError, ValueError) as error:
        raise VerificationError("value is not canonical JSON") from error


def pretty_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def content_digest(value: Mapping[str, Any]) -> str:
    body = dict(value)
    body.pop("content_digest", None)
    return "sha256:" + hashlib.sha256(canonical_json(body)).hexdigest()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_hex(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def exact(value: Any, expected: Any, field: str) -> None:
    require(value == expected, f"{field}: does not match closed contract")


def false_authority(value: Mapping[str, Any], field: str) -> None:
    exact(set(value), set(AUTHORITY_FIELDS), f"{field}.fields")
    require(all(value[name] is False for name in AUTHORITY_FIELDS), f"{field}: authority escalation")


def verify_lock(lock: Mapping[str, Any], fixture_bytes: bytes) -> None:
    exact(set(lock), {
        "schema_version", "status", "upstream", "fixture", "consumer",
        "compatibility", "authority", "claim_ceiling", "content_digest",
    }, "lock.fields")
    exact(lock["schema_version"], LOCK_SCHEMA, "lock.schema")
    exact(lock["status"], "staging_mcp_v2_locked_not_exported", "lock.status")
    exact(lock["content_digest"], content_digest(lock), "lock.digest")
    upstream = lock["upstream"]
    exact(set(upstream), {"repository", "branch", "commit", "artifacts"}, "upstream.fields")
    exact(upstream["repository"], "tempera-dev/tempera-mcp", "upstream.repository")
    exact(upstream["branch"], "codex/bio-source-inspection-consumer-v1", "upstream.branch")
    exact(upstream["commit"], MCP_COMMIT, "upstream.commit")
    exact(upstream["artifacts"], MCP_ARTIFACTS, "upstream.artifacts")
    for path, pin in upstream["artifacts"].items():
        require(isinstance(pin["bytes"], int) and pin["bytes"] > 0, f"{path}.bytes")
        require(GIT_SHA.fullmatch(pin["git_blob"]) is not None, f"{path}.git_blob")
        require(SHA256.fullmatch(pin["sha256"]) is not None, f"{path}.sha256")
    fixture = lock["fixture"]
    exact(set(fixture), {
        "producer_path", "consumer_path", "bytes", "sha256", "git_blob", "content_digest",
    }, "fixture.fields")
    exact(fixture["producer_path"], "contracts/bio-canonical-domain-inspector-v2-consumer-verification.json", "fixture.producer_path")
    exact(fixture["consumer_path"], "contracts/bio-canonical-domain-v2-mcp.producer.json", "fixture.consumer_path")
    exact(fixture["bytes"], len(fixture_bytes), "fixture.bytes")
    exact(fixture["sha256"], sha256_hex(fixture_bytes), "fixture.sha256")
    exact(fixture["git_blob"], git_blob_hex(fixture_bytes), "fixture.git_blob")
    exact(fixture["sha256"], MCP_ARTIFACTS[fixture["producer_path"]]["sha256"], "fixture.source_sha256")
    exact(fixture["git_blob"], MCP_ARTIFACTS[fixture["producer_path"]]["git_blob"], "fixture.source_blob")
    exact(lock["consumer"], {
        "implementation": "packages/python/src/tempera_sdk/bio_canonical_domain_v2.py",
        "package_root_export": False,
        "sdk_adapter_registered": False,
        "runtime_route_registered": False,
        "mcp_tool_registered": False,
        "workflow_registered": False,
        "network": "denied",
        "source_admission": False,
        "graph_write": False,
        "proof_promotion": False,
        "physical_action": False,
    }, "consumer")
    exact(lock["compatibility"], {
        "owner": "tempera-sdk",
        "python": ">=3.10,<4",
        "dependencies": "stdlib-only",
        "rollout": "staging-verification-only",
        "rollback": "remove unexported v2 verifier and sealed receipt",
        "affected_consumers": ["tempera-sdk-python-staging-tests"],
    }, "compatibility")
    false_authority(lock["authority"], "lock.authority")
    exact(lock["claim_ceiling"], "independent_mcp_v2_receipt_conformance", "lock.claim_ceiling")


def verify_bytes(lock_bytes: bytes, fixture_bytes: bytes) -> dict[str, Any]:
    try:
        lock = json.loads(lock_bytes)
        producer = json.loads(fixture_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VerificationError("inputs must be UTF-8 JSON") from error
    verify_lock(lock, fixture_bytes)
    exact(set(producer), {
        "schema_version", "producer", "source_lock_digest", "verified_domains",
        "experiment_receipts_present", "result", "producer_reexecuted",
        "runtime_registered", "source_admitted", "graph_projection_eligible",
        "authority", "claim_ceiling", "content_digest",
    }, "producer.fields")
    exact(producer["schema_version"], MCP_SCHEMA, "producer.schema")
    exact(producer["content_digest"], content_digest(producer), "producer.digest")
    exact(producer["content_digest"], lock["fixture"]["content_digest"], "producer.lock_binding")
    exact(producer["result"], "staging_v2_source_lock_conformant_not_registered", "producer.result")
    exact(producer["producer"], {
        "repository": "tempera-dev/tempera-bio",
        "commit": BIO_COMMIT,
        "verification_digest": "sha256:6bec8ce748c285ca44a273e4c070891724b221e85fcd2c5194fec02f79d5d270",
    }, "producer.producer")
    exact(producer["source_lock_digest"], "sha256:13a226f87e26eac31775d4e39fddefe9733929692de511b7e0ee39fd00532a35", "producer.source_lock")
    for field in ("producer_reexecuted", "runtime_registered", "source_admitted", "graph_projection_eligible"):
        exact(producer[field], False, f"producer.{field}")
    false_authority(producer["authority"], "producer.authority")
    exact(producer["claim_ceiling"], "software_receipt_and_source_lock_conformance", "producer.claim_ceiling")
    exact(set(producer["verified_domains"]), set(DOMAINS), "producer.domains")
    exact(set(producer["experiment_receipts_present"]), set(DOMAINS), "producer.experiment_domains")
    verified = {}
    experiment_receipts = {}
    for domain in DOMAINS:
        value = producer["verified_domains"][domain]
        exact(set(value), {"entrypoint_ref", "v2_result_digest", "adapter_result_digest"}, f"{domain}.fields")
        exact(value["entrypoint_ref"], ENTRYPOINT_REFS[domain], f"{domain}.entrypoint")
        for field in ("v2_result_digest", "adapter_result_digest"):
            digest = value[field]
            require(isinstance(digest, str) and digest.startswith("sha256:") and SHA256.fullmatch(digest[7:]) is not None, f"{domain}.{field}")
        receipts = producer["experiment_receipts_present"][domain]
        exact(set(receipts), set(EXPERIMENT_FIELDS), f"{domain}.experiment.fields")
        exact(receipts, {field: False for field in EXPERIMENT_FIELDS}, f"{domain}.experiment")
        verified[domain] = dict(value)
        experiment_receipts[domain] = dict(receipts)
    receipt = {
        "schema_version": "tempera.sdk.bio-canonical-domain-v2-consumer-verification/v1",
        "upstream": {
            "repository": "tempera-dev/tempera-mcp",
            "commit": MCP_COMMIT,
            "verification_digest": producer["content_digest"],
            "source_lock_digest": producer["source_lock_digest"],
        },
        "verified_domains": verified,
        "experiment_receipts_present": experiment_receipts,
        "result": "staging_mcp_v2_receipt_conformant_not_exported",
        "producer_reexecuted": False,
        "package_root_exported": False,
        "sdk_adapter_registered": False,
        "runtime_registered": False,
        "source_admitted": False,
        "graph_projection_eligible": False,
        "authority": {field: False for field in AUTHORITY_FIELDS},
        "claim_ceiling": "independent_mcp_v2_receipt_conformance",
    }
    receipt["content_digest"] = content_digest(receipt)
    return receipt


def verify_paths(lock_path: Path, fixture_path: Path) -> dict[str, Any]:
    return verify_bytes(lock_path.read_bytes(), fixture_path.read_bytes())


def main() -> int:
    root = Path(__file__).resolve().parents[4]
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, default=root / "contracts/bio-canonical-domain-v2-sdk.staging.lock.json")
    parser.add_argument("--fixture", type=Path, default=root / "contracts/bio-canonical-domain-v2-mcp.producer.json")
    args = parser.parse_args()
    print(json.dumps(verify_paths(args.lock, args.fixture), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "BIO_COMMIT", "DOMAINS", "MCP_COMMIT", "VerificationError", "content_digest",
    "verify_bytes", "verify_paths",
]
