#!/usr/bin/env python3
"""The Tempera SDK uniformity gate.

Fails when the three language packages can drift apart:

1. surface.json invariants (validated by the generator).
2. The generated surface tables (TypeScript, TypeScript .d.ts, Python, Rust)
   must byte-match a fresh render of surface.json — so nobody hand-edits a
   generated file or forgets to regenerate after changing the manifest.
3. The generated Mintlify docs site (docs/site/, rendered by
   scripts/gen-sdk-docs.py from surface.json and docs/ROLLOUT.md) must
   byte-match a fresh render — stale docs fail the gate the same way.
4. The three package versions must be identical.
5. The hand-written mirror files must each define the uniform primitives
   (TemperaApiError, the unified client, the MCP client) so a package cannot
   quietly drop part of the surface.
6. No tracked file may mention a legacy product codename; the current
   product names (palette, tempo, cradle, remi, tempOS, temp.js) are the
   only ones allowed.

Runtime conformance (every operation dispatching the right method, path, and
auth header) is asserted per-language by each package's own test suite, which
loops over the generated tables; `npm test` at the repo root runs all of it.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Hand-written files must keep exposing the uniform primitives by these names.
REQUIRED_MARKERS = {
    "packages/typescript/src/errors.js": ["class TemperaApiError", "class TemperaMcpError", "normalizeErrorBody"],
    "packages/typescript/src/client.js": ["export function createTemperaClient"],
    "packages/typescript/src/mcp.js": ["class TemperaMcpClient", "MCP_PROTOCOL_VERSION"],
    "packages/typescript/src/auth.js": ["class TemperaAuth", "createPkcePair", "pkceChallengeS256"],
    "packages/python/src/tempera_sdk/errors.py": ["class TemperaApiError", "class TemperaMcpError", "def normalize_error_body"],
    "packages/python/src/tempera_sdk/client.py": ["class TemperaClient"],
    "packages/python/src/tempera_sdk/mcp.py": ["class TemperaMcpClient", "MCP_PROTOCOL_VERSION"],
    "packages/python/src/tempera_sdk/auth.py": ["class TemperaAuth", "def create_pkce_pair", "def pkce_challenge_s256"],
    "packages/rust/src/error.rs": ["pub struct TemperaApiError", "pub fn normalize_error_body"],
    "packages/rust/src/client.rs": ["pub struct TemperaClient", "pub struct RequestSpec"],
    "packages/rust/src/mcp.rs": ["MCP_PROTOCOL_VERSION"],
    "packages/rust/src/auth.rs": ["pub struct TemperaAuth", "pub fn pkce_challenge_s256"],
}


def package_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    ts = json.loads((ROOT / "packages/typescript/package.json").read_text())
    versions["typescript"] = ts["version"]
    py = (ROOT / "packages/python/pyproject.toml").read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', py, re.MULTILINE)
    versions["python"] = match.group(1) if match else "?"
    cargo = (ROOT / "packages/rust/Cargo.toml").read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', cargo, re.MULTILINE)
    versions["rust"] = match.group(1) if match else "?"
    return versions


def main() -> int:
    failures: list[str] = []

    # 1 + 2: manifest invariants and generated-table drift.
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/gen-sdk-surface.py"), "--check"],
        capture_output=True,
        text=True,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode != 0:
        failures.append("generated surface tables are stale or surface.json is invalid")

    # 3: generated docs-site drift (same regenerate-and-diff pattern).
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/gen-sdk-docs.py"), "--check"],
        capture_output=True,
        text=True,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode != 0:
        failures.append(
            "generated docs site (docs/site/) is stale (run python3 scripts/gen-sdk-docs.py)"
        )

    # 4: one SDK version across the three packages.
    versions = package_versions()
    if len(set(versions.values())) != 1:
        failures.append(f"package versions differ: {versions}")

    # 5: uniform primitives present in every hand-written mirror file.
    for rel_path, markers in REQUIRED_MARKERS.items():
        path = ROOT / rel_path
        if not path.exists():
            failures.append(f"missing file: {rel_path}")
            continue
        text = path.read_text()
        for marker in markers:
            if marker not in text:
                failures.append(f"{rel_path}: missing marker {marker!r}")

    # 6: no legacy product codenames in any tracked file. The products are
    # palette, tempo, cradle, remi, tempOS, and temp.js — their pre-rename
    # codenames must not resurface in code, docs, or the manifest.
    legacy = re.compile(r"beater|beatbox", re.IGNORECASE)
    tracked = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, cwd=ROOT
    ).stdout.splitlines()
    for tracked_path in tracked:
        if tracked_path == "scripts/check-sdk-surface.py":
            continue  # this file necessarily spells the denied pattern
        path = ROOT / tracked_path
        try:
            text = path.read_text()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            if legacy.search(line):
                failures.append(
                    f"{tracked_path}:{line_number}: legacy product codename; use the current product names"
                )

    if failures:
        for failure in failures:
            print(f"SDK surface check failed: {failure}", file=sys.stderr)
        return 1
    print(f"SDK surface check passed (version {versions['typescript']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
