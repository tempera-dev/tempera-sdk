#!/usr/bin/env python3
"""Regression tests for shared generated SDK identifier transforms."""

from __future__ import annotations

import unittest

from sdk_names import snake_case


class SnakeCaseTests(unittest.TestCase):
    def test_preserves_acronyms_as_one_word(self) -> None:
        self.assertEqual(
            snake_case("ingestMaveDBScoreSet"),
            "ingest_mave_db_score_set",
        )

    def test_covers_product_and_parameter_names(self) -> None:
        self.assertEqual(snake_case("tempOS"), "temp_os")
        self.assertEqual(snake_case("dataEngine"), "data_engine")
        self.assertEqual(
            snake_case("rawMeasurementBase64"),
            "raw_measurement_base64",
        )

    def test_leaves_existing_snake_case_unchanged(self) -> None:
        self.assertEqual(snake_case("already_snake"), "already_snake")


if __name__ == "__main__":
    unittest.main()
