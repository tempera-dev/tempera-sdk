# WebAuthn wire contract

Auth Hub passkey finish operations carry WebAuthn assertion or attestation objects defined by the WebAuthn protocol. Fields such as `clientDataJSON` and `authenticatorData` retain their standards-defined spelling on the wire and are therefore narrow JSON-field exceptions to the SDK's generic AIP-127 lower-camel resource-message ratchet.

The exception applies only to the WebAuthn finish request payloads. Route versioning, HTTP method semantics, list pagination, errors, authentication metadata, and the rest of the control-plane OpenAPI surface remain subject to the normal AIP and exact-source checks.
