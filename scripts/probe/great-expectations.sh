#!/usr/bin/env bash
# Probe for Great Expectations (data pipeline testing) availability.
#
# Usage: scripts/probe/great-expectations.sh [BLOCKING_TICKET]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./_common.sh
source "$SCRIPT_DIR/_common.sh"

probe_run "great-expectations" "great_expectations" "python3 -m pip install --user great-expectations" "great_expectations" "data-pipeline" "${1:-}"
