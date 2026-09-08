#!/usr/bin/env python3
"""Re-vendor one or more producers and regenerate everything downstream.

This is the whole producer-to-SDK chain in one command, so that the automated
path and the human path are the same path:

    contract at an exact producer commit
      -> specs/<product>.json + its .source lock
      -> surface.json operations
      -> the generated surface table in every language
      -> the generated documentation site

Running the steps by hand in the wrong order used to be possible, and left a
surface.json that no committed spec produced. Here the order is not optional.
"""
from __future__ import annotations

import argparse
import base64
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

# Three producers predate the PRODUCTS registry and keep bespoke sync scripts.
# Leaving them out of this chain is how they drift: a sweep that says it
# re-vendored everything has to actually mean everything.
BESPOKE = {
    "controlPlane": {
        "source_repo": "tempera-dev/auth-hub",
        "source_branch": "main",
        "commands": [
            ["sync-control-plane-openapi.py"],
        ],
    },
    "dataEngineMcp": {
        "source_repo": "tempera-dev/data-engine",
        "source_branch": "main",
        "commands": [
            ["sync-data-engine-mcp-contracts.py"],
        ],
    },
    "paletteEval": {
        "source_repo": "tempera-dev/palette",
        "source_branch": "main",
        "commands": [],  # takes a checkout path rather than repo-dir arguments
    },
}


def registry() -> dict[str, dict[str, str]]:
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(
        "sync_vendored_openapi", SCRIPTS / "sync-vendored-openapi.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.PRODUCTS


def run(command: list[str], cwd: Path | None = None) -> None:
    print(f"$ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def _basic(token: str) -> str:
    """The Authorization value git uses for a token, without putting it in a URL."""
    return base64.b64encode(f"x-access-token:{token}".encode()).decode()


def clone(repository: str, branch: str, commit: str, destination: Path) -> str:
    """Clone a producer and check out the exact commit we intend to vendor."""
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    canonical = f"https://github.com/{repository}.git"
    url = (
        f"https://x-access-token:{token}@github.com/{repository}.git"
        if token
        else canonical
    )
    run(["git", "clone", "--quiet", "--no-tags", url, str(destination)])
    # Two reasons to rewrite the remote immediately: a token embedded in a
    # clone URL is written verbatim into .git/config, and the source-lock
    # validator canonicalizes `git remote get-url origin` to decide whether
    # this checkout really is the producer it claims to be. A credentialed
    # URL does not canonicalize, so vendoring would refuse it.
    run(["git", "remote", "set-url", "origin", canonical], cwd=destination)
    if token:
        run(
            [
                "git",
                "config",
                "http.https://github.com/.extraheader",
                f"Authorization: Basic {_basic(token)}",
            ],
            cwd=destination,
        )
    run(["git", "fetch", "--quiet", "--no-tags", "origin", branch], cwd=destination)
    resolved = commit or subprocess.run(
        ["git", "rev-parse", f"origin/{branch}"],
        cwd=destination,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    run(["git", "checkout", "--quiet", resolved], cwd=destination)
    return resolved


def revendor_bespoke(product: str, commit: str, workspace: Path) -> str:
    """Re-vendor a producer whose sync predates the PRODUCTS registry."""
    config = BESPOKE[product]
    repository = config["source_repo"]
    checkout = workspace / repository.split("/", 1)[1]
    resolved = (
        subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        if checkout.exists()
        else clone(repository, config["source_branch"], commit, checkout)
    )
    for command in config["commands"]:
        run(
            [sys.executable, str(SCRIPTS / command[0]), *command[1:],
             "--source-repo-dir", str(checkout),
             "--source-branch", config["source_branch"],
             "--source-commit", resolved]
        )
    if product == "paletteEval":
        run([
            sys.executable, str(SCRIPTS / "sync-palette-eval-openapi.py"),
            "--source", str(checkout / "sdks/openapi/palette-api.json"),
            "--source-checkout", str(checkout),
        ])
    return resolved


def revendor(product: str, commit: str, workspace: Path) -> str:
    config = registry()[product]
    repository = config["source_repo"]
    checkout = workspace / repository.split("/", 1)[1]
    resolved = clone(repository, config["source_branch"], commit, checkout)
    run(
        [
            sys.executable,
            str(SCRIPTS / "sync-vendored-openapi.py"),
            "--product",
            product,
            "--source-repo-dir",
            str(checkout),
            "--source-branch",
            config["source_branch"],
            "--source-commit",
            resolved,
        ]
    )
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--products",
        required=True,
        help="comma-separated SDK product keys, or 'all'",
    )
    parser.add_argument(
        "--commit",
        default="",
        help="an exact 40-character commit; only valid with a single product",
    )
    parser.add_argument(
        "--keep-checkouts",
        type=Path,
        help="directory to leave the producer checkouts in, for debugging",
    )
    args = parser.parse_args()

    products = registry()
    known = set(products) | set(BESPOKE)
    requested = (
        sorted(known)
        if args.products.strip() == "all"
        else [item.strip() for item in args.products.split(",") if item.strip()]
    )
    unknown = [product for product in requested if product not in known]
    if unknown:
        print(f"unknown products: {', '.join(unknown)}", file=sys.stderr)
        return 1
    if args.commit and len(requested) != 1:
        print("--commit names one producer's commit, so pass one product", file=sys.stderr)
        return 1

    workspace = args.keep_checkouts or Path(tempfile.mkdtemp(prefix="tempera-revendor-"))
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        for product in requested:
            resolved = (
                revendor_bespoke(product, args.commit, workspace)
                if product in BESPOKE
                else revendor(product, args.commit, workspace)
            )
            print(f"vendored {product} at {resolved}", flush=True)
        # Order matters: the surface is derived from the specs, the language
        # tables from the surface, and the documentation from the tables.
        typed = [product for product in requested if product in products]
        # paletteEval and dataEngineMcp publish side contracts, not typed
        # operations, so they have nothing to synchronize into the surface.
        surfaced = typed + (["controlPlane"] if "controlPlane" in requested else [])
        if surfaced:
            run(
                [sys.executable, str(SCRIPTS / "sync-openapi-surface.py")]
                + [argument for product in surfaced for argument in ("--product", product)]
            )
        run([sys.executable, str(SCRIPTS / "gen-sdk-surface.py")])
        run([sys.executable, str(SCRIPTS / "gen-sdk-docs.py")])
    except subprocess.CalledProcessError as error:
        print(f"re-vendor failed: {error}", file=sys.stderr)
        return 1
    finally:
        if args.keep_checkouts is None:
            shutil.rmtree(workspace, ignore_errors=True)
    print(f"re-vendored and regenerated {len(requested)} product(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
