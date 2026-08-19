#include "tempera/tempera.h"

#include <stdio.h>
#include <string.h>

static int copy_checked(char *dst, size_t cap, const char *src) {
  size_t n;
  if (!dst || !src || cap == 0) return TEMPERA_EINVAL;
  n = strlen(src);
  if (n >= cap) return TEMPERA_ECAPACITY;
  memcpy(dst, src, n + 1);
  return TEMPERA_OK;
}

static int append_checked(char *dst, size_t cap, const char *src) {
  size_t used, n;
  if (!dst || !src || cap == 0) return TEMPERA_EINVAL;
  used = strlen(dst); n = strlen(src);
  if (used + n >= cap) return TEMPERA_ECAPACITY;
  memcpy(dst + used, src, n + 1);
  return TEMPERA_OK;
}

static const char *find_param(const tempera_param *params, size_t count, const char *name) {
  size_t i;
  if (!name) return NULL;
  for (i = 0; i < count; ++i) {
    if (params[i].name && strcmp(params[i].name, name) == 0) return params[i].value;
  }
  return NULL;
}

static int substitute_path(char *dst, size_t cap, const char *path, const tempera_param *params, size_t count) {
  const char *p = path;
  dst[0] = '\0';
  while (*p) {
    const char *open = strchr(p, '{');
    if (!open) return append_checked(dst, cap, p);
    if ((size_t)(open - p) + strlen(dst) >= cap) return TEMPERA_ECAPACITY;
    strncat(dst, p, (size_t)(open - p));
    {
      const char *close = strchr(open + 1, '}');
      char name[128]; const char *value; size_t n;
      if (!close) return TEMPERA_EINVAL;
      n = (size_t)(close - open - 1);
      if (n == 0 || n >= sizeof(name)) return TEMPERA_EINVAL;
      memcpy(name, open + 1, n); name[n] = '\0';
      value = find_param(params, count, name);
      if (!value || !*value) return TEMPERA_EINVAL;
      /* Resource-name structural slashes are intentionally caller-preserved.
         Higher-level language SDKs validate AIP resource templates before this
         transport-neutral C layer; plain identifiers should already be escaped. */
      if (append_checked(dst, cap, value) != TEMPERA_OK) return TEMPERA_ECAPACITY;
      p = close + 1;
    }
  }
  return TEMPERA_OK;
}

int tempera_build_request(
    const char *base_url,
    const char *bearer,
    const char *product,
    const char *operation,
    const tempera_param *path_params,
    size_t path_param_count,
    const char *query_string,
    const char *body_json,
    tempera_request_spec *out) {
  const tempera_operation_spec *op;
  char path[2048];
  size_t n;
  int rc;
  if (!base_url || !product || !operation || !out) return TEMPERA_EINVAL;
  op = tempera_find_operation(product, operation);
  if (!op) return TEMPERA_ENOTFOUND;
  memset(out, 0, sizeof(*out));
  rc = copy_checked(out->method, sizeof(out->method), op->method); if (rc) return rc;
  rc = substitute_path(path, sizeof(path), op->path, path_params, path_param_count); if (rc) return rc;
  rc = copy_checked(out->url, sizeof(out->url), base_url); if (rc) return rc;
  n = strlen(out->url); while (n > 0 && out->url[n - 1] == '/') out->url[--n] = '\0';
  rc = append_checked(out->url, sizeof(out->url), path); if (rc) return rc;
  if (query_string && *query_string) {
    rc = append_checked(out->url, sizeof(out->url), "?"); if (rc) return rc;
    rc = append_checked(out->url, sizeof(out->url), query_string); if (rc) return rc;
  }
  if (bearer && *bearer && strcmp(op->auth, "none") != 0) {
    rc = copy_checked(out->authorization, sizeof(out->authorization), "Bearer "); if (rc) return rc;
    rc = append_checked(out->authorization, sizeof(out->authorization), bearer); if (rc) return rc;
  }
  if (body_json && *body_json) {
    rc = copy_checked(out->body, sizeof(out->body), body_json); if (rc) return rc;
    rc = copy_checked(out->content_type, sizeof(out->content_type), "application/json"); if (rc) return rc;
  }
  return TEMPERA_OK;
}

int tempera_browser_task_attach(tempera_browser_task *task, const char *base_url, const char *bearer, const char *session_id) {
  if (!task || !base_url || !session_id || !*session_id) return TEMPERA_EINVAL;
  memset(task, 0, sizeof(*task));
  task->base_url = base_url; task->bearer = bearer; task->state = TEMPERA_BROWSER_OPEN;
  return copy_checked(task->session_id, sizeof(task->session_id), session_id);
}

int tempera_browser_observe_request(const tempera_browser_task *task, tempera_request_spec *out) {
  tempera_param p;
  if (!task || task->state != TEMPERA_BROWSER_OPEN) return TEMPERA_ESTATE;
  p.name = "sessionId"; p.value = task->session_id;
  return tempera_build_request(task->base_url, task->bearer, "tempo", "observe", &p, 1, NULL, NULL, out);
}

int tempera_browser_act_batch_request(const tempera_browser_task *task, const char *batch_json, tempera_request_spec *out) {
  tempera_param p; char body[65536]; int written;
  if (!task || task->state != TEMPERA_BROWSER_OPEN || !batch_json || !*batch_json) return TEMPERA_EINVAL;
  p.name = "sessionId"; p.value = task->session_id;
  written = snprintf(body, sizeof(body), "{\"batch\":%s}", batch_json);
  if (written < 0 || (size_t)written >= sizeof(body)) return TEMPERA_ECAPACITY;
  return tempera_build_request(task->base_url, task->bearer, "tempo", "actBatch", &p, 1, NULL, body, out);
}

int tempera_browser_close_request(tempera_browser_task *task, tempera_request_spec *out) {
  tempera_param p; int rc;
  if (!task || task->state != TEMPERA_BROWSER_OPEN) return TEMPERA_ESTATE;
  task->state = TEMPERA_BROWSER_CLOSING;
  p.name = "sessionId"; p.value = task->session_id;
  rc = tempera_build_request(task->base_url, task->bearer, "tempo", "closeSession", &p, 1, NULL, NULL, out);
  if (rc != TEMPERA_OK) task->state = TEMPERA_BROWSER_OPEN;
  return rc;
}

void tempera_browser_mark_closed(tempera_browser_task *task) { if (task) task->state = TEMPERA_BROWSER_CLOSED; }
void tempera_browser_reopen_after_close_failure(tempera_browser_task *task) { if (task && task->state == TEMPERA_BROWSER_CLOSING) task->state = TEMPERA_BROWSER_OPEN; }
