#!/usr/bin/env python3
"""Fail closed when the five public SDK packages drift from one contract."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_LANGUAGES = ["typescript", "python", "rust", "go", "c"]


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> int:
    surface = json.loads((ROOT / "surface.json").read_text(encoding="utf-8"))
    sdk = tomllib.loads((ROOT / "sdk.toml").read_text(encoding="utf-8"))
    if sdk.get("sdk", {}).get("languages") != EXPECTED_LANGUAGES:
        fail(f"sdk.toml languages must be exactly {EXPECTED_LANGUAGES!r}")

    ts = json.loads((ROOT / "packages/typescript/package.json").read_text(encoding="utf-8"))["version"]
    py = tomllib.loads((ROOT / "packages/python/pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    rust = tomllib.loads((ROOT / "packages/rust/Cargo.toml").read_text(encoding="utf-8"))["package"]["version"]
    go_text = (ROOT / "packages/go/client.go").read_text(encoding="utf-8")
    c_text = (ROOT / "packages/c/include/tempera/surface_gen.h").read_text(encoding="utf-8")
    go_match = re.search(r'const Version = "([^"]+)"', go_text)
    c_match = re.search(r'#define TEMPERA_SDK_VERSION "([^"]+)"', c_text)
    if not go_match or not c_match:
        fail("Go or C package version marker is missing")
    versions = {"typescript": ts, "python": py, "rust": rust, "go": go_match.group(1), "c": c_match.group(1)}
    if len(set(versions.values())) != 1:
        fail(f"five-language package versions diverged: {versions}")

    required = {
        "typescript": ROOT / "packages/typescript/src/browser.js",
        "python": ROOT / "packages/python/src/tempera_sdk/browser.py",
        "rust": ROOT / "packages/rust/src/browser.rs",
        "go": ROOT / "packages/go/browser.go",
        "c": ROOT / "packages/c/include/tempera/tempera.h",
    }
    for language, path in required.items():
        if not path.exists() or "BrowserTask" not in path.read_text(encoding="utf-8") and "browser_task" not in path.read_text(encoding="utf-8"):
            fail(f"{language} BrowserTask surface is missing")

    for product, operations in surface["operations"].items():
        seen: set[str] = set()
        for op in operations:
            operation_id = op["id"]
            if operation_id in seen:
                fail(f"duplicate operation id: {product}.{operation_id}")
            seen.add(operation_id)
            description = op.get("description", "")
            if not isinstance(description, str) or not description.strip() or "\n" in description:
                fail(f"{product}.{operation_id} description must be a non-empty one-line sentence")
            if description[-1] not in ".!?)`'\"":
                fail(f"{product}.{operation_id} description must end with punctuation")
            if op.get("method") not in {"GET", "POST", "PATCH", "DELETE"}:
                fail(f"{product}.{operation_id} uses unsupported HTTP method {op.get('method')!r}")
            path = op.get("path", "")
            if not path.startswith("/"):
                fail(f"{product}.{operation_id} path must be absolute")

    subprocess.run([sys.executable, "scripts/gen-sdk-go-c.py", "--check"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/check-aip-conformance.py"], cwd=ROOT, check=True)
    print(f"five-language SDK uniformity passed at version {ts}; surface v{surface['version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
