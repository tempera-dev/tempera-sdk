#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, before: str, after: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if after in text:
        return
    count = text.count(before)
    if count != 1:
        raise SystemExit(f"{path}: expected one anchor, found {count}: {before[:100]!r}")
    target.write_text(text.replace(before, after, 1), encoding="utf-8")


# TypeScript: make Voice explicit where the test owns concrete URLs, and make
# registry assertions derive from producer-owned/generated contracts.
replace_once(
    "packages/typescript/test/client.test.mjs",
    '''      temperaLlm: "https://llm.example.test",
      temperaRisk: "https://risk.example.test",
''',
    '''      temperaLlm: "https://llm.example.test",
      temperaVoice: "https://voice.example.test",
      temperaRisk: "https://risk.example.test",
''',
)
replace_once(
    "packages/typescript/test/sdk.test.mjs",
    '''import assert from "node:assert/strict";
import { test } from "node:test";
''',
    '''import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
''',
)
replace_once(
    "packages/typescript/test/sdk.test.mjs",
    '''  assert.equal(TEMPERA_PRODUCTS.temperaLlm.repository, "https://github.com/tempera-dev/tempera-llm");
  assert.equal(TEMPERA_PRODUCTS.temperaRisk.repository, "https://github.com/tempera-dev/tempera-risk");
''',
    '''  assert.equal(TEMPERA_PRODUCTS.temperaLlm.repository, "https://github.com/tempera-dev/tempera-llm");
  assert.equal(TEMPERA_PRODUCTS.temperaVoice.repository, "https://github.com/tempera-dev/tempera-voice");
  assert.equal(TEMPERA_PRODUCTS.temperaRisk.repository, "https://github.com/tempera-dev/tempera-risk");
''',
)
replace_once(
    "packages/typescript/test/sdk.test.mjs",
    '''  assert.ok(TEMPERA_AUDIENCES.includes("tempera-llm"));
  assert.ok(TEMPERA_AUDIENCES.includes("tempera-risk"));
''',
    '''  assert.ok(TEMPERA_AUDIENCES.includes("tempera-llm"));
  assert.ok(TEMPERA_AUDIENCES.includes("tempera-voice"));
  assert.ok(TEMPERA_AUDIENCES.includes("tempera-risk"));
''',
)
path = ROOT / "packages/typescript/test/sdk.test.mjs"
text = path.read_text(encoding="utf-8")
start = text.find('test("scopes match the control-plane scope registry", () => {\n')
end = text.find('\ntest("all four environments carry the same target keys", () => {', start)
if start < 0 or end < 0:
    raise SystemExit("packages/typescript/test/sdk.test.mjs: scope test boundaries drifted")
replacement = '''test("scopes match the control-plane scope registry", () => {
  const controlPlane = JSON.parse(
    readFileSync(
      new URL("../../../specs/control-plane.openapi.json", import.meta.url),
      "utf8",
    ),
  );
  assert.deepEqual(
    [...TEMPERA_SCOPES],
    controlPlane.components.schemas.Scope.enum,
  );
});
'''
path.write_text(text[:start] + replacement + text[end:], encoding="utf-8")

# Python: consume the client-owned generated attribute map rather than keeping a
# second manual product registry in tests.
replace_once(
    "packages/python/tests/test_client.py",
    '''    normalize_error_body,
)

PRODUCT_ATTRS = {
    "controlPlane": "control_plane",
    "palette": "palette",
    "tempo": "tempo",
    "temperaLlm": "tempera_llm",
    "temperaRisk": "tempera_risk",
    "temperaWorkflows": "tempera_workflows",
    "temperaGym": "tempera_gym",
    "temperaBio": "tempera_bio",
    "temperaDocument": "tempera_document",
    "temperaPayments": "tempera_payments",
    "cradle": "cradle",
    "remi": "remi",
    "dataEngine": "data_engine",
    "humanData": "human_data",
    "tempJs": "temp_js",
    "tempOS": "temp_os",
    "arrha": "arrha",
}
''',
    '''    normalize_error_body,
)
from tempera_sdk.client import PRODUCT_ATTRS
''',
)
replace_once(
    "packages/python/tests/test_client.py",
    '''            "tempera_llm": "https://llm.example.test",
            "tempera_risk": "https://risk.example.test",
''',
    '''            "tempera_llm": "https://llm.example.test",
            "tempera_voice": "https://voice.example.test",
            "tempera_risk": "https://risk.example.test",
''',
)

# PRODUCT_AUDIENCES is a projection of PRODUCTS. Assert that relationship,
# rather than copying every product into a test literal.
replace_once(
    "packages/python/tests/test_auth.py",
    '''    PRODUCT_AUDIENCES,
    TemperaApiError,
''',
    '''    PRODUCT_AUDIENCES,
    PRODUCTS,
    TemperaApiError,
''',
)
auth_path = ROOT / "packages/python/tests/test_auth.py"
auth_text = auth_path.read_text(encoding="utf-8")
auth_start = auth_text.find(
    "    def test_product_audiences_derive_from_the_surface_registry(self):\n"
)
auth_end = auth_text.find("\n\n\nif __name__ == \"__main__\":", auth_start)
if auth_start < 0 or auth_end < 0:
    raise SystemExit("packages/python/tests/test_auth.py: product-audience test boundaries drifted")
auth_replacement = '''    def test_product_audiences_derive_from_the_surface_registry(self):
        expected = {
            key: (product["audience"], product["env_var"])
            for key, product in PRODUCTS.items()
            if product["audience"] is not None
        }
        self.assertEqual(PRODUCT_AUDIENCES, expected)
        self.assertEqual(
            PRODUCT_AUDIENCES["temperaVoice"],
            ("tempera-voice", "TEMPERA_VOICE_URL"),
        )
'''
auth_path.write_text(
    auth_text[:auth_start] + auth_replacement + auth_text[auth_end:],
    encoding="utf-8",
)

# Python scope parity also reads the exact vendored Auth Hub enum.
replace_once(
    "packages/python/tests/test_sdk.py",
    "import unittest\n",
    "import json\nimport unittest\nfrom pathlib import Path\n",
)
replace_once(
    "packages/python/tests/test_sdk.py",
    '''        self.assertEqual(PRODUCTS["temperaLlm"]["repository"], "https://github.com/tempera-dev/tempera-llm")
        self.assertEqual(PRODUCTS["temperaWorkflows"]["repository"], "https://github.com/tempera-dev/tempera-workflows")
''',
    '''        self.assertEqual(PRODUCTS["temperaLlm"]["repository"], "https://github.com/tempera-dev/tempera-llm")
        self.assertEqual(PRODUCTS["temperaVoice"]["repository"], "https://github.com/tempera-dev/tempera-voice")
        self.assertEqual(PRODUCTS["temperaWorkflows"]["repository"], "https://github.com/tempera-dev/tempera-workflows")
''',
)
replace_once(
    "packages/python/tests/test_sdk.py",
    '''        self.assertIn("tempera-llm", AUDIENCES)
        self.assertIn("tempera-workflows", AUDIENCES)
''',
    '''        self.assertIn("tempera-llm", AUDIENCES)
        self.assertIn("tempera-voice", AUDIENCES)
        self.assertIn("tempera-workflows", AUDIENCES)
''',
)
sdk_path = ROOT / "packages/python/tests/test_sdk.py"
sdk_text = sdk_path.read_text(encoding="utf-8")
sdk_start = sdk_text.find(
    "    def test_scopes_match_the_control_plane_scope_registry(self):\n"
)
sdk_end = sdk_text.find(
    "\n    def test_all_four_environments_carry_the_same_target_keys(self):",
    sdk_start,
)
if sdk_start < 0 or sdk_end < 0:
    raise SystemExit("packages/python/tests/test_sdk.py: scope test boundaries drifted")
sdk_replacement = '''    def test_scopes_match_the_control_plane_scope_registry(self):
        root = Path(__file__).resolve().parents[3]
        control_plane = json.loads(
            (root / "specs" / "control-plane.openapi.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            list(SCOPES),
            control_plane["components"]["schemas"]["Scope"]["enum"],
        )
'''
sdk_path.write_text(
    sdk_text[:sdk_start] + sdk_replacement + sdk_text[sdk_end:],
    encoding="utf-8",
)

print("refreshed Voice SDK tests and producer-derived registry assertions")
