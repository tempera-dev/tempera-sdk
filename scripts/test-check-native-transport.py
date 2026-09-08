#!/usr/bin/env python3
"""Unit tests for the native transport contract builder and call-site checker."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check-native-transport.py"

spec = importlib.util.spec_from_file_location("check_native_transport", SCRIPT)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

VOICE_OPERATIONS = {
    "createVoiceSession",
    "getVoiceSession",
    "listVoiceSessions",
    "listVoiceSessionActions",
    "listVoiceSessionEvents",
    "endVoiceSession",
    "resolveVoiceAction",
    "listVoiceAgents",
    "getDefaultVoiceAgent",
}


class ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = module.build_contract()
        cls.surface = json.loads((ROOT / "surface.json").read_text(encoding="utf-8"))
        cls.by_product: dict[str, dict[str, dict]] = {}
        for entry in cls.contract["operations"]:
            cls.by_product.setdefault(entry["product"], {})[entry["id"]] = entry

    def test_voice_publishes_only_the_phone_allowlist_plus_the_stream(self) -> None:
        self.assertEqual(
            set(self.by_product["temperaVoice"]),
            VOICE_OPERATIONS | {"streamVoiceSession"},
        )

    def test_existing_products_still_publish_every_surface_operation(self) -> None:
        for product in ("temperaDropshipping", "temperaBusiness"):
            expected = {op["id"] for op in self.surface["operations"][product]}
            self.assertEqual(set(self.by_product[product]), expected, product)

    def test_stream_operation_comes_from_the_websocket_contract(self) -> None:
        voice_spec = json.loads(
            (ROOT / "specs" / "tempera-voice-api.json").read_text(encoding="utf-8")
        )
        websocket = voice_spec["x-tempera-websocket-contract"]
        stream = self.by_product["temperaVoice"]["streamVoiceSession"]
        self.assertEqual(stream["method"], "WSS")
        self.assertEqual(stream["pathTemplate"], "/v1/sessions/{sessionId}/stream")
        self.assertEqual(stream["pathShape"], "/v1/sessions/{}/stream")
        self.assertEqual(stream["authAudience"], "tempera-voice")
        self.assertEqual(stream["scope"], "voice:stream")
        self.assertEqual(stream["safeRetry"], "none")
        self.assertEqual(stream["requestDigest"], module.digest(websocket))
        self.assertEqual(stream["responseDigest"], module.digest(websocket))

    def test_voice_operations_carry_the_producer_audience_and_scopes(self) -> None:
        for name, entry in self.by_product["temperaVoice"].items():
            self.assertEqual(entry["authAudience"], "tempera-voice", name)
            self.assertIn(entry["scope"], {"voice:read", "voice:write", "voice:stream"}, name)

    def test_producers_are_mainline_locks(self) -> None:
        for producer in self.contract["producers"]:
            self.assertEqual(producer["sourceBranch"], "main", producer["product"])
        self.assertNotIn("unmerged", self.contract["$comment"])


class ClientCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = module.build_contract()

    def check(self, name: str, source: str) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / name
            path.write_text(textwrap.dedent(source), encoding="utf-8")
            return module.check_client(path, self.contract)

    def test_annotated_wss_call_site_passes_the_literal_shape_rule(self) -> None:
        swift = '''
            // tempera-transport: temperaVoice.streamVoiceSession WSS /v1/sessions/{sessionId}/stream
            var request = try self.request("v1/sessions/\\(sessionID)/stream")
        '''
        kotlin = '''
            // tempera-transport: temperaVoice.streamVoiceSession WSS /v1/sessions/{sessionId}/stream
            val url = base.resolvePath("v1/sessions/$sessionId/stream").newBuilder().build()
        '''
        self.assertEqual(self.check("VoiceClient.swift", swift), [])
        self.assertEqual(self.check("VoiceClient.kt", kotlin), [])

    def test_wss_annotation_with_the_wrong_literal_shape_fails(self) -> None:
        source = '''
            // tempera-transport: temperaVoice.streamVoiceSession WSS /v1/sessions/{sessionId}/stream
            var request = try self.request("v1/sessions/\\(sessionID)/events")
        '''
        failures = self.check("VoiceClient.swift", source)
        self.assertEqual(len(failures), 1)
        self.assertIn("call site path", failures[0])

    def test_http_annotation_declaring_the_stream_as_get_fails(self) -> None:
        source = '''
            // tempera-transport: temperaVoice.streamVoiceSession GET /v1/sessions/{sessionId}/stream
            var request = try self.request("v1/sessions/\\(sessionID)/stream")
        '''
        failures = self.check("VoiceClient.swift", source)
        self.assertEqual(len(failures), 1)
        self.assertIn("declares GET, contract says WSS", failures[0])

    def test_unannotated_voice_and_business_routes_are_undeclared(self) -> None:
        source = '''
            let a = try request("v1/sessions", method: "POST", body: body)
            let b = try request("v1/agents:default")
            let c = try request("v1/actions/\\(action.id):resolve", method: "POST")
            let d: OperatingState = try await send("/v1/operatingState")
            let e = try await send("/v1/businessProfile")
            let f = try await send("/v1/cases/\\(reviewed.id):reviewDraft", method: "POST")
            let g = try await send("/v1/organizations/\\(org)/inbox")
            let unrelated = try request("v1/capabilities")
            let lookalike = try request("v1/sessionsarchive")
        '''
        failures = self.check("Mixed.swift", source)
        self.assertEqual(
            failures,
            [
                "Mixed.swift:2: undeclared temperaVoice route /v1/sessions; add a tempera-transport annotation above the call site",
                "Mixed.swift:3: undeclared temperaVoice route /v1/agents:default; add a tempera-transport annotation above the call site",
                "Mixed.swift:4: undeclared temperaVoice route /v1/actions/{}:resolve; add a tempera-transport annotation above the call site",
                "Mixed.swift:5: undeclared temperaBusiness route /v1/operatingState; add a tempera-transport annotation above the call site",
                "Mixed.swift:6: undeclared temperaBusiness route /v1/businessProfile; add a tempera-transport annotation above the call site",
                "Mixed.swift:7: undeclared temperaBusiness route /v1/cases/{}:reviewDraft; add a tempera-transport annotation above the call site",
                "Mixed.swift:8: undeclared temperaDropshipping route /v1/organizations/{}/inbox; add a tempera-transport annotation above the call site",
            ],
        )

    def test_annotated_http_voice_call_sites_pass(self) -> None:
        source = '''
            // tempera-transport: temperaVoice.getDefaultVoiceAgent GET /v1/agents:default
            let data = try await BoundedHTTP.data(for: try request("v1/agents:default"), limit: 65_536)
            // tempera-transport: temperaVoice.resolveVoiceAction POST /v1/actions/{actionId}:resolve
            let out = try await BoundedHTTP.data(for: try request("v1/actions/\\(action.id):resolve", method: "POST", body: body), limit: 65_536)
        '''
        self.assertEqual(self.check("VoiceActions.swift", source), [])

    def test_operations_outside_the_voice_allowlist_are_not_admitted(self) -> None:
        source = '''
            // tempera-transport: temperaVoice.exportVoiceSessions POST /v1/sessions:export
            let data = try request("v1/sessions:export", method: "POST")
        '''
        failures = self.check("VoiceClient.swift", source)
        # A rejected annotation does not vouch for its call line, so the
        # literal underneath is also reported as an undeclared voice route.
        self.assertEqual(
            failures,
            [
                "VoiceClient.swift:2: temperaVoice.exportVoiceSessions is not an admitted native operation",
                "VoiceClient.swift:3: undeclared temperaVoice route /v1/sessions:export; add a tempera-transport annotation above the call site",
            ],
        )


if __name__ == "__main__":
    unittest.main()
