# Tempera SDK for C

Version `0.13.0`. C99, no dependencies, no HTTP client.

Like the Rust package, this is a **request builder**. C has no standard HTTP
client, so the library never opens a socket: it turns
`(product, operation, parameters)` into a fully-described request — method,
URL, query pairs, headers, JSON or binary body — that you hand to whatever
transport your application already links (libcurl, an embedded stack, your own
socket code). Every product, audience, scope, environment target, and typed
operation comes from [`surface.json`](../../surface.json) through the generated
tables in `include/tempera/surface.h` and `src/surface.c`, shared verbatim with
the TypeScript, Python, Rust, and C++ packages.

Hosted Tempera services are in private design-partner access. Onboarding
provides your issuer URL, credentials, environment, and any product-specific
base URLs. Start with the provisioned `staging` environment.

## Layout

| Path | What it is |
|---|---|
| `include/tempera/surface.h` | GENERATED table declarations — never edit by hand |
| `src/surface.c` | GENERATED table definitions — never edit by hand |
| `include/tempera/tempera.h` | the hand-written runtime API, and the memory contract |
| `src/client.c` | `tempera_client_build_request` / `tempera_client_build_binary` |
| `src/auth.c` | credential store, PKCE (S256), OAuth body builders |
| `src/error.c`, `src/json.c` | `google.rpc.Status` normalization and its JSON scanner |
| `src/mcp.c` | JSON-RPC 2.0 body builders for the unified MCP gateway |
| `tests/test_tempera.c` | conformance loop over every generated operation, plus unit tests |

Regenerate the two generated files with `python3 scripts/gen-sdk-surface.py`
from the repository root; `python3 scripts/gen-sdk-surface.py --check` fails if
they are stale.

## Build and test

With CMake:

```sh
cmake -S packages/c -B build/c -DCMAKE_BUILD_TYPE=Release
cmake --build build/c
ctest --test-dir build/c --output-on-failure
```

Without CMake — one `cc` invocation builds and links the whole test binary:

```sh
cc -std=c99 -Wall -Wextra -Werror -pedantic -Ipackages/c/include \
   packages/c/tests/test_tempera.c packages/c/src/*.c -o /tmp/tempera-c-tests && /tmp/tempera-c-tests
```

To build just the library as an archive:

```sh
cc -std=c99 -Wall -Wextra -Werror -pedantic -Ipackages/c/include -c packages/c/src/*.c
ar rcs libtempera.a surface.o util.o json.o error.o auth.o client.o mcp.o
```

## Usage

```c
#include <stdio.h>
#include <tempera/tempera.h>

int main(void) {
    /* Onboarding provisions the issuer URL, the credential, and the base URLs. */
    tempera_auth *auth = tempera_auth_new("https://staging-api.tempera.dev");
    tempera_client *client = tempera_client_new();
    tempera_param params[2];
    tempera_request *request = NULL;
    tempera_error error;
    char *url;

    tempera_auth_set_api_key(auth, getenv("TEMPERA_API_KEY"));
    tempera_client_set_auth(client, auth);   /* borrowed: auth outlives client */
    tempera_client_set_base_url(client, "palette", "https://staging-mcp.tempera.dev");

    params[0] = tempera_param_string("tenant_id", "tenant_1");
    params[1] = tempera_param_string("trace_id", "trace_1");

    if (tempera_client_build_request(client, "palette", "get_trace", params, 2, &request,
                                     &error) != TEMPERA_OK) {
        fprintf(stderr, "%s\n", error.detail);
        return 1;
    }

    url = tempera_request_full_url(request);
    printf("%s %s\n", request->method, url);
    printf("authorization: %s\n", tempera_request_header(request, "authorization"));
    /* Hand request->method, url, request->headers and request->body_json to
       your own HTTP client here. */

    tempera_string_free(url);
    tempera_request_free(request);
    tempera_client_free(client);
    tempera_auth_free(auth);
    return 0;
}
```

Parameters accept the producer's canonical wire name (`tenantId`) or its
snake_case alias (`tenant_id`), never both. Path parameters substitute into the
URL, declared query keys go to the query string, declared body keys form the
JSON body, and anything undeclared spills to the query on `GET`/`DELETE` and
into the body otherwise — so a new server field is usable before the tables
catch up. The base URL is the explicit override, then the product's `envVar`.

Feed error responses to `tempera_normalize_error_body()` to get one
`tempera_api_error` shape (`status`, `code`, `message`, `reason`, `request_id`)
regardless of which supported wire shape the producer used.

## Memory

The full contract is documented at the top of `include/tempera/tempera.h`. In
short: everything you pass in is borrowed for the call; every `char *` you get
back is yours and is released with `tempera_string_free()`; every struct with
owned members has a matching `tempera_*_free()`; every `_free()` accepts `NULL`;
pointers into the generated tables are static and never freed; and the only
pointer the library retains is the `tempera_auth` handed to
`tempera_client_set_auth()`, which must outlive the client. There is no global
mutable state.

`tempera_error_message()` maps any `tempera_status` to a stable one-line
description; the `tempera_error` filled in by a failed build additionally
carries a `detail` line naming the product, the operation, and the field.
