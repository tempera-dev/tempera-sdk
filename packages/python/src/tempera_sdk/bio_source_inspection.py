"""Verify sealed Bio level-zero receipts without admitting an SDK capability.

This module is intentionally absent from :mod:`tempera_sdk` root exports.  It is
a staging consumer for exact-source integration evidence, not a runtime route,
model-facing tool, scientific evaluator, or authority boundary.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any


LOCK_SCHEMA = "tempera.sdk.bio-source-inspection-consumer-staging-lock/v1"
FIXTURE_SCHEMA = "tempera.scientific-source-inspection-consumer-fixtures/v1"
WORKFLOW_SCHEMA = "tempera.scientific-source-inspection-workflow-receipt/v1"
VERIFICATION_SCHEMA = "tempera.scientific-source-inspection-consumer-verification/v1"
WORKFLOW_REF = "tempera_bio.scientific_source_workflow/v1"
VERIFIER_REF = "tempera_bio.scientific_source_consumer/v1"
BIO_COMMIT = "d0ea9f24ddb1e37b5dc878be8b160e596e91d2ad"
MCP_COMMIT = "da99bf4175f5a178d9b7f1788832b0786d367a61"
DOMAINS = ("protein_variant", "metabolic_feasibility", "neuronal_response")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
GIT_SHA = re.compile(r"^[a-f0-9]{40}$")

LOCK_KEYS = {
    "schema_version", "status", "upstreams", "fixture", "consumer",
    "compatibility", "claim_ceiling", "content_digest",
}
BUNDLE_KEYS = {
    "schema_version", "producer", "claim_ceiling", "consumer_policy",
    "fixtures", "content_digest",
}
FIXTURE_KEYS = {"domain", "workflow_receipt", "consumer_verification"}
WORKFLOW_KEYS = {
    "schema_version", "workflow_ref", "request_id", "domain", "request_digest",
    "source_lock_digest", "connector_receipt_digest", "artifact_digest",
    "source_dispatch_receipt_digest", "inspection_receipt_digest", "status",
    "next_gate", "portable_consumer_contract", "eligibility", "boundaries",
    "content_digest",
}
VERIFICATION_KEYS = {
    "schema_version", "verifier_ref", "producer_contract", "request_id", "domain",
    "workflow_receipt_digest", "verified_bindings", "result", "consumer_registration",
    "authority", "claim_ceiling", "content_digest",
}

EXPECTED_BIO_ARTIFACTS = {
    "contracts/fixtures/scientific-source-inspection-consumer-fixtures-v1.json": (
        "b22ed98f595b519b704ba33c185677a3e60bf0b8",
        "32e22a99aca2179050a8d6d6691f7e1e4c7657f7a4dfff0269627dfc47d412ea",
    ),
    "contracts/scientific-source-inspection-consumer-fixtures-v1.schema.json": (
        "9f109129d1a913481a99ca439ff8379c218b5f4b",
        "4b0d214d6127b2dfd7eb10656194dc31e06a2bc83f6f2db1bb4af735447a5a46",
    ),
    "contracts/scientific-source-inspection-consumer-verification-v1.schema.json": (
        "54620c7edd5f8fb72660538a47151a2a71eb4031",
        "8fb0b67f47d80b37f4634400cbabb1bb5d726882a53cacfd47878cd7a5486168",
    ),
    "contracts/scientific-source-inspection-request-v1.schema.json": (
        "a6a0f54e9f2cae823b238b653f77ddd812b6e83a",
        "39d29e89b4a5310a076f27c99251c9681535b20817bdc6722bb8442c2660d003",
    ),
    "contracts/scientific-source-inspection-workflow-receipt-v1.schema.json": (
        "61b38c7872012c11be9d3880a23d8337c6a88dc6",
        "ac307b85358a9365deddd5b62db68297a97ef9aa46762ddc5eb1ec79f18e6541",
    ),
    "src/tempera_bio/scientific_source_consumer.py": (
        "60e01377cb8105eb8a6449253335aaac1c4af516",
        "690ba6c55c9bd65d32afcd86c2dae54f03e9b2132b98788a83dbb325923dc43c",
    ),
    "src/tempera_bio/scientific_source_fixtures.py": (
        "ee88642e040b11d97ebcfb3b0c9470b5f7bd9f23",
        "b8de03075a56cedf841e033918a25c05f09477d2925b300b814ea6e2a58ea967",
    ),
    "src/tempera_bio/scientific_source_workflow.py": (
        "1ebde13cfcdb1bf383417269838a447687f80872",
        "fedb58dbd17fdeacfcffcc973455a77627abccf41d225516b533acec61569048",
    ),
}
EXPECTED_MCP_ARTIFACTS = {
    "contracts/bio-source-inspection-consumer.staging.lock.json": (
        "c90acec422a250d014e34a7221cee0170709f0a1",
        "090579e72821d6849eb5cc31969a066ef4132eef7da776bd0af8c6297569e4f9",
    ),
    "contracts/bio-source-inspection-consumer-fixtures.json": (
        "b22ed98f595b519b704ba33c185677a3e60bf0b8",
        "32e22a99aca2179050a8d6d6691f7e1e4c7657f7a4dfff0269627dfc47d412ea",
    ),
    "scripts/verify-bio-source-inspection-consumer.py": (
        "e6a3a5e301b11b5623cae1bf57d000abe6015ed0",
        "3f2075b26041aa25a708aa7cd62d389d53566a3516b06f952f3a3edc1f0b531a",
    ),
    "scripts/test-verify-bio-source-inspection-consumer.py": (
        "a23ff042eeb82512bdd16a4cba73c5ec3e1f8d91",
        "39b8af7c3ae37b2f03fe6edf826489751d08edb7b177fc9f7a3b877765038378",
    ),
}


class VerificationError(ValueError):
    """An exact source, receipt, or authority binding drifted."""


def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise VerificationError("value is not canonical JSON") from exc


def content_digest(value: Mapping[str, Any]) -> str:
    body = dict(value)
    body.pop("content_digest", None)
    return "sha256:" + hashlib.sha256(canonical_json(body)).hexdigest()


def _exact(value: Any, expected: Any, field: str) -> None:
    if value != expected:
        raise VerificationError(f"{field}: does not match closed contract")


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise VerificationError(f"{field}: expected object")
    return value


def _digest(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:") or not SHA256.fullmatch(value[7:]):
        raise VerificationError(f"{field}: expected lowercase sha256 digest")
    return value


def _verify_artifacts(value: Any, expected: Mapping[str, tuple[str, str]], field: str) -> None:
    artifacts = _mapping(value, field)
    _exact(set(artifacts), set(expected), f"{field}.paths")
    for path, (blob, digest) in expected.items():
        if path.startswith("/") or ".." in Path(path).parts:
            raise VerificationError(f"{field}.{path}: unsafe path")
        pin = _mapping(artifacts[path], f"{field}.{path}")
        _exact(set(pin), {"git_blob", "sha256"}, f"{field}.{path}.fields")
        _exact(pin["git_blob"], blob, f"{field}.{path}.git_blob")
        _exact(pin["sha256"], digest, f"{field}.{path}.sha256")
        if not GIT_SHA.fullmatch(pin["git_blob"]):
            raise VerificationError(f"{field}.{path}.git_blob: expected git sha")
        if not SHA256.fullmatch(pin["sha256"]):
            raise VerificationError(f"{field}.{path}.sha256: expected sha256")


def _verify_workflow(receipt: Any, domain: str) -> Mapping[str, Any]:
    receipt = _mapping(receipt, f"{domain}.workflow")
    _exact(set(receipt), WORKFLOW_KEYS, f"{domain}.workflow.fields")
    _exact(receipt["schema_version"], WORKFLOW_SCHEMA, f"{domain}.workflow.schema")
    _exact(receipt["workflow_ref"], WORKFLOW_REF, f"{domain}.workflow.ref")
    _exact(receipt["domain"], domain, f"{domain}.workflow.domain")
    _exact(receipt["status"], "inspection_complete_not_admitted", f"{domain}.status")
    _exact(receipt["next_gate"], "source_admission_review", f"{domain}.next_gate")
    _exact(receipt["portable_consumer_contract"], {
        "sdk_adapter": "required_not_registered",
        "mcp_tool": "required_not_registered",
        "workflow_registration": "required_not_registered",
    }, f"{domain}.consumers")
    _exact(receipt["eligibility"], {
        "training": False, "evaluation": False, "official_claim": False,
    }, f"{domain}.eligibility")
    _exact(receipt["boundaries"], {
        "claim_ceiling": "software_contract_conformance",
        "evidence_stage_promotion": "prohibited",
        "graph_projection": "not_emitted_pre_admission",
        "graph_authority": "none",
        "proof_promotion": "prohibited",
        "physical_action": "prohibited",
    }, f"{domain}.boundaries")
    for name in (
        "request_digest", "source_lock_digest", "connector_receipt_digest",
        "artifact_digest", "source_dispatch_receipt_digest",
        "inspection_receipt_digest", "content_digest",
    ):
        _digest(receipt[name], f"{domain}.workflow.{name}")
    _exact(receipt["content_digest"], content_digest(receipt), f"{domain}.workflow.digest")
    return receipt


def _verify_consumer(value: Any, workflow: Mapping[str, Any], domain: str) -> Mapping[str, Any]:
    value = _mapping(value, f"{domain}.verification")
    _exact(set(value), VERIFICATION_KEYS, f"{domain}.verification.fields")
    _exact(value["schema_version"], VERIFICATION_SCHEMA, f"{domain}.verification.schema")
    _exact(value["verifier_ref"], VERIFIER_REF, f"{domain}.verification.ref")
    _exact(value["producer_contract"], {
        "schema_version": WORKFLOW_SCHEMA, "workflow_ref": WORKFLOW_REF,
    }, f"{domain}.producer_contract")
    _exact(value["request_id"], workflow["request_id"], f"{domain}.request_id")
    _exact(value["domain"], domain, f"{domain}.verification.domain")
    _exact(value["workflow_receipt_digest"], workflow["content_digest"], f"{domain}.workflow_binding")
    _exact(value["verified_bindings"], {name: workflow[name] for name in (
        "request_digest", "source_lock_digest", "connector_receipt_digest",
        "artifact_digest", "source_dispatch_receipt_digest", "inspection_receipt_digest",
    )}, f"{domain}.bindings")
    _exact(value["result"], {
        "contract_conformant": True, "producer_reexecuted": False, "source_admitted": False,
    }, f"{domain}.result")
    _exact(value["consumer_registration"], {
        "sdk_adapter": False, "mcp_tool": False, "workflow": False,
    }, f"{domain}.registration")
    _exact(value["authority"], {
        "evidence_stage_promotion": False, "graph_write": False,
        "proof_promotion": False, "physical_action": False,
    }, f"{domain}.authority")
    _exact(value["claim_ceiling"], "portable_receipt_contract_conformance", f"{domain}.claim_ceiling")
    _exact(value["content_digest"], content_digest(value), f"{domain}.verification.digest")
    return value


def verify_bytes(lock_bytes: bytes, fixture_bytes: bytes) -> dict[str, Any]:
    """Return a deterministic SDK receipt for exact sealed input bytes."""
    try:
        lock = json.loads(lock_bytes)
        bundle = json.loads(fixture_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError("inputs must be UTF-8 JSON") from exc
    lock = _mapping(lock, "lock")
    bundle = _mapping(bundle, "fixture")
    _exact(set(lock), LOCK_KEYS, "lock.fields")
    _exact(lock["schema_version"], LOCK_SCHEMA, "lock.schema")
    _exact(lock["status"], "staging_cross_consumer_locked_not_admitted", "lock.status")
    _exact(lock["content_digest"], content_digest(lock), "lock.digest")

    upstreams = _mapping(lock["upstreams"], "lock.upstreams")
    _exact(set(upstreams), {"bio", "mcp"}, "lock.upstreams.names")
    bio = _mapping(upstreams["bio"], "lock.upstreams.bio")
    mcp = _mapping(upstreams["mcp"], "lock.upstreams.mcp")
    for name, value, repository, commit, branch, artifacts in (
        ("bio", bio, "tempera-dev/tempera-bio", BIO_COMMIT, "codex/scientific-problem-contract-v1", EXPECTED_BIO_ARTIFACTS),
        ("mcp", mcp, "tempera-dev/tempera-mcp", MCP_COMMIT, "codex/bio-source-inspection-consumer-v1", EXPECTED_MCP_ARTIFACTS),
    ):
        _exact(set(value), {"repository", "branch", "commit", "artifacts"}, f"lock.upstreams.{name}.fields")
        _exact(value["repository"], repository, f"lock.upstreams.{name}.repository")
        _exact(value["branch"], branch, f"lock.upstreams.{name}.branch")
        _exact(value["commit"], commit, f"lock.upstreams.{name}.commit")
        if not GIT_SHA.fullmatch(value["commit"]):
            raise VerificationError(f"lock.upstreams.{name}.commit: expected exact commit")
        _verify_artifacts(value["artifacts"], artifacts, f"lock.upstreams.{name}.artifacts")

    fixture = _mapping(lock["fixture"], "lock.fixture")
    _exact(set(fixture), {"path", "sha256", "content_digest", "domain_receipts"}, "lock.fixture.fields")
    _exact(fixture["path"], "contracts/bio-source-inspection-sdk-consumer-fixtures.json", "lock.fixture.path")
    _exact(hashlib.sha256(fixture_bytes).hexdigest(), fixture["sha256"], "fixture.bytes")
    _exact(fixture["sha256"], EXPECTED_BIO_ARTIFACTS[
        "contracts/fixtures/scientific-source-inspection-consumer-fixtures-v1.json"
    ][1], "fixture.bio_binding")
    _exact(fixture["sha256"], EXPECTED_MCP_ARTIFACTS[
        "contracts/bio-source-inspection-consumer-fixtures.json"
    ][1], "fixture.mcp_binding")

    _exact(set(bundle), BUNDLE_KEYS, "fixture.fields")
    _exact(bundle["schema_version"], FIXTURE_SCHEMA, "fixture.schema")
    _exact(bundle["content_digest"], content_digest(bundle), "fixture.digest")
    _exact(bundle["content_digest"], fixture["content_digest"], "fixture.lock_binding")
    _exact(bundle["claim_ceiling"], "portable_receipt_contract_conformance", "fixture.claim_ceiling")
    _exact(bundle["consumer_policy"], {
        "network": "denied", "runtime_registration": "prohibited",
        "source_admission": "prohibited", "evidence_stage_promotion": "prohibited",
        "graph_write": "prohibited", "proof_promotion": "prohibited",
        "physical_action": "prohibited",
    }, "fixture.consumer_policy")

    consumer = _mapping(lock["consumer"], "lock.consumer")
    _exact(consumer, {
        "implementation": "packages/python/src/tempera_sdk/bio_source_inspection.py",
        "package_root_export": False,
        "mcp_tool_registered": False,
        "workflow_registered": False,
        "network": "denied",
        "source_admission": False,
        "evidence_stage_promotion": False,
        "graph_write": False,
        "proof_promotion": False,
        "physical_action": False,
    }, "lock.consumer")
    _exact(lock["compatibility"], {
        "owner": "tempera-sdk",
        "python": ">=3.10,<4",
        "dependencies": "stdlib-only",
        "rollout": "staging-verification-only",
        "rollback": "remove unexported verifier and sealed fixtures",
        "affected_consumers": ["tempera-sdk-python-staging-tests"],
    }, "lock.compatibility")
    _exact(lock["claim_ceiling"], "independent_cross_repo_contract_conformance", "lock.claim_ceiling")

    fixtures = bundle.get("fixtures")
    if not isinstance(fixtures, list):
        raise VerificationError("fixture.fixtures: expected list")
    _exact(len(fixtures), len(DOMAINS), "fixture.count")
    pins = _mapping(fixture["domain_receipts"], "lock.fixture.domain_receipts")
    _exact(set(pins), set(DOMAINS), "lock.fixture.domain_receipts.names")
    verified: dict[str, dict[str, str]] = {}
    for domain, item in zip(DOMAINS, fixtures, strict=True):
        item = _mapping(item, f"{domain}.fixture")
        _exact(set(item), FIXTURE_KEYS, f"{domain}.fixture.fields")
        _exact(item["domain"], domain, f"{domain}.fixture.domain")
        workflow = _verify_workflow(item["workflow_receipt"], domain)
        verification = _verify_consumer(item["consumer_verification"], workflow, domain)
        pin = _mapping(pins[domain], f"lock.fixture.domain_receipts.{domain}")
        _exact(set(pin), {"workflow_receipt_digest", "consumer_verification_digest"}, f"{domain}.pin.fields")
        _exact(pin["workflow_receipt_digest"], workflow["content_digest"], f"{domain}.workflow.pin")
        _exact(pin["consumer_verification_digest"], verification["content_digest"], f"{domain}.verification.pin")
        verified[domain] = {
            "workflow_receipt_digest": workflow["content_digest"],
            "consumer_verification_digest": verification["content_digest"],
        }

    receipt: dict[str, Any] = {
        "schema_version": "tempera.sdk.bio-source-inspection-consumer-verification/v1",
        "source_lock_digest": lock["content_digest"],
        "upstream_commits": {"bio": BIO_COMMIT, "mcp": MCP_COMMIT},
        "fixture_digest": bundle["content_digest"],
        "verified_domains": verified,
        "result": "staging_cross_consumer_conformant_not_admitted",
        "runtime_registration": False,
        "authority": {
            "source_admission": False, "evidence_stage_promotion": False,
            "graph_write": False, "proof_promotion": False, "physical_action": False,
        },
        "claim_ceiling": "independent_cross_repo_contract_conformance",
    }
    receipt["content_digest"] = content_digest(receipt)
    return receipt


def verify_paths(lock_path: Path, fixture_path: Path) -> dict[str, Any]:
    """Read two local sealed files and verify them; no network I/O is performed."""
    return verify_bytes(lock_path.read_bytes(), fixture_path.read_bytes())


def receipt_bytes(receipt: Mapping[str, Any]) -> bytes:
    """Serialize a verified receipt in its deterministic wire representation."""
    return canonical_json(receipt)


__all__ = [
    "BIO_COMMIT", "DOMAINS", "LOCK_SCHEMA", "MCP_COMMIT", "VerificationError",
    "canonical_json", "content_digest", "receipt_bytes", "verify_bytes", "verify_paths",
]
