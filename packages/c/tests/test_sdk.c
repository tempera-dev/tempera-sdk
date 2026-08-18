#include "tempera/tempera.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

static void test_surface_lookup(void) {
  const tempera_operation_spec *op = tempera_find_operation("tempo", "observe");
  assert(op != NULL);
  assert(strcmp(op->product, "tempo") == 0);
  assert(strcmp(op->id, "observe") == 0);
  assert(op->method != NULL && op->method[0] != '\0');
  assert(op->path != NULL && op->path[0] == '/');
}

static void test_browser_requests(void) {
  tempera_browser_task task;
  tempera_request_spec request;
  assert(tempera_browser_task_attach(&task, "https://tempo.example", "token", "session-1") == TEMPERA_OK);
  assert(task.state == TEMPERA_BROWSER_OPEN);
  assert(tempera_browser_observe_request(&task, &request) == TEMPERA_OK);
  assert(strcmp(request.method, "GET") == 0);
  assert(strcmp(request.authorization, "Bearer token") == 0);
  assert(strcmp(request.url, "https://tempo.example/v1/sessions/session-1:observe") == 0);
  assert(tempera_browser_act_batch_request(&task, "[{\"kind\":\"scroll\",\"y\":1}]", &request) == TEMPERA_OK);
  assert(strcmp(request.method, "POST") == 0);
  assert(strcmp(request.url, "https://tempo.example/v1/sessions/session-1:actBatch") == 0);
  assert(strstr(request.body, "\"batch\"") != NULL);
  assert(strstr(request.body, "\"actions\"") == NULL);
  assert(tempera_browser_close_request(&task, &request) == TEMPERA_OK);
  assert(strcmp(request.method, "DELETE") == 0);
  assert(strcmp(request.url, "https://tempo.example/v1/sessions/session-1") == 0);
  assert(task.state == TEMPERA_BROWSER_CLOSING);
  tempera_browser_reopen_after_close_failure(&task);
  assert(task.state == TEMPERA_BROWSER_OPEN);
  assert(tempera_browser_close_request(&task, &request) == TEMPERA_OK);
  tempera_browser_mark_closed(&task);
  assert(task.state == TEMPERA_BROWSER_CLOSED);
  assert(tempera_browser_observe_request(&task, &request) == TEMPERA_ESTATE);
}

static void test_capacity_fails_closed(void) {
  tempera_request_spec request;
  char huge[70000];
  memset(huge, 'x', sizeof(huge) - 1);
  huge[sizeof(huge) - 1] = '\0';
  assert(tempera_build_request("https://tempo.example", "token", "tempo", "health", NULL, 0, NULL, huge, &request) == TEMPERA_ECAPACITY);
}

int main(void) {
  test_surface_lookup();
  test_browser_requests();
  test_capacity_fails_closed();
  puts("tempera C SDK tests passed");
  return 0;
}
