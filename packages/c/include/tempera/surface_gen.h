/* GENERATED FROM surface.json by scripts/gen-sdk-go-c.py -- DO NOT EDIT BY HAND. */
#ifndef TEMPERA_SURFACE_GEN_H
#define TEMPERA_SURFACE_GEN_H
#include <stddef.h>
#define TEMPERA_SURFACE_VERSION 6
#define TEMPERA_SDK_VERSION "0.12.0"
typedef struct {
  const char *product, *id, *snake_id, *method, *path, *auth, *auth_audience;
  const char *path_params, *query_params, *required_query, *body_fields, *required_body, *forbidden_body;
  const char *request_body_kind, *request_content_type, *scope, *description;
} tempera_operation_spec;
extern const tempera_operation_spec tempera_operations[];
extern const size_t tempera_operations_count;
const tempera_operation_spec *tempera_find_operation(const char *product, const char *id);
#endif
