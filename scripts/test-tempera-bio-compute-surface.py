#!/usr/bin/env python3
"""Lock the bounded, compute-only Tempera Bio SDK producer surface."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "specs/tempera-bio-api.json"
LOCK_PATH = SPEC_PATH.with_name(SPEC_PATH.name + ".source")
SURFACE_PATH = ROOT / "surface.json"

SAFE_OPERATIONS = {
    "prepareProteinVariantTask": {
        "path": "/v1/proteinVariantTasks:prepare",
        "scope": "bio:proposal:write",
        "response": "ProteinVariantTask",
        "body": {
            "schemaVersion",
            "taskId",
            "sourceSnapshotDigest",
            "sequenceManifestDigest",
            "assayContextDigest",
            "splitDefinitionDigest",
            "candidateManifestDigest",
            "taskBoundary",
            "physicalAction",
        },
    },
    "prepareNeuralResponseTask": {
        "path": "/v1/neuralResponseTasks:prepare",
        "scope": "bio:proposal:write",
        "response": "NeuralResponseTask",
        "body": {
            "schemaVersion",
            "taskId",
            "sourceSnapshotDigest",
            "nwbSemanticsDigest",
            "featureManifestDigest",
            "stimulusProtocolDigest",
            "hiddenResponseCommitmentDigest",
            "groupKeys",
            "taskBoundary",
            "physicalAction",
        },
    },
    "prepareStoichiometricExperiment": {
        "path": "/v1/stoichiometricExperiments:prepare",
        "scope": "bio:proposal:write",
        "response": "StoichiometricExperiment",
        "body": {
            "schemaVersion",
            "experimentId",
            "sourceSnapshotDigest",
            "metaboliteIds",
            "reactionIds",
            "entries",
            "bounds",
            "claimBoundary",
            "physicalAction",
        },
    },
    "prepareStoichiometricFeasibilityReceipt": {
        "path": "/v1/stoichiometricFeasibilityReceipts:prepare",
        "scope": "bio:measurement:verify",
        "response": "StoichiometricFeasibilityReceipt",
        "body": {"schemaVersion", "experiment", "flux"},
    },
    "prepareComputationalExperimentPlan": {
        "path": "/v1/computationalExperimentPlans:prepare",
        "scope": "bio:proposal:write",
        "response": "ComputationalExperimentPlan",
        "body": {
            "schemaVersion",
            "experimentId",
            "discipline",
            "domainTask",
            "sourceSnapshots",
            "inputManifestDigest",
            "hiddenTargetCommitmentDigest",
            "splitDefinitionDigest",
            "baselineManifestDigest",
            "metricDefinitionDigest",
            "execution",
            "executionClass",
            "claimCeiling",
        },
    },
}

WITHHELD_OPERATIONS = {
    "prepareComputationalModelRunReceipt",
    "prepareComputationalEvaluationReceipt",
    "prepareComputationalBenchmarkManifest",
    "prepareComputationalIndependentReplayReceipt",
    "prepareComputationalQualificationBundle",
    "verifyProteinVariantTask",
    "verifyNeuralResponseTask",
    "verifyStoichiometricExperiment",
    "verifyStoichiometricFeasibilityReceipt",
    "verifyComputationalExperimentPlan",
}

FALSE_BOUNDARIES = {
    "x-tempera-hidden-target-access",
    "x-tempera-model-execution",
    "x-tempera-proof-promotion",
    "x-tempera-graph-write",
    "x-tempera-mcp-auto-admission",
    "x-tempera-physical-action",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TemperaBioComputeSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.spec = _load(SPEC_PATH)
        cls.lock = _load(LOCK_PATH)
        cls.surface = _load(SURFACE_PATH)

    def test_provisional_pr39_source_lock_is_byte_exact(self) -> None:
        data = SPEC_PATH.read_bytes()
        sha256 = hashlib.sha256(data).hexdigest()
        git_blob = hashlib.sha1(
            f"blob {len(data)}\0".encode("ascii") + data
        ).hexdigest()

        self.assertEqual(
            self.lock["source_commit"],
            "4656d6e48535423626b56d47690329a8cbfc9646",
        )
        self.assertEqual(
            self.lock["source_branch"],
            "agent/bio-compute-rest-contracts",
        )
        self.assertEqual(self.lock["source_blob_sha"], git_blob)
        self.assertEqual(self.lock["source_sha256"], sha256)
        self.assertEqual(self.lock["generated_sha256"], sha256)
        self.assertEqual(
            sha256,
            "963fe11c512d301e5e09f418a74b94ba88997fbda0acc3029ee50e112fbd5222",
        )

    def test_openapi_exposes_exactly_the_five_safe_compute_operations(self) -> None:
        operations = {
            item["post"]["operationId"]: (path, item["post"])
            for path, item in self.spec["paths"].items()
        }
        self.assertTrue(SAFE_OPERATIONS.keys() <= operations.keys())
        self.assertTrue(WITHHELD_OPERATIONS.isdisjoint(operations))

        for operation_id, expected in SAFE_OPERATIONS.items():
            path, operation = operations[operation_id]
            self.assertEqual(path, expected["path"])
            self.assertEqual(
                operation["x-tempera-required-scope"], expected["scope"]
            )
            self.assertEqual(operation["x-tempera-effect"], "derive_artifact")
            self.assertIs(operation["x-tempera-compute-only"], True)
            for boundary in FALSE_BOUNDARIES:
                self.assertIs(operation[boundary], False)

            request_ref = operation["requestBody"]["content"][
                "application/json"
            ]["schema"]["$ref"]
            request = self.spec["components"]["schemas"][
                request_ref.rsplit("/", 1)[1]
            ]
            self.assertEqual(set(request["properties"]), expected["body"])
            self.assertEqual(set(request["required"]), expected["body"])
            self.assertNotIn("contentDigest", request["properties"])
            self.assertIs(request["additionalProperties"], False)

            response = operation["responses"]["200"]["content"][
                "application/json"
            ]["schema"]
            self.assertIs(response["additionalProperties"], False)
            self.assertEqual(response["required"], ["result"])
            self.assertEqual(
                response["properties"]["result"]["$ref"],
                f"#/components/schemas/{expected['response']}",
            )

    def test_generated_sdk_surface_preserves_boundaries_and_required_fields(self) -> None:
        operations = {
            operation["id"]: operation
            for operation in self.surface["operations"]["temperaBio"]
        }
        self.assertTrue(SAFE_OPERATIONS.keys() <= operations.keys())
        self.assertTrue(WITHHELD_OPERATIONS.isdisjoint(operations))
        self.assertEqual(
            set(self.surface["scopeGaps"]),
            {"bio:claim:prepare", "bio:graph:project"},
        )

        for operation_id, expected in SAFE_OPERATIONS.items():
            operation = operations[operation_id]
            self.assertEqual(operation["path"], expected["path"])
            self.assertEqual(operation["scope"], expected["scope"])
            self.assertEqual(operation["auth"], "oauthResource")
            self.assertEqual(operation["authAudience"], "tempera-bio")
            self.assertIs(operation["physicalAction"], False)
            self.assertIs(operation["prepareCommitRequired"], False)
            self.assertEqual(set(operation["body"]), expected["body"])
            self.assertEqual(set(operation["requiredBody"]), expected["body"])
            self.assertEqual(operation["requestBodyKind"], "json")


if __name__ == "__main__":
    unittest.main()
