#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, before: str, after: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if after in text:
        return
    count = text.count(before)
    if count != 1:
        raise SystemExit(f"{path}: expected one anchor, found {count}: {before[:100]!r}")
    target.write_text(text.replace(before, after, 1), encoding="utf-8")


replace_once(
    "scripts/check-upstream-drift.py",
    '''    "temperaLlm": "tempera-llm-api.json",
    "temperaRisk": "tempera-risk-api.json",
''',
    '''    "temperaLlm": "tempera-llm-api.json",
    "temperaVoice": "tempera-voice-api.json",
    "temperaRisk": "tempera-risk-api.json",
''',
)

replace_once(
    ".github/workflows/test.yml",
    '''          - name: Tempera LLM
            product: temperaLlm
            repository: tempera-llm
            source_branch: main
            source_path: sdks/openapi/tempera-llm-api.json
            lock: specs/tempera-llm-api.json.source
            generated_path: specs/tempera-llm-api.json
            generated_with: source_lock.py@1+verbatim-openapi-copy
            transform: verbatim
          - name: Tempera Workflows
''',
    '''          - name: Tempera LLM
            product: temperaLlm
            repository: tempera-llm
            source_branch: main
            source_path: sdks/openapi/tempera-llm-api.json
            lock: specs/tempera-llm-api.json.source
            generated_path: specs/tempera-llm-api.json
            generated_with: source_lock.py@1+verbatim-openapi-copy
            transform: verbatim
          - name: Tempera Voice
            product: temperaVoice
            repository: tempera-voice
            source_branch: main
            source_path: contracts/voice-api.openapi.json
            lock: specs/tempera-voice-api.json.source
            generated_path: specs/tempera-voice-api.json
            generated_with: source_lock.py@1+verbatim-openapi-copy
            transform: verbatim
          - name: Tempera Workflows
''',
)

print("registered Tempera Voice as a strict exact-source SDK product")
