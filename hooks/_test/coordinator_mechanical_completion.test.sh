#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
python3 -B "$ROOT/hooks/_test/coordinator_mechanical_completion.py"
