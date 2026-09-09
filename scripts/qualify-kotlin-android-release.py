#!/usr/bin/env python3
"""Qualify the installed minified Android fixture through its real SDK transport.

The host owns the loopback server and device bridge. The fixture action only
hashes its installed APK and calls MainActivity.executeLoopback, so a log line
cannot substitute for the actual GET /base and MCP ping wire exchange.
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import secrets
import socket
import subprocess
import sys
import threading
import time

PACKAGE = "dev.tempera.sdk.fixture"
ACTIVITY = f"{PACKAGE}/.MainActivity"
ACTION = "dev.tempera.sdk.fixture.action.QUALIFY_RELEASE"
LOG_TAG = "TemperaSdkRelease"
EXTRA_NONCE = "tempera.release.nonce"
EXTRA_BASE_URL = "tempera.release.base_url"
EXTRA_EXPECTED_API = "tempera.release.expected_api"
NONCE_RE = re.compile(r"[0-9a-f]{32}\Z")
MAX_APK_BYTES = 64 * 1024 * 1024
MAX_COMMAND_OUTPUT = 128 * 1024
MAX_LOG_OUTPUT = 256 * 1024
MAX_HEADERS = 32 * 1024
MAX_BODY = 64 * 1024
IO_TIMEOUT_SECONDS = 10.0
SERVER_TIMEOUT_SECONDS = 15.0
QUIET_SECONDS = 0.25
COMMAND_TIMEOUT_SECONDS = 20.0
LOG_TIMEOUT_SECONDS = 15.0


class QualificationError(RuntimeError):
    pass


def fail(message):
    raise QualificationError(message)


def bounded_command(arguments, timeout=COMMAND_TIMEOUT_SECONDS, output_limit=MAX_COMMAND_OUTPUT):
    """Run one local command with bounded time and captured output."""
    try:
        process = subprocess.Popen(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as error:
        fail(f"could not start command: {error.__class__.__name__}")
    chunks = []
    byte_count = 0
    overflow = threading.Event()
    lock = threading.Lock()

    def drain(stream):
        nonlocal byte_count
        try:
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    return
                with lock:
                    remaining = output_limit - byte_count
                    if remaining > 0:
                        chunks.append(chunk[:remaining])
                        byte_count += min(len(chunk), remaining)
                    if len(chunk) > remaining:
                        overflow.set()
        finally:
            stream.close()

    readers = [threading.Thread(target=drain, args=(stream,), daemon=True) for stream in (process.stdout, process.stderr)]
    for reader in readers:
        reader.start()
    deadline = time.monotonic() + timeout
    timed_out = False
    while process.poll() is None:
        if overflow.is_set() or time.monotonic() >= deadline:
            timed_out = time.monotonic() >= deadline
            process.terminate()
            break
        time.sleep(0.02)
    try:
        process.wait(timeout=1.0)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=1.0)
    for reader in readers:
        reader.join(1.0)
    if any(reader.is_alive() for reader in readers):
        fail("command output reader did not terminate")
    if timed_out:
        fail("command timed out")
    if overflow.is_set():
        fail("command output exceeded bound")
    output = b"".join(chunks).decode("utf-8", "replace")
    if process.returncode != 0:
        fail(f"command failed with exit {process.returncode}: {output[:512]!r}")
    return output


def adb(*arguments, timeout=COMMAND_TIMEOUT_SECONDS, output_limit=MAX_COMMAND_OUTPUT):
    return bounded_command(["adb", *arguments], timeout=timeout, output_limit=output_limit)


def hash_apk(path):
    if not path.is_file() or path.is_symlink():
        fail("APK must be a regular file")
    if path.stat().st_size <= 0 or path.stat().st_size > MAX_APK_BYTES:
        fail("APK exceeds hash bound")
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as source:
        while True:
            block = source.read(64 * 1024)
            if not block:
                break
            total += len(block)
            if total > MAX_APK_BYTES:
                fail("APK exceeds hash bound")
            digest.update(block)
    return digest.hexdigest()


def require_single_line(output, description):
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if len(lines) != 1:
        fail(f"{description} did not produce exactly one line")
    return lines[0]


def device_api():
    value = require_single_line(adb("shell", "getprop", "ro.build.version.sdk"), "device API")
    if not value.isdecimal():
        fail("device API was not decimal")
    return int(value)


def device_serial():
    value = require_single_line(adb("get-serialno"), "device serial")
    if not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", value):
        fail("device serial was invalid")
    return value


def installed_apk_path():
    value = require_single_line(adb("shell", "pm", "path", PACKAGE), "fixture package path")
    if not value.startswith("package:"):
        fail("fixture package path had unexpected prefix")
    path = value.removeprefix("package:")
    if not path.startswith("/data/app/") or any(character.isspace() for character in path):
        fail("fixture package path was outside the installed app directory")
    return path


def observed_pid(timeout):
    if timeout <= 0:
        fail("fixture process PID deadline elapsed")
    output = adb("shell", "pidof", PACKAGE, timeout=min(COMMAND_TIMEOUT_SECONDS, timeout))
    values = output.split()
    if len(values) != 1 or not values[0].isdecimal() or int(values[0]) <= 0:
        fail("fixture process PID was malformed, absent, or ambiguous")
    return int(values[0])


def wait_for_pid():
    deadline = time.monotonic() + IO_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        try:
            return observed_pid(remaining)
        except QualificationError as error:
            if "absent" not in str(error):
                raise
        time.sleep(0.1)
    fail("fixture process did not start before timeout")


def is_http_token(value):
    return bool(value) and all(
        character.isascii() and (character.isalnum() or character in "!#$%&'*+-.^_`|~")
        for character in value
    )


class WireServer:
    """One bounded local HTTP/1.1 server for the expected SDK base and MCP calls."""

    def __init__(self):
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen(1)
        self._listener.settimeout(IO_TIMEOUT_SECONDS)
        self.port = self._listener.getsockname()[1]
        self.counts = {"base": 0, "mcp": 0}
        self.observations = []
        self._error = None
        self._done = threading.Event()
        self._closing = False
        self._active = None
        self._active_lock = threading.Lock()
        self._thread = None

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.port}"

    def start(self):
        if self._thread is not None:
            fail("wire server was started more than once")
        self._thread = threading.Thread(target=self._serve, name="tempera-release-wire", daemon=True)
        self._thread.start()

    def _serve(self):
        try:
            self._serve_base()
            self._serve_mcp()
            self._listener.settimeout(QUIET_SECONDS)
            try:
                connection, _ = self._listener.accept()
                connection.close()
                fail("fixture sent more than two HTTP requests")
            except socket.timeout:
                pass
        except Exception as error:
            if not self._closing:
                self._error = error
        finally:
            try:
                self._listener.close()
            except OSError:
                pass
            self._done.set()

    def _accept(self):
        connection, _ = self._listener.accept()
        connection.settimeout(IO_TIMEOUT_SECONDS)
        self._after_accept_before_registration(connection)
        with self._active_lock:
            if self._closing:
                connection.close()
                fail("wire server closed while accepting a connection")
            self._active = connection
        return connection

    def _after_accept_before_registration(self, _connection):
        """Test hook for the close-versus-accept ownership handoff."""

    def _release_connection(self, connection):
        with self._active_lock:
            if self._active is connection:
                self._active = None
        connection.close()

    def _serve_base(self):
        connection = self._accept()
        try:
            request = self._read_request(connection)
            self._require_request(request, "GET", "/base", False)
            self._require_headers(request["headers"], {"accept": "application/json", "authorization": "Bearer fixture"})
            self.counts["base"] += 1
            self.observations.append(
                {
                    "method": request["method"],
                    "path": request["path"],
                    "headers": {"accept": request["headers"]["accept"], "authorization": request["headers"]["authorization"]},
                    "body_sha256": hashlib.sha256(request["body"]).hexdigest(),
                }
            )
            self._write_json(connection, {"ok": True})
        finally:
            self._release_connection(connection)

    def _serve_mcp(self):
        connection = self._accept()
        try:
            request = self._read_request(connection)
            self._require_request(request, "POST", "/mcp", True)
            self._require_headers(
                request["headers"],
                {
                    "accept": "application/json",
                    "content-type": "application/json",
                    "authorization": "Bearer fixture",
                    "mcp-protocol-version": "2026-07-28",
                    "mcp-method": "ping",
                },
            )
            try:
                rpc = strict_json(request["body"].decode("utf-8"))
            except UnicodeDecodeError:
                fail("MCP request JSON was not UTF-8")
            if not isinstance(rpc, dict) or set(rpc) != {"jsonrpc", "id", "method", "params"}:
                fail("MCP request outer shape was invalid")
            if rpc.get("jsonrpc") != "2.0" or rpc.get("method") != "ping":
                fail("MCP request shape was invalid")
            identifier = rpc.get("id")
            if type(identifier) is not int or identifier != 1:
                fail("MCP request id was not integer 1")
            params = rpc.get("params")
            if not isinstance(params, dict) or set(params) != {"_meta"}:
                fail("MCP params were not meta-only")
            meta = params["_meta"]
            if not isinstance(meta, dict) or set(meta) != {
                "io.modelcontextprotocol/protocolVersion",
                "io.modelcontextprotocol/clientCapabilities",
            }:
                fail("MCP meta shape was invalid")
            if meta["io.modelcontextprotocol/protocolVersion"] != "2026-07-28":
                fail("MCP protocol version was invalid")
            if meta["io.modelcontextprotocol/clientCapabilities"] != {}:
                fail("MCP client capabilities were not empty")
            self.counts["mcp"] += 1
            self.observations.append(
                {
                    "method": request["method"],
                    "path": request["path"],
                    "headers": {
                        "accept": request["headers"]["accept"],
                        "content-type": request["headers"]["content-type"],
                        "authorization": request["headers"]["authorization"],
                        "mcp-protocol-version": request["headers"]["mcp-protocol-version"],
                        "mcp-method": request["headers"]["mcp-method"],
                    },
                    "rpc_id": identifier,
                    "validated_params": "meta-only protocol=2026-07-28 empty-capabilities",
                    "body_sha256": hashlib.sha256(request["body"]).hexdigest(),
                }
            )
            self._write_json(connection, {"jsonrpc": "2.0", "id": identifier, "result": {"ok": True}})
        finally:
            self._release_connection(connection)

    def _read_request(self, connection):
        deadline = time.monotonic() + IO_TIMEOUT_SECONDS
        data = bytearray()
        while b"\r\n\r\n" not in data:
            if len(data) >= MAX_HEADERS:
                fail("HTTP headers exceeded bound")
            data.extend(self._recv(connection, min(4096, MAX_HEADERS - len(data)), deadline))
        raw_headers, body = bytes(data).split(b"\r\n\r\n", 1)
        try:
            lines = raw_headers.decode("iso-8859-1").split("\r\n")
        except UnicodeDecodeError:
            fail("HTTP headers were not ISO-8859-1")
        if not lines or not lines[0]:
            fail("HTTP request line was missing")
        parts = lines[0].split(" ")
        if len(parts) != 3 or any(not part for part in parts) or parts[2] != "HTTP/1.1":
            fail("HTTP request line was invalid")
        headers = {}
        for line in lines[1:]:
            if not line or ":" not in line:
                fail("HTTP header was invalid")
            name, value = line.split(":", 1)
            name = name.lower()
            if not is_http_token(name) or name in headers:
                fail("HTTP header name was invalid or duplicated")
            headers[name] = value.strip()
        if "transfer-encoding" in headers:
            fail("chunked HTTP framing is unsupported")
        length = self._content_length(headers.get("content-length"))
        if len(body) > length:
            fail("HTTP body exceeded Content-Length")
        while len(body) < length:
            body += self._recv(connection, length - len(body), deadline)
        return {"method": parts[0], "path": parts[1], "headers": headers, "body": body}

    @staticmethod
    def _content_length(value):
        if value is None:
            return 0
        if not value or any(character not in "0123456789" for character in value):
            fail("HTTP Content-Length was invalid")
        length = int(value)
        if length > MAX_BODY:
            fail("HTTP body exceeded bound")
        return length

    @staticmethod
    def _require_headers(headers, required):
        for name, expected in required.items():
            if headers.get(name) != expected:
                fail(f"HTTP header {name} did not match")

    @staticmethod
    def _require_request(request, method, path, has_body):
        if request["method"] != method or request["path"] != path:
            fail("HTTP method or path did not match")
        if bool(request["body"]) != has_body:
            fail("HTTP request body presence did not match")
        if has_body and "content-length" not in request["headers"]:
            fail("HTTP request body lacked Content-Length")
        if not has_body and "content-length" in request["headers"]:
            fail("GET request unexpectedly had Content-Length")

    @staticmethod
    def _recv(connection, count, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            fail("HTTP read deadline elapsed")
        connection.settimeout(min(IO_TIMEOUT_SECONDS, remaining))
        try:
            chunk = connection.recv(count)
        except socket.timeout:
            fail("HTTP read timed out")
        if not chunk:
            fail("unexpected end of HTTP stream")
        return chunk

    @staticmethod
    def _write_json(connection, value):
        body = json.dumps(value, separators=(",", ":")).encode("utf-8")
        response = (
            b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: "
            + str(len(body)).encode("ascii")
            + b"\r\nConnection: close\r\n\r\n"
            + body
        )
        connection.sendall(response)

    def wait(self):
        if self._thread is None:
            fail("wire server was not started")
        if not self._done.wait(SERVER_TIMEOUT_SECONDS):
            fail("wire server did not complete before timeout")
        self._thread.join(1.0)
        if self._thread.is_alive():
            fail("wire server thread did not terminate")
        if self._error is not None:
            fail("wire server rejected fixture traffic")
        if self.counts != {"base": 1, "mcp": 1}:
            fail("wire server did not observe exactly one base and MCP request")

    def close(self):
        with self._active_lock:
            self._closing = True
            active = self._active
            self._active = None
        if active is not None:
            try:
                active.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                active.close()
            except OSError:
                pass
        # A local wakeup avoids waiting for a blocked accept on platforms where
        # closing the listening descriptor alone does not interrupt it.
        try:
            with socket.create_connection(("127.0.0.1", self.port), timeout=0.2):
                pass
        except OSError:
            pass
        try:
            self._listener.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self._listener.close()
        except OSError:
            pass
        if self._thread is None:
            return
        self._thread.join(1.0)
        if self._thread.is_alive():
            fail("wire server thread did not terminate during cleanup")


def strict_json(text):
    def unique_object(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                fail("JSON object contained a duplicate key")
            value[key] = item
        return value

    def reject_constant(value):
        fail(f"JSON contained non-finite constant {value}")

    try:
        return json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant)
    except json.JSONDecodeError as error:
        fail(f"JSON was malformed: {error.msg}")


def parse_log_payloads(output):
    if len(output.encode("utf-8", "replace")) > MAX_LOG_OUTPUT:
        fail("filtered log output exceeded bound")
    payloads = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("---------"):
            continue
        if not line.startswith("{"):
            fail("filtered release log contained a non-JSON message")
        payload = strict_json(line)
        if not isinstance(payload, dict):
            fail("release completion log was not a JSON object")
        payloads.append(payload)
    return payloads


def validate_completion(payloads, nonce, expected_api, expected_pid, expected_apk_sha256):
    if len(payloads) != 1:
        fail("release qualification did not emit exactly one matching completion")
    payload = payloads[0]
    if set(payload) != {"nonce", "api", "pid", "package", "debuggable", "apk_sha256", "status", "result"}:
        fail("release completion had an unexpected schema")
    if not isinstance(payload["nonce"], str) or not NONCE_RE.fullmatch(payload["nonce"]):
        fail("release completion nonce was invalid")
    if type(payload["api"]) is not int or payload["api"] <= 0 or type(payload["pid"]) is not int or payload["pid"] <= 0:
        fail("release completion API or PID was invalid")
    if not isinstance(payload["apk_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", payload["apk_sha256"]):
        fail("release completion APK digest was invalid")
    if payload.get("package") != PACKAGE:
        fail("release completion package did not match fixture")
    if type(payload["debuggable"]) is not bool or payload["debuggable"]:
        fail("installed fixture app was debuggable")
    if payload.get("nonce") != nonce or payload.get("api") != expected_api or payload.get("pid") != expected_pid:
        fail("release completion nonce, API, or PID did not match")
    if payload.get("apk_sha256") != expected_apk_sha256:
        fail("release completion APK digest did not match")
    if payload.get("status") != "ok" or payload.get("result") != "true:true":
        fail("release completion reported an error or unexpected SDK result")
    return payload


def release_log_payloads(pid, timeout):
    return parse_log_payloads(
        adb(
            "logcat",
            "-d",
            "-v",
            "raw",
            "--pid",
            str(pid),
            "-s",
            f"{LOG_TAG}:I",
            timeout=timeout,
            output_limit=MAX_LOG_OUTPUT,
        )
    )


def wait_for_completion(nonce, expected_api, expected_pid, expected_apk_sha256):
    deadline = time.monotonic() + LOG_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        payloads = release_log_payloads(expected_pid, min(COMMAND_TIMEOUT_SECONDS, remaining))
        if payloads:
            return validate_completion(payloads, nonce, expected_api, expected_pid, expected_apk_sha256)
        time.sleep(0.2)
    fail("release completion log was missing before timeout")


def fresh_evidence_directory(path):
    if path.exists():
        fail("evidence directory must not already exist")
    path.mkdir(parents=True)
    return path


def write_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    temporary.replace(path)


def qualify(apk, expected_api, evidence_dir):
    source_sha256 = hash_apk(apk)
    server = WireServer()
    reverse_added = False
    installed_sha256 = None
    receipt = None
    nonce = secrets.token_hex(16)
    if not NONCE_RE.fullmatch(nonce):
        fail("nonce generation failed")
    operation_error = None
    try:
        adb("install", "-r", str(apk))
        actual_api = device_api()
        if actual_api != expected_api:
            fail("device API did not match expected API")
        serial = device_serial()
        remote_apk = installed_apk_path()
        installed_apk = evidence_dir / "installed-fixture.apk"
        adb("pull", remote_apk, str(installed_apk), timeout=COMMAND_TIMEOUT_SECONDS)
        installed_sha256 = hash_apk(installed_apk)
        if installed_sha256 != source_sha256:
            fail("installed fixture APK digest differed from source APK")
        adb("shell", "am", "force-stop", PACKAGE)
        reverse_added = True
        adb("reverse", f"tcp:{server.port}", f"tcp:{server.port}")
        server.start()
        adb(
            "shell",
            "am",
            "start",
            "-W",
            "-n",
            ACTIVITY,
            "-a",
            ACTION,
            "--es",
            EXTRA_NONCE,
            nonce,
            "--es",
            EXTRA_BASE_URL,
            server.base_url,
            "--es",
            EXTRA_EXPECTED_API,
            str(expected_api),
        )
        pid = wait_for_pid()
        server.wait()
        completion = wait_for_completion(nonce, expected_api, pid, installed_sha256)
        time.sleep(QUIET_SECONDS)
        if observed_pid(IO_TIMEOUT_SECONDS) != pid:
            fail("fixture process PID changed before completion receipt")
        completion = validate_completion(
            release_log_payloads(pid, IO_TIMEOUT_SECONDS), nonce, expected_api, pid, installed_sha256
        )
        receipt = {
            "code": "tempera-kotlin-android-release-qualification/v1",
            "source_sha": os.environ.get("GITHUB_SHA", "manual"),
            "ci_run_id": os.environ.get("GITHUB_RUN_ID", "manual"),
            "source_apk": apk.name,
            "source_apk_sha256": source_sha256,
            "installed_apk_sha256": installed_sha256,
            "expected_api": expected_api,
            "device_api": actual_api,
            "device_serial": serial,
            "nonce": nonce,
            "pid": pid,
            "package": completion["package"],
            "debuggable": completion["debuggable"],
            "status": completion["status"],
            "result": completion["result"],
            "wire_counts": server.counts,
            "wire_observations": server.observations,
        }
    except Exception as error:
        operation_error = error
        raise
    finally:
        cleanup_errors = []
        if reverse_added:
            try:
                adb("reverse", "--remove", f"tcp:{server.port}")
            except QualificationError as error:
                cleanup_errors.append(f"reverse removal: {error}")
        try:
            adb("shell", "am", "force-stop", PACKAGE)
        except QualificationError as error:
            cleanup_errors.append(f"force stop: {error}")
        try:
            server.close()
        except QualificationError as error:
            cleanup_errors.append(f"wire server: {error}")
        if cleanup_errors:
            message = "release qualification cleanup failed: " + "; ".join(cleanup_errors)
            if operation_error is not None:
                raise QualificationError(f"{operation_error}; {message}") from operation_error
            fail(message)
    if receipt is None:
        fail("release qualification did not produce a receipt")
    write_json(evidence_dir / "receipt.json", receipt)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", required=True, type=pathlib.Path)
    parser.add_argument("--expected-api", required=True, type=int)
    parser.add_argument("--evidence-dir", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)
    if args.expected_api <= 0:
        parser.error("--expected-api must be positive")
    evidence_created = False
    try:
        apk = args.apk.resolve(strict=True)
        evidence_dir = fresh_evidence_directory(args.evidence_dir)
        evidence_created = True
        receipt = qualify(apk, args.expected_api, evidence_dir)
    except (OSError, QualificationError, ValueError) as error:
        if evidence_created:
            write_json(
                args.evidence_dir / "failure.json",
                {"code": "tempera-kotlin-android-release-qualification/v1", "status": "error", "error": str(error)[:512]},
            )
        print(f"release qualification failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
