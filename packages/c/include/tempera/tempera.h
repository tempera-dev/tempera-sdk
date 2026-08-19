#ifndef TEMPERA_H
#define TEMPERA_H

#include <stddef.h>
#include "tempera/surface_gen.h"

#ifdef __cplusplus
extern "C" {
#endif

#define TEMPERA_OK 0
#define TEMPERA_EINVAL 1
#define TEMPERA_ENOTFOUND 2
#define TEMPERA_ECAPACITY 3
#define TEMPERA_ESTATE 4

typedef struct {
  const char *name;
  const char *value;
} tempera_param;

typedef struct {
  char method[8];
  char url[4096];
  char authorization[4096];
  char content_type[128];
  char body[65536];
} tempera_request_spec;

typedef enum {
  TEMPERA_BROWSER_OPEN = 0,
  TEMPERA_BROWSER_CLOSING = 1,
  TEMPERA_BROWSER_CLOSED = 2
} tempera_browser_state;

typedef struct {
  const char *base_url;
  const char *bearer;
  char session_id[256];
  tempera_browser_state state;
} tempera_browser_task;

int tempera_build_request(
    const char *base_url,
    const char *bearer,
    const char *product,
    const char *operation,
    const tempera_param *path_params,
    size_t path_param_count,
    const char *query_string,
    const char *body_json,
    tempera_request_spec *out);

int tempera_browser_task_attach(tempera_browser_task *task, const char *base_url, const char *bearer, const char *session_id);
int tempera_browser_observe_request(const tempera_browser_task *task, tempera_request_spec *out);
int tempera_browser_act_batch_request(const tempera_browser_task *task, const char *actions_json, tempera_request_spec *out);
int tempera_browser_close_request(tempera_browser_task *task, tempera_request_spec *out);
void tempera_browser_mark_closed(tempera_browser_task *task);
void tempera_browser_reopen_after_close_failure(tempera_browser_task *task);

#ifdef __cplusplus
}
#endif
#endif
