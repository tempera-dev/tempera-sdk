import assert from "node:assert/strict";
import { test } from "node:test";
import {
  DEFAULT_AUDIENCE,
  TEMPERA_API_TARGETS,
  TEMPERA_AUDIENCES,
  TEMPERA_ENVIRONMENTS,
  TEMPERA_OPERATIONS,
  TEMPERA_PRODUCTS,
  TEMPERA_SCOPES,
} from "../src/index.js";

test("the product registry covers every Tempera product with palette included", () => {
  assert.equal(TEMPERA_PRODUCTS.controlPlane.repository, "https://github.com/tempera-dev/auth-hub");
  assert.equal(TEMPERA_PRODUCTS.palette.repository, "https://github.com/tempera-dev/palette");
  assert.equal(TEMPERA_PRODUCTS.tempo.repository, "https://github.com/tempera-dev/tempo");
  assert.equal(TEMPERA_PRODUCTS.temperaCode.repository, "https://github.com/tempera-dev/tempera-code");
  assert.equal(TEMPERA_PRODUCTS.temperaLlm.repository, "https://github.com/tempera-dev/tempera-llm");
  assert.equal(TEMPERA_PRODUCTS.temperaWorkflows.repository, "https://github.com/tempera-dev/tempera-workflows");
  assert.equal(TEMPERA_PRODUCTS.cradle.repository, "https://github.com/tempera-dev/cradle");
  assert.equal(TEMPERA_PRODUCTS.remi.repository, "https://github.com/tempera-dev/remi");
  assert.equal(TEMPERA_PRODUCTS.dataEngine.repository, "https://github.com/tempera-dev/data-engine");
  assert.equal(TEMPERA_PRODUCTS.humanData.repository, "https://github.com/tempera-dev/human-data");
  assert.equal(TEMPERA_PRODUCTS.tempJs.repository, "https://github.com/tempera-dev/temp.js");
  assert.equal(TEMPERA_PRODUCTS.tempOS.repository, "https://github.com/tempera-dev/tempOS");
  assert.equal(TEMPERA_PRODUCTS.arrha.repository, "https://github.com/tempera-dev/arrha");
});

test("audience-bearing products map to registered audiences", () => {
  for (const [key, product] of Object.entries(TEMPERA_PRODUCTS)) {
    if (product.audience !== null) {
      assert.ok(TEMPERA_AUDIENCES.includes(product.audience), `${key} audience registered`);
    }
  }
  assert.ok(TEMPERA_AUDIENCES.includes(DEFAULT_AUDIENCE));
  assert.ok(TEMPERA_AUDIENCES.includes("tempera-mcp"));
  assert.ok(TEMPERA_AUDIENCES.includes("human-data"));
  assert.ok(TEMPERA_AUDIENCES.includes("data-engine"));
  assert.ok(TEMPERA_AUDIENCES.includes("tempera-code"));
  assert.ok(TEMPERA_AUDIENCES.includes("tempera-llm"));
  assert.ok(TEMPERA_AUDIENCES.includes("tempera-workflows"));
});

test("scopes match the control-plane scope registry", () => {
  assert.deepEqual(
    [...TEMPERA_SCOPES],
    ["mcp:invoke", "trace:read", "trace:write", "dataset:read", "dataset:write", "eval:run", "workflow:read", "workflow:write", "workflow:run", "pii:unmask", "cyber:research", "clinical:run", "model:read", "model:invoke", "admin"],
  );
});

test("all four environments carry the same target keys", () => {
  const environmentNames = Object.keys(TEMPERA_ENVIRONMENTS);
  assert.deepEqual(environmentNames, ["local", "preview", "staging", "production"]);
  const keys = JSON.stringify(Object.keys(TEMPERA_ENVIRONMENTS.local).sort());
  for (const name of environmentNames) {
    assert.equal(JSON.stringify(Object.keys(TEMPERA_ENVIRONMENTS[name]).sort()), keys, name);
  }
  assert.equal(TEMPERA_ENVIRONMENTS.production.controlPlaneUrl, "https://api.tempera.dev");
  assert.equal(TEMPERA_ENVIRONMENTS.production.mcpGatewayUrl, "https://api.tempera.dev/mcp");
  assert.equal(TEMPERA_ENVIRONMENTS.production.paletteMcpUrl, "https://mcp.tempera.dev/mcp");
  assert.equal(TEMPERA_ENVIRONMENTS.production.tempoApiUrl, "https://tempo.tempera.dev");
  assert.equal(TEMPERA_ENVIRONMENTS.production.temperaCodeApiUrl, "https://code-api.tempera.dev");
  assert.equal(TEMPERA_ENVIRONMENTS.production.temperaLlmApiUrl, "https://llm.tempera.dev");
  assert.equal(TEMPERA_ENVIRONMENTS.production.temperaWorkflowsApiUrl, "https://workflows.tempera.dev");
  // Deprecated alias points at the same object.
  assert.equal(TEMPERA_API_TARGETS, TEMPERA_ENVIRONMENTS);
});

test("every operation has a unique name and a sentence description", () => {
  for (const [productKey, ops] of Object.entries(TEMPERA_OPERATIONS)) {
    const seen = new Set();
    for (const op of ops) {
      assert.ok(!seen.has(op.id), `${productKey}.${op.id} unique`);
      seen.add(op.id);
      assert.match(op.id, /^[a-z][a-zA-Z0-9]*$/, `${productKey}.${op.id} lowerCamelCase`);
      assert.match(op.description, /^[A-Z].*\.$/, `${productKey}.${op.id} description sentence`);
      assert.ok(["GET", "POST", "PUT", "PATCH", "DELETE"].includes(op.method));
    }
  }
});
