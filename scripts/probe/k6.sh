#!/usr/bin/env bash
# Probe for k6 (performance testing) availability.
#
# Usage: scripts/probe/k6.sh [BLOCKING_TICKET]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./_common.sh
source "$SCRIPT_DIR/_common.sh"

# k6 install cmd is OS-dependent; brew on Darwin, apt/snap on Linux. Default to
# brew here and let the infra ticket cover the Linux path if that route fails.
_probe_install_cmd_k6() {
    if [[ "$(uname -s)" == "Darwin" ]] && command -v brew >/dev/null 2>&1; then
        echo "brew install k6"
    elif command -v apt-get >/dev/null 2>&1; then
        echo "sudo gpg -k && sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69 && echo 'deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main' | sudo tee /etc/apt/sources.list.d/k6.list && sudo apt-get update && sudo apt-get install -y k6"
    else
        echo "unsupported-os: please install k6 manually per https://k6.io/docs/getting-started/installation/"
    fi
}

INSTALL_CMD=$(_probe_install_cmd_k6)
probe_run "k6" "k6" "$INSTALL_CMD" "" "performance" "${1:-}"
