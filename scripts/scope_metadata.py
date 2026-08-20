"""Canonical parsing for singular and compound operation scope authority."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


MAX_REQUIRED_SCOPES = 64
MAX_SCOPE_BYTES = 256


@dataclass(frozen=True)
class ScopeDeclaration:
    """One explicit singular, compound, or absent scope declaration."""

    kind: str | None
    singular: str | None = None
    plural: tuple[str, ...] | None = None


def valid_scope_token(value: object) -> bool:
    """Return whether ``value`` is one bounded RFC 6749 scope-token."""

    if not isinstance(value, str):
        return False
    encoded = value.encode("utf-8")
    return 0 < len(encoded) <= MAX_SCOPE_BYTES and all(
        byte == 0x21 or 0x23 <= byte <= 0x5B or 0x5D <= byte <= 0x7E
        for byte in encoded
    )


def parse_scope_declaration(
    value: Mapping[str, object],
    *,
    singular_key: str,
    plural_key: str,
    label: str,
) -> ScopeDeclaration:
    """Parse one exact scope declaration without collapsing an AND-set.

    A singular ``null`` is the established explicit-clear form. The plural
    form is always a non-empty, ordered, unique list. Key presence is
    authoritative: declaring both forms is ambiguous even if one value is
    ``null``.
    """

    has_singular = singular_key in value
    has_plural = plural_key in value
    if has_singular and has_plural:
        raise ValueError(
            f"{label}: {singular_key} and {plural_key} are mutually exclusive"
        )
    if has_singular:
        singular = value[singular_key]
        if singular is None:
            return ScopeDeclaration(kind="singular")
        if not valid_scope_token(singular):
            raise ValueError(
                f"{label}: {singular_key} must be null or one bounded OAuth scope-token"
            )
        return ScopeDeclaration(kind="singular", singular=singular)
    if has_plural:
        plural = value[plural_key]
        if (
            not isinstance(plural, list)
            or not plural
            or len(plural) > MAX_REQUIRED_SCOPES
            or not all(valid_scope_token(scope) for scope in plural)
            or len(set(plural)) != len(plural)
        ):
            raise ValueError(
                f"{label}: {plural_key} must be a non-empty ordered unique list "
                "of bounded OAuth scope-tokens"
            )
        return ScopeDeclaration(kind="plural", plural=tuple(plural))
    return ScopeDeclaration(kind=None)
