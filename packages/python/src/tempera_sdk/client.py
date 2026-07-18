"""The unified Tempera client: one credential set, every product.

Built entirely from the generated surface tables (tempera_sdk.surface), so the
TypeScript, Python, and Rust packages expose the same products, the same
operation names, the same descriptions, and the same error shape.

- Typed operations: ``client.palette.get_trace({"tenant_id": ..., "trace_id": ...})``
  — every operation in surface.json becomes a method on its product client.
  Parameters use wire names (snake_case) in every language.
- Passthrough: ``client.tempo.request("/custom", method="POST", body=...)``
  for endpoints the surface tables don't cover yet.
- Auth: audience products resolve their bearer through TemperaAuth (per-
  audience OAuth token with unified tp_ API-key fallback); control-plane
  operations use the account-session token, which login()/signup() store
  automatically.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Mapping

from .auth import TemperaAuth, Transport, _default_transport
from .errors import TemperaApiError, TemperaSdkError, _with_context
from .surface import DEFAULT_AUDIENCE, ENVIRONMENTS, OPERATIONS, PRODUCTS
from urllib import parse as urllib_parse


def _snake_case(key: str) -> str:
    return re.sub(r"([a-z0-9])([A-Z]+)", r"\1_\2", key).lower()


# camelCase registry key (surface.json) <-> snake_case client attribute.
PRODUCT_ATTRS = {key: _snake_case(key) for key in PRODUCTS}
_ATTR_TO_KEY = {attr: key for key, attr in PRODUCT_ATTRS.items()}

# Environment presets only carry base URLs for these products.
_ENVIRONMENT_TARGET_KEYS = {
    "controlPlane": "controlPlaneUrl",
    "palette": "paletteApiUrl",
    "tempo": "tempoApiUrl",
    "temperaCode": "temperaCodeApiUrl",
    "temperaLlm": "temperaLlmApiUrl",
    "dataEngine": "dataEngineApiUrl",
    "cradle": "cradleApiUrl",
}

_PATH_PARAM_RE = re.compile(r"\{([a-z_]+)\}")


def _query_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


class _ProductClient:
    """One product's client: registry metadata, typed operations, passthrough request()."""

    def __init__(self, client: "TemperaClient", product_key: str):
        product = PRODUCTS[product_key]
        self._client = client
        self.key = product_key
        self.name = product["name"]
        self.repository = product["repository"]
        self.env_var = product["env_var"]
        self.audience = product["audience"]
        self.description = product["description"]
        for op in OPERATIONS.get(product_key, []):
            setattr(self, op["id"], self._make_operation(op))

    def _make_operation(self, op: dict[str, Any]):
        client = self._client
        product_key = self.key

        def operation(params: Mapping[str, Any] | None = None, *, bearer: str | None = None,
                      headers: Mapping[str, str] | None = None, **extra: Any) -> Any:
            merged = dict(params or {})
            merged.update(extra)
            result = client._dispatch(product_key, op, merged, bearer=bearer, headers=headers)
            # login/signup return the account-session token pair and store the
            # access token so later control-plane calls are authenticated.
            if product_key == "controlPlane" and op["id"] in ("login", "signup"):
                if isinstance(result, Mapping) and result.get("access_token"):
                    client.account_token = result["access_token"]
            return result

        operation.__name__ = op["id"]
        operation.__qualname__ = f"TemperaClient.{PRODUCT_ATTRS[product_key]}.{op['id']}"
        operation.__doc__ = op["description"]
        return operation

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        body: Any = None,
        query: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        bearer: str | None = None,
    ) -> Any:
        """Raw request against this product for endpoints without a typed operation."""
        if not path.startswith("/"):
            path = f"/{path}"
        if bearer is None and (self.audience or self.key == "controlPlane"):
            bearer = self._client._try_bearer(self.key)
        return self._client._raw_request(
            self.key, path, method=method, body=body, query=query, headers=headers, bearer=bearer
        )


class TemperaClient:
    """One credential set, every Tempera product (see module docstring)."""

    def __init__(
        self,
        *,
        auth: TemperaAuth | None = None,
        account_token: str | None = None,
        introspection_secret: str | None = None,
        base_urls: Mapping[str, str] | None = None,
        environment: str | None = None,
        transport: Transport | None = None,
    ):
        self.auth = auth
        self.account_token = account_token
        self._introspection_secret = introspection_secret
        # base_urls accepts snake_case attribute names and camelCase registry keys.
        self._base_urls = {_ATTR_TO_KEY.get(key, key): value for key, value in (base_urls or {}).items()}
        if environment is not None and environment not in ENVIRONMENTS:
            raise TemperaSdkError(f"unknown Tempera environment: {environment}")
        self._environment_targets = ENVIRONMENTS[environment] if environment else None
        self._transport = transport or (auth.transport if auth else None) or _default_transport
        self.control_plane: _ProductClient
        self.palette: _ProductClient
        self.tempo: _ProductClient
        self.tempera_code: _ProductClient
        self.tempera_llm: _ProductClient
        self.cradle: _ProductClient
        self.remi: _ProductClient
        self.data_engine: _ProductClient
        self.human_data: _ProductClient
        self.temp_js: _ProductClient
        self.temp_os: _ProductClient
        self.arrha: _ProductClient
        for product_key, attr in PRODUCT_ATTRS.items():
            setattr(self, attr, _ProductClient(self, product_key))

    def _base_url_for(self, product_key: str) -> str:
        product = PRODUCTS.get(product_key)
        if product is None:
            raise TemperaSdkError(f"unknown Tempera product: {product_key}")
        from_environment = None
        if self._environment_targets is not None:
            target_key = _ENVIRONMENT_TARGET_KEYS.get(product_key)
            if target_key:
                from_environment = self._environment_targets.get(target_key)
        base_url = self._base_urls.get(product_key) or os.environ.get(product["env_var"]) or from_environment
        if not base_url:
            attr = PRODUCT_ATTRS[product_key]
            raise TemperaSdkError(
                f"missing base URL for {attr}; set {product['env_var']} or pass base_urls[{attr!r}]"
            )
        return base_url.rstrip("/")

    def _bearer_for(self, product_key: str, auth_kind: str) -> str | None:
        attr = PRODUCT_ATTRS[product_key]
        if auth_kind == "none":
            return None
        if auth_kind == "introspectionSecret":
            if not self._introspection_secret:
                raise TemperaSdkError(f"{attr}: introspect_token requires the introspection_secret option")
            return self._introspection_secret
        if auth_kind == "account":
            if not self.account_token:
                raise TemperaSdkError(
                    f"{attr}: an account token is required; call control_plane.login()/signup() first or pass account_token"
                )
            return self.account_token
        audience = PRODUCTS[product_key]["audience"] or DEFAULT_AUDIENCE
        if self.auth is None:
            raise TemperaSdkError(
                f"{attr}: pass a TemperaAuth (with an api_key or {audience} tokens) to call product endpoints"
            )
        return self.auth.bearer_for(audience)

    def _try_bearer(self, product_key: str) -> str | None:
        try:
            return self._bearer_for(product_key, "account" if product_key == "controlPlane" else "product")
        except TemperaSdkError:
            return None

    def _raw_request(
        self,
        product_key: str,
        path: str,
        *,
        method: str = "GET",
        body: Any = None,
        query: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        bearer: str | None = None,
        operation: str | None = None,
    ) -> Any:
        url = self._base_url_for(product_key) + path
        query_pairs = [(key, _query_value(value)) for key, value in (query or {}).items() if value is not None]
        if query_pairs:
            url += ("&" if "?" in url else "?") + urllib_parse.urlencode(query_pairs)
        request_headers = {"accept": "application/json"}
        if body is not None:
            request_headers["content-type"] = "application/json"
        if bearer:
            request_headers["authorization"] = f"Bearer {bearer}"
        if headers:
            request_headers.update(headers)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        try:
            return self._transport(method, url, request_headers, data)
        except TemperaApiError as error:
            raise _with_context(error, product_key, operation) from None

    def _substitute_path(self, template: str, params: Mapping[str, Any], product_key: str, operation_id: str) -> str:
        def replace(match: "re.Match[str]") -> str:
            key = match.group(1)
            value = params.get(key)
            if value is None or value == "":
                raise TemperaSdkError(
                    f'{PRODUCT_ATTRS[product_key]}.{operation_id}: missing required path parameter "{key}"'
                )
            return urllib_parse.quote(str(value), safe="")

        return _PATH_PARAM_RE.sub(replace, template)

    def _dispatch(
        self,
        product_key: str,
        op: dict[str, Any],
        params: Mapping[str, Any],
        *,
        bearer: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        path = self._substitute_path(op["path"], params, product_key, op["id"])
        consumed = set(op["path_params"])
        query: dict[str, Any] = {}
        for key in op["query"]:
            if key in params:
                query[key] = params[key]
                consumed.add(key)
        body: dict[str, Any] | None = None
        if op["body"] or op["body_defaults"]:
            body = dict(op["body_defaults"])
            for key in op["body"]:
                if key in params:
                    body[key] = params[key]
                    consumed.add(key)
        # Forward-compatibility: undeclared parameters flow to the query string
        # on GET/DELETE and into the JSON body otherwise, so a new server field
        # is usable before the surface tables catch up.
        for key, value in params.items():
            if key in consumed:
                continue
            if op["method"] in ("GET", "DELETE"):
                query[key] = value
            else:
                if body is None:
                    body = {}
                body[key] = value
        resolved_bearer = bearer if bearer is not None else self._bearer_for(product_key, op["auth"])
        return self._raw_request(
            product_key,
            path,
            method=op["method"],
            body=body,
            query=query,
            headers=headers,
            bearer=resolved_bearer,
            operation=op["id"],
        )


__all__ = ["TemperaClient"]
