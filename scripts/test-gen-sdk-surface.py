#!/usr/bin/env python3
"""Regression tests for byte-preserving SDK surface literals (Rust, C, C++)."""
from __future__ import annotations

import importlib
import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("gen-sdk-surface.py")
SPEC = importlib.util.spec_from_file_location("gen_sdk_surface", SCRIPT)
assert SPEC and SPEC.loader
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)

c_renderer = importlib.import_module("renderers.c")
cpp_renderer = importlib.import_module("renderers.cpp")

CC = os.environ.get("CC") or shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
CXX = (
    os.environ.get("CXX")
    or shutil.which("c++")
    or shutil.which("g++")
    or shutil.which("clang++")
)

# Values that have broken one generator or another: literal backslash escape
# sequences that must not be reinterpreted, a curly apostrophe, C0 controls, a
# non-BMP emoji, a hex digit right after an escaped byte (\x is greedy in C),
# and every trigraph prefix.
ROUND_TRIP_VALUES = (
    r"\b",
    r"\f",
    r"\u2019",
    r"\backslash",
    "organization’s",
    "\b\f",
    "\U0001f680",
    "\U0001f680" + "7abcdef",
    "’e",
    "??=??/??'??(??)??!??<??>??-",
    "quote\" and \\ and\ttab\nnewline",
    "\x7f\x01",
)


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


class CLiteralTest(unittest.TestCase):
    def test_literal_backslash_sequences_are_not_reinterpreted(self):
        self.assertEqual(c_renderer.c_literal(r"\b"), '"\\\\b"')
        self.assertEqual(c_renderer.c_literal(r"\u2019"), '"\\\\u2019"')

    def test_controls_and_quotes_use_c_escapes(self):
        self.assertEqual(c_renderer.c_literal("\b\f\x7f"), '"\\x08\\x0c\\x7f"')
        self.assertEqual(c_renderer.c_literal('"\\\n\r\t'), '"\\"\\\\\\n\\r\\t"')

    def test_non_ascii_becomes_utf8_byte_escapes_not_universal_character_names(self):
        # C99 has no portable \uXXXX inside an ordinary string literal, and a
        # non-BMP code point has no \u spelling at all: emit the UTF-8 bytes.
        self.assertEqual(c_renderer.c_literal("’"), '"\\xe2\\x80\\x99"')
        self.assertEqual(c_renderer.c_literal("🚀"), '"\\xf0\\x9f\\x9a\\x80"')
        self.assertNotIn("\\u", c_renderer.c_literal("🚀"))

    def test_hex_escape_is_split_before_a_literal_hex_digit(self):
        # \x is greedy in C: "\xf0\x9f\x9a\x807" would parse as one escape.
        self.assertEqual(
            c_renderer.c_literal("🚀7"), '"\\xf0\\x9f\\x9a\\x80" "7"'
        )
        self.assertEqual(c_renderer.c_literal("🚀g"), '"\\xf0\\x9f\\x9a\\x80g"')

    def test_every_question_mark_is_escaped_so_no_trigraph_can_form(self):
        self.assertEqual(c_renderer.c_literal("??="), '"\\?\\?="')
        self.assertEqual(c_renderer.c_literal("a?b"), '"a\\?b"')

    def test_nul_and_surrogates_are_rejected_before_c_generation(self):
        with self.assertRaisesRegex(ValueError, "NUL"):
            c_renderer.c_literal("a\x00b")
        with self.assertRaisesRegex(ValueError, "surrogate"):
            c_renderer.c_literal("\ud800")

    def test_generated_c_sources_are_pure_ascii(self):
        for path in ("packages/c/include/tempera/surface.h", "packages/c/src/surface.c"):
            with self.subTest(path=path):
                data = (SCRIPT.resolve().parents[1] / path).read_bytes()
                self.assertTrue(all(byte < 0x80 for byte in data))

    @unittest.skipUnless(CC, "no C compiler available")
    def test_cc_round_trips_literal_bytes_without_reinterpretation(self):
        for value in ROUND_TRIP_VALUES:
            with self.subTest(value=repr(value)), tempfile.TemporaryDirectory(
                prefix="tempera-sdk-c-literal-"
            ) as directory:
                root = Path(directory)
                source = root / "main.c"
                binary = root / "literal"
                source.write_text(
                    "#include <stdio.h>\n"
                    "int main(void) {\n"
                    "    static const char *const value = "
                    + c_renderer.c_literal(value)
                    + ";\n"
                    "    fputs(value, stdout);\n"
                    "    return 0;\n"
                    "}\n",
                    encoding="ascii",
                )
                subprocess.run(
                    [
                        CC,
                        "-std=c99",
                        "-Wall",
                        "-Wextra",
                        "-Werror",
                        "-pedantic",
                        # Trigraphs are OFF by default in gcc/clang; turn them
                        # ON so the escaping proves itself against a conforming
                        # C99 translation phase 1.
                        "-trigraphs",
                        str(source),
                        "-o",
                        str(binary),
                    ],
                    check=True,
                    capture_output=True,
                )
                self.assertEqual(
                    subprocess.check_output([str(binary)]), value.encode("utf-8")
                )


class CppLiteralTest(unittest.TestCase):
    def test_cpp_literals_reuse_the_c_escaping_rules(self):
        for value in ROUND_TRIP_VALUES:
            self.assertEqual(
                cpp_renderer.cpp_literal(value), c_renderer.c_literal(value)
            )

    def test_optional_members_render_as_nullopt(self):
        self.assertEqual(cpp_renderer.cpp_optional_literal(None), "std::nullopt")
        self.assertEqual(cpp_renderer.cpp_optional_literal("palette"), '"palette"')

    def test_generated_cpp_header_is_pure_ascii(self):
        data = (
            SCRIPT.resolve().parents[1] / "packages/cpp/include/tempera/surface.hpp"
        ).read_bytes()
        self.assertTrue(all(byte < 0x80 for byte in data))

    @unittest.skipUnless(CXX, "no C++ compiler available")
    def test_cxx_round_trips_literal_bytes_through_string_view(self):
        for value in ROUND_TRIP_VALUES:
            with self.subTest(value=repr(value)), tempfile.TemporaryDirectory(
                prefix="tempera-sdk-cpp-literal-"
            ) as directory:
                root = Path(directory)
                source = root / "main.cpp"
                binary = root / "literal"
                source.write_text(
                    "#include <cstdio>\n"
                    "#include <string_view>\n"
                    "int main() {\n"
                    "    constexpr std::string_view value = "
                    + cpp_renderer.cpp_literal(value)
                    + ";\n"
                    "    std::fwrite(value.data(), 1, value.size(), stdout);\n"
                    "    return 0;\n"
                    "}\n",
                    encoding="ascii",
                )
                subprocess.run(
                    [
                        CXX,
                        "-std=c++20",
                        "-Wall",
                        "-Wextra",
                        "-Werror",
                        "-pedantic",
                        str(source),
                        "-o",
                        str(binary),
                    ],
                    check=True,
                    capture_output=True,
                )
                self.assertEqual(
                    subprocess.check_output([str(binary)]), value.encode("utf-8")
                )


class RendererRegistryTest(unittest.TestCase):
    def test_plugin_renderers_are_registered_with_the_generator(self):
        for path in (
            "packages/c/include/tempera/surface.h",
            "packages/c/src/surface.c",
            "packages/cpp/include/tempera/surface.hpp",
        ):
            self.assertIn(path, generator.TARGETS)

    def test_builtin_targets_survive_the_plugin_merge(self):
        for path in (
            "packages/typescript/src/surface.js",
            "packages/typescript/src/surface.d.ts",
            "packages/python/src/tempera_sdk/surface.py",
            "packages/rust/src/surface.rs",
        ):
            self.assertIn(path, generator.TARGETS)


if __name__ == "__main__":
    unittest.main()
