#!/usr/bin/env python3
"""Vendor OpenAPI from an immutable commit still equivalent to branch HEAD."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from staged_source import validate_exact_local_source
from local_schema_bundle import bundle, strict_object


ROOT = Path(__file__).resolve().parents[1]
SOURCE_LOCK_SCRIPT = (
    ROOT
    / ".codex/skills/tempera-sync-contracts/scripts/source_lock.py"
)

PRODUCTS: dict[str, dict[str, str]] = {
    "temperaPayments": {
        "source_repo": "tempera-dev/tempera-payments",
        "source_branch": "main",
        "source_path": "contracts/openapi/payments.openapi.json",
        "generated_path": "specs/tempera-payments-api.json",
        "generated_with": "source_lock.py@1+verbatim-openapi-copy",
        "transform": "verbatim",
    },
    "dataEngine": {
        "source_repo": "tempera-dev/data-engine",
        "source_branch": "main",
        "source_path": "api/openapi.yaml",
        "generated_path": "specs/data-engine-openapi.json",
        "generated_with": "sync-vendored-openapi.py@2+PyYAML@6.0.3+source-pinned-local-json-bundle",
        "transform": "yaml-json-local-bundle",
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
    "temperaDocument": {
        "source_repo": "tempera-dev/tempera-document",
        "source_branch": "main",
        "source_path": "sdks/openapi/tempera-document-api.json",
        "generated_path": "specs/tempera-document-api.json",
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
    "temperaVoice": {
        "source_repo": "tempera-dev/tempera-voice",
        "source_branch": "main",
        "source_path": "contracts/voice-api.openapi.json",
        "generated_path": "specs/tempera-voice-api.json",
        "generated_with": "source_lock.py@1+verbatim-openapi-copy",
        "transform": "verbatim",
    },
    "temperaRisk": {
        "source_repo": "tempera-dev/tempera-risk",
        "source_branch": "main",
        "source_path": "api/openapi.yaml",
        "generated_path": "specs/tempera-risk-api.json",
        "generated_with": "sync-vendored-openapi.py@1+PyYAML@6.0.3+json.dumps-indent-2",
        "transform": "yaml-json",
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
    "temperaDropshipping": {
        "source_repo": "tempera-dev/tempera-dropshipping",
        "source_branch": "main",
        "source_path": "contracts/dropshipping.openapi.json",
        "generated_path": "specs/tempera-dropshipping-api.json",
        "generated_with": "sync-vendored-openapi.py@1+verbatim-openapi-copy",
        "transform": "verbatim",
    },
    "temperaBusiness": {
        "source_repo": "tempera-dev/tempera-business",
        "source_branch": "main",
        "source_path": "contracts/tempera-business.openapi.json",
        "generated_path": "specs/tempera-business-api.json",
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


def current_branch_equivalent_file(
    source_lock: Any,
    repo: Path,
    source_repo: str,
    source_branch: str,
    requested_commit: str,
    source_path: str,
    *,
    allow_local_source: bool = False,
) -> tuple[str, str, str, bytes]:
    """Read an exact source file whose tree entry still matches branch HEAD."""

    commit = (
        validate_exact_local_source(repo, source_repo, source_branch, requested_commit)
        if allow_local_source
        else source_lock.validate_source(repo, source_repo, source_branch, requested_commit)
    )
    blob, mode, content = source_lock.committed_file(repo, commit, source_path)
    branch_ref = (
        f"refs/heads/{source_branch}"
        if allow_local_source
        else f"refs/remotes/origin/{source_branch}"
    )
    current_head = git(repo, "rev-parse", f"{branch_ref}^{{commit}}")
    current_blob, current_mode, _ = source_lock.committed_file(
        repo, current_head, source_path
    )
    if (blob, mode) != (current_blob, current_mode):
        raise ValueError(
            f"source tree entry drift for {source_path}: "
            f"{commit} has {mode} {blob}, while "
            f"{branch_ref}@{current_head} has "
            f"{current_mode} {current_blob}; re-vendor from current source"
        )
    return commit, blob, mode, content


def synchronize(
    product: str,
    repo: Path,
    requested_commit: str,
    check: bool,
    source_branch: str | None = None,
    allow_local_source: bool = False,
) -> None:
    config = PRODUCTS[product]
    selected_branch = source_branch or config["source_branch"]
    source_lock = load_source_lock_module()
    commit, blob, mode, content = current_branch_equivalent_file(
        source_lock,
        repo,
        config["source_repo"],
        selected_branch,
        requested_commit,
        config["source_path"],
        allow_local_source=allow_local_source,
    )
    referenced_files: dict[str, dict[str, str]] = {}
    if config["transform"] == "yaml-json-local-bundle":
        def read_reference(path: str) -> bytes:
            _, ref_blob, ref_mode, ref_content = current_branch_equivalent_file(
                source_lock, repo, config["source_repo"], selected_branch,
                commit, path, allow_local_source=allow_local_source,
            )
            receipt = {"source_path": path, "source_blob_sha": ref_blob,
                "source_mode": ref_mode, "source_sha256": source_lock.digest(ref_content)}
            prior = referenced_files.setdefault(path, receipt)
            if prior != receipt:
                raise ValueError(f"inconsistent source receipt for referenced file: {path}")
            return ref_content

        import yaml
        if yaml.__version__ != "6.0.3":
            raise ValueError("PyYAML 6.0.3 is required for source-pinned YAML bundling")
        class UniqueLoader(yaml.SafeLoader):
            pass
        def unique_mapping(loader, node):
            return strict_object(loader.construct_pairs(node, deep=True))
        UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)
        root = yaml.load(content, Loader=UniqueLoader)
        if not isinstance(root, dict):
            raise ValueError("OpenAPI YAML root must be an object")
        rendered = (json.dumps(bundle(root, config["source_path"], read_reference),
                               indent=2, allow_nan=False) + "\n").encode()
    else:
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
    if config["transform"] == "yaml-json-local-bundle":
        lock["referenced_files"] = [referenced_files[path] for path in sorted(referenced_files)]
        expected_lock = json.dumps(lock, indent=2, sort_keys=True) + "\n"
    if check:
        observed_lock = lock_path.read_text(encoding="utf-8")
        if generated.read_bytes() != rendered or json.loads(observed_lock) != lock:
            raise ValueError(f"{product} vendored OpenAPI or source lock is stale")
        print(
            f"{product} OpenAPI lock verified at {commit}; "
            f"{config['source_path']} is unchanged on "
            f"{'local' if allow_local_source else 'origin'}/{selected_branch}"
        )
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
    parser.add_argument(
        "--allow-local-source",
        action="store_true",
        help="accept only an exact clean checked-out local branch head",
    )
    args = parser.parse_args()
    try:
        synchronize(
            args.product,
            args.source_repo_dir.resolve(),
            args.source_commit,
            args.check,
            args.source_branch,
            args.allow_local_source,
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
