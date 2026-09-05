#!/usr/bin/env bash
# Probe for pytest availability. Called by the scaffold hook (#661) before
# rendering a pytest-based stub, or manually to diagnose environment gaps.
#
# Usage: scripts/probe/pytest.sh [BLOCKING_TICKET]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./_common.sh
source "$SCRIPT_DIR/_common.sh"

probe_run "pytest" "pytest" "python3 -m pip install --user pytest" "pytest" "backend" "${1:-}"
