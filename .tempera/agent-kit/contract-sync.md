# Tempera contract synchronization

This file is generated into release-path repositories from the canonical
Tempera agent kit. It describes coordination invariants; it is not an API
contract and cannot introduce a route, schema, scope, or product capability.

## Runtime contract order

1. Identify the service that owns the durable resource and transition.
2. Prove handler and canonical OpenAPI/JSON Schema/typed-registry parity.
3. Classify the change as additive, breaking, or internal and record stable
   operation/schema identity, fixtures, auth, tenant/project binding,
   idempotency, pagination, retry/cancellation, migration, rollout, and rollback.
4. Commit the producer source and read its bytes with
   `git show <commit>:<path>`.
5. Record repository, branch, 40-character commit, source path, Git blob,
   content SHA-256, generator name/version, and generated-output digest.
6. Require bidirectional drift: no phantom consumer operations and no missing
   eligible producer operations.
7. Regenerate and test every supported SDK language.
8. Admit only deliberately model-facing MCP tools with source-derived scopes,
   pinned schemas, explicit effects, and guarded execution.
9. Hand independent consumers exact commits, fixtures, and compatibility notes.
10. Run the train at exact SHAs and attach the integration/staging receipt.

## Merge stops

Stop the train for dirty or irreproducible provenance, an unready breaking
consumer, unspecified auth or tenancy, an unreviewed effect boundary, missing
unique-commit accounting, or CI that never ran real steps. Documentation and
agent guidance are derived surfaces and never override producer truth.

## Agent-kit updates

The canonical kit lands through a reviewed coordination-repository PR. Consumer
repositories copy files and a managed `AGENTS.md` block, preserve local text
outside the markers, record exact source/blob/content and output digests in
`.tempera/agent-kit.lock.json`, and run the synchronizer in `check` mode in CI.
