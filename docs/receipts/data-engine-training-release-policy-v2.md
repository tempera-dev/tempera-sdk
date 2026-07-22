# Data Engine training-release policy v2 consumer receipt

Status: review-train consumer; not a staged runtime receipt.

This SDK change vendors the exact Data Engine contract prepared by
[Data Engine #76](https://github.com/tempera-dev/data-engine/pull/76). It is
an additive response-schema update: the existing request methods and MCP tool
names do not change.

## Exact producer input

- Repository: `tempera-dev/data-engine`
- Review-train branch: `jaden/release-dedup-v2-restack-clean`
- Commit: `56c1776c9a29343e8031bdf0bb3564403cdcf701`
- OpenAPI: `api/openapi.yaml`
- OpenAPI SHA-256:
  `f88ef55de1b174e760857106aa54d6dbc8dc80ae6380ddefd81b8df2e5bf7ec4`

The committed SDK lock and vendored MCP artifacts are generated only from
those Git bytes. The temporary reviewed branch is allowlisted solely to permit
this dormant consumer to merge before the additive provider; immediately after
the provider lands, this receipt must be regenerated with `source_branch:
main` and the same reachable producer commit (or its merged successor).

## Consumer behavior

`projects.trainingReleases.admit` and `projects.trainingReleases.get` now
return a required `policy_receipt` in the vendored response schema. A caller
may present a release as training eligible only when all of the following are
true:

- `policy_receipt.status == "PASS"`;
- its nine unique `passed_checks` are present; and
- the existing release status is not stale.

`LEGACY_UNVERIFIED` is stale and non-eligible, even if a legacy top-level
status previously appeared active. Consumers must use the exact vendored MCP
schemas; they must not rebuild these bounds from this prose.

## Generated consumer artifacts

- `contracts/data-engine-openapi-operations.json` pins the exact OpenAPI
  provenance and its operation-index digest.
- `specs/data-engine-mcp-admission.json` SHA-256:
  `28be9964f88f978d362fab47bcb62e6b7d6119a8d6fbf2df23682958e748c591`
- `specs/data-engine-mcp-tools.json` SHA-256:
  `d53828c99038f3a98f7aadb7ad33dda859d4744b808b5ff093c249aeabbc1e05`

## Verification and deferred staging

The local exact-source checks reproduce the producer bytes and the vendored
MCP artifacts at the commit above. GitHub Actions is the required independent
runner check, but it is presently unavailable because the organization’s
Actions capacity/billing produces zero-step runs. No staging admit/get round
trip has been claimed or performed: it is deferred until Data Engine #76 has
merged and deployed, after which the merge train must record the producer
commit, this SDK consumer commit, and one `PASS` admit/get round trip using
the same receipt.

Rollback: revert this SDK-only consumer change together with its source locks;
do not infer eligibility from an unpinned or legacy response.
