#!/usr/bin/env python3
"""Regression tests for byte-preserving Rust SDK surface literals."""
from __future__ import annotations

import importlib.util
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


if __name__ == "__main__":
    unittest.main()
