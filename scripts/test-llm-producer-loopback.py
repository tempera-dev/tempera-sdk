#!/usr/bin/env python3
"""Run SDK clients against an explicitly supplied local gateway binary.

The caller must supply build provenance for that binary. This tests static
fixture authentication and raw tool/structured-output HTTP with a local mock
provider and explicit unmetered mode; it is not hosted or real-provider proof.
"""
import argparse
import hashlib
import http.server
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/python/src"))
from tempera_sdk import TemperaAuth, TemperaClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gateway-binary", required=True, type=Path)
    args = parser.parse_args()
    captured = []
    assistant = {"role": "assistant", "content": None, "tool_calls": [
        {"id": "call_1", "type": "function", "function": {"name": "inspect", "arguments": "{}"}}
    ]}

    class Provider(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            captured.append(body)
            final = body.get("tool_choice") == "none"
            message = {"role": "assistant", "content": "{}"} if final else assistant
            result = {"id": "local", "object": "chat.completion", "created": 1,
                "model": "gpt-4o-mini", "choices": [{"index": 0, "message": message,
                "finish_reason": "stop" if final else "tool_calls"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
            data = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    provider = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    threading.Thread(target=provider.serve_forever, daemon=True).start()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    env = {"PATH": os.environ.get("PATH", ""), "TEMPERA_LLM_BIND": f"127.0.0.1:{port}",
        "TEMPERA_LLM_API_TOKEN": "fixture-key", "TEMPERA_LLM_ALLOW_UNMETERED": "1",
        "TEMPERA_ORGANIZATION": "org_fixture", "TEMPERA_PROJECT": "project_fixture",
        "TEMPERA_ENVIRONMENT": "test",
        "OPENAI_API_KEY": "local-provider-fixture",
        "OPENAI_BASE_URL": f"http://127.0.0.1:{provider.server_port}/v1", "RUST_LOG": "error"}
    process = subprocess.Popen([str(args.gateway_binary.resolve())], env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for attempt in range(100):
            if process.poll() is not None:
                raise RuntimeError("gateway exited before readiness")
            try:
                with urllib.request.urlopen(url + "/healthz", timeout=1):
                    break
            except (OSError, urllib.error.URLError):
                time.sleep(0.05)
        else:
            raise RuntimeError("gateway startup timed out")

        request = {"model": "gpt-4o-mini", "max_tokens": 64,
            "messages": [{"role": "user", "content": "inspect"}],
            "tools": [{"type": "function", "function": {"name": "inspect", "parameters": {"type": "object"}}}],
            "tool_choice": {"type": "function", "function": {"name": "inspect"}}}
        unauthorized = urllib.request.Request(url + "/v1/chat/completions",
            data=json.dumps(request).encode(), headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(unauthorized, timeout=3)
        except urllib.error.HTTPError as error:
            assert error.code == 401
        else:
            raise AssertionError("missing credential was accepted")
        assert captured == []

        py = TemperaClient(auth=TemperaAuth(issuer_url="https://issuer.example.test", api_key="fixture-key"),
            base_urls={"tempera_llm": url})
        js = """const {createTemperaClient,TemperaAuth}=await import(process.argv[1]);
const client=createTemperaClient({auth:new TemperaAuth({issuerUrl:'https://issuer.example.test',apiKey:'fixture-key'}),baseUrls:{temperaLlm:process.argv[2]}});
let raw='';for await(const part of process.stdin)raw+=part;
process.stdout.write(JSON.stringify(await client.temperaLlm.createChatCompletion(JSON.parse(raw))));"""
        for language in ("python", "typescript"):
            def call(payload):
                if language == "python":
                    return py.tempera_llm.create_chat_completion(payload)
                return json.loads(subprocess.check_output(["node", "--input-type=module", "-e", js,
                    (ROOT / "packages/typescript/src/index.js").as_uri(), url],
                    input=json.dumps(payload).encode(), timeout=15))

            result = call(request)
            assert result["choices"][0]["message"] == assistant
            assert captured[-1]["tools"] == request["tools"]
            assert captured[-1]["tool_choice"] == request["tool_choice"]
            final = {"model": request["model"], "max_tokens": 64,
                "messages": request["messages"] + [assistant, {"role": "tool", "tool_call_id": "call_1", "content": "{}"}],
                "tool_choice": "none", "response_format": {"type": "json_schema",
                    "json_schema": {"name": "final", "schema": {"type": "object"}}}}
            assert call(final)["choices"][0]["message"]["content"] == "{}"
            assert captured[-1]["messages"] == final["messages"]
            assert "tools" not in captured[-1]
        print(json.dumps({"result": "PASS", "clients": ["python", "typescript"],
            "provider_calls": len(captured), "missing_credential": "401_before_provider",
            "gateway_binary_sha256": hashlib.sha256(args.gateway_binary.read_bytes()).hexdigest(),
            "usage_mode": "explicit_unmetered_fixture", "provider": "local_mock"}))
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        provider.shutdown()
        provider.server_close()


if __name__ == "__main__":
    main()
