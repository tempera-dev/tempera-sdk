#!/usr/bin/env python3
"""Focused tests for the Palette source-receipt authority binding."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("sync-palette-eval-openapi.py")
SPEC = importlib.util.spec_from_file_location("sync_palette_eval_openapi", SCRIPT)
assert SPEC and SPEC.loader
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class PaletteSourceReceiptTest(unittest.TestCase):
    def test_repository_receipt_matches_the_evaluation_contract_pin(self) -> None:
        sync.validate_source_receipt()

    def test_commit_drift_is_rejected(self) -> None:
        receipt = json.loads(sync.SOURCE_RECEIPT.read_text(encoding="utf-8"))
        receipt["source_commit"] = "0" * 40
        self._assert_receipt_rejected(receipt)

    def test_unexpected_receipt_fields_are_rejected(self) -> None:
        receipt = json.loads(sync.SOURCE_RECEIPT.read_text(encoding="utf-8"))
        receipt["unreviewed"] = True
        self._assert_receipt_rejected(receipt)

    def _assert_receipt_rejected(self, receipt: dict[str, object]) -> None:
        with tempfile.TemporaryDirectory(
            prefix="tempera-sdk-palette-receipt-"
        ) as directory:
            path = Path(directory) / "palette-api.json.source"
            path.write_text(json.dumps(receipt), encoding="utf-8")
            with mock.patch.object(sync, "SOURCE_RECEIPT", path):
                with self.assertRaisesRegex(
                    sync.ContractError,
                    "source receipt differs from the evaluation contract pin",
                ):
                    sync.validate_source_receipt()


if __name__ == "__main__":
    unittest.main()
