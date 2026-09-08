#!/usr/bin/env python3
"""Emit the exact-source verification matrix from the vendoring registry.

The matrix used to be a hand-maintained hundred-line block in
`.github/workflows/test.yml`. Every product added to `sync-vendored-openapi.py`
had to be remembered there a second time, and a product that was forgotten was
simply never verified -- silently, with a green build. Generating the matrix
from `PRODUCTS` makes omission impossible: a product exists in the registry or
it is not vendored at all.

Writes `matrix=<json>` for `$GITHUB_OUTPUT`; `--print` renders it readably.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_registry() -> dict[str, dict[str, str]]:
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(
        "sync_vendored_openapi", SCRIPTS / "sync-vendored-openapi.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.PRODUCTS


def display_name(repository: str) -> str:
    """A human label for the job, e.g. tempera-voice -> Tempera Voice."""
    return " ".join(
        part.upper() if part in {"llm", "sdk", "api"} else part.capitalize()
        for part in repository.split("-")
    )


def build_matrix() -> dict[str, list[dict[str, str]]]:
    include = []
    for product, config in sorted(load_registry().items()):
        repository = config["source_repo"].split("/", 1)[1]
        include.append(
            {
                "name": display_name(repository),
                "product": product,
                "repository": repository,
                "source_branch": config["source_branch"],
                "source_path": config["source_path"],
                "lock": f"{config['generated_path']}.source",
                "generated_path": config["generated_path"],
                "generated_with": config["generated_with"],
                "transform": config["transform"],
            }
        )
    return {"include": include}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print", action="store_true", dest="pretty")
    args = parser.parse_args()
    matrix = build_matrix()
    if args.pretty:
        print(json.dumps(matrix, indent=2))
        print(f"\n{len(matrix['include'])} products", file=sys.stderr)
        return 0
    print(f"matrix={json.dumps(matrix, separators=(',', ':'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
