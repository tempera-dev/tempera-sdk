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

    def test_warning_migration_counts_are_pinned(self) -> None:
        migration = {
            "phantom_routes": 1,
            "upstream_only_routes": 2,
            "duplicate_routes": 0,
        }
        self.assertEqual(
            CHECKER.migration_count_errors(
                "palette",
                migration,
                phantom=1,
                upstream_only=2,
                duplicates=0,
            ),
            [],
        )
        self.assertTrue(
            CHECKER.migration_count_errors(
                "palette",
                migration,
                phantom=0,
                upstream_only=2,
                duplicates=0,
            )
        )


if __name__ == "__main__":
    unittest.main()
