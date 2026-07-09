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
