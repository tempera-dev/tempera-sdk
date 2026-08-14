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

print("registered Tempera Voice as a strict SDK drift product")
