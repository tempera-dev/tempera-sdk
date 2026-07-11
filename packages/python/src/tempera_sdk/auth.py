"""Unified Tempera auth: PKCE helpers, audience-aware token flows, product bearers."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
from dataclasses import dataclass, replace
from typing import Any, Callable, Iterable
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from . import TemperaSdkError

AUDIENCES = ("palette", "tempo", "cradle", "remi", "human-data", "tempera-mcp")
DEFAULT_AUDIENCE = "palette"

PRODUCT_AUDIENCES = {
    "palette": ("palette", "TEMPERA_PALETTE_URL"),
    "tempo": ("tempo", "TEMPERA_TEMPO_URL"),
    "cradle": ("cradle", "TEMPERA_CRADLE_URL"),
    "remi": ("remi", "TEMPERA_REMI_URL"),
}

Transport = Callable[[str, str, dict[str, str], bytes | None], Any]


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate_pkce_verifier(byte_length: int = 32) -> str:
    return _b64url(secrets.token_bytes(byte_length))


def pkce_challenge_s256(verifier: str) -> str:
    return _b64url(hashlib.sha256(verifier.encode("ascii")).digest())


def create_pkce_pair() -> tuple[str, str]:
    """Return a (verifier, challenge) pair for the S256 code challenge method."""
    verifier = generate_pkce_verifier()
    return verifier, pkce_challenge_s256(verifier)


def build_authorize_url(
    *,
    issuer_url: str,
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
    audience: str = DEFAULT_AUDIENCE,
    scope: str | Iterable[str] | None = None,
    state: str | None = None,
) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "resource": audience,
    }
    if scope:
        params["scope"] = scope if isinstance(scope, str) else " ".join(scope)
    if state:
        params["state"] = state
    return f"{issuer_url.rstrip('/')}/oauth/authorize?{urllib_parse.urlencode(params)}"


def _default_transport(method: str, url: str, headers: dict[str, str], data: bytes | None) -> Any:
    req = urllib_request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib_request.urlopen(req, timeout=30) as response:
            text = response.read().decode("utf-8")
    except urllib_error.HTTPError as error:
        body = error.read().decode("utf-8", "replace")
        raise TemperaSdkError(f"Tempera request failed: {method} {url} -> {error.code} {body}") from error
    return json.loads(text) if text else None


@dataclass(frozen=True)
class TokenSet:
    access_token: str
    refresh_token: str | None = None
    expires_in: int | None = None
    scope: str | None = None


class TemperaAuth:
    """One unified credential (API key or per-audience OAuth tokens) against one issuer."""

    def __init__(
        self,
        *,
        issuer_url: str,
        client_id: str | None = None,
        api_key: str | None = None,
        tokens: dict[str, TokenSet] | None = None,
        transport: Transport | None = None,
    ):
        if not issuer_url:
            raise TemperaSdkError("issuer_url is required (e.g. https://api.tempera.dev)")
        self.issuer_url = issuer_url.rstrip("/")
        self.client_id = client_id
        self.api_key = api_key
        self.tokens: dict[str, TokenSet] = dict(tokens or {})
        self.transport = transport or _default_transport

    @property
    def mcp_url(self) -> str:
        return f"{self.issuer_url}/mcp"

    def bearer_for(self, audience: str = DEFAULT_AUDIENCE) -> str:
        token_set = self.tokens.get(audience)
        if token_set is not None:
            return token_set.access_token
        if self.api_key:
            return self.api_key
        raise TemperaSdkError(f"no credential for audience {audience}; provide an api_key or tokens[{audience!r}]")

    def build_authorize_url(self, **options: Any) -> str:
        options.setdefault("issuer_url", self.issuer_url)
        options.setdefault("client_id", self.client_id)
        return build_authorize_url(**options)

    def _post(self, path: str, params: dict[str, str]) -> Any:
        headers = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
        }
        data = urllib_parse.urlencode(params).encode("ascii")
        return self.transport("POST", f"{self.issuer_url}{path}", headers, data)

    def _store(self, audience: str, token: dict[str, Any]) -> TokenSet:
        previous = self.tokens.get(audience)
        self.tokens[audience] = TokenSet(
            access_token=token["access_token"],
            # Refresh-token rotation: the new refresh token replaces the old one.
            refresh_token=token.get("refresh_token") or (previous.refresh_token if previous else None),
            expires_in=token.get("expires_in"),
            scope=token.get("scope"),
        )
        return self.tokens[audience]

    def exchange_code(
        self,
        *,
        code: str,
        code_verifier: str,
        redirect_uri: str,
        audience: str = DEFAULT_AUDIENCE,
    ) -> TokenSet:
        params = {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
            "resource": audience,
        }
        if self.client_id:
            params["client_id"] = self.client_id
        return self._store(audience, self._post("/oauth/token", params))

    def refresh(self, audience: str = DEFAULT_AUDIENCE) -> TokenSet:
        current = self.tokens.get(audience)
        if current is None or not current.refresh_token:
            raise TemperaSdkError(f"no refresh token for audience {audience}")
        params = {
            "grant_type": "refresh_token",
            "refresh_token": current.refresh_token,
            "resource": audience,
        }
        if self.client_id:
            params["client_id"] = self.client_id
        return self._store(audience, self._post("/oauth/token", params))

    def revoke(self, audience: str = DEFAULT_AUDIENCE, *, token_type_hint: str = "refresh_token") -> None:
        current = self.tokens.get(audience)
        token = None
        if current is not None:
            token = current.access_token if token_type_hint == "access_token" else current.refresh_token or current.access_token
        if not token:
            raise TemperaSdkError(f"no token to revoke for audience {audience}")
        params = {"token": token, "token_type_hint": token_type_hint}
        if self.client_id:
            params["client_id"] = self.client_id
        self._post("/oauth/revoke", params)
        self.tokens.pop(audience, None)

    def set_tokens(self, audience: str, token_set: TokenSet) -> None:
        self.tokens[audience] = replace(token_set)


class TemperaProducts:
    """Product clients that attach the audience-matched bearer from one TemperaAuth."""

    def __init__(
        self,
        auth: TemperaAuth,
        *,
        base_urls: dict[str, str] | None = None,
        mcp_url: str | None = None,
        transport: Transport | None = None,
    ):
        self.auth = auth
        self.base_urls = dict(base_urls or {})
        self.mcp_url = mcp_url or auth.mcp_url
        self.transport = transport or auth.transport

    def base_url_for(self, product_key: str) -> str:
        product = PRODUCT_AUDIENCES.get(product_key)
        if product is None:
            raise TemperaSdkError(f"unknown Tempera product: {product_key}")
        base_url = self.base_urls.get(product_key) or os.environ.get(product[1])
        if not base_url:
            raise TemperaSdkError(f"missing base URL for {product_key}; set {product[1]}")
        return base_url.rstrip("/")

    def request(self, product_key: str, path: str, *, method: str = "GET", body: Any = None) -> Any:
        audience = PRODUCT_AUDIENCES[product_key][0] if product_key in PRODUCT_AUDIENCES else None
        base_url = self.base_url_for(product_key)
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self.auth.bearer_for(audience)}",
        }
        if data is not None:
            headers["content-type"] = "application/json"
        return self.transport(method, f"{base_url}/{path.lstrip('/')}", headers, data)

    def palette(self, path: str, **options: Any) -> Any:
        return self.request("palette", path, **options)

    def tempo(self, path: str, **options: Any) -> Any:
        return self.request("tempo", path, **options)

    def cradle(self, path: str, **options: Any) -> Any:
        return self.request("cradle", path, **options)

    def remi(self, path: str, **options: Any) -> Any:
        return self.request("remi", path, **options)


__all__ = [
    "AUDIENCES",
    "DEFAULT_AUDIENCE",
    "PRODUCT_AUDIENCES",
    "TemperaAuth",
    "TemperaProducts",
    "TokenSet",
    "build_authorize_url",
    "create_pkce_pair",
    "generate_pkce_verifier",
    "pkce_challenge_s256",
]
