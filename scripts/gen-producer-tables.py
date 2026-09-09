#!/usr/bin/env python3
"""Render the producer tables in the docs from the one producer registry.

These tables used to be maintained by hand and had gone badly stale: they still
named `api/openapi.json` for tempo and human-data, `sdks/openapi.json` for
cradle and a YAML artefact for Data Engine, none of which had been true for
some time. A table nobody can trust is worse than no table, so it is generated.

    python3 scripts/gen-producer-tables.py            # rewrite
    python3 scripts/gen-producer-tables.py --check    # fail if stale (CI)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from product_registry import PRODUCTS  # noqa: E402  (path is set above)

ROOT = Path(__file__).resolve().parents[1]
BEGIN = "<!-- BEGIN generated producer registry table -->"
END = "<!-- END generated producer registry table -->"
TARGETS = (ROOT / "docs" / "ROLLOUT.md", ROOT / "docs" / "site" / "rollout.mdx")
CANONICAL_PREFIX = "contracts/openapi/"


def table() -> str:
    rows = [
        "| Product key | Repository | Producer contract | Vendored as | Canonical |",
        "| --- | --- | --- | --- | --- |",
    ]
    for product in PRODUCTS:
        canonical = "yes" if product.source_path.startswith(CANONICAL_PREFIX) else "**no**"
        repository = product.source_repo.split("/", 1)[1]
        rows.append(
            f"| `{product.key}` | {repository} | `{product.source_path}` "
            f"| `{product.generated_path}` | {canonical} |"
        )
    return "\n".join(rows)


def rendered() -> str:
    return f"{BEGIN}\n\n{table()}\n\n{END}"


def apply(path: Path, check: bool) -> str | None:
    text = path.read_text(encoding="utf-8")
    if BEGIN not in text or END not in text:
        return f"{path.relative_to(ROOT)}: missing the generated-table markers"
    head, _, rest = text.partition(BEGIN)
    _, _, tail = rest.partition(END)
    updated = head + rendered() + tail
    if updated == text:
        return None
    if check:
        return f"{path.relative_to(ROOT)}: stale; run scripts/gen-producer-tables.py"
    path.write_text(updated, encoding="utf-8")
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    problems = [message for path in TARGETS if (message := apply(path, arguments.check))]
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    print(f"producer tables reflect all {len(PRODUCTS)} registered producers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
