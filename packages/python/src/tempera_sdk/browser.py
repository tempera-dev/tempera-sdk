"""High-level browser task and workflow primitives over the generated Tempo client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, MutableMapping

from .errors import TemperaSdkError


def _method(target: Any, name: str) -> Callable[..., Any]:
    value = getattr(target, name, None)
    if not callable(value):
        raise TemperaSdkError(f"tempo.{name} is required by BrowserTask")
    return value


def _session_id(value: Any) -> str:
    if isinstance(value, Mapping):
        candidate = value.get("sessionId") or value.get("session_id") or value.get("id") or value.get("name")
    else:
        candidate = getattr(value, "session_id", None) or getattr(value, "sessionId", None) or getattr(value, "id", None)
    if not isinstance(candidate, str) or not candidate:
        raise TemperaSdkError("tempo.create_session returned no session identifier")
    return candidate


@dataclass(slots=True)
class BrowserLoopResult:
    task: "BrowserTask"
    steps: int
    observation: Any
    receipt: Any = None
    value: Any = None


class BrowserTask:
    """Stateful browser session suitable for deterministic workflows or agent loops."""

    def __init__(self, client: Any, session_id: str, *, session: Any = None, owned: bool = False) -> None:
        if not session_id:
            raise TemperaSdkError("BrowserTask requires session_id")
        self.client = client
        self.tempo = client.tempo
        self.session_id = session_id
        self.session = session
        self.owned = owned
        self.state = "open"
        self.last_observation: Any = None
        self.last_receipt: Any = None

    @classmethod
    def create(cls, client: Any, **options: Any) -> "BrowserTask":
        session = _method(client.tempo, "create_session")(**options)
        return cls(client, _session_id(session), session=session, owned=True)

    @classmethod
    def attach(cls, client: Any, session_id: str, *, session: Any = None) -> "BrowserTask":
        return cls(client, session_id, session=session, owned=False)

    @property
    def closed(self) -> bool:
        return self.state == "closed"

    def _assert_open(self) -> None:
        if self.state != "open":
            raise TemperaSdkError(f"BrowserTask {self.session_id} is {self.state}")

    def observe(self, **params: Any) -> Any:
        self._assert_open()
        observation = _method(self.tempo, "observe_session")(session_id=self.session_id, **params)
        self.last_observation = observation
        return observation

    def act(self, actions: list[Any], **params: Any) -> Any:
        self._assert_open()
        if not isinstance(actions, list) or not actions:
            raise TemperaSdkError("BrowserTask.act requires a non-empty actions list")
        receipt = _method(self.tempo, "act_batch")(session_id=self.session_id, actions=actions, **params)
        self.last_receipt = receipt
        return receipt

    def step(self, action: Any, **params: Any) -> Any:
        return self.act([action], **params)

    def run(
        self,
        worker: Callable[[Mapping[str, Any]], Any],
        *,
        max_steps: int = 50,
        initial_observation: Any = None,
        close: bool = False,
    ) -> BrowserLoopResult:
        if not callable(worker):
            raise TemperaSdkError("BrowserTask.run requires a worker")
        if not isinstance(max_steps, int) or max_steps <= 0:
            raise TemperaSdkError("max_steps must be a positive integer")
        self._assert_open()
        observation = initial_observation if initial_observation is not None else self.observe()
        value = None
        steps = 0
        try:
            while steps < max_steps:
                decision = worker({"task": self, "observation": observation, "step": steps})
                if decision is None or decision is False or decision == "done":
                    break
                normalized = {"actions": decision} if isinstance(decision, list) else decision
                if not isinstance(normalized, Mapping):
                    raise TemperaSdkError("BrowserTask worker must return actions, a decision mapping, or a stop sentinel")
                if "value" in normalized:
                    value = normalized["value"]
                actions = normalized.get("actions")
                if normalized.get("done") and not actions:
                    break
                if not isinstance(actions, list) or not actions:
                    raise TemperaSdkError("BrowserTask worker decision must contain non-empty actions")
                receipt = self.act(actions, **dict(normalized.get("act_params") or {}))
                steps += 1
                if normalized.get("done"):
                    break
                if isinstance(receipt, Mapping):
                    observation = (
                        receipt.get("observation")
                        or receipt.get("settledObservation")
                        or receipt.get("settled_observation")
                    )
                else:
                    observation = None
                if observation is None:
                    observation = self.observe()
                self.last_observation = observation
            return BrowserLoopResult(self, steps, self.last_observation or observation, self.last_receipt, value)
        finally:
            if close and self.state == "open":
                self.close()

    def workflow(self) -> "BrowserWorkflow":
        return BrowserWorkflow(self)

    def close(self, **params: Any) -> Any:
        if self.state == "closed":
            return None
        if self.state != "open":
            raise TemperaSdkError(f"BrowserTask {self.session_id} is already closing")
        self.state = "closing"
        try:
            result = _method(self.tempo, "close_session")(session_id=self.session_id, **params)
            self.state = "closed"
            return result
        except BaseException:
            self.state = "open"
            raise

    def __enter__(self) -> "BrowserTask":
        self._assert_open()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self.state == "open" and self.owned:
            self.close()


class BrowserWorkflow:
    """Small deterministic workflow composer whose steps share one BrowserTask."""

    def __init__(self, task: BrowserTask | None = None) -> None:
        self.task = task
        self.steps: list[tuple[str, Callable[..., Any]]] = []

    def use(self, name: str | Callable[..., Any], handler: Callable[..., Any] | None = None) -> "BrowserWorkflow":
        if callable(name) and handler is None:
            handler = name
            name = getattr(handler, "__name__", "") or f"step_{len(self.steps)}"
        if not isinstance(name, str) or not callable(handler):
            raise TemperaSdkError("BrowserWorkflow.use requires a name and handler")
        self.steps.append((name, handler))
        return self

    def run(self, context: Mapping[str, Any] | None = None, *, task: BrowserTask | None = None) -> dict[str, Any]:
        active_task = task or self.task
        if active_task is None:
            raise TemperaSdkError("BrowserWorkflow.run requires a BrowserTask")
        state: MutableMapping[str, Any] = dict(context or {})
        for index, (name, handler) in enumerate(self.steps):
            result = handler(task=active_task, context=state, index=index, name=name)
            if isinstance(result, Mapping):
                state.update(result)
        return {"task": active_task, "context": dict(state)}


def browser_workflow(task: BrowserTask | None = None) -> BrowserWorkflow:
    return BrowserWorkflow(task)
