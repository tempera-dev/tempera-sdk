import { TemperaSdkError } from "./index.js";

export const TEMPERA_AUDIENCES = Object.freeze([
  "palette",
  "tempo",
  "cradle",
  "remi",
  "human-data",
  "tempera-mcp",
]);

export const DEFAULT_AUDIENCE = "palette";

function base64UrlEncode(bytes) {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}

function trimTrailingSlash(url) {
  return url.replace(/\/+$/, "");
}

export function generatePkceVerifier(byteLength = 32) {
  const bytes = new Uint8Array(byteLength);
  globalThis.crypto.getRandomValues(bytes);
  return base64UrlEncode(bytes);
}

export async function pkceChallengeS256(verifier) {
  const digest = await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return base64UrlEncode(new Uint8Array(digest));
}

export async function createPkcePair() {
  const verifier = generatePkceVerifier();
  return { verifier, challenge: await pkceChallengeS256(verifier), method: "S256" };
}

export function buildAuthorizeUrl({
  issuerUrl,
  clientId,
  redirectUri,
  codeChallenge,
  audience = DEFAULT_AUDIENCE,
  scope,
  state,
} = {}) {
  if (!issuerUrl) throw new Error("issuerUrl is required");
  if (!clientId) throw new Error("clientId is required");
  if (!redirectUri) throw new Error("redirectUri is required");
  if (!codeChallenge) throw new Error("codeChallenge is required; use createPkcePair()");
  const url = new URL(`${trimTrailingSlash(issuerUrl)}/oauth/authorize`);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("client_id", clientId);
  url.searchParams.set("redirect_uri", redirectUri);
  url.searchParams.set("code_challenge", codeChallenge);
  url.searchParams.set("code_challenge_method", "S256");
  url.searchParams.set("resource", audience);
  if (scope) url.searchParams.set("scope", Array.isArray(scope) ? scope.join(" ") : scope);
  if (state) url.searchParams.set("state", state);
  return url.toString();
}

export class TemperaAuth {
  constructor({ issuerUrl, clientId, apiKey, tokens = {}, fetch: fetchImpl = globalThis.fetch } = {}) {
    if (!issuerUrl) throw new Error("issuerUrl is required (e.g. https://api.tempera.dev)");
    this.issuerUrl = trimTrailingSlash(issuerUrl);
    this.clientId = clientId;
    this.apiKey = apiKey;
    this.tokens = { ...tokens };
    this.fetch = fetchImpl;
  }

  get mcpUrl() {
    return `${this.issuerUrl}/mcp`;
  }

  bearerFor(audience = DEFAULT_AUDIENCE) {
    const tokenSet = this.tokens[audience];
    if (tokenSet?.accessToken) return tokenSet.accessToken;
    if (this.apiKey) return this.apiKey;
    throw new Error(`no credential for audience ${audience}; provide an apiKey or tokens.${audience}`);
  }

  buildAuthorizeUrl(options = {}) {
    return buildAuthorizeUrl({ issuerUrl: this.issuerUrl, clientId: this.clientId, ...options });
  }

  async #post(path, params) {
    if (!this.fetch) throw new Error("fetch is required");
    const response = await this.fetch(`${this.issuerUrl}${path}`, {
      method: "POST",
      headers: {
        accept: "application/json",
        "content-type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams(params).toString(),
    });
    const text = await response.text();
    const parsed = text ? JSON.parse(text) : null;
    if (!response.ok) throw new TemperaSdkError(`Tempera auth request failed: POST ${path}`, { status: response.status, body: parsed });
    return parsed;
  }

  #store(audience, token) {
    const previous = this.tokens[audience];
    this.tokens[audience] = {
      accessToken: token.access_token,
      // Refresh-token rotation: the new refresh token replaces the old one.
      refreshToken: token.refresh_token ?? previous?.refreshToken,
      expiresIn: token.expires_in,
      scope: token.scope,
    };
    return this.tokens[audience];
  }

  async exchangeCode({ code, codeVerifier, redirectUri, audience = DEFAULT_AUDIENCE } = {}) {
    if (!code) throw new Error("code is required");
    if (!codeVerifier) throw new Error("codeVerifier is required (PKCE is mandatory)");
    if (!redirectUri) throw new Error("redirectUri is required and must match the authorize request");
    const token = await this.#post("/oauth/token", {
      grant_type: "authorization_code",
      code,
      code_verifier: codeVerifier,
      redirect_uri: redirectUri,
      resource: audience,
      ...(this.clientId ? { client_id: this.clientId } : {}),
    });
    return this.#store(audience, token);
  }

  async refresh(audience = DEFAULT_AUDIENCE) {
    const current = this.tokens[audience];
    if (!current?.refreshToken) throw new Error(`no refresh token for audience ${audience}`);
    const token = await this.#post("/oauth/token", {
      grant_type: "refresh_token",
      refresh_token: current.refreshToken,
      resource: audience,
      ...(this.clientId ? { client_id: this.clientId } : {}),
    });
    return this.#store(audience, token);
  }

  async revoke(audience = DEFAULT_AUDIENCE, { tokenTypeHint = "refresh_token" } = {}) {
    const current = this.tokens[audience];
    const token = tokenTypeHint === "access_token" ? current?.accessToken : current?.refreshToken ?? current?.accessToken;
    if (!token) throw new Error(`no token to revoke for audience ${audience}`);
    await this.#post("/oauth/revoke", {
      token,
      token_type_hint: tokenTypeHint,
      ...(this.clientId ? { client_id: this.clientId } : {}),
    });
    delete this.tokens[audience];
  }
}

export const TEMPERA_PRODUCT_AUDIENCES = Object.freeze({
  palette: { audience: "palette", env: "TEMPERA_PALETTE_URL" },
  tempo: { audience: "tempo", env: "TEMPERA_TEMPO_URL" },
  cradle: { audience: "cradle", env: "TEMPERA_CRADLE_URL" },
  remi: { audience: "remi", env: "TEMPERA_REMI_URL" },
});

export function createTemperaProducts({ auth, baseUrls = {}, mcpUrl, fetch: fetchImpl } = {}) {
  if (!auth) throw new Error("auth is required; pass a TemperaAuth instance");
  const doFetch = fetchImpl ?? auth.fetch ?? globalThis.fetch;
  if (!doFetch) throw new Error("fetch is required");

  async function request(productKey, path, { method = "GET", body, headers = {} } = {}) {
    const product = TEMPERA_PRODUCT_AUDIENCES[productKey];
    if (!product) throw new Error(`unknown Tempera product: ${productKey}`);
    const baseUrl = baseUrls[productKey] ?? process?.env?.[product.env];
    if (!baseUrl) throw new Error(`missing base URL for ${productKey}; set ${product.env}`);
    const response = await doFetch(new URL(path, baseUrl).toString(), {
      method,
      headers: {
        accept: "application/json",
        ...(body ? { "content-type": "application/json" } : {}),
        authorization: `Bearer ${auth.bearerFor(product.audience)}`,
        ...headers,
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    const text = await response.text();
    const parsed = text ? JSON.parse(text) : null;
    if (!response.ok) throw new TemperaSdkError(`Tempera ${productKey} request failed`, { status: response.status, body: parsed });
    return parsed;
  }

  return {
    mcpUrl: mcpUrl ?? auth.mcpUrl,
    request,
    palette: (path, options) => request("palette", path, options),
    tempo: (path, options) => request("tempo", path, options),
    cradle: (path, options) => request("cradle", path, options),
    remi: (path, options) => request("remi", path, options),
  };
}
