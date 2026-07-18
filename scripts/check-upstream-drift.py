#!/usr/bin/env python3
"""Upstream-spec drift gate for the Tempera SDK aggregate.

`surface.json` is the hand-maintained SDK surface, but the ecosystem style
guide (§2, "tempera-sdk is a generated aggregate, not a hand-written
inventory") requires that every operation the aggregate declares for a product
actually exists in that product's *real*, committed OpenAPI spec. This gate
establishes that direction: it reads the vendored upstream specs under
`specs/` and asserts, for every product whose spec is available in-repo, that
each surface operation matches an upstream (method, path) pair.

Path parameter *names* differ across the ecosystem (control-plane serves
`/api-keys/{id}`, the surface calls it `{api_key_id}`; the style guide even
calls this out), so paths are compared structurally: every `{param}` segment
is normalized to a single `{}` placeholder. Method + normalized path is the
identity we compare on.

Two enforcement tiers:

* STRICT products (see `STRICT_PRODUCTS`) must match their upstream spec
  *exactly*. Any surface operation without a matching upstream (method, path)
  fails the gate (exit 1). These products are new and authoritative, so they
  are held to the generated-aggregate standard from day one.
* WARN products (`palette`, `controlPlane`, `cradle`) are existing, still
  hand-maintained clients. Mismatches are *reported* as warnings — valuable
  signal for the migration to a fully generated surface — but do not fail the
  gate yet.

Vendored specs live in `specs/` (each with a `.source` note recording its
origin path) so this check is reproducible in-repo without checking out every
service. Refresh them by re-copying the upstream committed specs.

Usage:
  python3 scripts/check-upstream-drift.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "surface.json"
SPECS_DIR = ROOT / "specs"

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}

# surface product key -> vendored spec filename under specs/.
VENDORED_SPECS = {
    "temperaLlm": "tempera-llm-api.json",
    "temperaWorkflows": "tempera-workflows-api.json",
    "temperaGym": "tempera-gym-api.json",
    "palette": "palette-api.json",
    "controlPlane": "control-plane.openapi.json",
    "cradle": "cradle-openapi.json",
}

# Products held to an exact match (new + authoritative). Everything else with a
# vendored spec is reported as a warning while the surface is still migrating.
STRICT_PRODUCTS = {"temperaLlm", "temperaWorkflows", "temperaGym"}

PARAM_RE = re.compile(r"\{[^}]+\}")


def normalize_path(path: str) -> str:
    """Collapse every `{param}` segment to `{}` so param *names* don't matter."""
    return PARAM_RE.sub("{}", path)


def upstream_index(spec: dict) -> set[tuple[str, str]]:
    """Return the set of (METHOD, normalized-path) pairs an OpenAPI spec serves."""
    pairs: set[tuple[str, str]] = set()
    for path, item in (spec.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for method, operation in item.items():
            if method.lower() in HTTP_METHODS and isinstance(operation, dict):
                pairs.add((method.upper(), normalize_path(path)))
    return pairs


def main() -> int:
    surface = json.loads(SURFACE.read_text())
    operations = surface.get("operations", {})

    strict_failures: list[str] = []
    warnings: list[str] = []
    summary_rows: list[tuple[str, str, int, int, int]] = []

    for product_key, spec_file in VENDORED_SPECS.items():
        spec_path = SPECS_DIR / spec_file
        tier = "STRICT" if product_key in STRICT_PRODUCTS else "warn"

        if not spec_path.exists():
            message = (
                f"{product_key}: vendored spec {spec_file} is missing from specs/ "
                f"(copy it from its upstream repo)"
            )
            if product_key in STRICT_PRODUCTS:
                strict_failures.append(message)
            else:
                warnings.append(message)
            summary_rows.append((product_key, tier, 0, 0, 0))
            continue

        try:
            spec = json.loads(spec_path.read_text())
        except json.JSONDecodeError as error:
            message = f"{product_key}: vendored spec {spec_file} is not valid JSON: {error}"
            if product_key in STRICT_PRODUCTS:
                strict_failures.append(message)
            else:
                warnings.append(message)
            summary_rows.append((product_key, tier, 0, 0, 0))
            continue

        upstream = upstream_index(spec)
        ops = operations.get(product_key, [])
        mismatches: list[str] = []
        for op in ops:
            key = (op["method"], normalize_path(op["path"]))
            if key not in upstream:
                mismatches.append(
                    f"{product_key}.{op['id']}: {op['method']} {op['path']} "
                    f"(normalized {normalize_path(op['path'])}) not found in {spec_file}"
                )

        matched = len(ops) - len(mismatches)
        summary_rows.append((product_key, tier, len(ops), matched, len(mismatches)))

        for mismatch in mismatches:
            if product_key in STRICT_PRODUCTS:
                strict_failures.append(mismatch)
            else:
                warnings.append(mismatch)

    # Surface products that declare operations but have no vendored spec are
    # simply out of scope for this gate (no upstream available locally); note
    # them so the coverage is explicit.
    uncovered = [
        key
        for key, ops in operations.items()
        if ops and key not in VENDORED_SPECS
    ]

    print("Upstream-spec drift gate")
    print("=" * 72)
    print(f"{'product':<14} {'tier':<7} {'surface ops':>11} {'matched':>8} {'mismatch':>9}")
    print("-" * 72)
    for product_key, tier, total, matched, missing in summary_rows:
        print(f"{product_key:<14} {tier:<7} {total:>11} {matched:>8} {missing:>9}")
    print("-" * 72)
    if uncovered:
        print(
            "Not gated (no vendored upstream spec available in specs/): "
            + ", ".join(sorted(uncovered))
        )
        print()

    if warnings:
        print(f"WARNINGS ({len(warnings)}) — existing products still migrating to the generated aggregate:")
        for warning in warnings:
            print(f"  - {warning}")
        print()

    if strict_failures:
        print(f"FAILURES ({len(strict_failures)}) — strict products must match their upstream spec exactly:")
        for failure in strict_failures:
            print(f"  - {failure}", file=sys.stderr)
        print()
        print("Upstream drift gate FAILED.", file=sys.stderr)
        return 1

    strict_names = ", ".join(sorted(STRICT_PRODUCTS))
    print(f"Upstream drift gate passed: strict products ({strict_names}) match their vendored specs exactly.")
    if warnings:
        print(f"{len(warnings)} warning(s) reported above for hand-maintained products (non-fatal).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
