#!/usr/bin/env bash
set -euo pipefail

python3 scripts/harden-hybrid-auth-runtime.py
python3 - <<'PY'
from pathlib import Path

hardening = Path("packages/auth-rust/tests/hardening.rs")
text = hardening.read_text()
if not text.startswith("//!"):
    hardening.write_text(
        "//! Adversarial configuration tests for the hybrid authorization runtime.\n\n" + text
    )

hybrid = Path("packages/auth-rust/tests/hybrid.rs")
text = hybrid.read_text().replace("http://auth.test", "http://127.0.0.1:8080")
needle = "    let secure = Config::new("
if text.count(needle) != 1:
    raise SystemExit("secure fixture declaration: expected exactly one match")
text = text.replace(needle, "    let mut secure = Config::new(", 1)
needle = "    );\n    assert!(secure.validate().is_ok());"
replacement = (
    "    );\n"
    "    secure.introspection_secret = Some(\"resource-server-secret\".into());\n"
    "    assert!(secure.validate().is_ok());"
)
if text.count(needle) != 1:
    raise SystemExit("secure fixture assertion: expected exactly one match")
hybrid.write_text(text.replace(needle, replacement, 1))
PY

cargo fmt --manifest-path packages/auth-rust/Cargo.toml --all
cargo clippy --manifest-path packages/auth-rust/Cargo.toml --locked --all-targets --all-features -- -D warnings
