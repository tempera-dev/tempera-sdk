/**
 * The unified Tempera client: one credential set, every product.
 *
 * Built entirely from the generated surface tables (src/surface.js), so the
 * TypeScript, Python, and Rust packages expose the same products, the same
 * operation names, the same descriptions, and the same error shape.
 *
 * - Typed operations: `client.palette.getTrace({ tenant_id, trace_id })` —
 *   every operation in surface.json becomes a method on its product client.
 *   Parameters accept canonical wire names and snake_case aliases; requests
 *   always emit the producer's canonical wire names.
 * - Passthrough: `client.tempo.request("/custom", { method: "POST", body })`
 *   for endpoints the surface tables don't cover yet.
 * - Auth: audience products resolve their bearer through TemperaAuth (per-
 *   audience OAuth token with unified tp_ API-key fallback); control-plane
 *   operations use the account-session token returned by
 *   createHostedSession().
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

function snakeCase(value) {
  return value.replace(/([a-z0-9])([A-Z])/g, "$1_$2").toLowerCase();
}

function normalizeDeclaredParams(productKey, op, params) {
  const normalized = { ...params };
  const consumedAliases = new Set();
  const declared = new Set([
    ...(op.pathParams ?? []),
    ...(op.query ?? []),
    ...(op.body ?? []),
    ...(op.forbiddenBody ?? []),
  ]);
  for (const wireName of declared) {
    const alias = snakeCase(wireName);
    if (alias === wireName) continue;
    const hasWireName = Object.hasOwn(params, wireName);
    const hasAlias = Object.hasOwn(params, alias);
    if (hasWireName && hasAlias) {
      throw new TemperaSdkError(
        `${productKey}.${op.id}: pass either "${wireName}" or its snake_case alias "${alias}", not both`,
      );
    }
    if (hasAlias) {
      normalized[wireName] = params[alias];
      consumedAliases.add(alias);
    }
  }
  return { normalized, consumedAliases };
}

function expandPathParam(value, resourcePattern, { product, operation, key }) {
  if (!resourcePattern) return encodeURIComponent(String(value));
  const expected = resourcePattern.split("/");
  const observed = String(value).split("/");
  if (
    observed.length !== expected.length ||
    expected.some((segment, index) => segment !== "*" && segment !== observed[index]) ||
    observed.some((segment, index) => expected[index] === "*" && (!segment || segment === "." || segment === ".."))
  ) {
    throw new TemperaSdkError(
      `${product}.${operation}: path parameter "${key}" must match AIP resource pattern "${resourcePattern}"`,
    );
  }
  return observed
    .map((segment, index) => (expected[index] === "*" ? encodeURIComponent(segment) : segment))
    .join("/");
}

function substitutePath(template, params, { product, operation, pathParamTemplates = {} }) {
  return template.replace(/\{([A-Za-z_][A-Za-z0-9_]*)\}/g, (_, key) => {
    const value = params[key];
    if (value === undefined || value === null || value === "") {
      throw new TemperaSdkError(`${product}.${operation}: missing required path parameter "${key}"`);
    }
    return expandPathParam(value, pathParamTemplates[key], { product, operation, key });
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
          temperaLlm: environmentTargets.temperaLlmApiUrl,
          temperaWorkflows: environmentTargets.temperaWorkflowsApiUrl,
          temperaGym: environmentTargets.temperaGymUrl,
          temperaBio: environmentTargets.temperaBioApiUrl,
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

  function bearerFor(productKey, authKind, authAudience) {
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
          `${productKey}: an account token is required; call controlPlane.createHostedSession() first or pass accountToken`,
        );
      }
      return state.accountToken;
    }
    if (authKind === "oauthResource") {
      if (!auth) {
        throw new TemperaSdkError(
          `${productKey}: pass a TemperaAuth (with an apiKey or ${authAudience} tokens) to call this resource endpoint`,
        );
      }
      return auth.bearerFor(authAudience);
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
    const { normalized, consumedAliases } = normalizeDeclaredParams(productKey, op, params);
    for (const key of op.forbiddenBody ?? []) {
      if (normalized[key] !== undefined) {
        throw new TemperaSdkError(`${productKey}.${op.id}: ${key} is derived from the authenticated principal`);
      }
    }
    const path = substitutePath(op.path, normalized, {
      product: productKey,
      operation: op.id,
      pathParamTemplates: op.pathParamTemplates,
    });
    const consumed = new Set([...(op.pathParams ?? []), ...consumedAliases]);
    const query = {};
    for (const key of op.query) {
      if (normalized[key] !== undefined) {
        query[key] = normalized[key];
        consumed.add(key);
      }
    }
    let body;
    if (op.body.length > 0 || Object.keys(op.bodyDefaults).length > 0) {
      body = { ...op.bodyDefaults };
      for (const key of op.body) {
        if (normalized[key] !== undefined) {
          body[key] = normalized[key];
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
    const bearer =
      options.bearer ?? bearerFor(productKey, op.auth, op.authAudience);
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

  // createHostedSession returns the account-session token pair and stores the
  // token so subsequent control-plane calls are authenticated automatically.
  const createHostedSession = client.controlPlane.createHostedSession;
  client.controlPlane.createHostedSession = async (params, options) => {
    const tokens = await createHostedSession(params, options);
    if (tokens?.access_token) state.accountToken = tokens.access_token;
    return tokens;
  };

  return client;
}
