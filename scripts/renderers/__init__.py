"""Plug-in registry for generated SDK surface renderers.

`scripts/gen-sdk-surface.py` renders the TypeScript, Python, and Rust surface
tables inline. Languages added afterwards register here instead: one module per
language exporting

    TARGETS = {"<repo-relative path>": render}

where ``render(surface) -> str`` takes the parsed ``surface.json`` and returns
the complete file text. :func:`load_targets` merges every module's table into
one mapping, in module-name order, so the generator writes and ``--check``s the
plug-in languages exactly like the built-in ones.

Modules whose name starts with an underscore are private helpers and are never
loaded as renderers.
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import Callable, Dict

Renderer = Callable[[dict], str]


def load_targets() -> Dict[str, Renderer]:
    """Collect ``{path: render}`` from every renderer module, name-ordered."""

    targets: Dict[str, Renderer] = {}
    module_names = sorted(
        info.name for info in pkgutil.iter_modules(__path__) if not info.name.startswith("_")
    )
    for module_name in module_names:
        module = importlib.import_module(f"{__name__}.{module_name}")
        module_targets = getattr(module, "TARGETS", None)
        if not module_targets:
            raise RuntimeError(f"renderer module {module_name!r} exports no TARGETS")
        for path, render in module_targets.items():
            if path in targets:
                raise RuntimeError(f"two renderers claim {path!r}")
            if not callable(render):
                raise RuntimeError(f"renderer for {path!r} is not callable")
            targets[path] = render
    return targets


__all__ = ["Renderer", "load_targets"]
