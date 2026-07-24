# Worktree Safety Reference

1. Inventory free disk, listening ports, status, branches, processes, and `git worktree list --porcelain` before mutation.
2. Treat unknown worktrees, branches, untracked files, stashes, caches, databases, and build locks as owned by someone else.
3. Create a fresh worktree from an exact fetched base. One agent owns it; register absolute path, branch, ports, and owner.
4. Isolate mutable outputs: `CARGO_TARGET_DIR`, Python environment/UV cache, npm cache/modules, databases, object stores, queues, and test tenants.
5. Serialize heavy builds with an atomic owner-identified lock.
6. Never use hard reset, forced clean, broad recursive deletion, or unresolved targets.
7. Retire only your worktree after clean status, pushed recovery, PR disposition, process check, and exact-path validation. Use `git worktree remove`, then dry-run/prune metadata.
8. Stop for ambiguous ownership or insufficient disk.
