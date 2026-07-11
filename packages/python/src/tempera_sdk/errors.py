"""Uniform Tempera SDK errors, shared in shape with the TypeScript and Rust
packages (see surface.json ``errorContract``).

- ``TemperaSdkError``: base class for every error the SDK raises, including
  configuration and usage mistakes (missing credential, unknown product).
- ``TemperaApiError``: an HTTP response error, normalized from the five wire
  error shapes in the Tempera fleet so callers always read the same fields.
- ``TemperaMcpError``: a JSON-RPC error from an MCP endpoint.
"""

from __future__ import annotations

from typing import Any, Mapping


class TemperaSdkError(RuntimeError):
    """Base class for every error the Tempera SDK raises."""


class TemperaApiError(TemperaSdkError):
    """An HTTP response error with the uniform Tempera error fields."""

    def __init__(
        self,
        *,
        status: int,
        code: str | None = None,
        message: str = "",
        request_id: str | None = None,
        product: str | None = None,
        operation: str | None = None,
        body: Any = None,
        status_text: str = "",
    ):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.request_id = request_id
        self.product = product
        self.operation = operation
        self.body = body
        # Kept so the error can be re-labelled with product/operation context
        # after a transport raises it (see _with_context).
        self.status_text = status_text


class TemperaMcpError(TemperaSdkError):
    """A JSON-RPC error returned by an MCP endpoint."""

    def __init__(self, message: str, *, code: int, data: Any = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data


def normalize_error_body(body: Any, status_text: str = "") -> dict[str, Any]:
    """Normalize any Tempera product error body into {code, message, request_id}.

    Wire shapes handled (see surface.json errorContract.wireShapes):
    - control plane / palette: ``{"error": "<code>", "message": "<text>"}``
    - tempo:                   ``{"error": "<human message>"}``
    - cradle / remi:           ``{"error": {"code", "message", "request_id"?, ...}}``
    """
    if isinstance(body, Mapping):
        error = body.get("error")
        if isinstance(error, Mapping):
            code = error.get("code")
            message = error.get("message")
            request_id = error.get("request_id")
            return {
                "code": code if isinstance(code, str) else None,
                "message": message if isinstance(message, str) else status_text,
                "request_id": request_id if isinstance(request_id, str) else None,
            }
        if isinstance(error, str):
            if isinstance(body.get("message"), str):
                return {"code": error, "message": body["message"], "request_id": None}
            return {"code": None, "message": error, "request_id": None}
    return {"code": None, "message": status_text or "request failed", "request_id": None}


def _header_get(headers: Any, name: str) -> str | None:
    if headers is None:
        return None
    if isinstance(headers, Mapping):
        for key, value in headers.items():
            if isinstance(key, str) and key.lower() == name:
                return value
        return None
    get = getattr(headers, "get", None)
    if callable(get):
        # e.g. http.client.HTTPMessage, whose get() is case-insensitive.
        return get(name)
    return None


def api_error_from_response(
    status: int,
    status_text: str = "",
    headers: Any = None,
    body: Any = None,
    product: str | None = None,
    operation: str | None = None,
) -> TemperaApiError:
    """Build a TemperaApiError from a failed HTTP response.

    ``request_id`` falls back to the ``x-request-id`` response header.
    """
    normalized = normalize_error_body(body, status_text)
    header_request_id = _header_get(headers, "x-request-id")
    label = ".".join(part for part in (product, operation) if part)
    return TemperaApiError(
        status=status,
        code=normalized["code"],
        message=f"Tempera {label or 'request'} failed ({status}): {normalized['message']}",
        request_id=normalized["request_id"] or header_request_id,
        product=product,
        operation=operation,
        body=body,
        status_text=status_text,
    )


def _with_context(error: TemperaApiError, product: str | None, operation: str | None) -> TemperaApiError:
    """Re-label a context-free TemperaApiError (raised by a transport) with the
    product and operation that made the request."""
    if error.product or error.operation:
        return error
    headers = {"x-request-id": error.request_id} if error.request_id else None
    return api_error_from_response(error.status, error.status_text, headers, error.body, product, operation)


__all__ = [
    "TemperaApiError",
    "TemperaMcpError",
    "TemperaSdkError",
    "api_error_from_response",
    "normalize_error_body",
]
