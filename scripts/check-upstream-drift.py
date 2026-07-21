#!/usr/bin/env python3
"""Bidirectional upstream-contract drift gate for the Tempera aggregate SDK."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "surface.json"
SPECS_DIR = ROOT / "specs"
EXCLUSIONS = ROOT / "contracts" / "sdk-operation-exclusions.json"
MIGRATIONS = ROOT / "contracts" / "sdk-coverage-migrations.json"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
VENDORED_SPECS = {
    "temperaLlm": "tempera-llm-api.json",
    "temperaWorkflows": "tempera-workflows-api.json",
    "temperaGym": "tempera-gym-api.json",
    "palette": "palette-api.json",
    "controlPlane": "control-plane.openapi.json",
    "cradle": "cradle-openapi.json",
}
STRICT_PRODUCTS = {"temperaLlm", "temperaWorkflows", "temperaGym"}
PARAM_RE = re.compile(r"\{[^}]+\}")
EXCLUSION_KEYS = {
    "product",
    "method",
    "path",
    "operation_id",
    "compatibility",
    "owner",
    "rationale",
    "migration",
    "review_after",
}
MIGRATION_KEYS = {
    "product",
    "compatibility",
    "owner",
    "depends_on",
    "migration",
    "rollback",
    "review_after",
    "phantom_routes",
    "upstream_only_routes",
    "duplicate_routes",
}

Route = tuple[str, str]


def normalize_path(path: str) -> str:
    return PARAM_RE.sub("{}", path)


def upstream_index(spec: dict[str, Any]) -> dict[Route, str]:
    operations: dict[Route, str] = {}
    for path, item in (spec.get("paths") or {}).items():
        if not isinstance(path, str) or not isinstance(item, dict):
            continue
        for method, operation in item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            route = (method.upper(), normalize_path(path))
            if route in operations:
                raise ValueError(f"duplicate upstream route shape {route}")
            operation_id = operation.get("operationId")
            if not isinstance(operation_id, str) or not operation_id:
                raise ValueError(f"upstream route {method.upper()} {path} has no operationId")
            operations[route] = operation_id
    return operations


def surface_index(
    operations: list[dict[str, Any]],
) -> tuple[dict[Route, str], list[str]]:
    indexed: dict[Route, str] = {}
    duplicates: list[str] = []
    for operation in operations:
        route = (operation["method"], normalize_path(operation["path"]))
        if route in indexed:
            duplicates.append(
                f"duplicate SDK route shape {route} for "
                f"{indexed[route]!r} and {operation['id']!r}"
            )
            continue
        indexed[route] = operation["id"]
    return indexed, duplicates


def classify_routes(
    surface: dict[Route, str],
    upstream: dict[Route, str],
    exclusions: set[Route],
) -> tuple[set[Route], set[Route], set[Route]]:
    phantom = set(surface) - set(upstream)
    missing = set(upstream) - set(surface) - exclusions
    stale_exclusions = exclusions - (set(upstream) - set(surface))
    return phantom, missing, stale_exclusions


def load_exclusions(path: Path) -> tuple[dict[str, dict[Route, dict[str, str]]], list[str]]:
    errors: list[str] = []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {}, [f"invalid operation exclusion ledger: {error}"]
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        return {}, ["operation exclusion ledger must use schema_version 1"]
    entries = value.get("exclusions")
    if not isinstance(entries, list):
        return {}, ["operation exclusion ledger exclusions must be an array"]
    indexed: dict[str, dict[Route, dict[str, str]]] = {}
    for position, entry in enumerate(entries):
        label = f"exclusions[{position}]"
        if not isinstance(entry, dict) or set(entry) != EXCLUSION_KEYS:
            errors.append(f"{label} keys differ from the exact exclusion schema")
            continue
        if not all(isinstance(entry[key], str) and entry[key] for key in EXCLUSION_KEYS):
            errors.append(f"{label} fields must be non-empty strings")
            continue
        if entry["product"] not in VENDORED_SPECS:
            errors.append(f"{label} names unknown product {entry['product']!r}")
            continue
        if entry["method"].lower() not in HTTP_METHODS:
            errors.append(f"{label} has unsupported method {entry['method']!r}")
            continue
        route = (entry["method"].upper(), normalize_path(entry["path"]))
        product_entries = indexed.setdefault(entry["product"], {})
        if route in product_entries:
            errors.append(f"{label} duplicates exclusion route {route}")
            continue
        product_entries[route] = entry
    return indexed, errors


def load_migrations(path: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    errors: list[str] = []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {}, [f"invalid SDK coverage migration ledger: {error}"]
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        return {}, ["SDK coverage migration ledger must use schema_version 1"]
    entries = value.get("migrations")
    if not isinstance(entries, list):
        return {}, ["SDK coverage migration ledger migrations must be an array"]
    indexed: dict[str, dict[str, Any]] = {}
    for position, entry in enumerate(entries):
        label = f"migrations[{position}]"
        if not isinstance(entry, dict) or set(entry) != MIGRATION_KEYS:
            errors.append(f"{label} keys differ from the exact migration schema")
            continue
        product = entry.get("product")
        if not isinstance(product, str) or product not in VENDORED_SPECS:
            errors.append(f"{label} names unknown product {product!r}")
            continue
        if product in indexed:
            errors.append(f"{label} duplicates product {product!r}")
            continue
        for key in MIGRATION_KEYS - {
            "phantom_routes",
            "upstream_only_routes",
            "duplicate_routes",
        }:
            if not isinstance(entry.get(key), str) or not entry[key]:
                errors.append(f"{label}.{key} must be a non-empty string")
        for key in ("phantom_routes", "upstream_only_routes", "duplicate_routes"):
            if not isinstance(entry.get(key), int) or entry[key] < 0:
                errors.append(f"{label}.{key} must be a non-negative integer")
        indexed[product] = entry
    return indexed, errors


def migration_count_errors(
    product: str,
    migration: dict[str, Any] | None,
    *,
    phantom: int,
    upstream_only: int,
    duplicates: int,
) -> list[str]:
    if migration is None:
        return [f"{product}: warning-tier product has no coverage migration"]
    expected = {
        "phantom_routes": phantom,
        "upstream_only_routes": upstream_only,
        "duplicate_routes": duplicates,
    }
    return [
        f"{product}: migration {field} {migration.get(field)!r} != observed {observed}"
        for field, observed in expected.items()
        if migration.get(field) != observed
    ]


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []
    try:
        surface = json.loads(SURFACE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"upstream drift gate failed: invalid surface.json: {error}", file=sys.stderr)
        return 1
    exclusions, exclusion_errors = load_exclusions(EXCLUSIONS)
    failures.extend(exclusion_errors)
    migrations, migration_errors = load_migrations(MIGRATIONS)
    failures.extend(migration_errors)
    rows: list[tuple[str, str, int, int, int, int]] = []

    for product, spec_file in VENDORED_SPECS.items():
        tier = "STRICT" if product in STRICT_PRODUCTS else "warn"
        try:
            spec = json.loads((SPECS_DIR / spec_file).read_text(encoding="utf-8"))
            upstream = upstream_index(spec)
            sdk, duplicate_sdk_routes = surface_index(
                surface.get("operations", {}).get(product, [])
            )
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            message = f"{product}: cannot compare {spec_file}: {error}"
            (failures if product in STRICT_PRODUCTS else warnings).append(message)
            rows.append((product, tier, 0, 0, 0, 0))
            continue

        product_exclusions = exclusions.get(product, {})
        destination = failures if product in STRICT_PRODUCTS else warnings
        for duplicate in duplicate_sdk_routes:
            destination.append(f"{product}: {duplicate}")
        for route, entry in product_exclusions.items():
            observed_operation_id = upstream.get(route)
            if observed_operation_id != entry["operation_id"]:
                failures.append(
                    f"{product}: exclusion {route} operationId {entry['operation_id']!r} "
                    f"!= upstream {observed_operation_id!r}"
                )
        phantom, missing, stale = classify_routes(sdk, upstream, set(product_exclusions))
        if product not in STRICT_PRODUCTS:
            failures.extend(
                migration_count_errors(
                    product,
                    migrations.get(product),
                    phantom=len(phantom),
                    upstream_only=len(missing),
                    duplicates=len(duplicate_sdk_routes),
                )
            )
        for route in sorted(stale):
            failures.append(f"{product}: stale operation exclusion {route}")
        for route in sorted(phantom):
            destination.append(
                f"{product}.{sdk[route]}: phantom SDK route {route[0]} {route[1]}"
            )
        for route in sorted(missing):
            missing_kind = (
                "missing eligible SDK route"
                if product in STRICT_PRODUCTS
                else "unclassified upstream-only route"
            )
            destination.append(
                f"{product}.{upstream[route]}: {missing_kind} {route[0]} {route[1]}"
            )
        rows.append(
            (product, tier, len(sdk), len(upstream), len(phantom), len(missing))
        )

    uncovered = sorted(
        product
        for product, operations in surface.get("operations", {}).items()
        if operations and product not in VENDORED_SPECS
    )
    print("Bidirectional upstream-spec drift gate")
    print("=" * 88)
    print(
        f"{'product':<18} {'tier':<7} {'SDK':>6} {'upstream':>9} "
        f"{'phantom':>8} {'upstream-only':>13}"
    )
    print("-" * 88)
    for product, tier, sdk_count, upstream_count, phantom_count, missing_count in rows:
        print(
            f"{product:<18} {tier:<7} {sdk_count:>6} {upstream_count:>9} "
            f"{phantom_count:>8} {missing_count:>13}"
        )
    if uncovered:
        print("Not gated (no vendored contract): " + ", ".join(uncovered))
    if warnings:
        print(f"\nWARNINGS ({len(warnings)}) — count-pinned migration gaps:")
        for warning in warnings:
            print(f"  - {warning}")
    if failures:
        print(f"\nFAILURES ({len(failures)}):", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print("\nUpstream drift gate passed; strict products have zero phantom or missing eligible operations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
