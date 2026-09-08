# Tempera SDK for C++

Version `0.12.0`. C++20, header-only, no dependencies, no HTTP client.

C++ has no standard HTTP client before C++26, so — like the Rust and C
packages — this is a **request builder**. It turns
`(product, operation, parameters)` into a fully-described `RequestSpec` —
method, URL, query pairs, headers, JSON or binary body — that you hand to
whatever transport your application already links (cpp-httplib, Boost.Beast,
libcurl, your own socket code). Every product, audience, scope, environment
target, and typed operation comes from [`surface.json`](../../surface.json)
through the generated table in `include/tempera/surface.hpp`, shared verbatim
with the TypeScript, Python, Rust, and C packages.

Hosted Tempera services are in private design-partner access. Onboarding
provides your issuer URL, credentials, environment, and any product-specific
base URLs. Start with the provisioned `staging` environment.

## Layout

| Path | What it is |
|---|---|
| `include/tempera/surface.hpp` | GENERATED `constexpr` tables — never edit by hand |
| `include/tempera/tempera.hpp` | umbrella header; include this one |
| `include/tempera/client.hpp` | `Client::build_request` / `Client::build_binary`, `RequestSpec`, `BuildError` |
| `include/tempera/auth.hpp` | credential store, PKCE (S256), OAuth body builders |
| `include/tempera/error.hpp` | `google.rpc.Status` normalization and its JSON scanner |
| `include/tempera/mcp.hpp` | JSON-RPC 2.0 body builders for the unified MCP gateway |
| `tests/test_tempera.cpp` | conformance loop over every generated operation, plus unit tests |

Regenerate `surface.hpp` with `python3 scripts/gen-sdk-surface.py` from the
repository root; `python3 scripts/gen-sdk-surface.py --check` fails if it is
stale.

## Build and test

With CMake:

```sh
cmake -S packages/cpp -B build/cpp -DCMAKE_BUILD_TYPE=Release
cmake --build build/cpp
ctest --test-dir build/cpp --output-on-failure
```

Without CMake — the package is header-only, so one `c++` invocation builds and
runs the tests:

```sh
c++ -std=c++20 -Wall -Wextra -Werror -pedantic -Ipackages/cpp/include \
    packages/cpp/tests/test_tempera.cpp -o /tmp/tempera-cpp-tests && /tmp/tempera-cpp-tests
```

To use it in your own program there is nothing to build or link: add
`packages/cpp/include` to your include path.

## Usage

```cpp
#include <cstdlib>
#include <iostream>
#include <tempera/tempera.hpp>

int main() {
    // Onboarding provisions the issuer URL, the credential, and the base URLs.
    tempera::Auth auth("https://staging-api.tempera.dev");
    auth.with_api_key(std::getenv("TEMPERA_API_KEY"));

    tempera::Client client;
    client.with_auth(auth).with_base_url("palette", "https://staging-mcp.tempera.dev");

    const auto request = client.build_request(
        "palette", "get_trace", {{"tenant_id", "tenant_1"}, {"trace_id", "trace_1"}});
    if (!request) {
        std::cerr << request.error().message() << "\n";
        return 1;
    }

    std::cout << request.value().method << " " << request.value().full_url() << "\n";
    std::cout << "authorization: " << *request.value().header("authorization") << "\n";
    // Hand method, full_url(), headers and body_json to your own HTTP client here.
    return 0;
}
```

Parameters accept the producer's canonical wire name (`tenantId`) or its
snake_case alias (`tenant_id`), never both. Path parameters substitute into the
URL, declared query keys go to the query string, declared body keys form the
JSON body, and anything undeclared spills to the query on `GET`/`DELETE` and
into the body otherwise — so a new server field is usable before the tables
catch up. The base URL is the explicit override, then the product's `envVar`.

`build_request` returns a `Result<RequestSpec>`: no exceptions are thrown, and
a failure carries a `BuildError` with an `ErrorCode`, the product, the
operation, the field at fault, and a ready-to-log message. Feed error responses
to `tempera::normalize_error_body()` to get one `ApiError` shape (`status`,
`code`, `message`, `reason`, `request_id`) regardless of which supported wire
shape the producer used.

## Types

Everything is a value type with ordinary C++ ownership: `Client` holds its own
copy of the `Auth` you give it, `RequestSpec` owns its strings, and the only
non-owning member is `RequestSpec::method`, a `std::string_view` into the
static generated table. The tables themselves are `constexpr`, so
`tempera::surface::find_operation(...)` and `find_product(...)` are usable in a
`static_assert`.
