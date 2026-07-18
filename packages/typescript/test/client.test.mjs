import assert from "node:assert/strict";
import { test } from "node:test";
import {
  TEMPERA_OPERATIONS,
  TEMPERA_PRODUCTS,
  TemperaApiError,
  TemperaAuth,
  TemperaSdkError,
  createTemperaClient,
  normalizeErrorBody,
} from "../src/index.js";

function jsonResponse(body, { status = 200, headers = {} } = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", ...headers },
  });
}

function testClient(overrides = {}) {
  const calls = [];
  const client = createTemperaClient({
    auth: new TemperaAuth({ issuerUrl: "https://api.tempera.dev", apiKey: "tp_key_1" }),
    accountToken: "account_token_1",
    introspectionSecret: "introspect_secret_1",
    baseUrls: {
      controlPlane: "https://cp.example.test",
      palette: "https://palette.example.test",
      tempo: "https://tempo.example.test",
      temperaCode: "https://code.example.test",
      temperaLlm: "https://llm.example.test",
      temperaWorkflows: "https://workflows.example.test",
      temperaGym: "https://gym.example.test",
      cradle: "https://cradle.example.test",
      remi: "https://remi.example.test",
      dataEngine: "https://data-engine.example.test",
      humanData: "https://human.example.test",
      tempJs: "https://tempjs.example.test",
      tempOS: "https://tempos.example.test",
      arrha: "https://arrha.example.test",
    },
    fetch: async (url, options) => {
      calls.push({ url: new URL(url), options });
      return jsonResponse({ ok: true });
    },
    ...overrides,
  });
  return { client, calls };
}

const SAMPLE_PARAM_VALUE = "sample-value";

test("every surface operation dispatches its method, path, and auth header", async () => {
  const { client, calls } = testClient();
  for (const [productKey, ops] of Object.entries(TEMPERA_OPERATIONS)) {
    for (const op of ops) {
      calls.length = 0;
      const params = {};
      for (const key of op.pathParams) params[key] = SAMPLE_PARAM_VALUE;
      const result = await client[productKey][op.id](params);
      assert.deepEqual(result, { ok: true }, `${productKey}.${op.id} result`);
      assert.equal(calls.length, 1, `${productKey}.${op.id} made one request`);
      const { url, options } = calls[0];
      assert.equal(options.method, op.method, `${productKey}.${op.id} method`);
      const expectedPath = op.path.replace(/\{[a-z_]+\}/g, SAMPLE_PARAM_VALUE);
      assert.equal(url.pathname, expectedPath, `${productKey}.${op.id} path`);
      const authHeader = options.headers.authorization;
      if (op.auth === "none") {
        assert.equal(authHeader, undefined, `${productKey}.${op.id} sends no bearer`);
      } else if (op.auth === "account") {
        assert.equal(authHeader, "Bearer account_token_1", `${productKey}.${op.id} account bearer`);
      } else if (op.auth === "introspectionSecret") {
        assert.equal(authHeader, "Bearer introspect_secret_1", `${productKey}.${op.id} introspection bearer`);
      } else {
        assert.equal(authHeader, "Bearer tp_key_1", `${productKey}.${op.id} product bearer`);
      }
      // Body defaults (e.g. login/signup mode) must reach the wire.
      for (const [key, value] of Object.entries(op.bodyDefaults ?? {})) {
        const body = JSON.parse(options.body);
        assert.equal(body[key], value, `${productKey}.${op.id} body default ${key}`);
      }
    }
  }
});

test("declared query and body parameters are routed to the right place", async () => {
  const { client, calls } = testClient();
  await client.palette.listTraces({ tenant_id: "t1", limit: 5, cursor: "abc" });
  assert.equal(calls[0].url.pathname, "/v1/traces/t1");
  assert.equal(calls[0].url.searchParams.get("limit"), "5");
  assert.equal(calls[0].url.searchParams.get("cursor"), "abc");
  assert.equal(calls[0].options.body, undefined);

  await client.remi.remember({ kind: "fact", text: "hello" });
  const body = JSON.parse(calls[1].options.body);
  assert.deepEqual(body, { kind: "fact", text: "hello" });
  const context = { question: "Which workflow evidence is current?", max_tokens: 600, require_fresh: true, modes: ["procedural", "gotcha", "state"], reconstruction_mode: "off" };
  await client.remi.context(context);
  assert.deepEqual(JSON.parse(calls.at(-1).options.body), context);
  const feedback = { schema: "remi.memory_feedback.v2", retrieval_receipt_id: "receipt_1", evidence_node_id: "node_1", helpful: true, terminal_state: "succeeded", outcome_artifact_id: "test://sdk/generated-wire", idempotency_key: "feedback_1" };
  await client.remi.feedback(feedback);
  assert.deepEqual(JSON.parse(calls.at(-1).options.body), feedback);
  await assert.rejects(client.remi.remember({ tenant_id: "t1", kind: "fact", text: "nope" }), /derived from the authenticated principal/);
  await assert.rejects(client.remi.context({ tenant_id: "t1", question: "what is current?" }), /derived from the authenticated principal/);
  await assert.rejects(client.remi.feedback({ environment_id: "prod", ...feedback }), /derived from the authenticated principal/);
  const beforeCalls = calls.length;
  for (const field of ["scope", "tenant_id", "project_id", "environment_id"]) {
    await assert.rejects(client.remi.context({ question: "what is current?", [field]: null }), /derived from the authenticated principal/);
  }
  assert.equal(calls.length, beforeCalls);
});

test("undeclared parameters pass through for forward compatibility", async () => {
  const { client, calls } = testClient();
  await client.tempo.listSessions({ future_filter: "x" });
  assert.equal(calls[0].url.searchParams.get("future_filter"), "x");
  await client.cradle.execute({ lane: "wasm", source: "s", future_field: 7 });
  assert.equal(JSON.parse(calls[1].options.body).future_field, 7);
});

test("action-suffix paths keep the literal colon un-encoded", async () => {
  const { client, calls } = testClient();
  await client.dataEngine.ingestArtifact({ project_id: "p1", envelopes: [] });
  assert.equal(calls[0].url.pathname, "/v1/projects/p1/artifacts:ingest");
  assert.ok(calls[0].url.toString().endsWith("/v1/projects/p1/artifacts:ingest"));
  assert.ok(!calls[0].url.toString().includes("%3A"), "colon must not be percent-encoded");
  // Colons inside a substituted path *value* are still encoded.
  await client.dataEngine.getJob({ project_id: "p1", job_id: "job:1" });
  assert.equal(calls[1].url.pathname, "/v1/projects/p1/jobs/job%3A1");
});

test("missing path parameters fail fast with a clear message", async () => {
  const { client } = testClient();
  await assert.rejects(
    () => client.palette.getTrace({ tenant_id: "t1" }),
    (error) =>
      error instanceof TemperaSdkError && error.message.includes('missing required path parameter "trace_id"'),
  );
});

test("login and signup store the account token for later control-plane calls", async () => {
  const calls = [];
  const client = createTemperaClient({
    baseUrls: { controlPlane: "https://cp.example.test" },
    fetch: async (url, options) => {
      calls.push({ url: new URL(url), options });
      if (calls.length === 1) return jsonResponse({ access_token: "account_at_1", token_type: "Bearer" });
      return jsonResponse({ sub: "user_1" });
    },
  });
  await client.controlPlane.login({ email: "demo@tempera.dev", password: "tempera-demo" });
  assert.equal(JSON.parse(calls[0].options.body).mode, "login");
  assert.equal(client.accountToken, "account_at_1");
  await client.controlPlane.me();
  assert.equal(calls[1].options.headers.authorization, "Bearer account_at_1");
});

test("account operations without a token fail with guidance", async () => {
  const client = createTemperaClient({
    baseUrls: { controlPlane: "https://cp.example.test" },
    fetch: async () => jsonResponse({}),
  });
  await assert.rejects(
    () => client.controlPlane.me(),
    (error) => error instanceof TemperaSdkError && error.message.includes("login()/signup()"),
  );
});

test("product operations without credentials fail with guidance", async () => {
  const client = createTemperaClient({
    baseUrls: { palette: "https://palette.example.test" },
    fetch: async () => jsonResponse({}),
  });
  await assert.rejects(
    () => client.palette.listTraces({ tenant_id: "t1" }),
    (error) => error instanceof TemperaSdkError && error.message.includes("TemperaAuth"),
  );
});

test("audience-matched bearers win over the API key fallback", async () => {
  const { client, calls } = testClient({
    auth: new TemperaAuth({
      issuerUrl: "https://api.tempera.dev",
      apiKey: "tp_key_1",
      tokens: { tempo: { accessToken: "at_tempo" }, remi: { accessToken: "at_remi" } },
    }),
  });
  await client.tempo.listSessions();
  await client.remi.getStats();
  await client.cradle.getCapabilities();
  assert.equal(calls[0].options.headers.authorization, "Bearer at_tempo");
  assert.equal(calls[1].options.headers.authorization, "Bearer at_remi");
  assert.equal(calls[2].options.headers.authorization, "Bearer tp_key_1");
});

test("passthrough request covers products without typed operations", async () => {
  const { client, calls } = testClient();
  const result = await client.tempJs.request("/runtime/status");
  assert.deepEqual(result, { ok: true });
  assert.equal(calls[0].url.toString(), "https://tempjs.example.test/runtime/status");
});

test("environment presets resolve control-plane, palette, Tempera Code, and tempera-llm base URLs", async () => {
  const calls = [];
  const client = createTemperaClient({
    environment: "production",
    fetch: async (url) => {
      calls.push(new URL(url));
      return jsonResponse({ ok: true });
    },
  });
  await client.controlPlane.health();
  await client.palette.health();
  await client.temperaCode.health();
  await client.temperaLlm.health();
  await client.temperaWorkflows.health();
  await client.temperaGym.health();
  assert.equal(calls[0].origin, "https://api.tempera.dev");
  assert.equal(calls[1].origin, "https://mcp.tempera.dev");
  assert.equal(calls[2].origin, "https://code-api.tempera.dev");
  assert.equal(calls[3].origin, "https://llm.tempera.dev");
  assert.equal(calls[4].origin, "https://workflows.tempera.dev");
  assert.equal(calls[5].origin, "https://gym.tempera.dev");
});

test("HTTP errors normalize every fleet wire shape into TemperaApiError", async () => {
  const shapes = [
    // control plane / palette: flat code + message
    { body: { error: "missing_scope", message: "Scope is required." }, code: "missing_scope", message: "Scope is required." },
    // tempo: flat human message only
    { body: { error: "session not found" }, code: null, message: "session not found" },
    // remi: nested code + message
    { body: { error: { code: "rate_limited", message: "Too many requests." } }, code: "rate_limited", message: "Too many requests." },
    // cradle: nested rich shape with request id
    {
      body: { error: { code: "invalid_json", message: "Bad body.", request_id: "req-123", retryable: false } },
      code: "invalid_json",
      message: "Bad body.",
      requestId: "req-123",
    },
    // data-engine: same nested rich shape, uppercase codes + details array
    {
      body: {
        error: { code: "INVALID_ARGUMENT", message: "Bad envelope.", status: 400, request_id: "req-de-1", retryable: false, details: [] },
      },
      code: "INVALID_ARGUMENT",
      message: "Bad envelope.",
      requestId: "req-de-1",
    },
  ];
  for (const shape of shapes) {
    const client = createTemperaClient({
      accountToken: "t",
      baseUrls: { controlPlane: "https://cp.example.test" },
      fetch: async () => jsonResponse(shape.body, { status: 403 }),
    });
    await assert.rejects(
      () => client.controlPlane.me(),
      (error) => {
        assert.ok(error instanceof TemperaApiError);
        assert.equal(error.status, 403);
        assert.equal(error.code, shape.code);
        assert.ok(error.message.includes(shape.message));
        if (shape.requestId) assert.equal(error.requestId, shape.requestId);
        assert.equal(error.product, "controlPlane");
        assert.equal(error.operation, "me");
        return true;
      },
    );
  }
});

test("requestId falls back to the x-request-id response header", async () => {
  const client = createTemperaClient({
    accountToken: "t",
    baseUrls: { controlPlane: "https://cp.example.test" },
    fetch: async () =>
      jsonResponse({ error: "unauthenticated", message: "No." }, { status: 401, headers: { "x-request-id": "req_hdr_1" } }),
  });
  await assert.rejects(
    () => client.controlPlane.me(),
    (error) => error instanceof TemperaApiError && error.requestId === "req_hdr_1",
  );
});

test("normalizeErrorBody handles unknown and empty bodies", () => {
  assert.deepEqual(normalizeErrorBody(null, "Bad Gateway"), { code: null, message: "Bad Gateway", requestId: null });
  assert.deepEqual(normalizeErrorBody("nonsense", "Oops"), { code: null, message: "Oops", requestId: null });
});

test("every product client carries its registry metadata", () => {
  const { client } = testClient();
  for (const [key, product] of Object.entries(TEMPERA_PRODUCTS)) {
    assert.equal(client[key].name, product.name, `${key} name`);
    assert.equal(client[key].envVar, product.envVar, `${key} envVar`);
    assert.equal(client[key].audience, product.audience, `${key} audience`);
    assert.ok(client[key].description.endsWith("."), `${key} description`);
    assert.equal(typeof client[key].request, "function", `${key} passthrough`);
  }
});
