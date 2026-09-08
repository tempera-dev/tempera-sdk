#!/usr/bin/env python3
import importlib.util
import contextlib
import io
import json
import pathlib
import socket
import sys
import tempfile
import time
import threading
import unittest
from unittest import mock

SCRIPT = pathlib.Path(__file__).with_name("qualify-kotlin-android-release.py")
spec = importlib.util.spec_from_file_location("release_qualifier", SCRIPT)
qualifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qualifier)

NONCE = "0123456789abcdef0123456789abcdef"
SHA = "a" * 64


def read_response(connection):
    data = bytearray()
    deadline = time.monotonic() + 2.0
    while b"\r\n\r\n" not in data:
        if len(data) >= qualifier.MAX_HEADERS or time.monotonic() >= deadline:
            raise AssertionError("response headers did not complete within bounds")
        chunk = connection.recv(min(4096, qualifier.MAX_HEADERS - len(data)))
        if not chunk:
            raise AssertionError("response closed before headers")
        data.extend(chunk)
    headers, body = bytes(data).split(b"\r\n\r\n", 1)
    length = next(
        int(line.split(b":", 1)[1].strip())
        for line in headers.split(b"\r\n")
        if line.lower().startswith(b"content-length:")
    )
    if length < 0 or length > qualifier.MAX_BODY or len(body) > length:
        raise AssertionError("response body framing was invalid")
    while len(body) < length:
        if time.monotonic() >= deadline:
            raise AssertionError("response body did not complete within deadline")
        chunk = connection.recv(min(4096, length - len(body)))
        if not chunk:
            raise AssertionError("response closed before body")
        body += chunk
    return json.loads(body[:length].decode("utf-8"))


def send_request(port, request):
    with socket.create_connection(("127.0.0.1", port), timeout=2.0) as connection:
        connection.sendall(request)
        return read_response(connection)


class CompletionValidationTest(unittest.TestCase):
    def payload(self):
        return {
            "nonce": NONCE,
            "api": 36,
            "pid": 1234,
            "package": qualifier.PACKAGE,
            "debuggable": False,
            "apk_sha256": SHA,
            "status": "ok",
            "result": "true:true",
        }

    def test_valid_completion(self):
        self.assertEqual(
            qualifier.validate_completion([self.payload()], NONCE, 36, 1234, SHA)["result"],
            "true:true",
        )

    def test_completion_poison_is_rejected(self):
        for field, value in [
            ("nonce", "f" * 32),
            ("api", 26),
            ("pid", 9),
            ("debuggable", True),
            ("debuggable", 0),
            ("debuggable", "false"),
            ("apk_sha256", "b" * 64),
            ("status", "error"),
            ("result", "true:false"),
        ]:
            with self.subTest(field=field):
                payload = self.payload()
                payload[field] = value
                with self.assertRaises(qualifier.QualificationError):
                    qualifier.validate_completion([payload], NONCE, 36, 1234, SHA)
        with self.assertRaises(qualifier.QualificationError):
            qualifier.validate_completion([self.payload(), self.payload()], NONCE, 36, 1234, SHA)

    def test_log_parser_is_strict_and_completion_rejects_stale_nonce(self):
        output = "\n".join(
            [
                json.dumps({"nonce": "f" * 32}),
                json.dumps(self.payload()),
            ]
        )
        payloads = qualifier.parse_log_payloads(output)
        self.assertEqual(len(payloads), 2)
        with self.assertRaises(qualifier.QualificationError):
            qualifier.validate_completion(payloads, NONCE, 36, 1234, SHA)
        for poison in ('{"nonce":"x","nonce":"y"}', '{"value":NaN}', 'not-json'):
            with self.subTest(poison=poison), self.assertRaises(qualifier.QualificationError):
                qualifier.parse_log_payloads(poison)


class WireServerTest(unittest.TestCase):
    def request_pair(self, server):
        self.assertEqual(
            send_request(
                server.port,
                b"GET /base HTTP/1.1\r\nHost: fixture\r\nAccept: application/json\r\nAuthorization: Bearer fixture\r\n\r\n",
            ),
            {"ok": True},
        )
        rpc = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "ping",
            "params": {
                "_meta": {
                    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                    "io.modelcontextprotocol/clientCapabilities": {},
                }
            },
        }
        body = json.dumps(rpc, separators=(",", ":")).encode("utf-8")
        response = send_request(
            server.port,
            b"POST /mcp HTTP/1.1\r\nHost: fixture\r\nAccept: application/json\r\nContent-Type: application/json\r\nAuthorization: Bearer fixture\r\nMcp-Protocol-Version: 2026-07-28\r\nMcp-Method: ping\r\nContent-Length: "
            + str(len(body)).encode("ascii")
            + b"\r\n\r\n"
            + body,
        )
        self.assertEqual(response, {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}})

    def test_exact_sdk_wire_pair(self):
        server = qualifier.WireServer()
        try:
            server.start()
            self.request_pair(server)
            server.wait()
            self.assertEqual(server.counts, {"base": 1, "mcp": 1})
        finally:
            server.close()

    def test_bad_bearer_is_not_a_pass(self):
        server = qualifier.WireServer()
        try:
            server.start()
            with socket.create_connection(("127.0.0.1", server.port), timeout=2.0) as connection:
                connection.sendall(
                    b"GET /base HTTP/1.1\r\nHost: fixture\r\nAccept: application/json\r\nAuthorization: Bearer poison\r\n\r\n"
                )
            with self.assertRaises(qualifier.QualificationError):
                server.wait()
        finally:
            server.close()

    def test_mcp_duplicate_keys_and_nonfinite_values_are_rejected(self):
        poison_bodies = [
            b'{"jsonrpc":"2.0","id":1,"id":1,"method":"ping","params":{}}',
            b'{"jsonrpc":"2.0","id":1,"method":"ping","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":NaN}}}',
        ]
        for body in poison_bodies:
            with self.subTest(body=body):
                server = qualifier.WireServer()
                try:
                    server.start()
                    send_request(
                        server.port,
                        b"GET /base HTTP/1.1\r\nHost: fixture\r\nAccept: application/json\r\nAuthorization: Bearer fixture\r\n\r\n",
                    )
                    with socket.create_connection(("127.0.0.1", server.port), timeout=2.0) as connection:
                        connection.sendall(
                            b"POST /mcp HTTP/1.1\r\nHost: fixture\r\nAccept: application/json\r\nContent-Type: application/json\r\nAuthorization: Bearer fixture\r\nMcp-Protocol-Version: 2026-07-28\r\nMcp-Method: ping\r\nContent-Length: "
                            + str(len(body)).encode("ascii")
                            + b"\r\n\r\n"
                            + body
                        )
                    with self.assertRaises(qualifier.QualificationError):
                        server.wait()
                finally:
                    server.close()

    def test_non_ascii_content_length_is_rejected(self):
        with self.assertRaises(qualifier.QualificationError):
            qualifier.WireServer._content_length("١")


class BoundsTest(unittest.TestCase):
    def test_hash_rejects_oversized_and_symlinked_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            apk = root / "fixture.apk"
            apk.write_bytes(b"apk")
            self.assertEqual(len(qualifier.hash_apk(apk)), 64)
            link = root / "fixture-link.apk"
            link.symlink_to(apk.name)
            with self.assertRaises(qualifier.QualificationError):
                qualifier.hash_apk(link)
            old_limit = qualifier.MAX_APK_BYTES
            qualifier.MAX_APK_BYTES = 1
            try:
                with self.assertRaises(qualifier.QualificationError):
                    qualifier.hash_apk(apk)
            finally:
                qualifier.MAX_APK_BYTES = old_limit

    def test_bounded_command_rejects_timeout_and_output_overflow(self):
        with self.assertRaises(qualifier.QualificationError):
            qualifier.bounded_command([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.05)
        with self.assertRaises(qualifier.QualificationError):
            qualifier.bounded_command([sys.executable, "-c", "print('x' * 10000)"], output_limit=16)

    def test_stalled_wire_read_closes_promptly(self):
        server = qualifier.WireServer()
        server.start()
        connection = socket.create_connection(("127.0.0.1", server.port), timeout=2.0)
        try:
            connection.sendall(b"GET /base HTTP/1.1\r\n")
            time.sleep(0.05)
            started = time.monotonic()
            server.close()
            self.assertLess(time.monotonic() - started, 1.5)
        finally:
            connection.close()

    def test_close_wins_accept_registration_handoff(self):
        class RegistrationBarrierServer(qualifier.WireServer):
            def __init__(self):
                self.accepted = threading.Event()
                self.release = threading.Event()
                super().__init__()

            def _after_accept_before_registration(self, _connection):
                self.accepted.set()
                if not self.release.wait(1.0):
                    raise AssertionError("test did not release accepted socket")

        server = RegistrationBarrierServer()
        server.start()
        connection = socket.create_connection(("127.0.0.1", server.port), timeout=2.0)
        close_error = []

        def close_server():
            try:
                server.close()
            except Exception as error:  # pragma: no cover - asserted below
                close_error.append(error)

        closer = threading.Thread(target=close_server)
        try:
            self.assertTrue(server.accepted.wait(1.0))
            closer.start()
            deadline = time.monotonic() + 1.0
            while not server._closing and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(server._closing)
            server.release.set()
            closer.join(1.5)
            self.assertFalse(closer.is_alive())
            self.assertEqual(close_error, [])
        finally:
            server.release.set()
            connection.close()
            if closer.is_alive():
                closer.join(1.5)


class FakeWireServer:
    def __init__(self):
        self.port = 39001
        self.counts = {"base": 1, "mcp": 1}
        self.observations = [{"method": "GET", "path": "/base", "body_sha256": "0" * 64}, {"method": "POST", "path": "/mcp", "rpc_id": 1, "body_sha256": "1" * 64}]
        self.started = False
        self.closed = False

    @property
    def base_url(self):
        return "http://127.0.0.1:39001"

    def start(self):
        self.started = True

    def wait(self):
        if not self.started:
            raise AssertionError("server was not started")

    def close(self):
        self.closed = True


class FakeAdb:
    def __init__(self, source, pull_bytes, payloads, pids=(1234, 1234), cleanup_fails=False):
        self.source = source
        self.pull_bytes = pull_bytes
        self.payloads = payloads
        self.pids = list(pids)
        self.cleanup_fails = cleanup_fails
        self.calls = []

    def __call__(self, *arguments, **_kwargs):
        self.calls.append(arguments)
        if arguments[:2] == ("install", "-r"):
            return "Success\n"
        if arguments == ("shell", "getprop", "ro.build.version.sdk"):
            return "36\n"
        if arguments == ("get-serialno",):
            return "emulator-5554\n"
        if arguments == ("shell", "pm", "path", qualifier.PACKAGE):
            return "package:/data/app/fixture/base.apk\n"
        if arguments[:1] == ("pull",):
            pathlib.Path(arguments[2]).write_bytes(self.pull_bytes)
            return "1 file pulled\n"
        if arguments == ("shell", "pidof", qualifier.PACKAGE):
            return f"{self.pids.pop(0) if self.pids else 1234}\n"
        if arguments[:1] == ("logcat",):
            return "\n".join(json.dumps(payload) for payload in self.payloads)
        if arguments[:2] == ("reverse", "--remove") and self.cleanup_fails:
            raise qualifier.QualificationError("reverse removal failed")
        if arguments[:1] in (("reverse",), ("shell",)):
            return "\n"
        raise AssertionError(f"unexpected adb call {arguments}")


class QualifyControlFlowTest(unittest.TestCase):
    def run_qualify(self, pull_bytes=b"fixture", payloads=None, pids=(1234, 1234), cleanup_fails=False, log_timeout=None):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            apk = root / "fixture.apk"
            apk.write_bytes(b"fixture")
            evidence = root / "evidence"
            evidence.mkdir()
            sha = qualifier.hash_apk(apk)
            payload = {
                "nonce": NONCE,
                "api": 36,
                "pid": 1234,
                "package": qualifier.PACKAGE,
                "debuggable": False,
                "apk_sha256": sha,
                "status": "ok",
                "result": "true:true",
            }
            fake_adb = FakeAdb(apk, pull_bytes, [payload] if payloads is None else payloads, pids, cleanup_fails)
            patches = [
                mock.patch.object(qualifier, "adb", fake_adb),
                mock.patch.object(qualifier, "WireServer", FakeWireServer),
                mock.patch.object(qualifier.secrets, "token_hex", return_value=NONCE),
            ]
            if log_timeout is not None:
                patches.append(mock.patch.object(qualifier, "LOG_TIMEOUT_SECONDS", log_timeout))
            with patches[0], patches[1], patches[2]:
                if len(patches) == 4:
                    with patches[3]:
                        return self._qualify_result(apk, evidence, fake_adb)
                return self._qualify_result(apk, evidence, fake_adb)

    @staticmethod
    def _qualify_result(apk, evidence, fake_adb):
        try:
            receipt = qualifier.qualify(apk, 36, evidence)
        except qualifier.QualificationError:
            receipt = None
        receipt_path = evidence / "receipt.json"
        persisted = json.loads(receipt_path.read_text()) if receipt_path.exists() else None
        return receipt, {"receipt_exists": receipt_path.exists(), "receipt": persisted}, fake_adb

    def test_installed_hash_mismatch_cannot_write_pass_receipt(self):
        receipt, outcome, _ = self.run_qualify(pull_bytes=b"different")
        self.assertIsNone(receipt)
        self.assertFalse(outcome["receipt_exists"])

    def test_success_writes_receipt_only_after_cleanup(self):
        receipt, outcome, fake_adb = self.run_qualify()
        self.assertIsNotNone(receipt)
        self.assertTrue(outcome["receipt_exists"])
        stored = outcome["receipt"]
        self.assertEqual(stored["device_serial"], "emulator-5554")
        self.assertEqual(stored["package"], qualifier.PACKAGE)
        self.assertFalse(stored["debuggable"])
        self.assertIn(("reverse", "--remove", "tcp:39001"), fake_adb.calls)

    def test_pid_change_and_missing_log_cannot_write_pass_receipt(self):
        receipt, outcome, _ = self.run_qualify(pids=(1234, 5678))
        self.assertIsNone(receipt)
        self.assertFalse(outcome["receipt_exists"])
        receipt, outcome, _ = self.run_qualify(payloads=[], log_timeout=0.01)
        self.assertIsNone(receipt)
        self.assertFalse(outcome["receipt_exists"])

    def test_cleanup_failure_cannot_write_pass_receipt_and_removes_reverse(self):
        receipt, outcome, fake_adb = self.run_qualify(cleanup_fails=True)
        self.assertIsNone(receipt)
        self.assertFalse(outcome["receipt_exists"])
        self.assertIn(("reverse", "--remove", "tcp:39001"), fake_adb.calls)

    def test_main_records_failure_without_a_pass_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            apk = root / "fixture.apk"
            apk.write_bytes(b"fixture")
            evidence = root / "evidence"
            with contextlib.redirect_stderr(io.StringIO()), mock.patch.object(
                qualifier, "qualify", side_effect=qualifier.QualificationError("cleanup failed")
            ):
                self.assertEqual(qualifier.main(["--apk", str(apk), "--expected-api", "36", "--evidence-dir", str(evidence)]), 1)
            self.assertFalse((evidence / "receipt.json").exists())
            failure = json.loads((evidence / "failure.json").read_text())
            self.assertEqual(failure["status"], "error")
            self.assertIn("cleanup failed", failure["error"])


if __name__ == "__main__":
    unittest.main()
