#!/bin/bash
# UserPromptSubmit hook — inject standing-order directive when active.
#
# Checks for a session-scoped standing-order.json first, then legacy
# workspace-root standing-order.json. If present and active, injects a
# shift-work directive into every turn, including loop prompts, stacked
# messages, and "no response requested" situations.
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
# Preferred locations:
#   - CLAUDE_STANDING_ORDER env var (explicit override)
#   - CLAUDE_SIGNAL_DIR/standing-order.json or CRAFT_AGENT_SIGNAL_DIR/standing-order.json
#   - CRAFT_AGENT_SESSION_DIR/standing-order.json or CLAUDE_SESSION_DIR/standing-order.json
#   - <workspace>/sessions/<session-id>/standing-order.json
# Legacy fallback: <workspace>/standing-order.json.
#
# Fail-open: if the file doesn't exist, emit nothing and exit 0.

set -euo pipefail

HOOK_INPUT_JSON=$(cat 2>/dev/null || true)
export CCP_HOOK_INPUT_JSON="$HOOK_INPUT_JSON"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
safe_session_id() {
  printf '%s' "$1" | tr -c 'A-Za-z0-9_.-' '_'
}

hook_input_session_id() {
  python3 - <<'PY' 2>/dev/null || true
import json, os, re

def find(obj):
    if isinstance(obj, dict):
        for key in ("sessionId", "session_id", "sessionID", "id"):
            value = obj.get(key)
            if isinstance(value, str) and value.strip():
                return value
        for key in ("session", "conversation", "metadata"):
            value = find(obj.get(key))
            if value:
                return value
        transcript = obj.get("transcript_path") or obj.get("transcriptPath")
        if isinstance(transcript, str):
            match = re.search(r"/sessions/([^/]+)/", transcript)
            if match:
                return match.group(1)
    return ""

raw = os.environ.get("CCP_HOOK_INPUT_JSON", "").strip()
if raw:
    try:
        value = find(json.loads(raw))
        if value:
            print(value)
    except Exception:
        pass
PY
}

SIGNAL_FILE="${CLAUDE_STANDING_ORDER:-}"
if [ -z "$SIGNAL_FILE" ]; then
  for dir in "${CLAUDE_SIGNAL_DIR:-}" "${CRAFT_AGENT_SIGNAL_DIR:-}" "${CRAFT_AGENT_SESSION_DIR:-}" "${CLAUDE_SESSION_DIR:-}"; do
    if [ -n "$dir" ] && [ -f "$dir/standing-order.json" ]; then
      SIGNAL_FILE="$dir/standing-order.json"
      break
    fi
  done
fi
if [ -z "$SIGNAL_FILE" ]; then
  RAW_SESSION_ID="${CRAFT_AGENT_SESSION_ID:-${CLAUDE_SESSION_ID:-${SESSION_ID:-}}}"
  if [ -z "$RAW_SESSION_ID" ]; then
    RAW_SESSION_ID="$(hook_input_session_id)"
  fi
  if [ -n "$RAW_SESSION_ID" ]; then
    SID=$(safe_session_id "$RAW_SESSION_ID")
    for candidate in "$WORKSPACE_ROOT/sessions/$SID/standing-order.json" "$WORKSPACE_ROOT/session-signals/$SID/standing-order.json"; do
      if [ -f "$candidate" ]; then
        SIGNAL_FILE="$candidate"
        break
      fi
    done
  fi
fi
if [ -z "$SIGNAL_FILE" ]; then
  SIGNAL_FILE="$WORKSPACE_ROOT/standing-order.json"
fi

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
   runtime-available re-entry mechanism when one exists. If no scheduler
   exists, keep doing foreground work or leave durable external blocker
   evidence. If no agents are running and work remains, spawn one.
2. "No response requested" is NEVER valid during a standing order.
   The standing order IS the request. Respond by doing the work.
3. Stacked loop prompts are not a reason to stop. They are a reason
   to check progress and spawn more work.
4. Each fired turn must produce at least one operator-visible artifact
   unless all work is blocked or exhausted: ticket update, PR comment,
   review/investigation artifact, branch push, verification output, or
   explicit blocker with Waiting on / Unblocks when evidence.
5. A progress summary is NOT a stopping point while work remains. If you
   just summarized progress and the queue is not empty, immediately start
   the next item in this same turn.
6. Only the deadline, the user, or exhaustion of all work items ends
   this shift. You do not get to decide it is over.

If you are about to end your response without runtime-available re-entry,
without an operator-visible artifact, without starting the next available
item, or without all work items exhausted, you are violating a direct
instruction. Do not claim async events are operator-visible unless this
runtime has proven that delivery path.
</standing-order>
EOF
