#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "auth-hub",
    "tempo",
    "temp.js",
    "tempOS",
    "remi",
    "cradle",
    "Arrha",
    "https://github.com/tempera-dev/tempo",
    "https://github.com/tempera-dev/temp.js",
    "https://github.com/tempera-dev/tempOS",
    "https://github.com/tempera-dev/remi",
    "https://github.com/tempera-dev/cradle",
    "https://github.com/tempera-dev/arrha",
    "typescript",
    "python",
    "rust",
]

FILES = [
    "sdk.toml",
    "packages/typescript/src/index.js",
    "packages/typescript/src/index.d.ts",
    "packages/python/src/tempera_sdk/__init__.py",
    "packages/rust/src/lib.rs",
]


def main() -> int:
    text = "\n".join((ROOT / path).read_text() for path in FILES)
    missing = [item for item in REQUIRED if item not in text]
    if missing:
        for item in missing:
            print(f"missing SDK surface marker: {item}")
        return 1
    print("SDK surface check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
