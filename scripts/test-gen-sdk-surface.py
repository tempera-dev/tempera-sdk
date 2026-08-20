#!/usr/bin/env python3
"""Fail-closed tests for generated singular and compound scope metadata."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "gen_sdk_surface", ROOT / "scripts" / "gen-sdk-surface.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load gen-sdk-surface.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CompoundScopeGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.surface = json.loads((ROOT / "surface.json").read_text())

    @staticmethod
    def export_operation(surface: dict) -> dict:
        return next(
            operation
            for operation in surface["operations"]["temperaGym"]
            if operation["id"] == "exportEpisode"
        )

    def compound_surface(self) -> dict:
        surface = copy.deepcopy(self.surface)
        operation = self.export_operation(surface)
        operation.pop("scope", None)
        operation["scopes"] = ["eval:run", "dataset:write"]
        return surface

    def test_current_and_compound_surfaces_are_valid(self) -> None:
        self.assertEqual(MODULE.validate(self.surface), [])
        self.assertEqual(MODULE.validate(self.compound_surface()), [])

    def test_ambiguous_or_malformed_canonical_sets_fail_closed(self) -> None:
        invalid_scopes = [
            None,
            "eval:run dataset:write",
            [],
            ["eval:run", "eval:run"],
            ["eval:run", "dataset:write extra"],
            ["eval:run", "dataset:\\write"],
            ["eval:run", "dataset:\"write"],
            ["eval:run", "dataset:write-🧪"],
            ["scope:x" for _ in range(65)],
            ["x" * 257],
        ]
        for scopes in invalid_scopes:
            with self.subTest(scopes=scopes):
                surface = self.compound_surface()
                self.export_operation(surface)["scopes"] = scopes
                self.assertTrue(MODULE.validate(surface))

        for singular in (None, "eval:run"):
            with self.subTest(singular=singular):
                surface = self.compound_surface()
                self.export_operation(surface)["scope"] = singular
                self.assertTrue(
                    any("mutually exclusive" in item for item in MODULE.validate(surface))
                )

        invalid_singular = [
            "",
            ["eval:run"],
            " eval:run",
            "eval:run extra",
            "eval:\\run",
            "eval:\"run",
            "eval:run-🧪",
            "x" * 257,
        ]
        for scope in invalid_singular:
            with self.subTest(scope=scope):
                surface = copy.deepcopy(self.surface)
                self.export_operation(surface)["scope"] = scope
                self.assertTrue(MODULE.validate(surface))

    def test_unknown_member_requires_an_explicit_registry_gap(self) -> None:
        surface = self.compound_surface()
        self.export_operation(surface)["scopes"].append("future:scope")
        self.assertTrue(
            any("unregistered scope 'future:scope'" in item for item in MODULE.validate(surface))
        )

        surface["scopeGaps"]["future:scope"] = {
            "owner": "tempera-gym",
            "reportedDate": "2026-08-20",
            "status": "staged",
            "migration": "register before release",
        }
        self.assertEqual(MODULE.validate(surface), [])

    def test_public_operation_cannot_require_any_scope(self) -> None:
        surface = self.compound_surface()
        operation = self.export_operation(surface)
        operation["auth"] = "none"
        operation.pop("authAudience", None)
        self.assertIn(
            "temperaGym.exportEpisode: public operation cannot require scopes",
            MODULE.validate(surface),
        )

    def test_language_renderers_preserve_exact_order_and_exclusivity(self) -> None:
        surface = self.compound_surface()

        typescript = MODULE.render_typescript(surface)
        ts_start = typescript.index('"id": "exportEpisode"')
        ts_end = typescript.find('\n    {', ts_start + 1)
        ts_operation = typescript[ts_start : ts_end if ts_end >= 0 else None]
        self.assertNotIn('"scope":', ts_operation)
        self.assertIn(
            '"scopes": [\n        "eval:run",\n        "dataset:write"\n      ]',
            ts_operation,
        )

        python = MODULE.render_python(surface)
        py_start = python.index('"id": "export_episode"')
        py_end = python.find('\n        {', py_start + 1)
        py_operation = python[py_start : py_end if py_end >= 0 else None]
        self.assertNotIn('"scope":', py_operation)
        self.assertIn(
            '"scopes": [\n                "eval:run",\n                "dataset:write"\n            ]',
            py_operation,
        )

        rust = MODULE.render_rust(surface)
        rust_start = rust.index('id: "export_episode"')
        rust_end = rust.find("\n    OperationSpec {", rust_start + 1)
        rust_operation = rust[rust_start : rust_end if rust_end >= 0 else None]
        self.assertIn("scope: None,", rust_operation)
        self.assertIn(
            'scopes: Some(&["eval:run", "dataset:write"]),',
            rust_operation,
        )
        self.assertIn("pub const fn scope(&self)", rust)
        self.assertIn("pub const fn scopes(&self)", rust)
        self.assertIn("pub(crate) scope: Option", rust)
        self.assertIn("pub(crate) scopes: Option", rust)
        self.assertNotIn("    pub scope: Option", rust)
        self.assertNotIn("    pub scopes: Option", rust)

        declarations = MODULE.render_typescript_dts(surface)
        self.assertIn("export type TemperaOperationScopeAuthority =", declarations)
        self.assertIn("scopes?: never", declarations)
        self.assertIn(
            "scopes: readonly [TemperaScope, ...TemperaScope[]]", declarations
        )

    def test_representative_singular_scope_remains_singular(self) -> None:
        operation = self.export_operation(self.surface)
        self.assertEqual(
            MODULE.rendered_scope_fields(operation), {"scope": "eval:run"}
        )

    def test_package_and_default_client_versions_move_together(self) -> None:
        version = json.loads(
            (ROOT / "packages" / "typescript" / "package.json").read_text()
        )["version"]
        self.assertEqual(version, "0.13.0")

        expected_toml = f'version = "{version}"'
        for path in (
            ROOT / "packages" / "python" / "pyproject.toml",
            ROOT / "packages" / "python" / "uv.lock",
            ROOT / "packages" / "rust" / "Cargo.toml",
            ROOT / "packages" / "rust" / "Cargo.lock",
        ):
            with self.subTest(path=path):
                self.assertIn(expected_toml, path.read_text())

        self.assertIn(
            f'version: str = "{version}"',
            (ROOT / "packages" / "python" / "src" / "tempera_sdk" / "mcp.py").read_text(),
        )
        self.assertIn(
            f'version = "{version}"',
            (ROOT / "packages" / "typescript" / "src" / "mcp.js").read_text(),
        )
        self.assertIn(
            f'initialize_body("tempera-sdk", "{version}")',
            (ROOT / "packages" / "rust" / "src" / "mcp.rs").read_text(),
        )

    def test_synthetic_rust_compound_accessors_compile_and_preserve_order(self) -> None:
        rendered = MODULE.render_rust(self.compound_surface())
        rendered += """

#[cfg(test)]
mod compound_scope_accessor_regression {
    use super::*;

    #[test]
    fn compound_scope_is_exclusive_and_ordered() {
        let operation = find_operation("tempera_gym", "export_episode").unwrap();
        assert_eq!(operation.scope(), None);
        assert_eq!(operation.scopes(), Some(&["eval:run", "dataset:write"][..]));
    }
}
"""
        with tempfile.TemporaryDirectory(prefix="tempera-sdk-compound-rust-") as directory:
            source = Path(directory) / "surface.rs"
            binary = Path(directory) / "surface-test"
            source.write_text(rendered)
            subprocess.run(
                [
                    "rustc",
                    "--edition=2024",
                    "--test",
                    str(source),
                    "-o",
                    str(binary),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [str(binary), "--exact", "compound_scope_accessor_regression::compound_scope_is_exclusive_and_ordered"],
                check=True,
                capture_output=True,
                text=True,
            )


if __name__ == "__main__":
    unittest.main()
