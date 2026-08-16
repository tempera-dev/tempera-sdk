#!/usr/bin/env python3
"""Make the shared auth runtime transport-neutral without changing authority semantics."""

from pathlib import Path

CARGO = Path("packages/auth-rust/Cargo.toml")
LIB = Path("packages/auth-rust/src/lib.rs")
README = Path("packages/auth-rust/README.md")

cargo = CARGO.read_text(encoding="utf-8")
old = '''[workspace]\n\n[dependencies]\nasync-trait = "0.1"\nbase64 = "0.22"\nfutures-util = "0.3"\njsonwebtoken = { version = "=10.4.0", default-features = false, features = ["aws_lc_rs"] }\nreqwest = { version = "0.13.2", default-features = false, features = ["json", "rustls", "stream"] }\n'''
new = '''[workspace]\n\n[features]\ndefault = ["reqwest-transport"]\nreqwest-transport = ["dep:futures-util", "dep:reqwest"]\n\n[dependencies]\nasync-trait = "0.1"\nbase64 = "0.22"\nfutures-util = { version = "0.3", optional = true }\njsonwebtoken = { version = "=10.4.0", default-features = false, features = ["aws_lc_rs"] }\nreqwest = { version = "0.13.2", default-features = false, features = ["json", "rustls", "stream"], optional = true }\n'''
if cargo.count(old) != 1:
    raise SystemExit(f"Cargo dependency shape changed: {cargo.count(old)}")
CARGO.write_text(cargo.replace(old, new, 1), encoding="utf-8")

text = LIB.read_text(encoding="utf-8")
text = text.replace(
    'use futures_util::StreamExt as _;\n',
    '#[cfg(feature = "reqwest-transport")]\nuse futures_util::StreamExt as _;\n',
    1,
)
text = text.replace(
    'use reqwest::header;\n',
    '#[cfg(feature = "reqwest-transport")]\nuse reqwest::header;\n',
    1,
)

old_transport = '''/// Reqwest-backed authority transport with bounded responses and no redirects.\n#[derive(Clone)]\npub struct ReqwestAuthorityTransport {\n    client: reqwest::Client,\n}\n\nimpl ReqwestAuthorityTransport {\n'''
new_transport = '''/// Reqwest-backed authority transport with bounded responses and no redirects.\n#[cfg(feature = "reqwest-transport")]\n#[derive(Clone)]\npub struct ReqwestAuthorityTransport {\n    client: reqwest::Client,\n}\n\n/// Marker type retained when the built-in HTTP transport is disabled.\n///\n/// Consumers using `default-features = false` provide their own\n/// [`AuthorityTransport`] implementation and construct [`HybridAuthorizer`]\n/// through `with_transport`.\n#[cfg(not(feature = "reqwest-transport"))]\n#[derive(Clone, Copy, Debug)]\npub enum ReqwestAuthorityTransport {}\n\n#[cfg(feature = "reqwest-transport")]\nimpl ReqwestAuthorityTransport {\n'''
if text.count(old_transport) != 1:
    raise SystemExit(f"Reqwest transport shape changed: {text.count(old_transport)}")
text = text.replace(old_transport, new_transport, 1)
text = text.replace(
    'impl Default for ReqwestAuthorityTransport {\n',
    '#[cfg(feature = "reqwest-transport")]\nimpl Default for ReqwestAuthorityTransport {\n',
    1,
)
text = text.replace(
    '#[async_trait]\nimpl AuthorityTransport for ReqwestAuthorityTransport {\n',
    '#[cfg(feature = "reqwest-transport")]\n#[async_trait]\nimpl AuthorityTransport for ReqwestAuthorityTransport {\n',
    1,
)
text = text.replace(
    'impl HybridAuthorizer<ReqwestAuthorityTransport> {\n',
    '#[cfg(feature = "reqwest-transport")]\nimpl HybridAuthorizer<ReqwestAuthorityTransport> {\n',
    1,
)
text = text.replace(
    'fn json_content_type(headers: &reqwest::header::HeaderMap) -> bool {\n',
    '#[cfg(feature = "reqwest-transport")]\nfn json_content_type(headers: &reqwest::header::HeaderMap) -> bool {\n',
    1,
)
text = text.replace(
    'async fn bounded_response_bytes(\n',
    '#[cfg(feature = "reqwest-transport")]\nasync fn bounded_response_bytes(\n',
    1,
)
LIB.write_text(text, encoding="utf-8")

readme = README.read_text(encoding="utf-8")
addition = '''\n## Transport boundary\n\nThe default `reqwest-transport` feature provides a hardened no-redirect HTTP client. Services that already own an HTTP/TLS stack can depend on `tempera-auth-runtime` with `default-features = false`, implement `AuthorityTransport`, and reuse their existing connection pool. Local JWT, JWKS, cache, singleflight, scope, audience, and central-freshness semantics remain inside this crate; only network I/O is injected. This avoids duplicate HTTP/TLS dependency graphs and duplicate connection pools in resource-server binaries.\n'''
if "## Transport boundary" not in readme:
    readme += addition
README.write_text(readme, encoding="utf-8")
print("made auth runtime transport optional")
