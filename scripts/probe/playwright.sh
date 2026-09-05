#!/usr/bin/env bash
# Probe for Playwright availability. Checks for the npx-launchable `playwright`
# CLI. Install command targets a project-local install (npm i -D) since
# Playwright is not typically installed globally.
#
# Usage: scripts/probe/playwright.sh [BLOCKING_TICKET]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./_common.sh
source "$SCRIPT_DIR/_common.sh"

# Detection: `npx --no-install playwright --version` succeeds if playwright is
# installed in the current project's node_modules OR globally.
_probe_check_playwright() {
    if command -v playwright >/dev/null 2>&1; then
        return 0
    fi
    if command -v npx >/dev/null 2>&1 && npx --no-install playwright --version >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

if _probe_check_playwright; then
    ver=$( (command -v playwright >/dev/null 2>&1 && playwright --version) || npx --no-install playwright --version 2>&1 | head -1 )
    _probe_emit_json "{\"status\":\"installed\",\"tool\":\"playwright\",\"version\":\"$ver\"}"
    exit 0
fi

# Absent: delegate to shared install/escalate flow via probe_run's install path.
# Use a shim BIN_NAME that _probe_check_bin will always miss so probe_run takes
# the absent branch and applies the shared policy resolution.
probe_run "playwright" "__playwright_absent__" "npm install -D @playwright/test && npx playwright install --with-deps" "" "e2e" "${1:-}"
