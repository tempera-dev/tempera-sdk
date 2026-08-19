import type { TemperaClient } from "./index.js";

export type BrowserLoopDecision<T = unknown> =
  | null
  | false
  | "done"
  | unknown[]
  | {
      actions?: unknown[];
      done?: boolean;
      value?: T;
      actParams?: Record<string, unknown>;
    };

export type BrowserLoopContext = {
  task: BrowserTask;
  observation: unknown;
  step: number;
};

export declare class BrowserTask {
  static create(client: TemperaClient, options?: Record<string, unknown>): Promise<BrowserTask>;
  static attach(client: TemperaClient, sessionId: string, options?: { session?: unknown }): BrowserTask;
  constructor(client: TemperaClient, sessionId: string, options?: { session?: unknown; owned?: boolean });
  client: TemperaClient;
  tempo: TemperaClient["tempo"];
  sessionId: string;
  session: unknown;
  owned: boolean;
  state: "open" | "closing" | "closed";
  lastObservation: unknown;
  lastReceipt: unknown;
  readonly closed: boolean;
  observe(params?: Record<string, unknown>, options?: unknown): Promise<unknown>;
  act(actions: unknown[], params?: Record<string, unknown>, options?: unknown): Promise<unknown>;
  step(action: unknown, params?: Record<string, unknown>, options?: unknown): Promise<unknown>;
  run<T = unknown>(
    worker: (context: BrowserLoopContext) => BrowserLoopDecision<T> | Promise<BrowserLoopDecision<T>>,
    options?: {
      maxSteps?: number;
      signal?: AbortSignal;
      initialObservation?: unknown;
      close?: boolean;
    },
  ): Promise<{ task: BrowserTask; steps: number; observation: unknown; receipt: unknown; value?: T }>;
  workflow(): BrowserWorkflow;
  close(params?: Record<string, unknown>, options?: unknown): Promise<unknown>;
}

export declare class BrowserWorkflow<T extends Record<string, unknown> = Record<string, unknown>> {
  constructor(task?: BrowserTask | null);
  task: BrowserTask | null;
  steps: Array<{ name: string; handler: Function }>;
  use(
    name: string,
    handler: (input: { task: BrowserTask; context: T; index: number; name: string }) =>
      | void
      | Partial<T>
      | Promise<void | Partial<T>>,
  ): this;
  use(
    handler: (input: { task: BrowserTask; context: T; index: number; name: string }) =>
      | void
      | Partial<T>
      | Promise<void | Partial<T>>,
  ): this;
  run(
    context?: T,
    options?: { task?: BrowserTask; signal?: AbortSignal },
  ): Promise<{ task: BrowserTask; context: T }>;
}

export declare function browserWorkflow<T extends Record<string, unknown> = Record<string, unknown>>(
  task?: BrowserTask,
): BrowserWorkflow<T>;
