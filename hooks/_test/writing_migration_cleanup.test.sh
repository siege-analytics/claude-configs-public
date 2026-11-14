#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
failed=0
for file in "$ROOT"/skills/_writing-*-rules.md; do
  if grep -q '^## Migration note' "$file"; then
    echo "FAIL: expired writing migration note remains in ${file#$ROOT/}" >&2
    failed=1
  fi
done
[[ $failed -eq 0 ]]
echo "writing_migration_cleanup: PASS"
