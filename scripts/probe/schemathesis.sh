#!/usr/bin/env bash
# Probe for Schemathesis (API contract fuzzer) availability.
#
# Usage: scripts/probe/schemathesis.sh [BLOCKING_TICKET]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./_common.sh
source "$SCRIPT_DIR/_common.sh"

probe_run "schemathesis" "schemathesis" "python3 -m pip install --user schemathesis" "schemathesis" "api-contract" "${1:-}"
