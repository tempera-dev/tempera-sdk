#!/usr/bin/env python3
"""Focused tests for bidirectional upstream operation classification."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("check-upstream-drift.py")
SPEC = importlib.util.spec_from_file_location("check_upstream_drift", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)

SYNC_SCRIPT = Path(__file__).with_name("sync-openapi-surface.py")
SYNC_SPEC = importlib.util.spec_from_file_location(
    "sync_openapi_surface", SYNC_SCRIPT
)
assert SYNC_SPEC is not None and SYNC_SPEC.loader is not None
SYNCHRONIZER = importlib.util.module_from_spec(SYNC_SPEC)
SYNC_SPEC.loader.exec_module(SYNCHRONIZER)


class UpstreamDriftTest(unittest.TestCase):
    def test_parameter_names_are_structural(self) -> None:
        self.assertEqual(
            CHECKER.normalize_path("/v1/runs/{runId}/events"),
            CHECKER.normalize_path("/v1/runs/{run_id}/events"),
        )

    def test_phantom_and_missing_are_both_detected(self) -> None:
        shared = ("GET", "/shared")
        phantom = ("POST", "/phantom")
        missing = ("DELETE", "/missing")
        observed = CHECKER.classify_routes(
            {shared: "shared", phantom: "phantom"},
            {shared: "shared", missing: "missing"},
            set(),
        )
        self.assertEqual(observed, ({phantom}, {missing}, set()))

    def test_reviewed_exclusion_removes_only_matching_missing_route(self) -> None:
        missing = ("GET", "/v1/runs/{}/events")
        observed = CHECKER.classify_routes(
            {},
            {missing: "runs.events"},
            {missing},
        )
        self.assertEqual(observed, (set(), set(), set()))

    def test_supported_or_absent_exclusion_is_stale(self) -> None:
        route = ("GET", "/v1/runs/{}/events")
        self.assertEqual(
            CHECKER.classify_routes(
                {route: "events"},
                {route: "runs.events"},
                {route},
            )[2],
            {route},
        )
        self.assertEqual(
            CHECKER.classify_routes({}, {}, {route})[2],
            {route},
        )

    def test_http_route_manifest_generates_authoritative_request_fields(self) -> None:
        surface = {
            "operations": {
                "remi": [
                    {
                        "id": "remember",
                        "method": "POST",
                        "path": "/v1/remember",
                        "auth": "product",
                        "body": ["stale"],
                        "requiredBody": ["stale"],
                        "forbiddenBody": ["stale"],
                        "description": "Stale description.",
                    }
                ]
            }
        }
        manifest = {
            "contract_kind": "http-route-manifest",
            "endpoints": [
                {
                    "operation": "livez",
                    "method": "GET",
                    "path": "/livez",
                    "auth": "public",
                },
                {
                    "operation": "remember",
                    "method": "POST",
                    "path": "/v1/remember",
                    "auth": "bearer",
                    "request_schema": "RememberHttpRequest",
                    "request_fields": ["tenant_id", "project_id", "kind", "text"],
                    "required_request_fields": [
                        "tenant_id",
                        "project_id",
                        "kind",
                        "text",
                    ],
                    "description": "Write one memory event.",
                },
            ],
        }

        SYNCHRONIZER.synchronize_product(
            surface, "remi", manifest, exclusions=set(), overrides={}
        )

        self.assertEqual(
            [item["id"] for item in surface["operations"]["remi"]],
            ["livez", "remember"],
        )
        self.assertEqual(surface["operations"]["remi"][0]["auth"], "none")
        self.assertEqual(
            surface["operations"]["remi"][1]["body"],
            ["tenant_id", "project_id", "kind", "text"],
        )
        self.assertEqual(
            surface["operations"]["remi"][1]["requiredBody"],
            ["tenant_id", "project_id", "kind", "text"],
        )
        self.assertNotIn("forbiddenBody", surface["operations"]["remi"][1])
        self.assertEqual(
            surface["operations"]["remi"][1]["description"],
            "Write one memory event.",
        )

    def test_one_of_only_requires_fields_shared_by_every_variant(self) -> None:
        document = {
            "components": {
                "schemas": {
                    "Generic": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "payload": {"type": "object"},
                        },
                    },
                    "Strict": {
                        "type": "object",
                        "required": ["source", "payload", "signature"],
                        "properties": {
                            "source": {"type": "string"},
                            "payload": {"type": "object"},
                            "signature": {"type": "string"},
                        },
                    },
                }
            }
        }
        schema = {
            "oneOf": [
                {"$ref": "#/components/schemas/Generic"},
                {"$ref": "#/components/schemas/Strict"},
            ]
        }

        properties, required = SYNCHRONIZER.schema_fields(document, schema)

        self.assertEqual(properties, ["source", "payload", "signature"])
        self.assertEqual(required, [])

    def test_all_of_unions_required_fields(self) -> None:
        properties, required = SYNCHRONIZER.schema_fields(
            {},
            {
                "allOf": [
                    {
                        "type": "object",
                        "required": ["left"],
                        "properties": {"left": {"type": "string"}},
                    },
                    {
                        "type": "object",
                        "required": ["right"],
                        "properties": {"right": {"type": "string"}},
                    },
                ]
            },
        )

        self.assertEqual(properties, ["left", "right"])
        self.assertEqual(required, ["left", "right"])

    def test_aip_resource_path_template_is_generated_from_parameter(self) -> None:
        surface = {"operations": {"dataEngine": []}}
        spec = {
            "paths": {
                "/v1/{parent}/artifacts": {
                    "get": {
                        "operationId": "projects.artifacts.list",
                        "parameters": [
                            {
                                "name": "parent",
                                "in": "path",
                                "required": True,
                                "x-tempera-resource-pattern": "projects/*",
                                "schema": {"type": "string"},
                            }
                        ],
                        "responses": {"200": {"description": "ok"}},
                    }
                }
            }
        }

        SYNCHRONIZER.synchronize_product(
            surface, "dataEngine", spec, exclusions=set(), overrides={}
        )

        self.assertEqual(
            surface["operations"]["dataEngine"][0]["pathParamTemplates"],
            {"parent": "projects/*"},
        )

    def test_operation_id_preserves_sdk_method_across_aip_path_move(self) -> None:
        surface = {
            "operations": {
                "dataEngine": [
                    {
                        "id": "runUseCase",
                        "upstreamOperationId": "projects.pipelines.runUseCase",
                        "method": "POST",
                        "path": "/v1/{parent}/pipelines:run-use-case",
                        "auth": "product",
                        "description": "Run one use case.",
                    }
                ]
            }
        }
        spec = {
            "paths": {
                "/v1/{parent}/pipelines:runUseCase": {
                    "post": {
                        "operationId": "projects.pipelines.runUseCase",
                        "responses": {"200": {"description": "ok"}},
                    }
                }
            }
        }

        SYNCHRONIZER.synchronize_product(
            surface, "dataEngine", spec, exclusions=set(), overrides={}
        )

        operation = surface["operations"]["dataEngine"][0]
        self.assertEqual(operation["id"], "runUseCase")
        self.assertEqual(
            operation["path"], "/v1/{parent}/pipelines:runUseCase"
        )

    def test_override_and_producer_auth_extensions_are_both_enforced(self) -> None:
        surface = {"operations": {"controlPlane": []}}
        spec = {
            "paths": {
                "/bio-signer-keys": {
                    "get": {
                        "operationId": "bioSignerKeys.list",
                        "summary": "List Bio signer keys.",
                        "x-tempera-auth-kind": "oauthResource",
                        "x-tempera-auth-audience": "tempera-bio",
                        "x-tempera-required-scope": "bio:signer:manage",
                        "responses": {"200": {"description": "ok"}},
                    }
                }
            }
        }
        overrides = {
            ("GET", "/bio-signer-keys"): {
                "upstreamOperationId": "bioSignerKeys.list",
                "id": "listBioSignerKeys",
            }
        }

        SYNCHRONIZER.synchronize_product(
            surface,
            "controlPlane",
            spec,
            exclusions=set(),
            overrides=overrides,
        )

        operation = surface["operations"]["controlPlane"][0]
        self.assertEqual(operation["id"], "listBioSignerKeys")
        self.assertEqual(operation["auth"], "oauthResource")
        self.assertEqual(operation["authAudience"], "tempera-bio")
        self.assertEqual(operation["scope"], "bio:signer:manage")

    def test_unauthenticated_probe_accepts_explicit_null_auth_metadata(self) -> None:
        surface = {"operations": {"temperaGym": []}}
        spec = {
            "paths": {
                "/healthz": {
                    "get": {
                        "operationId": "health.get",
                        "security": [],
                        "x-tempera-auth-audience": None,
                        "x-tempera-required-scope": None,
                        "responses": {"200": {"description": "ok"}},
                    }
                }
            }
        }

        SYNCHRONIZER.synchronize_product(
            surface,
            "temperaGym",
            spec,
            exclusions=set(),
            overrides={},
        )

        operation = surface["operations"]["temperaGym"][0]
        self.assertEqual(operation["auth"], "none")
        self.assertNotIn("authAudience", operation)
        self.assertNotIn("scope", operation)

    def test_producer_audience_implies_oauth_resource_auth(self) -> None:
        surface = {"operations": {"temperaGym": []}}
        spec = {
            "paths": {
                "/v1/tasks": {
                    "get": {
                        "operationId": "tasks.list",
                        "x-tempera-auth-audience": "tempera-gym",
                        "x-tempera-required-scope": "dataset:read",
                        "responses": {"200": {"description": "ok"}},
                    }
                }
            }
        }

        SYNCHRONIZER.synchronize_product(
            surface,
            "temperaGym",
            spec,
            exclusions=set(),
            overrides={},
        )

        operation = surface["operations"]["temperaGym"][0]
        self.assertEqual(operation["auth"], "oauthResource")
        self.assertEqual(operation["authAudience"], "tempera-gym")
        self.assertEqual(operation["scope"], "dataset:read")

if __name__ == "__main__":
    unittest.main()
