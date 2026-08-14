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

print("refreshed Voice SDK tests and control-plane registry assertion")
