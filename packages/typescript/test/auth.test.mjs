import assert from "node:assert/strict";
import { test } from "node:test";
import {
  DEFAULT_AUDIENCE,
  TEMPERA_AUDIENCES,
  TemperaApiError,
  TemperaAuth,
  buildAuthorizeUrl,
  createPkcePair,
  generatePkceVerifier,
  pkceChallengeS256,
} from "../src/index.js";

test("pkce challenge is unpadded base64url of SHA-256(verifier)", async () => {
  // RFC 7636 appendix B reference vector.
  const challenge = await pkceChallengeS256("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk");
  assert.equal(challenge, "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM");
  assert.ok(!challenge.includes("="));

  const verifier = generatePkceVerifier();
  assert.match(verifier, /^[A-Za-z0-9_-]{43,128}$/);

  const pair = await createPkcePair();
  assert.equal(pair.method, "S256");
  assert.equal(pair.challenge, await pkceChallengeS256(pair.verifier));
});

test("authorize url carries the resource audience and S256 challenge", () => {
  const url = new URL(
    buildAuthorizeUrl({
      issuerUrl: "https://api.tempera.dev/",
      clientId: "client_1",
      redirectUri: "https://app.example.test/callback",
      codeChallenge: "challenge_1",
      audience: "tempo",
      scope: ["trace:read", "trace:write"],
      state: "state_1",
    }),
  );
  assert.equal(`${url.origin}${url.pathname}`, "https://api.tempera.dev/oauth/authorize");
  assert.equal(url.searchParams.get("response_type"), "code");
  assert.equal(url.searchParams.get("resource"), "tempo");
  assert.equal(url.searchParams.get("code_challenge"), "challenge_1");
  assert.equal(url.searchParams.get("code_challenge_method"), "S256");
  assert.equal(url.searchParams.get("scope"), "trace:read trace:write");
  assert.equal(url.searchParams.get("state"), "state_1");
  assert.ok(TEMPERA_AUDIENCES.includes(DEFAULT_AUDIENCE));
});

test("code exchange and refresh propagate resource and rotate the refresh token", async () => {
  const calls = [];
  let refreshCount = 0;
  const auth = new TemperaAuth({
    issuerUrl: "https://api.tempera.dev",
    clientId: "client_1",
    fetch: async (url, options) => {
      const body = new URLSearchParams(options.body);
      calls.push({ url, body });
      if (body.get("grant_type") === "authorization_code") {
        return new Response(JSON.stringify({ access_token: "at_1", refresh_token: "rt_1", token_type: "Bearer" }));
      }
      refreshCount += 1;
      return new Response(
        JSON.stringify({ access_token: `at_${refreshCount + 1}`, refresh_token: `rt_${refreshCount + 1}`, token_type: "Bearer" }),
      );
    },
  });

  await auth.exchangeCode({
    code: "code_1",
    codeVerifier: "verifier_1",
    redirectUri: "https://app.example.test/callback",
    audience: "tempo",
  });
  assert.equal(calls[0].url, "https://api.tempera.dev/oauth/token");
  assert.equal(calls[0].body.get("grant_type"), "authorization_code");
  assert.equal(calls[0].body.get("resource"), "tempo");
  assert.equal(calls[0].body.get("code_verifier"), "verifier_1");
  assert.equal(auth.bearerFor("tempo"), "at_1");

  await auth.refresh("tempo");
  assert.equal(calls[1].body.get("grant_type"), "refresh_token");
  assert.equal(calls[1].body.get("refresh_token"), "rt_1");
  assert.equal(calls[1].body.get("resource"), "tempo");

  // Rotation: the second refresh must present the newly issued refresh token.
  await auth.refresh("tempo");
  assert.equal(calls[2].body.get("refresh_token"), "rt_2");
  assert.equal(auth.bearerFor("tempo"), "at_3");
  assert.equal(auth.tokens.tempo.refreshToken, "rt_3");
});

test("revoke posts the token to /oauth/revoke and drops the token set", async () => {
  const calls = [];
  const auth = new TemperaAuth({
    issuerUrl: "https://api.tempera.dev",
    clientId: "client_1",
    tokens: { remi: { accessToken: "at_remi", refreshToken: "rt_remi" } },
    fetch: async (url, options) => {
      calls.push({ url, body: new URLSearchParams(options.body) });
      return new Response(null, { status: 200 });
    },
  });

  await auth.revoke("remi");
  assert.equal(calls[0].url, "https://api.tempera.dev/oauth/revoke");
  assert.equal(calls[0].body.get("token"), "rt_remi");
  assert.equal(calls[0].body.get("token_type_hint"), "refresh_token");
  assert.equal(auth.tokens.remi, undefined);
});

test("bearerFor matches the audience with API-key fallback and mcpUrl derives from the issuer", () => {
  const auth = new TemperaAuth({
    issuerUrl: "https://api.tempera.dev",
    apiKey: "tp_key_1",
    tokens: {
      tempo: { accessToken: "at_tempo" },
      remi: { accessToken: "at_remi" },
    },
  });
  assert.equal(auth.bearerFor("tempo"), "at_tempo");
  assert.equal(auth.bearerFor("remi"), "at_remi");
  // No cradle token: the unified API key is the fallback bearer.
  assert.equal(auth.bearerFor("cradle"), "tp_key_1");
  assert.equal(auth.mcpUrl, "https://api.tempera.dev/mcp");
  assert.throws(() => new TemperaAuth({ issuerUrl: "https://api.tempera.dev" }).bearerFor("palette"), /no credential/);
});

test("failed token requests raise TemperaApiError with the control-plane error code", async () => {
  const auth = new TemperaAuth({
    issuerUrl: "https://api.tempera.dev",
    clientId: "client_1",
    fetch: async () =>
      new Response(JSON.stringify({ error: "unauthenticated", message: "Authorization code is invalid." }), {
        status: 401,
        headers: { "content-type": "application/json" },
      }),
  });
  await assert.rejects(
    () =>
      auth.exchangeCode({
        code: "bad",
        codeVerifier: "verifier_1",
        redirectUri: "https://app.example.test/callback",
      }),
    (error) => {
      assert.ok(error instanceof TemperaApiError);
      assert.equal(error.status, 401);
      assert.equal(error.code, "unauthenticated");
      return true;
    },
  );
});
