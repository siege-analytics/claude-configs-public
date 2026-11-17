#!/usr/bin/env bash
# An unresolved target repository denies task ownership (#1281).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
python3 "$ROOT/hooks/_test/unresolved_target_repo_1281.py"
