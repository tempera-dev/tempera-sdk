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
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))

from aip_rules import (  # noqa: E402  (path is set immediately above)
    HTTP_METHODS,
    RULES,
    Exemptions,
    discover_violations,
    declared_protocol_routes,
    is_list_operation,
    is_lower_camel,
    operation_rows,
    resolve_local_reference,
    violation_key,
)


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "contracts" / "aip-conformance-baseline.json"
SPECS = {
    "controlPlane": "control-plane.openapi.json",
    "cradle": "cradle-openapi.json",
    "dataEngine": "data-engine-openapi.json",
    "humanData": "human-data-openapi.json",
    "palette": "palette-api.json",
    "remi": "remi-http-contract.json",
    "temperaBio": "tempera-bio-api.json",
    "temperaBusiness": "tempera-business-api.json",
    "temperaConnectors": "tempera-connectors-api.json",
    "temperaDocument": "tempera-document-api.json",
    "temperaDropshipping": "tempera-dropshipping-api.json",
    "temperaGym": "tempera-gym-api.json",
    "temperaLlm": "tempera-llm-api.json",
    "temperaPayments": "tempera-payments-api.json",
    "temperaRisk": "tempera-risk-api.json",
    "temperaVoice": "tempera-voice-api.json",
    "temperaWorkflows": "tempera-workflows-api.json",
    "tempo": "tempo-openapi.json",
}
REFERENCE_GATED_PRODUCTS = {"controlPlane", "dataEngine"}

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
    # SAML is a browser/identity-provider protocol, not a Google-style resource
    # API. The aggregate SDK deliberately excludes these routes.
    ("controlPlane", "/sso/saml/login"),
    ("controlPlane", "/sso/saml/metadata/{configId}"),
    ("controlPlane", "/sso/saml/acs/{configId}"),
    ("cradle", "/v1/health"),
    ("cradle", "/mcp"),
    ("dataEngine", "/mcp"),
    ("palette", "/health"),
    ("palette", "/v1/traces"),
    ("remi", "/livez"),
    ("remi", "/readyz"),
    ("temperaGym", "/healthz"),
    # These routes intentionally implement OpenAI's public wire contract so
    # existing OpenAI-compatible clients can use Tempera LLM unchanged.
    ("temperaLlm", "/v1/chat/completions"),
    ("temperaLlm", "/v1/models"),
    ("temperaLlm", "/v1/responses"),
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
# Exact operations that implement an externally defined protocol even though
# they live below a versioned product path. OAuth token introspection is defined
# by RFC 7662, including its snake_case members and inactive-token response.
PROTOCOL_OPERATION_EXCEPTIONS = {
    ("controlPlane", "POST", "/v1/oauth/introspect"),
    # Runtime requires a server-only BFF handoff secret despite OpenAPI's empty
    # security declaration; it is deliberately excluded from the general SDK.
    ("controlPlane", "POST", "/v1/sso/handoffs:exchange"),
}
# Resource operations may deliberately return an embedded protocol payload.
# Continue checking their path, parameters, pagination, and AIP-193 errors, but
# do not reinterpret the OAuth token vocabulary as resource-message debt.
PROTOCOL_JSON_EXCEPTIONS = {
    ("controlPlane", "POST", "/v1/admin/step-up"),
    ("controlPlane", "POST", "/v1/passkeys/authentication:finish"),
    ("controlPlane", "POST", "/v1/passkeys/registration:finish"),
    ("controlPlane", "POST", "/v1/sessions"),
    ("controlPlane", "POST", "/v1/step-up/passkey:finish"),
    ("controlPlane", "POST", "/v1/workspace/select"),
}

# The reviewed protocol tables above, handed to the shared rule engine. Keeping
# them here rather than in the engine is what lets a producer lint its own
# contract with the identical rules and its own, much shorter, exemption list.
SDK_EXEMPTIONS = Exemptions(
    paths=frozenset(PROTOCOL_EXCEPTIONS),
    prefixes=frozenset(PROTOCOL_PREFIX_EXCEPTIONS),
    suffixes=frozenset(PROTOCOL_SUFFIX_EXCEPTIONS),
    operations=frozenset(PROTOCOL_OPERATION_EXCEPTIONS),
    json_payloads=frozenset(PROTOCOL_JSON_EXCEPTIONS),
)


def exemptions_for(
    specs: dict[str, dict[str, Any]]
) -> tuple[Exemptions, list[str]]:
    """Union the reviewed tables with what each producer declares for itself.

    A producer that publishes x-tempera-protocol-routes has already said which
    of its routes are governed by a native protocol, and the producer linter
    checked that claim before the contract was ever published. Re-deriving the
    same list by hand here is how the reviewed table and the contracts drifted
    apart: Voice declared /livez and /readyz, and the ratchet still counted
    them as unversioned resource paths because nobody had mirrored them.

    The declaration is re-validated rather than trusted -- a route that is not
    served, or that is not an exemptible shape, fails the build.
    """
    declared: set[tuple[str, str]] = set()
    problems: list[str] = []
    for product, spec in specs.items():
        routes, issues = declared_protocol_routes(product, spec)
        declared |= routes
        problems += issues
    return (
        Exemptions(
            paths=frozenset(PROTOCOL_EXCEPTIONS) | frozenset(declared),
            prefixes=frozenset(PROTOCOL_PREFIX_EXCEPTIONS),
            suffixes=frozenset(PROTOCOL_SUFFIX_EXCEPTIONS),
            operations=frozenset(PROTOCOL_OPERATION_EXCEPTIONS),
            json_payloads=frozenset(PROTOCOL_JSON_EXCEPTIONS),
        ),
        problems,
    )


def load_specs() -> dict[str, dict[str, Any]]:
    loaded: dict[str, dict[str, Any]] = {}
    for product, filename in SPECS.items():
        path = ROOT / "specs" / filename
        loaded[product] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def validate_local_references(specs: dict[str, dict[str, Any]]) -> list[str]:
    """Walk every local JSON reference and require its pointer to resolve."""

    failures: list[str] = []

    def resolve(document: Any, reference: str) -> None:
        if reference == "#":
            return
        if not reference.startswith("#/"):
            raise ValueError("local reference must be '#' or start with '#/'")
        current = document
        for encoded in reference[2:].split("/"):
            token = unquote(encoded).replace("~1", "/").replace("~0", "~")
            if isinstance(current, dict) and token in current:
                current = current[token]
            elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
                current = current[int(token)]
            else:
                raise ValueError(f"missing pointer token {token!r}")

    def walk(product: str, document: Any, value: Any, location: str) -> None:
        if isinstance(value, dict):
            # A subtree that declares its own $id is a separate JSON Schema
            # resource, and a "#/..." pointer inside it resolves against that
            # resource rather than against this document. Data Engine embeds
            # its evidence schema exactly that way -- with the $id, so its
            # internal #/$defs pointers still resolve -- and resolving them
            # from the document root reports a break that does not exist.
            if isinstance(value.get("$id"), str) and location != "#":
                return
            reference = value.get("$ref")
            if isinstance(reference, str) and reference.startswith("#"):
                try:
                    resolve(document, reference)
                except ValueError as error:
                    failures.append(
                        f"{product}:{location}: dangling local $ref {reference!r}: {error}"
                    )
            for key, child in value.items():
                walk(product, document, child, f"{location}/{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(product, document, child, f"{location}/{index}")

    for product, document in specs.items():
        walk(product, document, document, "#")
    return failures


def load_baseline() -> dict[str, Any]:
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def validate_protocol_exceptions(specs: dict[str, dict[str, Any]]) -> list[str]:
    rows = {
        product: operation_rows(product, spec)
        for product, spec in specs.items()
    }
    paths = {
        product: {row["path"] for row in product_rows}
        for product, product_rows in rows.items()
    }
    operations = {
        (
            product,
            row["method"],
            row["path"],
        )
        for product, product_rows in rows.items()
        for row in product_rows
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
    for exception in sorted(PROTOCOL_OPERATION_EXCEPTIONS):
        if exception not in operations:
            failures.append(
                "stale protocol operation exception: " + "|".join(exception)
            )
    for exception in sorted(PROTOCOL_JSON_EXCEPTIONS):
        if exception not in operations:
            failures.append(
                "stale protocol JSON exception: " + "|".join(exception)
            )
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
    if baseline.get("protocol_operation_exceptions") != sorted(
        "|".join(exception) for exception in PROTOCOL_OPERATION_EXCEPTIONS
    ):
        failures.append("baseline protocol operation exceptions are stale")
    if baseline.get("protocol_json_exceptions") != sorted(
        "|".join(exception) for exception in PROTOCOL_JSON_EXCEPTIONS
    ):
        failures.append("baseline protocol JSON exceptions are stale")
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
        "protocol_operation_exceptions": sorted(
            "|".join(exception) for exception in PROTOCOL_OPERATION_EXCEPTIONS
        ),
        "protocol_json_exceptions": sorted(
            "|".join(exception) for exception in PROTOCOL_JSON_EXCEPTIONS
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
        exemptions, declaration_problems = exemptions_for(specs)
        if declaration_problems:
            for problem in declaration_problems:
                print(f"protocol-route declaration rejected: {problem}", file=sys.stderr)
            return 1
        violations = discover_violations(specs, exemptions)
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
    failures.extend(
        validate_local_references(
            {
                product: spec
                for product, spec in specs.items()
                if product in REFERENCE_GATED_PRODUCTS
            }
        )
    )
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
