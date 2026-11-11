#!/usr/bin/env bash
# #1274 own-PR artifact-heading resolution; see pipeline_state_own_pr_1274.py.
set -euo pipefail
python3 -B "$(dirname "${BASH_SOURCE[0]}")/pipeline_state_own_pr_1274.py"
