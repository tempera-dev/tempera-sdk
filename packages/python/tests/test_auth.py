import unittest
from urllib import parse as urllib_parse

from tempera_sdk import (
    AUDIENCES,
    DEFAULT_AUDIENCE,
    ISSUER_PATHS,
    PRODUCT_AUDIENCES,
    TemperaApiError,
    TemperaAuth,
    TemperaSdkError,
    TokenSet,
    api_error_from_response,
    build_authorize_url,
    create_pkce_pair,
    generate_pkce_verifier,
    pkce_challenge_s256,
)


class PkceTest(unittest.TestCase):
    def test_challenge_is_unpadded_base64url_sha256_of_verifier(self):
        # RFC 7636 appendix B reference vector.
        challenge = pkce_challenge_s256("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk")
        self.assertEqual(challenge, "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM")
        self.assertNotIn("=", challenge)

    def test_generated_pair_is_consistent(self):
        pair = create_pkce_pair()
        self.assertRegex(pair.verifier, r"^[A-Za-z0-9_-]{43,128}$")
        self.assertEqual(pair.challenge, pkce_challenge_s256(pair.verifier))
        self.assertEqual(pair.method, "S256")
        self.assertNotEqual(generate_pkce_verifier(), generate_pkce_verifier())


class AuthorizeUrlTest(unittest.TestCase):
    def test_carries_resource_audience_and_s256_challenge(self):
        url = build_authorize_url(
            issuer_url="https://api.tempera.dev/",
            client_id="client_1",
            redirect_uri="https://app.example.test/callback",
            code_challenge="challenge_1",
            audience="tempo",
            scope=["trace:read", "trace:write"],
            state="state_1",
        )
        parsed = urllib_parse.urlparse(url)
        params = dict(urllib_parse.parse_qsl(parsed.query))
        self.assertEqual(parsed.path, ISSUER_PATHS["authorize"])
        self.assertEqual(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", "https://api.tempera.dev/oauth/authorize")
        self.assertEqual(params["response_type"], "code")
        self.assertEqual(params["resource"], "tempo")
        self.assertEqual(params["code_challenge"], "challenge_1")
        self.assertEqual(params["code_challenge_method"], "S256")
        self.assertEqual(params["scope"], "trace:read trace:write")
        self.assertEqual(params["state"], "state_1")
        self.assertIn(DEFAULT_AUDIENCE, AUDIENCES)


class FakeTransport:
    def __init__(self, responder):
        self.responder = responder
        self.calls = []

    def __call__(self, method, url, headers, data):
        params = dict(urllib_parse.parse_qsl(data.decode("ascii"))) if data else {}
        self.calls.append({"method": method, "url": url, "headers": headers, "params": params})
        return self.responder(url, params)


class TokenFlowTest(unittest.TestCase):
    def test_exchange_and_refresh_propagate_resource_and_rotate(self):
        refresh_count = 0

        def responder(url, params):
            nonlocal refresh_count
            if params.get("grant_type") == "authorization_code":
                return {"access_token": "at_1", "refresh_token": "rt_1", "token_type": "Bearer"}
            refresh_count += 1
            return {
                "access_token": f"at_{refresh_count + 1}",
                "refresh_token": f"rt_{refresh_count + 1}",
                "token_type": "Bearer",
            }

        transport = FakeTransport(responder)
        auth = TemperaAuth(issuer_url="https://api.tempera.dev", client_id="client_1", transport=transport)

        auth.exchange_code(
            code="code_1",
            code_verifier="verifier_1",
            redirect_uri="https://app.example.test/callback",
            audience="tempo",
        )
        self.assertEqual(transport.calls[0]["url"], "https://api.tempera.dev/oauth/token")
        self.assertEqual(transport.calls[0]["params"]["grant_type"], "authorization_code")
        self.assertEqual(transport.calls[0]["params"]["resource"], "tempo")
        self.assertEqual(transport.calls[0]["params"]["code_verifier"], "verifier_1")
        self.assertEqual(auth.bearer_for("tempo"), "at_1")

        auth.refresh("tempo")
        self.assertEqual(transport.calls[1]["params"]["grant_type"], "refresh_token")
        self.assertEqual(transport.calls[1]["params"]["refresh_token"], "rt_1")
        self.assertEqual(transport.calls[1]["params"]["resource"], "tempo")

        # Rotation: the second refresh must present the newly issued refresh token.
        auth.refresh("tempo")
        self.assertEqual(transport.calls[2]["params"]["refresh_token"], "rt_2")
        self.assertEqual(auth.bearer_for("tempo"), "at_3")
        self.assertEqual(auth.tokens["tempo"].refresh_token, "rt_3")

    def test_revoke_posts_token_and_drops_token_set(self):
        transport = FakeTransport(lambda url, params: None)
        auth = TemperaAuth(
            issuer_url="https://api.tempera.dev",
            client_id="client_1",
            tokens={"remi": TokenSet(access_token="at_remi", refresh_token="rt_remi")},
            transport=transport,
        )
        auth.revoke("remi")
        self.assertEqual(transport.calls[0]["url"], "https://api.tempera.dev/oauth/revoke")
        self.assertEqual(transport.calls[0]["params"]["token"], "rt_remi")
        self.assertEqual(transport.calls[0]["params"]["token_type_hint"], "refresh_token")
        self.assertNotIn("remi", auth.tokens)

    def test_failed_token_requests_raise_tempera_api_error(self):
        def transport(method, url, headers, data):
            raise api_error_from_response(
                401, "Unauthorized", {}, {"error": "unauthenticated", "message": "Authorization code is invalid."}
            )

        auth = TemperaAuth(issuer_url="https://api.tempera.dev", client_id="client_1", transport=transport)
        with self.assertRaises(TemperaApiError) as ctx:
            auth.exchange_code(
                code="bad",
                code_verifier="verifier_1",
                redirect_uri="https://app.example.test/callback",
            )
        self.assertEqual(ctx.exception.status, 401)
        self.assertEqual(ctx.exception.code, "unauthenticated")
        self.assertEqual(ctx.exception.product, "controlPlane")
        self.assertEqual(ctx.exception.operation, ISSUER_PATHS["token"])


class ProductBearerTest(unittest.TestCase):
    def test_bearer_for_matches_the_audience_with_api_key_fallback(self):
        auth = TemperaAuth(
            issuer_url="https://api.tempera.dev",
            api_key="tp_key_1",
            tokens={
                "tempo": TokenSet(access_token="at_tempo"),
                "remi": TokenSet(access_token="at_remi"),
            },
        )
        self.assertEqual(auth.bearer_for("tempo"), "at_tempo")
        self.assertEqual(auth.bearer_for("remi"), "at_remi")
        # No cradle token: the unified API key is the fallback bearer.
        self.assertEqual(auth.bearer_for("cradle"), "tp_key_1")
        self.assertEqual(auth.mcp_url, "https://api.tempera.dev/mcp")

    def test_missing_credential_is_clear(self):
        auth = TemperaAuth(issuer_url="https://api.tempera.dev")
        with self.assertRaises(TemperaSdkError) as ctx:
            auth.bearer_for("cradle")
        self.assertIn("no credential", str(ctx.exception))

    def test_product_audiences_derive_from_the_surface_registry(self):
        self.assertEqual(
            PRODUCT_AUDIENCES,
            {
                "palette": ("palette", "TEMPERA_PALETTE_URL"),
                "tempo": ("tempo", "TEMPERA_TEMPO_URL"),
                "temperaCode": ("tempera-code", "TEMPERA_CODE_GATEWAY_URL"),
                "temperaLlm": ("tempera-llm", "TEMPERA_LLM_URL"),
                "temperaWorkflows": ("tempera-workflows", "TEMPERA_WORKFLOWS_URL"),
                "temperaGym": ("tempera-gym", "TEMPERA_GYM_URL"),
                "cradle": ("cradle", "TEMPERA_CRADLE_URL"),
                "remi": ("remi", "TEMPERA_REMI_URL"),
                "dataEngine": ("data-engine", "TEMPERA_DATA_ENGINE_URL"),
                "humanData": ("human-data", "TEMPERA_HUMAN_DATA_URL"),
            },
        )


if __name__ == "__main__":
    unittest.main()
