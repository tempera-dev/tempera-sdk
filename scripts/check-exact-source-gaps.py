#!/usr/bin/env python3
"""Validate explicit hosted exact-source verification gaps.

Private producers without the Tempera Contract Reader GitHub App cannot be
checked out by SDK Actions. The gap is allowed only when it names the exact
vendored commit, links producer-side hosted CI, has an owner/remediation, and
has not expired. This is not a substitute for exact-source reproduction.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "contracts" / "sdk-exact-source-gaps.json"
EXACT_KEYS = {
    "repository",
    "source_commit",
    "blocker",
    "owner",
    "remediation",
    "producer_ci_url",
    "review_after",
}


def source_commits() -> dict[str, set[str]]:
    observed: dict[str, set[str]] = {}
    for path in sorted((ROOT / "specs").glob("*.source")):
        lock = json.loads(path.read_text(encoding="utf-8"))
        observed.setdefault(lock["source_repo"], set()).add(lock["source_commit"])
    return observed


def validate(repository: str | None = None) -> list[str]:
    failures: list[str] = []
    try:
        ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
        sources = source_commits()
    except (OSError, json.JSONDecodeError, KeyError) as error:
        return [f"cannot load exact-source gap inputs: {error}"]
    if ledger.get("schema_version") != 1:
        failures.append("gap ledger schema_version must be 1")
    entries = ledger.get("gaps")
    if not isinstance(entries, list):
        return failures + ["gap ledger gaps must be an array"]
    indexed: dict[str, dict[str, str]] = {}
    for index, entry in enumerate(entries):
        label = f"gaps[{index}]"
        if not isinstance(entry, dict) or set(entry) != EXACT_KEYS:
            failures.append(f"{label} keys differ from the exact gap schema")
            continue
        if not all(isinstance(entry[key], str) and entry[key] for key in EXACT_KEYS):
            failures.append(f"{label} values must be non-empty strings")
            continue
        repo = entry["repository"]
        if repo in indexed:
            failures.append(f"{label} duplicates repository {repo}")
            continue
        indexed[repo] = entry
        if re.fullmatch(r"[0-9a-f]{40}", entry["source_commit"]) is None:
            failures.append(f"{label} source_commit is not a 40-character SHA")
        if sources.get(repo) != {entry["source_commit"]}:
            failures.append(
                f"{label} commit {entry['source_commit']} does not exactly match "
                f"vendored locks {sorted(sources.get(repo, set()))}"
            )
        if re.fullmatch(
            rf"https://github\.com/{re.escape(repo)}/actions/runs/[0-9]+",
            entry["producer_ci_url"],
        ) is None:
            failures.append(f"{label} producer_ci_url is not an exact Actions run")
        try:
            review_after = date.fromisoformat(entry["review_after"])
            if review_after < date.today():
                failures.append(
                    f"{label} review expired on {review_after.isoformat()}"
                )
        except ValueError:
            failures.append(f"{label} review_after must be an ISO calendar date")
    if repository is not None and repository not in indexed:
        failures.append(f"{repository} has no explicit exact-source verification gap")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository")
    args = parser.parse_args()
    failures = validate(args.repository)
    if failures:
        print(f"exact-source gap gate failed ({len(failures)}):", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    print(
        f"exact-source gap gate passed: {len(ledger['gaps'])} explicit, "
        "expiring private-repository blockers"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
