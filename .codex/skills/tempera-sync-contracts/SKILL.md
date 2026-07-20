---
name: tempera-sync-contracts
description: Keep Tempera runtime APIs, OpenAPI/JSON Schema, aggregate TypeScript/Python/Rust SDKs, MCP tools, Workflows locks, scopes, and shared agent-kit files synchronized. Use for any public route/schema/scope change, upstream refresh, generated client update, drift failure, vendored contract, or AGENTS/SKILL synchronization.
---

# Tempera Contract Sync

Synchronize from authoritative committed source to derived consumers. Never use a skill or hand-written operation table as the API source of truth.

## Classify the sync

- **Runtime contract:** handler/schema → canonical OpenAPI/JSON Schema/typed registry → exact source lock → SDK → curated MCP → Workflows/other consumer lock → exact-SHA integration.
- **Agent kit:** canonical reviewed kit → per-repo generated files/managed `AGENTS.md` block → agent-kit lock → CI check. Agent-kit sync never changes API shapes.

## Runtime-contract procedure

1. Identify durable resource owner and authoritative contract path.
2. Verify handler ↔ contract parity in the producer.
3. Classify additive/breaking/internal and collect stable operation IDs, success/error fixtures, auth/scopes, project binding, idempotency, pagination, migration, rollout, rollback, and consumers.
4. Commit the producer source. Reject dirty source checkouts.
5. Create a source lock with repo, branch, 40-character commit, path, Git blob, SHA-256, generator/version, and output digest. Obtain source bytes with `git show <commit>:<path>`.
6. Run bidirectional drift: consumers may have neither phantom operations nor missing eligible operations.
7. Regenerate every supported SDK and inspect semantic plus generated diffs.
8. Add/update MCP only for deliberately model-facing capabilities; record effect class and required scopes from the authoritative registry.
9. Send a contract/fixture handoff to the independent Workflows/UI owner rather than editing active UI paths.
10. Run exact-SHA ecosystem checks and follow the merge order in [contract-train.md](references/contract-train.md).

## Agent-kit procedure

1. Change the canonical kit through a reviewed coordination-repo PR.
2. Preserve repository-owned text outside managed markers.
3. Copy files—never use cross-worktree symlinks—and record source commit plus per-file SHA-256 in `.tempera/agent-kit.lock.json`.
4. Run the sync tool in `--check` mode in CI. Do not self-update during unrelated feature builds.
5. Generate operation indexes from contracts; do not manually encode API inventories in `AGENTS.md` or `SKILL.md`.

Use `scripts/source_lock.py` to create/check committed-source locks and `scripts/sync_agent_kit.py` as the reference implementation for deterministic file/block synchronization.

## Fail closed

Do not declare synchronized if the source is dirty, provenance cannot be reproduced from Git, checks are one-directional, a breaking consumer is not review-ready, a scope is invented downstream, generated language surfaces differ, or CI never ran on a runner.
