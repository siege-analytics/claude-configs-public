#!/bin/bash
# Shared library: log-block.sh
# Records enforcement gate blocks to enforcement-blocks.jsonl.
#
# Hooks source this file and call log_block_event before exit 2 to
# create an automatic, agent-independent record of blocks. The
# block-classifier-guard (UserPromptSubmit) reads this log and
# requires classification of unresolved blocks.
#
# Usage in a hook:
#   source "$HOOK_DIR/../lib/log-block.sh"
#   log_block_event "hook-name" "what the gate protects" "$COMMAND"
#   exit 2
#
# Ref: #602 (mechanical enforcement for contradiction rule)
#
# Timestamps are UTC with an explicit offset. An invariant ending in
# "(advisory)" is a would-have-blocked audit record, not a block: it is
# written with "advisory": true and readers must not count it (#1119).

log_block_event() {
    local gate_id="${1:-unknown}"
    local invariant="${2:-unknown}"
    local command="${3:-}"
    local workspace="${CRAFT_AGENT_WORKSPACE:-}"

    if [[ -z "$workspace" ]]; then
        local script_dir
        script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        workspace="$(cd "$script_dir/../.." && pwd)"
    fi

    local logfile="$workspace/enforcement-blocks.jsonl"

    python3 -c "
import json, sys, os
from datetime import datetime, timezone

event = {
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'gate_id': sys.argv[1],
    'invariant': sys.argv[2],
    'command': sys.argv[3][:200],
    'classified': False,
    'advisory': sys.argv[2].endswith('(advisory)'),
}

logfile = sys.argv[4]
try:
    with open(logfile, 'a') as f:
        f.write(json.dumps(event) + '\n')
except Exception as e:
    print(f'WARNING: log-block: failed to write block event: {e}', file=sys.stderr)
" "$gate_id" "$invariant" "$command" "$logfile" 2>/dev/null || {
        echo "WARNING: log-block.sh: block event logging failed" >&2
    }
}
