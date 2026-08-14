#!/usr/bin/env python3
"""Prevent the one-shot generator from editing the shared SDK CI workflow."""

from pathlib import Path

path = Path(__file__).resolve().parent / "apply-tempera-voice-sdk.py"
value = path.read_text(encoding="utf-8")
old = "    patch_exact_source_workflow()\n"
if value.count(old) != 1:
    raise SystemExit("Voice SDK exact-source workflow call anchor drifted")
path.write_text(value.replace(old, "", 1), encoding="utf-8")
print("Kept the bulk Voice SDK publisher out of the shared test workflow")
