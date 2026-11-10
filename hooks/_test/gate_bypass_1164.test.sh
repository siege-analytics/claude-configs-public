#!/usr/bin/env bash
# #1164 B1/B2 gate-bypass regressions; see gate_bypass_1164.py.
set -euo pipefail
python3 -B "$(dirname "${BASH_SOURCE[0]}")/gate_bypass_1164.py"
