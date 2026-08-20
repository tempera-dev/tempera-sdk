import assert from "node:assert/strict";
import { test } from "node:test";
import {
  MCP_ERROR_CODES,
  MCP_METHOD_HEADER,
  MCP_NAME_HEADER,
  MCP_PROTOCOL_VERSION,
  MCP_PROTOCOL_VERSION_HEADER,
  TemperaApiError,
  TemperaAuth,
  TemperaMcpClient,
  TemperaMcpError,
  TemperaMcpInputRequired,
  TemperaSdkError,
} from "../src/index.js";

function rpcResponse(payload, { status = 200 } = {}) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function gatewayClient(handler) {
  const calls = [];
  const client = new TemperaMcpClient({
    url: "https://api.tempera.dev/mcp",
    bearer: "tp_key_1",
    fetch: async (url, options) => {
      const request = JSON.parse(options.body);
      calls.push({ url, options, request });
      return handler(request);
    },
  });
  return { client, calls };
}

function discoveryResult() {
  return {
    resultType: "complete",
    supportedVersions: ["2026-07-28"],
    capabilities: { tools: {} },
    ttlMs: 0,
    cacheScope: "private",
  };
}

test("discovery alias and every request use the stateless protocol", async () => {
  const { client, calls } = gatewayClient((request) => {
    if (request.method === "tools/list") {
      return rpcResponse({
        jsonrpc: "2.0",
        id: request.id,
        result: { resultType: "complete", tools: [{ name: "tempera_whoami" }] },
      });
    }
    const result = request.method === "server/discover" ? discoveryResult() : {};
    return rpcResponse({ jsonrpc: "2.0", id: request.id, result });
  });
  await client.initialize({ name: "tempera-voice", version: "0.1.0" });
  await client.ping();
  const tools = await client.listTools();
  assert.deepEqual(tools, [{ name: "tempera_whoami" }]);
  for (const call of calls) {
    assert.equal(call.options.headers.authorization, "Bearer tp_key_1");
    assert.equal(call.options.headers[MCP_PROTOCOL_VERSION_HEADER], MCP_PROTOCOL_VERSION);
    assert.equal(call.options.headers[MCP_METHOD_HEADER], call.request.method);
    assert.equal(call.options.headers.accept, "application/json, text/event-stream");
    assert.equal(call.request.jsonrpc, "2.0");
    assert.ok(Number.isInteger(call.request.id));
    assert.equal(call.request.params._meta["io.modelcontextprotocol/protocolVersion"], MCP_PROTOCOL_VERSION);
    assert.deepEqual(call.request.params._meta["io.modelcontextprotocol/clientInfo"], {
      name: "tempera-voice",
      version: "0.1.0",
    });
    assert.deepEqual(call.request.params._meta["io.modelcontextprotocol/clientCapabilities"], {});
  }
  assert.equal(calls[0].request.method, "server/discover");
  assert.ok(!calls.some((call) => call.request.method === "initialize"));
  assert.equal(MCP_PROTOCOL_VERSION, "2026-07-28");
  assert.equal(calls[1].request.method, "ping");
  assert.equal(calls[2].request.method, "tools/list");
});

test("callTool, whoami, and status wrap tools/call", async () => {
  const { client, calls } = gatewayClient((request) =>
    rpcResponse({
      jsonrpc: "2.0",
      id: request.id,
      result: { resultType: "complete", content: [{ type: "text", text: "{}" }], isError: false },
    }),
  );
  await client.callTool("tempera_search", { query: "browser capability" });
  await client.whoami();
  await client.status();
  assert.equal(calls[0].request.method, "tools/call");
  assert.equal(calls[0].request.params.name, "tempera_search");
  assert.deepEqual(calls[0].request.params.arguments, { query: "browser capability" });
  assert.equal(calls[0].options.headers[MCP_NAME_HEADER], "tempera_search");
  assert.equal(calls[1].request.params.name, "tempera_whoami");
  assert.equal(calls[2].request.params.name, "tempera_status");
});

test("caller meta is preserved but protocol identity is authoritative", async () => {
  const { client, calls } = gatewayClient((request) => rpcResponse({ jsonrpc: "2.0", id: request.id, result: {} }));
  await client.rpc("ping", {
    _meta: {
      traceparent: "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01",
      "io.modelcontextprotocol/protocolVersion": "wrong",
    },
  });
  const meta = calls[0].request.params._meta;
  assert.equal(meta.traceparent, "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01");
  assert.equal(meta["io.modelcontextprotocol/protocolVersion"], "2026-07-28");
});

test("SSE notifications are ignored and the matching response is returned", async () => {
  const { client } = gatewayClient(
    (request) =>
      new Response(
        `event: message\ndata: {"jsonrpc":"2.0","method":"notifications/resources/updated"}\n\n` +
          `data: {"jsonrpc":"2.0","id":${request.id},"result":{"tools":[]}}\n\n`,
        { status: 200, headers: { "content-type": "text/event-stream" } },
      ),
  );
  assert.deepEqual(await client.rpc("tools/list"), { tools: [] });
});

test("same-id server requests are not mistaken for the correlated response", async () => {
  const { client } = gatewayClient(
    (request) =>
      new Response(
        `data: {"jsonrpc":"2.0","id":${request.id},"method":"sampling/createMessage","params":{}}\n\n` +
          `data: {"jsonrpc":"2.0","id":${request.id},"result":{}}\n\n`,
        { status: 200, headers: { "content-type": "text/event-stream" } },
      ),
  );
  assert.deepEqual(await client.ping(), {});
});

test("non-empty client capabilities are rejected until dispatch exists", () => {
  assert.throws(
    () =>
      new TemperaMcpClient({
        url: "https://api.tempera.dev/mcp",
        bearer: "tp_key_1",
        clientCapabilities: { sampling: {} },
      }),
    /must stay empty/,
  );
  assert.throws(
    () => new TemperaMcpClient({ url: "https://api.tempera.dev/mcp", bearer: "tp_key_1", clientName: "" }),
    /clientName/,
  );
});

test("discovery rejects empty dynamic client identity", async () => {
  const { client } = gatewayClient((request) => rpcResponse({ jsonrpc: "2.0", id: request.id, result: discoveryResult() }));
  await assert.rejects(() => client.discover({ version: "" }), /client version/);
});

test("invalid params, metadata, and missing response ids fail closed", async () => {
  const { client } = gatewayClient((request) => rpcResponse({ jsonrpc: "2.0", id: request.id + 1, result: {} }));
  await assert.rejects(() => client.rpc("ping", []), TemperaSdkError);
  await assert.rejects(() => client.rpc("ping", { _meta: [] }), TemperaSdkError);
  await assert.rejects(() => client.callTool("bad\r\nheader"), /safe routing value/);
  await assert.rejects(() => client.ping(), /omitted request id/);
});

test("invalid JSON-RPC envelopes, duplicate ids, and unsafe bearers fail closed", async () => {
  for (const handler of [
    () => rpcResponse({ jsonrpc: "2.0", id: true, result: {} }),
    (request) => rpcResponse({ jsonrpc: "1.0", id: request.id, result: {} }),
    (request) => rpcResponse({ jsonrpc: "2.0", id: request.id }),
    (request) => rpcResponse({ jsonrpc: "2.0", id: request.id, result: {}, error: {} }),
    (request) => rpcResponse({ jsonrpc: "2.0", id: request.id, result: {}, error: null }),
    (request) =>
      new Response(
        `data: {"jsonrpc":"2.0","id":${request.id},"result":{}}\n\n` +
          `data: {"jsonrpc":"2.0","id":${request.id},"result":{}}\n\n`,
        { status: 200, headers: { "content-type": "text/event-stream" } },
      ),
  ]) {
    const { client } = gatewayClient(handler);
    await assert.rejects(() => client.ping(), TemperaSdkError);
  }
  const { client } = gatewayClient((request) => rpcResponse({ jsonrpc: "2.0", id: request.id, result: {} }));
  await assert.rejects(() => client.rpc("tools/call", {}), /tool name/);
  await assert.rejects(() => client.callTool("tempera_status", []), /arguments must be an object/);
  const unsafe = new TemperaMcpClient({
    url: "https://api.tempera.dev/mcp",
    bearer: "token\r\nheader",
    fetch: async () => rpcResponse({ jsonrpc: "2.0", id: 1, result: {} }),
  });
  await assert.rejects(() => unsafe.ping(), /unsafe header/);
});

test("JSON-RPC errors raise TemperaMcpError with the gateway's code and data", async () => {
  const { client } = gatewayClient((request) =>
    rpcResponse({
      jsonrpc: "2.0",
      id: request.id,
      error: { code: MCP_ERROR_CODES.planLimit, message: "Plan limit exceeded.", data: { error: "plan_limit_exceeded" } },
    }),
  );
  await assert.rejects(
    () => client.callTool("tempera_search", { query: "browser capability" }),
    (error) => {
      assert.ok(error instanceof TemperaMcpError);
      assert.equal(error.code, -32002);
      assert.deepEqual(error.data, { error: "plan_limit_exceeded" });
      return true;
    },
  );
});

test("tool error and input_required outcomes never look completed", async () => {
  const outcomes = [
    { resultType: "complete", isError: true, content: [{ type: "text", text: "provider rejected the call" }] },
    { resultType: "input_required" },
    {
      resultType: "input_required",
      requestState: "opaque-next-step",
      inputRequests: {
        approval: {
          method: "elicitation/create",
          params: { message: "Approve?" },
        },
        roots: { method: "roots/list" },
      },
    },
    { resultType: "futureOutcome" },
    "not-an-object",
  ];
  const { client } = gatewayClient((request) =>
    rpcResponse({ jsonrpc: "2.0", id: request.id, result: outcomes.shift() }),
  );
  await assert.rejects(
    () => client.callTool("tempera_invoke"),
    (error) => {
      assert.ok(error instanceof TemperaMcpError);
      assert.equal(error.code, 0);
      assert.equal(error.data.isError, true);
      return true;
    },
  );
  await assert.rejects(
    () => client.callTool("tempera_execute_plan"),
    (error) => {
      assert.ok(error instanceof TemperaMcpError);
      assert.match(error.message, /malformed/);
      return true;
    },
  );
  await assert.rejects(
    () => client.callTool("tempera_execute_plan"),
    (error) => {
      assert.ok(error instanceof TemperaMcpInputRequired);
      assert.equal(error.result.requestState, "opaque-next-step");
      return true;
    },
  );
  await assert.rejects(
    () => client.callTool("tempera_execute_plan"),
    (error) => {
      assert.ok(error instanceof TemperaMcpError);
      assert.equal(error.data.resultType, "futureOutcome");
      return true;
    },
  );
  await assert.rejects(
    () => client.callTool("tempera_execute_plan"),
    (error) => {
      assert.ok(error instanceof TemperaMcpError);
      assert.equal(error.data, "not-an-object");
      return true;
    },
  );
});

test("discovery, catalogs, complete results, and continuation fail closed", async () => {
  const outcomes = [
    {},
    { ...discoveryResult(), supportedVersions: ["2025-06-18"] },
    { resultType: "complete", tools: {} },
    { resultType: "complete" },
    { resultType: "complete", content: [1] },
    { resultType: "complete", content: [{ type: "text", text: "x", _meta: [] }] },
    { resultType: "complete", content: [] },
  ];
  const { client, calls } = gatewayClient((request) =>
    rpcResponse({ jsonrpc: "2.0", id: request.id, result: outcomes.shift() }),
  );
  await assert.rejects(() => client.discover(), TemperaMcpError);
  await assert.rejects(() => client.discover(), TemperaMcpError);
  await assert.rejects(() => client.listTools(), TemperaMcpError);
  await assert.rejects(() => client.callTool("tempera_execute_plan"), /empty complete/);
  await assert.rejects(() => client.callTool("tempera_execute_plan"), /malformed complete/);
  await assert.rejects(() => client.callTool("tempera_execute_plan"), /malformed complete/);
  const result = await client.callTool(
    "tempera_execute_plan",
    {},
    { inputResponses: { approval: { accepted: true } }, requestState: "opaque-next-step" },
  );
  assert.equal(result.resultType, "complete");
  assert.deepEqual(calls.at(-1).request.params.inputResponses, { approval: { accepted: true } });
  assert.equal(calls.at(-1).request.params.requestState, "opaque-next-step");
});

test("HTTP auth failures raise TemperaApiError with the gateway error code", async () => {
  const { client } = gatewayClient(() =>
    rpcResponse({ error: "unauthenticated", message: "Bearer token required." }, { status: 401 }),
  );
  await assert.rejects(
    () => client.ping(),
    (error) => {
      assert.ok(error instanceof TemperaApiError);
      assert.equal(error.status, 401);
      assert.equal(error.code, "unauthenticated");
      return true;
    },
  );
});

test("the gateway URL derives from TemperaAuth when not passed explicitly", () => {
  const auth = new TemperaAuth({ issuerUrl: "https://api.tempera.dev/", apiKey: "tp_key_1" });
  const client = new TemperaMcpClient({ auth });
  assert.equal(client.url, "https://api.tempera.dev/mcp");
});

test("non-conformant error shapes fail closed as malformed envelopes", async () => {
  const { client } = gatewayClient(() => rpcResponse({ jsonrpc: "2.0", id: 1, error: "nope" }));
  await assert.rejects(() => client.ping(), /malformed error object/);
  const fractional = gatewayClient(() =>
    rpcResponse({ jsonrpc: "2.0", id: 1, error: { code: 1.5, message: "nope" } }),
  ).client;
  await assert.rejects(() => fractional.ping(), /malformed error object/);
});

test("an empty error object is not silently treated as success", async () => {
  const { client } = gatewayClient(() => rpcResponse({ jsonrpc: "2.0", id: 1, error: {} }));
  await assert.rejects(() => client.ping(), /malformed error object/);
});
