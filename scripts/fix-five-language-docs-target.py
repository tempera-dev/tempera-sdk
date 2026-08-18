#!/usr/bin/env python3
"""Repair the temporary five-language docs target with quote-safe source.

The main applicator deliberately operates by exact source replacement. This
small bridge replaces only the newly inserted render_index Go/C block so the
committed generator remains ordinary, readable Python after the bootstrap.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "gen-sdk-docs.py"


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    render_index = text.index("def render_index(surface: dict) -> str:")
    start = text.index("\n    go_code = (\n", render_index) + 1
    end = text.index("\n    lines += code_group(\n", start) + 1
    replacement = r'''    go_code = (
        "// Module access and environment values are supplied during onboarding.\n"
        "import (\n"
        '    "context"\n'
        '    "os"\n'
        '    tempera "tempera.dev/sdk-go"\n'
        ")\n"
        "ctx := context.Background()\n"
        'apiKey := os.Getenv("TEMPERA_API_KEY")\n'
        "client := tempera.NewClient()\n"
        'client.BaseURLs["tempo"] = os.Getenv("TEMPERA_TEMPO_URL")\n'
        'client.BaseURLs["palette"] = os.Getenv("TEMPERA_PALETTE_URL")\n'
        'client.Bearers["tempo"] = apiKey\n'
        'client.Bearers["palette"] = apiKey\n'
        "var session map[string]any\n"
        'if err := client.Do(ctx, "tempo", "createSession", map[string]any{\n'
        '    "url": "https://example.com",\n'
        "}, &session); err != nil {\n"
        "    return err\n"
        "}\n"
        "var traces map[string]any\n"
        'if err := client.Do(ctx, "palette", "listTraces", map[string]any{\n'
        '    "tenant_id": os.Getenv("TEMPERA_TENANT_ID"),\n'
        '    "limit": 20,\n'
        "}, &traces); err != nil {\n"
        "    return err\n"
        "}"
    )
    c_quickstart_body = json.dumps(
        {"url": "https://example.com"},
        separators=(",", ":"),
    )
    c_code = (
        "/* The C11 SDK builds bounded request specs; supply your HTTP transport. */\n"
        'const tempera_param params[] = {{"url", "https://example.com"}};\n'
        "tempera_request_spec request;\n"
        f"const char *body_json = {json.dumps(c_quickstart_body)};\n"
        "int rc = tempera_build_request(\n"
        "    tempo_url, api_key, \"tempo\", \"createSession\",\n"
        "    NULL, 0, NULL, body_json, &request);\n"
        "if (rc != TEMPERA_OK) {\n"
        "    /* Handle the fail-closed bounded build error. */\n"
        "}"
    )
'''
    TARGET.write_text(text[:start] + replacement + text[end:], encoding="utf-8")


if __name__ == "__main__":
    main()
