#!/usr/bin/env python3
"""Align hand-authored SDK conformance expectations with the generated Voice surface."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(relative: str, old: str, new: str) -> None:
    path = ROOT / relative
    value = path.read_text(encoding="utf-8")
    count = value.count(old)
    if count != 1:
        raise SystemExit(
            f"{relative}: expected one SDK test anchor, found {count}: {old[:100]!r}"
        )
    path.write_text(value.replace(old, new, 1), encoding="utf-8")


def patch_typescript() -> None:
    relative = "packages/typescript/test/sdk.test.mjs"
    replace_once(
        relative,
        '  assert.equal(TEMPERA_PRODUCTS.temperaRisk.repository, "https://github.com/tempera-dev/tempera-risk");\n',
        '  assert.equal(TEMPERA_PRODUCTS.temperaRisk.repository, "https://github.com/tempera-dev/tempera-risk");\n'
        '  assert.equal(TEMPERA_PRODUCTS.temperaVoice.repository, "https://github.com/tempera-dev/tempera-voice");\n',
    )
    replace_once(
        relative,
        '  assert.ok(TEMPERA_AUDIENCES.includes("tempera-risk"));\n',
        '  assert.ok(TEMPERA_AUDIENCES.includes("tempera-risk"));\n'
        '  assert.ok(TEMPERA_AUDIENCES.includes("tempera-voice"));\n',
    )
    replace_once(
        relative,
        '      "payments:webhooks:write", "payments:refunds:write", "payments:admin", "admin",\n',
        '      "payments:webhooks:write", "payments:refunds:write", "payments:admin",\n'
        '      "voice:read", "voice:write", "voice:stream", "admin",\n',
    )
    replace_once(
        relative,
        '  assert.equal(TEMPERA_ENVIRONMENTS.production.temperaRiskApiUrl, "https://risk.tempera.dev");\n',
        '  assert.equal(TEMPERA_ENVIRONMENTS.production.temperaRiskApiUrl, "https://risk.tempera.dev");\n'
        '  assert.equal(TEMPERA_ENVIRONMENTS.production.temperaVoiceApiUrl, "https://voice.tempera.dev");\n'
        '  assert.equal(TEMPERA_ENVIRONMENTS.local.temperaVoiceApiUrl, "http://127.0.0.1:8102");\n',
    )


def patch_python() -> None:
    replace_once(
        "packages/python/tests/test_auth.py",
        '                "temperaPayments": ("tempera-payments", "TEMPERA_PAYMENTS_URL"),\n',
        '                "temperaPayments": ("tempera-payments", "TEMPERA_PAYMENTS_URL"),\n'
        '                "temperaVoice": ("tempera-voice", "TEMPERA_VOICE_URL"),\n',
    )
    relative = "packages/python/tests/test_sdk.py"
    replace_once(
        relative,
        '        self.assertEqual(PRODUCTS["temperaDocument"]["repository"], "https://github.com/tempera-dev/tempera-document")\n',
        '        self.assertEqual(PRODUCTS["temperaDocument"]["repository"], "https://github.com/tempera-dev/tempera-document")\n'
        '        self.assertEqual(PRODUCTS["temperaVoice"]["repository"], "https://github.com/tempera-dev/tempera-voice")\n',
    )
    replace_once(
        relative,
        '        self.assertIn("tempera-document", AUDIENCES)\n',
        '        self.assertIn("tempera-document", AUDIENCES)\n'
        '        self.assertIn("tempera-voice", AUDIENCES)\n',
    )
    replace_once(
        relative,
        '                "payments:webhooks:write", "payments:refunds:write", "payments:admin", "admin",\n',
        '                "payments:webhooks:write", "payments:refunds:write", "payments:admin",\n'
        '                "voice:read", "voice:write", "voice:stream", "admin",\n',
    )
    replace_once(
        relative,
        '        self.assertEqual(ENVIRONMENTS["production"]["temperaWorkflowsApiUrl"], "https://workflows.tempera.dev")\n',
        '        self.assertEqual(ENVIRONMENTS["production"]["temperaWorkflowsApiUrl"], "https://workflows.tempera.dev")\n'
        '        self.assertEqual(ENVIRONMENTS["production"]["temperaVoiceApiUrl"], "https://voice.tempera.dev")\n'
        '        self.assertEqual(ENVIRONMENTS["local"]["temperaVoiceApiUrl"], "http://127.0.0.1:8102")\n',
    )


def main() -> None:
    patch_typescript()
    patch_python()
    print("Aligned hand-authored TypeScript and Python SDK expectations with Tempera Voice")


if __name__ == "__main__":
    main()
