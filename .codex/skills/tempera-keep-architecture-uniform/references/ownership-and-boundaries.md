# Ownership and Program Boundaries

| Owner | Durable responsibility |
| --- | --- |
| Auth Hub | Identity, tenancy, projects/environments, entitlements, billing, revocation |
| Data Engine | Artifacts, evidence, review state, provenance, data products/releases |
| Human Data | Reviewer/admin experience and analytics; no duplicate truth |
| Palette | Traces, evaluations, experiments, comparisons, gates |
| Tempera Evals | Benchmark definitions, frozen cases/splits, scorecards/claims |
| Gray | Repository profiling and coding-task generation |
| Gym | Deterministic environments and trajectories |
| Workflows | Orchestration and the separately owned central product application |
| Cradle | Generic isolated execution and attestations |
| Tempera LLM | Provider routing, model identity, usage/cost |
| SDK/MCP | Derived access surfaces, not independent product inventories |

The independent Workflows/UI program owns Architect, Apps, App Contract, capability packs, navigation, Studio, and central UI. Cyber owns Cyber schemas/analyzers/CLI/workflows/benchmarks, target leases, `cyber_range`, and internal red-team behavior. Shared lanes provide general contracts and reviewed handoffs only.

One service owns a durable transition. Other services keep references, projections, or caches. Ambiguity requires an ADR, not a duplicate service/table.
