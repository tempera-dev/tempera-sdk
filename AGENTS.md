# Repository Agent Notes

- Treat environment presets as SDK contract data, not deployment-readiness or
  general-availability claims. While hosted access is private, public examples
  must use onboarding-provisioned issuer and credential values, start with
  `staging`, and describe `production` targets as reserved unless readiness and
  access are explicitly approved.
- Edit `scripts/gen-sdk-docs.py`, then regenerate `docs/site/`; never hand-edit
  the generated Mintlify files.

<!-- TEMPERA-AGENT-KIT:BEGIN -->
## Tempera shared contract discipline

This managed block is copied from the reviewed Tempera agent kit. Preserve
repository-owned guidance outside the managed markers.

- Treat runtime handlers and their canonical committed contract as the source of
  truth. Skills, SDK tables, MCP catalogs, and prose cannot authorize a route or
  scope.
- Synchronize public changes in order: runtime parity, exact source lock,
  generated clients, deliberately admitted MCP capabilities, independent
  consumers, and exact-SHA integration evidence.
- Reject dirty-checkout provenance, moving-ref-only locks, one-directional drift,
  invented downstream scopes, unexplained generated diffs, and checks that did
  not execute on a runner.
- Record compatibility, owner, migration, rollout, rollback, and affected
  consumers. A breaking producer waits for review-ready consumers and a staged
  exact-SHA receipt.
- Keep MCP model-facing exposure curated. REST coverage is not an MCP target;
  every admitted tool needs explicit scope, schema, effect, and guard evidence.
- Respect repository ownership and independent Workflows/UI and Cyber program
  boundaries. Send exact contract and fixture handoffs instead of editing their
  product behavior without acceptance.
- Run the repository's agent-kit check in CI. Update generated files only through
  the synchronizer and never replace them with cross-worktree symlinks.
<!-- TEMPERA-AGENT-KIT:END -->
