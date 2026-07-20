---
name: tempera-review-cross-repo
description: Review and sequence dependent Tempera pull requests across producer, SDK, MCP, Workflows, Auth, runtime, data, and evaluation repositories. Use for stacked PRs, contract trains, generated-code PRs, stale or conflicting drafts, exact-SHA integration, merge ordering, and superseding old branches without losing commits.
---

# Tempera Cross-Repository Review

Produce an evidence-backed merge verdict for the whole train, not a superficial green-check summary.

## Procedure

1. Build the dependency graph: PR URL, base/head SHA, mergeability, draft/review state, unique commits, files, checks, consumer, rollout position, and owner.
2. Confirm each check obtained a runner and ran steps. A zero-step billing/allocation failure is unknown, not pass/fail evidence.
3. Inspect the small authoritative source diff first, then schemas/migrations/security boundaries, then generated files. Reproduce generation and require no unexplained generated diff.
4. Validate exact producer commit/path/blob/content digest. Reject dirty-checkout or filesystem-path provenance.
5. Run producer tests and affected consumer checks at exact SHAs. For stacked PRs, restack and rerun after every parent merge.
6. Apply [review-checklist.md](references/review-checklist.md), including tenancy, auth, idempotency, migrations, data policy, observability, rollout, and rollback.
7. Require owning-lane approval, affected-consumer approval, and security/data review when triggered.
8. Publish: merge/block/supersede verdict, evidence, unresolved risks, exact merge order, and who owns each follow-up.
9. Close a superseded PR only after every unique wanted commit is landed or archived on a pushed recovery branch.

## Merge discipline

One merge captain owns the train manifest. Additive consumers may land dormant before a provider. Breaking providers wait for review-ready consumers and exact-SHA integration. Re-review after rebase if security/schema/generated regions changed.

Never resolve a train by merging a stale root wholesale, force-pushing someone else's branch, or editing an independent Workflows/Cyber program without handoff acceptance.
