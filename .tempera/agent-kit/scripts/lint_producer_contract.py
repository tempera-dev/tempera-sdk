#!/usr/bin/env python3
"""Lint one producer's OpenAPI contract against the Tempera contract standard.

This runs in the producer's own repository, before the contract is ever
published, using the identical rule engine the SDK runs over the aggregate
vendored surface (`scripts/aip_rules.py`). A contract that passes here cannot
fail once it is vendored, which is the whole point of having one engine.

    python3 lint_producer_contract.py --product temperaVoice contracts/openapi/voice.openapi.json

Beyond the AIP rules it enforces the format half of the standard: OpenAPI
3.1.0, canonical JSON serialization, the byte-identical google.rpc.Status
components, honest protocol-route declarations, and the x-tempera-* extensions
the SDK generator needs in order to emit a typed client at all.

See docs/CONTRACT_STANDARD.md for the normative text.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from aip_rules import (  # noqa: E402  (path is set immediately above)
    HTTP_METHODS,
    Exemptions,
    discover_violations,
)

HERE = Path(__file__).resolve().parent
REQUIRED_OPENAPI = "3.1.0"
AUTH_KINDS = {"none", "account", "product", "oauthResource", "introspectionSecret"}
# Health, transport, and identity-protocol routes are the only shapes that may
# be declared exempt. Anything else is a resource API and answers to AIP.
EXEMPTIBLE = re.compile(
    r"^/(healthz|readyz|livez|metrics|mcp|bidi|openapi\.json)$"
    r"|^/\.well-known/"
    r"|^/oauth/"
    # A versioned webhook collection is a legitimate receiver shape; without
    # this, producers were renaming /v1/webhooks/stripe just to get past the
    # exemption check, which is churn, not conformance.
    r"|^/v1/webhooks/"
    r"|webhook$|/callback$|^/v1/otlp/|/events$"
)


def canonical_status_components() -> dict[str, Any]:
    """The one true error envelope, resolved from wherever this script lives."""
    for candidate in (
        HERE.parent / "contracts" / "status-component.json",
        HERE / "status-component.json",
    ):
        if candidate.is_file():
            return json.loads(candidate.read_text(encoding="utf-8"))
    raise SystemExit("status-component.json is missing next to this script")


def serialization_issues(path: Path, document: dict[str, Any]) -> list[str]:
    expected = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    if path.read_text(encoding="utf-8") != expected:
        return [
            "file is not canonically serialized: rewrite it with "
            "json.dumps(document, indent=2, ensure_ascii=False) plus a trailing newline"
        ]
    return []


def component_issues(document: dict[str, Any]) -> list[str]:
    canonical = canonical_status_components()
    components = document.get("components") or {}
    issues: list[str] = []
    observed_schema = (components.get("schemas") or {}).get("Status")
    if observed_schema != canonical["schemas"]["Status"]:
        issues.append(
            "components.schemas.Status differs from contracts/status-component.json"
        )
    observed_response = (components.get("responses") or {}).get("Error")
    if observed_response != canonical["responses"]["Error"]:
        issues.append(
            "components.responses.Error differs from contracts/status-component.json"
        )
    return issues


def reference_issues(document: dict[str, Any]) -> list[str]:
    """Every local $ref must resolve inside this document.

    A contract that points at a component it does not define is broken for
    every consumer, but it looks fine to a schema-shape reviewer and it looks
    fine to the AIP rules. tempera-connectors shipped four such references --
    utoipa emitted fully-qualified `crate.models.X` names for request bodies
    it had registered under their short names -- and nothing noticed until the
    SDK tried to derive typed operations from it and could not.
    """
    # Only document-root OpenAPI pointers are checked. A bare "#/$defs/x"
    # inside an embedded JSON Schema resolves against that schema resource,
    # not against this document, and flagging it would be wrong.
    text = json.dumps(document)
    issues: list[str] = []
    for reference in sorted(set(re.findall(r'"(#/components/[^"]+)"', text))):
        target: Any = document
        for token in reference[2:].split("/"):
            key = token.replace("~1", "/").replace("~0", "~")
            if isinstance(target, list):
                try:
                    target = target[int(key)]
                    continue
                except (ValueError, IndexError):
                    target = None
                    break
            if not isinstance(target, dict) or key not in target:
                target = None
                break
            target = target[key]
        if target is None:
            issues.append(f"unresolved local reference: {reference}")
    return issues


def declared_paths(document: dict[str, Any]) -> set[str]:
    return {path for path in (document.get("paths") or {}) if isinstance(path, str)}


def protocol_route_issues(document: dict[str, Any]) -> tuple[list[str], set[str]]:
    """Validate x-tempera-protocol-routes and return the routes it exempts."""
    declared = document.get("x-tempera-protocol-routes")
    if declared is None:
        return [], set()
    if not isinstance(declared, list) or not all(
        isinstance(route, str) for route in declared
    ):
        return ["x-tempera-protocol-routes must be an array of strings"], set()
    issues: list[str] = []
    present = declared_paths(document)
    for route in declared:
        if route not in present:
            issues.append(
                f"x-tempera-protocol-routes declares {route}, which the document does not serve"
            )
        elif EXEMPTIBLE.search(route) is None:
            issues.append(
                f"{route} is a resource route and cannot be declared a protocol route"
            )
    if len(set(declared)) != len(declared):
        issues.append("x-tempera-protocol-routes contains duplicates")
    return issues, set(declared)


def extension_issues(
    document: dict[str, Any], exempt: set[str], audiences: set[str]
) -> list[str]:
    issues: list[str] = []
    for path, item in (document.get("paths") or {}).items():
        if not isinstance(item, dict) or path in exempt:
            continue
        for method, operation in item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            label = f"{method.upper()} {path}"
            kind = operation.get("x-tempera-auth-kind")
            if kind not in AUTH_KINDS:
                issues.append(
                    f"{label}: x-tempera-auth-kind must be one of {sorted(AUTH_KINDS)}"
                )
                continue
            audience = operation.get("x-tempera-auth-audience")
            if kind == "oauthResource":
                if not isinstance(audience, str) or not audience:
                    issues.append(
                        f"{label}: x-tempera-auth-kind oauthResource requires x-tempera-auth-audience"
                    )
                elif audiences and audience not in audiences:
                    issues.append(f"{label}: unregistered audience {audience!r}")
            elif audience is not None:
                issues.append(
                    f"{label}: x-tempera-auth-audience is only valid with auth-kind oauthResource"
                )
            scope = operation.get("x-tempera-required-scope")
            if kind == "none":
                if scope is not None:
                    issues.append(
                        f"{label}: an unauthenticated route cannot require a scope"
                    )
            elif not isinstance(scope, str) or not scope:
                issues.append(f"{label}: x-tempera-required-scope is required")
            commit_required = operation.get("x-tempera-prepare-commit-required")
            if commit_required and not operation.get("x-tempera-physical-action"):
                issues.append(
                    f"{label}: x-tempera-prepare-commit-required implies x-tempera-physical-action"
                )
    return issues


def load_baseline(path: Path | None) -> tuple[set[str], list[str]]:
    """Read an expiring, reviewed list of violations this producer still owes."""
    if path is None or not path.is_file():
        return set(), []
    ledger = json.loads(path.read_text(encoding="utf-8"))
    issues: list[str] = []
    if ledger.get("schema_version") != 1:
        issues.append(f"{path.name}: schema_version must be 1")
    try:
        review_after = date.fromisoformat(ledger.get("review_after", ""))
    except ValueError:
        return set(), issues + [f"{path.name}: review_after must be an ISO date"]
    if review_after < date.today():
        issues.append(
            f"{path.name}: review expired on {review_after.isoformat()}; "
            "fix the violations or have the owner re-review them"
        )
    accepted = ledger.get("accepted_violations") or []
    if not isinstance(accepted, list):
        return set(), issues + [f"{path.name}: accepted_violations must be an array"]
    return set(accepted), issues


def lint(
    contract: Path, product: str, baseline: Path | None, audiences: set[str]
) -> list[str]:
    document = json.loads(contract.read_text(encoding="utf-8"))
    issues: list[str] = []

    version = document.get("openapi")
    if version != REQUIRED_OPENAPI:
        issues.append(f"openapi must be {REQUIRED_OPENAPI!r}, found {version!r}")
    issues += serialization_issues(contract, document)
    issues += component_issues(document)
    issues += reference_issues(document)
    route_issues, exempt = protocol_route_issues(document)
    issues += route_issues
    issues += extension_issues(document, exempt, audiences)

    exemptions = Exemptions(paths=frozenset((product, route) for route in exempt))
    violations = discover_violations({product: document}, exemptions)
    accepted, baseline_issues = load_baseline(baseline)
    issues += baseline_issues
    live = set(violations) - accepted
    for key in sorted(live):
        issues.append(f"{key}: {', '.join(violations[key]['observed'])}")
    for stale in sorted(accepted - set(violations)):
        issues.append(f"{stale}: baselined but no longer a violation; remove it")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument(
        "--product",
        required=True,
        help="the lowerCamel SDK product key, e.g. temperaVoice",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        help="an expiring ledger of violations this producer has not migrated yet",
    )
    parser.add_argument(
        "--audience",
        action="append",
        default=[],
        help="a registered audience; repeat to allow several",
    )
    args = parser.parse_args()
    try:
        issues = lint(
            args.contract, args.product, args.baseline, set(args.audience)
        )
    except (OSError, json.JSONDecodeError) as error:
        print(f"cannot lint {args.contract}: {error}", file=sys.stderr)
        return 1
    if issues:
        print(
            f"producer contract lint failed ({len(issues)}) for {args.product}:",
            file=sys.stderr,
        )
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
        return 1
    print(f"producer contract lint passed: {args.contract} conforms to the standard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
