---
name: tempera-shared-machine
description: Coordinate safe parallel Tempera engineering on one host. Use before creating, reusing, cleaning, deleting, building, or retiring Git worktrees; when multiple agents or independent programs share disk, ports, caches, databases, or branches; and when diagnosing shared-host collisions.
---

# Tempera Shared Machine

Protect every other task on the host while creating an isolated lane.

## Procedure

1. Read `shared/SHARED-MACHINE-PROTOCOL.md` when this skill is used from the four-lane bundle. If it was vendored alone, read [worktree-safety.md](references/worktree-safety.md).
2. Run `scripts/machine_preflight.sh` from the intended repository. It is read-only.
3. Inventory `git status`, `git worktree list --porcelain`, local/remote branches, listening ports, free disk, and existing lane registry. Treat every unexplained worktree as owned by someone else.
4. Require 40 GiB free before four build-capable lanes. If lower, continue only with read-only audit or small edits and serialize installs/builds.
5. Allocate an absolute lane root, unique worktree, branch, port range, virtual environment, database/object-store paths, npm/UV cache, and `CARGO_TARGET_DIR`. Record them in the machine registry.
6. Fetch in a clean anchor checkout and create a new worktree from the exact intended base. Never reset or clean an existing checkout into shape.
7. Acquire the atomic heavy-build lock before a full Rust workspace or multi-service Docker build. Never remove another owner’s lock.
8. Before file or worktree deletion, prove exact ownership, clean status, pushed recovery, no open processes, and exact path. Prefer `git worktree remove`; never recursively delete an unresolved path.
9. Close by stopping servers, releasing locks, reporting disk, updating registry/status, and leaving changes clean or intentionally committed.

## Mandatory stop conditions

Stop and ask the owner when there are unexplained modifications, an occupied port/path, unknown untracked files, ambiguous branch ownership, insufficient disk for the next operation, or a destructive target not resolved to the lane base.

Never use `git reset --hard`, `git clean -fdx`, broad recursive deletion, `$HOME`, `~`, globs, or unresolved variables for cleanup.
