# `tempera-auth-runtime`

A bounded resource-server authorization runtime for Tempera services.

It combines two checks instead of forcing a service to choose between low latency and current authority:

1. **Local JWT verification** rejects malformed or forged access tokens without an Auth Hub round trip. It requires RS256, a bounded JOSE header, an exact issuer and audience, a known JWKS `kid`, a valid signature, bounded temporal claims, a subject/JTI, workspace claims, and syntactically valid scopes.
2. **Central freshness** confirms the locally verified access token through Auth Hub introspection on cache miss. Opaque API keys always take this path. Positive decisions are cached for at most five seconds by default, bounding role, grant, security-epoch, and revocation staleness.

Concurrent misses for the same token are singleflighted. Cache and flight keys are SHA-256 digests; raw bearer values are never retained as map keys, metric labels, or log fields.

```rust
use tempera_auth_runtime::{Config, HybridAuthorizer};

let mut config = Config::new(
    "https://api.tempera.dev",
    "tempera-document",
    "https://api.tempera.dev/.well-known/jwks.json",
    "https://api.tempera.dev/v1/oauth/introspect",
);
config.introspection_secret = Some(std::env::var(
    "TEMPERA_TOKEN_INTROSPECTION_SECRET",
)?);
let authorizer = HybridAuthorizer::new(config)?;

let principal = authorizer
    .authorize(bearer, &["document:read"])
    .await?;
```

## Authority invariants

- The issuer, JWKS, and introspection endpoints must share the same scheme, host, and effective port.
- Hosted authority endpoints require HTTPS and a resource-server introspection secret.
- Plain HTTP is accepted only for explicit loopback development (`localhost`, `127.0.0.0/8`, or `::1`) when `allow_insecure_http` is enabled.
- Access tokens require integer `iat` and `exp` claims. Their lifetime is bounded to one hour by default and is configurable only within the runtime's safety limits.
- Future issuance, expired tokens, malformed claim types, malformed scope collections, oversized values, and local/central authority disagreement fail closed.
- JWKS and introspection responses are size-bounded, redirects are disabled, and the runtime never authorizes from stale-on-error state.

## Failure behavior

- A malformed, forged, expired, wrong-issuer, or wrong-audience JWT fails locally.
- An inactive centrally introspected credential fails as invalid.
- A local/central claim disagreement fails closed.
- Auth Hub or JWKS transport failures fail as unavailable when no fresh positive decision exists.
- API keys are never parsed as JWTs and are never accepted without central introspection.
- Scope checks are repeated for each operation, including positive-cache hits.
- Exactly one resource audience is accepted, and duplicate claim aliases must agree.
- Cache hits inspect only the requested entry; expiry sweeping remains off the hot path.

## Operational guidance

The default five-second positive cache is the maximum revocation-freshness window for repeated traffic handled by one process. Services may reduce it, but cannot configure it above the runtime's hard safety ceiling. High-risk operations can bypass application-level request caching and should still require their narrow operation scopes.

The package exposes privacy-safe counters for cache hits/misses, local JWT rejection, central introspection, authority failure, and claim mismatch. These counters contain no credential or tenant identifiers.
