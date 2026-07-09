import assert from "node:assert/strict";
import { test } from "node:test";
import { TEMPERA_PRODUCTS, TEMPERA_SCOPES, createTemperaClient } from "../src/index.js";

test("exports the aggregated Tempera product surface", () => {
  assert.equal(TEMPERA_PRODUCTS.tempJs.repository, "https://github.com/tempera-dev/temp.js");
  assert.equal(TEMPERA_PRODUCTS.tempo.repository, "https://github.com/tempera-dev/tempo");
  assert.equal(TEMPERA_PRODUCTS.tempOS.repository, "https://github.com/tempera-dev/tempOS");
  assert.equal(TEMPERA_PRODUCTS.remi.repository, "https://github.com/tempera-dev/remi");
  assert.equal(TEMPERA_PRODUCTS.cradle.repository, "https://github.com/tempera-dev/cradle");
  assert.equal(TEMPERA_PRODUCTS.arrha.repository, "https://github.com/tempera-dev/arrha");
  assert.ok(TEMPERA_SCOPES.includes("mcp:invoke"));
  assert.ok(TEMPERA_SCOPES.includes("admin"));
});

test("client sends bearer-authenticated product requests", async () => {
  const calls = [];
  const client = createTemperaClient({
    accessToken: "token_123",
    endpoints: { remi: "https://remi.example.test" },
    fetch: async (url, options) => {
      calls.push({ url, options });
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    },
  });

  const result = await client.remi("/memory");
  assert.deepEqual(result, { ok: true });
  assert.equal(calls[0].url, "https://remi.example.test/memory");
  assert.equal(calls[0].options.headers.authorization, "Bearer token_123");
});
