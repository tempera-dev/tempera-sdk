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
    fetch: async (url, options) => {
      const request = JSON.parse(options.body);
      calls.push({ url, options, request });
      return handler(request);
    },
  });
  return { client, calls };
}

test("initialize, ping, and tools/list send well-formed JSON-RPC with the bearer", async () => {
  const { client, calls } = gatewayClient((request) => {
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
    assert.equal(call.request.jsonrpc, "2.0");
    assert.ok(Number.isInteger(call.request.id));
  }
  assert.equal(calls[0].request.method, "initialize");
  assert.equal(calls[0].request.params.protocolVersion, "2025-06-18");
  assert.equal(calls[1].request.method, "ping");
  assert.equal(calls[2].request.method, "tools/list");
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
