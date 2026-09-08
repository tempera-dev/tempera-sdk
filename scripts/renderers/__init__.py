"""Per-language surface renderers, discovered rather than enumerated.

The three original renderers live inline in `gen-sdk-surface.py`. Adding four
more languages there would have made one file own seven mutually irrelevant
escaping dialects, so additional languages register here instead: one module
per language, each exporting

    TARGETS = {"<repository-relative path>": render}

where ``render(surface) -> str`` takes the parsed ``surface.json`` and returns
the complete file text. :func:`load_targets` merges every module's table into
one mapping, in module-name order, so the generator writes and ``--check``s a
plug-in language exactly like a built-in one.

A renderer receives `surface.json` after `gen-sdk-surface.py` has already
validated it, so it may assume every invariant `validate()` enforces and does
not re-check them. Modules whose name starts with an underscore are private
helpers and are never loaded as renderers.
"""
from __future__ import annotations

import importlib
import pkgutil
from typing import Any, Callable

Renderer = Callable[[dict[str, Any]], str]


def load_targets() -> dict[str, Renderer]:
    """Collect ``{path: render}`` from every renderer module, name-ordered.

    Two renderers claiming one output would make the winner depend on import
    order, so that is an error rather than a silent overwrite: one output, one
    owner.
    """
    targets: dict[str, Renderer] = {}
    module_names = sorted(
        info.name
        for info in pkgutil.iter_modules(__path__)
        if not info.name.startswith("_")
    )
    for module_name in module_names:
        module = importlib.import_module(f"{__name__}.{module_name}")
        module_targets = getattr(module, "TARGETS", None)
        if not module_targets:
            raise RuntimeError(f"renderer module {module_name!r} exports no TARGETS")
        for path, render in module_targets.items():
            if path in targets:
                raise RuntimeError(f"two renderers both claim {path!r}")
            if not callable(render):
                raise RuntimeError(f"renderer for {path!r} is not callable")
            targets[path] = render
    return targets


# The first plug-in landed under this name; keep it working.
discover = load_targets
