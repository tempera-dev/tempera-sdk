import unittest
from urllib import parse as urllib_parse

from tempera_sdk import (
    AUDIENCES,
    DEFAULT_AUDIENCE,
    TemperaAuth,
    TemperaProducts,
    TemperaSdkError,
    TokenSet,
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
        verifier, challenge = create_pkce_pair()
        self.assertRegex(verifier, r"^[A-Za-z0-9_-]{43,128}$")
        self.assertEqual(challenge, pkce_challenge_s256(verifier))
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


class ProductBearerTest(unittest.TestCase):
    def test_products_attach_audience_matched_bearer(self):
        transport = FakeTransport(lambda url, params: {"ok": True})
        auth = TemperaAuth(
            issuer_url="https://api.tempera.dev",
            api_key="tp_key_1",
            tokens={
                "tempo": TokenSet(access_token="at_tempo"),
                "remi": TokenSet(access_token="at_remi"),
            },
        )
        products = TemperaProducts(
            auth,
            base_urls={
                "tempo": "https://tempo.example.test",
                "remi": "https://remi.example.test",
                "cradle": "https://cradle.example.test",
            },
            transport=transport,
        )

        products.tempo("/v1/traces")
        products.remi("/memory")
        products.cradle("/runs")

        self.assertEqual(transport.calls[0]["url"], "https://tempo.example.test/v1/traces")
        self.assertEqual(transport.calls[0]["headers"]["authorization"], "Bearer at_tempo")
        self.assertEqual(transport.calls[1]["headers"]["authorization"], "Bearer at_remi")
        # No cradle token: the unified API key is the fallback bearer.
        self.assertEqual(transport.calls[2]["headers"]["authorization"], "Bearer tp_key_1")
        self.assertEqual(products.mcp_url, "https://api.tempera.dev/mcp")

    def test_missing_credential_is_clear(self):
        auth = TemperaAuth(issuer_url="https://api.tempera.dev")
        with self.assertRaises(TemperaSdkError):
            auth.bearer_for("cradle")


if __name__ == "__main__":
    unittest.main()
