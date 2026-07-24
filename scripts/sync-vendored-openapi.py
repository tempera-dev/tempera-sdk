#!/usr/bin/env python3
"""Vendor an upstream OpenAPI artifact from the exact current source branch head."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_LOCK_SCRIPT = (
    ROOT
    / ".codex/skills/tempera-sync-contracts/scripts/source_lock.py"
)

PRODUCTS: dict[str, dict[str, str]] = {
    "dataEngine": {
        "source_repo": "tempera-dev/data-engine",
        "source_branch": "main",
        "source_path": "api/openapi.yaml",
        "generated_path": "specs/data-engine-openapi.json",
        "generated_with": "sync-vendored-openapi.py@1+PyYAML@6.0.3+json.dumps-indent-2",
        "transform": "yaml-json",
    },
    "humanData": {
        "source_repo": "tempera-dev/human-data",
        "source_branch": "main",
        "source_path": "api/openapi.json",
        "generated_path": "specs/human-data-openapi.json",
        "generated_with": "source_lock.py@1+verbatim-openapi-copy",
        "transform": "verbatim",
    },
    "palette": {
        "source_repo": "tempera-dev/palette",
        "source_branch": "main",
        "source_path": "sdks/openapi/palette-api.json",
        "generated_path": "specs/palette-api.json",
        "generated_with": "source_lock.py@1+palette-api-dump-openapi",
        "transform": "verbatim",
    },
    "cradle": {
        "source_repo": "tempera-dev/cradle",
        "source_branch": "main",
        "source_path": "sdks/openapi.json",
        "generated_path": "specs/cradle-openapi.json",
        "generated_with": "source_lock.py@1+verbatim-openapi-copy",
        "transform": "verbatim",
    },
    "temperaGym": {
        "source_repo": "tempera-dev/tempera-gym",
        "source_branch": "main",
        "source_path": "contracts/gym-api.openapi.yaml",
        "generated_path": "specs/tempera-gym-api.json",
        "generated_with": "source_lock.py@1+PyYAML@6.0.3+json.dumps-indent-2",
        "transform": "yaml-json",
    },
    "temperaBio": {
        "source_repo": "tempera-dev/tempera-bio",
        "source_branch": "main",
        "source_path": "openapi/tempera-bio-discovery-v1.openapi.json",
        "generated_path": "specs/tempera-bio-api.json",
        "generated_with": "source_lock.py@1+verbatim-openapi-copy",
        "transform": "verbatim",
    },
    "temperaLlm": {
        "source_repo": "tempera-dev/tempera-llm",
        "source_branch": "main",
        "source_path": "sdks/openapi/tempera-llm-api.json",
        "generated_path": "specs/tempera-llm-api.json",
        "generated_with": "source_lock.py@1+verbatim-openapi-copy",
        "transform": "verbatim",
    },
    "temperaWorkflows": {
        "source_repo": "tempera-dev/tempera-workflows",
        "source_branch": "main",
        "source_path": "sdks/openapi/tempera-workflows-api.json",
        "generated_path": "specs/tempera-workflows-api.json",
        "generated_with": "source_lock.py@1+verbatim-openapi-copy",
        "transform": "verbatim",
    },
    "remi": {
        "source_repo": "tempera-dev/remi",
        "source_branch": "main",
        "source_path": "docs/public-http-contract.json",
        "generated_path": "specs/remi-http-contract.json",
        "generated_with": "sync-vendored-openapi.py@1+verbatim-contract-copy",
        "transform": "verbatim",
    },
    "tempo": {
        "source_repo": "tempera-dev/tempo",
        "source_branch": "main",
        "source_path": "api/openapi.json",
        "generated_path": "specs/tempo-openapi.json",
        "generated_with": "sync-vendored-openapi.py@1+verbatim-openapi-copy",
        "transform": "verbatim",
    },
}


def load_source_lock_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "tempera_source_lock", SOURCE_LOCK_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise ValueError("cannot load vendored source-lock implementation")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SOURCE_LOCK_SCRIPT.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def render(content: bytes, transform: str) -> bytes:
    if transform == "verbatim":
        return content
    if transform == "yaml-json":
        try:
            import yaml
        except ImportError as error:
            raise ValueError("PyYAML 6.0.3 is required for the yaml-json transform") from error
        return (json.dumps(yaml.safe_load(content), indent=2) + "\n").encode()
    raise ValueError(f"unknown transform {transform!r}")


def synchronize(
    product: str,
    repo: Path,
    requested_commit: str,
    check: bool,
    source_branch: str | None = None,
) -> None:
    config = PRODUCTS[product]
    selected_branch = source_branch or config["source_branch"]
    source_lock = load_source_lock_module()
    commit = source_lock.validate_source(
        repo,
        config["source_repo"],
        selected_branch,
        requested_commit,
    )
    current_head = git(
        repo, "rev-parse", f"refs/remotes/origin/{selected_branch}^{{commit}}"
    )
    if commit != current_head:
        raise ValueError(
            f"{product} source commit {commit} is not current "
            f"origin/{selected_branch} ({current_head})"
        )
    blob, mode, content = source_lock.committed_file(
        repo, commit, config["source_path"]
    )
    rendered = render(content, config["transform"])
    generated = ROOT / config["generated_path"]
    lock_path = generated.with_name(generated.name + ".source")
    lock = {
        "schema_version": 1,
        "source_repo": config["source_repo"],
        "source_branch": selected_branch,
        "source_commit": commit,
        "source_path": config["source_path"],
        "source_blob_sha": blob,
        "source_mode": mode,
        "source_sha256": source_lock.digest(content),
        "generated_with": config["generated_with"],
        "generated_path": config["generated_path"],
        "generated_sha256": source_lock.digest(rendered),
    }
    expected_lock = json.dumps(lock, indent=2, sort_keys=True) + "\n"
    if check:
        observed_lock = lock_path.read_text(encoding="utf-8")
        if generated.read_bytes() != rendered or json.loads(observed_lock) != lock:
            raise ValueError(f"{product} vendored OpenAPI or source lock is stale")
        print(f"{product} current-head OpenAPI lock verified at {commit}")
        return
    generated.write_bytes(rendered)
    lock_path.write_text(expected_lock, encoding="utf-8")
    print(f"wrote {config['generated_path']} and {lock_path.relative_to(ROOT)} at {commit}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", choices=sorted(PRODUCTS), required=True)
    parser.add_argument("--source-repo-dir", type=Path, required=True)
    parser.add_argument(
        "--source-branch",
        help=(
            "Exact staged producer branch. Omit for the canonical mainline "
            "branch; the aggregate release gate rejects non-main locks."
        ),
    )
    parser.add_argument("--source-commit", default="HEAD")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        synchronize(
            args.product,
            args.source_repo_dir.resolve(),
            args.source_commit,
            args.check,
            args.source_branch,
        )
        return 0
    except (
        json.JSONDecodeError,
        OSError,
        subprocess.CalledProcessError,
        ValueError,
    ) as error:
        print(f"vendored OpenAPI sync failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
