#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, before: str, after: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if after in text:
        return
    if text.count(before) != 1:
        raise SystemExit(f"{path}: expected one registration anchor")
    target.write_text(text.replace(before, after, 1), encoding="utf-8")


# Add Voice to the exact-source vendor and aggregate OpenAPI synchronizers.
replace_once(
    "scripts/sync-vendored-openapi.py",
    '    "temperaRisk": {\n        "source_repo": "tempera-dev/tempera-risk",',
    '    "temperaVoice": {\n        "source_repo": "tempera-dev/tempera-voice",\n        "source_branch": "main",\n        "source_path": "contracts/voice-api.openapi.json",\n        "generated_path": "specs/tempera-voice-api.json",\n        "generated_with": "source_lock.py@1+verbatim-openapi-copy",\n        "transform": "verbatim",\n    },\n    "temperaRisk": {\n        "source_repo": "tempera-dev/tempera-risk",',
)
replace_once(
    "scripts/sync-openapi-surface.py",
    '    "temperaRisk": "tempera-risk-api.json",',
    '    "temperaVoice": "tempera-voice-api.json",\n    "temperaRisk": "tempera-risk-api.json",',
)
replace_once(
    "scripts/sync-openapi-surface.py",
    '    "temperaRisk": "product",',
    '    "temperaVoice": "oauthResource",\n    "temperaRisk": "product",',
)

surface_path = ROOT / "surface.json"
surface = json.loads(surface_path.read_text(encoding="utf-8"))
products = surface["products"]
if "temperaVoice" not in products:
    voice = {
        "name": "tempera-voice",
        "repository": "https://github.com/tempera-dev/tempera-voice",
        "envVar": "TEMPERA_VOICE_URL",
        "audience": "tempera-voice",
        "auth": "bearer minted for audience tempera-voice with voice:read/voice:write/voice:stream or shared eval:run, or a central tp_ API key",
        "description": "Provider-neutral realtime voice control plane with durable sessions, bounded provider adapters, MCP-mediated actions, Palette telemetry, and governed Tempera Evals evidence. A hosted URL must be supplied explicitly until a deployed environment is registered.",
    }
    rebuilt = {}
    inserted = False
    for key, value in products.items():
        if key == "temperaRisk" and not inserted:
            rebuilt["temperaVoice"] = voice
            inserted = True
        rebuilt[key] = value
    if not inserted:
        rebuilt["temperaVoice"] = voice
    surface["products"] = rebuilt
surface.setdefault("operations", {}).setdefault("temperaVoice", [])
surface_path.write_text(json.dumps(surface, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# The Python runtime is dynamic, but keep editor/type discovery uniform with the
# other generated product attributes.
replace_once(
    "packages/python/src/tempera_sdk/client.py",
    '        self.tempera_risk: _ProductClient\n        self.tempera_workflows: _ProductClient',
    '        self.tempera_risk: _ProductClient\n        self.tempera_voice: _ProductClient\n        self.tempera_workflows: _ProductClient',
)

print("registered Tempera Voice in SDK generation inputs")
