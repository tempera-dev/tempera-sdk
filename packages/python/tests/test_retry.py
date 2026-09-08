"""Retry-rule conformance for the Python client, proven against a REAL local
HTTP server.

Nothing here monkeypatches the transport: a ``http.server`` instance is bound to
an ephemeral port, the client's own default transport sends real requests to it,
and every assertion is made from what the server actually received on the wire.
"""

from __future__ import annotations

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

from tempera_sdk.client import TemperaClient
from tempera_sdk.errors import TemperaApiError, TemperaSdkError
from tempera_sdk.retry import (
    INITIAL_BACKOFF_SECONDS,
    MAX_ATTEMPTS,
    RETRYABLE_STATUSES,
    canonical_idempotency_key,
    retry_delay_seconds,
)

IDEMPOTENCY_KEY = "a4-intake-key-0000000001"
CASE_PARAMS = {
    "case_id": "case-1",
    "idempotency_key": IDEMPOTENCY_KEY,
    "expected_revision": 1,
    "decision": "ready_for_owner_review",
}


class _StubAuth:
    """Minimal bearer source; the transport under test is the real one."""

    transport = None

    def bearer_for(self, audience: str) -> str:
        return "test_token_1"


class LiveServer:
    """A real HTTP server that records every request it receives."""

    def __init__(self, respond: Callable[[int], tuple[int, dict[str, Any]]]):
        self.received: list[dict[str, Any]] = []
        received = self.received

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def _handle(self) -> None:
                length = int(self.headers.get("content-length") or 0)
                raw = self.rfile.read(length) if length else b""
                received.append(
                    {
                        "method": self.command,
                        "path": self.path,
                        "headers": dict(self.headers),
                        "body": raw,
                    }
                )
                status, payload = respond(len(received))
                encoded = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            do_GET = _handle
            do_POST = _handle
            do_PATCH = _handle

            def log_message(self, *args: Any) -> None:
                return

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)

    def __enter__(self) -> "LiveServer":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()


def live_client(url: str, slept: list[float]) -> TemperaClient:
    return TemperaClient(
        auth=_StubAuth(),
        base_urls={"tempera_business": url, "tempera_dropshipping": url},
        sleep=slept.append,
    )


def unavailable(_attempt: int) -> tuple[int, dict[str, Any]]:
    return 503, {"error": {"status": "UNAVAILABLE", "message": "cold"}}


class RetryRulesTest(unittest.TestCase):
    def test_retry_reuses_original_idempotency_key(self):
        def respond(attempt: int) -> tuple[int, dict[str, Any]]:
            if attempt < 3:
                return unavailable(attempt)
            return 200, {"ok": True}

        slept: list[float] = []
        with LiveServer(respond) as server:
            client = live_client(server.url, slept)
            result = client.tempera_business.business_cases_review_draft(CASE_PARAMS)
            self.assertEqual(result, {"ok": True})
            self.assertEqual(len(server.received), 3)
            bodies = {request["body"] for request in server.received}
            self.assertEqual(len(bodies), 1, "every attempt resent byte-identical bytes")
            for request in server.received:
                sent = json.loads(request["body"])
                self.assertEqual(sent["idempotencyKey"], IDEMPOTENCY_KEY)
            self.assertEqual(
                slept, [INITIAL_BACKOFF_SECONDS, INITIAL_BACKOFF_SECONDS * 2]
            )

    def test_unsafe_operation_is_never_retried(self):
        slept: list[float] = []
        with LiveServer(unavailable) as server:
            client = live_client(server.url, slept)
            # prepare_proposal carries no idempotency key, so the generated
            # surface classifies it safe_retry "none".
            with self.assertRaises(TemperaApiError) as ctx:
                client.tempera_dropshipping.prepare_proposal(
                    {
                        "organization": "org",
                        "project": "proj",
                        "environment": "env",
                        "site": "site",
                        "order_id": "order-1",
                        "expected_revision": 1,
                    }
                )
            self.assertEqual(ctx.exception.status, 503)
            self.assertEqual(len(server.received), 1)
            self.assertEqual(slept, [])

    def test_retry_gives_up_after_three_attempts(self):
        slept: list[float] = []
        with LiveServer(
            lambda attempt: (500, {"error": {"status": "INTERNAL", "message": "boom"}})
        ) as server:
            client = live_client(server.url, slept)
            with self.assertRaises(TemperaApiError) as ctx:
                client.tempera_business.business_cases_review_draft(CASE_PARAMS)
            self.assertEqual(ctx.exception.status, 500)
            self.assertEqual(len(server.received), MAX_ATTEMPTS)
            self.assertEqual(len(slept), MAX_ATTEMPTS - 1)

    def test_reason_is_parsed_from_details(self):
        payload = {
            "error": {
                "code": 409,
                "status": "ABORTED",
                "message": "revision moved",
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.RequestInfo",
                        "requestId": "req-1",
                    },
                    {
                        "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                        "reason": "REVISION_CONFLICT",
                        "domain": "tempera-business",
                    },
                ],
            }
        }
        slept: list[float] = []
        with LiveServer(lambda attempt: (409, payload)) as server:
            client = live_client(server.url, slept)
            with self.assertRaises(TemperaApiError) as ctx:
                client.tempera_business.business_cases_review_draft(CASE_PARAMS)
            self.assertEqual(ctx.exception.reason, "REVISION_CONFLICT")
            self.assertEqual(ctx.exception.code, "ABORTED")

    def test_a_4xx_is_not_retried(self):
        slept: list[float] = []
        payload = {"error": {"status": "INVALID_ARGUMENT", "message": "bad intake"}}
        with LiveServer(lambda attempt: (422, payload)) as server:
            client = live_client(server.url, slept)
            with self.assertRaises(TemperaApiError) as ctx:
                client.tempera_business.business_cases_review_draft(CASE_PARAMS)
            self.assertEqual(ctx.exception.status, 422)
            self.assertEqual(len(server.received), 1)
            self.assertEqual(slept, [])
        self.assertNotIn(422, RETRYABLE_STATUSES)

    def test_connection_failure_is_retried_for_a_safe_operation(self):
        server = LiveServer(lambda attempt: (200, {"ok": True}))
        closed_url = server.url
        server.close()
        slept: list[float] = []
        client = live_client(closed_url, slept)
        with self.assertRaises(OSError):
            client.tempera_business.business_cases_review_draft(CASE_PARAMS)
        self.assertEqual(len(slept), MAX_ATTEMPTS - 1)

    def test_non_canonical_idempotency_key_never_reaches_the_wire(self):
        with LiveServer(lambda attempt: (200, {"ok": True})) as server:
            client = live_client(server.url, [])
            for invalid in ("", "has space", "has\nnewline", "snowman-☃", "x" * 257):
                params = dict(CASE_PARAMS, idempotency_key=invalid)
                with self.assertRaises(TemperaSdkError) as ctx:
                    client.tempera_business.business_cases_review_draft(params)
                self.assertNotIsInstance(ctx.exception, TemperaApiError)
            self.assertEqual(server.received, [])

    def test_canonical_key_matches_the_tempera_mcp_rule_exactly(self):
        self.assertEqual(canonical_idempotency_key("Request-1._~"), "Request-1._~")
        for invalid in ("", "has space", "has\nnewline", "snowman-☃"):
            self.assertIsNone(canonical_idempotency_key(invalid))
        self.assertEqual(canonical_idempotency_key("x" * 256), "x" * 256)
        self.assertIsNone(canonical_idempotency_key("x" * 257))

    def test_backoff_is_exponential_from_250_ms(self):
        self.assertEqual(retry_delay_seconds(2), 0.25)
        self.assertEqual(retry_delay_seconds(3), 0.5)


if __name__ == "__main__":
    unittest.main()
