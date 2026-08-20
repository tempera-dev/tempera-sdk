#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("check-mcp-protocol-source.py")
SPEC = importlib.util.spec_from_file_location("check_mcp_protocol_source", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class McpProtocolSourceCheckTest(unittest.TestCase):
    def test_committed_receipt_and_projection_are_valid(self) -> None:
        lock = MODULE.load_lock()
        MODULE.validate_lock(lock)
        MODULE.validate_sdk()

    def test_decisive_receipt_mutations_fail_closed(self) -> None:
        lock = MODULE.load_lock()
        mutations = []
        for field, replacement in [
            ("protocol_version", "2025-06-18"),
            ("source_commit", "0" * 40),
            ("source_tree", "invalid"),
            ("lifecycle", "stateful-initialize"),
            ("official_rust_sdk_repo", "example/incorrect"),
            ("official_rust_sdk_commit", "1" * 40),
            ("official_rust_sdk_tree", "2" * 40),
            ("required_headers", ["accept"]),
            ("required_meta", []),
            ("tool_result_contract", {"complete_result_type": "complete"}),
        ]:
            candidate = copy.deepcopy(lock)
            candidate[field] = replacement
            mutations.append(candidate)
        missing_file = copy.deepcopy(lock)
        missing_file["source_files"].pop("src/app.rs")
        mutations.append(missing_file)
        wrong_blob = copy.deepcopy(lock)
        wrong_blob["source_files"]["src/client.rs"]["blob"] = "0" * 40
        mutations.append(wrong_blob)
        wrong_digest = copy.deepcopy(lock)
        wrong_digest["source_files"]["Cargo.toml"]["sha256"] = "0" * 64
        mutations.append(wrong_digest)
        missing_official_file = copy.deepcopy(lock)
        missing_official_file["official_rust_sdk_source_files"].pop(
            "crates/rmcp/src/model.rs"
        )
        mutations.append(missing_official_file)

        for candidate in mutations:
            with self.subTest(candidate=candidate):
                with self.assertRaises(ValueError):
                    MODULE.validate_lock(candidate)

    def test_language_projection_mutation_fails_closed(self) -> None:
        paths = [
            Path("surface.json"),
            Path("packages/python/src/tempera_sdk/mcp.py"),
            Path("packages/typescript/src/mcp.js"),
            Path("packages/rust/src/mcp.rs"),
            Path("packages/python/src/tempera_sdk/provider.py"),
            Path("packages/python/src/tempera_sdk/provider_capabilities.py"),
            Path("packages/rust/examples/mcp_protocol_e2e.rs"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in paths:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(MODULE.ROOT / relative, target)
            MODULE.validate_sdk(root)
            python_client = root / paths[1]
            python_client.write_text(
                python_client.read_text(encoding="utf-8").replace(
                    'MCP_PROTOCOL_VERSION = "2026-07-28"',
                    'MCP_PROTOCOL_VERSION = "2025-06-18"',
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                MODULE.validate_sdk(root)


if __name__ == "__main__":
    unittest.main()
