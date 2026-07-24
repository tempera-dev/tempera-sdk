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
        violations = MODULE.discover_violations({"test": spec})
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
            },
        )

    def test_protocol_routes_are_explicitly_exempt(self) -> None:
        self.assertTrue(MODULE.is_protocol_exception("tempo", "/mcp"))
        self.assertTrue(MODULE.is_protocol_exception("remi", "/readyz"))
        self.assertTrue(
            MODULE.is_protocol_exception("palette", "/v1/otlp/t/p/e/v1/traces")
        )
        self.assertFalse(MODULE.is_protocol_exception("tempo", "/v1/sessions"))

    def test_list_detection_handles_common_operation_id_styles(self) -> None:
        for operation_id in ("listWidgets", "projects.widgets.list", "widgets-list"):
            with self.subTest(operation_id=operation_id):
                self.assertTrue(MODULE.is_list_operation(operation_id))
        self.assertFalse(MODULE.is_list_operation("getWidget"))

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


if __name__ == "__main__":
    unittest.main()
