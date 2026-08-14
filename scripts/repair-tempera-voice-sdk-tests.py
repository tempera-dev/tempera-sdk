#!/usr/bin/env python3
"""Align hand-authored SDK conformance expectations with the generated Voice surface."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "packages/typescript/test/sdk.test.mjs"


def replace_once(value: str, old: str, new: str) -> str:
    count = value.count(old)
    if count != 1:
        raise SystemExit(f"expected one SDK test anchor, found {count}: {old[:100]!r}")
    return value.replace(old, new, 1)


def main() -> None:
    value = PATH.read_text(encoding="utf-8")
    value = replace_once(
        value,
        '  assert.equal(TEMPERA_PRODUCTS.temperaRisk.repository, "https://github.com/tempera-dev/tempera-risk");\n',
        '  assert.equal(TEMPERA_PRODUCTS.temperaRisk.repository, "https://github.com/tempera-dev/tempera-risk");\n'
        '  assert.equal(TEMPERA_PRODUCTS.temperaVoice.repository, "https://github.com/tempera-dev/tempera-voice");\n',
    )
    value = replace_once(
        value,
        '  assert.ok(TEMPERA_AUDIENCES.includes("tempera-risk"));\n',
        '  assert.ok(TEMPERA_AUDIENCES.includes("tempera-risk"));\n'
        '  assert.ok(TEMPERA_AUDIENCES.includes("tempera-voice"));\n',
    )
    value = replace_once(
        value,
        '      "payments:webhooks:write", "payments:refunds:write", "payments:admin", "admin",\n',
        '      "payments:webhooks:write", "payments:refunds:write", "payments:admin",\n'
        '      "voice:read", "voice:write", "voice:stream", "admin",\n',
    )
    value = replace_once(
        value,
        '  assert.equal(TEMPERA_ENVIRONMENTS.production.temperaRiskApiUrl, "https://risk.tempera.dev");\n',
        '  assert.equal(TEMPERA_ENVIRONMENTS.production.temperaRiskApiUrl, "https://risk.tempera.dev");\n'
        '  assert.equal(TEMPERA_ENVIRONMENTS.production.temperaVoiceApiUrl, "https://voice.tempera.dev");\n'
        '  assert.equal(TEMPERA_ENVIRONMENTS.local.temperaVoiceApiUrl, "http://127.0.0.1:8102");\n',
    )
    PATH.write_text(value, encoding="utf-8")
    print("Aligned hand-authored SDK registry expectations with Tempera Voice")


if __name__ == "__main__":
    main()
