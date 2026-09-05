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

if _probe_check_vitest; then
    ver=$( (command -v vitest >/dev/null 2>&1 && vitest --version) || npx --no-install vitest --version 2>&1 | head -1 )
    _probe_emit_json "{\"status\":\"installed\",\"tool\":\"vitest\",\"version\":\"$ver\"}"
    exit 0
fi

probe_run "vitest" "__vitest_absent__" "npm install -D vitest" "" "frontend" "${1:-}"
