#!/usr/bin/env python3
"""Guard the aggregate HTTP surface against new Google AIP style debt.

This is intentionally a ratchet, not a claim that the current producers are
already fully AIP compliant. Mechanical violations are discovered from the
exact vendored producer contracts. Every legacy violation must exist in the
reviewed baseline, and every baseline entry must still correspond to a real
violation. New or stale entries fail CI.

Protocol endpoints (MCP, OAuth, OTLP, webhooks, WebSocket, SSE, health, and
metrics) remain governed by their native protocols and are excluded explicitly.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "contracts" / "aip-conformance-baseline.json"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
SPECS = {
    "controlPlane": "control-plane.openapi.json",
    "cradle": "cradle-openapi.json",
    "dataEngine": "data-engine-openapi.json",
    "palette": "palette-api.json",
    "remi": "remi-http-contract.json",
    "temperaGym": "tempera-gym-api.json",
    "temperaLlm": "tempera-llm-api.json",
    "temperaWorkflows": "tempera-workflows-api.json",
    "tempo": "tempo-openapi.json",
}

# These are transport or operational endpoints, not Google-style resource APIs.
# Keeping the list exact makes an accidentally added exception fail the ratchet.
PROTOCOL_EXCEPTIONS = {
    ("controlPlane", "/healthz"),
    ("controlPlane", "/mcp"),
    ("controlPlane", "/oauth/authorize"),
    ("controlPlane", "/oauth/revoke"),
    ("controlPlane", "/oauth/token"),
    ("controlPlane", "/billing/webhook"),
    ("controlPlane", "/billing/rails/coinbase/webhook"),
    ("controlPlane", "/billing/rails/paypal/webhook"),
    ("controlPlane", "/github/callback"),
    ("controlPlane", "/github/webhook"),
    ("controlPlane", "/readyz"),
    ("cradle", "/v1/health"),
    ("cradle", "/mcp"),
    ("dataEngine", "/v1/health"),
    ("dataEngine", "/mcp"),
    ("palette", "/health"),
    ("palette", "/v1/traces"),
    ("remi", "/livez"),
    ("remi", "/readyz"),
    ("temperaGym", "/healthz"),
    ("temperaLlm", "/healthz"),
    ("temperaLlm", "/readyz"),
    ("temperaWorkflows", "/healthz"),
    ("tempo", "/health"),
    ("tempo", "/ready"),
    ("tempo", "/metrics"),
    ("tempo", "/openapi.json"),
    ("tempo", "/bidi"),
    ("tempo", "/mcp"),
}
PROTOCOL_PREFIX_EXCEPTIONS = {
    ("controlPlane", "/.well-known/"),
    ("palette", "/v1/otlp/"),
    ("tempo", "/.well-known/"),
}
PROTOCOL_SUFFIX_EXCEPTIONS = {
    ("temperaWorkflows", "/events"),
    ("tempo", "/bidi"),
}

RULES = {
    "aip-127-versioned-path": {
        "aip": "https://google.aip.dev/127",
        "summary": "Resource API paths use the versioned /v1 namespace.",
    },
    "aip-127-no-put": {
        "aip": "https://google.aip.dev/127",
        "summary": "Resource APIs do not use HTTP PUT.",
    },
    "aip-127-lower-camel-parameters": {
        "aip": "https://google.aip.dev/127",
        "summary": "Public path and query parameter names use lowerCamelCase.",
    },
    "aip-127-lower-camel-json-fields": {
        "aip": "https://google.aip.dev/127",
        "summary": "Public request and response JSON field names use lowerCamelCase.",
    },
    "aip-136-lower-camel-custom-verb": {
        "aip": "https://google.aip.dev/136",
        "summary": "Colon custom verbs use lowerCamelCase.",
    },
    "aip-158-list-pagination": {
        "aip": "https://google.aip.dev/158",
        "summary": "List methods accept pageSize and pageToken.",
    },
    "aip-161-update-mask": {
        "aip": "https://google.aip.dev/161",
        "summary": "PATCH update methods accept updateMask.",
    },
    "aip-193-standard-errors": {
        "aip": "https://google.aip.dev/193",
        "summary": "HTTP errors use google.rpc.Status-compatible JSON semantics.",
    },
}


def is_protocol_exception(product: str, path: str) -> bool:
    if (product, path) in PROTOCOL_EXCEPTIONS:
        return True
    if any(
        product == exception_product and path.startswith(prefix)
        for exception_product, prefix in PROTOCOL_PREFIX_EXCEPTIONS
    ):
        return True
    return any(
        product == exception_product and path.endswith(suffix)
        for exception_product, suffix in PROTOCOL_SUFFIX_EXCEPTIONS
    )


def resolve_parameter(
    parameter: dict[str, Any], spec: dict[str, Any]
) -> dict[str, Any]:
    """Resolve local OpenAPI component parameter references for inspection."""
    reference = parameter.get("$ref")
    if not isinstance(reference, str):
        return parameter
    prefix = "#/components/parameters/"
    if not reference.startswith(prefix):
        return parameter
    name = reference.removeprefix(prefix).replace("~1", "/").replace("~0", "~")
    resolved = ((spec.get("components") or {}).get("parameters") or {}).get(name)
    return resolved if isinstance(resolved, dict) else parameter


def resolve_local_reference(
    value: dict[str, Any], spec: dict[str, Any]
) -> tuple[dict[str, Any], str | None]:
    """Resolve a local JSON Pointer reference and return its stable identity."""
    reference = value.get("$ref")
    if not isinstance(reference, str) or not reference.startswith("#/"):
        return value, None
    resolved: Any = spec
    try:
        for token in reference[2:].split("/"):
            resolved = resolved[token.replace("~1", "/").replace("~0", "~")]
    except (KeyError, TypeError):
        return value, None
    return (resolved, reference) if isinstance(resolved, dict) else (value, None)


def schema_property_names(
    schema: dict[str, Any],
    spec: dict[str, Any],
    seen_references: set[str] | None = None,
) -> set[str]:
    """Collect JSON property names recursively from an OpenAPI schema."""
    seen = set() if seen_references is None else seen_references
    resolved, reference = resolve_local_reference(schema, spec)
    if reference is not None:
        if reference in seen:
            return set()
        seen.add(reference)

    names = {
        name
        for name in (resolved.get("properties") or {})
        if isinstance(name, str)
    }
    for child in (resolved.get("properties") or {}).values():
        if isinstance(child, dict):
            names.update(schema_property_names(child, spec, seen))
    items = resolved.get("items")
    if isinstance(items, dict):
        names.update(schema_property_names(items, spec, seen))
    additional = resolved.get("additionalProperties")
    if isinstance(additional, dict):
        names.update(schema_property_names(additional, spec, seen))
    for keyword in ("allOf", "anyOf", "oneOf"):
        for child in resolved.get(keyword) or []:
            if isinstance(child, dict):
                names.update(schema_property_names(child, spec, seen))
    return names


def operation_json_property_names(
    operation: dict[str, Any], spec: dict[str, Any]
) -> set[str]:
    """Collect wire JSON fields reachable from request and response bodies."""
    names: set[str] = set()
    body_containers: list[dict[str, Any]] = []
    request_body = operation.get("requestBody")
    if isinstance(request_body, dict):
        resolved, _ = resolve_local_reference(request_body, spec)
        body_containers.append(resolved)
    for response in (operation.get("responses") or {}).values():
        if isinstance(response, dict):
            resolved, _ = resolve_local_reference(response, spec)
            body_containers.append(resolved)

    for container in body_containers:
        for media_type in (container.get("content") or {}).values():
            if not isinstance(media_type, dict):
                continue
            schema = media_type.get("schema")
            if isinstance(schema, dict):
                names.update(schema_property_names(schema, spec))
    return names


def schema_properties(
    schema: dict[str, Any],
    spec: dict[str, Any],
    seen_references: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Return properties declared by a schema and its composed parents."""
    seen = set() if seen_references is None else seen_references
    resolved, reference = resolve_local_reference(schema, spec)
    if reference is not None:
        if reference in seen:
            return {}
        seen.add(reference)
    properties = {
        name: value
        for name, value in (resolved.get("properties") or {}).items()
        if isinstance(name, str) and isinstance(value, dict)
    }
    for keyword in ("allOf", "anyOf", "oneOf"):
        for child in resolved.get(keyword) or []:
            if isinstance(child, dict):
                properties.update(schema_properties(child, spec, seen))
    return properties


def google_rpc_error_schema_issues(
    schema: dict[str, Any], spec: dict[str, Any]
) -> list[str]:
    """Validate the REST JSON wrapper for a google.rpc.Status error."""
    wrapper = schema_properties(schema, spec)
    error_schema = wrapper.get("error")
    if error_schema is None:
        return ["error"]
    error = schema_properties(error_schema, spec)
    issues: list[str] = []
    expected_types = {
        "code": "integer",
        "status": "string",
        "message": "string",
        "details": "array",
    }
    for name, expected_type in expected_types.items():
        value = error.get(name)
        if value is None:
            issues.append(f"error.{name}")
            continue
        resolved, _ = resolve_local_reference(value, spec)
        actual_type = resolved.get("type")
        if actual_type != expected_type:
            issues.append(
                f"error.{name}:{actual_type or 'unspecified'}"
            )
    return issues


def operation_standard_error_issues(
    operation: dict[str, Any], spec: dict[str, Any]
) -> list[str]:
    """Return non-conformant HTTP error response codes and schema details."""
    responses = operation.get("responses") or {}
    error_responses = {
        str(status): response
        for status, response in responses.items()
        if str(status) == "default"
        or re.fullmatch(r"[45](?:[0-9]{2}|XX)", str(status), re.IGNORECASE)
    }
    if not error_responses:
        return ["missing-error-response"]

    issues: list[str] = []
    for status, response in sorted(error_responses.items()):
        if not isinstance(response, dict):
            issues.append(f"{status}:response")
            continue
        resolved, _ = resolve_local_reference(response, spec)
        media_type = (resolved.get("content") or {}).get("application/json")
        if not isinstance(media_type, dict):
            issues.append(f"{status}:application/json")
            continue
        schema = media_type.get("schema")
        if not isinstance(schema, dict):
            issues.append(f"{status}:schema")
            continue
        for issue in google_rpc_error_schema_issues(schema, spec):
            issues.append(f"{status}:{issue}")
    return issues


def operation_rows(product: str, spec: dict[str, Any]) -> list[dict[str, Any]]:
    if spec.get("contract_kind") == "http-route-manifest":
        manifest_error_fields = set(
            (spec.get("error_shape") or {}).get("fields") or []
        )
        manifest_error_issues = []
        if "error.code" not in manifest_error_fields:
            manifest_error_issues.append("manifest:error.code")
        else:
            manifest_error_issues.append("manifest:error.code:string")
        for field in ("error.status", "error.details"):
            if field not in manifest_error_fields:
                manifest_error_issues.append(f"manifest:{field}")
        rows: list[dict[str, Any]] = []
        for endpoint in spec.get("endpoints") or []:
            if not isinstance(endpoint, dict):
                continue
            method = endpoint.get("method")
            path = endpoint.get("path")
            operation_id = endpoint.get("operation")
            if all(isinstance(value, str) and value for value in (method, path, operation_id)):
                parameters = [
                    {"name": name, "in": "query"}
                    for name in endpoint.get("query_fields") or []
                    if isinstance(name, str)
                ]
                rows.append(
                    {
                        "product": product,
                        "method": method.upper(),
                        "path": path,
                        "operation_id": operation_id,
                        "parameters": parameters,
                        "json_fields": [
                            name
                            for field in ("body_fields", "response_fields")
                            for name in endpoint.get(field) or []
                            if isinstance(name, str)
                        ],
                        "standard_error_issues": manifest_error_issues,
                    }
                )
        return rows

    rows = []
    for path, path_item in (spec.get("paths") or {}).items():
        if not isinstance(path, str) or not isinstance(path_item, dict):
            continue
        inherited_parameters = [
            resolve_parameter(value, spec)
            for value in path_item.get("parameters", [])
            if isinstance(value, dict)
        ]
        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            parameters = inherited_parameters + [
                resolve_parameter(value, spec)
                for value in operation.get("parameters", [])
                if isinstance(value, dict)
            ]
            rows.append(
                {
                    "product": product,
                    "method": method.upper(),
                    "path": path,
                    "operation_id": operation.get("operationId", ""),
                    "parameters": parameters,
                    "json_fields": sorted(
                        operation_json_property_names(operation, spec)
                    ),
                    "standard_error_issues": operation_standard_error_issues(
                        operation, spec
                    ),
                }
            )
    return rows


def is_lower_camel(value: str) -> bool:
    return re.fullmatch(r"[a-z][A-Za-z0-9]*", value) is not None


def is_list_operation(operation_id: str) -> bool:
    return (
        re.match(r"^list(?:[A-Z_]|$)", operation_id) is not None
        or re.search(r"(?:^|[._-])list(?:$|[._-])", operation_id, re.IGNORECASE)
        is not None
    )


def violation_key(
    product: str, method: str, path: str, rule: str
) -> str:
    return "|".join((product, method, path, rule))


def discover_violations(specs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    violations: dict[str, dict[str, Any]] = {}

    def add(row: dict[str, Any], rule: str, observed: list[str]) -> None:
        key = violation_key(row["product"], row["method"], row["path"], rule)
        violations[key] = {
            "product": row["product"],
            "method": row["method"],
            "path": row["path"],
            "operation_id": row["operation_id"],
            "rule": rule,
            "observed": sorted(set(observed)),
        }

    for product, spec in specs.items():
        for row in operation_rows(product, spec):
            path = row["path"]
            if is_protocol_exception(product, path):
                continue
            if not (path == "/v1" or path.startswith("/v1/")):
                add(row, "aip-127-versioned-path", [path])
            if row["method"] == "PUT":
                add(row, "aip-127-no-put", ["PUT"])

            parameter_names = {
                parameter.get("name")
                for parameter in row["parameters"]
                if parameter.get("in") in {"path", "query"}
                and isinstance(parameter.get("name"), str)
            }
            # Route-manifest contracts still expose path parameter names.
            parameter_names.update(re.findall(r"\{([^}]+)\}", path))
            non_camel = sorted(
                name for name in parameter_names if not is_lower_camel(name)
            )
            if non_camel:
                add(row, "aip-127-lower-camel-parameters", non_camel)

            non_camel_json_fields = sorted(
                name
                for name in row.get("json_fields") or []
                if name != "@type" and not is_lower_camel(name)
            )
            if non_camel_json_fields:
                add(
                    row,
                    "aip-127-lower-camel-json-fields",
                    non_camel_json_fields,
                )

            for custom_verb in re.findall(r":([^/{}]+)", path):
                if not is_lower_camel(custom_verb):
                    add(
                        row,
                        "aip-136-lower-camel-custom-verb",
                        [custom_verb],
                    )

            if row["method"] == "GET" and is_list_operation(row["operation_id"]):
                missing = [
                    name
                    for name in ("pageSize", "pageToken")
                    if name not in parameter_names
                ]
                if missing:
                    add(row, "aip-158-list-pagination", missing)

            if row["method"] == "PATCH" and "updateMask" not in parameter_names:
                add(row, "aip-161-update-mask", ["updateMask"])

            error_issues = row.get("standard_error_issues") or []
            if error_issues:
                add(row, "aip-193-standard-errors", error_issues)
    return violations


def load_specs() -> dict[str, dict[str, Any]]:
    loaded: dict[str, dict[str, Any]] = {}
    for product, filename in SPECS.items():
        path = ROOT / "specs" / filename
        loaded[product] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def load_baseline() -> dict[str, Any]:
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def validate_protocol_exceptions(specs: dict[str, dict[str, Any]]) -> list[str]:
    paths = {
        product: {row["path"] for row in operation_rows(product, spec)}
        for product, spec in specs.items()
    }
    failures: list[str] = []
    for product, path in sorted(PROTOCOL_EXCEPTIONS):
        if path not in paths.get(product, set()):
            failures.append(f"stale exact protocol exception: {product}|{path}")
    for product, prefix in sorted(PROTOCOL_PREFIX_EXCEPTIONS):
        if not any(path.startswith(prefix) for path in paths.get(product, set())):
            failures.append(f"stale protocol prefix exception: {product}|{prefix}")
    for product, suffix in sorted(PROTOCOL_SUFFIX_EXCEPTIONS):
        if not any(path.endswith(suffix) for path in paths.get(product, set())):
            failures.append(f"stale protocol suffix exception: {product}|{suffix}")
    return failures


def validate_baseline_shape(baseline: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if baseline.get("schema_version") != 1:
        failures.append("baseline schema_version must be 1")
    if baseline.get("rules") != RULES:
        failures.append("baseline rules differ from the executable policy")
    if baseline.get("protocol_exceptions") != sorted(
        f"{product}|{path}" for product, path in PROTOCOL_EXCEPTIONS
    ):
        failures.append("baseline exact protocol exceptions are stale")
    if baseline.get("protocol_prefix_exceptions") != sorted(
        f"{product}|{path}" for product, path in PROTOCOL_PREFIX_EXCEPTIONS
    ):
        failures.append("baseline protocol prefix exceptions are stale")
    if baseline.get("protocol_suffix_exceptions") != sorted(
        f"{product}|{path}" for product, path in PROTOCOL_SUFFIX_EXCEPTIONS
    ):
        failures.append("baseline protocol suffix exceptions are stale")
    try:
        review_after = date.fromisoformat(baseline["review_after"])
        if review_after < date.today():
            failures.append(
                f"baseline review expired on {review_after.isoformat()}"
            )
    except (KeyError, TypeError, ValueError):
        failures.append("baseline review_after must be an ISO calendar date")
    entries = baseline.get("accepted_violations")
    if not isinstance(entries, list) or not all(
        isinstance(value, str) and value for value in entries
    ):
        failures.append("accepted_violations must be an array of non-empty strings")
    elif entries != sorted(set(entries)):
        failures.append("accepted_violations must be unique and sorted")
    return failures


def rendered_baseline(
    previous: dict[str, Any], violations: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "policy": "Google Cloud API Improvement Proposals",
        "review_after": previous.get("review_after", "2026-10-01"),
        "rules": RULES,
        "protocol_exceptions": sorted(
            f"{product}|{path}" for product, path in PROTOCOL_EXCEPTIONS
        ),
        "protocol_prefix_exceptions": sorted(
            f"{product}|{path}" for product, path in PROTOCOL_PREFIX_EXCEPTIONS
        ),
        "protocol_suffix_exceptions": sorted(
            f"{product}|{path}" for product, path in PROTOCOL_SUFFIX_EXCEPTIONS
        ),
        "accepted_violations": sorted(violations),
        "design_migrations": previous.get("design_migrations", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Rewrite the exact mechanical debt snapshot after reviewed migration work.",
    )
    args = parser.parse_args()

    try:
        specs = load_specs()
        violations = discover_violations(specs)
        baseline = load_baseline()
    except (OSError, json.JSONDecodeError) as error:
        print(f"AIP conformance gate failed to load inputs: {error}", file=sys.stderr)
        return 1

    if args.update_baseline:
        BASELINE.write_text(
            json.dumps(rendered_baseline(baseline, violations), indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            f"wrote {BASELINE.relative_to(ROOT)} with "
            f"{len(violations)} accepted mechanical violations"
        )
        return 0

    failures = validate_baseline_shape(baseline)
    failures.extend(validate_protocol_exceptions(specs))
    accepted = set(baseline.get("accepted_violations") or [])
    discovered = set(violations)
    new = sorted(discovered - accepted)
    stale = sorted(accepted - discovered)
    if new:
        failures.extend(f"new AIP violation: {key}" for key in new)
    if stale:
        failures.extend(f"stale AIP exception: {key}" for key in stale)

    counts: dict[str, int] = {rule: 0 for rule in RULES}
    for violation in violations.values():
        counts[violation["rule"]] += 1
    print("Google Cloud AIP conformance ratchet")
    print("=" * 72)
    for rule, count in counts.items():
        print(f"{rule:<40} {count:>5}")
    print("-" * 72)
    print(
        f"tracked mechanical violations: {len(violations)}; "
        f"protocol exceptions: "
        f"{len(PROTOCOL_EXCEPTIONS) + len(PROTOCOL_PREFIX_EXCEPTIONS) + len(PROTOCOL_SUFFIX_EXCEPTIONS)}"
    )
    if failures:
        print(f"\nFAILURES ({len(failures)}):", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print(
        "AIP ratchet passed: no new or stale mechanical violations; "
        "breaking design migrations remain explicit."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
