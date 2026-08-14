#!/usr/bin/env python3
"""Register Tempera Voice in the aggregate SDK before source regeneration."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def write(relative: str, value: str) -> None:
    (ROOT / relative).write_text(value, encoding="utf-8")


def replace_once(relative: str, old: str, new: str) -> None:
    value = read(relative)
    count = value.count(old)
    if count != 1:
        raise SystemExit(f"{relative}: expected one anchor, found {count}: {old[:120]!r}")
    write(relative, value.replace(old, new, 1))


def patch_surface_seed() -> None:
    path = ROOT / "surface.json"
    surface = json.loads(path.read_text(encoding="utf-8"))
    if "temperaVoice" in surface["products"] or "temperaVoice" in surface["operations"]:
        raise SystemExit("surface.json already contains Tempera Voice")
    surface["version"] = max(int(surface.get("version", 0)) + 1, 7)
    targets = {
        "local": "http://127.0.0.1:8102",
        "preview": "https://preview-voice.tempera.dev",
        "staging": "https://staging-voice.tempera.dev",
        "production": "https://voice.tempera.dev",
    }
    for environment, target in surface["environments"].items():
        if "temperaVoiceApiUrl" in target:
            raise SystemExit(f"{environment} already contains temperaVoiceApiUrl")
        target["temperaVoiceApiUrl"] = targets[environment]
    products: dict[str, object] = {}
    inserted = False
    for key, value in surface["products"].items():
        products[key] = value
        if key == "temperaPayments":
            products["temperaVoice"] = {
                "name": "tempera-voice",
                "repository": "https://github.com/tempera-dev/tempera-voice",
                "envVar": "TEMPERA_VOICE_URL",
                "audience": "tempera-voice",
                "auth": (
                    "bearer minted for audience tempera-voice with the operation's "
                    "voice scope or eval:run, or a central tp_ API key"
                ),
                "description": (
                    "Provider-neutral realtime voice control plane with durable sessions, "
                    "bounded media, MCP-mediated actions, Palette telemetry, and governed "
                    "Tempera Evals evidence."
                ),
            }
            inserted = True
    if not inserted:
        raise SystemExit("surface.json is missing the temperaPayments insertion anchor")
    surface["products"] = products
    operations: dict[str, object] = {}
    inserted = False
    for key, value in surface["operations"].items():
        operations[key] = value
        if key == "temperaPayments":
            operations["temperaVoice"] = []
            inserted = True
    if not inserted:
        raise SystemExit("surface.json operations are missing temperaPayments")
    surface["operations"] = operations
    surface["errorContract"]["wireShapes"]["temperaVoice"] = (
        '{"error":{"code":<number>,"message":"<text>","status":"<enum>",'
        '"details":[]}} for HTTP routes; WebSocket failures use the versioned Voice '
        "stream envelope and close codes"
    )
    path.write_text(json.dumps(surface, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def patch_registries() -> None:
    replace_once(
        "scripts/sync-vendored-openapi.py",
        '    "temperaPayments": {\n'
        '        "source_repo": "tempera-dev/tempera-payments",\n',
        '    "temperaVoice": {\n'
        '        "source_repo": "tempera-dev/tempera-voice",\n'
        '        "source_branch": "main",\n'
        '        "source_path": "contracts/voice-api.openapi.json",\n'
        '        "generated_path": "specs/tempera-voice-api.json",\n'
        '        "generated_with": "source_lock.py@1+verbatim-openapi-copy",\n'
        '        "transform": "verbatim",\n'
        '    },\n'
        '    "temperaPayments": {\n'
        '        "source_repo": "tempera-dev/tempera-payments",\n',
    )
    replace_once(
        "scripts/sync-openapi-surface.py",
        '    "temperaPayments": "tempera-payments-api.json",\n',
        '    "temperaVoice": "tempera-voice-api.json",\n'
        '    "temperaPayments": "tempera-payments-api.json",\n',
    )
    replace_once(
        "scripts/sync-openapi-surface.py",
        '    "temperaPayments": "oauthResource",\n',
        '    "temperaVoice": "oauthResource",\n'
        '    "temperaPayments": "oauthResource",\n',
    )
    replace_once(
        "scripts/check-upstream-drift.py",
        '    "temperaPayments": "tempera-payments-api.json",\n',
        '    "temperaVoice": "tempera-voice-api.json",\n'
        '    "temperaPayments": "tempera-payments-api.json",\n',
    )


def patch_clients_and_tests() -> None:
    replace_once(
        "packages/typescript/src/client.js",
        '          temperaRisk: environmentTargets.temperaRiskApiUrl,\n',
        '          temperaRisk: environmentTargets.temperaRiskApiUrl,\n'
        '          temperaVoice: environmentTargets.temperaVoiceApiUrl,\n',
    )
    replace_once(
        "packages/typescript/src/index.d.ts",
        '  TemperaRiskClient,\n',
        '  TemperaRiskClient,\n  TemperaVoiceClient,\n',
    )
    replace_once(
        "packages/typescript/src/index.d.ts",
        '  temperaRisk: TemperaRiskClient;\n',
        '  temperaRisk: TemperaRiskClient;\n  temperaVoice: TemperaVoiceClient;\n',
    )
    replace_once(
        "packages/typescript/test/client.test.mjs",
        '      temperaRisk: "https://risk.example.test",\n',
        '      temperaRisk: "https://risk.example.test",\n'
        '      temperaVoice: "https://voice.example.test",\n',
    )
    replace_once(
        "packages/python/src/tempera_sdk/client.py",
        '    "temperaRisk": "temperaRiskApiUrl",\n',
        '    "temperaRisk": "temperaRiskApiUrl",\n'
        '    "temperaVoice": "temperaVoiceApiUrl",\n',
    )
    replace_once(
        "packages/python/src/tempera_sdk/client.py",
        '        self.tempera_risk: _ProductClient\n',
        '        self.tempera_risk: _ProductClient\n'
        '        self.tempera_voice: _ProductClient\n',
    )
    replace_once(
        "packages/python/tests/test_client.py",
        '    "temperaRisk": "tempera_risk",\n',
        '    "temperaRisk": "tempera_risk",\n'
        '    "temperaVoice": "tempera_voice",\n',
    )
    replace_once(
        "packages/python/tests/test_client.py",
        '            "tempera_risk": "https://risk.example.test",\n',
        '            "tempera_risk": "https://risk.example.test",\n'
        '            "tempera_voice": "https://voice.example.test",\n',
    )


def patch_inventory() -> None:
    replace_once(
        "sdk.toml",
        '[products.tempera_risk]\n',
        '[products.tempera_voice]\n'
        'name = "tempera-voice"\n'
        'repository = "https://github.com/tempera-dev/tempera-voice"\n'
        'visibility = "private"\n'
        'default_env = "TEMPERA_VOICE_URL"\n'
        'scopes = ["voice:read", "voice:write", "voice:stream", "eval:run"]\n\n'
        '[products.tempera_risk]\n',
    )
    replace_once(
        "README.md",
        '| `temperaBio` / `tempera_bio` | [tempera-bio](https://github.com/tempera-dev/tempera-bio) — fail-closed computational-biology artifacts, Gym selection materialization, measurement verification, and replay-derived campaign state | 10 | `tempera-bio` |\n',
        '| `temperaBio` / `tempera_bio` | [tempera-bio](https://github.com/tempera-dev/tempera-bio) — fail-closed computational-biology artifacts, Gym selection materialization, measurement verification, and replay-derived campaign state | 10 | `tempera-bio` |\n'
        '| `temperaVoice` / `tempera_voice` | [tempera-voice](https://github.com/tempera-dev/tempera-voice) — provider-neutral realtime voice control plane; typed HTTP operations plus a separately versioned full-duplex WebSocket contract | 23 | `tempera-voice` |\n',
    )
    replace_once(
        "README.md",
        '`tempera-llm`, `tempera-workflows`, and `tempera-mcp` registered).',
        '`tempera-llm`, `tempera-workflows`, `tempera-voice`, and `tempera-mcp` registered).',
    )


def patch_exact_source_workflow() -> None:
    relative = ".github/workflows/test.yml"
    value = read(relative)
    old_expected = '''          expected = {
              "source_repo": "tempera-dev/auth-hub",
              "source_branch": "main",
              "source_path": "contracts/control-plane.openapi.json",
          }
'''
    new_expected = '''          expected = {
              "source_repo": "tempera-dev/auth-hub",
              "source_path": "contracts/control-plane.openapi.json",
          }
'''
    if value.count(old_expected) != 1:
        raise SystemExit("Auth Hub exact-source expected-values anchor drifted")
    value = value.replace(old_expected, new_expected, 1)
    old_output = '''          commit = lock.get("source_commit", "")
          if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
              raise SystemExit("source_commit must be a 40-character lowercase SHA")
          with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
              output.write(f"commit={commit}\\n")
'''
    new_output = '''          commit = lock.get("source_commit", "")
          branch = lock.get("source_branch", "")
          if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
              raise SystemExit("source_commit must be a 40-character lowercase SHA")
          if (
              re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,255}", branch) is None
              or ".." in branch
              or branch.endswith("/")
          ):
              raise SystemExit("source_branch must be a safe exact Git branch")
          with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
              output.write(f"commit={commit}\\n")
              output.write(f"branch={branch}\\n")
'''
    if value.count(old_output) < 1:
        raise SystemExit("Auth Hub exact-source output anchor drifted")
    value = value.replace(old_output, new_output, 1)
    old_verify = '''          git -C .auth-hub-source fetch --no-tags origin main:refs/remotes/origin/main
          test "$(git -C .auth-hub-source rev-parse HEAD)" = "$(git -C .auth-hub-source rev-parse refs/remotes/origin/main)"
          python3 scripts/sync-control-plane-openapi.py --check --source-repo-dir .auth-hub-source --source-commit "${{ steps.auth-hub-lock.outputs.commit }}"
'''
    new_verify = '''          git -C .auth-hub-source fetch --no-tags origin "${{ steps.auth-hub-lock.outputs.branch }}:refs/remotes/origin/sdk-source"
          test "$(git -C .auth-hub-source rev-parse HEAD)" = "$(git -C .auth-hub-source rev-parse refs/remotes/origin/sdk-source)"
          python3 scripts/sync-control-plane-openapi.py --check --source-repo-dir .auth-hub-source --source-branch "${{ steps.auth-hub-lock.outputs.branch }}" --source-commit "${{ steps.auth-hub-lock.outputs.commit }}"
'''
    if value.count(old_verify) != 1:
        raise SystemExit("Auth Hub exact-source verification anchor drifted")
    value = value.replace(old_verify, new_verify, 1)
    matrix_anchor = '''          - name: Tempera Payments
            product: temperaPayments
            repository: tempera-payments
'''
    voice_matrix = '''          - name: Tempera Voice
            product: temperaVoice
            repository: tempera-voice
            source_branch: agent/full-stack-voice-api
            source_path: contracts/voice-api.openapi.json
            lock: specs/tempera-voice-api.json.source
            generated_path: specs/tempera-voice-api.json
            generated_with: source_lock.py@1+verbatim-openapi-copy
            transform: verbatim
'''
    if value.count(matrix_anchor) != 1:
        raise SystemExit("upstream exact-source matrix anchor drifted")
    value = value.replace(matrix_anchor, voice_matrix + matrix_anchor, 1)
    write(relative, value)


def main() -> None:
    patch_surface_seed()
    patch_registries()
    patch_clients_and_tests()
    patch_inventory()
    patch_exact_source_workflow()
    print("Staged Tempera Voice aggregate SDK integration")


if __name__ == "__main__":
    main()
