/**
 * The unified Tempera client: one credential set, every product.
 *
 * Built entirely from the generated surface tables (src/surface.js), so the
 * TypeScript, Python, and Rust packages expose the same products, the same
 * operation names, the same descriptions, and the same error shape.
 *
 * - Typed operations: `client.palette.getTrace({ tenant_id, trace_id })` —
 *   every operation in surface.json becomes a method on its product client.
 *   Parameters use wire names (snake_case) in every language.
 * - Passthrough: `client.tempo.request("/custom", { method: "POST", body })`
 *   for endpoints the surface tables don't cover yet.
 * - Auth: audience products resolve their bearer through TemperaAuth (per-
 *   audience OAuth token with unified tp_ API-key fallback); control-plane
 *   operations use the account-session token, which login()/signup() store
 *   automatically.
 */

import {
  DEFAULT_AUDIENCE,
  TEMPERA_ENVIRONMENTS,
  TEMPERA_OPERATIONS,
  TEMPERA_PRODUCTS,
} from "./surface.js";
import { TemperaSdkError, apiErrorFromResponse } from "./errors.js";

function trimTrailingSlash(url) {
  return url.replace(/\/+$/, "");
}

function substitutePath(template, params, { product, operation }) {
  return template.replace(/\{([a-z_]+)\}/g, (_, key) => {
    const value = params[key];
    if (value === undefined || value === null || value === "") {
      throw new TemperaSdkError(`${product}.${operation}: missing required path parameter "${key}"`);
    }
    return encodeURIComponent(String(value));
  });
}

async function parseResponseBody(response) {
  const contentType = response.headers?.get?.("content-type") ?? "";
  if (contentType.includes("application/json") || contentType.includes("+json")) {
    const text = await response.text();
    return text ? JSON.parse(text) : null;
  }
  if (contentType.startsWith("text/")) return response.text();
  if (contentType === "") {
    const text = await response.text();
    if (!text) return null;
    try {
      return JSON.parse(text);
    } catch {
      return text;
    }
  }
  return response.arrayBuffer();
}

export function createTemperaClient({
  auth,
  accountToken,
  introspectionSecret,
  baseUrls = {},
  environment,
  fetch: fetchImpl,
} = {}) {
  const doFetch = fetchImpl ?? auth?.fetch ?? globalThis.fetch;
  if (!doFetch) throw new TemperaSdkError("fetch is required");
  const environmentTargets = environment ? TEMPERA_ENVIRONMENTS[environment] : null;
  if (environment && !environmentTargets) {
    throw new TemperaSdkError(`unknown Tempera environment: ${environment}`);
  }

  const state = { accountToken: accountToken ?? null };

  function baseUrlFor(productKey) {
    const product = TEMPERA_PRODUCTS[productKey];
    if (!product) throw new TemperaSdkError(`unknown Tempera product: ${productKey}`);
    const fromEnvironment = environmentTargets
      ? {
          controlPlane: environmentTargets.controlPlaneUrl,
          palette: environmentTargets.paletteApiUrl,
          tempo: environmentTargets.tempoApiUrl,
          temperaCode: environmentTargets.temperaCodeApiUrl,
          temperaLlm: environmentTargets.temperaLlmApiUrl,
          temperaWorkflows: environmentTargets.temperaWorkflowsApiUrl,
          temperaGym: environmentTargets.temperaGymUrl,
          dataEngine: environmentTargets.dataEngineApiUrl,
          cradle: environmentTargets.cradleApiUrl,
        }[productKey]
      : undefined;
    const baseUrl = baseUrls[productKey] ?? process?.env?.[product.envVar] ?? fromEnvironment;
    if (!baseUrl) {
      throw new TemperaSdkError(`missing base URL for ${productKey}; set ${product.envVar} or pass baseUrls.${productKey}`);
    }
    return trimTrailingSlash(baseUrl);
  }

  function bearerFor(productKey, authKind) {
    if (authKind === "none") return null;
    if (authKind === "introspectionSecret") {
      if (!introspectionSecret) {
        throw new TemperaSdkError(`${productKey}: introspectToken requires the introspectionSecret option`);
      }
      return introspectionSecret;
    }
    if (authKind === "account") {
      if (!state.accountToken) {
        throw new TemperaSdkError(
          `${productKey}: an account token is required; call controlPlane.login()/signup() first or pass accountToken`,
        );
      }
      return state.accountToken;
    }
    const audience = TEMPERA_PRODUCTS[productKey]?.audience ?? DEFAULT_AUDIENCE;
    if (!auth) {
      throw new TemperaSdkError(`${productKey}: pass a TemperaAuth (with an apiKey or ${audience} tokens) to call product endpoints`);
    }
    return auth.bearerFor(audience);
  }

  async function rawRequest(productKey, path, { method = "GET", body, query, headers = {}, bearer, operation } = {}) {
    const url = new URL(baseUrlFor(productKey) + path);
    for (const [key, value] of Object.entries(query ?? {})) {
      if (value !== undefined && value !== null) url.searchParams.set(key, String(value));
    }
    const response = await doFetch(url.toString(), {
      method,
      headers: {
        accept: "application/json",
        ...(body !== undefined ? { "content-type": "application/json" } : {}),
        ...(bearer ? { authorization: `Bearer ${bearer}` } : {}),
        ...headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    const parsed = await parseResponseBody(response);
    if (!response.ok) {
      throw apiErrorFromResponse({
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
        body: parsed,
        product: productKey,
        operation,
      });
    }
    return parsed;
  }

  function dispatch(productKey, op, params = {}, options = {}) {
    for (const key of op.forbiddenBody ?? []) {
      if (params[key] !== undefined) {
        throw new TemperaSdkError(`${productKey}.${op.id}: ${key} is derived from the authenticated principal`);
      }
    }
    const path = substitutePath(op.path, params, { product: productKey, operation: op.id });
    const consumed = new Set(op.pathParams);
    const query = {};
    for (const key of op.query) {
      if (params[key] !== undefined) {
        query[key] = params[key];
        consumed.add(key);
      }
    }
    let body;
    if (op.body.length > 0 || Object.keys(op.bodyDefaults).length > 0) {
      body = { ...op.bodyDefaults };
      for (const key of op.body) {
        if (params[key] !== undefined) {
          body[key] = params[key];
          consumed.add(key);
        }
      }
    }
    // Forward-compatibility: undeclared parameters flow to the query string on
    // GET/DELETE and into the JSON body otherwise, so a new server field is
    // usable before the surface tables catch up.
    for (const [key, value] of Object.entries(params)) {
      if (consumed.has(key) || value === undefined) continue;
      if (op.method === "GET" || op.method === "DELETE") query[key] = value;
      else (body ??= {})[key] = value;
    }
    const bearer = options.bearer ?? bearerFor(productKey, op.auth);
    return rawRequest(productKey, path, {
      method: op.method,
      body,
      query,
      headers: options.headers ?? {},
      bearer,
      operation: op.id,
    });
  }

  function buildProductClient(productKey) {
    const product = {
      key: productKey,
      ...TEMPERA_PRODUCTS[productKey],
      request: (path, { method = "GET", body, query, headers, bearer } = {}) =>
        rawRequest(productKey, path.startsWith("/") ? path : `/${path}`, {
          method,
          body,
          query,
          headers,
          bearer:
            bearer ??
            (TEMPERA_PRODUCTS[productKey].audience || productKey === "controlPlane"
              ? tryBearer(productKey)
              : null),
        }),
    };
    for (const op of TEMPERA_OPERATIONS[productKey] ?? []) {
      // async so configuration errors (missing credential/path param) reject
      // rather than throw synchronously — one failure mode for callers.
      product[op.id] = async (params, options) => dispatch(productKey, op, params, options);
    }
    return product;
  }

  function tryBearer(productKey) {
    try {
      return bearerFor(productKey, productKey === "controlPlane" ? "account" : "product");
    } catch {
      return null;
    }
  }

  const client = {
    auth: auth ?? null,
    get accountToken() {
      return state.accountToken;
    },
    set accountToken(token) {
      state.accountToken = token;
    },
  };
  for (const productKey of Object.keys(TEMPERA_PRODUCTS)) {
    client[productKey] = buildProductClient(productKey);
  }

  // login/signup return the account-session token pair and store the access
  // token so subsequent control-plane calls are authenticated automatically.
  for (const opId of ["login", "signup"]) {
    const plain = client.controlPlane[opId];
    client.controlPlane[opId] = async (params, options) => {
      const tokens = await plain(params, options);
      if (tokens?.access_token) state.accountToken = tokens.access_token;
      return tokens;
    };
  }

  return client;
}
