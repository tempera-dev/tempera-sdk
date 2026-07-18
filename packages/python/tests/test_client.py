import json
import re
import unittest
from urllib import parse as urllib_parse

from tempera_sdk import (
    OPERATIONS,
    PRODUCTS,
    TemperaApiError,
    TemperaAuth,
    TemperaClient,
    TemperaSdkError,
    TokenSet,
    api_error_from_response,
    normalize_error_body,
)

PRODUCT_ATTRS = {
    "controlPlane": "control_plane",
    "palette": "palette",
    "tempo": "tempo",
    "temperaCode": "tempera_code",
    "cradle": "cradle",
    "remi": "remi",
    "dataEngine": "data_engine",
    "humanData": "human_data",
    "tempJs": "temp_js",
    "tempOS": "temp_os",
    "arrha": "arrha",
}

SAMPLE_PARAM_VALUE = "sample-value"


class FakeTransport:
    """Records (method, url, headers, data) and returns the responder's value."""

    def __init__(self, responder=None):
        self.responder = responder or (lambda call: {"ok": True})
        self.calls = []

    def __call__(self, method, url, headers, data):
        split = urllib_parse.urlsplit(url)
        call = {
            "method": method,
            "url": url,
            "path": split.path,
            "origin": f"{split.scheme}://{split.netloc}",
            "query": dict(urllib_parse.parse_qsl(split.query)),
            "headers": headers,
            "data": data,
            "body": json.loads(data) if data else None,
        }
        self.calls.append(call)
        return self.responder(call)


def make_client(**overrides):
    transport = overrides.pop("transport", FakeTransport())
    kwargs = dict(
        auth=TemperaAuth(issuer_url="https://api.tempera.dev", api_key="tp_key_1"),
        account_token="account_token_1",
        introspection_secret="introspect_secret_1",
        base_urls={
            # snake_case attribute names and camelCase registry keys both work.
            "control_plane": "https://cp.example.test",
            "palette": "https://palette.example.test",
            "tempo": "https://tempo.example.test",
            "tempera_code": "https://code.example.test",
            "cradle": "https://cradle.example.test",
            "remi": "https://remi.example.test",
            "data_engine": "https://data-engine.example.test",
            "human_data": "https://human.example.test",
            "tempJs": "https://tempjs.example.test",
            "temp_os": "https://tempos.example.test",
            "arrha": "https://arrha.example.test",
        },
        transport=transport,
    )
    kwargs.update(overrides)
    return TemperaClient(**kwargs), transport


class ConformanceTest(unittest.TestCase):
    def test_every_surface_operation_dispatches_method_path_and_auth_header(self):
        client, transport = make_client()
        for product_key, ops in OPERATIONS.items():
            product = getattr(client, PRODUCT_ATTRS[product_key])
            for op in ops:
                label = f"{product_key}.{op['id']}"
                transport.calls.clear()
                params = {key: SAMPLE_PARAM_VALUE for key in op["path_params"]}
                result = getattr(product, op["id"])(params)
                self.assertEqual(result, {"ok": True}, f"{label} result")
                self.assertEqual(len(transport.calls), 1, f"{label} made one request")
                call = transport.calls[0]
                self.assertEqual(call["method"], op["method"], f"{label} method")
                expected_path = re.sub(r"\{[a-z_]+\}", SAMPLE_PARAM_VALUE, op["path"])
                self.assertEqual(call["path"], expected_path, f"{label} path")
                auth_header = call["headers"].get("authorization")
                if op["auth"] == "none":
                    self.assertIsNone(auth_header, f"{label} sends no bearer")
                elif op["auth"] == "account":
                    self.assertEqual(auth_header, "Bearer account_token_1", f"{label} account bearer")
                elif op["auth"] == "introspectionSecret":
                    self.assertEqual(auth_header, "Bearer introspect_secret_1", f"{label} introspection bearer")
                else:
                    self.assertEqual(auth_header, "Bearer tp_key_1", f"{label} product bearer")
                # Body defaults (e.g. login/signup mode) must reach the wire.
                for key, value in op["body_defaults"].items():
                    self.assertEqual(call["body"][key], value, f"{label} body default {key}")


class DispatchTest(unittest.TestCase):
    def test_declared_query_and_body_parameters_route_to_the_right_place(self):
        client, transport = make_client()
        client.palette.list_traces({"tenant_id": "t1", "limit": 5, "cursor": "abc"})
        self.assertEqual(transport.calls[0]["path"], "/v1/traces/t1")
        self.assertEqual(transport.calls[0]["query"]["limit"], "5")
        self.assertEqual(transport.calls[0]["query"]["cursor"], "abc")
        self.assertIsNone(transport.calls[0]["data"])

        client.remi.remember({"kind": "fact", "text": "hello"})
        self.assertEqual(
            transport.calls[1]["body"],
            {"kind": "fact", "text": "hello"},
        )
        with self.assertRaisesRegex(TemperaSdkError, "derived from the authenticated principal"):
            client.remi.remember({"tenant_id": "t1", "kind": "fact", "text": "nope"})

    def test_undeclared_parameters_pass_through_for_forward_compatibility(self):
        client, transport = make_client()
        client.tempo.list_sessions({"future_filter": "x"})
        self.assertEqual(transport.calls[0]["query"]["future_filter"], "x")
        client.cradle.execute({"lane": "wasm", "source": "s", "future_field": 7})
        self.assertEqual(transport.calls[1]["body"]["future_field"], 7)

    def test_action_suffix_paths_keep_the_literal_colon_unencoded(self):
        client, transport = make_client()
        client.data_engine.ingest_artifact({"project_id": "p1", "envelopes": []})
        self.assertEqual(transport.calls[0]["path"], "/v1/projects/p1/artifacts:ingest")
        self.assertNotIn("%3A", transport.calls[0]["url"], "colon must not be percent-encoded")
        # Colons inside a substituted path *value* are still encoded.
        client.data_engine.get_job({"project_id": "p1", "job_id": "job:1"})
        self.assertEqual(transport.calls[1]["path"], "/v1/projects/p1/jobs/job%3A1")

    def test_missing_path_parameters_fail_fast_with_a_clear_message(self):
        client, _ = make_client()
        with self.assertRaises(TemperaSdkError) as ctx:
            client.palette.get_trace({"tenant_id": "t1"})
        self.assertIn('missing required path parameter "trace_id"', str(ctx.exception))

    def test_login_and_signup_store_the_account_token_for_later_calls(self):
        def responder(call):
            if len(transport.calls) == 1:
                return {"access_token": "account_at_1", "token_type": "Bearer"}
            return {"sub": "user_1"}

        transport = FakeTransport(responder)
        client = TemperaClient(base_urls={"control_plane": "https://cp.example.test"}, transport=transport)
        client.control_plane.login({"email": "demo@tempera.dev", "password": "tempera-demo"})
        self.assertEqual(transport.calls[0]["body"]["mode"], "login")
        self.assertEqual(client.account_token, "account_at_1")
        client.control_plane.me()
        self.assertEqual(transport.calls[1]["headers"]["authorization"], "Bearer account_at_1")

    def test_account_operations_without_a_token_fail_with_guidance(self):
        client = TemperaClient(base_urls={"control_plane": "https://cp.example.test"}, transport=FakeTransport())
        with self.assertRaises(TemperaSdkError) as ctx:
            client.control_plane.me()
        self.assertIn("login()/signup()", str(ctx.exception))

    def test_product_operations_without_credentials_fail_with_guidance(self):
        client = TemperaClient(base_urls={"palette": "https://palette.example.test"}, transport=FakeTransport())
        with self.assertRaises(TemperaSdkError) as ctx:
            client.palette.list_traces({"tenant_id": "t1"})
        self.assertIn("TemperaAuth", str(ctx.exception))

    def test_audience_matched_bearers_win_over_the_api_key_fallback(self):
        client, transport = make_client(
            auth=TemperaAuth(
                issuer_url="https://api.tempera.dev",
                api_key="tp_key_1",
                tokens={"tempo": TokenSet(access_token="at_tempo"), "remi": TokenSet(access_token="at_remi")},
            ),
        )
        client.tempo.list_sessions()
        client.remi.get_stats()
        client.cradle.get_capabilities()
        self.assertEqual(transport.calls[0]["headers"]["authorization"], "Bearer at_tempo")
        self.assertEqual(transport.calls[1]["headers"]["authorization"], "Bearer at_remi")
        self.assertEqual(transport.calls[2]["headers"]["authorization"], "Bearer tp_key_1")

    def test_passthrough_request_covers_products_without_typed_operations(self):
        client, transport = make_client()
        result = client.temp_js.request("/runtime/status")
        self.assertEqual(result, {"ok": True})
        self.assertEqual(transport.calls[0]["url"], "https://tempjs.example.test/runtime/status")

    def test_environment_presets_resolve_control_plane_palette_and_tempera_code(self):
        transport = FakeTransport()
        client = TemperaClient(environment="production", transport=transport)
        client.control_plane.health()
        client.palette.health()
        client.tempera_code.health()
        self.assertEqual(transport.calls[0]["origin"], "https://api.tempera.dev")
        self.assertEqual(transport.calls[1]["origin"], "https://mcp.tempera.dev")
        self.assertEqual(transport.calls[2]["origin"], "https://code-api.tempera.dev")

    def test_unknown_environment_is_rejected(self):
        with self.assertRaises(TemperaSdkError):
            TemperaClient(environment="galactic")


class ErrorNormalizationTest(unittest.TestCase):
    def test_http_errors_normalize_every_fleet_wire_shape(self):
        shapes = [
            # control plane / palette: flat code + message
            {
                "body": {"error": "missing_scope", "message": "Scope is required."},
                "code": "missing_scope",
                "message": "Scope is required.",
            },
            # tempo: flat human message only
            {"body": {"error": "session not found"}, "code": None, "message": "session not found"},
            # remi: nested code + message
            {
                "body": {"error": {"code": "rate_limited", "message": "Too many requests."}},
                "code": "rate_limited",
                "message": "Too many requests.",
            },
            # cradle: nested rich shape with request id
            {
                "body": {"error": {"code": "invalid_json", "message": "Bad body.", "request_id": "req-123", "retryable": False}},
                "code": "invalid_json",
                "message": "Bad body.",
                "request_id": "req-123",
            },
            # data-engine: same nested rich shape, uppercase codes + details array
            {
                "body": {
                    "error": {
                        "code": "INVALID_ARGUMENT",
                        "message": "Bad envelope.",
                        "status": 400,
                        "request_id": "req-de-1",
                        "retryable": False,
                        "details": [],
                    }
                },
                "code": "INVALID_ARGUMENT",
                "message": "Bad envelope.",
                "request_id": "req-de-1",
            },
        ]
        for shape in shapes:
            def transport(method, url, headers, data, _body=shape["body"]):
                raise api_error_from_response(403, "Forbidden", {}, _body)

            client = TemperaClient(
                account_token="t",
                base_urls={"control_plane": "https://cp.example.test"},
                transport=transport,
            )
            with self.assertRaises(TemperaApiError) as ctx:
                client.control_plane.me()
            error = ctx.exception
            self.assertEqual(error.status, 403)
            self.assertEqual(error.code, shape["code"])
            self.assertIn(shape["message"], str(error))
            if shape.get("request_id"):
                self.assertEqual(error.request_id, shape["request_id"])
            self.assertEqual(error.product, "controlPlane")
            self.assertEqual(error.operation, "me")
            self.assertEqual(error.body, shape["body"])

    def test_request_id_falls_back_to_the_x_request_id_response_header(self):
        def transport(method, url, headers, data):
            raise api_error_from_response(
                401, "", {"x-request-id": "req_hdr_1"}, {"error": "unauthenticated", "message": "No."}
            )

        client = TemperaClient(
            account_token="t",
            base_urls={"control_plane": "https://cp.example.test"},
            transport=transport,
        )
        with self.assertRaises(TemperaApiError) as ctx:
            client.control_plane.me()
        self.assertEqual(ctx.exception.request_id, "req_hdr_1")
        self.assertEqual(ctx.exception.status, 401)

    def test_normalize_error_body_handles_unknown_and_empty_bodies(self):
        self.assertEqual(
            normalize_error_body(None, "Bad Gateway"),
            {"code": None, "message": "Bad Gateway", "request_id": None},
        )
        self.assertEqual(
            normalize_error_body("nonsense", "Oops"),
            {"code": None, "message": "Oops", "request_id": None},
        )


class ProductMetadataTest(unittest.TestCase):
    def test_every_product_client_carries_its_registry_metadata(self):
        client, _ = make_client()
        for key, product in PRODUCTS.items():
            product_client = getattr(client, PRODUCT_ATTRS[key])
            self.assertEqual(product_client.name, product["name"], f"{key} name")
            self.assertEqual(product_client.env_var, product["env_var"], f"{key} env_var")
            self.assertEqual(product_client.audience, product["audience"], f"{key} audience")
            self.assertTrue(product_client.description.endswith("."), f"{key} description")
            self.assertTrue(callable(product_client.request), f"{key} passthrough")

    def test_operation_methods_carry_the_surface_description_as_docstring(self):
        client, _ = make_client()
        self.assertEqual(
            client.palette.get_trace.__doc__,
            "Fetch one full trace with all canonical spans; unmasking PII requires the pii:unmask scope and a reason.",
        )


if __name__ == "__main__":
    unittest.main()
