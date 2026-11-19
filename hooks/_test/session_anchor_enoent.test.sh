#!/usr/bin/env bash
# Bounded own-directory ENOENT retry for registered session binding (#1284).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec python3 "$ROOT/bin/_test/session_anchor_enoent_test.py"
