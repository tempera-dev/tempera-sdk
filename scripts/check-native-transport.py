#!/usr/bin/env python3
"""Publish and enforce the native transport contract.

The Kotlin and Swift clients in tempera-mobile and tempera-iOS do not consume
the generated SDK packages: they hand-write their call sites. Nothing otherwise
stops one of them from drifting off the producer's canonical route, sending an
operation under the wrong audience, or keeping a stale request shape after the
producer contract moves.

`contracts/native-transport-v1.json` closes that gap. For every admitted
operation it publishes the method, the path template, the auth audience, and a
request and response digest derived from the vendored producer contract. This
script both writes that file and checks a native client against it.

Usage:
  python3 scripts/check-native-transport.py --write        # regenerate
  python3 scripts/check-native-transport.py                # fail if stale
  python3 scripts/check-native-transport.py --client PATH  # check call sites

A native call site declares itself with an annotation comment placed
immediately above the call:

    // tempera-transport: temperaDropshipping.listInbox GET /v1/organizations/...

The checker requires that the annotation names a real operation, that the
method and path template match the contract exactly, and that the very next
code line carries a string literal whose interpolated path shape is that same
route. It also requires that every literal reaching into the canonical
`/v1/organizations/...` namespace is annotated, so a new hand-written call
cannot slip in undeclared.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "surface.json"
CONTRACT = ROOT / "contracts" / "native-transport-v1.json"

# Products whose operations the native clients are allowed to call directly.
NATIVE_PRODUCTS = ("temperaDropshipping", "temperaBusiness", "temperaPayments")
PRODUCT_SPECS = {
    "temperaDropshipping": "tempera-dropshipping-api.json",
    "temperaBusiness": "tempera-business-api.json",
    "temperaPayments": "tempera-payments-api.json",
}

# Payments remains a broad producer contract, but native phones receive only
# the merchant onboarding seam. Keep this allowlist here rather than adding
# the legacy payment-intent or raw money operations to surface.json.
PAYMENTS_NATIVE_OPERATIONS = (
    {
        "id": "getMerchantWorkspace",
        "upstreamOperationId": "getMerchantWorkspace",
        "method": "GET",
        "path": "/v1/merchants/workspace",
        "safeRetry": "read",
        "authAudience": "tempera-payments",
        "scope": "payments:merchants:read",
    },
    {
        "id": "getWorkspaceMerchant",
        "upstreamOperationId": "getWorkspaceMerchant",
        "method": "GET",
        "path": "/v1/merchants",
        "query": ["tenant_id"],
        "requiredQuery": ["tenant_id"],
        "safeRetry": "read",
        "authAudience": "tempera-payments",
        "scope": "payments:merchants:read",
    },
    {
        "id": "createMerchant",
        "upstreamOperationId": "createMerchant",
        "method": "POST",
        "path": "/v1/merchants",
        "body": ["tenant_id", "country", "currency", "category"],
        "requiredBody": ["tenant_id", "country", "currency", "category"],
        "requestBodyKind": "json",
        "requestContentType": "application/json",
        "safeRetry": "none",
        "authAudience": "tempera-payments",
        "scope": "payments:merchants:write",
        "headers": ["Idempotency-Key"],
        "requiredHeaders": ["Idempotency-Key"],
    },
    {
        "id": "getMerchant",
        "upstreamOperationId": "getMerchant",
        "method": "GET",
        "path": "/v1/merchants/{merchant_id}",
        "pathParams": ["merchant_id"],
        "query": ["tenant_id"],
        "requiredQuery": ["tenant_id"],
        "safeRetry": "read",
        "authAudience": "tempera-payments",
        "scope": "payments:merchants:read",
    },
    {
        "id": "refreshMerchantEligibility",
        "upstreamOperationId": "refreshMerchantEligibility",
        "method": "POST",
        "path": "/v1/merchants/{merchant_id}/refresh",
        "pathParams": ["merchant_id"],
        "body": ["tenant_id"],
        "requiredBody": ["tenant_id"],
        "requestBodyKind": "json",
        "requestContentType": "application/json",
        "safeRetry": "none",
        "authAudience": "tempera-payments",
        "scope": "payments:merchants:read",
    },
    {
        "id": "createMerchantOnboardingLink",
        "upstreamOperationId": "createMerchantOnboardingLink",
        "method": "POST",
        "path": "/v1/merchants/{merchant_id}/onboarding",
        "pathParams": ["merchant_id"],
        "body": ["tenant_id"],
        "requiredBody": ["tenant_id"],
        "requestBodyKind": "json",
        "requestContentType": "application/json",
        "safeRetry": "none",
        "authAudience": "tempera-payments",
        "scope": "payments:merchants:write",
        "headers": ["Idempotency-Key"],
        "requiredHeaders": ["Idempotency-Key"],
    },
)

PARAM_RE = re.compile(r"\{[^}]+\}")
ANNOTATION_RE = re.compile(
    r"tempera-transport:\s*(?P<product>[A-Za-z][A-Za-z0-9]*)\."
    r"(?P<operation>[A-Za-z][A-Za-z0-9]*)\s+(?P<method>[A-Z]+)\s+(?P<path>/\S+)\s*$"
)
STRING_LITERAL_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')
# Kotlin "$name" / "${expr}" and Swift "\(expr)" interpolations.
INTERPOLATION_RE = re.compile(r"\\\([^)]*\)|\$\{[^}]*\}|\$[A-Za-z_][A-Za-z0-9_]*")
CANONICAL_PREFIXES = ("/v1/organizations/", "/v1/merchants")


def digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def path_shape(path: str) -> str:
    """A route's structural shape, independent of parameter spelling."""
    return PARAM_RE.sub("{}", path)


def resolve(document: dict[str, Any], value: Any) -> Any:
    seen: set[str] = set()
    while isinstance(value, dict) and isinstance(value.get("$ref"), str):
        reference = value["$ref"]
        if reference in seen or not reference.startswith("#/"):
            raise ValueError(f"unsupported OpenAPI reference: {reference}")
        seen.add(reference)
        target: Any = document
        for token in reference[2:].split("/"):
            key = token.replace("~1", "/").replace("~0", "~")
            if not isinstance(target, dict) or key not in target:
                raise ValueError(f"unresolved OpenAPI reference: {reference}")
            target = target[key]
        value = target
    return value


def response_schema(document: dict[str, Any], operation: dict[str, Any]) -> Any:
    """The producer's success-response JSON schema, or None when it declares none."""
    responses = operation.get("responses") or {}
    codes = sorted(code for code in responses if code.isdigit() and code.startswith("2"))
    if not codes:
        return None
    response = resolve(document, responses[codes[0]])
    content = (response or {}).get("content") or {}
    json_content = content.get("application/json")
    if not isinstance(json_content, dict):
        return None
    return resolve(document, json_content.get("schema"))


def upstream_operations(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for path, item in (spec.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for method, operation in item.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            operation_id = operation.get("operationId")
            if isinstance(operation_id, str) and operation_id:
                indexed[operation_id] = {
                    **operation,
                    "_path": path,
                    "_method": method.upper(),
                    "_headers": [resolve(spec, p) for p in [*(item.get("parameters") or []), *(operation.get("parameters") or [])] if resolve(spec, p).get("in") == "header"],
                }
    return indexed


def validate_payment_mapping(op: dict[str, Any], upstream_operation: dict[str, Any]) -> None:
    """Keep the bounded payment mapping tied to the producer's wire metadata."""
    if upstream_operation["_method"] != op["method"] or upstream_operation["_path"] != op["path"]:
        raise ValueError(f"Payments native mapping drifts from OpenAPI for {op['id']}")
    if upstream_operation.get("x-tempera-auth-audience") != op["authAudience"]:
        raise ValueError(f"Payments native audience drifts for {op['id']}")
    if upstream_operation.get("x-tempera-required-scope") != op["scope"]:
        raise ValueError(f"Payments native scope drifts for {op['id']}")
    headers = upstream_operation.get("_headers", [])
    if set(op.get("headers", [])) != {p["name"] for p in headers} or set(op.get("requiredHeaders", [])) != {p["name"] for p in headers if p.get("required") is True}:
        raise ValueError(f"Payments native headers drift for {op['id']}")


def build_contract() -> dict[str, Any]:
    surface = json.loads(SURFACE.read_text(encoding="utf-8"))
    producers: list[dict[str, Any]] = []
    operations: list[dict[str, Any]] = []
    for product in NATIVE_PRODUCTS:
        spec_name = PRODUCT_SPECS[product]
        spec = json.loads((ROOT / "specs" / spec_name).read_text(encoding="utf-8"))
        lock = json.loads(
            (ROOT / "specs" / f"{spec_name}.source").read_text(encoding="utf-8")
        )
        producers.append(
            {
                "product": product,
                "audience": surface["products"][product]["audience"],
                "envVar": surface["products"][product]["envVar"],
                "spec": f"specs/{spec_name}",
                "sourceRepo": lock["source_repo"],
                "sourceBranch": lock["source_branch"],
                "sourceCommit": lock["source_commit"],
                "sourceSha256": lock["source_sha256"],
            }
        )
        upstream = upstream_operations(spec)
        native_surface = (
            PAYMENTS_NATIVE_OPERATIONS
            if product == "temperaPayments"
            else surface["operations"][product]
        )
        for op in native_surface:
            upstream_operation = upstream[op["upstreamOperationId"]]
            if product == "temperaPayments":
                validate_payment_mapping(op, upstream_operation)
            request_descriptor = {
                "method": op["method"],
                "path": op["path"],
                "pathParams": op.get("pathParams", []),
                "query": op.get("query", []),
                "requiredQuery": op.get("requiredQuery", []),
                "headers": op.get("headers", []),
                "requiredHeaders": op.get("requiredHeaders", []),
                "body": op.get("body", []),
                "requiredBody": op.get("requiredBody", []),
                "requestBodyKind": op.get("requestBodyKind", "none"),
                "requestContentType": op.get("requestContentType"),
            }
            operations.append(
                {
                    "operation": f"{product}.{op['id']}",
                    "product": product,
                    "id": op["id"],
                    "upstreamOperationId": op["upstreamOperationId"],
                    "method": op["method"],
                    "pathTemplate": op["path"],
                    "pathShape": path_shape(op["path"]),
                    "authAudience": op.get("authAudience"),
                    "scope": op.get("scope"),
                    "safeRetry": op["safeRetry"],
                    "headers": op.get("headers", []),
                    "requiredHeaders": op.get("requiredHeaders", []),
                    "requestDigest": digest(request_descriptor),
                    "responseDigest": digest(response_schema(spec, upstream_operation)),
                }
            )
    return {
        "schema_version": 1,
        "contract": "tempera.native-transport/v1",
        "$comment": (
            "Method, path template, auth audience, and request/response digests "
            "for every operation a hand-written native client may call. "
            "Generated by scripts/check-native-transport.py from surface.json "
            "and the vendored producer contracts; each producer below records the "
            "exact mainline commit its vendored contract was locked to."
        ),
        "surfaceVersion": surface["version"],
        "producers": producers,
        "operations": sorted(operations, key=lambda entry: entry["operation"]),
    }


def rendered(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, ensure_ascii=False) + "\n"


def literal_path_shapes(line: str) -> list[str]:
    """Normalized route shapes for every string literal on one source line."""
    shapes: list[str] = []
    for match in STRING_LITERAL_RE.finditer(line):
        literal = match.group(1)
        shape = INTERPOLATION_RE.sub("{}", literal)
        if not shape.startswith("/"):
            shape = "/" + shape
        shapes.append(shape)
    return shapes


def check_client(path: Path, contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        return [f"cannot read native client {path}: {error}"]
    indexed = {entry["operation"]: entry for entry in contract["operations"]}
    annotated_lines: set[int] = set()
    for number, line in enumerate(lines, 1):
        match = ANNOTATION_RE.search(line)
        if match is None:
            continue
        label = f"{path.name}:{number}"
        name = f"{match.group('product')}.{match.group('operation')}"
        entry = indexed.get(name)
        if entry is None:
            failures.append(f"{label}: {name} is not an admitted native operation")
            continue
        if match.group("method") != entry["method"]:
            failures.append(
                f"{label}: {name} declares {match.group('method')}, "
                f"contract says {entry['method']}"
            )
        if match.group("path") != entry["pathTemplate"]:
            failures.append(
                f"{label}: {name} declares path {match.group('path')}, "
                f"contract says {entry['pathTemplate']}"
            )
        # The annotation must sit directly above real code carrying the route.
        follower = next(
            (
                index
                for index in range(number, min(number + 4, len(lines)))
                if lines[index].strip()
            ),
            None,
        )
        if follower is None:
            failures.append(f"{label}: {name} annotates no call site")
            continue
        annotated_lines.add(follower + 1)
        shapes = literal_path_shapes(lines[follower])
        if entry["pathShape"] not in shapes:
            failures.append(
                f"{path.name}:{follower + 1}: {name} call site path "
                f"{shapes or ['<no string literal>']} != {entry['pathShape']}"
            )
    for number, line in enumerate(lines, 1):
        if number in annotated_lines or ANNOTATION_RE.search(line):
            continue
        for shape in literal_path_shapes(line):
            if any(shape.startswith(prefix) for prefix in CANONICAL_PREFIXES):
                failures.append(
                    f"{path.name}:{number}: undeclared canonical route {shape}; "
                    "add a tempera-transport annotation above the call site"
                )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="regenerate the contract")
    parser.add_argument(
        "--client",
        type=Path,
        action="append",
        default=[],
        help="native client source file to validate; repeatable",
    )
    args = parser.parse_args()
    try:
        contract = build_contract()
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"native transport contract build failed: {error}", file=sys.stderr)
        return 2
    if args.write:
        CONTRACT.write_text(rendered(contract), encoding="utf-8")
        print(
            f"wrote {CONTRACT.relative_to(ROOT)} "
            f"({len(contract['operations'])} operations)"
        )
        return 0
    failures: list[str] = []
    if not CONTRACT.exists():
        failures.append("contracts/native-transport-v1.json is missing")
    elif CONTRACT.read_text(encoding="utf-8") != rendered(contract):
        failures.append(
            "contracts/native-transport-v1.json is stale "
            "(run scripts/check-native-transport.py --write)"
        )
    for client in args.client:
        failures.extend(check_client(client, contract))
    if failures:
        print(f"native transport check failed ({len(failures)}):", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    checked = ", ".join(client.name for client in args.client) or "contract only"
    print(
        f"native transport check passed: {len(contract['operations'])} published "
        f"operations; {checked}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
