#!/usr/bin/env bash
set -u

minimum_gib="${1:-40}"
target_path="${2:-$PWD}"

if ! [[ "$minimum_gib" =~ ^[0-9]+$ ]]; then
  echo "minimum GiB must be an integer" >&2
  exit 64
fi

if [[ ! -d "$target_path" ]]; then
  echo "target path is not a directory: $target_path" >&2
  exit 66
fi

available_kib="$(df -Pk "$target_path" | awk 'NR==2 {print $4}')"
required_kib="$((minimum_gib * 1024 * 1024))"
available_gib="$(awk -v kib="$available_kib" 'BEGIN {printf "%.1f", kib / 1024 / 1024}')"

echo "target=$target_path"
echo "available_gib=$available_gib"
echo "required_gib=$minimum_gib"

if git -C "$target_path" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "repository=$(git -C "$target_path" rev-parse --show-toplevel)"
  git -C "$target_path" status --short --branch
  git -C "$target_path" worktree list --porcelain
else
  echo "repository=none"
fi

if command -v lsof >/dev/null 2>&1; then
  lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null || true
else
  echo "listening_ports=unavailable_lsof_missing"
fi

if (( available_kib < required_kib )); then
  echo "preflight=insufficient_disk_for_parallel_builds" >&2
  exit 2
fi

echo "preflight=ok"
