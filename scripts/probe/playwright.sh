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

# #678: version function called by _probe_get_version_target when the
# CHECK_FN target is _probe_check_playwright. Naming convention:
# <check_fn>_version. Symmetric with _probe_check_playwright so
# probe_run's pre-check AND post-install re-check both go through the
# check function rather than a sentinel BIN_NAME that could never
# resolve.
_probe_check_playwright_version() {
    (command -v playwright >/dev/null 2>&1 && playwright --version) \
        || npx --no-install playwright --version 2>&1 | head -1
}

# Delegate to probe_run with the CHECK_FN as target (#678). No sentinel
# BIN_NAME; probe_run's pre-check calls _probe_check_playwright, install
# runs under policy, and the re-check calls _probe_check_playwright again
# so a successful install is observable.
probe_run "playwright" "_probe_check_playwright" "npm install -D @playwright/test && npx playwright install --with-deps" "" "e2e" "${1:-}"
