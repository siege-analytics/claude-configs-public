#!/bin/bash
# UserPromptSubmit hook — warn on wrong branch state.
#
# Companion to the PreToolUse branch-guard/ticket-required hooks, which do not
# fire in Craft Agent sessions. See: claude-configs-public#261
#
# On every turn:
# 1. protected branch  -> advisory narration
# 2. detached HEAD     -> advisory narration
# 3. otherwise         -> silent (plus the workaround-tally advisory below)
#
# #873 P1 (defects D5, D1): ADVISORY, not blocking. This hook previously emitted
# {"continue": false} for detached HEAD or a protected branch. Craft Agents
# honors continue:false as a hard turn-halt BEFORE the model runs, so a workspace
# in detached HEAD hard-halted EVERY Claude turn, including read-only questions
# -- the root cause of craft-agents#49. The hard block belongs at the PreToolUse
# mutation point (branch-guard.sh blocks the actual commit); prompt-submit
# narrates. Would-have-blocked events are still logged for audit.
#
# Fail-open: exits 0 if not in a git repo or git is unavailable.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Fail-safe audit logger: record a would-have-blocked event, never error.
_pag_audit() {
    local _lb="$SCRIPT_DIR/../lib/log-block.sh"
    if [ -r "$_lb" ]; then
        # shellcheck disable=SC1090
        . "$_lb" 2>/dev/null || true
        command -v log_block_event >/dev/null 2>&1 && \
            log_block_event "pre-action-guard" "$1" "UserPromptSubmit" 2>/dev/null || true
    fi
}

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

if [ -z "$BRANCH" ]; then
    exit 0
fi

PROTECTED="^(main|master|develop|dev|development|staging|next|integration)$"

if [ "$BRANCH" = "HEAD" ]; then
    _pag_audit "detached HEAD (advisory)"
    cat <<EOF
<pre-action-guard>
Advisory: working directory is in DETACHED HEAD state. Create a feature branch
before making changes: git checkout -b feat/<scope>-<description>.
Commits are still hard-blocked at commit/push time. Ref: #261, #450, #873
</pre-action-guard>
EOF
    exit 0
fi

if echo "$BRANCH" | grep -qE "$PROTECTED"; then
    _pag_audit "protected branch '$BRANCH' (advisory)"
    cat <<EOF
<pre-action-guard>
Advisory: working directory is on protected branch '$BRANCH'. Do NOT commit
directly. Create a feature branch first: git checkout -b feat/<scope>-<description>.
Commits are still hard-blocked at commit/push time. Ref: #261, #450, #873
</pre-action-guard>
EOF
    exit 0
fi

# Workaround tally check — reads the tally file written by
# hooks/bash/workaround-tally.sh and warns when patterns exceed threshold.
# Covers Craft Agent sessions where PreToolUse doesn't fire.
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TALLY_FILE="${WORKSPACE_ROOT}/workaround-tally.json"
THRESHOLD=3

if [ -f "$TALLY_FILE" ]; then
    TALLY_WARN=$(python3 -c "
import json, sys
try:
    tally = json.load(open('$TALLY_FILE'))
except:
    sys.exit(0)
alerts = []
for sig, entry in tally.get('patterns', {}).items():
    if entry.get('count', 0) >= $THRESHOLD:
        alerts.append(f\"  {entry['label']}: {entry['count']}x (e.g., {entry['first_command'][:80]})\")
if alerts:
    print('Repeated workaround patterns detected:')
    for a in alerts:
        print(a)
    print()
    print('These patterns suggest a bug being masked by workarounds.')
    print('File a ticket for the root cause instead of repeating the fix.')
" 2>/dev/null || true)
    if [ -n "$TALLY_WARN" ]; then
        cat <<EOF
<pre-action-guard>
$TALLY_WARN
</pre-action-guard>
EOF
    fi
fi

exit 0
