import { TemperaSdkError } from "./errors.js";

function requireFunction(target, name) {
  const fn = target?.[name];
  if (typeof fn !== "function") {
    throw new TemperaSdkError(`tempo.${name} is required by BrowserTask`);
  }
  return fn.bind(target);
}

function sessionIdFrom(value) {
  const id = value?.sessionId ?? value?.session_id ?? value?.id ?? value?.name;
  if (!id || typeof id !== "string") {
    throw new TemperaSdkError("tempo.createSession returned no session identifier");
  }
  return id;
}

function assertPositiveInteger(name, value) {
  if (!Number.isInteger(value) || value <= 0) {
    throw new TemperaSdkError(`${name} must be a positive integer`);
  }
}

function sessionParams(params, sessionId) {
  const payload = { ...(params ?? {}) };
  // BrowserTask owns session routing. Remove the language alias so the
  // generated client cannot observe both spellings of the same parameter.
  delete payload.session_id;
  payload.sessionId = sessionId;
  return payload;
}

/**
 * Stateful, lifecycle-owning browser session built on the generated Tempo client.
 * It deliberately does not hide Tempo receipts or observations: higher-level
 * agents can reason over the native runtime contract without SDK translation.
 */
export class BrowserTask {
  static async create(client, options = {}) {
    if (!client?.tempo) throw new TemperaSdkError("BrowserTask requires a TemperaClient with tempo");
    const createSession = requireFunction(client.tempo, "createSession");
    const session = await createSession(options);
    return new BrowserTask(client, sessionIdFrom(session), { session, owned: true });
  }

  static attach(client, sessionId, { session = null } = {}) {
    if (!sessionId || typeof sessionId !== "string") {
      throw new TemperaSdkError("BrowserTask.attach requires sessionId");
    }
    return new BrowserTask(client, sessionId, { session, owned: false });
  }

  constructor(client, sessionId, { session = null, owned = false } = {}) {
    this.client = client;
    this.tempo = client.tempo;
    this.sessionId = sessionId;
    this.session = session;
    this.owned = owned;
    this.state = "open";
    this.lastObservation = null;
    this.lastReceipt = null;
  }

  get closed() {
    return this.state === "closed";
  }

  #assertOpen() {
    if (this.state !== "open") {
      throw new TemperaSdkError(`BrowserTask ${this.sessionId} is ${this.state}`);
    }
  }

  async observe(params = {}, options) {
    this.#assertOpen();
    const observe = requireFunction(this.tempo, "observe");
    const observation = await observe(sessionParams(params, this.sessionId), options);
    this.lastObservation = observation;
    return observation;
  }

  async act(actions, params = {}, options) {
    this.#assertOpen();
    if (!Array.isArray(actions) || actions.length === 0) {
      throw new TemperaSdkError("BrowserTask.act requires a non-empty actions array");
    }
    const actBatch = requireFunction(this.tempo, "actBatch");
    const payload = sessionParams(params, this.sessionId);
    // `batch` is the canonical Tempo request field. BrowserTask owns it; do
    // not leak the pre-AIP `actions` compatibility spelling onto the wire.
    delete payload.actions;
    payload.batch = actions;
    const receipt = await actBatch(payload, options);
    this.lastReceipt = receipt;
    return receipt;
  }

  async step(action, params = {}, options) {
    return this.act([action], params, options);
  }

  /**
   * Run a bounded observe -> decide -> act loop.
   *
   * worker returns one of:
   * - null/false/"done" to stop;
   * - an action array;
   * - { actions, done?, value?, actParams? }.
   */
  async run(worker, { maxSteps = 50, signal, initialObservation, close = false } = {}) {
    if (typeof worker !== "function") throw new TemperaSdkError("BrowserTask.run requires a worker function");
    assertPositiveInteger("maxSteps", maxSteps);
    this.#assertOpen();

    let observation = initialObservation ?? (await this.observe());
    let value;
    let steps = 0;
    try {
      while (steps < maxSteps) {
        if (signal?.aborted) throw signal.reason ?? new DOMException("Aborted", "AbortError");
        const decision = await worker({ task: this, observation, step: steps });
        if (decision === null || decision === false || decision === "done") break;

        const normalized = Array.isArray(decision) ? { actions: decision } : decision;
        if (!normalized || typeof normalized !== "object") {
          throw new TemperaSdkError("BrowserTask worker must return actions, a decision object, or a stop sentinel");
        }
        if (normalized.value !== undefined) value = normalized.value;
        if (normalized.done && !normalized.actions) break;
        if (!Array.isArray(normalized.actions) || normalized.actions.length === 0) {
          throw new TemperaSdkError("BrowserTask worker decision must contain non-empty actions");
        }

        const receipt = await this.act(normalized.actions, normalized.actParams ?? {});
        steps += 1;
        if (normalized.done) break;

        // Do not invent a translated state. Prefer a native settled observation
        // if Tempo returns one, otherwise explicitly re-observe.
        observation =
          receipt?.observation ?? receipt?.settledObservation ?? receipt?.settled_observation ?? (await this.observe());
        this.lastObservation = observation;
      }
      return { task: this, steps, observation: this.lastObservation ?? observation, receipt: this.lastReceipt, value };
    } finally {
      if (close && this.state === "open") await this.close();
    }
  }

  workflow() {
    return new BrowserWorkflow(this);
  }

  async close(params = {}, options) {
    if (this.state === "closed") return null;
    if (this.state !== "open") throw new TemperaSdkError(`BrowserTask ${this.sessionId} is already closing`);
    this.state = "closing";
    try {
      const closeSession = requireFunction(this.tempo, "closeSession");
      const result = await closeSession(sessionParams(params, this.sessionId), options);
      this.state = "closed";
      return result;
    } catch (error) {
      this.state = "open";
      throw error;
    }
  }
}

/** Lightweight deterministic composition around a BrowserTask. */
export class BrowserWorkflow {
  constructor(task = null) {
    this.task = task;
    this.steps = [];
  }

  use(name, handler) {
    if (typeof name === "function") {
      handler = name;
      name = handler.name || `step_${this.steps.length}`;
    }
    if (typeof handler !== "function") throw new TemperaSdkError("BrowserWorkflow.use requires a handler");
    this.steps.push({ name, handler });
    return this;
  }

  async run(context = {}, { task = this.task, signal } = {}) {
    if (!task) throw new TemperaSdkError("BrowserWorkflow.run requires a BrowserTask");
    const state = { ...context };
    for (let index = 0; index < this.steps.length; index += 1) {
      if (signal?.aborted) throw signal.reason ?? new DOMException("Aborted", "AbortError");
      const step = this.steps[index];
      const result = await step.handler({ task, context: state, index, name: step.name });
      if (result && typeof result === "object" && !Array.isArray(result)) Object.assign(state, result);
    }
    return { task, context: state };
  }
}

export function browserWorkflow(task) {
  return new BrowserWorkflow(task);
}
