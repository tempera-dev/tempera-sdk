"""Bundle file-local producer schemas; the caller supplies committed bytes only."""
from __future__ import annotations

import json
import re
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"ambiguous duplicate JSON key: {key}")
        result[key] = value
    return result


def pointer(document, fragment):
    if re.search(r"%(?![0-9a-fA-F]{2})", fragment):
        raise ValueError(f"invalid percent escape in JSON Pointer: {fragment}")
    fragment = unquote(fragment, errors="strict")
    if not fragment:
        return document
    if not fragment.startswith("/"):
        raise ValueError(f"unsupported reference anchor: {fragment}")
    value = document
    for encoded in fragment[1:].split("/"):
        if re.search(r"~(?![01])", encoded):
            raise ValueError(f"invalid JSON Pointer escape: {encoded}")
        key = encoded.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict) and key in value:
            value = value[key]
        elif isinstance(value, list) and re.fullmatch(r"0|[1-9][0-9]*", key):
            if int(key) >= len(value):
                raise ValueError(f"JSON Pointer index out of range: {fragment}")
            value = value[int(key)]
        else:
            raise ValueError(f"unresolved JSON Pointer: {fragment}")
    return value


def relative_path(current, path):
    # URI decoding of paths is intentionally unsupported; accept only literal
    # repository paths, with parent steps contained within the repository.
    if not path or any(c in path for c in ("%", "\\", "\x00", ":")) or path.startswith("/"):
        raise ValueError(f"unsupported local reference path: {path!r}")
    parts = list(PurePosixPath(current).parent.parts)
    for part in path.split("/"):
        if part in ("", "."):
            raise ValueError(f"ambiguous local reference path: {path!r}")
        if part == "..":
            if not parts:
                raise ValueError(f"reference escapes producer repository: {path!r}")
            parts.pop()
        else:
            parts.append(part)
    result = "/".join(parts)
    if not result.endswith(".json"):
        raise ValueError(f"unsupported referenced file type: {result}")
    return result


def bundle(root, source_path, read_file):
    """Preserve root pointers; inline imported JSON schemas and their pointers.

    read_file(path) must validate path/mode/commit/branch equivalence and return
    immutable committed bytes. No filesystem or network I/O is performed here.
    """
    documents = {source_path: root}
    nodes = 0

    def document(path):
        if path not in documents:
            data = read_file(path)
            if len(data) > 8 * 1024 * 1024 or len(documents) >= 64:
                raise ValueError("schema bundle source limit exceeded")
            documents[path] = json.loads(data, object_pairs_hook=strict_object,
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON: {value}")))
        return documents[path]

    def walk(value, current, stack, depth=0, top=False, ancestors=()):
        nonlocal nodes
        nodes += 1
        if depth > 128 or nodes > 100000:
            raise ValueError("schema bundle expansion limit exceeded")
        if isinstance(value, list):
            if id(value) in ancestors:
                raise ValueError("cyclic in-memory schema structure")
            return [walk(item, current, stack, depth + 1, ancestors=ancestors + (id(value),))
                    for item in value]
        if not isinstance(value, dict):
            return value
        if id(value) in ancestors:
            raise ValueError("cyclic in-memory schema structure")
        if any(key in value for key in ("$dynamicRef", "$recursiveRef", "$anchor", "$dynamicAnchor", "$recursiveAnchor")):
            raise ValueError("unsupported dynamic or anchored schema reference")
        if "$id" in value and not top:
            raise ValueError("unsupported nested schema $id changes reference scope")
        if "$ref" in value:
            ref = value["$ref"]
            if not isinstance(ref, str):
                raise ValueError("schema $ref must be a string")
            uri = urlsplit(ref)
            if uri.scheme or uri.netloc or uri.query:
                raise ValueError(f"remote/file/query reference forbidden: {ref}")
            if uri.path and current != source_path and "$id" in document(current):
                raise ValueError("ambiguous file reference under schema $id")
            target_path = relative_path(current, uri.path) if uri.path else current
            target = pointer(document(target_path), uri.fragment)
            # Root-local recursive components remain legal local references;
            # only imported expansion cycles are rejected.
            if target_path == source_path and current == source_path and not uri.path:
                return {key: item if key == "$ref" else walk(item, current, stack, depth + 1,
                                                               ancestors=ancestors + (id(value),))
                        for key, item in value.items()}
            identity = (target_path, unquote(uri.fragment, errors="strict"))
            if identity in stack:
                raise ValueError(f"cyclic schema expansion: {target_path}#{uri.fragment}")
            if not isinstance(target, (dict, bool)):
                raise ValueError(f"reference does not select a schema: {ref}")
            expanded = walk(target, target_path, stack + (identity,), depth + 1,
                            top=not uri.fragment, ancestors=ancestors + (id(value),))
            siblings = {key: walk(item, current, stack, depth + 1,
                                  ancestors=ancestors + (id(value),))
                        for key, item in value.items() if key != "$ref"}
            # JSON Schema $ref siblings are conjunctive, never overrides.
            return {"allOf": [expanded, siblings]} if siblings else expanded
        # Annotation payloads can contain literal $ref strings; they are data.
        return {key: item if key in ("example", "examples", "default", "const", "enum")
                else walk(item, current, stack, depth + 1, ancestors=ancestors + (id(value),))
                for key, item in value.items()}

    return walk(root, source_path, (), top=True)
