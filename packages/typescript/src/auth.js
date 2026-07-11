/**
 * Unified Tempera auth against the control-plane issuer: PKCE (S256) helpers,
 * an authorize-URL builder carrying the RFC 8707 `resource` audience selector,
 * code exchange / refresh / revoke with refresh-token rotation, and a
 * per-audience credential store with unified tp_ API-key fallback.
 *
 * Mirrored by tempera_sdk.TemperaAuth in Python and tempera_sdk::auth in Rust
 * (the Rust crate builds request bodies instead of sending them).
 */

import {
  DEFAULT_AUDIENCE,
  TEMPERA_AUDIENCES,
  TEMPERA_ISSUER_PATHS,
  TEMPERA_PRODUCTS,
} from "./surface.js";
import { TemperaSdkError, apiErrorFromResponse } from "./errors.js";

export { DEFAULT_AUDIENCE, TEMPERA_AUDIENCES };

function base64UrlEncode(bytes) {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}

function trimTrailingSlash(url) {
  return url.replace(/\/+$/, "");
}

/** Generate a PKCE code verifier: base64url of cryptographically random bytes. */
export function generatePkceVerifier(byteLength = 32) {
  const bytes = new Uint8Array(byteLength);
  globalThis.crypto.getRandomValues(bytes);
  return base64UrlEncode(bytes);
}

/** Compute the S256 code challenge: unpadded base64url of SHA-256(verifier). */
export async function pkceChallengeS256(verifier) {
  const digest = await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return base64UrlEncode(new Uint8Array(digest));
}

/** Create a {verifier, challenge, method: "S256"} PKCE pair. */
export async function createPkcePair() {
  const verifier = generatePkceVerifier();
  return { verifier, challenge: await pkceChallengeS256(verifier), method: "S256" };
}

/** Build the /oauth/authorize URL with PKCE and the resource audience selector. */
export function buildAuthorizeUrl({
  issuerUrl,
  clientId,
  redirectUri,
  codeChallenge,
  audience = DEFAULT_AUDIENCE,
  scope,
  state,
} = {}) {
  if (!issuerUrl) throw new TemperaSdkError("issuerUrl is required");
  if (!clientId) throw new TemperaSdkError("clientId is required");
  if (!redirectUri) throw new TemperaSdkError("redirectUri is required");
  if (!codeChallenge) throw new TemperaSdkError("codeChallenge is required; use createPkcePair()");
  const url = new URL(`${trimTrailingSlash(issuerUrl)}${TEMPERA_ISSUER_PATHS.authorize}`);
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

/** One unified credential (tp_ API key or per-audience OAuth tokens) against one issuer. */
export class TemperaAuth {
  constructor({ issuerUrl, clientId, apiKey, tokens = {}, fetch: fetchImpl = globalThis.fetch } = {}) {
    if (!issuerUrl) throw new TemperaSdkError("issuerUrl is required (e.g. https://api.tempera.dev)");
    this.issuerUrl = trimTrailingSlash(issuerUrl);
    this.clientId = clientId;
    this.apiKey = apiKey;
    this.tokens = { ...tokens };
    this.fetch = fetchImpl;
  }

  /** Unified MCP gateway URL (streamable-HTTP MCP, audience tempera-mcp). */
  get mcpUrl() {
    return `${this.issuerUrl}${TEMPERA_ISSUER_PATHS.mcp}`;
  }

  /** The bearer for an audience: its access token, falling back to the tp_ API key. */
  bearerFor(audience = DEFAULT_AUDIENCE) {
    const tokenSet = this.tokens[audience];
    if (tokenSet?.accessToken) return tokenSet.accessToken;
    if (this.apiKey) return this.apiKey;
    throw new TemperaSdkError(`no credential for audience ${audience}; provide an apiKey or tokens.${audience}`);
  }

  /** Build the authorize URL for this issuer and client. */
  buildAuthorizeUrl(options = {}) {
    return buildAuthorizeUrl({ issuerUrl: this.issuerUrl, clientId: this.clientId, ...options });
  }

  async #post(path, params) {
    if (!this.fetch) throw new TemperaSdkError("fetch is required");
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
    if (!response.ok) {
      throw apiErrorFromResponse({
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
        body: parsed,
        product: "controlPlane",
        operation: path,
      });
    }
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

  /** Exchange an authorization code (PKCE) for the audience's token set. */
  async exchangeCode({ code, codeVerifier, redirectUri, audience = DEFAULT_AUDIENCE } = {}) {
    if (!code) throw new TemperaSdkError("code is required");
    if (!codeVerifier) throw new TemperaSdkError("codeVerifier is required (PKCE is mandatory)");
    if (!redirectUri) throw new TemperaSdkError("redirectUri is required and must match the authorize request");
    const token = await this.#post(TEMPERA_ISSUER_PATHS.token, {
      grant_type: "authorization_code",
      code,
      code_verifier: codeVerifier,
      redirect_uri: redirectUri,
      resource: audience,
      ...(this.clientId ? { client_id: this.clientId } : {}),
    });
    return this.#store(audience, token);
  }

  /** Refresh the audience's tokens; rotation stores the newly issued refresh token. */
  async refresh(audience = DEFAULT_AUDIENCE) {
    const current = this.tokens[audience];
    if (!current?.refreshToken) throw new TemperaSdkError(`no refresh token for audience ${audience}`);
    const token = await this.#post(TEMPERA_ISSUER_PATHS.token, {
      grant_type: "refresh_token",
      refresh_token: current.refreshToken,
      resource: audience,
      ...(this.clientId ? { client_id: this.clientId } : {}),
    });
    return this.#store(audience, token);
  }

  /** Revoke the audience's token at the issuer and drop it from the store. */
  async revoke(audience = DEFAULT_AUDIENCE, { tokenTypeHint = "refresh_token" } = {}) {
    const current = this.tokens[audience];
    const token = tokenTypeHint === "access_token" ? current?.accessToken : current?.refreshToken ?? current?.accessToken;
    if (!token) throw new TemperaSdkError(`no token to revoke for audience ${audience}`);
    await this.#post(TEMPERA_ISSUER_PATHS.revoke, {
      token,
      token_type_hint: tokenTypeHint,
      ...(this.clientId ? { client_id: this.clientId } : {}),
    });
    delete this.tokens[audience];
  }
}

/** Product key -> {audience, env} for the audience-bearing products. */
export const TEMPERA_PRODUCT_AUDIENCES = Object.freeze(
  Object.fromEntries(
    Object.entries(TEMPERA_PRODUCTS)
      .filter(([, product]) => product.audience)
      .map(([key, product]) => [key, { audience: product.audience, env: product.envVar }]),
  ),
);
