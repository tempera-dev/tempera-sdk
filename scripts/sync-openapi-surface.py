#!/usr/bin/env python3
"""Synchronize aggregate SDK bindings from vendored producer contracts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "surface.json"
EXCLUSIONS = ROOT / "contracts" / "sdk-operation-exclusions.json"
OVERRIDES = ROOT / "contracts" / "sdk-operation-overrides.json"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
PRODUCT_SPECS = {
    "dataEngine": "data-engine-openapi.json",
    "controlPlane": "control-plane.openapi.json",
    "palette": "palette-api.json",
    "cradle": "cradle-openapi.json",
    "temperaLlm": "tempera-llm-api.json",
    "temperaWorkflows": "tempera-workflows-api.json",
    "temperaGym": "tempera-gym-api.json",
    "remi": "remi-http-contract.json",
    "tempo": "tempo-openapi.json",
}
DEFAULT_AUTH = {
    "dataEngine": "product",
    "controlPlane": "account",
    "palette": "product",
    "cradle": "product",
    "temperaLlm": "product",
    "temperaWorkflows": "product",
    "temperaGym": "product",
    "remi": "product",
    "tempo": "product",
}
PARAM_RE = re.compile(r"\{([^}]+)\}")
WORD_RE = re.compile(r"[^A-Za-z0-9]+")
Route = tuple[str, str]


def normalize_path(path: str) -> str:
    return PARAM_RE.sub("{}", path)


def route(method: str, path: str) -> Route:
    return method.upper(), normalize_path(path)


def product_route(product: str, method: str, path: str) -> Route:
    if product == "dataEngine":
        path = re.sub(r"^/v1/projects/\{[^}]+\}", "/v1/{parent}", path)
    return route(method, path)


def resolve_pointer(document: dict[str, Any], reference: str) -> Any:
    if not reference.startswith("#/"):
        raise ValueError(f"only local OpenAPI references are supported: {reference}")
    value: Any = document
    for token in reference[2:].split("/"):
        key = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(value, dict) or key not in value:
            raise ValueError(f"unresolved OpenAPI reference: {reference}")
        value = value[key]
    return value


def dereference(document: dict[str, Any], value: Any) -> Any:
    seen: set[str] = set()
    while isinstance(value, dict) and isinstance(value.get("$ref"), str):
        reference = value["$ref"]
        if reference in seen:
            raise ValueError(f"cyclic OpenAPI reference: {reference}")
        seen.add(reference)
        target = resolve_pointer(document, reference)
        if not isinstance(target, dict):
            return target
        value = {**target, **{key: item for key, item in value.items() if key != "$ref"}}
    return value


def schema_fields(
    document: dict[str, Any], schema: Any
) -> tuple[list[str], list[str]]:
    schema = dereference(document, schema)
    if not isinstance(schema, dict):
        return [], []
    properties: list[str] = []
    required: list[str] = []

    def add(items: Any, destination: list[str]) -> None:
        if not isinstance(items, list):
            return
        for item in items:
            if isinstance(item, str) and item not in destination:
                destination.append(item)

    for part in schema.get("allOf", []) or []:
        nested_properties, nested_required = schema_fields(document, part)
        add(nested_properties, properties)
        add(nested_required, required)
    for composition in ("oneOf", "anyOf"):
        alternatives = schema.get(composition, []) or []
        alternative_required: list[list[str]] = []
        for part in alternatives:
            nested_properties, nested_required = schema_fields(document, part)
            add(nested_properties, properties)
            alternative_required.append(nested_required)
        if alternative_required:
            common_required = [
                field
                for field in alternative_required[0]
                if all(field in fields for fields in alternative_required[1:])
            ]
            add(common_required, required)
    own_properties = schema.get("properties")
    if isinstance(own_properties, dict):
        add(list(own_properties), properties)
    add(schema.get("required"), required)
    return properties, required


def parameters(
    document: dict[str, Any], path_item: dict[str, Any], operation: dict[str, Any]
) -> tuple[list[str], dict[str, str], list[str]]:
    path_params: list[str] = []
    path_param_templates: dict[str, str] = {}
    query: list[str] = []
    for candidate in [*(path_item.get("parameters") or []), *(operation.get("parameters") or [])]:
        parameter = dereference(document, candidate)
        if not isinstance(parameter, dict):
            continue
        name = parameter.get("name")
        location = parameter.get("in")
        if not isinstance(name, str):
            continue
        destination = path_params if location == "path" else query if location == "query" else None
        if destination is not None and name not in destination:
            destination.append(name)
        resource_pattern = parameter.get("x-tempera-resource-pattern")
        if location == "path" and resource_pattern is not None:
            if not isinstance(resource_pattern, str) or not resource_pattern:
                raise ValueError(
                    f"path parameter {name!r} has an invalid x-tempera-resource-pattern"
                )
            path_param_templates[name] = resource_pattern
    return path_params, path_param_templates, query


def request_fields(
    document: dict[str, Any], operation: dict[str, Any]
) -> tuple[list[str], list[str]]:
    request_body = dereference(document, operation.get("requestBody"))
    if not isinstance(request_body, dict):
        return [], []
    content = request_body.get("content")
    json_content = content.get("application/json") if isinstance(content, dict) else None
    if not isinstance(json_content, dict):
        return [], []
    return schema_fields(document, json_content.get("schema"))


def sdk_operation_id(operation_id: str) -> str:
    words = [word for word in WORD_RE.split(operation_id) if word]
    if not words:
        raise ValueError(f"cannot derive SDK operation id from {operation_id!r}")
    return words[0][0].lower() + words[0][1:] + "".join(
        word[0].upper() + word[1:] for word in words[1:]
    )


def sentence(operation: dict[str, Any], method: str, path: str) -> str:
    value = operation.get("summary") or operation.get("description")
    if not isinstance(value, str) or not value.strip():
        value = f"Call {method.upper()} {path}"
    value = " ".join(value.split())
    value = value[0].upper() + value[1:]
    if value[-1] not in ".!?":
        value += "."
    return value


def load_exclusions() -> dict[str, set[Route]]:
    value = json.loads(EXCLUSIONS.read_text(encoding="utf-8"))
    indexed: dict[str, set[Route]] = {}
    for entry in value["exclusions"]:
        indexed.setdefault(entry["product"], set()).add(
            route(entry["method"], entry["path"])
        )
    return indexed


def load_overrides() -> dict[str, dict[Route, dict[str, str]]]:
    value = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    if value.get("schema_version") != 1 or not isinstance(
        value.get("overrides"), list
    ):
        raise ValueError("SDK operation overrides contract is invalid")
    indexed: dict[str, dict[Route, dict[str, str]]] = {}
    required = {
        "product",
        "method",
        "path",
        "upstream_operation_id",
        "id",
    }
    for entry in value["overrides"]:
        if not isinstance(entry, dict) or set(entry) != required:
            raise ValueError("SDK operation override fields drifted")
        if not all(isinstance(entry[key], str) and entry[key] for key in required):
            raise ValueError("SDK operation override values must be non-empty strings")
        product = entry["product"]
        identity = product_route(
            product, entry["method"], entry["path"]
        )
        product_overrides = indexed.setdefault(product, {})
        if identity in product_overrides:
            raise ValueError(
                f"duplicate SDK operation override for {product} {identity}"
            )
        product_overrides[identity] = {
            "upstreamOperationId": entry["upstream_operation_id"],
            "id": entry["id"],
        }
    return indexed


def synchronize_control_plane_registries(
    surface: dict[str, Any], spec: dict[str, Any]
) -> None:
    schemas = spec.get("components", {}).get("schemas", {})
    audiences = schemas.get("ResourceAudience", {}).get("enum")
    scopes = schemas.get("Scope", {}).get("enum")
    if (
        not isinstance(audiences, list)
        or not audiences
        or not all(isinstance(item, str) and item for item in audiences)
    ):
        raise ValueError("controlPlane ResourceAudience enum is invalid")
    if (
        not isinstance(scopes, list)
        or not scopes
        or not all(isinstance(item, str) and item for item in scopes)
    ):
        raise ValueError("controlPlane Scope enum is invalid")
    surface["audiences"] = audiences
    surface["scopes"] = scopes


def synchronize_product(
    surface: dict[str, Any],
    product: str,
    spec: dict[str, Any],
    exclusions: set[Route],
    overrides: dict[Route, dict[str, str]],
) -> None:
    existing = surface["operations"][product]
    by_route: dict[Route, dict[str, Any]] = {}
    by_upstream_operation_id: dict[str, dict[str, Any]] = {}
    for item in existing:
        identity = product_route(product, item["method"], item["path"])
        if identity in by_route:
            raise ValueError(
                f"{product} has duplicate route {identity}; resolve the alias before syncing"
            )
        by_route[identity] = item
        upstream_operation_id = item.get("upstreamOperationId")
        if isinstance(upstream_operation_id, str):
            if upstream_operation_id in by_upstream_operation_id:
                raise ValueError(
                    f"{product} has duplicate upstream operationId "
                    f"{upstream_operation_id!r}"
                )
            by_upstream_operation_id[upstream_operation_id] = item

    synchronized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    matched_existing_routes: set[Route] = set()
    matched_overrides: set[Route] = set()
    if spec.get("contract_kind") == "http-route-manifest":
        for endpoint in spec.get("endpoints") or []:
            if not isinstance(endpoint, dict):
                continue
            method = endpoint.get("method")
            path = endpoint.get("path")
            operation_id = endpoint.get("operation")
            if not all(
                isinstance(value, str) and value
                for value in (method, path, operation_id)
            ):
                raise ValueError(f"{product} HTTP route manifest has an invalid endpoint")
            identity = product_route(product, method, path)
            if identity in exclusions:
                continue
            observed = by_route.get(identity) or by_upstream_operation_id.get(
                operation_id
            )
            if observed is not None:
                matched_existing_routes.add(
                    product_route(
                        product, observed["method"], observed["path"]
                    )
                )
            item = dict(observed) if observed is not None else {
                "id": sdk_operation_id(operation_id),
                "auth": (
                    "none"
                    if endpoint.get("auth") == "public"
                    else DEFAULT_AUTH[product]
                ),
                "description": f"Call {method.upper()} {path}.",
            }
            item["method"] = method.upper()
            item["path"] = path
            item["upstreamOperationId"] = operation_id
            override = overrides.get(identity)
            if override is not None:
                if override["upstreamOperationId"] != operation_id:
                    raise ValueError(
                        f"{product} override operationId drifted for {identity}"
                    )
                item["id"] = override["id"]
                matched_overrides.add(identity)
            path_params = PARAM_RE.findall(path)
            if isinstance(endpoint.get("description"), str) and endpoint["description"]:
                item["description"] = endpoint["description"]
            for key, values in (
                ("pathParams", path_params),
                ("query", endpoint.get("query_fields") or []),
                ("body", endpoint.get("request_fields") or []),
                (
                    "requiredBody",
                    endpoint.get("required_request_fields") or [],
                ),
                ("forbiddenBody", endpoint.get("forbidden_body") or []),
            ):
                if not isinstance(values, list) or not all(
                    isinstance(value, str) and value for value in values
                ):
                    raise ValueError(
                        f"{product} {operation_id} {key} must be an array of strings"
                    )
                if values:
                    item[key] = values
                else:
                    item.pop(key, None)
            if item["id"] in seen_ids:
                raise ValueError(
                    f"{product} generated duplicate operation id {item['id']!r}"
                )
            seen_ids.add(item["id"])
            synchronized.append(item)
        missing_existing = sorted(set(by_route) - matched_existing_routes)
        if missing_existing:
            raise ValueError(f"{product} has phantom surface routes: {missing_existing}")
        if set(overrides) != matched_overrides:
            raise ValueError(
                f"{product} has unmatched SDK operation overrides: "
                f"{sorted(set(overrides) - matched_overrides)}"
            )
        surface["operations"][product] = synchronized
        return

    for path, path_item in spec.get("paths", {}).items():
        if not isinstance(path, str) or not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            identity = product_route(product, method, path)
            if identity in exclusions:
                continue
            operation_id = operation.get("operationId")
            if not isinstance(operation_id, str) or not operation_id:
                raise ValueError(f"{product} {method.upper()} {path} has no operationId")
            observed = by_route.get(identity) or by_upstream_operation_id.get(
                operation_id
            )
            if observed is not None:
                matched_existing_routes.add(
                    product_route(
                        product, observed["method"], observed["path"]
                    )
                )
            item = dict(observed) if observed is not None else {
                "id": sdk_operation_id(operation_id),
                "method": method.upper(),
                "path": path,
                "auth": (
                    "none"
                    if operation.get("security") == []
                    or path in {"/health", "/healthz", "/livez", "/readyz"}
                    else DEFAULT_AUTH[product]
                ),
                "description": sentence(operation, method, path),
            }
            item["method"] = method.upper()
            item["path"] = path
            item["upstreamOperationId"] = operation_id
            override = overrides.get(identity)
            if override is not None:
                if override["upstreamOperationId"] != operation_id:
                    raise ValueError(
                        f"{product} override operationId drifted for {identity}"
                    )
                item["id"] = override["id"]
                matched_overrides.add(identity)
            path_params, path_param_templates, query = parameters(
                spec, path_item, operation
            )
            body, required_body = request_fields(spec, operation)
            for key, values in (
                ("pathParams", path_params),
                ("pathParamTemplates", path_param_templates),
                ("query", query),
                ("body", body),
                ("requiredBody", required_body),
            ):
                if values:
                    item[key] = values
                else:
                    item.pop(key, None)
            if "x-tempera-auth-kind" in operation:
                auth_kind = operation["x-tempera-auth-kind"]
                if auth_kind not in {
                    "none",
                    "account",
                    "product",
                    "oauthResource",
                    "introspectionSecret",
                }:
                    raise ValueError(
                        f"{product} {operation_id} has invalid "
                        "x-tempera-auth-kind"
                    )
                item["auth"] = auth_kind
            if "x-tempera-auth-audience" in operation:
                audience = operation["x-tempera-auth-audience"]
                if audience is None and item.get("auth") == "none":
                    item.pop("authAudience", None)
                elif isinstance(audience, str) and audience:
                    if "x-tempera-auth-kind" not in operation:
                        item["auth"] = "oauthResource"
                    elif item.get("auth") != "oauthResource":
                        raise ValueError(
                            f"{product} {operation_id} declares an auth audience "
                            "for a non-oauthResource operation"
                        )
                    item["authAudience"] = audience
                else:
                    raise ValueError(
                        f"{product} {operation_id} has invalid "
                        "x-tempera-auth-audience"
                    )
            elif item.get("auth") != "oauthResource":
                item.pop("authAudience", None)
            if "x-tempera-required-scope" in operation:
                scope = operation["x-tempera-required-scope"]
                if scope is None:
                    item.pop("scope", None)
                elif isinstance(scope, str) and scope:
                    item["scope"] = scope
                else:
                    raise ValueError(
                        f"{product} {operation_id} has invalid "
                        "x-tempera-required-scope"
                    )
            if item["id"] in seen_ids:
                raise ValueError(f"{product} generated duplicate operation id {item['id']!r}")
            seen_ids.add(item["id"])
            synchronized.append(item)
    missing_existing = sorted(set(by_route) - matched_existing_routes)
    if missing_existing:
        raise ValueError(f"{product} has phantom surface routes: {missing_existing}")
    if set(overrides) != matched_overrides:
        raise ValueError(
            f"{product} has unmatched SDK operation overrides: "
            f"{sorted(set(overrides) - matched_overrides)}"
        )
    surface["operations"][product] = synchronized


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--product",
        action="append",
        choices=sorted(PRODUCT_SPECS),
        help="Product to synchronize; repeatable. Defaults to every vendored product.",
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    products = args.product or list(PRODUCT_SPECS)
    try:
        surface = json.loads(SURFACE.read_text(encoding="utf-8"))
        exclusions = load_exclusions()
        overrides = load_overrides()
        for product in products:
            spec = json.loads(
                (ROOT / "specs" / PRODUCT_SPECS[product]).read_text(encoding="utf-8")
            )
            if product == "controlPlane":
                synchronize_control_plane_registries(surface, spec)
            synchronize_product(
                surface,
                product,
                spec,
                exclusions.get(product, set()),
                overrides.get(product, {}),
            )
        expected = json.dumps(surface, indent=2, ensure_ascii=False) + "\n"
        if args.check:
            if SURFACE.read_text(encoding="utf-8") != expected:
                raise ValueError(
                    "surface.json is stale; run scripts/sync-openapi-surface.py"
                )
            print("vendored producer-contract surface bindings are current")
            return 0
        SURFACE.write_text(expected, encoding="utf-8")
        print("wrote surface.json from vendored producer contracts")
        return 0
    except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError) as error:
        print(f"producer-contract surface sync failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
