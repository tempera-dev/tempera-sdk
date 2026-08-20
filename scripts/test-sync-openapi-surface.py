#!/usr/bin/env python3
"""Regression tests for producer-driven SDK surface synchronization."""

from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("sync-openapi-surface.py")
SPEC = importlib.util.spec_from_file_location("sync_openapi_surface", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SynchronizeProductTests(unittest.TestCase):
    @staticmethod
    def compound_surface(existing: dict | None = None) -> dict:
        return {
            "products": {"temperaGym": {"audience": "tempera-gym"}},
            "scopes": ["eval:run", "dataset:write", "dataset:read"],
            "scopeGaps": {},
            "operations": {
                "temperaGym": [] if existing is None else [existing],
            },
        }

    @staticmethod
    def export_producer(**authority: object) -> dict:
        return {
            "paths": {
                "/v1/episodes/{episode}:export": {
                    "post": {
                        "operationId": "episodes.export",
                        "summary": "Export an episode",
                        "x-tempera-auth-kind": "oauthResource",
                        "x-tempera-auth-audience": "tempera-gym",
                        "parameters": [
                            {
                                "name": "episode",
                                "in": "path",
                                "required": True,
                            }
                        ],
                        **authority,
                    }
                }
            }
        }

    def sync_export(self, surface: dict, **authority: object) -> dict:
        MODULE.synchronize_product(
            surface,
            "temperaGym",
            self.export_producer(**authority),
            set(),
            {},
        )
        return surface["operations"]["temperaGym"][0]

    def test_compound_scope_extension_preserves_exact_order_and_auth(self) -> None:
        operation = self.sync_export(
            self.compound_surface(),
            **{
                "x-tempera-required-scopes": [
                    "eval:run",
                    "dataset:write",
                ]
            },
        )

        self.assertEqual(operation["auth"], "oauthResource")
        self.assertEqual(operation["authAudience"], "tempera-gym")
        self.assertNotIn("scope", operation)
        self.assertEqual(
            operation["scopes"],
            ["eval:run", "dataset:write"],
        )

    def test_scope_transitions_remove_the_inactive_form_and_are_idempotent(self) -> None:
        existing = {
            "id": "exportEpisode",
            "upstreamOperationId": "episodes.export",
            "method": "POST",
            "path": "/v1/episodes/{episode}:export",
            "auth": "oauthResource",
            "authAudience": "tempera-gym",
            "scope": "eval:run",
            "description": "Export an episode.",
        }
        surface = self.compound_surface(existing)
        compound = {
            "x-tempera-required-scopes": ["eval:run", "dataset:write"]
        }
        first = self.sync_export(surface, **compound)
        self.assertNotIn("scope", first)
        self.assertEqual(first["scopes"], ["eval:run", "dataset:write"])

        first_snapshot = copy.deepcopy(surface)
        second = self.sync_export(surface, **compound)
        self.assertEqual(surface, first_snapshot)
        self.assertEqual(second["scopes"], ["eval:run", "dataset:write"])

        singular = self.sync_export(
            surface,
            **{"x-tempera-required-scope": "dataset:read"},
        )
        self.assertEqual(singular["scope"], "dataset:read")
        self.assertNotIn("scopes", singular)

        plural_again = self.sync_export(surface, **compound)
        self.assertNotIn("scope", plural_again)
        self.assertEqual(
            plural_again["scopes"], ["eval:run", "dataset:write"]
        )

        no_declaration = self.sync_export(surface)
        self.assertNotIn("scopes", no_declaration)

    def test_legacy_singular_null_remains_an_explicit_clear(self) -> None:
        existing = {
            "id": "exportEpisode",
            "upstreamOperationId": "episodes.export",
            "method": "POST",
            "path": "/v1/episodes/{episode}:export",
            "auth": "oauthResource",
            "authAudience": "tempera-gym",
            "scopes": ["eval:run", "dataset:write"],
            "description": "Export an episode.",
        }
        operation = self.sync_export(
            self.compound_surface(existing),
            **{"x-tempera-required-scope": None},
        )
        self.assertNotIn("scope", operation)
        self.assertNotIn("scopes", operation)

    def test_compound_scope_extension_rejects_ambiguous_or_malformed_sets(self) -> None:
        invalid_authority = [
            {
                "x-tempera-required-scope": None,
                "x-tempera-required-scopes": ["eval:run", "dataset:write"],
            },
            {
                "x-tempera-required-scope": "eval:run",
                "x-tempera-required-scopes": ["eval:run", "dataset:write"],
            },
            {"x-tempera-required-scopes": None},
            {"x-tempera-required-scopes": "eval:run dataset:write"},
            {"x-tempera-required-scopes": []},
            {"x-tempera-required-scopes": ["eval:run", "eval:run"]},
            {"x-tempera-required-scopes": ["eval:run", " dataset:write"]},
            {"x-tempera-required-scopes": ["eval:run", "dataset:write extra"]},
            {"x-tempera-required-scopes": ["eval:run", "dataset:\\write"]},
            {"x-tempera-required-scopes": ["eval:run", "dataset:\"write"]},
            {"x-tempera-required-scopes": ["eval:run", "dataset:write-🧪"]},
            {"x-tempera-required-scopes": ["x" * 257]},
            {
                "x-tempera-required-scopes": [
                    f"scope:{index}" for index in range(65)
                ]
            },
        ]
        for authority in invalid_authority:
            with self.subTest(authority=authority):
                with self.assertRaisesRegex(
                    ValueError, "required-scope|required-scopes"
                ):
                    self.sync_export(self.compound_surface(), **authority)

    def test_singular_scope_extension_rejects_malformed_tokens(self) -> None:
        invalid_authority = [
            {"x-tempera-required-scope": ""},
            {"x-tempera-required-scope": ["eval:run"]},
            {"x-tempera-required-scope": " eval:run"},
            {"x-tempera-required-scope": "eval:run extra"},
            {"x-tempera-required-scope": "eval:\\run"},
            {"x-tempera-required-scope": "eval:\"run"},
            {"x-tempera-required-scope": "eval:run-🧪"},
            {"x-tempera-required-scope": "x" * 257},
        ]
        for authority in invalid_authority:
            with self.subTest(authority=authority):
                with self.assertRaisesRegex(ValueError, "required-scope"):
                    self.sync_export(self.compound_surface(), **authority)

    def test_unknown_compound_member_requires_registry_or_explicit_gap(self) -> None:
        authority = {
            "x-tempera-required-scopes": ["eval:run", "future:scope"]
        }
        with self.assertRaisesRegex(ValueError, "unregistered required scope"):
            self.sync_export(self.compound_surface(), **authority)

        surface = self.compound_surface()
        surface["scopeGaps"]["future:scope"] = {
            "owner": "tempera-gym",
            "reportedDate": "2026-08-20",
            "status": "staged",
            "migration": "register before release",
        }
        operation = self.sync_export(surface, **authority)
        self.assertEqual(operation["scopes"], ["eval:run", "future:scope"])

    def test_oauth_security_and_authority_extension_cannot_both_declare_scope(self) -> None:
        producer = self.export_producer(
            **{"x-tempera-required-scopes": ["eval:run", "dataset:write"]}
        )
        producer["paths"]["/v1/episodes/{episode}:export"]["post"]["security"] = [
            {"tempera_oauth": ["eval:run"]}
        ]
        with self.assertRaisesRegex(ValueError, "both OAuth security"):
            MODULE.synchronize_product(
                self.compound_surface(),
                "temperaGym",
                producer,
                set(),
                {},
            )

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
