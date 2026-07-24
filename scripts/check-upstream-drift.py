#!/usr/bin/env python3
"""Bidirectional upstream-contract drift gate for the Tempera aggregate SDK."""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "surface.json"
SPECS_DIR = ROOT / "specs"
EXCLUSIONS = ROOT / "contracts" / "sdk-operation-exclusions.json"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
VENDORED_SPECS = {
    "dataEngine": "data-engine-openapi.json",
    "temperaLlm": "tempera-llm-api.json",
    "temperaWorkflows": "tempera-workflows-api.json",
    "temperaGym": "tempera-gym-api.json",
    "palette": "palette-api.json",
    "controlPlane": "control-plane.openapi.json",
    "cradle": "cradle-openapi.json",
    "remi": "remi-http-contract.json",
    "tempo": "tempo-openapi.json",
}
STRICT_PRODUCTS = set(VENDORED_SPECS)
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
Route = tuple[str, str]


def normalize_path(path: str) -> str:
    return PARAM_RE.sub("{}", path)


def upstream_index(spec: dict[str, Any]) -> dict[Route, str]:
    if spec.get("contract_kind") == "http-route-manifest":
        operations: dict[Route, str] = {}
        for endpoint in spec.get("endpoints") or []:
            if not isinstance(endpoint, dict):
                continue
            method = endpoint.get("method")
            path = endpoint.get("path")
            operation_id = endpoint.get("operation")
            if not all(isinstance(value, str) and value for value in (method, path, operation_id)):
                raise ValueError("HTTP route manifest has an invalid endpoint")
            route = (method.upper(), normalize_path(path))
            if route in operations:
                raise ValueError(f"duplicate upstream route shape {route}")
            operations[route] = operation_id
        return operations
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
        upstream_operation_id = operation.get("upstreamOperationId")
        if not isinstance(upstream_operation_id, str) or not upstream_operation_id:
            duplicates.append(
                f"{operation['id']!r} lacks a generated upstreamOperationId"
            )
            upstream_operation_id = operation["id"]
        indexed[route] = upstream_operation_id
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
        try:
            review_after = date.fromisoformat(entry["review_after"])
        except ValueError:
            errors.append(f"{label} review_after must be an ISO calendar date")
            continue
        if review_after < date.today():
            errors.append(
                f"{label} operation exclusion review expired on {review_after.isoformat()}"
            )
            continue
        route = (entry["method"].upper(), normalize_path(entry["path"]))
        product_entries = indexed.setdefault(entry["product"], {})
        if route in product_entries:
            errors.append(f"{label} duplicates exclusion route {route}")
            continue
        product_entries[route] = entry
    return indexed, errors


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
        for route in sorted(stale):
            failures.append(f"{product}: stale operation exclusion {route}")
        for route in sorted(phantom):
            destination.append(
                f"{product}.{sdk[route]}: phantom SDK route {route[0]} {route[1]}"
            )
        for route in sorted(set(sdk) & set(upstream)):
            if sdk[route] != upstream[route]:
                destination.append(
                    f"{product}: operationId drift for {route[0]} {route[1]}: "
                    f"SDK lock {sdk[route]!r} != upstream {upstream[route]!r}"
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
        print(f"\nWARNINGS ({len(warnings)}):")
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
