#!/usr/bin/env bash
set -euo pipefail
# Compatibility entry point: evidence only. No output/exit code authorizes --admin.
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec python3 "$ROOT/scripts/ci/verify-billing-block.py" "$@"
