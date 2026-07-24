#!/usr/bin/env python3
"""Lock the source-pinned Palette signed-evaluation operations used by the SDK.

The SDK exposes only real hosted methods. This lock is derived from Palette's
generated OpenAPI and binds the exact source revision, artifact digest,
operation IDs, request/receipt schemas, failure responses, and SDK surface.

Usage:
  python3 scripts/sync-palette-eval-openapi.py
  python3 scripts/sync-palette-eval-openapi.py --check
  python3 scripts/sync-palette-eval-openapi.py --check \
    --source /path/to/palette/sdks/openapi/palette-api.json \
    --source-checkout /path/to/palette
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "contracts" / "palette-eval-openapi-operations.json"
DEFAULT_SOURCE = ROOT / "specs" / "palette-api.json"
SURFACE = ROOT / "surface.json"

PALETTE_REPOSITORY = "https://github.com/tempera-dev/palette"
PALETTE_REVISION = "55532b2cf3fb1b228b4d6620a3aa88899c262f12"
PALETTE_SOURCE_PATH = "sdks/openapi/palette-api.json"
PALETTE_SOURCE_BLOB = "32e5aed508a963fdd4e7af153c81190475beeac8"
PALETTE_SOURCE_SHA256 = (
    "sha256:18942d5e2c26332b40050cda5a882540f14d914d717d5b94342a0afb72001dd0"
)
PALETTE_REVIEW_URL = "https://github.com/tempera-dev/palette/pull/16"
PALETTE_AVAILABILITY = "merged_main"
PALETTE_SCOPE = "eval:run"
REQUEST_SCHEMA = "#/components/schemas/ImportTemperaEvidenceRequest"
RECEIPT_SCHEMA = "#/components/schemas/TemperaEvidenceReceipt"
REQUEST_FIELDS = ["canonical_json", "public_key_pem", "signature_base64"]
REQUIRED_REQUEST_FIELDS = ["canonical_json", "signature_base64", "public_key_pem"]
IMPORT_RESPONSE_CODES = ["200", "400", "401", "403", "409", "413", "422", "503"]
RECEIPT_RESPONSE_CODES = ["200", "400", "401", "403", "404"]

OPERATIONS = [
    {
        "sdkOperationId": "importTemperaBundle",
        "operationId": "evalResults.importTemperaBundle",
        "method": "POST",
        "path": "/v1/eval-results/{tenant_id}/{project_id}/tempera/bundles",
        "pathParams": ["tenant_id", "project_id"],
        "body": REQUEST_FIELDS,
        "requiredBody": REQUIRED_REQUEST_FIELDS,
        "responseCodes": IMPORT_RESPONSE_CODES,
    },
    {
        "sdkOperationId": "recordTemperaDecision",
        "operationId": "evalResults.recordTemperaDecision",
        "method": "POST",
        "path": "/v1/eval-results/{tenant_id}/{project_id}/tempera/decisions",
        "pathParams": ["tenant_id", "project_id"],
        "body": REQUEST_FIELDS,
        "requiredBody": REQUIRED_REQUEST_FIELDS,
        "responseCodes": IMPORT_RESPONSE_CODES,
    },
    {
        "sdkOperationId": "getTemperaEvidence",
        "operationId": "evalResults.getTemperaEvidence",
        "method": "GET",
        "path": (
            "/v1/eval-results/{tenant_id}/{project_id}/tempera/"
            "{kind}/{external_id}"
        ),
        "pathParams": ["tenant_id", "project_id", "kind", "external_id"],
        "body": [],
        "requiredBody": [],
        "responseCodes": RECEIPT_RESPONSE_CODES,
    },
]


class ContractError(ValueError):
    """The vendored or source-checkout Palette contract differs from its pin."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def schema_ref(value: Any, location: str) -> str:
    try:
        reference = value["content"]["application/json"]["schema"]["$ref"]
    except (KeyError, TypeError) as error:
        raise ContractError(f"Palette OpenAPI omits {location} JSON schema") from error
    if not isinstance(reference, str):
        raise ContractError(f"Palette OpenAPI {location} schema ref is invalid")
    return reference


def git_read(checkout: Path, arguments: list[str], purpose: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(checkout), *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ContractError(f"Palette source {purpose} failed: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "git failed"
        raise ContractError(f"Palette source {purpose} failed: {detail}")
    return result.stdout.strip()


def canonical_repository(url: str) -> str:
    value = url.strip().removesuffix(".git")
    for prefix in ("https://github.com/", "http://github.com/", "git@github.com:"):
        if value.startswith(prefix):
            return value[len(prefix) :]
    return value


def verify_source_checkout(source: Path, checkout: Path) -> None:
    checkout = checkout.resolve()
    expected_source = (checkout / PALETTE_SOURCE_PATH).resolve()
    if not checkout.is_dir() or source.resolve() != expected_source:
        raise ContractError(
            "Palette OpenAPI must be the pinned path inside the supplied checkout"
        )
    if git_read(checkout, ["rev-parse", "HEAD"], "revision read") != PALETTE_REVISION:
        raise ContractError("Palette checkout revision differs from the source pin")
    origin = git_read(checkout, ["remote", "get-url", "origin"], "origin read")
    if canonical_repository(origin) != canonical_repository(PALETTE_REPOSITORY):
        raise ContractError("Palette checkout origin differs from the source pin")
    if git_read(
        checkout,
        ["status", "--porcelain", "--", PALETTE_SOURCE_PATH],
        "artifact status",
    ):
        raise ContractError("Palette OpenAPI artifact has uncommitted changes")


def render(source: Path, *, source_checkout: Path | None = None) -> str:
    if not source.is_file():
        raise ContractError(f"Palette OpenAPI source is missing: {source}")
    observed_digest = sha256(source)
    if observed_digest != PALETTE_SOURCE_SHA256:
        raise ContractError(
            "Palette OpenAPI digest differs from the source pin "
            f"(observed {observed_digest})"
        )
    if source_checkout is not None:
        verify_source_checkout(source, source_checkout)

    document = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not str(document.get("openapi", "")).startswith(
        "3."
    ):
        raise ContractError("Palette contract must be an OpenAPI 3 document")
    paths = document.get("paths")
    if not isinstance(paths, dict):
        raise ContractError("Palette OpenAPI paths must be an object")

    locked_operations: list[dict[str, Any]] = []
    for expected in OPERATIONS:
        path_item = paths.get(expected["path"])
        operation = (
            path_item.get(expected["method"].lower())
            if isinstance(path_item, dict)
            else None
        )
        if not isinstance(operation, dict):
            raise ContractError(
                f"Palette OpenAPI omits {expected['method']} {expected['path']}"
            )
        if operation.get("operationId") != expected["operationId"]:
            raise ContractError(
                f"Palette operation ID for {expected['path']} differs from the pin"
            )
        if expected["method"] == "POST":
            request_body = operation.get("requestBody")
            if (
                not isinstance(request_body, dict)
                or request_body.get("required") is not True
                or schema_ref(request_body, f"{expected['operationId']} request")
                != REQUEST_SCHEMA
            ):
                raise ContractError(
                    f"Palette request contract for {expected['operationId']} differs"
                )
        responses = operation.get("responses")
        if not isinstance(responses, dict) or sorted(responses) != sorted(
            expected["responseCodes"]
        ):
            raise ContractError(
                f"Palette response codes for {expected['operationId']} differ"
            )
        if schema_ref(
            responses.get("200"), f"{expected['operationId']} success response"
        ) != RECEIPT_SCHEMA:
            raise ContractError(
                f"Palette receipt contract for {expected['operationId']} differs"
            )
        locked_operations.append(dict(expected))

    components = document.get("components")
    schemas = components.get("schemas") if isinstance(components, dict) else None
    request_schema = (
        schemas.get("ImportTemperaEvidenceRequest")
        if isinstance(schemas, dict)
        else None
    )
    receipt_schema = (
        schemas.get("TemperaEvidenceReceipt") if isinstance(schemas, dict) else None
    )
    required = request_schema.get("required") if isinstance(request_schema, dict) else None
    properties = (
        request_schema.get("properties") if isinstance(request_schema, dict) else None
    )
    if (
        not isinstance(required, list)
        or sorted(required) != sorted(REQUEST_FIELDS)
        or not isinstance(properties, dict)
        or sorted(properties) != sorted(REQUEST_FIELDS)
    ):
        raise ContractError("Palette import request fields differ from the pin")
    receipt_properties = (
        receipt_schema.get("properties") if isinstance(receipt_schema, dict) else None
    )
    required_receipt_fields = {
        "declared_content_sha256",
        "signed_payload_sha256",
        "signature_sha256",
        "public_key_sha256",
        "summary",
    }
    if (
        not isinstance(receipt_properties, dict)
        or not required_receipt_fields.issubset(receipt_properties)
        or set(REQUEST_FIELDS) & set(receipt_properties)
    ):
        raise ContractError("Palette receipt evidence fields differ from the pin")

    surface = json.loads(SURFACE.read_text(encoding="utf-8"))
    palette_operations = surface.get("operations", {}).get("palette", [])
    indexed_surface = {
        operation.get("id"): operation
        for operation in palette_operations
        if isinstance(operation, dict)
    }
    for expected in OPERATIONS:
        observed = indexed_surface.get(expected["sdkOperationId"])
        if not isinstance(observed, dict):
            raise ContractError(
                f"SDK surface omits palette.{expected['sdkOperationId']}"
            )
        bindings = {
            "method": expected["method"],
            "path": expected["path"],
            "auth": "product",
            "pathParams": expected["pathParams"],
            "body": expected["body"],
            "requiredBody": expected["requiredBody"],
            "scope": PALETTE_SCOPE,
        }
        for field, expected_value in bindings.items():
            empty_default = [] if field in {"body", "requiredBody"} else None
            observed_value = observed.get(field, empty_default)
            if observed_value != expected_value:
                raise ContractError(
                    f"SDK palette.{expected['sdkOperationId']}.{field} differs "
                    "from generated Palette OpenAPI"
                )

    lock = {
        "schemaVersion": 1,
        "repository": PALETTE_REPOSITORY,
        "revision": PALETTE_REVISION,
        "sourcePath": PALETTE_SOURCE_PATH,
        "sourceBlob": PALETTE_SOURCE_BLOB,
        "sourceSha256": PALETTE_SOURCE_SHA256,
        "reviewUrl": PALETTE_REVIEW_URL,
        "availability": PALETTE_AVAILABILITY,
        "requiredScope": PALETTE_SCOPE,
        "requestSchema": REQUEST_SCHEMA,
        "receiptSchema": RECEIPT_SCHEMA,
        "operations": locked_operations,
    }
    return json.dumps(lock, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--source-checkout", type=Path)
    args = parser.parse_args()
    try:
        expected = render(args.source.resolve(), source_checkout=args.source_checkout)
    except (ContractError, OSError, json.JSONDecodeError) as error:
        print(f"Palette evaluation OpenAPI sync failed: {error}", file=sys.stderr)
        return 1
    if args.check:
        actual = LOCK.read_text(encoding="utf-8") if LOCK.exists() else ""
        if actual != expected:
            print(
                "Palette evaluation OpenAPI lock is stale; run "
                "python3 scripts/sync-palette-eval-openapi.py",
                file=sys.stderr,
            )
            return 1
        print(
            "Palette evaluation OpenAPI lock passed "
            f"({len(OPERATIONS)} source-pinned operations)"
        )
        return 0
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(expected, encoding="utf-8")
    print(f"wrote {LOCK.relative_to(ROOT)} ({len(OPERATIONS)} operations)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
