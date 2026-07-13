import assert from "node:assert/strict";
import { test } from "node:test";
import {
  MCP_ERROR_CODES,
  TemperaApiError,
  TemperaAuth,
  TemperaMcpClient,
  TemperaMcpError,
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
    autoInitialize: false,
    fetch: async (url, options) => {
      const request = JSON.parse(options.body);
      calls.push({ url, options, request });
      return handler(request, options);
    },
  });
  return { client, calls };
}

test("initialize, ping, and tools/list send well-formed JSON-RPC with the bearer", async () => {
  const { client, calls } = gatewayClient((request) => {
    if (request.method === "initialize") {
      return rpcResponse({
        jsonrpc: "2.0",
        id: request.id,
        result: { protocolVersion: "2025-11-25", capabilities: {}, serverInfo: { name: "gateway", version: "1" } },
      });
    }
    if (request.method === "tools/list") {
      return rpcResponse({ jsonrpc: "2.0", id: request.id, result: { tools: [{ name: "tempera_whoami" }] } });
    }
    return rpcResponse({ jsonrpc: "2.0", id: request.id, result: {} });
  });
  await client.initialize();
  await client.ping();
  const tools = await client.listTools();
  assert.deepEqual(tools, [{ name: "tempera_whoami" }]);
  for (const call of calls) {
    assert.equal(call.options.headers.authorization, "Bearer tp_key_1");
    assert.equal(call.options.headers.accept, "application/json, text/event-stream");
    assert.equal(call.options.redirect, "error");
    assert.equal(call.request.jsonrpc, "2.0");
  }
  assert.equal(calls[0].request.method, "initialize");
  assert.equal(calls[0].request.params.protocolVersion, "2025-11-25");
  assert.equal(calls[1].request.method, "notifications/initialized");
  assert.equal(calls[2].request.method, "ping");
  assert.equal(calls[3].request.method, "tools/list");
});

test("initialize rejects an unsupported negotiated protocol version", async () => {
  const { client, calls } = gatewayClient((request) => rpcResponse({
    jsonrpc: "2.0",
    id: request.id,
    result: { protocolVersion: "2099-01-01", capabilities: {}, serverInfo: { name: "gateway", version: "1" } },
  }));
  await assert.rejects(() => client.initialize(), /did not negotiate supported protocol version/);
  assert.equal(calls.length, 1);
  assert.equal(client.sessionId, null);
  assert.equal(client.initialized, false);
});

test("constructor and request timeouts reject invalid values", async () => {
  assert.throws(
    () => new TemperaMcpClient({ url: "https://api.tempera.dev/mcp", bearer: "token", timeoutMs: -1 }),
    /non-negative integer/,
  );
  const { client } = gatewayClient(() => rpcResponse({ jsonrpc: "2.0", id: 1, result: {} }));
  await assert.rejects(() => client.ping({ timeoutMs: 1.5 }), /non-negative integer/);
});

test("callTool, whoami, and status wrap tools/call", async () => {
  const { client, calls } = gatewayClient((request) =>
    rpcResponse({ jsonrpc: "2.0", id: request.id, result: { content: [{ type: "text", text: "{}" }], isError: false } }),
  );
  await client.callTool("cradle_get_capabilities", { verbose: true });
  await client.whoami();
  await client.status();
  assert.equal(calls[0].request.method, "tools/call");
  assert.deepEqual(calls[0].request.params, { name: "cradle_get_capabilities", arguments: { verbose: true } });
  assert.equal(calls[1].request.params.name, "tempera_whoami");
  assert.equal(calls[2].request.params.name, "tempera_status");
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
    () => client.callTool("palette_list_traces"),
    (error) => {
      assert.ok(error instanceof TemperaMcpError);
      assert.equal(error.code, -32002);
      assert.deepEqual(error.data, { error: "plan_limit_exceeded" });
      return true;
    },
  );
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

test("non-conformant string errors raise TemperaMcpError with code 0", async () => {
  const { client } = gatewayClient(() => rpcResponse({ jsonrpc: "2.0", id: 1, error: "nope" }));
  await assert.rejects(
    () => client.ping(),
    (error) => {
      assert.ok(error instanceof TemperaMcpError);
      assert.equal(error.code, 0);
      assert.equal(error.message, "nope");
      return true;
    },
  );
});

test("auto initialization preserves sessions and parses SSE responses", async () => {
  const calls = [];
  const client = new TemperaMcpClient({
    url: "https://api.tempera.dev/mcp",
    bearer: "tp_key_1",
    fetch: async (_url, options) => {
      const request = JSON.parse(options.body);
      calls.push({ request, headers: options.headers });
      if (request.method === "initialize") {
        return new Response(
          `data: \nid: 0\nretry: 3000\n\nevent: message\ndata: ${JSON.stringify({
            jsonrpc: "2.0",
            id: request.id,
            result: { protocolVersion: "2025-11-25", capabilities: {}, serverInfo: { name: "gateway", version: "1" } },
          })}\n\n`,
          { headers: { "content-type": "text/event-stream", "mcp-session-id": "session_1" } },
        );
      }
      if (request.method === "notifications/initialized") return new Response(null, { status: 202 });
      return new Response(
        `data: ${JSON.stringify({ jsonrpc: "2.0", id: request.id, result: { tools: [] } })}\n\n`,
        { headers: { "content-type": "text/event-stream" } },
      );
    },
  });

  assert.deepEqual(await client.listTools(), []);
  assert.equal(client.sessionId, "session_1");
  assert.equal(calls[0].request.method, "initialize");
  assert.equal(calls[1].headers["mcp-session-id"], "session_1");
  assert.equal(calls[2].headers["mcp-session-id"], "session_1");
  assert.equal(calls[2].headers["mcp-protocol-version"], "2025-11-25");
});

test("tool pagination and progressive discovery helpers are bounded and compact", async () => {
  const { client, calls } = gatewayClient((request) => {
    if (request.method === "tools/list") {
      return rpcResponse({
        jsonrpc: "2.0",
        id: request.id,
        result: request.params?.cursor
          ? { tools: [{ name: "second" }] }
          : { tools: [{ name: "first" }], nextCursor: "page-2" },
      });
    }
    return rpcResponse({ jsonrpc: "2.0", id: request.id, result: { structuredContent: [] } });
  });

  assert.deepEqual(await client.listTools(), [{ name: "first" }, { name: "second" }]);
  await client.searchTools("traces", { server: "palette", limit: 3 });
  await client.describeTool("palette_list_traces");
  await client.callDiscoveredTool("palette_list_traces", { limit: 5 });
  assert.deepEqual(calls[1].request.params, { cursor: "page-2" });
  assert.deepEqual(calls[2].request.params.arguments, {
    query: "traces",
    server: "palette",
    limit: 3,
    includeSchema: false,
  });
  assert.equal(calls[3].request.params.name, "tempera_describe_tool");
  assert.equal(calls[4].request.params.name, "tempera_call");
});

test("list pagination enforces an item bound", async () => {
  const client = new TemperaMcpClient({
    url: "https://api.tempera.dev/mcp",
    bearer: "tp_key_1",
    autoInitialize: false,
    maxItems: 1,
    fetch: async (_url, options) => {
      const request = JSON.parse(options.body);
      return rpcResponse({
        jsonrpc: "2.0",
        id: request.id,
        result: { tools: [{ name: "one" }, { name: "two" }] },
      });
    },
  });
  await assert.rejects(() => client.listTools(), /tools\/list exceeded 1 items/);
});

test("list pagination rejects malformed cursors", async () => {
  const client = new TemperaMcpClient({
    url: "https://api.tempera.dev/mcp",
    bearer: "tp_key_1",
    autoInitialize: false,
    fetch: async (_url, options) => {
      const request = JSON.parse(options.body);
      return rpcResponse({
        jsonrpc: "2.0",
        id: request.id,
        result: { tools: [], nextCursor: 42 },
      });
    },
  });
  await assert.rejects(() => client.listTools(), /invalid nextCursor/);
});

test("aborting a list request sends an MCP cancellation notification", async () => {
  const requests = [];
  let markStarted;
  const started = new Promise((resolve) => { markStarted = resolve; });
  const client = new TemperaMcpClient({
    url: "https://api.tempera.dev/mcp",
    bearer: "tp_key_1",
    autoInitialize: false,
    fetch: async (_url, options) => {
      const request = JSON.parse(options.body);
      requests.push(request);
      if (request.method === "notifications/cancelled") return new Response(null, { status: 202 });
      markStarted();
      return new Promise((_resolve, reject) => {
        const abort = () => reject(options.signal.reason ?? new Error("aborted"));
        if (options.signal.aborted) abort();
        else options.signal.addEventListener("abort", abort, { once: true });
      });
    },
  });
  const controller = new AbortController();
  const pending = client.listTools({ signal: controller.signal });
  await started;
  controller.abort(new Error("stop list"));
  await assert.rejects(pending, /stop list/);
  for (let attempt = 0; attempt < 10 && requests.length < 2; attempt += 1) {
    await new Promise((resolve) => setImmediate(resolve));
  }
  assert.equal(requests[1].method, "notifications/cancelled");
  assert.equal(requests[1].params.requestId, requests[0].id);
});

test("abort remains active while an SSE response body is streaming", async () => {
  const requests = [];
  let markHeaders;
  const headersReady = new Promise((resolve) => { markHeaders = resolve; });
  const client = new TemperaMcpClient({
    url: "https://api.tempera.dev/mcp",
    bearer: "tp_key_1",
    autoInitialize: false,
    fetch: async (_url, options) => {
      const request = JSON.parse(options.body);
      requests.push(request);
      if (request.method === "notifications/cancelled") return new Response(null, { status: 202 });
      const body = new ReadableStream({
        start(streamController) {
          const abort = () => streamController.error(options.signal.reason ?? new Error("aborted"));
          if (options.signal.aborted) abort();
          else options.signal.addEventListener("abort", abort, { once: true });
          streamController.enqueue(new TextEncoder().encode("event: message\n"));
          markHeaders();
        },
      });
      return new Response(body, { headers: { "content-type": "text/event-stream" } });
    },
  });
  const controller = new AbortController();
  const pending = client.listTools({ signal: controller.signal });
  await headersReady;
  controller.abort(new Error("stop stream"));
  await assert.rejects(pending, /stop stream/);
  for (let attempt = 0; attempt < 10 && requests.length < 2; attempt += 1) {
    await new Promise((resolve) => setImmediate(resolve));
  }
  assert.equal(requests[1].method, "notifications/cancelled");
});

test("failed initialized notification clears partial session state", async () => {
  const client = new TemperaMcpClient({
    url: "https://api.tempera.dev/mcp",
    bearer: "tp_key_1",
    autoInitialize: false,
    fetch: async (_url, options) => {
      const request = JSON.parse(options.body);
      if (request.method === "initialize") {
        return new Response(JSON.stringify({
          jsonrpc: "2.0",
          id: request.id,
          result: { protocolVersion: "2025-11-25", capabilities: {}, serverInfo: { name: "test", version: "1" } },
        }), { headers: { "content-type": "application/json", "mcp-session-id": "partial" } });
      }
      return rpcResponse({ error: "initialization_failed" }, { status: 500 });
    },
  });
  await assert.rejects(() => client.initialize(), TemperaApiError);
  assert.equal(client.sessionId, null);
  assert.equal(client.serverInfo, null);
  assert.equal(client.initialized, false);
});
