"""First-class MCP resources and prompts layered onto :mod:`tempera_sdk.provider`.

This module deliberately extends provider authoring only. The Tempera MCP gateway
continues to own authorization, retrieval, durability, policy, admission, and
evidence. Resource and prompt handlers use the same registration-time schema
compilation, pre-execution argument validation, async semantics, and redacted
application failures as tools.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .provider import (
    ProviderArgumentError,
    ProviderDefinitionError,
    TemperaProvider as _ToolProvider,
    _compile_tool,
    _decode_arguments,
)


@dataclass(frozen=True)
class _RegisteredResource:
    uri: str
    name: str
    description: str
    mime_type: str
    function: Callable[..., Any]

    def public_spec(self) -> dict[str, Any]:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


@dataclass(frozen=True)
class _RegisteredPrompt:
    name: str
    description: str
    function: Callable[..., Any]
    compiled: Any

    def public_spec(self) -> dict[str, Any]:
        schema = self.compiled.input_schema
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        arguments = []
        for argument_name in sorted(properties):
            spec = properties[argument_name]
            arguments.append(
                {
                    "name": argument_name,
                    "description": argument_name.replace("_", " "),
                    "required": argument_name in required,
                    "schema": spec,
                }
            )
        return {
            "name": self.name,
            "description": self.description,
            "arguments": arguments,
        }


def _clean_token(value: str, *, label: str) -> str:
    cleaned = value.strip()
    if not cleaned or any(character.isspace() for character in cleaned):
        raise ProviderDefinitionError(f"{label} must be a non-empty token")
    return cleaned


def _resource_contents(resource: _RegisteredResource, result: Any) -> dict[str, Any]:
    if isinstance(result, str):
        return {
            "contents": [
                {
                    "uri": resource.uri,
                    "mimeType": resource.mime_type,
                    "text": result,
                }
            ]
        }
    if isinstance(result, bytes):
        import base64

        return {
            "contents": [
                {
                    "uri": resource.uri,
                    "mimeType": resource.mime_type,
                    "blob": base64.b64encode(result).decode("ascii"),
                }
            ]
        }
    raise ProviderDefinitionError("resource handlers must return str or bytes")


def _prompt_messages(result: Any) -> dict[str, Any]:
    if isinstance(result, str):
        messages = [{"role": "user", "content": {"type": "text", "text": result}}]
    elif isinstance(result, Sequence) and not isinstance(result, (str, bytes, bytearray)):
        messages = []
        for item in result:
            if not isinstance(item, Mapping):
                raise ProviderDefinitionError("prompt message entries must be mappings")
            role = item.get("role")
            content = item.get("content")
            if role not in {"user", "assistant"} or not isinstance(content, Mapping):
                raise ProviderDefinitionError("prompt messages require a user/assistant role and content")
            if content.get("type") != "text" or not isinstance(content.get("text"), str):
                raise ProviderDefinitionError("prompt messages currently support text content only")
            messages.append({"role": role, "content": {"type": "text", "text": content["text"]}})
    else:
        raise ProviderDefinitionError("prompt handlers must return str or a sequence of text messages")
    return {"messages": messages}


class TemperaProvider(_ToolProvider):
    """Typed MCP provider with first-class tools, resources, and prompts."""

    def __init__(self, name: str, *, version: str = "1.0.0") -> None:
        super().__init__(name, version=version)
        self._resources: dict[str, _RegisteredResource] = {}
        self._prompts: dict[str, _RegisteredPrompt] = {}

    def resource(
        self,
        uri: str,
        *,
        name: str | None = None,
        description: str | None = None,
        mime_type: str = "text/plain",
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a static MCP resource.

        Resource handlers intentionally take no arguments in this first contract.
        Parameterized URI templates will be a separate extension because they need
        independent ambiguity and traversal proofs.
        """
        resource_uri = uri.strip()
        if not resource_uri or "://" not in resource_uri:
            raise ProviderDefinitionError("resource URI must be an absolute URI")
        if resource_uri in self._resources:
            raise ProviderDefinitionError(f"duplicate resource URI: {resource_uri}")
        if not mime_type.strip():
            raise ProviderDefinitionError("resource MIME type must not be empty")

        def register(target: Callable[..., Any]) -> Callable[..., Any]:
            if inspect.signature(target).parameters:
                raise ProviderDefinitionError("static resource handlers must not take arguments")
            resource_name = _clean_token(name or target.__name__, label="resource name")
            if any(existing.name == resource_name for existing in self._resources.values()):
                raise ProviderDefinitionError(f"duplicate resource name: {resource_name}")
            resource_description = description or inspect.getdoc(target) or target.__name__.replace("_", " ")
            self._resources[resource_uri] = _RegisteredResource(
                uri=resource_uri,
                name=resource_name,
                description=resource_description,
                mime_type=mime_type.strip(),
                function=target,
            )
            return target

        return register

    def prompt(
        self,
        function: Callable[..., Any] | None = None,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> Callable[..., Any]:
        """Register a typed MCP prompt using the same argument compiler as tools."""

        def register(target: Callable[..., Any]) -> Callable[..., Any]:
            prompt_name = _clean_token(name or target.__name__, label="prompt name")
            if prompt_name in self._prompts:
                raise ProviderDefinitionError(f"duplicate prompt name: {prompt_name}")
            prompt_description = description or inspect.getdoc(target) or target.__name__.replace("_", " ")
            compiled = _compile_tool(
                target,
                name=prompt_name,
                description=prompt_description,
                annotations={},
            )
            self._prompts[prompt_name] = _RegisteredPrompt(
                name=prompt_name,
                description=prompt_description,
                function=target,
                compiled=compiled,
            )
            return target

        if function is None:
            return register
        return register(function)

    def _base_response(self, request: Mapping[str, Any]) -> dict[str, Any] | None:
        method = request.get("method")
        if method == "server/discover":
            capabilities: dict[str, dict[str, Any]] = {"tools": {}}
            if self._resources:
                capabilities["resources"] = {}
            if self._prompts:
                capabilities["prompts"] = {}
            return {
                "resultType": "complete",
                "supportedVersions": ["2026-07-28"],
                "capabilities": capabilities,
                "serverInfo": {"name": self.name, "version": self.version},
                "ttlMs": 0,
                "cacheScope": "private",
            }
        if method == "resources/list":
            return {"resources": [self._resources[uri].public_spec() for uri in sorted(self._resources)]}
        if method == "prompts/list":
            return {"prompts": [self._prompts[name].public_spec() for name in sorted(self._prompts)]}
        return super()._base_response(request)

    def _requested_resource(self, request: Mapping[str, Any]) -> _RegisteredResource:
        params = request.get("params") or {}
        if not isinstance(params, Mapping):
            raise ProviderArgumentError("resources/read params must be an object")
        uri = params.get("uri")
        if not isinstance(uri, str) or uri not in self._resources:
            raise ProviderArgumentError("unknown resource")
        return self._resources[uri]

    def _requested_prompt(self, request: Mapping[str, Any]) -> tuple[_RegisteredPrompt, dict[str, Any]]:
        params = request.get("params") or {}
        if not isinstance(params, Mapping):
            raise ProviderArgumentError("prompts/get params must be an object")
        name = params.get("name")
        if not isinstance(name, str) or name not in self._prompts:
            raise ProviderArgumentError("unknown prompt")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, Mapping):
            raise ProviderArgumentError("prompt arguments must be an object")
        prompt = self._prompts[name]
        return prompt, _decode_arguments(prompt.compiled, arguments)

    def handle(self, request: Mapping[str, Any]) -> dict[str, Any]:
        method = request.get("method")
        if method == "resources/read":
            resource = self._requested_resource(request)
            if inspect.iscoroutinefunction(resource.function):
                raise ProviderDefinitionError("async resource requires handle_async() or run_stdio()")
            try:
                result = resource.function()
            except Exception:
                return {"contents": []}
            if inspect.isawaitable(result):
                if inspect.iscoroutine(result):
                    result.close()
                raise ProviderDefinitionError("resource returned an awaitable from synchronous handle()")
            return _resource_contents(resource, result)
        if method == "prompts/get":
            prompt, decoded = self._requested_prompt(request)
            if inspect.iscoroutinefunction(prompt.function):
                raise ProviderDefinitionError("async prompt requires handle_async() or run_stdio()")
            try:
                result = prompt.function(**decoded)
            except Exception:
                return {"messages": []}
            if inspect.isawaitable(result):
                if inspect.iscoroutine(result):
                    result.close()
                raise ProviderDefinitionError("prompt returned an awaitable from synchronous handle()")
            return _prompt_messages(result)
        base = self._base_response(request)
        if base is not None:
            return base
        return super().handle(request)

    async def handle_async(self, request: Mapping[str, Any]) -> dict[str, Any]:
        method = request.get("method")
        if method == "resources/read":
            resource = self._requested_resource(request)
            try:
                result = resource.function()
                if inspect.isawaitable(result):
                    result = await result
            except Exception:
                return {"contents": []}
            return _resource_contents(resource, result)
        if method == "prompts/get":
            prompt, decoded = self._requested_prompt(request)
            try:
                result = prompt.function(**decoded)
                if inspect.isawaitable(result):
                    result = await result
            except Exception:
                return {"messages": []}
            return _prompt_messages(result)
        base = self._base_response(request)
        if base is not None:
            return base
        return await super().handle_async(request)


__all__ = ["TemperaProvider"]
