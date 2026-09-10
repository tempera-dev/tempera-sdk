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
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from product_registry import PRODUCTS  # noqa: E402  (path is set above)

ROOT = Path(__file__).resolve().parents[1]
BEGIN = "<!-- BEGIN generated producer registry table -->"
END = "<!-- END generated producer registry table -->"
CLIENTS_BEGIN = "<!-- BEGIN generated client table -->"
CLIENTS_END = "<!-- END generated client table -->"
TARGETS = (ROOT / "docs" / "ROLLOUT.md", ROOT / "docs" / "site" / "rollout.mdx")
CLIENT_TARGETS = (ROOT / "README.md",)
SURFACE = ROOT / "surface.json"
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


def client_table() -> str:
    """Every client the SDK generates, with the operation count it really has.

    These counts were maintained by hand and had drifted badly -- the control
    plane read 71 against an actual 123, human-data read 1 against 3, and nine
    products were missing from the tables altogether. A number a reader cannot
    trust is worse than no number.
    """
    surface = json.loads(SURFACE.read_text(encoding="utf-8"))
    rows = [
        "| Client | Product | Typed operations | Audience |",
        "| --- | --- | --- | --- |",
    ]
    entries = sorted(
        surface["products"].items(),
        key=lambda item: (-len(surface["operations"].get(item[0], [])), item[0]),
    )
    for key, product in entries:
        count = len(surface["operations"].get(key, []))
        repository = product.get("repository")
        name = product.get("name", key)
        label = f"[{name}]({repository})" if repository else name
        audience = product.get("audience")
        rows.append(
            f"| `{key}` | {label} | {count or 'passthrough; no typed operations'} "
            f"| {f'`{audience}`' if audience else '—'} |"
        )
    return "\n".join(rows)


def rendered() -> str:
    return f"{BEGIN}\n\n{table()}\n\n{END}"


def rendered_clients() -> str:
    return f"{CLIENTS_BEGIN}\n\n{client_table()}\n\n{CLIENTS_END}"


def apply(
    path: Path,
    check: bool,
    begin: str = BEGIN,
    end: str = END,
    render: Any = None,
) -> str | None:
    render = render or rendered
    text = path.read_text(encoding="utf-8")
    if begin not in text or end not in text:
        return f"{path.relative_to(ROOT)}: missing the generated-table markers"
    head, _, rest = text.partition(begin)
    _, _, tail = rest.partition(end)
    updated = head + render() + tail
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
    problems += [
        message
        for path in CLIENT_TARGETS
        if (
            message := apply(
                path, arguments.check, CLIENTS_BEGIN, CLIENTS_END, rendered_clients
            )
        )
    ]
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    surface = json.loads(SURFACE.read_text(encoding="utf-8"))
    operations = sum(len(value) for value in surface["operations"].values())
    print(
        f"producer tables reflect all {len(PRODUCTS)} registered producers; "
        f"README reflects {len(surface['products'])} clients and {operations} operations"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
