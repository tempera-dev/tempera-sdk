#!/usr/bin/env python3
"""The single Google-AIP rule engine, shared by producers and the SDK.

`scripts/check-aip-conformance.py` runs these rules over the aggregate vendored
surface; `scripts/lint_producer_contract.py` runs the identical rules over one
producer's own contract before it is ever published. Two call sites, one
implementation, so a contract that passes in its home repository cannot fail
once it is vendored.

Exemptions are passed in rather than hardcoded: the SDK supplies its reviewed
baseline tables, a producer supplies its own `x-tempera-protocol-routes`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import unquote


HTTP_METHODS = {"get", "post", "put", "patch", "delete"}

# The only route shapes a producer may declare as protocol routes. Anything
# else is a resource API and answers to AIP, so a producer cannot exempt its
# way out of the rules by writing a path into x-tempera-protocol-routes.
EXEMPTIBLE_ROUTE = re.compile(
    r"^/(healthz|readyz|livez|metrics|mcp|bidi|openapi\.json)$"
    r"|^/\.well-known/"
    r"|^/oauth/"
    r"|^/v1/webhooks/"
    r"|webhook$|/callback$|^/v1/otlp/|/events$"
)


def declared_protocol_routes(
    product: str, spec: dict[str, Any]
) -> tuple[set[tuple[str, str]], list[str]]:
    """Read a contract's own x-tempera-protocol-routes declaration.

    The producer states which of its routes are governed by a native protocol
    rather than by Google AIP style. Honouring that declaration is what stops
    the SDK from having to mirror every producer's health and transport routes
    in a hand-maintained table. The declaration is re-validated here rather
    than trusted: a route that is not served, or that is not an exemptible
    shape, is an error, not an exemption.
    """
    declared = spec.get("x-tempera-protocol-routes")
    if declared is None:
        return set(), []
    if not isinstance(declared, list) or not all(
        isinstance(route, str) for route in declared
    ):
        return set(), [f"{product}: x-tempera-protocol-routes must be an array of strings"]
    served = set(spec.get("paths") or {})
    problems: list[str] = []
    exempt: set[tuple[str, str]] = set()
    for route in declared:
        if route not in served:
            problems.append(
                f"{product}: x-tempera-protocol-routes declares {route}, "
                "which the contract does not serve"
            )
        elif EXEMPTIBLE_ROUTE.search(route) is None:
            problems.append(
                f"{product}: {route} is a resource route and cannot be "
                "declared a protocol route"
            )
        else:
            exempt.add((product, route))
    return exempt, problems

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


@dataclass(frozen=True)
class Exemptions:
    """Routes governed by a native protocol rather than by Google AIP style."""

    paths: frozenset[tuple[str, str]] = frozenset()
    prefixes: frozenset[tuple[str, str]] = frozenset()
    suffixes: frozenset[tuple[str, str]] = frozenset()
    operations: frozenset[tuple[str, str, str]] = frozenset()
    json_payloads: frozenset[tuple[str, str, str]] = frozenset()

    def covers_path(self, product: str, path: str) -> bool:
        if (product, path) in self.paths:
            return True
        if any(
            product == exempt_product and path.startswith(prefix)
            for exempt_product, prefix in self.prefixes
        ):
            return True
        return any(
            product == exempt_product and path.endswith(suffix)
            for exempt_product, suffix in self.suffixes
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
        manifest_error_types = (
            (spec.get("error_shape") or {}).get("field_types") or {}
        )
        manifest_error_issues = []
        for field, expected_type in {
            "error.code": "integer",
            "error.status": "string",
            "error.message": "string",
            "error.details": "array",
        }.items():
            if field not in manifest_error_fields:
                manifest_error_issues.append(f"manifest:{field}")
                continue
            actual_type = manifest_error_types.get(field)
            if actual_type != expected_type:
                manifest_error_issues.append(
                    f"manifest:{field}:{actual_type or 'unspecified'}"
                )
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
                            for field in (
                                "request_fields",
                                "body_fields",
                                "response_fields",
                            )
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


def discover_violations(
    specs: dict[str, dict[str, Any]], exemptions: Exemptions
) -> dict[str, dict[str, Any]]:
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
            if exemptions.covers_path(product, path):
                continue
            operation_key = (product, row["method"], path)
            if operation_key in exemptions.operations:
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
            if (
                non_camel_json_fields
                and operation_key not in exemptions.json_payloads
            ):
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
