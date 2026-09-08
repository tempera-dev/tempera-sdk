// Dependency-free Tempera SDK for C++ (C++20), header-only.
//
// The library is HTTP-less by design, exactly like packages/rust and
// packages/c: it builds request URLs, query pairs, headers, and bodies for the
// caller's own HTTP client instead of sending them. Every product, audience,
// scope, environment target, and typed operation comes from the generated
// tables in tempera/surface.hpp (rendered from surface.json), shared verbatim
// with the TypeScript, Python, Rust, and C packages.
//
//   tempera/surface.hpp  the generated tables. GENERATED -- never edit by hand.
//   tempera/client.hpp   Client turns (product, operation, params) into a
//                        RequestSpec, and reports failures as a BuildError.
//   tempera/auth.hpp     PKCE (S256) helpers, audience-aware OAuth request
//                        builders, and the per-audience credential store with
//                        tp_ API-key fallback.
//   tempera/error.hpp    ApiError and normalize_error_body, folding the
//                        canonical AIP-193 envelope and the supported
//                        compatibility shapes into one type.
//   tempera/mcp.hpp      JSON-RPC 2.0 body builders for the MCP gateway.
//
// Include this header to get all of them.

#ifndef TEMPERA_TEMPERA_HPP
#define TEMPERA_TEMPERA_HPP

#include <string_view>

#include "tempera/auth.hpp"
#include "tempera/client.hpp"
#include "tempera/error.hpp"
#include "tempera/mcp.hpp"
#include "tempera/surface.hpp"

namespace tempera {

/// Package version; identical across every Tempera SDK language package.
inline constexpr std::string_view SDK_VERSION = "0.12.0";

}  // namespace tempera

#endif  // TEMPERA_TEMPERA_HPP
