#!/usr/bin/env python3
"""Generate Go and C SDK surface tables from the canonical surface.json."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sdk_names import snake_case

ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "surface.json"
HEADER = "GENERATED FROM surface.json by scripts/gen-sdk-go-c.py -- DO NOT EDIT BY HAND."


def goq(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def go_slice(values: list[str]) -> str:
    return "[]string{" + ", ".join(goq(v) for v in values) + "}"


def render_go(surface: dict) -> str:
    lines = [
        f"// {HEADER}",
        "package tempera",
        "",
        "type ProductSpec struct { Key, Name, Repository, EnvVar, Audience, Description string }",
        "type OperationSpec struct {",
        "\tID, SnakeID, UpstreamOperationID, Method, Path, Auth, AuthAudience, RequestBodyKind, RequestContentType, Scope, Description string",
        "\tPathParams, Query, RequiredQuery, Body, ForbiddenBody, RequiredBody []string",
        "\tPathParamTemplates map[string]string",
        "\tBodyDefaults map[string]any",
        "}",
        f"const SurfaceVersion = {surface['version']}",
        f"const DefaultAudience = {goq(surface['defaultAudience'])}",
        f"var Audiences = {go_slice(surface['audiences'])}",
        f"var Scopes = {go_slice(surface['scopes'])}",
        "",
        "var Products = map[string]ProductSpec{",
    ]
    for key, p in surface["products"].items():
        lines.append(f"\t{goq(key)}: {{Key:{goq(key)}, Name:{goq(p['name'])}, Repository:{goq(p['repository'])}, EnvVar:{goq(p['envVar'])}, Audience:{goq(p.get('audience') or '')}, Description:{goq(p['description'])}}},")
    lines += ["}", "", "var Operations = map[string][]OperationSpec{"]
    for product, ops in surface["operations"].items():
        lines.append(f"\t{goq(product)}: {{")
        for op in ops:
            templates = "map[string]string{" + ", ".join(f"{goq(k)}:{goq(v)}" for k, v in op.get("pathParamTemplates", {}).items()) + "}"
            defaults = "map[string]any{" + ", ".join(f"{goq(k)}:{goq(v)}" for k, v in op.get("bodyDefaults", {}).items()) + "}"
            lines.append("\t\t{" + ", ".join([
                f"ID:{goq(op['id'])}", f"SnakeID:{goq(snake_case(op['id']))}", f"UpstreamOperationID:{goq(op['upstreamOperationId'])}",
                f"Method:{goq(op['method'])}", f"Path:{goq(op['path'])}", f"Auth:{goq(op['auth'])}", f"AuthAudience:{goq(op.get('authAudience') or '')}",
                f"RequestBodyKind:{goq(op.get('requestBodyKind','none'))}", f"RequestContentType:{goq(op.get('requestContentType') or '')}", f"Scope:{goq(op.get('scope') or '')}", f"Description:{goq(op['description'])}",
                f"PathParams:{go_slice(op.get('pathParams',[]))}", f"Query:{go_slice(op.get('query',[]))}", f"RequiredQuery:{go_slice(op.get('requiredQuery',[]))}",
                f"Body:{go_slice(op.get('body',[]))}", f"ForbiddenBody:{go_slice(op.get('forbiddenBody',[]))}", f"RequiredBody:{go_slice(op.get('requiredBody',[]))}",
                f"PathParamTemplates:{templates}", f"BodyDefaults:{defaults}",
            ]) + "},")
        lines.append("\t},")
    lines += [
        "}", "",
        "func FindOperation(product, id string) (OperationSpec, bool) {",
        "\tfor _, op := range Operations[product] { if op.ID == id || op.SnakeID == id { return op, true } }",
        "\treturn OperationSpec{}, false",
        "}", "",
    ]
    return "\n".join(lines)


def cq(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def joined(values: list[str]) -> str:
    return "|".join(values)


def render_c_h(surface: dict) -> str:
    return f'''/* {HEADER} */
#ifndef TEMPERA_SURFACE_GEN_H
#define TEMPERA_SURFACE_GEN_H
#include <stddef.h>
#define TEMPERA_SURFACE_VERSION {surface['version']}
#define TEMPERA_SDK_VERSION "0.12.0"
typedef struct {{
  const char *product, *id, *snake_id, *method, *path, *auth, *auth_audience;
  const char *path_params, *query_params, *required_query, *body_fields, *required_body, *forbidden_body;
  const char *request_body_kind, *request_content_type, *scope, *description;
}} tempera_operation_spec;
extern const tempera_operation_spec tempera_operations[];
extern const size_t tempera_operations_count;
const tempera_operation_spec *tempera_find_operation(const char *product, const char *id);
#endif
'''


def render_c_c(surface: dict) -> str:
    lines = [f"/* {HEADER} */", '#include "tempera/surface_gen.h"', "#include <string.h>", "", "const tempera_operation_spec tempera_operations[] = {"]
    for product, ops in surface["operations"].items():
        for op in ops:
            fields = [product, op["id"], snake_case(op["id"]), op["method"], op["path"], op["auth"], op.get("authAudience") or "",
                      joined(op.get("pathParams", [])), joined(op.get("query", [])), joined(op.get("requiredQuery", [])), joined(op.get("body", [])),
                      joined(op.get("requiredBody", [])), joined(op.get("forbiddenBody", [])), op.get("requestBodyKind", "none"), op.get("requestContentType") or "",
                      op.get("scope") or "", op["description"]]
            lines.append("  {" + ", ".join(cq(v) for v in fields) + "},")
    lines += ["};", "const size_t tempera_operations_count = sizeof(tempera_operations)/sizeof(tempera_operations[0]);", "",
              "const tempera_operation_spec *tempera_find_operation(const char *product, const char *id) {",
              "  size_t i; if (!product || !id) return NULL;",
              "  for (i=0; i<tempera_operations_count; ++i) { const tempera_operation_spec *op=&tempera_operations[i]; if (strcmp(op->product,product)==0 && (strcmp(op->id,id)==0 || strcmp(op->snake_id,id)==0)) return op; }",
              "  return NULL;", "}", ""]
    return "\n".join(lines)


def outputs(surface: dict) -> dict[Path, str]:
    return {
        ROOT / "packages/go/surface_gen.go": render_go(surface),
        ROOT / "packages/c/include/tempera/surface_gen.h": render_c_h(surface),
        ROOT / "packages/c/src/surface_gen.c": render_c_c(surface),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    surface = json.loads(SURFACE.read_text(encoding="utf-8"))
    stale = []
    for path, content in outputs(surface).items():
        content = content.rstrip() + "\n"
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if stale:
        print("stale Go/C generated surfaces: " + ", ".join(stale))
        return 1
    if args.check:
        print("Go/C generated surfaces match surface.json")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
