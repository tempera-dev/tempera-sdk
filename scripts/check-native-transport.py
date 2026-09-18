#!/usr/bin/env python3
"""Publish and enforce the native transport contract.

The Kotlin and Swift clients in tempera-mobile and tempera-iOS do not consume
the generated SDK packages: they hand-write their call sites. Nothing otherwise
stops one of them from drifting off the producer's canonical route, sending an
operation under the wrong audience, or keeping a stale request shape after the
producer contract moves.

`contracts/native-transport-v1.json` closes that gap. For every admitted
operation it publishes the method, the path template, the auth audience and
scope, and a request and response digest derived from the vendored producer
contract. This script both writes that file and checks a native client against
it.

Six producers are admitted. tempera-dropshipping and tempera-business publish
every operation surface.json carries for them. tempera-payments publishes only
the merchant onboarding seam named in PAYMENTS_NATIVE_OPERATIONS, each entry
validated against the producer's wire metadata. The control plane publishes only
the seven account reads named in CONTROL_PLANE_NATIVE_OPERATIONS, under the
tempera-account audience and the account:read scope the device plane declares.
tempera-voice publishes only
the phone-relevant session, pending-action, and agent operations named in
NATIVE_OPERATIONS (no eval, artifact, agent-authoring, or export routes) plus
one synthetic WebSocket operation, `temperaVoice.streamVoiceSession`, taken
from the contract's top-level `x-tempera-websocket-contract`: method `WSS`,
the contract's path, audience, and required scope, and both digests computed
over that websocket contract object itself.
tempera-workflows publishes only the four reads named in NATIVE_OPERATIONS
(workflows.list, workflows.get, runs.list, runs.get). Starting a run is
deliberately absent: runs.create and workflows.call carry the workflow:run
scope, so a device never holds them, and the assistant harness starts a run
behind an approval card instead.

Usage:
  python3 scripts/check-native-transport.py --write        # regenerate
  python3 scripts/check-native-transport.py                # fail if stale
  python3 scripts/check-native-transport.py --client PATH  # check call sites

A native call site declares itself with an annotation comment placed
immediately above the call:

    // tempera-transport: temperaDropshipping.listInbox GET /v1/organizations/...
    // tempera-transport: temperaVoice.streamVoiceSession WSS /v1/sessions/{session_id}/stream

The checker requires that the annotation names a published operation, that the
method and path template match the contract exactly, and that the very next
code line carries a string literal whose interpolated path shape is that same
route. A `WSS` annotation is checked exactly like an HTTP one. It also requires
that every literal reaching into a producer's canonical namespace
(NATIVE_NAMESPACES: `/v1/organizations` for dropshipping; `/v1/operating-state`,
`/v1/business-profile`, and `/v1/cases` for business; `/v1/merchants` for
payments; `/v1/sessions`, `/v1/agents`, and `/v1/actions` for voice;
`/v1/workflows` and `/v1/runs` for workflows; `/v1/me`,
`/v1/billing`, `/v1/usage`, and `/v1/team` for the control plane, whose
`/v1/sessions` account read stays under the voice root the two products share)
is annotated, so a new hand-written call cannot slip in undeclared.
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
NATIVE_PRODUCTS = (
    "temperaDropshipping",
    "temperaBusiness",
    "temperaPayments",
    "temperaVoice",
    "temperaWorkflows",
    "controlPlane",
)
PRODUCT_SPECS = {
    "temperaDropshipping": "tempera-dropshipping.openapi.json",
    "temperaBusiness": "tempera-business.openapi.json",
    "temperaPayments": "tempera-payments.openapi.json",
    "temperaVoice": "tempera-voice.openapi.json",
    "temperaWorkflows": "tempera-workflows.openapi.json",
    "controlPlane": "control-plane.openapi.json",
}
# surface.json carries no single audience for the control plane: most of its
# routes answer an account session rather than a resource token. The native
# device plane is the one audience it publishes, so name it here and pin it
# against the vendored contract's own audience and scope enums.
PRODUCT_AUDIENCES = {"controlPlane": "tempera-account"}
# Operations each product publishes to the phones, by surface.json id. None
# means every operation surface.json carries for the product. An allowlisted
# id that surface.json no longer carries fails the build rather than silently
# shrinking the published set. temperaPayments is bounded by the explicit
# PAYMENTS_NATIVE_OPERATIONS mapping below instead of by surface.json.
NATIVE_OPERATIONS: dict[str, frozenset[str] | None] = {
    "temperaDropshipping": None,
    "temperaBusiness": None,
    "temperaPayments": None,
    "controlPlane": None,
    "temperaVoice": frozenset(
        {
            "createVoiceSession",
            "getVoiceSession",
            "listVoiceSessions",
            "listVoiceSessionActions",
            "listVoiceSessionEvents",
            "endVoiceSession",
            "resolveVoiceAction",
            "listVoiceAgents",
            "getDefaultVoiceAgent",
        }
    ),
    # Reads only. workflow:run never reaches a device: runs.create and
    # workflows.call stay with the assistant harness behind an approval.
    "temperaWorkflows": frozenset(
        {
            "listWorkflows",
            "getWorkflow",
            "listRuns",
            "getRun",
        }
    ),
}
# Producers whose vendored OpenAPI carries a top-level
# x-tempera-websocket-contract the phones consume directly. Each is published
# as one synthetic operation with this method.
WEBSOCKET_PRODUCTS = ("temperaVoice",)
WEBSOCKET_CONTRACT_KEY = "x-tempera-websocket-contract"
WEBSOCKET_METHOD = "WSS"
# Route roots a hand-written client may only name from an annotated call site.
# A literal matches a root when it equals it or continues it with "/" or ":".
NATIVE_NAMESPACES: dict[str, tuple[str, ...]] = {
    "temperaDropshipping": ("/v1/organizations",),
    "temperaBusiness": ("/v1/operatingState", "/v1/businessProfile", "/v1/cases"),
    "temperaPayments": ("/v1/merchants",),
    "temperaVoice": ("/v1/sessions", "/v1/agents", "/v1/actions"),
    "temperaWorkflows": ("/v1/workflows", "/v1/runs"),
    "controlPlane": ("/v1/me", "/v1/billing", "/v1/usage", "/v1/team"),
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
        "query": ["tenantId"],
        "requiredQuery": ["tenantId"],
        "safeRetry": "read",
        "authAudience": "tempera-payments",
        "scope": "payments:merchants:read",
    },
    {
        "id": "createMerchant",
        "upstreamOperationId": "createMerchant",
        "method": "POST",
        "path": "/v1/merchants",
        "body": ["tenantId", "country", "currency", "category"],
        "requiredBody": ["tenantId", "country", "currency", "category"],
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
        "path": "/v1/merchants/{merchantId}",
        "pathParams": ["merchantId"],
        "query": ["tenantId"],
        "requiredQuery": ["tenantId"],
        "safeRetry": "read",
        "authAudience": "tempera-payments",
        "scope": "payments:merchants:read",
    },
    {
        "id": "refreshMerchantEligibility",
        "upstreamOperationId": "refreshMerchantEligibility",
        "method": "POST",
        "path": "/v1/merchants/{merchantId}/refresh",
        "pathParams": ["merchantId"],
        "body": ["tenantId"],
        "requiredBody": ["tenantId"],
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
        "path": "/v1/merchants/{merchantId}/onboarding",
        "pathParams": ["merchantId"],
        "body": ["tenantId"],
        "requiredBody": ["tenantId"],
        "requestBodyKind": "json",
        "requestContentType": "application/json",
        "safeRetry": "none",
        "authAudience": "tempera-payments",
        "scope": "payments:merchants:write",
        "headers": ["Idempotency-Key"],
        "requiredHeaders": ["Idempotency-Key"],
    },
)

# The account plane the phones read. auth-hub accepts the device scope
# account:read on exactly these seven GETs alongside the account-session
# permission each route already required, so the reads are declared here rather
# than taken from surface.json, which carries neither the audience nor the
# device scope for them. Every entry is still pinned to the producer's method,
# path, query and header metadata, and the audience and scope are pinned to the
# vendored contract's ResourceAudience, Scope and TemperaMobileAudience enums.
CONTROL_PLANE_AUDIENCE = "tempera-account"
CONTROL_PLANE_SCOPE = "account:read"
CONTROL_PLANE_NATIVE_OPERATIONS = (
    {
        "id": "getMe",
        "upstreamOperationId": "getMe",
        "method": "GET",
        "path": "/v1/me",
        "safeRetry": "read",
        "authAudience": CONTROL_PLANE_AUDIENCE,
        "scope": CONTROL_PLANE_SCOPE,
        "headers": ["X-Tempera-Reference-Request-Id"],
        "requiredHeaders": [],
    },
    {
        "id": "getBillingStatus",
        "upstreamOperationId": "getBillingStatus",
        "method": "GET",
        "path": "/v1/billing/status",
        "safeRetry": "read",
        "authAudience": CONTROL_PLANE_AUDIENCE,
        "scope": CONTROL_PLANE_SCOPE,
    },
    {
        "id": "getBillingPricing",
        "upstreamOperationId": "getBillingPricing",
        "method": "GET",
        "path": "/v1/billing/pricing",
        "safeRetry": "read",
        "authAudience": CONTROL_PLANE_AUDIENCE,
        "scope": CONTROL_PLANE_SCOPE,
    },
    {
        "id": "getBillingCredits",
        "upstreamOperationId": "getBillingCredits",
        "method": "GET",
        "path": "/v1/billing/credits",
        "safeRetry": "read",
        "authAudience": CONTROL_PLANE_AUDIENCE,
        "scope": CONTROL_PLANE_SCOPE,
    },
    {
        "id": "usageSummary.get",
        "upstreamOperationId": "usageSummary.get",
        "method": "GET",
        "path": "/v1/usage/summary",
        "query": [
            "granularity",
            "groupBy",
            "from",
            "to",
            "projectId",
            "environmentId",
            "productId",
            "operation",
            "metric",
            "section",
            "pageSize",
            "pageToken",
        ],
        "requiredQuery": [],
        "safeRetry": "read",
        "authAudience": CONTROL_PLANE_AUDIENCE,
        "scope": CONTROL_PLANE_SCOPE,
    },
    {
        "id": "listTeamMembers",
        "upstreamOperationId": "listTeamMembers",
        "method": "GET",
        "path": "/v1/team/members",
        "query": ["pageSize", "pageToken"],
        "requiredQuery": [],
        "safeRetry": "read",
        "authAudience": CONTROL_PLANE_AUDIENCE,
        "scope": CONTROL_PLANE_SCOPE,
    },
    {
        "id": "listAccountSessions",
        "upstreamOperationId": "listAccountSessions",
        "method": "GET",
        "path": "/v1/sessions",
        "query": ["pageSize", "pageToken"],
        "requiredQuery": [],
        "safeRetry": "read",
        "authAudience": CONTROL_PLANE_AUDIENCE,
        "scope": CONTROL_PLANE_SCOPE,
    },
)

# Producers bounded by an explicit mapping here instead of by surface.json.
EXPLICIT_NATIVE_SURFACES = {
    "temperaPayments": PAYMENTS_NATIVE_OPERATIONS,
    "controlPlane": CONTROL_PLANE_NATIVE_OPERATIONS,
}

PARAM_RE = re.compile(r"\{[^}]+\}")
ANNOTATION_RE = re.compile(
    r"tempera-transport:\s*(?P<product>[A-Za-z][A-Za-z0-9]*)\."
    # Dots are allowed in the operation: the control plane publishes ids such as
    # usageSummary.get, and a call site must be able to name them.
    r"(?P<operation>[A-Za-z][A-Za-z0-9.]*)\s+(?P<method>[A-Z]+)\s+(?P<path>/\S+)\s*$"
)
STRING_LITERAL_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')
# Kotlin "$name" / "${expr}" and Swift "\(expr)" interpolations.
INTERPOLATION_RE = re.compile(r"\\\([^)]*\)|\$\{[^}]*\}|\$[A-Za-z_][A-Za-z0-9_]*")


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
                    "_query": [resolve(spec, p) for p in [*(item.get("parameters") or []), *(operation.get("parameters") or [])] if resolve(spec, p).get("in") == "query"],
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


def enum_values(spec: dict[str, Any], schema: str, *path: str) -> list[Any]:
    node: Any = (spec.get("components") or {}).get("schemas", {}).get(schema)
    for key in path:
        node = resolve(spec, (node or {}).get("properties", {}).get(key, {}))
    node = resolve(spec, node or {})
    if node.get("type") == "array":
        node = resolve(spec, node.get("items") or {})
    values = node.get("enum")
    return values if isinstance(values, list) else []


def validate_control_plane_mapping(
    op: dict[str, Any], upstream_operation: dict[str, Any], spec: dict[str, Any]
) -> None:
    """Keep the bounded account reads tied to the producer's wire metadata.

    The routes carry an account permission, not the device scope, so the
    audience and scope cannot be read off the operation. They are pinned
    instead to the enums the vendored contract publishes: the registered
    resource audiences, the scope vocabulary, and the device plane's own
    per-audience scope list.
    """
    if upstream_operation["_method"] != op["method"] or upstream_operation["_path"] != op["path"]:
        raise ValueError(f"Control-plane native mapping drifts from OpenAPI for {op['id']}")
    if op["method"] != "GET" or op["safeRetry"] != "read":
        raise ValueError(f"Control-plane native operation {op['id']} is not a read")
    query = upstream_operation.get("_query", [])
    if list(op.get("query", [])) != [p["name"] for p in query]:
        raise ValueError(f"Control-plane native query drifts for {op['id']}")
    if set(op.get("requiredQuery", [])) != {p["name"] for p in query if p.get("required") is True}:
        raise ValueError(f"Control-plane native required query drifts for {op['id']}")
    headers = upstream_operation.get("_headers", [])
    if list(op.get("headers", [])) != [p["name"] for p in headers]:
        raise ValueError(f"Control-plane native headers drift for {op['id']}")
    if set(op.get("requiredHeaders", [])) != {p["name"] for p in headers if p.get("required") is True}:
        raise ValueError(f"Control-plane native required headers drift for {op['id']}")
    if op["authAudience"] not in enum_values(spec, "ResourceAudience"):
        raise ValueError(
            f"Control-plane native audience {op['authAudience']!r} is not a "
            "registered resource audience"
        )
    if op["scope"] not in enum_values(spec, "Scope"):
        raise ValueError(
            f"Control-plane native scope {op['scope']!r} is not in the producer's "
            "scope vocabulary"
        )
    device_audiences = enum_values(spec, "TemperaMobileAudience", "oauth_resource_audience")
    device_scopes = enum_values(spec, "TemperaMobileAudience", "scopes")
    if op["authAudience"] not in device_audiences or op["scope"] not in device_scopes:
        raise ValueError(
            f"Control-plane native {op['id']} names an audience or scope the "
            "device plane does not publish"
        )


def websocket_operation(
    product: str, spec: dict[str, Any], audience: str
) -> dict[str, Any]:
    """The synthetic WSS operation published from a producer's websocket contract."""
    contract = spec.get(WEBSOCKET_CONTRACT_KEY)
    if not isinstance(contract, dict):
        raise ValueError(f"{product}: vendored contract has no {WEBSOCKET_CONTRACT_KEY}")
    operation_id = contract.get("operationId")
    path = contract.get("path")
    ws_audience = contract.get("x-tempera-auth-audience")
    scope = contract.get("x-tempera-required-scope")
    if not isinstance(operation_id, str) or not operation_id:
        raise ValueError(f"{product}: {WEBSOCKET_CONTRACT_KEY} names no operationId")
    if not isinstance(path, str) or not path.startswith("/"):
        raise ValueError(f"{product}: {WEBSOCKET_CONTRACT_KEY} names no absolute path")
    if ws_audience != audience:
        raise ValueError(
            f"{product}: {WEBSOCKET_CONTRACT_KEY} audience {ws_audience!r} "
            f"differs from the product audience {audience!r}"
        )
    if not isinstance(scope, str) or not scope:
        raise ValueError(f"{product}: {WEBSOCKET_CONTRACT_KEY} names no required scope")
    return {
        "operation": f"{product}.{operation_id}",
        "product": product,
        "id": operation_id,
        "upstreamOperationId": operation_id,
        "method": WEBSOCKET_METHOD,
        "pathTemplate": path,
        "pathShape": path_shape(path),
        "authAudience": ws_audience,
        "scope": scope,
        "safeRetry": "none",
        "headers": [],
        "requiredHeaders": [],
        "requestDigest": digest(contract),
        "responseDigest": digest(contract),
    }


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
        audience = PRODUCT_AUDIENCES.get(
            product, surface["products"][product]["audience"]
        )
        producers.append(
            {
                "product": product,
                "audience": audience,
                "envVar": surface["products"][product]["envVar"],
                "spec": f"specs/{spec_name}",
                "sourceRepo": lock["source_repo"],
                "sourceBranch": lock["source_branch"],
                "sourceCommit": lock["source_commit"],
                "sourceSha256": lock["source_sha256"],
            }
        )
        upstream = upstream_operations(spec)
        native_surface = EXPLICIT_NATIVE_SURFACES.get(
            product, surface["operations"][product]
        )
        allowed = NATIVE_OPERATIONS[product]
        published: set[str] = set()
        for op in native_surface:
            if allowed is not None and op["id"] not in allowed:
                continue
            published.add(op["id"])
            upstream_operation = upstream[op["upstreamOperationId"]]
            if product == "temperaPayments":
                validate_payment_mapping(op, upstream_operation)
            elif product == "controlPlane":
                validate_control_plane_mapping(op, upstream_operation, spec)
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
        if allowed is not None:
            missing = sorted(allowed - published)
            if missing:
                raise ValueError(
                    f"{product}: allowlisted operations missing from surface.json: "
                    f"{missing}"
                )
        if product in WEBSOCKET_PRODUCTS:
            stream = websocket_operation(product, spec, audience)
            if stream["id"] in published:
                raise ValueError(
                    f"{product}: websocket operation {stream['id']} collides with "
                    "an HTTP operation"
                )
            operations.append(stream)
    return {
        "schema_version": 1,
        "contract": "tempera.native-transport/v1",
        "$comment": (
            "Method, path template, auth audience, and request/response digests "
            "for every operation a hand-written native client may call. "
            "Generated by scripts/check-native-transport.py from surface.json "
            "and the vendored producer contracts; each producer below records the "
            "exact mainline commit its vendored contract was locked to. Method "
            "WSS marks the synthetic WebSocket operation published from the "
            "producer's x-tempera-websocket-contract; both of its digests cover "
            "that contract object."
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


def in_namespace(shape: str, root: str) -> bool:
    root = root.rstrip("/")
    return shape == root or shape.startswith(root + "/") or shape.startswith(root + ":")


def namespace_owner(shape: str) -> str | None:
    """The product whose canonical namespace a route shape reaches into, if any."""
    for product, roots in NATIVE_NAMESPACES.items():
        if any(in_namespace(shape, root) for root in roots):
            return product
    return None


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
            owner = namespace_owner(shape)
            if owner is not None:
                failures.append(
                    f"{path.name}:{number}: undeclared {owner} route {shape}; "
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
