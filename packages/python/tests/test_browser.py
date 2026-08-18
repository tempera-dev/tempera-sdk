from tempera_sdk.browser import BrowserTask, BrowserWorkflow


class FakeTempo:
    def __init__(self):
        self.calls = []
        self.revision = 0

    def create_session(self, params=None, **extra):
        payload = dict(params or {})
        payload.update(extra)
        self.calls.append(("create", payload))
        return {"session_id": "s-1"}

    def observe_session(self, params=None, **extra):
        payload = dict(params or {})
        payload.update(extra)
        self.calls.append(("observe", payload))
        return {"revision": self.revision, "url": "https://example.test"}

    def act_batch(self, params=None, **extra):
        payload = dict(params or {})
        payload.update(extra)
        self.calls.append(("act", payload))
        self.revision += 1
        return {"settledObservation": {"revision": self.revision, "url": "https://example.test"}}

    def close_session(self, params=None, **extra):
        payload = dict(params or {})
        payload.update(extra)
        self.calls.append(("close", payload))
        return {"closed": True}


class FakeClient:
    def __init__(self):
        self.tempo = FakeTempo()


def test_browser_task_reuses_settled_observation():
    client = FakeClient()
    task = BrowserTask.create(client, url="https://example.test")

    result = task.run(
        lambda ctx: [{"kind": "scroll", "y": 100}] if ctx["step"] < 2 else "done",
        max_steps=5,
    )

    assert result.steps == 2
    assert result.observation["revision"] == 2
    assert len([call for call in client.tempo.calls if call[0] == "observe"]) == 1
    assert len([call for call in client.tempo.calls if call[0] == "act"]) == 2
    task.close()
    assert task.closed


def test_browser_workflow_shares_task_and_context():
    client = FakeClient()
    task = BrowserTask.attach(client, "existing")
    workflow = BrowserWorkflow(task)

    def observe(*, task, **_):
        return {"observation": task.observe()}

    def act(*, task, **_):
        return {"receipt": task.step({"kind": "scroll", "y": 1})}

    workflow.use("observe", observe).use("act", act)
    result = workflow.run({"request_id": "r1"})

    assert result["context"]["request_id"] == "r1"
    assert result["context"]["observation"]["revision"] == 0
    assert result["context"]["receipt"]["settledObservation"]["revision"] == 1
