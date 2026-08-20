#!/usr/bin/env python3
"""Documentation regressions for compound operation authority."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "gen_sdk_docs", ROOT / "scripts" / "gen-sdk-docs.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load gen-sdk-docs.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CompoundScopeDocumentationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.surface = json.loads((ROOT / "surface.json").read_text())

    def compound_surface(self) -> tuple[dict, dict]:
        surface = copy.deepcopy(self.surface)
        operation = next(
            candidate
            for candidate in surface["operations"]["temperaGym"]
            if candidate["id"] == "exportEpisode"
        )
        operation.pop("scope", None)
        operation["scopes"] = ["eval:run", "dataset:write"]
        return surface, operation

    def test_operation_docs_preserve_all_required_wording_and_order(self) -> None:
        surface, operation = self.compound_surface()
        rendered = "\n".join(
            MODULE.operation_section(surface, "temperaGym", operation)
        )
        self.assertIn(
            "- **Scopes (all required):** `eval:run`, `dataset:write`",
            rendered,
        )
        self.assertNotIn("- **Scope:**", rendered)

    def test_authentication_index_lists_operation_under_every_member(self) -> None:
        surface, _ = self.compound_surface()
        rendered = MODULE.render_authentication(surface)
        for scope in ("eval:run", "dataset:write"):
            row = next(
                line
                for line in rendered.splitlines()
                if line.startswith(f"| `{scope}` |")
            )
            self.assertIn(
                f"{surface['products']['temperaGym']['name']}: ", row
            )
            self.assertIn("`exportEpisode`", row)

    def test_compound_gap_is_disclosed_on_the_operation(self) -> None:
        surface, operation = self.compound_surface()
        operation["scopes"].append("future:scope")
        surface["scopeGaps"]["future:scope"] = {
            "owner": "tempera-gym",
            "reportedDate": "2026-08-20",
            "status": "staged",
            "migration": "register before release",
        }
        rendered = "\n".join(
            MODULE.operation_section(surface, "temperaGym", operation)
        )
        self.assertIn("Blocked on central scope registration", rendered)

    def test_ambiguous_or_malformed_scope_authority_is_not_documented(self) -> None:
        invalid_authority = [
            {"scope": None, "scopes": ["eval:run", "dataset:write"]},
            {"scope": "eval:run", "scopes": ["eval:run", "dataset:write"]},
            {"scopes": None},
            {"scopes": []},
            {"scopes": ["eval:run", "eval:run"]},
            {"scopes": ["eval:run", "dataset:write extra"]},
        ]
        for authority in invalid_authority:
            with self.subTest(authority=authority):
                surface, operation = self.compound_surface()
                operation.pop("scope", None)
                operation.pop("scopes", None)
                operation.update(authority)
                with self.assertRaisesRegex(ValueError, "scope|scopes"):
                    MODULE.operation_section(surface, "temperaGym", operation)

        surface, operation = self.compound_surface()
        operation["scopes"].append("future:scope")
        with self.assertRaisesRegex(ValueError, "unregistered scope"):
            MODULE.operation_section(surface, "temperaGym", operation)


if __name__ == "__main__":
    unittest.main()
