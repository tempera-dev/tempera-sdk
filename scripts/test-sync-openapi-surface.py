#!/usr/bin/env python3
"""Regression tests for producer-driven SDK surface synchronization."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("sync-openapi-surface.py")
SPEC = importlib.util.spec_from_file_location("sync_openapi_surface", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SynchronizeProductTests(unittest.TestCase):
    def test_sentence_repairs_a_rust_doc_summary_split(self) -> None:
        self.assertEqual(
            MODULE.sentence(
                {
                    "summary": "Resolve an ambiguous dispatch. This",
                    "description": "operation can only look up the provider order.",
                },
                "post",
                "/v1/example:reconcile",
            ),
            (
                "Resolve an ambiguous dispatch. This operation can only look up "
                "the provider order."
            ),
        )

    def test_workflows_campaign_compiler_keeps_the_canonical_sdk_name(self) -> None:
        path = "/v1/workflows/{workflowId}:compileBioCampaign"
        identity = MODULE.product_route("temperaWorkflows", "POST", path)
        overrides = MODULE.load_overrides()["temperaWorkflows"]
        surface = {"operations": {"temperaWorkflows": []}}
        producer = {
            "paths": {
                path: {
                    "post": {
                        "operationId": "workflows.compileBioCampaign",
                        "summary": "Compile a Bio campaign",
                        "x-tempera-physical-action": False,
                        "x-tempera-prepare-commit-required": False,
                        "parameters": [
                            {
                                "name": "workflowId",
                                "in": "path",
                                "required": True,
                            }
                        ],
                    }
                }
            }
        }

        MODULE.synchronize_product(
            surface,
            "temperaWorkflows",
            producer,
            set(),
            {identity: overrides[identity]},
        )

        operation = surface["operations"]["temperaWorkflows"][0]
        self.assertEqual(operation["id"], "compileBioCampaign")
        self.assertEqual(
            operation["upstreamOperationId"],
            "workflows.compileBioCampaign",
        )
        self.assertFalse(operation["physicalAction"])
        self.assertFalse(operation["prepareCommitRequired"])

    def test_workflows_physical_action_metadata_is_exact_and_fail_closed(self) -> None:
        path = "/v1/experimentSubmissions"
        surface = {"operations": {"temperaWorkflows": []}}
        producer = {
            "paths": {
                path: {
                    "post": {
                        "operationId": "experimentSubmissions.create",
                        "summary": "Submit an experiment",
                        "x-tempera-physical-action": True,
                        "x-tempera-prepare-commit-required": True,
                    }
                }
            }
        }

        MODULE.synchronize_product(
            surface, "temperaWorkflows", producer, set(), {}
        )

        operation = surface["operations"]["temperaWorkflows"][0]
        self.assertTrue(operation["physicalAction"])
        self.assertTrue(operation["prepareCommitRequired"])

        for missing_key in (
            "x-tempera-physical-action",
            "x-tempera-prepare-commit-required",
        ):
            invalid = {
                "paths": {
                    path: {
                        "post": {
                            **producer["paths"][path]["post"],
                        }
                    }
                }
            }
            invalid["paths"][path]["post"].pop(missing_key)
            with self.assertRaisesRegex(
                ValueError, "must explicitly declare"
            ):
                MODULE.synchronize_product(
                    {"operations": {"temperaWorkflows": []}},
                    "temperaWorkflows",
                    invalid,
                    set(),
                    {},
                )

        invalid = {
            "paths": {
                path: {
                    "post": {
                        **producer["paths"][path]["post"],
                        "x-tempera-physical-action": False,
                    }
                }
            }
        }
        with self.assertRaisesRegex(
            ValueError, "without being a physical action"
        ):
            MODULE.synchronize_product(
                {"operations": {"temperaWorkflows": []}},
                "temperaWorkflows",
                invalid,
                set(),
                {},
            )

    def test_preserves_sdk_identity_across_aip_path_migration(self) -> None:
        surface = {
            "operations": {
                "dataEngine": [
                    {
                        "id": "runUseCase",
                        "method": "POST",
                        "path": "/v1/{parent}/pipelines:run-use-case",
                        "auth": "product",
                        "description": "Run a use case.",
                        "upstreamOperationId": "projects.pipelines.runUseCase",
                    }
                ]
            }
        }
        producer = {
            "paths": {
                "/v1/{parent}/pipelines:runUseCase": {
                    "post": {
                        "operationId": "projects.pipelines.runUseCase",
                        "summary": "Run a use case",
                    }
                }
            }
        }

        MODULE.synchronize_product(surface, "dataEngine", producer, set(), {})

        operation = surface["operations"]["dataEngine"][0]
        self.assertEqual(operation["id"], "runUseCase")
        self.assertEqual(operation["path"], "/v1/{parent}/pipelines:runUseCase")

    def test_deprecated_alias_with_new_operation_id_gets_a_distinct_sdk_name(
        self,
    ) -> None:
        """A Clearing-style AIP action migration cannot collapse aliases."""

        legacy_path = "/v1/actions/{id}/commit"
        canonical_path = "/v1/actions/{id}:commit"
        surface = {
            "operations": {
                "temperaClearing": [
                    {
                        "id": "commitClearingAction",
                        "method": "POST",
                        "path": legacy_path,
                        "auth": "product",
                        "description": "Commit a clearing action.",
                        "upstreamOperationId": "commitClearingAction",
                    }
                ]
            }
        }
        producer = {
            "paths": {
                canonical_path: {
                    "post": {
                        "operationId": "commitClearingAction",
                        "summary": "Commit a clearing action",
                    }
                },
                legacy_path: {
                    "post": {
                        "operationId": "commitClearingActionLegacy",
                        "summary": "Commit a clearing action (legacy)",
                        "deprecated": True,
                    }
                },
            }
        }

        MODULE.synchronize_product(
            surface, "temperaClearing", producer, set(), {}
        )

        operations = surface["operations"]["temperaClearing"]
        self.assertEqual(
            [(item["path"], item["id"], item["upstreamOperationId"]) for item in operations],
            [
                (
                    canonical_path,
                    "commitClearingAction",
                    "commitClearingAction",
                ),
                (
                    legacy_path,
                    "commitClearingActionLegacy",
                    "commitClearingActionLegacy",
                ),
            ],
        )

    def test_required_query_parameters_are_preserved_from_openapi(self) -> None:
        path = "/v1/payment_intents/{payment_intent_id}"
        surface = {"operations": {"temperaPayments": []}}
        producer = {
            "paths": {
                path: {
                    "get": {
                        "operationId": "getPaymentIntent",
                        "summary": "Read a payment intent",
                        "parameters": [
                            {"name": "payment_intent_id", "in": "path", "required": True},
                            {"name": "tenant_id", "in": "query", "required": True},
                            {"name": "expand", "in": "query", "required": False},
                        ],
                    }
                }
            }
        }

        MODULE.synchronize_product(surface, "temperaPayments", producer, set(), {})

        operation = surface["operations"]["temperaPayments"][0]
        self.assertEqual(operation["query"], ["tenant_id", "expand"])
        self.assertEqual(operation["requiredQuery"], ["tenant_id"])

    def test_still_rejects_unexplained_deleted_routes(self) -> None:
        surface = {
            "operations": {
                "dataEngine": [
                    {
                        "id": "removed",
                        "method": "GET",
                        "path": "/v1/{parent}/removed",
                        "auth": "product",
                        "description": "Removed operation.",
                        "upstreamOperationId": "projects.removed.get",
                    }
                ]
            }
        }

        with self.assertRaisesRegex(ValueError, "phantom surface routes"):
            MODULE.synchronize_product(
                surface, "dataEngine", {"paths": {}}, set(), {}
            )


if __name__ == "__main__":
    unittest.main()
