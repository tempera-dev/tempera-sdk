#!/usr/bin/env python3
"""Regression tests for byte-preserving Swift and Kotlin SDK surface literals.

`scripts/test-gen-sdk-surface.py` covers the Rust literal escaper, which once
round-tripped `\\u2019` back into a smart quote. Swift and Kotlin have their own
ways to lose bytes:

- Kotlin reads `$` as the start of a string template, so `${issuer}` in the MCP
  gateway description is a compile error (or a silent substitution) unless the
  renderer escapes it.
- Kotlin has no `\\f` escape and no astral escape; its `\\uXXXX` is a single
  UTF-16 code unit.
- Swift's `\\u{...}` takes a Unicode scalar, so a surrogate pair from
  `json.dumps` is two invalid scalars rather than one emoji.

Each escaper is checked three ways: against fixed expectations, against a
reference unescaper implementing that language's lexer rules, and -- when the
toolchain is installed -- by compiling and running a program that prints the
literal back.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from renderers import kotlin as kotlin_renderer  # noqa: E402
from renderers import swift as swift_renderer  # noqa: E402

#: Byte sequences that have historically been mangled by one generator or another.
ROUND_TRIP_VALUES = (
    r"\b",
    r"\f",
    r"\u2019",
    r"\backslash",
    "organization’s",
    "\b\f",
    "\x00",
    "\U0001F680",
    "${issuer}",
    "$audience",
    'quote " inside',
    "tab\there",
    "line\nbreak",
    "delete\x7f",
)


def swift_unescape(literal: str) -> str:
    """Reference Swift string-literal reader (single-line literals only)."""
    assert literal.startswith('"') and literal.endswith('"'), literal
    body = literal[1:-1]
    simple = {"0": "\0", "\\": "\\", "t": "\t", "n": "\n", "r": "\r", '"': '"', "'": "'"}
    out: list[str] = []
    index = 0
    while index < len(body):
        character = body[index]
        if character == "\\":
            following = body[index + 1]
            if following == "u":
                assert body[index + 2] == "{", literal
                end = body.index("}", index + 3)
                out.append(chr(int(body[index + 3 : end], 16)))
                index = end + 1
                continue
            assert following in simple, f"invalid Swift escape \\{following}"
            out.append(simple[following])
            index += 2
            continue
        assert character != '"', "unescaped quote closes the literal"
        assert character not in "\n\r", "raw newline is not allowed in a Swift literal"
        out.append(character)
        index += 1
    return "".join(out)


def kotlin_unescape(literal: str) -> str:
    """Reference Kotlin string-literal reader (escaped, non-raw literals only)."""
    assert literal.startswith('"') and literal.endswith('"'), literal
    body = literal[1:-1]
    # Kotlin's complete escape set: no \f, no \xNN, no \0.
    simple = {"t": "\t", "b": "\b", "n": "\n", "r": "\r", "'": "'", '"': '"', "\\": "\\", "$": "$"}
    out: list[str] = []
    index = 0
    while index < len(body):
        character = body[index]
        if character == "\\":
            following = body[index + 1]
            if following == "u":
                out.append(chr(int(body[index + 2 : index + 6], 16)))
                index += 6
                continue
            assert following in simple, f"invalid Kotlin escape \\{following}"
            out.append(simple[following])
            index += 2
            continue
        assert character != "$", "unescaped $ starts a string template"
        assert character != '"', "unescaped quote closes the literal"
        assert character not in "\n\r", "raw newline is not allowed in a Kotlin literal"
        out.append(character)
        index += 1
    return "".join(out)


class SwiftLiteralTest(unittest.TestCase):
    def test_literal_backslash_sequences_are_not_reinterpreted(self):
        self.assertEqual(swift_renderer.swift_literal(r"\b"), '"\\\\b"')
        self.assertEqual(swift_renderer.swift_literal(r"\f"), '"\\\\f"')
        self.assertEqual(swift_renderer.swift_literal(r"\u2019"), '"\\\\u2019"')

    def test_controls_quotes_and_unicode_have_valid_lossless_swift_escapes(self):
        self.assertEqual(swift_renderer.swift_literal("\b\f\x7f"), '"\\u{8}\\u{c}\\u{7f}"')
        self.assertEqual(swift_renderer.swift_literal('"\\\n\r\t'), '"\\"\\\\\\n\\r\\t"')
        self.assertEqual(
            swift_renderer.swift_literal("organization’s"), '"organization’s"'
        )

    def test_dollar_and_astral_characters_stay_verbatim(self):
        # Swift has no string templates, and an astral scalar is one scalar.
        self.assertEqual(swift_renderer.swift_literal("${issuer}"), '"${issuer}"')
        self.assertEqual(swift_renderer.swift_literal("\U0001F680"), '"\U0001F680"')

    def test_surrogate_code_points_are_rejected_before_swift_generation(self):
        with self.assertRaisesRegex(ValueError, "surrogate"):
            swift_renderer.swift_literal("\ud800")

    def test_reference_reader_round_trips_every_value(self):
        for value in ROUND_TRIP_VALUES:
            with self.subTest(value=repr(value)):
                self.assertEqual(swift_unescape(swift_renderer.swift_literal(value)), value)

    @unittest.skipUnless(shutil.which("swiftc"), "swiftc is not installed")
    def test_swiftc_round_trips_literal_bytes_without_reinterpretation(self):
        for value in ROUND_TRIP_VALUES:
            with self.subTest(value=repr(value)), tempfile.TemporaryDirectory(
                prefix="tempera-sdk-swift-literal-"
            ) as directory:
                root = Path(directory)
                source = root / "main.swift"
                binary = root / "literal"
                source.write_text(
                    "print(" + swift_renderer.swift_literal(value) + ', terminator: "")\n',
                    encoding="utf-8",
                )
                subprocess.run(
                    ["swiftc", "-swift-version", "6", str(source), "-o", str(binary)],
                    check=True,
                    capture_output=True,
                )
                self.assertEqual(subprocess.check_output([str(binary)]), value.encode("utf-8"))


class KotlinLiteralTest(unittest.TestCase):
    def test_literal_backslash_sequences_are_not_reinterpreted(self):
        self.assertEqual(kotlin_renderer.kotlin_literal(r"\b"), '"\\\\b"')
        self.assertEqual(kotlin_renderer.kotlin_literal(r"\f"), '"\\\\f"')
        self.assertEqual(kotlin_renderer.kotlin_literal(r"\u2019"), '"\\\\u2019"')

    def test_dollar_is_escaped_so_templates_never_expand(self):
        self.assertEqual(kotlin_renderer.kotlin_literal("${issuer}"), '"\\${issuer}"')
        self.assertEqual(kotlin_renderer.kotlin_literal("$audience"), '"\\$audience"')

    def test_controls_use_four_digit_unicode_escapes(self):
        # Kotlin has no \f, no \xNN and no \0: every control uses \uXXXX.
        self.assertEqual(
            kotlin_renderer.kotlin_literal("\b\f\x7f\x00"), '"\\u0008\\u000c\\u007f\\u0000"'
        )
        self.assertEqual(kotlin_renderer.kotlin_literal('"\\\n\r\t'), '"\\"\\\\\\n\\r\\t"')

    def test_astral_characters_stay_verbatim(self):
        self.assertEqual(kotlin_renderer.kotlin_literal("\U0001F680"), '"\U0001F680"')

    def test_surrogate_code_points_are_rejected_before_kotlin_generation(self):
        with self.assertRaisesRegex(ValueError, "surrogate"):
            kotlin_renderer.kotlin_literal("\udc00")

    def test_reference_reader_round_trips_every_value(self):
        for value in ROUND_TRIP_VALUES:
            with self.subTest(value=repr(value)):
                self.assertEqual(kotlin_unescape(kotlin_renderer.kotlin_literal(value)), value)

    @unittest.skipUnless(shutil.which("kotlinc"), "kotlinc is not installed")
    def test_kotlinc_round_trips_literal_bytes_without_reinterpretation(self):
        with tempfile.TemporaryDirectory(prefix="tempera-sdk-kotlin-literal-") as directory:
            root = Path(directory)
            source = root / "main.kt"
            # One program per run: kotlinc start-up dominates its runtime.
            body = "\n".join(
                "print(" + kotlin_renderer.kotlin_literal(value) + ")"
                for value in ROUND_TRIP_VALUES
            )
            source.write_text(f"fun main() {{\n{body}\n}}\n", encoding="utf-8")
            jar = root / "literal.jar"
            subprocess.run(
                ["kotlinc", str(source), "-include-runtime", "-d", str(jar)],
                check=True,
                capture_output=True,
            )
            output = subprocess.check_output(["java", "-jar", str(jar)])
            self.assertEqual(output, "".join(ROUND_TRIP_VALUES).encode("utf-8"))


class GeneratedSurfaceTest(unittest.TestCase):
    """The emitted files themselves, checked without a Swift or JVM toolchain."""

    SWIFT = ROOT / "packages/swift/Sources/TemperaSDK/Surface.swift"
    KOTLIN = ROOT / "packages/kotlin/src/main/kotlin/dev/tempera/sdk/Surface.kt"

    def test_both_files_start_with_the_do_not_edit_marker(self):
        for path in (self.SWIFT, self.KOTLIN):
            with self.subTest(path=path.name):
                self.assertTrue(
                    path.read_text(encoding="utf-8").startswith(f"// {swift_renderer.HEADER}"),
                    f"{path} lost the generated-file marker",
                )

    def test_kotlin_never_emits_an_unescaped_dollar(self):
        source = self.KOTLIN.read_text(encoding="utf-8")
        for match in re.finditer(r"\$", source):
            self.assertEqual(
                source[match.start() - 1],
                "\\",
                f"unescaped $ at offset {match.start()} would start a Kotlin template",
            )
        # The one real occurrence is the MCP gateway description.
        self.assertIn("\\${issuer}", source)

    def test_every_operation_reaches_both_generated_tables(self):
        surface = json.loads((ROOT / "surface.json").read_text(encoding="utf-8"))
        expected = sum(len(ops) for ops in surface["operations"].values())
        # Swift spells the type as `struct TemperaOperationSpec:`, Kotlin as
        # `data class TemperaOperationSpec(`, so only Kotlin's declaration also
        # matches the constructor-call needle.
        for path, declarations in ((self.SWIFT, 0), (self.KOTLIN, 1)):
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertEqual(
                    source.count("TemperaOperationSpec("), expected + declarations
                )

    def test_mcp_protocol_version_matches_the_hand_written_runtimes(self):
        rust = (ROOT / "packages/rust/src/mcp.rs").read_text(encoding="utf-8")
        python = (ROOT / "packages/python/src/tempera_sdk/mcp.py").read_text(encoding="utf-8")
        rust_version = re.search(r'MCP_PROTOCOL_VERSION: &str = "([^"]+)"', rust).group(1)
        python_version = re.search(r'MCP_PROTOCOL_VERSION = "([^"]+)"', python).group(1)
        self.assertEqual(swift_renderer.MCP_PROTOCOL_VERSION, rust_version)
        self.assertEqual(kotlin_renderer.MCP_PROTOCOL_VERSION, rust_version)
        self.assertEqual(python_version, rust_version)


if __name__ == "__main__":
    unittest.main()
