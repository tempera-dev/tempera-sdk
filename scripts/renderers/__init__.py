"""Per-language surface renderers, discovered rather than enumerated.

The three original renderers live inline in `gen-sdk-surface.py`. Adding four
more languages there would have made one file own seven mutually irrelevant
escaping dialects, so additional languages register here instead: one module
per language, each exporting `TARGETS`, a mapping of repository-relative
output path to a `render(surface) -> str` callable.

A renderer receives the parsed `surface.json` after `gen-sdk-surface.py` has
already validated it, so it may assume every invariant that `validate()`
enforces and does not re-check them.
"""
from __future__ import annotations

import importlib
import pkgutil
from typing import Any, Callable


def discover() -> dict[str, Callable[[dict[str, Any]], str]]:
    """Collect every registered renderer, failing loudly on a path collision."""
    targets: dict[str, Callable[[dict[str, Any]], str]] = {}
    for module_info in sorted(
        pkgutil.iter_modules(__path__), key=lambda info: info.name
    ):
        module = importlib.import_module(f"{__name__}.{module_info.name}")
        for rel_path, renderer in getattr(module, "TARGETS", {}).items():
            if rel_path in targets:
                raise RuntimeError(
                    f"two renderers both claim {rel_path}; one output, one owner"
                )
            targets[rel_path] = renderer
    return targets
