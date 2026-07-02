#!/bin/bash
# UserPromptSubmit hook — inject standing-order directive when active.
#
# Checks for standing-order.json in the workspace root (co-located with
# the hook). If present and active, injects a shift-work directive into
# every turn — including loop prompts, stacked messages, and "no
# response requested" situations.
#
# The signal file is written by the agent when it receives a standing
# order and deleted when the order ends. Format:
#
#   {
#     "active": true,
#     "deadline": "2026-05-29T10:00:00-05:00",
#     "directive": "Work Epic #776 tickets using the skills pipeline",
#     "work_queue": ["#816", "#768"]
#   }
#
# Location: <workspace>/standing-order.json, derived from the script's
# own path (hooks/resolver/standing-order-guard.sh → ../../).
# Override: CLAUDE_STANDING_ORDER env var.
#
# Fail-open: if the file doesn't exist, emit nothing and exit 0.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SIGNAL_FILE="${CLAUDE_STANDING_ORDER:-$WORKSPACE_ROOT/standing-order.json}"

if [ ! -f "$SIGNAL_FILE" ]; then
  exit 0
fi

ACTIVE=$(python3 -c "
import json, sys
try:
    data = json.load(open('$SIGNAL_FILE'))
    print('true' if data.get('active', False) else 'false')
except Exception:
    print('false')
" 2>/dev/null)

if [ "$ACTIVE" != "true" ]; then
  exit 0
fi

DEADLINE=$(python3 -c "
import json
data = json.load(open('$SIGNAL_FILE'))
print(data.get('deadline', 'unspecified'))
" 2>/dev/null)

DIRECTIVE=$(python3 -c "
import json
data = json.load(open('$SIGNAL_FILE'))
print(data.get('directive', 'Continue working on pending tasks.'))
" 2>/dev/null)

WORK_QUEUE=$(python3 -c "
import json
data = json.load(open('$SIGNAL_FILE'))
items = data.get('work_queue', [])
print(', '.join(str(i) for i in items) if items else 'check ticket tracker')
" 2>/dev/null)

cat <<EOF
<standing-order>
A STANDING ORDER IS ACTIVE. Deadline: $DEADLINE

This is shift work. You know what you are supposed to be doing: do it
according to the rules and only ask for help when it becomes necessary.

Directive: $DIRECTIVE
Work queue: $WORK_QUEUE

RULES OF THE SHIFT:
1. You may NOT go idle. If background agents are running, schedule a
   ScheduleWakeup. If no agents are running and work remains, spawn one.
2. "No response requested" is NEVER valid during a standing order.
   The standing order IS the request. Respond by doing the work.
3. Stacked loop prompts are not a reason to stop. They are a reason
   to check progress and spawn more work.
4. Each fired turn must produce at least one operator-visible artifact
   unless all work is blocked or exhausted: ticket update, PR comment,
   review/investigation artifact, branch push, verification output, or
   explicit blocker with Waiting on / Unblocks when evidence.
5. Only the deadline, the user, or exhaustion of all work items ends
   this shift. You do not get to decide it is over.

If you are about to end your response without a ScheduleWakeup, without
an operator-visible artifact, or without all work items exhausted, you are
violating a direct instruction.
</standing-order>
EOF
