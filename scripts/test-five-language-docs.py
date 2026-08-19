#!/usr/bin/env python3
"""Assert that the generated SDK docs expose every supported language."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("typescript", "python", "rust", "go", "c")


def kebab(value: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "-", value).lower()


def require_tabs(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    failures: list[str] = []
    for language in LANGUAGES:
        if f"```{language} " not in text:
            failures.append(f"{path.relative_to(ROOT)} lacks a {language} code tab")
    return failures


def main() -> int:
    surface = json.loads((ROOT / "surface.json").read_text(encoding="utf-8"))
    failures = require_tabs(ROOT / "docs/site/index.mdx")
    for product_key in surface["operations"]:
        failures.extend(
            require_tabs(ROOT / f"docs/site/products/{kebab(product_key)}.mdx")
        )

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if "TypeScript, Python, Rust, Go, and C" not in readme:
        failures.append("README.md does not state the five-language contract")
    if "TypeScript/Python/Rust/Go/C examples" not in readme:
        failures.append("README.md does not state five-language API-reference examples")

    if failures:
        raise SystemExit("\n".join(failures))
    print(
        f"five-language documentation passed for {len(surface['operations'])} typed products"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
