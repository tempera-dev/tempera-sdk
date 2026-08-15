#!/usr/bin/env python3
"""Advance the explicit TypeScript scope ratchet to current Auth Hub producer truth."""
from pathlib import Path

path = Path("packages/typescript/test/sdk.test.mjs")
text = path.read_text()
anchor = '      "payments:webhooks:write", "payments:refunds:write", "payments:admin", "admin",\n'
replacement = (
    '      "payments:webhooks:write", "payments:refunds:write", "payments:admin",\n'
    '      "voice:read", "voice:write", "voice:stream",\n'
    '      "clearing:actions:read", "clearing:actions:propose", "clearing:actions:commit",\n'
    '      "clearing:actions:reconcile", "clearing:receipts:read", "clearing:actions:approve",\n'
    '      "admin",\n'
)
if replacement in text:
    raise SystemExit(0)
if text.count(anchor) != 1:
    raise SystemExit("scope ratchet anchor changed; refusing ambiguous update")
path.write_text(text.replace(anchor, replacement, 1))
