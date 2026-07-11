export * from "./auth.js";

export const TEMPERA_PRODUCTS = Object.freeze({
  authHub: { name: "auth-hub", repository: "https://github.com/tempera-dev/auth-hub", env: "TEMPERA_CONTROL_PLANE_URL" },
  tempo: { name: "tempo", repository: "https://github.com/tempera-dev/tempo", env: "TEMPERA_TEMPO_URL" },
  tempJs: { name: "temp.js", repository: "https://github.com/tempera-dev/temp.js", env: "TEMPERA_TEMPJS_URL" },
  tempOS: { name: "tempOS", repository: "https://github.com/tempera-dev/tempOS", env: "TEMPERA_TEMPOS_URL" },
  remi: { name: "remi", repository: "https://github.com/tempera-dev/remi", env: "TEMPERA_REMI_URL" },
  cradle: { name: "cradle", repository: "https://github.com/tempera-dev/cradle", env: "TEMPERA_CRADLE_URL" },
  arrha: { name: "Arrha", repository: "https://github.com/tempera-dev/arrha", env: "TEMPERA_ARRHA_URL" },
});

export const TEMPERA_API_TARGETS = Object.freeze({
  local: {
    publicSiteUrl: "http://localhost:3000",
    controlPlaneUrl: "http://localhost:8787",
    authIssuerUrl: "http://localhost:8787",
    authJwksUrl: "http://localhost:8787/.well-known/jwks.json",
    paletteApiUrl: "http://localhost:8080",
    paletteMcpUrl: "http://localhost:8080/mcp",
    tempoApiUrl: "http://localhost:7878",
  },
  preview: {
    publicSiteUrl: "https://tempera-public-site-git-preview-tempera.vercel.app",
    controlPlaneUrl: "https://preview-api.tempera.dev",
    authIssuerUrl: "https://preview-api.tempera.dev",
    authJwksUrl: "https://preview-api.tempera.dev/.well-known/jwks.json",
    paletteApiUrl: "https://preview-mcp.tempera.dev",
    paletteMcpUrl: "https://preview-mcp.tempera.dev/mcp",
    tempoApiUrl: "https://preview-tempo.tempera.dev",
  },
  staging: {
    publicSiteUrl: "https://staging.tempera.dev",
    controlPlaneUrl: "https://staging-api.tempera.dev",
    authIssuerUrl: "https://staging-api.tempera.dev",
    authJwksUrl: "https://staging-api.tempera.dev/.well-known/jwks.json",
    paletteApiUrl: "https://staging-mcp.tempera.dev",
    paletteMcpUrl: "https://staging-mcp.tempera.dev/mcp",
    tempoApiUrl: "https://staging-tempo.tempera.dev",
  },
  production: {
    publicSiteUrl: "https://tempera.dev",
    controlPlaneUrl: "https://api.tempera.dev",
    authIssuerUrl: "https://api.tempera.dev",
    authJwksUrl: "https://api.tempera.dev/.well-known/jwks.json",
    paletteApiUrl: "https://mcp.tempera.dev",
    paletteMcpUrl: "https://mcp.tempera.dev/mcp",
    tempoApiUrl: "https://tempo.tempera.dev",
  },
});

export const TEMPERA_SCOPES = Object.freeze([
  "mcp:invoke",
  "trace:read",
  "trace:write",
  "dataset:read",
  "dataset:write",
  "eval:run",
  "pii:unmask",
  "admin",
]);

export class TemperaSdkError extends Error {
  constructor(message, { status, body } = {}) {
    super(message);
    this.name = "TemperaSdkError";
    this.status = status;
    this.body = body;
  }
}

export function createTemperaClient({ endpoints = {}, accessToken, fetch: fetchImpl = globalThis.fetch } = {}) {
  if (!fetchImpl) throw new Error("fetch is required");

  async function request(productKey, path, { method = "GET", body, headers = {} } = {}) {
    const product = TEMPERA_PRODUCTS[productKey];
    if (!product) throw new Error(`unknown Tempera product: ${productKey}`);
    const baseUrl = endpoints[productKey] ?? process?.env?.[product.env];
    if (!baseUrl) throw new Error(`missing endpoint for ${product.name}; set ${product.env}`);
    const response = await fetchImpl(new URL(path, baseUrl).toString(), {
      method,
      headers: {
        accept: "application/json",
        ...(body ? { "content-type": "application/json" } : {}),
        ...(accessToken ? { authorization: `Bearer ${accessToken}` } : {}),
        ...headers,
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    const text = await response.text();
    const parsed = text ? JSON.parse(text) : null;
    if (!response.ok) throw new TemperaSdkError(`Tempera ${product.name} request failed`, { status: response.status, body: parsed });
    return parsed;
  }

  return {
    products: TEMPERA_PRODUCTS,
    targets: TEMPERA_API_TARGETS,
    request,
    authHub: (path, options) => request("authHub", path, options),
    tempo: (path, options) => request("tempo", path, options),
    tempJs: (path, options) => request("tempJs", path, options),
    tempOS: (path, options) => request("tempOS", path, options),
    remi: (path, options) => request("remi", path, options),
    cradle: (path, options) => request("cradle", path, options),
    arrha: (path, options) => request("arrha", path, options),
  };
}
