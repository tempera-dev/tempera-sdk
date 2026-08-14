# `tempera-auth-runtime`

A small resource-server authorization runtime for Tempera services.

It combines two checks instead of forcing a service to choose between them:

1. **Local JWT verification** rejects malformed or forged access tokens without an Auth Hub round trip. It requires a bounded RS256 header, exact issuer and audience, a known JWKS `kid`, signature validity, temporal claims, subject/JTI, workspace claims, and scopes.
2. **Central freshness** confirms the locally verified access token through Auth Hub introspection on cache miss. Opaque API keys always take this path. Positive decisions are cached for at most five seconds by default, bounding role, grant, epoch, and revocation staleness.

Concurrent misses for the same token are singleflighted. Cache and flight keys are SHA-256 digests; raw bearer values are never retained as map keys, metrics labels, or log fields.

```rust
use tempera_auth_runtime::{Config, HybridAuthorizer};

let mut config = Config::new(
    "https://api.tempera.dev",
    "tempera-document",
    "https://api.tempera.dev/.well-known/jwks.json",
    "https://api.tempera.dev/v1/oauth/introspect",
);
config.introspection_secret = Some(std::env::var("TEMPERA_TOKEN_INTROSPECTION_SECRET")?);
let authorizer = HybridAuthorizer::new(config)?;

let principal = authorizer
    .authorize(bearer, &["document:read"])
    .await?;
```

## Failure behavior

- A malformed, forged, expired, wrong-issuer, or wrong-audience JWT fails locally.
- An inactive centrally introspected credential fails as invalid.
- A local/central claim disagreement fails closed.
- Auth Hub or JWKS transport failures fail as unavailable when no fresh positive decision exists.
- The runtime does not use stale-on-error authorization.
- API keys are never parsed as JWTs and are never accepted without central introspection.

The package exposes counters for cache hits/misses, local JWT rejection, introspection, authority failure, and claim mismatch. These counters contain no credential or tenant identifiers.
