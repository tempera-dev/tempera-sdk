"""Shared SDK identifier transforms used by code and documentation generators."""

from __future__ import annotations

import re


_WORD_BEFORE_ACRONYM = re.compile(r"(.)([A-Z][a-z]+)")
_LOWER_BEFORE_UPPER = re.compile(r"([a-z0-9])([A-Z])")


def snake_case(value: str) -> str:
    """Convert lowerCamelCase to acronym-aware snake_case."""
    words = _WORD_BEFORE_ACRONYM.sub(r"\1_\2", value)
    return _LOWER_BEFORE_UPPER.sub(r"\1_\2", words).lower()
