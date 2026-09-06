#!/usr/bin/env bash
# Probe for Vitest availability. Same npx-first pattern as playwright.
#
# Usage: scripts/probe/vitest.sh [BLOCKING_TICKET]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./_common.sh
source "$SCRIPT_DIR/_common.sh"

_probe_check_vitest() {
    if command -v vitest >/dev/null 2>&1; then
        return 0
    fi
    if command -v npx >/dev/null 2>&1 && npx --no-install vitest --version >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

# #678: version function paired with _probe_check_vitest.
_probe_check_vitest_version() {
    (command -v vitest >/dev/null 2>&1 && vitest --version) \
        || npx --no-install vitest --version 2>&1 | head -1
}

# Delegate to probe_run with CHECK_FN target (#678); no sentinel BIN_NAME.
probe_run "vitest" "_probe_check_vitest" "npm install -D vitest" "" "frontend" "${1:-}"
