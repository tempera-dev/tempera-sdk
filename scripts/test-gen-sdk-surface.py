#!/usr/bin/env python3
"""Regression tests for byte-preserving Rust SDK surface literals."""
from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("gen-sdk-surface.py")
SPEC = importlib.util.spec_from_file_location("gen_sdk_surface", SCRIPT)
assert SPEC and SPEC.loader
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)


class RustLiteralTest(unittest.TestCase):
    def test_literal_backslash_sequences_are_not_reinterpreted(self):
        self.assertEqual(generator.rust_literal(r"\b"), '"\\\\b"')
        self.assertEqual(generator.rust_literal(r"\f"), '"\\\\f"')
        self.assertEqual(generator.rust_literal(r"\u2019"), '"\\\\u2019"')

    def test_controls_quotes_and_unicode_have_valid_lossless_rust_escapes(self):
        self.assertEqual(generator.rust_literal("\b\f\x7f"), '"\\u{8}\\u{c}\\u{7f}"')
        self.assertEqual(generator.rust_literal('"\\\n\r\t'), '"\\"\\\\\\n\\r\\t"')
        self.assertEqual(generator.rust_literal("organization’s"), '"organization’s"')

    def test_surrogate_code_points_are_rejected_before_rust_generation(self):
        with self.assertRaisesRegex(ValueError, "surrogate"):
            generator.rust_literal("\ud800")

    def test_rustc_round_trips_literal_bytes_without_reinterpretation(self):
        for value in (r"\b", r"\f", r"\u2019", r"\backslash", "organization’s", "\b\f", "\x00", "🚀"):
            with self.subTest(value=repr(value)), tempfile.TemporaryDirectory(
                prefix="tempera-sdk-rust-literal-"
            ) as directory:
                root = Path(directory)
                source = root / "main.rs"
                binary = root / "literal"
                source.write_text(
                    "fn main() { print!(\"{}\", " + generator.rust_literal(value) + "); }\n",
                    encoding="utf-8",
                )
                subprocess.run(
                    ["rustc", "--edition", "2024", str(source), "-o", str(binary)],
                    check=True,
                    capture_output=True,
                )
                self.assertEqual(subprocess.check_output([str(binary)]), value.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
