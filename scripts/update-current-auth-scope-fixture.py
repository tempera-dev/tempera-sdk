#!/usr/bin/env python3
"""Advance explicit SDK scope ratchets to current Auth Hub producer truth."""
from pathlib import Path

TS = Path("packages/typescript/test/sdk.test.mjs")
PY = Path("packages/python/tests/test_sdk.py")


def replace_once(path: Path, anchor: str, replacement: str) -> None:
    text = path.read_text()
    if replacement in text:
        return
    if text.count(anchor) != 1:
        raise SystemExit(f"{path}: scope ratchet anchor changed; refusing ambiguous update")
    path.write_text(text.replace(anchor, replacement, 1))


replace_once(
    TS,
    '      "payments:webhooks:write", "payments:refunds:write", "payments:admin", "admin",\n',
    '      "payments:webhooks:write", "payments:refunds:write", "payments:admin",\n'
    '      "voice:read", "voice:write", "voice:stream",\n'
    '      "clearing:actions:read", "clearing:actions:propose", "clearing:actions:commit",\n'
    '      "clearing:actions:reconcile", "clearing:receipts:read", "clearing:actions:approve",\n'
    '      "admin",\n',
)
replace_once(
    PY,
    '                "payments:webhooks:write", "payments:refunds:write", "payments:admin", "admin",\n',
    '                "payments:webhooks:write", "payments:refunds:write", "payments:admin",\n'
    '                "voice:read", "voice:write", "voice:stream",\n'
    '                "clearing:actions:read", "clearing:actions:propose",\n'
    '                "clearing:actions:commit", "clearing:actions:reconcile",\n'
    '                "clearing:receipts:read", "clearing:actions:approve", "admin",\n',
)
