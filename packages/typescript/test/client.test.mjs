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

function samplePathParam(op, key) {
  return op.pathParamTemplates?.[key]?.replaceAll("*", SAMPLE_PARAM_VALUE) ?? SAMPLE_PARAM_VALUE;
}

test("every surface operation dispatches its method, path, and auth header", async () => {
  const { client, calls } = testClient();
  for (const [productKey, ops] of Object.entries(TEMPERA_OPERATIONS)) {
    for (const op of ops) {
      calls.length = 0;
      const params = {};
      for (const key of op.pathParams) params[key] = samplePathParam(op, key);
      const result = await client[productKey][op.id](params);
      assert.deepEqual(result, { ok: true }, `${productKey}.${op.id} result`);
      assert.equal(calls.length, 1, `${productKey}.${op.id} made one request`);
      const { url, options } = calls[0];
      assert.equal(options.method, op.method, `${productKey}.${op.id} method`);
      const expectedPath = op.path.replace(
        /\{([A-Za-z_][A-Za-z0-9_]*)\}/g,
        (_, key) => samplePathParam(op, key),
      );
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
      // Declared body defaults must reach the wire.
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

  await client.palette.scenariosList({
    tenant_id: "t1",
    project_id: "p1",
    pageSize: 12,
    pageToken: "scenarios-token",
  });
  assert.equal(calls.at(-1).url.pathname, "/v1/scenarios/t1/p1");
  assert.equal(calls.at(-1).url.searchParams.get("pageSize"), "12");
  assert.equal(calls.at(-1).url.searchParams.get("pageToken"), "scenarios-token");
  assert.equal(calls.at(-1).url.searchParams.get("limit"), null);
  assert.equal(calls.at(-1).url.searchParams.get("cursor"), null);

  for (const [operation, params] of [
    ["listUseCases", { parent: "projects/p1", pageSize: 2, pageToken: "use-cases-token" }],
    ["getJobResults", { parent: "projects/p1", jobId: "job-1", pageSize: 3, pageToken: "results-token" }],
    ["listTools", { parent: "projects/p1", pageSize: 4, pageToken: "tools-token" }],
  ]) {
    await client.dataEngine[operation](params);
    const url = calls.at(-1).url;
    assert.equal(url.searchParams.get("pageSize"), String(params.pageSize), operation);
    assert.equal(url.searchParams.get("pageToken"), params.pageToken, operation);
    assert.equal(url.searchParams.get("page_size"), null, operation);
    assert.equal(url.searchParams.get("page_token"), null, operation);
  }
  await client.remi.listAudit({ pageSize: 5, pageToken: "audit-token" });
  assert.equal(calls.at(-1).url.searchParams.get("pageSize"), "5");
  assert.equal(calls.at(-1).url.searchParams.get("pageToken"), "audit-token");
  assert.equal(calls.at(-1).url.searchParams.get("limit"), null);

  await client.temperaLlm.listModels({ pageSize: 6, pageToken: "models-token" });
  assert.equal(calls.at(-1).url.searchParams.get("pageSize"), "6");
  assert.equal(calls.at(-1).url.searchParams.get("pageToken"), "models-token");
  assert.equal(calls.at(-1).url.searchParams.get("limit"), null);

  await client.temperaGym.listEnvironments({ pageSize: 7, pageToken: "environments-token" });
  assert.equal(calls.at(-1).url.searchParams.get("pageSize"), "7");
  assert.equal(calls.at(-1).url.searchParams.get("pageToken"), "environments-token");
  assert.equal(calls.at(-1).url.searchParams.get("limit"), null);
  await client.temperaGym.listRuns({
    environmentId: "env-1",
    pageSize: 8,
    pageToken: "runs-token",
  });
  assert.equal(calls.at(-1).url.searchParams.get("environmentId"), "env-1");
  assert.equal(calls.at(-1).url.searchParams.get("pageSize"), "8");
  assert.equal(calls.at(-1).url.searchParams.get("pageToken"), "runs-token");
  assert.equal(calls.at(-1).url.searchParams.get("environment_id"), null);
  await client.temperaGym.createRollout({ environmentId: "env-1", seed: 42 });
  assert.deepEqual(JSON.parse(calls.at(-1).options.body), {
    environmentId: "env-1",
    seed: 42,
  });

  for (const [operation, params] of [
    ["listNodeTypes", { pageSize: 9, pageToken: "node-types-token" }],
    ["listWorkflows", { pageSize: 10, pageToken: "workflows-token" }],
    [
      "listRuns",
      {
        workflowId: "workflow-1",
        pageSize: 11,
        pageToken: "workflow-runs-token",
      },
    ],
  ]) {
    await client.temperaWorkflows[operation](params);
    const url = calls.at(-1).url;
    assert.equal(url.searchParams.get("pageSize"), String(params.pageSize), operation);
    assert.equal(url.searchParams.get("pageToken"), params.pageToken, operation);
    assert.equal(url.searchParams.get("limit"), null, operation);
    assert.equal(url.searchParams.get("cursor"), null, operation);
  }
  assert.equal(calls.at(-1).url.searchParams.get("workflowId"), "workflow-1");
  await client.temperaWorkflows.updateWorkflow({
    workflowId: "workflow-1",
    updateMask: "definition",
    contractVersion: "v1",
    id: "workflow-1",
    name: "Smoke",
    nodes: [],
    edges: [],
  });
  assert.equal(calls.at(-1).options.method, "PATCH");
  assert.equal(calls.at(-1).url.searchParams.get("updateMask"), "definition");

  for (const [operation, params, expectedPath] of [
    ["runUseCase", { parent: "projects/p1", use_case: "smoke" }, "/v1/projects/p1/pipelines:runUseCase"],
    [
      "saveExpertTaskDraft",
      {
        parent: "projects/p1",
        expertTaskId: "task-1",
        idempotency_key: "idem-1",
        lease_token: "lease-1",
        draft: {},
        expected_version: 1,
      },
      "/v1/projects/p1/expert-tasks/task-1:saveDraft",
    ],
    [
      "checkProductLeakage",
      { parent: "projects/p1", product_ids: ["products/a", "products/b"] },
      "/v1/projects/p1/products:checkLeakage",
    ],
    [
      "emitEval",
      { parent: "projects/p1", artifact_ids: ["artifacts/a"], job: {} },
      "/v1/projects/p1/products:emitEval",
    ],
  ]) {
    await client.dataEngine[operation](params);
    assert.equal(calls.at(-1).url.pathname, expectedPath, operation);
  }

  await client.remi.remember({ tenant_id: "t1", project_id: "p1", kind: "fact", text: "hello" });
  const body = JSON.parse(calls.at(-1).options.body);
  assert.deepEqual(body, {
    tenant_id: "t1",
    project_id: "p1",
    kind: "fact",
    text: "hello",
  });
  const query = {
    question: "Which workflow evidence is current?",
    scope: {
      tenant_id: "t1",
      project_id: "p1",
      environment_id: "dev",
      as_of_unix_ms: null,
    },
    max_tokens: 600,
    require_fresh: true,
    modes: ["procedural", "gotcha", "state"],
    reconstruction_mode: "off",
  };
  await client.remi.query(query);
  assert.deepEqual(JSON.parse(calls.at(-1).options.body), query);
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
  await client.dataEngine.ingestArtifact({ parent: "projects/p1", envelopes: [] });
  assert.equal(calls[0].url.pathname, "/v1/projects/p1/artifacts:ingest");
  assert.ok(calls[0].url.toString().endsWith("/v1/projects/p1/artifacts:ingest"));
  assert.ok(!calls[0].url.toString().includes("%3A"), "colon must not be percent-encoded");
  // Colons inside a substituted path *value* are still encoded.
  await client.dataEngine.getJob({ parent: "projects/p1", jobId: "job:1" });
  assert.equal(calls[1].url.pathname, "/v1/projects/p1/jobs/job%3A1");
  await assert.rejects(
    () => client.dataEngine.ingestArtifact({ parent: "projects/../secrets" }),
    /must match AIP resource pattern "projects\/\*"/,
  );
  await assert.rejects(
    () => client.dataEngine.ingestArtifact({ parent: "organizations/p1" }),
    /must match AIP resource pattern "projects\/\*"/,
  );
});

test("missing path parameters fail fast with a clear message", async () => {
  const { client } = testClient();
  await assert.rejects(
    () => client.palette.getTrace({ tenant_id: "t1" }),
    (error) =>
      error instanceof TemperaSdkError && error.message.includes('missing required path parameter "trace_id"'),
  );
});

test("createHostedSession stores the account token for later control-plane calls", async () => {
  const calls = [];
  const client = createTemperaClient({
    baseUrls: { controlPlane: "https://cp.example.test" },
    fetch: async (url, options) => {
      calls.push({ url: new URL(url), options });
      if (calls.length === 1) return jsonResponse({ access_token: "account_at_1", token_type: "Bearer" });
      return jsonResponse({ sub: "user_1" });
    },
  });
  await client.controlPlane.createHostedSession({ mode: "login", email: "demo@tempera.dev", password: "tempera-demo" });
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
    (error) => error instanceof TemperaSdkError && error.message.includes("createHostedSession()"),
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

test("environment presets resolve control-plane, palette, and product gateway base URLs", async () => {
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
  await client.temperaLlm.health();
  await client.temperaWorkflows.health();
  await client.temperaGym.health();
  assert.equal(calls[0].origin, "https://api.tempera.dev");
  assert.equal(calls[1].origin, "https://mcp.tempera.dev");
  assert.equal(calls[2].origin, "https://llm.tempera.dev");
  assert.equal(calls[3].origin, "https://workflows.tempera.dev");
  assert.equal(calls[4].origin, "https://gym.tempera.dev");
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
