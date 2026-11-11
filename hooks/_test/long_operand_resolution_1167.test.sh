#!/usr/bin/env bash
# Long literal operand lists resolve within the hook budget.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
python3 "$ROOT/hooks/_test/long_operand_resolution_1167.py"
