# Cross-Repository Review Checklist

## Graph and provenance

- Exact base/head SHAs, dependency order, unique commits, mergeability, and superseded-commit recovery are recorded.
- Source bytes reproduce from committed Git path/blob/content digest; no dirty checkout or developer path.
- Checks acquired runners and executed steps.

## Contract and generated output

- Runtime and canonical contract are exact peers.
- Stable IDs, compatibility class, fixtures, errors, idempotency, pagination, cancellation, migration, rollout, and rollback are explicit.
- SDK languages and MCP/consumer surfaces are mechanically derived; generated diffs reproduce and contain no unexplained edits.

## Security and data

- Actor/org/project/environment/audience/scopes/expiry/revocation and tenant isolation are tested.
- Secrets, egress, external effects, sandboxing, budgets, audit, and failure mode fail closed.
- Provenance, consent/license/classification, retention/deletion, split identity, sealed-eval isolation, and reviewer/verifier references are enforced where relevant.

## Operations

- Logs/traces/metrics/health/usage/cost and alerts expose the change.
- Deployment/migration is reversible and restore is tested proportional to risk.
- Owning, consumer, security, and data reviewers approve as triggered.

Verdict states merge/block/supersede, exact evidence, merge order, residual risk, and owner.
