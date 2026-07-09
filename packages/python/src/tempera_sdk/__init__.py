from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib import request as urllib_request
import json
import os


SCOPES = (
    "mcp:invoke",
    "trace:read",
    "trace:write",
    "dataset:read",
    "dataset:write",
    "eval:run",
    "pii:unmask",
    "admin",
)


@dataclass(frozen=True)
class Product:
    name: str
    repository: str
    env: str


PRODUCTS = {
    "auth_hub": Product("auth-hub", "https://github.com/tempera-dev/auth-hub", "TEMPERA_CONTROL_PLANE_URL"),
    "tempo": Product("tempo", "https://github.com/tempera-dev/tempo", "TEMPERA_TEMPO_URL"),
    "temp_js": Product("temp.js", "https://github.com/tempera-dev/temp.js", "TEMPERA_TEMPJS_URL"),
    "temp_os": Product("tempOS", "https://github.com/tempera-dev/tempOS", "TEMPERA_TEMPOS_URL"),
    "remi": Product("remi", "https://github.com/tempera-dev/remi", "TEMPERA_REMI_URL"),
    "cradle": Product("cradle", "https://github.com/tempera-dev/cradle", "TEMPERA_CRADLE_URL"),
    "arrha": Product("Arrha", "https://github.com/tempera-dev/arrha", "TEMPERA_ARRHA_URL"),
}


class TemperaSdkError(RuntimeError):
    pass


class TemperaClient:
    def __init__(self, *, endpoints: dict[str, str] | None = None, access_token: str | None = None):
        self.endpoints = endpoints or {}
        self.access_token = access_token

    def endpoint_for(self, product_key: str) -> str:
        product = PRODUCTS.get(product_key)
        if product is None:
            raise TemperaSdkError(f"unknown Tempera product: {product_key}")
        endpoint = self.endpoints.get(product_key) or os.environ.get(product.env)
        if not endpoint:
            raise TemperaSdkError(f"missing endpoint for {product.name}; set {product.env}")
        return endpoint.rstrip("/")

    def request(self, product_key: str, path: str, *, method: str = "GET", body: Any = None) -> Any:
        endpoint = self.endpoint_for(product_key)
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"accept": "application/json"}
        if data is not None:
            headers["content-type"] = "application/json"
        if self.access_token:
            headers["authorization"] = f"Bearer {self.access_token}"
        req = urllib_request.Request(f"{endpoint}/{path.lstrip('/')}", data=data, headers=headers, method=method)
        with urllib_request.urlopen(req, timeout=30) as response:
            text = response.read().decode("utf-8")
            return json.loads(text) if text else None


__all__ = ["PRODUCTS", "SCOPES", "Product", "TemperaClient", "TemperaSdkError"]
