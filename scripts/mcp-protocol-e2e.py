#!/usr/bin/env python3
"""Run protocol-only Python, TypeScript, and Rust SDK proof against exact MCP.

The disposable server intentionally uses ``auth.mode=none``. This binds wire,
result, and logging semantics only; it is not authorization or tenancy proof.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from tempera_sdk import MCP_PROTOCOL_VERSION, TemperaMcpClient, TemperaMcpError


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def wait_ready(url: str, process: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Tempera MCP exited before readiness with {process.returncode}")
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(0.1)
    raise TimeoutError("Tempera MCP did not become ready")


def rejected_rpc(
    endpoint: str,
    *,
    method: str,
    protocol: str,
    request_id: int,
    expected_http: int,
) -> None:
    meta = {
        "io.modelcontextprotocol/protocolVersion": protocol,
        "io.modelcontextprotocol/clientInfo": {"name": "rejection-probe", "version": "1"},
        "io.modelcontextprotocol/clientCapabilities": {},
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": {"_meta": meta},
            }
        ).encode(),
        headers={
            "accept": "application/json, text/event-stream",
            "content-type": "application/json",
            "mcp-protocol-version": protocol,
            "mcp-method": method,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            raise AssertionError(
                f"{method}/{protocol} returned HTTP {response.status}, expected {expected_http}"
            )
    except urllib.error.HTTPError as error:
        if error.code != expected_http:
            raise AssertionError(
                f"{method}/{protocol} returned HTTP {error.code}, expected {expected_http}"
            )
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--rust-client-binary", type=Path, required=True)
    parser.add_argument("--typescript-client-script", type=Path, required=True)
    args = parser.parse_args()
    binary = args.binary.resolve()
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise SystemExit(f"MCP binary is not executable: {binary}")
    rust_client_binary = args.rust_client_binary.resolve()
    if not rust_client_binary.is_file() or not os.access(rust_client_binary, os.X_OK):
        raise SystemExit(f"Rust MCP E2E client is not executable: {rust_client_binary}")
    expected_rust_client = (
        Path(__file__).resolve().parents[1]
        / "packages/rust/target/debug/examples/mcp_protocol_e2e"
    ).resolve()
    if rust_client_binary != expected_rust_client:
        raise SystemExit(f"Rust MCP E2E client must be the reviewed example: {expected_rust_client}")
    typescript_client_script = args.typescript_client_script.resolve()
    if not typescript_client_script.is_file():
        raise SystemExit(f"TypeScript MCP E2E client is not a file: {typescript_client_script}")
    expected_typescript_client = (
        Path(__file__).resolve().parents[1]
        / "packages/typescript/examples/mcp_protocol_e2e.mjs"
    ).resolve()
    if typescript_client_script != expected_typescript_client:
        raise SystemExit(
            f"TypeScript MCP E2E client must be the reviewed example: {expected_typescript_client}"
        )

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    endpoint = f"{base}/mcp"
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        config = root / "tempera-mcp.toml"
        config.write_text(
            "\n".join(
                [
                    "[server]",
                    f'bind = "127.0.0.1:{port}"',
                    f'public_url = "{endpoint}"',
                    "",
                    "[auth]",
                    'mode = "none"',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        stdout_path = root / "stdout.log"
        stderr_path = root / "stderr.log"
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            process = subprocess.Popen(
                [str(binary), "serve", "--config", str(config)],
                stdout=stdout,
                stderr=stderr,
                env={"PATH": os.environ.get("PATH", ""), "RUST_LOG": "warn"},
            )
            try:
                wait_ready(f"{base}/healthz", process)
                client = TemperaMcpClient(
                    url=endpoint,
                    bearer="local-e2e-placeholder",
                    client_name="tempera-sdk-e2e",
                    client_version="0.13.0",
                )
                discovery = client.discover()
                if discovery.get("resultType") != "complete":
                    raise AssertionError("server/discover did not complete")
                if discovery.get("supportedVersions") != [MCP_PROTOCOL_VERSION]:
                    raise AssertionError("server/discover returned the wrong protocol version")
                tools = client.list_tools()
                if len(tools) != 11:
                    raise AssertionError(f"expected the fixed 11-tool surface, got {len(tools)}")
                if {tool.get("name") for tool in tools} != {
                    "tempera_capability_catalog",
                    "tempera_children",
                    "tempera_commit",
                    "tempera_describe",
                    "tempera_execute_plan",
                    "tempera_invoke",
                    "tempera_manage_connections",
                    "tempera_prepare",
                    "tempera_search",
                    "tempera_status",
                    "tempera_whoami",
                }:
                    raise AssertionError("tools/list did not match the exact fixed surface")
                identity = client.whoami()
                if identity.get("isError") is True:
                    raise AssertionError("tempera_whoami returned a tool error")
                try:
                    client.call_tool("tempera_commit", {"receipt": "secret-argument-sentinel"})
                except TemperaMcpError as error:
                    if not isinstance(error.data, dict) or error.data.get("isError") is not True:
                        raise AssertionError(
                            "invalid tool arguments did not produce a classified tool error"
                        ) from error
                else:
                    raise AssertionError("invalid tool arguments were reported as completed")
                rejected_rpc(
                    endpoint,
                    method="initialize",
                    protocol=MCP_PROTOCOL_VERSION,
                    request_id=99,
                    expected_http=404,
                )
                rejected_rpc(
                    endpoint,
                    method="server/discover",
                    protocol="2025-06-18",
                    request_id=100,
                    expected_http=400,
                )
                rust_result = subprocess.run(
                    [
                        str(rust_client_binary),
                        endpoint,
                        "local-e2e-placeholder",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=20,
                    env={"PATH": os.environ.get("PATH", "")},
                )
                if rust_result.returncode != 0:
                    raise AssertionError("Rust SDK failed its exact MCP protocol E2E")
                if "exact MCP 2026-07-28 Rust SDK E2E passed" not in rust_result.stdout:
                    raise AssertionError("Rust SDK E2E omitted its success receipt")
                typescript_result = subprocess.run(
                    [
                        "node",
                        str(typescript_client_script),
                        endpoint,
                        "local-e2e-placeholder",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=20,
                    env={"PATH": os.environ.get("PATH", "")},
                )
                if typescript_result.returncode != 0:
                    raise AssertionError("TypeScript SDK failed its exact MCP protocol E2E")
                if (
                    "exact MCP 2026-07-28 TypeScript SDK E2E passed"
                    not in typescript_result.stdout
                ):
                    raise AssertionError("TypeScript SDK E2E omitted its success receipt")
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        logs = stdout_path.read_text(encoding="utf-8", errors="replace") + stderr_path.read_text(
            encoding="utf-8", errors="replace"
        )
        if "local-e2e-placeholder" in logs:
            raise AssertionError("MCP logs leaked the bearer")
        if "secret-argument-sentinel" in logs:
            raise AssertionError("MCP logs leaked tool arguments")
        if "rust-secret-argument-sentinel" in logs:
            raise AssertionError("MCP logs leaked Rust tool arguments")
        if "typescript-secret-argument-sentinel" in logs:
            raise AssertionError("MCP logs leaked TypeScript tool arguments")
    print("exact MCP 2026-07-28 Python, TypeScript, and Rust SDK E2E passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
