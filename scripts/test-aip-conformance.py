#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("check-aip-conformance.py")
SPEC = importlib.util.spec_from_file_location("check_aip_conformance", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AipConformanceTest(unittest.TestCase):
    def test_discovers_mechanical_aip_violations(self) -> None:
        spec = {
            "openapi": "3.1.0",
            "paths": {
                "/workflows/{workflow_id}": {
                    "put": {
                        "operationId": "updateWorkflow",
                        "parameters": [
                            {
                                "name": "workflow_id",
                                "in": "path",
                                "required": True,
                            }
                        ],
                    }
                },
                "/v1/widgets": {
                    "get": {
                        "operationId": "listWidgets",
                        "parameters": [],
                    }
                },
                "/v1/widgets/{name}:run-job": {
                    "post": {
                        "operationId": "runWidgetJob",
                        "parameters": [
                            {"name": "name", "in": "path", "required": True}
                        ],
                    }
                },
                "/v1/widgets/{name}": {
                    "patch": {
                        "operationId": "updateWidget",
                        "parameters": [
                            {"name": "name", "in": "path", "required": True}
                        ],
                    }
                },
            },
        }
        violations = MODULE.discover_violations({"test": spec}, MODULE.SDK_EXEMPTIONS)
        rules = {value["rule"] for value in violations.values()}
        self.assertEqual(
            rules,
            {
                "aip-127-versioned-path",
                "aip-127-no-put",
                "aip-127-lower-camel-parameters",
                "aip-136-lower-camel-custom-verb",
                "aip-158-list-pagination",
                "aip-161-update-mask",
                "aip-193-standard-errors",
            },
        )

    def test_discovers_lower_camel_json_fields_through_local_refs(self) -> None:
        spec = {
            "openapi": "3.1.0",
            "components": {
                "schemas": {
                    "Widget": {
                        "type": "object",
                        "properties": {
                            "display_name": {"type": "string"},
                            "nestedValue": {
                                "type": "object",
                                "properties": {
                                    "created_at": {"type": "string"},
                                },
                            },
                        },
                    }
                }
            },
            "paths": {
                "/v1/widgets": {
                    "post": {
                        "operationId": "createWidget",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Widget"
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "$ref": "#/components/schemas/Widget"
                                        }
                                    }
                                }
                            }
                        },
                    }
                }
            },
        }
        violations = MODULE.discover_violations({"test": spec}, MODULE.SDK_EXEMPTIONS)
        key = "test|POST|/v1/widgets|aip-127-lower-camel-json-fields"
        self.assertEqual(
            violations[key]["observed"],
            ["created_at", "display_name"],
        )

    def test_protocol_routes_exempt_json_field_names(self) -> None:
        spec = {
            "openapi": "3.1.0",
            "paths": {
                "/oauth/token": {
                    "post": {
                        "operationId": "oauthToken",
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "access_token": {"type": "string"}
                                            },
                                        }
                                    }
                                }
                            }
                        },
                    }
                }
            },
        }
        violations = MODULE.discover_violations({"controlPlane": spec}, MODULE.SDK_EXEMPTIONS)
        self.assertNotIn(
            "controlPlane|POST|/oauth/token|aip-127-lower-camel-json-fields",
            violations,
        )
        self.assertNotIn(
            "controlPlane|POST|/oauth/token|aip-193-standard-errors",
            violations,
        )

    def test_discovers_non_standard_error_schemas(self) -> None:
        spec = {
            "openapi": "3.1.0",
            "paths": {
                "/v1/widgets/{name}": {
                    "get": {
                        "operationId": "getWidget",
                        "parameters": [{"name": "name", "in": "path"}],
                        "responses": {
                            "404": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "error": {
                                                    "type": "object",
                                                    "properties": {
                                                        "code": {
                                                            "type": "string"
                                                        },
                                                        "message": {
                                                            "type": "string"
                                                        },
                                                    },
                                                }
                                            },
                                        }
                                    }
                                }
                            }
                        },
                    }
                }
            },
        }
        violations = MODULE.discover_violations({"test": spec}, MODULE.SDK_EXEMPTIONS)
        key = "test|GET|/v1/widgets/{name}|aip-193-standard-errors"
        self.assertEqual(
            violations[key]["observed"],
            [
                "404:error.code:string",
                "404:error.details",
                "404:error.status",
            ],
        )

    def test_accepts_google_rpc_status_compatible_error_schema(self) -> None:
        spec = {
            "openapi": "3.1.0",
            "paths": {
                "/v1/widgets/{name}": {
                    "get": {
                        "operationId": "getWidget",
                        "parameters": [{"name": "name", "in": "path"}],
                        "responses": {
                            "404": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "error": {
                                                    "type": "object",
                                                    "properties": {
                                                        "code": {
                                                            "type": "integer"
                                                        },
                                                        "status": {
                                                            "type": "string"
                                                        },
                                                        "message": {
                                                            "type": "string"
                                                        },
                                                        "details": {
                                                            "type": "array",
                                                            "items": {
                                                                "type": "object"
                                                            },
                                                        },
                                                    },
                                                }
                                            },
                                        }
                                    }
                                }
                            }
                        },
                    }
                }
            },
        }
        violations = MODULE.discover_violations({"test": spec}, MODULE.SDK_EXEMPTIONS)
        self.assertNotIn(
            "test|GET|/v1/widgets/{name}|aip-193-standard-errors",
            violations,
        )

    def test_protocol_routes_are_explicitly_exempt(self) -> None:
        self.assertTrue(MODULE.SDK_EXEMPTIONS.covers_path("tempo", "/mcp"))
        self.assertTrue(
            MODULE.SDK_EXEMPTIONS.covers_path("controlPlane", "/github/callback")
        )
        self.assertTrue(
            MODULE.SDK_EXEMPTIONS.covers_path("tempo", "/.well-known/agent-card.json")
        )
        self.assertTrue(MODULE.SDK_EXEMPTIONS.covers_path("remi", "/readyz"))
        self.assertTrue(MODULE.SDK_EXEMPTIONS.covers_path("temperaLlm", "/readyz"))
        # tempera-llm's three OpenAI-wire routes are exempt from the field-name
        # rule only. They are ordinary /v1 resource routes in every other
        # respect, and waiving the whole route would have hidden a pagination
        # or standard-error regression on the busiest surface in the fleet.
        for method, path in (
            ("GET", "/v1/models"),
            ("POST", "/v1/chat/completions"),
            ("POST", "/v1/responses"),
        ):
            self.assertIn(
                ("temperaLlm", method, path),
                MODULE.SDK_EXEMPTIONS.json_payloads,
            )
            self.assertFalse(MODULE.SDK_EXEMPTIONS.covers_path("temperaLlm", path))
        self.assertTrue(
            MODULE.SDK_EXEMPTIONS.covers_path("palette", "/v1/otlp/t/p/e/v1/traces")
        )
        self.assertFalse(MODULE.SDK_EXEMPTIONS.covers_path("tempo", "/v1/sessions"))

    def test_list_detection_handles_common_operation_id_styles(self) -> None:
        for operation_id in ("listWidgets", "projects.widgets.list", "widgets-list"):
            with self.subTest(operation_id=operation_id):
                self.assertTrue(MODULE.is_list_operation(operation_id))
        self.assertFalse(MODULE.is_list_operation("getWidget"))

    def test_resolves_referenced_pagination_parameters(self) -> None:
        spec = {
            "openapi": "3.1.0",
            "components": {
                "parameters": {
                    "PageSize": {"name": "pageSize", "in": "query"},
                    "PageToken": {"name": "pageToken", "in": "query"},
                }
            },
            "paths": {
                "/v1/widgets": {
                    "get": {
                        "operationId": "widgets.list",
                        "parameters": [
                            {"$ref": "#/components/parameters/PageSize"},
                            {"$ref": "#/components/parameters/PageToken"},
                        ],
                    }
                }
            },
        }
        violations = MODULE.discover_violations({"test": spec}, MODULE.SDK_EXEMPTIONS)
        self.assertNotIn(
            "test|GET|/v1/widgets|aip-158-list-pagination",
            violations,
        )

    def test_full_local_reference_walk_resolves_and_rejects_dangling_refs(self) -> None:
        valid = {
            "components": {
                "schemas": {
                    "Widget/Name": {"type": "string"},
                }
            },
            "paths": {
                "/v1/widgets": {
                    "get": {
                        "responses": {
                            "200": {
                                "$ref": "#/components/schemas/Widget~1Name"
                            }
                        }
                    }
                }
            },
        }
        self.assertEqual(MODULE.validate_local_references({"test": valid}), [])
        valid["paths"]["/v1/widgets"]["get"]["responses"]["409"] = {
            "$ref": "#/components/responses/AlreadyExists"
        }
        failures = MODULE.validate_local_references({"test": valid})
        self.assertEqual(len(failures), 1)
        self.assertIn("AlreadyExists", failures[0])

    def test_route_manifest_query_fields_are_inspected(self) -> None:
        manifest = {
            "contract_kind": "http-route-manifest",
            "endpoints": [
                {
                    "operation": "widgets.list",
                    "method": "GET",
                    "path": "/v1/widgets",
                    "query_fields": ["pageSize", "pageToken"],
                }
            ],
        }
        violations = MODULE.discover_violations({"test": manifest}, MODULE.SDK_EXEMPTIONS)
        self.assertNotIn(
            "test|GET|/v1/widgets|aip-158-list-pagination",
            violations,
        )

    def test_route_manifest_wire_fields_and_error_types_are_inspected(self) -> None:
        manifest = {
            "contract_kind": "http-route-manifest",
            "error_shape": {
                "fields": [
                    "error.code",
                    "error.status",
                    "error.message",
                    "error.details",
                ],
                "field_types": {
                    "error.code": "integer",
                    "error.status": "string",
                    "error.message": "string",
                    "error.details": "array",
                },
            },
            "endpoints": [
                {
                    "operation": "createWidget",
                    "method": "POST",
                    "path": "/v1/widgets",
                    "request_fields": ["display_name"],
                }
            ],
        }
        violations = MODULE.discover_violations({"test": manifest}, MODULE.SDK_EXEMPTIONS)
        json_key = (
            "test|POST|/v1/widgets|aip-127-lower-camel-json-fields"
        )
        self.assertEqual(violations[json_key]["observed"], ["display_name"])
        self.assertNotIn(
            "test|POST|/v1/widgets|aip-193-standard-errors",
            violations,
        )

    def test_stale_protocol_exceptions_are_rejected(self) -> None:
        failures = MODULE.validate_protocol_exceptions(
            {
                product: {"openapi": "3.1.0", "paths": {}}
                for product in MODULE.SPECS
            }
        )
        self.assertTrue(
            any("stale exact protocol exception" in failure for failure in failures)
        )

    def test_exact_oauth_introspection_operation_is_protocol_native(self) -> None:
        spec = {
            "openapi": "3.1.0",
            "paths": {
                "/v1/oauth/introspect": {
                    "post": {
                        "operationId": "introspectOAuthToken",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "token_type_hint": {"type": "string"}
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "token_type": {"type": "string"}
                                            },
                                        }
                                    }
                                }
                            }
                        },
                    }
                }
            },
        }
        self.assertEqual(MODULE.discover_violations({"controlPlane": spec}, MODULE.SDK_EXEMPTIONS), {})

    def test_embedded_oauth_response_only_exempts_json_spelling(self) -> None:
        spec = {
            "openapi": "3.1.0",
            "paths": {
                "/v1/sessions": {
                    "post": {
                        "operationId": "createHostedSession",
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "access_token": {"type": "string"}
                                            },
                                        }
                                    }
                                }
                            }
                        },
                    }
                }
            },
        }
        violations = MODULE.discover_violations({"controlPlane": spec}, MODULE.SDK_EXEMPTIONS)
        self.assertNotIn(
            "controlPlane|POST|/v1/sessions|aip-127-lower-camel-json-fields",
            violations,
        )
        self.assertIn(
            "controlPlane|POST|/v1/sessions|aip-193-standard-errors",
            violations,
        )


if __name__ == "__main__":
    unittest.main()
