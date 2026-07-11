export type TemperaScope =
  | "mcp:invoke"
  | "trace:read"
  | "trace:write"
  | "dataset:read"
  | "dataset:write"
  | "eval:run"
  | "pii:unmask"
  | "admin";

export type TemperaProductKey = "authHub" | "tempo" | "tempJs" | "tempOS" | "remi" | "cradle" | "arrha";

export type TemperaProduct = {
  name: "auth-hub" | "tempo" | "temp.js" | "tempOS" | "remi" | "cradle" | "Arrha";
  repository: string;
  env: string;
};

export declare const TEMPERA_PRODUCTS: Readonly<Record<TemperaProductKey, TemperaProduct>>;
export declare const TEMPERA_SCOPES: readonly TemperaScope[];
export type TemperaEnvironment = "local" | "preview" | "staging" | "production";
export type TemperaApiTargets = {
  publicSiteUrl: string;
  controlPlaneUrl: string;
  authIssuerUrl: string;
  authJwksUrl: string;
  paletteApiUrl: string;
  paletteMcpUrl: string;
  tempoApiUrl: string;
};
export declare const TEMPERA_API_TARGETS: Readonly<Record<TemperaEnvironment, TemperaApiTargets>>;

export declare class TemperaSdkError extends Error {
  status?: number;
  body?: unknown;
}

export type TemperaClientOptions = {
  endpoints?: Partial<Record<TemperaProductKey, string>>;
  accessToken?: string;
  fetch?: typeof fetch;
};

export type TemperaRequestOptions = {
  method?: string;
  body?: unknown;
  headers?: HeadersInit;
};

export type TemperaAudience = "palette" | "tempo" | "cradle" | "remi" | "human-data" | "tempera-mcp";
export declare const TEMPERA_AUDIENCES: readonly TemperaAudience[];
export declare const DEFAULT_AUDIENCE: "palette";

export declare function generatePkceVerifier(byteLength?: number): string;
export declare function pkceChallengeS256(verifier: string): Promise<string>;
export declare function createPkcePair(): Promise<{ verifier: string; challenge: string; method: "S256" }>;

export type TemperaAuthorizeUrlOptions = {
  issuerUrl: string;
  clientId: string;
  redirectUri: string;
  codeChallenge: string;
  audience?: TemperaAudience | (string & {});
  scope?: TemperaScope | (string & {}) | readonly (TemperaScope | (string & {}))[];
  state?: string;
};
export declare function buildAuthorizeUrl(options: TemperaAuthorizeUrlOptions): string;

export type TemperaTokenSet = {
  accessToken: string;
  refreshToken?: string;
  expiresIn?: number;
  scope?: string;
};

export type TemperaAuthOptions = {
  issuerUrl: string;
  clientId?: string;
  apiKey?: string;
  tokens?: Record<string, TemperaTokenSet>;
  fetch?: typeof fetch;
};

export declare class TemperaAuth {
  constructor(options: TemperaAuthOptions);
  issuerUrl: string;
  clientId?: string;
  apiKey?: string;
  tokens: Record<string, TemperaTokenSet>;
  fetch?: typeof fetch;
  get mcpUrl(): string;
  bearerFor(audience?: TemperaAudience | (string & {})): string;
  buildAuthorizeUrl(options: Omit<TemperaAuthorizeUrlOptions, "issuerUrl" | "clientId"> & { clientId?: string }): string;
  exchangeCode(options: {
    code: string;
    codeVerifier: string;
    redirectUri?: string;
    audience?: TemperaAudience | (string & {});
  }): Promise<TemperaTokenSet>;
  refresh(audience?: TemperaAudience | (string & {})): Promise<TemperaTokenSet>;
  revoke(
    audience?: TemperaAudience | (string & {}),
    options?: { tokenTypeHint?: "refresh_token" | "access_token" },
  ): Promise<void>;
}

export type TemperaProductAudienceKey = "palette" | "tempo" | "cradle" | "remi";
export declare const TEMPERA_PRODUCT_AUDIENCES: Readonly<
  Record<TemperaProductAudienceKey, { audience: TemperaAudience; env: string }>
>;

export type TemperaProductsOptions = {
  auth: TemperaAuth;
  baseUrls?: Partial<Record<TemperaProductAudienceKey, string>>;
  mcpUrl?: string;
  fetch?: typeof fetch;
};

export declare function createTemperaProducts(options: TemperaProductsOptions): {
  mcpUrl: string;
  request(productKey: TemperaProductAudienceKey, path: string, options?: TemperaRequestOptions): Promise<unknown>;
  palette(path: string, options?: TemperaRequestOptions): Promise<unknown>;
  tempo(path: string, options?: TemperaRequestOptions): Promise<unknown>;
  cradle(path: string, options?: TemperaRequestOptions): Promise<unknown>;
  remi(path: string, options?: TemperaRequestOptions): Promise<unknown>;
};

export declare function createTemperaClient(options?: TemperaClientOptions): {
  products: typeof TEMPERA_PRODUCTS;
  targets: typeof TEMPERA_API_TARGETS;
  request(productKey: TemperaProductKey, path: string, options?: TemperaRequestOptions): Promise<unknown>;
  authHub(path: string, options?: TemperaRequestOptions): Promise<unknown>;
  tempo(path: string, options?: TemperaRequestOptions): Promise<unknown>;
  tempJs(path: string, options?: TemperaRequestOptions): Promise<unknown>;
  tempOS(path: string, options?: TemperaRequestOptions): Promise<unknown>;
  remi(path: string, options?: TemperaRequestOptions): Promise<unknown>;
  cradle(path: string, options?: TemperaRequestOptions): Promise<unknown>;
  arrha(path: string, options?: TemperaRequestOptions): Promise<unknown>;
};
