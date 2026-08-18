import test from "node:test";
import assert from "node:assert/strict";
import { BrowserTask, BrowserWorkflow } from "../src/browser.js";

function fakeClient() {
  const calls = [];
  let revision = 0;
  return {
    calls,
    tempo: {
      async createSession(params) {
        calls.push(["create", params]);
        return { session_id: "s-1" };
      },
      async observeSession(params) {
        calls.push(["observe", params]);
        return { revision, url: "https://example.test" };
      },
      async actBatch(params) {
        calls.push(["act", params]);
        revision += 1;
        return { receipt: true, settledObservation: { revision, url: "https://example.test" } };
      },
      async closeSession(params) {
        calls.push(["close", params]);
        return { closed: true };
      },
    },
  };
}

test("BrowserTask owns session lifecycle and reuses settled observations", async () => {
  const client = fakeClient();
  const task = await BrowserTask.create(client, { url: "https://example.test" });
  const result = await task.run(
    ({ step }) => (step < 2 ? [{ kind: "scroll", y: 100 }] : "done"),
    { maxSteps: 5 },
  );

  assert.equal(result.steps, 2);
  assert.equal(result.observation.revision, 2);
  assert.equal(client.calls.filter(([kind]) => kind === "observe").length, 1);
  assert.equal(client.calls.filter(([kind]) => kind === "act").length, 2);
  await task.close();
  assert.equal(task.closed, true);
});

test("BrowserWorkflow composes deterministic steps around one task", async () => {
  const client = fakeClient();
  const task = BrowserTask.attach(client, "existing");
  const workflow = new BrowserWorkflow(task)
    .use("observe", async ({ task: browser }) => ({ observation: await browser.observe() }))
    .use("act", async ({ task: browser }) => ({ receipt: await browser.step({ kind: "scroll", y: 1 }) }));

  const result = await workflow.run({ requestId: "r1" });
  assert.equal(result.context.requestId, "r1");
  assert.equal(result.context.observation.revision, 0);
  assert.equal(result.context.receipt.receipt, true);
});
