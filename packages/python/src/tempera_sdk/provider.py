"""Dependency-free typed MCP provider authoring for Tempera.

This module is intentionally small: it authors ordinary MCP stdio providers while
Tempera MCP remains the policy, retrieval, durability, and execution boundary.
Schemas are compiled once when a tool is registered and request handling is line-
delimited JSON-RPC with protocol-only stdout.
"""

from __future__ import annotations

import asyncio
import dataclasses
import inspect
import json
import sys
import types
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Annotated, Literal, Union, get_args, get_origin, get_type_hints

MCP_PROVIDER_PROTOCOL_VERSION = "2026-07-28"


class ProviderDefinitionError(ValueError):
    """The authored provider definition cannot be represented safely."""


class ProviderArgumentError(ValueError):
    """A tool invocation does not satisfy the registered Python type contract."""


class _ProviderExecutionError(RuntimeError):
    """Redacted application failure translated to a JSON-RPC internal error."""


@dataclass(frozen=True)
class _RegisteredTool:
    name: str
    description: str
    function: Callable[..., Any]
    signature: inspect.Signature
    hints: Mapping[str, Any]
    input_schema: Mapping[str, Any]
    annotations: Mapping[str, bool]

    def public_spec(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": dict(self.input_schema),
            "annotations": dict(self.annotations),
        }


def _json_default(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)
    raise TypeError(f"{type(value).__name__} is not JSON serializable")


def _json_safe_default(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, default=_json_default))
    except (TypeError, ValueError) as error:
        raise ProviderDefinitionError("tool defaults must be JSON serializable") from error


def _schema_for(annotation: Any) -> dict[str, Any]:
    if annotation in (inspect.Signature.empty, Any):
        return {}
    if annotation is None or annotation is type(None):
        return {"type": "null"}

    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is Annotated:
        return _schema_for(args[0])
    if origin is Literal:
        values = list(args)
        schema: dict[str, Any] = {"enum": values}
        value_types = {type(value) for value in values}
        if len(value_types) == 1:
            value_type = next(iter(value_types))
            primitive = {str: "string", int: "integer", float: "number", bool: "boolean"}.get(
                value_type
            )
            if primitive:
                schema["type"] = primitive
        return schema
    if origin in (Union, types.UnionType):
        return {"anyOf": [_schema_for(arg) for arg in args]}
    if origin in (list, tuple):
        if origin is tuple and len(args) == 2 and args[1] is Ellipsis:
            item = args[0]
        elif origin is tuple:
            return {
                "type": "array",
                "prefixItems": [_schema_for(arg) for arg in args],
                "minItems": len(args),
                "maxItems": len(args),
            }
        else:
            item = args[0] if args else Any
        return {"type": "array", "items": _schema_for(item)}
    if origin is dict:
        key_type, value_type = args if len(args) == 2 else (str, Any)
        if key_type not in (str, Any):
            raise ProviderDefinitionError("MCP object keys must be strings")
        return {"type": "object", "additionalProperties": _schema_for(value_type)}

    if annotation is str:
        return {"type": "string"}
    if annotation is bool:
        return {"type": "boolean"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}

    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        hints = get_type_hints(annotation, include_extras=True)
        properties: dict[str, Any] = {}
        required: list[str] = []
        for field in dataclasses.fields(annotation):
            field_schema = _schema_for(hints.get(field.name, field.type))
            if field.default is not dataclasses.MISSING:
                field_schema["default"] = _json_safe_default(field.default)
            elif field.default_factory is not dataclasses.MISSING:  # type: ignore[misc]
                field_schema["default"] = _json_safe_default(field.default_factory())
            else:
                required.append(field.name)
            properties[field.name] = field_schema
        schema = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }
        if required:
            schema["required"] = required
        return schema

    raise ProviderDefinitionError(f"unsupported tool annotation: {annotation!r}")


def _matches_primitive(value: Any, annotation: Any) -> bool:
    if annotation is bool:
        return isinstance(value, bool)
    if annotation is int:
        return isinstance(value, int) and not isinstance(value, bool)
    if annotation is float:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if annotation is str:
        return isinstance(value, str)
    return False


def _decode(value: Any, annotation: Any, path: str) -> Any:
    if annotation in (inspect.Signature.empty, Any):
        return value
    if annotation is None or annotation is type(None):
        if value is None:
            return None
        raise ProviderArgumentError(f"{path} must be null")

    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is Annotated:
        return _decode(value, args[0], path)
    if origin is Literal:
        if value in args and any(type(value) is type(candidate) for candidate in args if candidate == value):
            return value
        raise ProviderArgumentError(f"{path} must be one of {list(args)!r}")
    if origin in (Union, types.UnionType):
        for option in args:
            try:
                return _decode(value, option, path)
            except ProviderArgumentError:
                pass
        raise ProviderArgumentError(f"{path} does not match any allowed type")
    if origin is list:
        if not isinstance(value, list):
            raise ProviderArgumentError(f"{path} must be an array")
        item_type = args[0] if args else Any
        return [_decode(item, item_type, f"{path}[{index}]") for index, item in enumerate(value)]
    if origin is tuple:
        if not isinstance(value, list):
            raise ProviderArgumentError(f"{path} must be an array")
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_decode(item, args[0], f"{path}[{index}]") for index, item in enumerate(value))
        if len(value) != len(args):
            raise ProviderArgumentError(f"{path} must contain exactly {len(args)} items")
        return tuple(
            _decode(item, item_type, f"{path}[{index}]")
            for index, (item, item_type) in enumerate(zip(value, args))
        )
    if origin is dict:
        if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
            raise ProviderArgumentError(f"{path} must be an object with string keys")
        key_type, value_type = args if len(args) == 2 else (str, Any)
        if key_type not in (str, Any):
            raise ProviderArgumentError(f"{path} has an unsupported key type")
        return {key: _decode(item, value_type, f"{path}.{key}") for key, item in value.items()}

    if annotation in (str, bool, int, float):
        if not _matches_primitive(value, annotation):
            raise ProviderArgumentError(f"{path} must be {annotation.__name__}")
        return float(value) if annotation is float else value

    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        if not isinstance(value, dict):
            raise ProviderArgumentError(f"{path} must be an object")
        hints = get_type_hints(annotation, include_extras=True)
        fields = {field.name: field for field in dataclasses.fields(annotation)}
        extras = set(value) - set(fields)
        if extras:
            raise ProviderArgumentError(f"{path} has unknown fields: {sorted(extras)!r}")
        decoded: dict[str, Any] = {}
        for name, field in fields.items():
            if name in value:
                decoded[name] = _decode(value[name], hints.get(name, field.type), f"{path}.{name}")
            elif field.default is dataclasses.MISSING and field.default_factory is dataclasses.MISSING:  # type: ignore[misc]
                raise ProviderArgumentError(f"{path}.{name} is required")
        return annotation(**decoded)

    raise ProviderArgumentError(f"{path} uses an unsupported type")


def _compile_tool(
    function: Callable[..., Any],
    *,
    name: str,
    description: str,
    annotations: Mapping[str, bool],
) -> _RegisteredTool:
    signature = inspect.signature(function)
    hints = get_type_hints(function, include_extras=True)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for parameter_name, parameter in signature.parameters.items():
        if parameter.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
            inspect.Parameter.POSITIONAL_ONLY,
        ):
            raise ProviderDefinitionError(
                f"tool {name!r} must use named parameters without *args/**kwargs"
            )
        annotation = hints.get(parameter_name, parameter.annotation)
        field_schema = _schema_for(annotation)
        if parameter.default is inspect.Parameter.empty:
            required.append(parameter_name)
        else:
            field_schema["default"] = _json_safe_default(parameter.default)
        properties[parameter_name] = field_schema
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        input_schema["required"] = required
    return _RegisteredTool(
        name=name,
        description=description,
        function=function,
        signature=signature,
        hints=hints,
        input_schema=input_schema,
        annotations=dict(annotations),
    )


def _decode_arguments(tool: _RegisteredTool, arguments: Mapping[str, Any]) -> dict[str, Any]:
    extras = set(arguments) - set(tool.signature.parameters)
    if extras:
        raise ProviderArgumentError(f"unknown arguments: {sorted(extras)!r}")
    decoded: dict[str, Any] = {}
    for name, parameter in tool.signature.parameters.items():
        if name in arguments:
            decoded[name] = _decode(
                arguments[name],
                tool.hints.get(name, parameter.annotation),
                name,
            )
        elif parameter.default is inspect.Parameter.empty:
            raise ProviderArgumentError(f"{name} is required")
    return decoded


def _tool_result(result: Any) -> dict[str, Any]:
    if dataclasses.is_dataclass(result) and not isinstance(result, type):
        structured = dataclasses.asdict(result)
    elif isinstance(result, Mapping):
        structured = dict(result)
    elif result is None:
        structured = {}
    else:
        structured = {"value": result}
    try:
        text = json.dumps(structured, separators=(",", ":"), default=_json_default)
    except (TypeError, ValueError):
        return {
            "resultType": "complete",
            "content": [{"type": "text", "text": "Tool returned a non-JSON value"}],
            "structuredContent": {"error": "non_json_result"},
            "isError": True,
        }
    return {
        "resultType": "complete",
        "content": [{"type": "text", "text": text}],
        "structuredContent": structured,
        "isError": False,
    }


def _tool_failure() -> dict[str, Any]:
    return {
        "resultType": "complete",
        "content": [{"type": "text", "text": "Tool execution failed"}],
        "structuredContent": {"error": "tool_execution_failed"},
        "isError": True,
    }


class TemperaProvider:
    """Tiny typed MCP provider intended to run behind the Tempera gateway."""

    def __init__(self, name: str, *, version: str = "1.0.0") -> None:
        if not name.strip():
            raise ProviderDefinitionError("provider name must not be empty")
        self.name = name.strip()
        self.version = version
        self._tools: dict[str, _RegisteredTool] = {}

    def tool(
        self,
        function: Callable[..., Any] | None = None,
        *,
        name: str | None = None,
        description: str | None = None,
        read_only: bool = False,
        idempotent: bool = False,
        destructive: bool = False,
        open_world: bool = False,
    ) -> Callable[..., Any]:
        """Register a function as one typed MCP tool.

        Use as ``@app.tool`` or ``@app.tool(read_only=True, idempotent=True)``.
        Sync and async functions share the same registration contract.
        """

        def register(target: Callable[..., Any]) -> Callable[..., Any]:
            tool_name = (name or target.__name__).strip()
            if not tool_name or any(character.isspace() for character in tool_name):
                raise ProviderDefinitionError("tool name must be a non-empty token")
            if tool_name in self._tools:
                raise ProviderDefinitionError(f"duplicate tool name: {tool_name}")
            if read_only and destructive:
                raise ProviderDefinitionError("a read-only tool cannot be destructive")
            tool_description = description
            if tool_description is None:
                tool_description = inspect.getdoc(target) or target.__name__.replace("_", " ")
            annotations = {
                "readOnlyHint": read_only,
                "idempotentHint": idempotent,
                "destructiveHint": destructive,
                "openWorldHint": open_world,
            }
            self._tools[tool_name] = _compile_tool(
                target,
                name=tool_name,
                description=tool_description,
                annotations=annotations,
            )
            return target

        if function is None:
            return register
        return register(function)

    def _base_response(self, request: Mapping[str, Any]) -> dict[str, Any] | None:
        method = request.get("method")
        if method == "server/discover":
            return {
                "resultType": "complete",
                "supportedVersions": [MCP_PROVIDER_PROTOCOL_VERSION],
                "capabilities": {"tools": {}},
                "serverInfo": {"name": self.name, "version": self.version},
                "ttlMs": 0,
                "cacheScope": "private",
            }
        if method == "ping":
            return {}
        if method == "tools/list":
            return {
                "resultType": "complete",
                "tools": [self._tools[name].public_spec() for name in sorted(self._tools)],
            }
        return None

    def _requested_tool(self, request: Mapping[str, Any]) -> tuple[_RegisteredTool, Mapping[str, Any]]:
        params = request.get("params") or {}
        if not isinstance(params, Mapping):
            raise ProviderArgumentError("tools/call params must be an object")
        tool_name = params.get("name")
        if not isinstance(tool_name, str) or tool_name not in self._tools:
            raise ProviderArgumentError("unknown tool")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, Mapping):
            raise ProviderArgumentError("tool arguments must be an object")
        return self._tools[tool_name], arguments

    def handle(self, request: Mapping[str, Any]) -> dict[str, Any]:
        """Handle one synchronous decoded JSON-RPC request.

        Async tools are rejected before invocation. Call :meth:`handle_async` or use
        :meth:`run_stdio` for providers containing async tools.
        """
        base = self._base_response(request)
        if base is not None:
            return base
        if request.get("method") != "tools/call":
            raise KeyError("unknown method")
        tool, arguments = self._requested_tool(request)
        if inspect.iscoroutinefunction(tool.function):
            raise ProviderDefinitionError("async tool requires handle_async() or run_stdio()")
        decoded = _decode_arguments(tool, arguments)
        try:
            result = tool.function(**decoded)
        except Exception:
            return _tool_failure()
        if inspect.isawaitable(result):
            if inspect.iscoroutine(result):
                result.close()
            raise ProviderDefinitionError("tool returned an awaitable from synchronous handle()")
        return _tool_result(result)

    async def handle_async(self, request: Mapping[str, Any]) -> dict[str, Any]:
        """Handle one decoded request, supporting both sync and async tools."""
        base = self._base_response(request)
        if base is not None:
            return base
        if request.get("method") != "tools/call":
            raise KeyError("unknown method")
        tool, arguments = self._requested_tool(request)
        decoded = _decode_arguments(tool, arguments)
        try:
            result = tool.function(**decoded)
            if inspect.isawaitable(result):
                result = await result
        except Exception:
            return _tool_failure()
        return _tool_result(result)

    async def run_stdio_async(self) -> None:
        """Run line-delimited JSON-RPC stdio in the caller's async runtime."""
        while True:
            raw_line = await asyncio.to_thread(sys.stdin.readline)
            if raw_line == "":
                return
            request: Any = None
            try:
                request = json.loads(raw_line)
                if not isinstance(request, Mapping):
                    raise ProviderArgumentError("request must be an object")
                if "id" not in request:
                    continue
                result = await self.handle_async(request)
                response = {"jsonrpc": "2.0", "id": request["id"], "result": result}
            except KeyError:
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id") if isinstance(request, Mapping) else None,
                    "error": {"code": -32601, "message": "Method not found"},
                }
            except (ProviderArgumentError, ProviderDefinitionError, json.JSONDecodeError):
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id") if isinstance(request, Mapping) else None,
                    "error": {"code": -32602, "message": "Invalid request"},
                }
            except _ProviderExecutionError:
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id") if isinstance(request, Mapping) else None,
                    "error": {"code": -32603, "message": "Provider execution failed"},
                }
            sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
            sys.stdout.flush()

    def run_stdio(self) -> None:
        """Run the provider over stdio, owning one event loop for sync and async tools."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self.run_stdio_async())
            return
        raise ProviderDefinitionError("run_stdio() cannot own an already-running event loop; await run_stdio_async()")


__all__ = [
    "MCP_PROVIDER_PROTOCOL_VERSION",
    "ProviderArgumentError",
    "ProviderDefinitionError",
    "TemperaProvider",
]
