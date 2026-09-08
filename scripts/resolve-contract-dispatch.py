#!/usr/bin/env python3
"""Validate a contract-update request before it reaches a checkout or a token.

The product name and commit arrive in a repository_dispatch payload, which is
influenced by whoever can fire the dispatch. Resolving them against the
committed vendoring registry here means an unknown product, a bogus commit, or
an attempt to widen the minted token's repository scope fails before any
credential exists.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def registry() -> dict[str, dict[str, str]]:
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(
        "sync_vendored_openapi", SCRIPTS / "sync-vendored-openapi.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.PRODUCTS


def main() -> int:
    products = registry()
    event = os.environ.get("EVENT_NAME", "")
    requested = (
        os.environ.get("PAYLOAD_PRODUCT")
        if event == "repository_dispatch"
        else os.environ.get("INPUT_PRODUCT")
    ) or ""
    requested = requested.strip()
    commit = (os.environ.get("PAYLOAD_COMMIT") or "").strip()

    if requested:
        if requested not in products:
            print(
                f"unknown product {requested!r}; it is not in the vendoring registry",
                file=sys.stderr,
            )
            return 1
        selected = [requested]
        if commit and re.fullmatch(r"[0-9a-f]{40}", commit) is None:
            print("commit must be a 40-character lowercase SHA", file=sys.stderr)
            return 1
    else:
        # A scheduled sweep re-vendors everything at each producer's main.
        selected = sorted(products)
        commit = ""

    repositories = sorted(
        {products[product]["source_repo"].split("/", 1)[1] for product in selected}
    )
    output = {
        "products": ",".join(selected),
        "repositories": ",".join(repositories),
        "commit": commit,
    }
    for key, value in output.items():
        print(f"{key}={value}")
    print(
        f"resolved {len(selected)} product(s) across {len(repositories)} repositor"
        f"{'y' if len(repositories) == 1 else 'ies'}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
