/**
 * Retry-rule conformance for the TypeScript client, proven against a REAL
 * local HTTP server. Nothing here monkeypatches fetch or the transport: every
 * assertion is made from what the server actually received on the wire.
 */
import assert from "node:assert/strict";
import { createServer } from "node:http";
import test from "node:test";

import { createTemperaClient } from "../src/client.js";
import { TemperaApiError, TemperaSdkError } from "../src/errors.js";
import {
  INITIAL_BACKOFF_MS,
  MAX_ATTEMPTS,
  RETRYABLE_STATUSES,
  canonicalIdempotencyKey,
  retryDelayMs,
} from "../src/retry.js";

const IDEMPOTENCY_KEY = "a4-intake-key-0000000001";

/** Start a real HTTP server that records every request it receives. */
async function startServer(handler) {
  const received = [];
  const server = createServer((request, response) => {
    const chunks = [];
    request.on("data", (chunk) => chunks.push(chunk));
    request.on("end", () => {
      const body = Buffer.concat(chunks).toString("utf8");
      received.push({
        method: request.method,
        url: request.url,
        headers: request.headers,
        body,
      });
      handler(received.length, response, { body, url: request.url });
    });
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();
  return {
    received,
    url: `http://127.0.0.1:${port}`,
    async close() {
      await new Promise((resolve) => server.close(resolve));
    },
  };
}

function send(response, status, payload) {
  const body = JSON.stringify(payload);
  response.writeHead(status, { "content-type": "application/json" });
  response.end(body);
}

/** A client wired to the live server; sleeps are collected, never awaited. */
function liveClient(baseUrl, slept) {
  return createTemperaClient({
    auth: { bearerFor: () => "test_token_1" },
    baseUrls: { temperaBusiness: baseUrl, temperaDropshipping: baseUrl },
    sleep: async (ms) => {
      slept.push(ms);
    },
  });
}

const CASE_PARAMS = {
  case_id: "case-1",
  idempotency_key: IDEMPOTENCY_KEY,
  expected_revision: 1,
  decision: "ready_for_owner_review",
};

test("retry_reuses_original_idempotency_key", async () => {
  const server = await startServer((attempt, response) => {
    if (attempt < 3) return send(response, 503, { error: { status: "UNAVAILABLE", message: "cold" } });
    return send(response, 200, { ok: true });
  });
  const slept = [];
  try {
    const client = liveClient(server.url, slept);
    const result = await client.temperaBusiness.businessCasesReviewDraft(CASE_PARAMS);
    assert.deepEqual(result, { ok: true });
    assert.equal(server.received.length, 3, "three real requests reached the server");
    const bodies = server.received.map((request) => request.body);
    assert.equal(new Set(bodies).size, 1, "every attempt resent byte-identical bytes");
    for (const request of server.received) {
      assert.equal(JSON.parse(request.body).idempotencyKey, IDEMPOTENCY_KEY);
    }
    assert.deepEqual(slept, [INITIAL_BACKOFF_MS, INITIAL_BACKOFF_MS * 2]);
  } finally {
    await server.close();
  }
});

test("unsafe_operation_is_never_retried", async () => {
  const server = await startServer((attempt, response) =>
    send(response, 503, { error: { status: "UNAVAILABLE", message: "cold" } }),
  );
  const slept = [];
  try {
    const client = liveClient(server.url, slept);
    // prepareProposal has no idempotency key in its request body, so the
    // generated surface classifies it safeRetry "none".
    const error = await client.temperaDropshipping
      .prepareProposal({
        organization: "org",
        project: "proj",
        environment: "env",
        site: "site",
        order_id: "order-1",
        expected_revision: 1,
      })
      .catch((thrown) => thrown);
    assert.ok(error instanceof TemperaApiError);
    assert.equal(error.status, 503);
    assert.equal(server.received.length, 1, "an unsafe write is sent exactly once");
    assert.deepEqual(slept, []);
  } finally {
    await server.close();
  }
});

test("retry_gives_up_after_three_attempts", async () => {
  const server = await startServer((attempt, response) =>
    send(response, 500, { error: { status: "INTERNAL", message: "boom" } }),
  );
  const slept = [];
  try {
    const client = liveClient(server.url, slept);
    const error = await client.temperaBusiness
      .businessCasesReviewDraft(CASE_PARAMS)
      .catch((thrown) => thrown);
    assert.ok(error instanceof TemperaApiError);
    assert.equal(error.status, 500);
    assert.equal(server.received.length, MAX_ATTEMPTS);
    assert.equal(slept.length, MAX_ATTEMPTS - 1);
  } finally {
    await server.close();
  }
});

test("reason_is_parsed_from_details", async () => {
  const server = await startServer((attempt, response) =>
    send(response, 409, {
      error: {
        code: 409,
        status: "ABORTED",
        message: "revision moved",
        details: [
          { "@type": "type.googleapis.com/google.rpc.RequestInfo", requestId: "req-1" },
          {
            "@type": "type.googleapis.com/google.rpc.ErrorInfo",
            reason: "REVISION_CONFLICT",
            domain: "tempera-business",
          },
        ],
      },
    }),
  );
  const slept = [];
  try {
    const client = liveClient(server.url, slept);
    const error = await client.temperaBusiness
      .businessCasesReviewDraft(CASE_PARAMS)
      .catch((thrown) => thrown);
    assert.ok(error instanceof TemperaApiError);
    assert.equal(error.reason, "REVISION_CONFLICT");
    assert.equal(error.code, "ABORTED");
  } finally {
    await server.close();
  }
});

test("a 4xx is not retried", async () => {
  const server = await startServer((attempt, response) =>
    send(response, 422, { error: { status: "INVALID_ARGUMENT", message: "bad intake" } }),
  );
  const slept = [];
  try {
    const client = liveClient(server.url, slept);
    const error = await client.temperaBusiness
      .businessCasesReviewDraft(CASE_PARAMS)
      .catch((thrown) => thrown);
    assert.ok(error instanceof TemperaApiError);
    assert.equal(error.status, 422);
    assert.equal(server.received.length, 1, "a caller error is surfaced immediately");
    assert.deepEqual(slept, []);
    assert.ok(!RETRYABLE_STATUSES.includes(422));
  } finally {
    await server.close();
  }
});

test("a connection failure is retried for a safe operation", async () => {
  const server = await startServer((attempt, response) => send(response, 200, { ok: true }));
  const closedUrl = server.url;
  await server.close();
  const slept = [];
  const client = liveClient(closedUrl, slept);
  const error = await client.temperaBusiness
    .businessCasesReviewDraft(CASE_PARAMS)
    .catch((thrown) => thrown);
  assert.ok(!(error instanceof TemperaApiError));
  assert.equal(slept.length, MAX_ATTEMPTS - 1, "connection failures exhaust the attempt budget");
});

test("a non-canonical idempotency key is rejected before the first attempt", async () => {
  const server = await startServer((attempt, response) => send(response, 200, { ok: true }));
  try {
    const client = liveClient(server.url, []);
    for (const invalid of ["", "has space", "has\nnewline", "snowman-☃", "x".repeat(257)]) {
      const error = await client.temperaBusiness
        .businessCasesReviewDraft({ ...CASE_PARAMS, idempotency_key: invalid })
        .catch((thrown) => thrown);
      assert.ok(error instanceof TemperaSdkError, `${JSON.stringify(invalid)} rejected`);
      assert.ok(!(error instanceof TemperaApiError));
    }
    assert.equal(server.received.length, 0, "no malformed key ever reached the wire");
  } finally {
    await server.close();
  }
});

test("canonicalIdempotencyKey matches the tempera-mcp rule exactly", () => {
  assert.equal(canonicalIdempotencyKey("Request-1._~"), "Request-1._~");
  for (const invalid of ["", "has space", "has\nnewline", "snowman-☃"]) {
    assert.equal(canonicalIdempotencyKey(invalid), null);
  }
  assert.equal(canonicalIdempotencyKey("x".repeat(256)), "x".repeat(256));
  assert.equal(canonicalIdempotencyKey("x".repeat(257)), null);
});

test("retry backoff is exponential from 250 ms", () => {
  assert.equal(retryDelayMs(2), 250);
  assert.equal(retryDelayMs(3), 500);
});
