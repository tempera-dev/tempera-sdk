# Browser tasks and workflows

The generated `tempo` product client remains the source of truth for Tempo's HTTP contract. The SDK adds a thin lifecycle/composition layer above it so applications can keep one browser session across deterministic workflows or bounded agent loops without reimplementing session plumbing.

## TypeScript

```ts
import { BrowserTask, BrowserWorkflow, createTemperaClient } from "@tempera/sdk";

const client = createTemperaClient({ auth, environment: "staging" });
const browser = await BrowserTask.create(client, { url: "https://example.com" });

const result = await browser.run(async ({ observation, step }) => {
  const decision = await model.decide({ observation, step });
  if (decision.done) return { done: true, value: decision.answer };
  return { actions: decision.actions };
}, { maxSteps: 40, close: true });
```

A deterministic workflow can share the same stateful browser task:

```ts
const browser = await BrowserTask.create(client, { url: "https://example.com" });
const workflow = new BrowserWorkflow(browser)
  .use("login", async ({ task }) => {
    await task.act(loginActions);
    return { loggedIn: true };
  })
  .use("collect", async ({ task, context }) => {
    const observation = await task.observe();
    return { ...context, observation };
  });

const { context } = await workflow.run({ jobId });
await browser.close();
```

## Python

```python
from tempera_sdk import BrowserTask, BrowserWorkflow, TemperaClient

client = TemperaClient(auth=auth, environment="staging")
browser = BrowserTask.create(client, url="https://example.com")

result = browser.run(
    lambda ctx: agent.decide(ctx["observation"]),
    max_steps=40,
    close=True,
)
```

`BrowserTask` preserves native Tempo observations and receipts. If an action receipt already contains an authoritative settled observation, the loop reuses it rather than immediately issuing a redundant observe call. Otherwise it explicitly re-observes.

## Rust

The Rust crate intentionally owns no HTTP runtime, so `BrowserTask` is a request builder rather than an executor. It emits the same Tempo `RequestSpec`s for callers to send with their HTTP stack:

```rust
let mut browser = BrowserTask::attach(&client, "session-1");
let observe = browser.observe_request(&[])?;
let act = browser.act_batch_request("[{\"kind\":\"scroll\",\"y\":100}]", &[])?;
let close = browser.close_request(&[])?;
```

## Contract boundary

The high-level API does not create a second browser protocol. It delegates to the generated Tempo operations and therefore inherits Tempo's state guards, approval semantics, durable BrowserTask recovery, typed human-handoff states, and executor receipts. Producer OpenAPI stays authoritative; when Tempo changes, `specs/tempo-openapi.json`, `surface.json`, generated language surfaces, and generated docs must be updated together through the SDK drift gates.
