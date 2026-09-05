import assert from "node:assert/strict";
import { test } from "node:test";
import { createTemperaClient, TemperaAuth } from "../src/index.js";

test("LLM operation preserves tool turns, nulls, omissions, and final JSON output", async () => {
  const toolMessage = { role: "assistant", content: null, tool_calls: [
    { id: "call_1", type: "function", function: { name: "inspect", arguments: "{}" } },
  ] };
  const messages = [{ role: "user", content: "inspect" }, toolMessage,
    { role: "tool", tool_call_id: "call_1", content: "{}" }];
  const base = { model: "gpt-4o-mini", max_tokens: 64, messages };
  const cases = [base, { ...base, tools: null, tool_choice: null }, {
    ...base, tools: [{ type: "function", function: { name: "inspect", parameters: { type: "object" } } }],
    tool_choice: { type: "function", function: { name: "inspect" } }, parallel_tool_calls: false,
  }, { ...base, tool_choice: "none", response_format: {
    type: "json_schema", json_schema: { name: "final", schema: { type: "object" } },
  } }];
  let expected;
  const result = { choices: [{ message: toolMessage, finish_reason: "tool_calls" }] };
  const client = createTemperaClient({
    auth: new TemperaAuth({ issuerUrl: "https://issuer.example.test", apiKey: "fixture-key" }),
    baseUrls: { temperaLlm: "http://127.0.0.1:8080" },
    fetch: async (url, options) => {
      assert.equal(new URL(url).pathname, "/v1/chat/completions");
      assert.equal(options.method, "POST");
      assert.equal(options.headers.authorization, "Bearer fixture-key");
      assert.deepEqual(JSON.parse(options.body), expected);
      return new Response(JSON.stringify(result), { headers: { "content-type": "application/json" } });
    },
  });
  for (expected of cases) {
    assert.deepEqual(await client.temperaLlm.createChatCompletion(expected), result);
  }
});
