#!/usr/bin/env python3
"""The one table of Tempera producers that every producer-facing script reads.

Registering a producer used to mean editing five hand-maintained dictionaries
that had no way of noticing when they disagreed: the vendoring table in
`sync-vendored-openapi.py`, the spec-name maps in `sync-openapi-surface.py`,
`check-aip-conformance.py` and `check-upstream-drift.py`, and the default-auth
map beside the first of those. A producer added to four of the five was a
producer that vendored and generated but silently skipped a gate.

There is now one entry per producer here and the five tables are derived from
it, so a partial registration is not expressible.
"""

from __future__ import annotations

from dataclasses import dataclass


VERBATIM = "sync-vendored-openapi.py@1+verbatim-openapi-copy"


@dataclass(frozen=True)
class Product:
    """One producer, from its repository through to its generated surface."""

    key: str
    source_repo: str
    source_path: str
    spec: str
    audience: str
    default_auth: str
    source_branch: str = "main"
    transform: str = "verbatim"
    generated_with: str = VERBATIM
    # `bespoke` producers are vendored by their own script rather than by
    # sync-vendored-openapi.py, because their contract needs assembling from
    # more than one source file. They are still gated identically.
    bespoke: bool = False

    @property
    def generated_path(self) -> str:
        return f"specs/{self.spec}"


PRODUCTS: tuple[Product, ...] = (
    Product(
        key="controlPlane",
        source_repo="tempera-dev/auth-hub",
        source_path="contracts/control-plane.openapi.json",
        spec="control-plane.openapi.json",
        audience="control-plane",
        default_auth="account",
        generated_with="sync-control-plane-openapi.py@1+verbatim-openapi-copy",
        bespoke=True,
    ),
    Product(
        key="cradle",
        source_repo="tempera-dev/cradle",
        source_path="contracts/openapi/cradle.openapi.json",
        spec="cradle.openapi.json",
        audience="cradle",
        default_auth="product",
    ),
    Product(
        key="dataEngine",
        source_repo="tempera-dev/data-engine",
        source_path="contracts/openapi/data-engine.openapi.json",
        spec="data-engine.openapi.json",
        audience="data-engine",
        default_auth="product",
    ),
    Product(
        key="humanData",
        source_repo="tempera-dev/human-data",
        source_path="contracts/openapi/human-data.openapi.json",
        spec="human-data.openapi.json",
        audience="data-engine",
        default_auth="product",
    ),
    Product(
        key="palette",
        source_repo="tempera-dev/palette",
        source_path="contracts/openapi/palette.openapi.json",
        spec="palette.openapi.json",
        audience="palette",
        default_auth="product",
    ),
    Product(
        key="remi",
        source_repo="tempera-dev/remi",
        source_path="contracts/openapi/remi.openapi.json",
        spec="remi.openapi.json",
        audience="remi",
        default_auth="product",
    ),
    Product(
        key="tempo",
        source_repo="tempera-dev/tempo",
        source_path="contracts/openapi/tempo.openapi.json",
        spec="tempo.openapi.json",
        audience="tempo",
        default_auth="product",
    ),
    Product(
        key="temperaBio",
        source_repo="tempera-dev/tempera-bio",
        source_path="contracts/openapi/bio.openapi.json",
        spec="tempera-bio.openapi.json",
        audience="tempera-bio",
        default_auth="product",
    ),
    Product(
        key="temperaBusiness",
        source_repo="tempera-dev/tempera-business",
        source_path="contracts/openapi/business.openapi.json",
        spec="tempera-business.openapi.json",
        audience="tempera-business",
        default_auth="oauthResource",
    ),
    Product(
        key="temperaConnectors",
        source_repo="tempera-dev/tempera-connectors-runtime",
        source_path="contracts/openapi/connectors.openapi.json",
        spec="tempera-connectors.openapi.json",
        audience="tempera-connectors",
        default_auth="oauthResource",
    ),
    Product(
        key="temperaDocument",
        source_repo="tempera-dev/tempera-document",
        source_path="contracts/openapi/document.openapi.json",
        spec="tempera-document.openapi.json",
        audience="tempera-document",
        default_auth="product",
    ),
    Product(
        key="temperaDropshipping",
        source_repo="tempera-dev/tempera-dropshipping",
        source_path="contracts/openapi/dropshipping.openapi.json",
        spec="tempera-dropshipping.openapi.json",
        audience="tempera-dropshipping",
        default_auth="oauthResource",
    ),
    Product(
        key="temperaGym",
        source_repo="tempera-dev/tempera-gym",
        source_path="contracts/openapi/gym.openapi.json",
        spec="tempera-gym.openapi.json",
        audience="tempera-gym",
        default_auth="product",
    ),
    Product(
        key="temperaInvestigations",
        source_repo="tempera-dev/tempera-investigations",
        source_path="contracts/openapi/investigations.openapi.json",
        spec="tempera-investigations.openapi.json",
        audience="tempera-investigations",
        default_auth="oauthResource",
    ),
    Product(
        key="temperaLlm",
        source_repo="tempera-dev/tempera-llm",
        source_path="contracts/openapi/llm.openapi.json",
        spec="tempera-llm.openapi.json",
        audience="tempera-llm",
        default_auth="product",
    ),
    Product(
        key="temperaPayments",
        source_repo="tempera-dev/tempera-payments",
        source_path="contracts/openapi/payments.openapi.json",
        spec="tempera-payments.openapi.json",
        audience="tempera-payments",
        default_auth="oauthResource",
    ),
    Product(
        key="temperaRisk",
        source_repo="tempera-dev/tempera-risk",
        source_path="contracts/openapi/risk.openapi.json",
        spec="tempera-risk.openapi.json",
        audience="tempera-risk",
        default_auth="product",
    ),
    Product(
        key="temperaVoice",
        source_repo="tempera-dev/tempera-voice",
        source_path="contracts/openapi/voice.openapi.json",
        spec="tempera-voice.openapi.json",
        audience="tempera-voice",
        default_auth="oauthResource",
    ),
    Product(
        key="temperaWorkflows",
        source_repo="tempera-dev/tempera-workflows",
        source_path="sdks/openapi/tempera-workflows-api.json",
        spec="tempera-workflows.openapi.json",
        audience="tempera-workflows",
        default_auth="product",
    ),
)

BY_KEY: dict[str, Product] = {product.key: product for product in PRODUCTS}
if len(BY_KEY) != len(PRODUCTS):
    raise SystemExit("product_registry: duplicate product key")
_SPECS = {product.spec for product in PRODUCTS}
if len(_SPECS) != len(PRODUCTS):
    raise SystemExit("product_registry: two products claim one vendored spec file")

# The five derived tables. Each one used to be maintained by hand.
VENDORED_BY_REGISTRY: dict[str, dict[str, str]] = {
    product.key: {
        "source_repo": product.source_repo,
        "source_branch": product.source_branch,
        "source_path": product.source_path,
        "generated_path": product.generated_path,
        "generated_with": product.generated_with,
        "transform": product.transform,
    }
    for product in PRODUCTS
    if not product.bespoke
}
SPEC_FILES: dict[str, str] = {product.key: product.spec for product in PRODUCTS}
DEFAULT_AUTH: dict[str, str] = {
    product.key: product.default_auth for product in PRODUCTS
}
AUDIENCES: dict[str, str] = {product.key: product.audience for product in PRODUCTS}
