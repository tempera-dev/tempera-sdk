# Contract Train Reference

## Required producer package

- Canonical contract plus runtime parity.
- Stable operation/schema identity and additive/breaking/internal classification.
- Source repo, branch, 40-character commit, path, Git blob, content SHA-256.
- Request, success, and error fixtures.
- Audience/scopes, tenant/project binding, idempotency, pagination, retry/cancellation.
- Durable owner, consumers, migration, rollout, rollback, removal criteria.

## Merge order

```text
producer source/runtime
→ canonical ecosystem lock
→ TypeScript/Python/Rust SDKs
→ curated MCP adapter/fixtures
→ independent Workflows consumer handoff
→ Auth clients/scopes
→ exact-SHA integration manifest
→ staged rollout
→ compatibility contraction
```

Consumers may land dormant before additive providers. Breaking providers wait for review-ready consumers and exact-SHA proof. Skills/docs are derived and cannot authorize a route or scope.
