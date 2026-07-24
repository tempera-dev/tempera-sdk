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

        MODULE.synchronize_product(surface, "dataEngine", producer, set())

        operation = surface["operations"]["dataEngine"][0]
        self.assertEqual(operation["id"], "runUseCase")
        self.assertEqual(operation["path"], "/v1/{parent}/pipelines:runUseCase")

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
                surface, "dataEngine", {"paths": {}}, set()
            )


if __name__ == "__main__":
    unittest.main()
