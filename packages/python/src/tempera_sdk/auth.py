"""Unified Tempera auth: PKCE helpers, audience-aware token flows, product bearers."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass, replace
from typing import Any, Callable, Iterable, NamedTuple
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from .errors import TemperaApiError, TemperaSdkError, _with_context, api_error_from_response
from .surface import AUDIENCES, DEFAULT_AUDIENCE, ISSUER_PATHS, PRODUCTS

Transport = Callable[[str, str, dict[str, str], "bytes | None"], Any]


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate_pkce_verifier(byte_length: int = 32) -> str:
    return _b64url(secrets.token_bytes(byte_length))


def pkce_challenge_s256(verifier: str) -> str:
    return _b64url(hashlib.sha256(verifier.encode("ascii")).digest())


class PkcePair(NamedTuple):
    verifier: str
    challenge: str
    method: str = "S256"


def create_pkce_pair() -> PkcePair:
    """Create a (verifier, challenge, method="S256") PKCE pair."""
    verifier = generate_pkce_verifier()
    return PkcePair(verifier=verifier, challenge=pkce_challenge_s256(verifier))


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
    """Build the /oauth/authorize URL with PKCE and the resource audience selector."""
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
    return f"{issuer_url.rstrip('/')}{ISSUER_PATHS['authorize']}?{urllib_parse.urlencode(params)}"


def _parse_body(raw: bytes, content_type: str) -> Any:
    if not raw:
        return None
    if "json" in content_type:
        return json.loads(raw.decode("utf-8"))
    if content_type.startswith("text/"):
        return raw.decode("utf-8", "replace")
    if not content_type:
        text = raw.decode("utf-8", "replace")
        try:
            return json.loads(text)
        except ValueError:
            return text
    return raw


def _default_transport(method: str, url: str, headers: dict[str, str], data: bytes | None) -> Any:
    """Stdlib HTTP transport: returns the parsed response body, raising a
    TemperaApiError (normalized per surface.json errorContract) on HTTP errors."""
    req = urllib_request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib_request.urlopen(req, timeout=30) as response:
            return _parse_body(response.read(), response.headers.get("content-type") or "")
    except urllib_error.HTTPError as error:
        body = _parse_body(error.read(), error.headers.get("content-type") or "")
        raise api_error_from_response(error.code, error.reason or "", error.headers, body) from None


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
        """Unified MCP gateway URL (streamable-HTTP MCP, audience tempera-mcp)."""
        return f"{self.issuer_url}{ISSUER_PATHS['mcp']}"

    def bearer_for(self, audience: str = DEFAULT_AUDIENCE) -> str:
        """The bearer for an audience: its access token, falling back to the tp_ API key."""
        token_set = self.tokens.get(audience)
        if token_set is not None and token_set.access_token:
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
        try:
            return self.transport("POST", f"{self.issuer_url}{path}", headers, data)
        except TemperaApiError as error:
            raise _with_context(error, "controlPlane", path) from None

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
        """Exchange an authorization code (PKCE) for the audience's token set."""
        params = {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
            "resource": audience,
        }
        if self.client_id:
            params["client_id"] = self.client_id
        return self._store(audience, self._post(ISSUER_PATHS["token"], params))

    def refresh(self, audience: str = DEFAULT_AUDIENCE) -> TokenSet:
        """Refresh the audience's tokens; rotation stores the newly issued refresh token."""
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
        return self._store(audience, self._post(ISSUER_PATHS["token"], params))

    def revoke(self, audience: str = DEFAULT_AUDIENCE, *, token_type_hint: str = "refresh_token") -> None:
        """Revoke the audience's token at the issuer and drop it from the store."""
        current = self.tokens.get(audience)
        token = None
        if current is not None:
            token = current.access_token if token_type_hint == "access_token" else current.refresh_token or current.access_token
        if not token:
            raise TemperaSdkError(f"no token to revoke for audience {audience}")
        params = {"token": token, "token_type_hint": token_type_hint}
        if self.client_id:
            params["client_id"] = self.client_id
        self._post(ISSUER_PATHS["revoke"], params)
        self.tokens.pop(audience, None)

    def set_tokens(self, audience: str, token_set: TokenSet) -> None:
        self.tokens[audience] = replace(token_set)


# Product key -> (audience, env var) for the audience-bearing products.
PRODUCT_AUDIENCES = {
    key: (product["audience"], product["env_var"])
    for key, product in PRODUCTS.items()
    if product["audience"]
}


__all__ = [
    "AUDIENCES",
    "DEFAULT_AUDIENCE",
    "ISSUER_PATHS",
    "PRODUCT_AUDIENCES",
    "PkcePair",
    "TemperaAuth",
    "TokenSet",
    "build_authorize_url",
    "create_pkce_pair",
    "generate_pkce_verifier",
    "pkce_challenge_s256",
]
