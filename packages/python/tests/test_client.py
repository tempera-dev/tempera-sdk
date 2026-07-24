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
    "temperaLlm": "tempera_llm",
    "temperaWorkflows": "tempera_workflows",
    "temperaGym": "tempera_gym",
    "temperaBio": "tempera_bio",
    "cradle": "cradle",
    "remi": "remi",
    "dataEngine": "data_engine",
    "humanData": "human_data",
    "tempJs": "temp_js",
    "tempOS": "temp_os",
    "arrha": "arrha",
}

SAMPLE_PARAM_VALUE = "sample-value"


def sample_path_param(op, key):
    template = op["path_param_templates"].get(key)
    return template.replace("*", SAMPLE_PARAM_VALUE) if template else SAMPLE_PARAM_VALUE


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
            "tempera_llm": "https://llm.example.test",
            "tempera_workflows": "https://workflows.example.test",
            "tempera_gym": "https://gym.example.test",
            "tempera_bio": "https://bio.example.test",
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
                params = {
                    key: sample_path_param(op, key)
                    for key in op["path_params"]
                }
                result = getattr(product, op["id"])(params)
                self.assertEqual(result, {"ok": True}, f"{label} result")
                self.assertEqual(len(transport.calls), 1, f"{label} made one request")
                call = transport.calls[0]
                self.assertEqual(call["method"], op["method"], f"{label} method")
                expected_path = re.sub(
                    r"\{([A-Za-z_][A-Za-z0-9_]*)\}",
                    lambda match: sample_path_param(op, match.group(1)),
                    op["path"],
                )
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
                # Declared body defaults must reach the wire.
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

        client.palette.scenarios_list(
            {
                "tenant_id": "t1",
                "project_id": "p1",
                "pageSize": 12,
                "pageToken": "scenarios-token",
            }
        )
        self.assertEqual(transport.calls[-1]["path"], "/v1/scenarios/t1/p1")
        query = transport.calls[-1]["query"]
        self.assertEqual(query["pageSize"], "12")
        self.assertEqual(query["pageToken"], "scenarios-token")
        self.assertNotIn("limit", query)
        self.assertNotIn("cursor", query)

        pagination_calls = (
            (
                client.data_engine.list_use_cases,
                {
                    "parent": "projects/p1",
                    "pageSize": 2,
                    "pageToken": "use-cases-token",
                },
            ),
            (
                client.data_engine.get_job_results,
                {
                    "parent": "projects/p1",
                    "jobId": "job-1",
                    "pageSize": 3,
                    "pageToken": "results-token",
                },
            ),
            (
                client.data_engine.list_tools,
                {
                    "parent": "projects/p1",
                    "pageSize": 4,
                    "pageToken": "tools-token",
                },
            ),
        )
        for operation, params in pagination_calls:
            operation(params)
            query = transport.calls[-1]["query"]
            self.assertEqual(query["pageSize"], str(params["pageSize"]))
            self.assertEqual(query["pageToken"], params["pageToken"])
            self.assertNotIn("page_size", query)
            self.assertNotIn("page_token", query)
        client.remi.list_audit({"pageSize": 5, "pageToken": "audit-token"})
        query = transport.calls[-1]["query"]
        self.assertEqual(query["pageSize"], "5")
        self.assertEqual(query["pageToken"], "audit-token")
        self.assertNotIn("limit", query)

        client.tempera_llm.list_models(
            {"pageSize": 6, "pageToken": "models-token"}
        )
        query = transport.calls[-1]["query"]
        self.assertEqual(query["pageSize"], "6")
        self.assertEqual(query["pageToken"], "models-token")
        self.assertNotIn("limit", query)

        client.tempera_gym.list_environments(
            {"pageSize": 7, "pageToken": "environments-token"}
        )
        query = transport.calls[-1]["query"]
        self.assertEqual(query["pageSize"], "7")
        self.assertEqual(query["pageToken"], "environments-token")
        self.assertNotIn("limit", query)
        client.tempera_gym.list_runs(
            {
                "environmentId": "env-1",
                "pageSize": 8,
                "pageToken": "runs-token",
            }
        )
        query = transport.calls[-1]["query"]
        self.assertEqual(query["environmentId"], "env-1")
        self.assertEqual(query["pageSize"], "8")
        self.assertEqual(query["pageToken"], "runs-token")
        self.assertNotIn("environment_id", query)
        client.tempera_gym.create_rollout(
            {"environmentId": "env-1", "seed": 42}
        )
        self.assertEqual(
            transport.calls[-1]["body"],
            {"environmentId": "env-1", "seed": 42},
        )

        client.tempera_bio.verify_measurement(
            {
                "raw_measurement_base64": "Zml4dHVyZQ==",
                "identity_signature": "sig-1",
            }
        )
        self.assertEqual(
            transport.calls[-1]["body"],
            {
                "rawMeasurementBase64": "Zml4dHVyZQ==",
                "identitySignature": "sig-1",
            },
        )
        self.assertEqual(transport.calls[-1]["path"], "/v1/measurements:verify")

        client.human_data.compute_qualification(
            {
                "product_id": "product-1",
                "release_id": "release-1",
            }
        )
        self.assertEqual(
            transport.calls[-1]["path"], "/v1/qualifications:compute"
        )
        self.assertEqual(
            transport.calls[-1]["query"],
            {
                "productId": "product-1",
                "releaseId": "release-1",
            },
        )

        workflow_list_calls = (
            (
                client.tempera_workflows.list_node_types,
                {"pageSize": 9, "pageToken": "node-types-token"},
            ),
            (
                client.tempera_workflows.list_workflows,
                {"pageSize": 10, "pageToken": "workflows-token"},
            ),
            (
                client.tempera_workflows.list_runs,
                {
                    "workflowId": "workflow-1",
                    "pageSize": 11,
                    "pageToken": "workflow-runs-token",
                },
            ),
        )
        for operation, params in workflow_list_calls:
            operation(params)
            query = transport.calls[-1]["query"]
            self.assertEqual(query["pageSize"], str(params["pageSize"]))
            self.assertEqual(query["pageToken"], params["pageToken"])
            self.assertNotIn("limit", query)
            self.assertNotIn("cursor", query)
        self.assertEqual(transport.calls[-1]["query"]["workflowId"], "workflow-1")
        client.tempera_workflows.update_workflow(
            {
                "workflowId": "workflow-1",
                "updateMask": "definition",
                "contractVersion": "v1",
                "id": "workflow-1",
                "name": "Smoke",
                "nodes": [],
                "edges": [],
            }
        )
        self.assertEqual(transport.calls[-1]["method"], "PATCH")
        self.assertEqual(
            transport.calls[-1]["query"]["updateMask"], "definition"
        )

        custom_verb_calls = (
            (
                client.data_engine.run_use_case,
                {"parent": "projects/p1", "use_case": "smoke"},
                "/v1/projects/p1/pipelines:runUseCase",
            ),
            (
                client.data_engine.save_expert_task_draft,
                {
                    "parent": "projects/p1",
                    "expertTaskId": "task-1",
                    "idempotency_key": "idem-1",
                    "lease_token": "lease-1",
                    "draft": {},
                    "expected_version": 1,
                },
                "/v1/projects/p1/expert-tasks/task-1:saveDraft",
            ),
            (
                client.data_engine.check_product_leakage,
                {
                    "parent": "projects/p1",
                    "product_ids": ["products/a", "products/b"],
                },
                "/v1/projects/p1/products:checkLeakage",
            ),
            (
                client.data_engine.emit_eval,
                {
                    "parent": "projects/p1",
                    "artifact_ids": ["artifacts/a"],
                    "job": {},
                },
                "/v1/projects/p1/products:emitEval",
            ),
        )
        for operation, params, expected_path in custom_verb_calls:
            operation(params)
            self.assertEqual(transport.calls[-1]["path"], expected_path)

        client.remi.remember(
            {
                "tenant_id": "t1",
                "project_id": "p1",
                "kind": "fact",
                "text": "hello",
            }
        )
        self.assertEqual(
            transport.calls[-1]["body"],
            {
                "tenantId": "t1",
                "projectId": "p1",
                "kind": "fact",
                "text": "hello",
            },
        )
        query = {
            "question": "Which workflow evidence is current?",
            "scope": {
                "tenant_id": "t1",
                "project_id": "p1",
                "environment_id": "dev",
                "as_of_unix_ms": None,
            },
            "max_tokens": 600,
            "require_fresh": True,
            "modes": ["procedural", "gotcha", "state"],
            "reconstruction_mode": "off",
        }
        client.remi.query(query)
        self.assertEqual(
            transport.calls[-1]["body"],
            {
                "question": query["question"],
                "scope": query["scope"],
                "maxTokens": 600,
                "requireFresh": True,
                "modes": query["modes"],
                "reconstructionMode": "off",
            },
        )

    def test_snake_case_parameter_aliases_emit_only_lower_camel_wire_names(self):
        client, transport = make_client()
        client.tempera_gym.list_runs(
            {
                "environment_id": "env-1",
                "page_size": 8,
                "page_token": "runs-token",
            }
        )
        query = transport.calls[-1]["query"]
        self.assertEqual(query["environmentId"], "env-1")
        self.assertEqual(query["pageSize"], "8")
        self.assertEqual(query["pageToken"], "runs-token")
        self.assertNotIn("environment_id", query)
        self.assertNotIn("page_size", query)
        self.assertNotIn("page_token", query)

        client.tempera_gym.create_rollout({"environment_id": "env-1", "seed": 42})
        self.assertEqual(
            transport.calls[-1]["body"],
            {"environmentId": "env-1", "seed": 42},
        )

    def test_canonical_and_snake_case_spellings_cannot_both_be_supplied(self):
        client, _ = make_client()
        with self.assertRaisesRegex(
            TemperaSdkError,
            r"pass either 'pageSize' or its snake_case alias 'page_size', not both",
        ):
            client.tempera_gym.list_runs({"pageSize": 8, "page_size": 9})

    def test_json_request_bodies_use_the_compact_wire_shape(self):
        client, transport = make_client()
        client.cradle.execute({"lane": "wasm", "source": {"kind": "wasm_wat", "text": "fixture-雪-🙂"}})
        self.assertEqual(
            transport.calls[0]["data"],
            '{"lane":"wasm","source":{"kind":"wasm_wat","text":"fixture-雪-🙂"}}'.encode(),
        )

    def test_json_request_bodies_preserve_unpaired_surrogates_as_escapes(self):
        client, transport = make_client()
        client.cradle.execute({"text": f"{chr(0xD800)}{chr(0xDC00)}"})
        self.assertEqual(transport.calls[0]["data"], b'{"text":"\\ud800\\udc00"}')

    def test_undeclared_parameters_pass_through_for_forward_compatibility(self):
        client, transport = make_client()
        client.tempo.list_sessions({"future_filter": "x"})
        self.assertEqual(transport.calls[0]["query"]["future_filter"], "x")
        client.cradle.execute({"lane": "wasm", "source": "s", "future_field": 7})
        self.assertEqual(transport.calls[1]["body"]["future_field"], 7)

    def test_action_suffix_paths_keep_the_literal_colon_unencoded(self):
        client, transport = make_client()
        client.data_engine.ingest_artifact({"parent": "projects/p1", "envelopes": []})
        self.assertEqual(transport.calls[0]["path"], "/v1/projects/p1/artifacts:ingest")
        self.assertNotIn("%3A", transport.calls[0]["url"], "colon must not be percent-encoded")
        client.tempera_workflows.runs_signal(
            {
                "runId": "run/1",
                "signalName": "provider.completed",
                "idempotencyKey": "callback-1",
                "payload": {"resultRef": "sha256:abc"},
                "payloadDigest": "sha256:def",
            }
        )
        self.assertEqual(transport.calls[1]["path"], "/v1/runs/run%2F1:signal")
        self.assertNotIn(
            "%3A", transport.calls[1]["url"], "action colon must remain literal"
        )
        self.assertEqual(
            transport.calls[1]["body"],
            {
                "idempotencyKey": "callback-1",
                "payload": {"resultRef": "sha256:abc"},
                "payloadDigest": "sha256:def",
                "signalName": "provider.completed",
            },
        )
        # Colons inside a substituted path *value* are still encoded.
        client.data_engine.get_job({"parent": "projects/p1", "jobId": "job:1"})
        self.assertEqual(transport.calls[2]["path"], "/v1/projects/p1/jobs/job%3A1")
        with self.assertRaisesRegex(
            TemperaSdkError, r'must match AIP resource pattern "projects/\*"'
        ):
            client.data_engine.ingest_artifact({"parent": "projects/../secrets"})
        with self.assertRaisesRegex(
            TemperaSdkError, r'must match AIP resource pattern "projects/\*"'
        ):
            client.data_engine.ingest_artifact({"parent": "organizations/p1"})

    def test_missing_path_parameters_fail_fast_with_a_clear_message(self):
        client, _ = make_client()
        with self.assertRaises(TemperaSdkError) as ctx:
            client.palette.get_trace({"tenant_id": "t1"})
        self.assertIn('missing required path parameter "traceId"', str(ctx.exception))

    def test_create_hosted_session_stores_the_account_token_for_later_calls(self):
        def responder(call):
            if len(transport.calls) == 1:
                return {"access_token": "account_at_1", "token_type": "Bearer"}
            return {"sub": "user_1"}

        transport = FakeTransport(responder)
        client = TemperaClient(base_urls={"control_plane": "https://cp.example.test"}, transport=transport)
        client.control_plane.create_hosted_session(
            {"mode": "login", "email": "demo@tempera.dev", "password": "tempera-demo"}
        )
        self.assertEqual(transport.calls[0]["body"]["mode"], "login")
        self.assertEqual(client.account_token, "account_at_1")
        client.control_plane.me()
        self.assertEqual(transport.calls[1]["headers"]["authorization"], "Bearer account_at_1")

    def test_account_operations_without_a_token_fail_with_guidance(self):
        client = TemperaClient(base_urls={"control_plane": "https://cp.example.test"}, transport=FakeTransport())
        with self.assertRaises(TemperaSdkError) as ctx:
            client.control_plane.me()
        self.assertIn("create_hosted_session()", str(ctx.exception))

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

    def test_control_plane_discovery_operations_use_producer_pinned_audiences(self):
        client, transport = make_client(
            auth=TemperaAuth(
                issuer_url="https://api.tempera.dev",
                api_key="tp_key_1",
                tokens={
                    "tempera-bio": TokenSet(access_token="at_bio_human"),
                    "tempera-workflows": TokenSet(
                        access_token="at_workflows_service"
                    ),
                },
            ),
        )
        client.control_plane.list_bio_signer_keys()
        client.control_plane.resolve_experiment_provider_connection(
            {"id": "connection-1"}
        )
        self.assertEqual(
            transport.calls[0]["headers"]["authorization"],
            "Bearer at_bio_human",
        )
        self.assertEqual(
            transport.calls[1]["headers"]["authorization"],
            "Bearer at_workflows_service",
        )

    def test_passthrough_request_covers_products_without_typed_operations(self):
        client, transport = make_client()
        result = client.temp_js.request("/runtime/status")
        self.assertEqual(result, {"ok": True})
        self.assertEqual(transport.calls[0]["url"], "https://tempjs.example.test/runtime/status")

    def test_environment_presets_resolve_control_plane_palette_and_gateways(self):
        transport = FakeTransport()
        client = TemperaClient(environment="production", transport=transport)
        client.control_plane.health()
        client.palette.health()
        client.tempera_llm.health()
        client.tempera_workflows.health()
        client.tempera_gym.health()
        self.assertEqual(transport.calls[0]["origin"], "https://api.tempera.dev")
        self.assertEqual(transport.calls[1]["origin"], "https://mcp.tempera.dev")
        self.assertEqual(transport.calls[2]["origin"], "https://llm.tempera.dev")
        self.assertEqual(transport.calls[3]["origin"], "https://workflows.tempera.dev")
        self.assertEqual(transport.calls[4]["origin"], "https://gym.tempera.dev")

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
            # canonical google.rpc.Status REST mapping
            {
                "body": {
                    "error": {
                        "code": 400,
                        "status": "INVALID_ARGUMENT",
                        "message": "Bad envelope.",
                        "requestId": "req-de-1",
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
