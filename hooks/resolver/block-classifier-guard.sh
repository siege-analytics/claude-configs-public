#!/bin/bash
# UserPromptSubmit hook — enforcement block classifier.
#
# When enforcement gates block commands, they log the block event to
# enforcement-blocks.jsonl (via hooks/lib/log-block.sh). This hook
# checks for unclassified block events and injects a classification
# requirement into the agent's context.
#
# The agent must classify each block as:
#   - "normal": artifacts not produced, gate working correctly
#   - "contradiction": enforcement system has a bug (taxonomy class 1-7)
#
# Classification is recorded by writing to block-classification.json.
# The hook checks this file to determine which blocks are resolved.
#
# This moves enforcement contradiction detection from "will the agent
# remember to invoke the rule" to "the agent cannot proceed without
# making a classification." Ref: #602.
#
# Known limitation: classification is agent self-attestation. The value
# is in FORCING the record to exist — operator audit can detect dishonest
# classifications. Until #602's meta-hook is fully implemented, this is
# behavioral guidance with an audit trail, not mechanical verification.
#
# Always active — no env var required.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_ROOT="${CRAFT_AGENT_WORKSPACE:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
BLOCKS_LOG="$WORKSPACE_ROOT/enforcement-blocks.jsonl"
CLASSIFICATION_FILE="$WORKSPACE_ROOT/block-classification.json"

if [ ! -f "$BLOCKS_LOG" ]; then
    exit 0
fi

UNCLASSIFIED=$(python3 -c "
import json, sys, os
from datetime import datetime, timedelta

blocks_log = sys.argv[1]
classification_file = sys.argv[2]

classified_ids = set()
if os.path.isfile(classification_file):
    try:
        data = json.load(open(classification_file))
        for c in data.get('classifications', []):
            classified_ids.add(c.get('block_id', ''))
    except Exception:
        pass

unclassified = []
try:
    # 4-hour window: blocks older than this are no longer actionable.
    # The context has changed and re-classification serves no purpose.
    cutoff = datetime.now() - timedelta(hours=4)
    with open(blocks_log) as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                block_id = f\"{event.get('gate_id', '')}:{event.get('timestamp', '')}\"
                if block_id in classified_ids:
                    continue
                ts = datetime.fromisoformat(event['timestamp'])
                if ts < cutoff:
                    continue
                unclassified.append({
                    'block_id': block_id,
                    'gate_id': event.get('gate_id', ''),
                    'invariant': event.get('invariant', ''),
                    'command': event.get('command', '')[:80]
                })
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
except Exception:
    pass

if unclassified:
    print(json.dumps(unclassified[-3:]))
else:
    print('[]')
" "$BLOCKS_LOG" "$CLASSIFICATION_FILE" 2>/dev/null)

if [ -z "$UNCLASSIFIED" ] || [ "$UNCLASSIFIED" = "[]" ]; then
    exit 0
fi

BLOCK_COUNT=$(echo "$UNCLASSIFIED" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")

if [ "$BLOCK_COUNT" = "0" ]; then
    exit 0
fi

BLOCK_DETAILS=$(echo "$UNCLASSIFIED" | python3 -c "
import json, sys
blocks = json.load(sys.stdin)
for b in blocks:
    print(f\"  Gate: {b['gate_id']}\")
    print(f\"  Invariant: {b['invariant']}\")
    print(f\"  Command: {b['command']}\")
    print()
" 2>/dev/null || echo "  (unable to parse block details)")

cat <<EOF
<enforcement-block-classification required="true">
$BLOCK_COUNT recent enforcement block(s) are UNCLASSIFIED.

$BLOCK_DETAILS
Before continuing, classify each block:

1. **Normal gate failure**: You have not produced the required artifacts.
   The gate is working correctly. Produce the artifacts and retry.

2. **Enforcement contradiction** (classes 1-7): The enforcement system
   itself has a bug. Capture evidence per the enforcement contradiction
   rule and file a ticket with a contradiction packet.

To classify, write block-classification.json:
  {
    "classifications": [
      {
        "block_id": "<gate_id>:<timestamp>",
        "classification": "normal" | "contradiction",
        "class": null | 1-7,
        "evidence": "<for contradictions: evidence packet summary>"
      }
    ]
  }

This is a mechanical enforcement requirement. The gate blocked a command
and the system needs to know whether the block was correct or a bug.
Ref: #602
</enforcement-block-classification>
EOF
