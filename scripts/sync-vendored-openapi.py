#!/usr/bin/env python3
"""Vendor OpenAPI from an immutable commit still equivalent to branch HEAD."""

from __future__ import annotations

import argparse
import importlib.util
import json
import posixpath
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
    "temperaPayments": {
        "source_repo": "tempera-dev/tempera-payments",
        "source_branch": "main",
        "source_path": "contracts/openapi/payments.openapi.json",
        "generated_path": "specs/tempera-payments-api.json",
        "generated_with": "source_lock.py@1+verbatim-openapi-copy",
        "transform": "verbatim",
    },
    "temperaClearing": {
        "source_repo": "tempera-dev/tempera-clearing",
        "source_branch": "main",
        "source_path": "contracts/openapi/clearing.openapi.json",
        "generated_path": "specs/tempera-clearing-api.json",
        "generated_with": "source_lock.py@2+inline-local-json-ref-bundle",
        "transform": "json-inline-local-refs",
    },
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


def normalize_source_path(current_path: str, reference_path: str) -> str:
    """Resolve a relative Git-tree path without permitting repository escape."""

    if reference_path.startswith("/"):
        raise ValueError(f"absolute local reference is not allowed: {reference_path}")
    resolved = posixpath.normpath(
        posixpath.join(posixpath.dirname(current_path), reference_path)
    )
    if resolved == "." or resolved.startswith("../"):
        raise ValueError(f"local reference escapes source tree: {reference_path}")
    return resolved


def resolve_json_pointer(document: Any, fragment: str) -> Any:
    if not fragment:
        return document
    if not fragment.startswith("/"):
        raise ValueError(f"unsupported local reference fragment #{fragment}")
    value = document
    for token in fragment[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict) and token in value:
            value = value[token]
        elif isinstance(value, list) and token.isdigit() and int(token) < len(value):
            value = value[int(token)]
        else:
            raise ValueError(f"unresolved local JSON pointer #{fragment}")
    return value


def render_inline_local_json_refs(
    content: bytes,
    source_lock: Any,
    repo: Path,
    source_branch: str,
    commit: str,
    source_path: str,
) -> tuple[bytes, list[dict[str, str]]]:
    """Bundle checked-in relative JSON refs and lock every source dependency.

    Generated SDK tables need request-body field names. A verbatim OpenAPI copy
    that leaves relative schema references behind cannot provide those fields or
    prove which schema revision they came from. Remote schema IDs remain remote;
    only files addressed through the producer's Git tree are inlined.
    """

    dependencies: dict[str, dict[str, str]] = {}
    resolving: set[tuple[str, str]] = set()
    current_head = git(repo, "rev-parse", f"refs/remotes/origin/{source_branch}^{{commit}}")

    def source_document(path: str) -> Any:
        blob, mode, bytes_at_commit = source_lock.committed_file(repo, commit, path)
        current_blob, current_mode, _ = source_lock.committed_file(repo, current_head, path)
        if (blob, mode) != (current_blob, current_mode):
            raise ValueError(
                f"source tree entry drift for {path}: {commit} has {mode} {blob}, while "
                f"origin/{source_branch}@{current_head} has {current_mode} {current_blob}; "
                "re-vendor from current source"
            )
        dependencies[path] = {
            "source_path": path,
            "source_blob_sha": blob,
            "source_mode": mode,
            "source_sha256": source_lock.digest(bytes_at_commit),
        }
        try:
            return json.loads(bytes_at_commit)
        except json.JSONDecodeError as error:
            raise ValueError(f"local reference {path} is not valid JSON") from error

    def visit(value: Any, current_path: str) -> Any:
        if isinstance(value, list):
            return [visit(item, current_path) for item in value]
        if not isinstance(value, dict):
            return value
        reference = value.get("$ref")
        if isinstance(reference, str) and not reference.startswith("#") and "://" not in reference:
            reference_path, marker, fragment = reference.partition("#")
            resolved_path = normalize_source_path(current_path, reference_path)
            identity = (resolved_path, fragment)
            if identity in resolving:
                raise ValueError(f"cyclic local JSON reference {reference!r}")
            resolving.add(identity)
            try:
                target = resolve_json_pointer(source_document(resolved_path), fragment if marker else "")
                expanded = visit(target, resolved_path)
            finally:
                resolving.remove(identity)
            if len(value) == 1:
                return expanded
            if not isinstance(expanded, dict):
                raise ValueError(f"local reference {reference!r} cannot be merged with sibling keys")
            return visit({**expanded, **{key: item for key, item in value.items() if key != "$ref"}}, current_path)
        return {key: visit(item, current_path) for key, item in value.items()}

    try:
        document = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError("inline-local-json-ref bundle requires JSON source") from error
    rendered = (json.dumps(visit(document, source_path), indent=2) + "\n").encode()
    return rendered, [dependencies[path] for path in sorted(dependencies)]


def render(
    content: bytes,
    transform: str,
    source_lock: Any,
    repo: Path,
    source_branch: str,
    commit: str,
    source_path: str,
) -> tuple[bytes, list[dict[str, str]]]:
    if transform == "verbatim":
        return content, []
    if transform == "yaml-json":
        try:
            import yaml
        except ImportError as error:
            raise ValueError("PyYAML 6.0.3 is required for the yaml-json transform") from error
        return (json.dumps(yaml.safe_load(content), indent=2) + "\n").encode(), []
    if transform == "json-inline-local-refs":
        return render_inline_local_json_refs(
            content, source_lock, repo, source_branch, commit, source_path
        )
    raise ValueError(f"unknown transform {transform!r}")


def current_branch_equivalent_file(
    source_lock: Any,
    repo: Path,
    source_repo: str,
    source_branch: str,
    requested_commit: str,
    source_path: str,
) -> tuple[str, str, str, bytes]:
    """Read an exact source file whose tree entry still matches branch HEAD."""

    commit = source_lock.validate_source(
        repo,
        source_repo,
        source_branch,
        requested_commit,
    )
    blob, mode, content = source_lock.committed_file(repo, commit, source_path)
    current_head = git(
        repo, "rev-parse", f"refs/remotes/origin/{source_branch}^{{commit}}"
    )
    current_blob, current_mode, _ = source_lock.committed_file(
        repo, current_head, source_path
    )
    if (blob, mode) != (current_blob, current_mode):
        raise ValueError(
            f"source tree entry drift for {source_path}: "
            f"{commit} has {mode} {blob}, while "
            f"origin/{source_branch}@{current_head} has "
            f"{current_mode} {current_blob}; re-vendor from current source"
        )
    return commit, blob, mode, content


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
    commit, blob, mode, content = current_branch_equivalent_file(
        source_lock,
        repo,
        config["source_repo"],
        selected_branch,
        requested_commit,
        config["source_path"],
    )
    rendered, source_dependencies = render(
        content,
        config["transform"],
        source_lock,
        repo,
        selected_branch,
        commit,
        config["source_path"],
    )
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
    if source_dependencies:
        lock["source_dependencies"] = source_dependencies
    expected_lock = json.dumps(lock, indent=2, sort_keys=True) + "\n"
    if check:
        observed_lock = lock_path.read_text(encoding="utf-8")
        if generated.read_bytes() != rendered or json.loads(observed_lock) != lock:
            raise ValueError(f"{product} vendored OpenAPI or source lock is stale")
        print(
            f"{product} OpenAPI lock verified at {commit}; "
            f"{config['source_path']} is unchanged on origin/{selected_branch}"
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
