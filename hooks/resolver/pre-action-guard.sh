#!/bin/bash
# UserPromptSubmit hook — block on wrong branch state.
#
# Closes the enforcement gap where PreToolUse hooks (branch-guard,
# ticket-required) do not fire in Craft Agent sessions.
# See: claude-configs-public#261
#
# On every turn:
# 1. If cwd is a git repo on a protected branch → emit JSON block
# 2. If detached HEAD → emit JSON block
# 3. Otherwise → silent exit
#
# Always active — no env var required. CLAUDE_CA_ENFORCE gate removed
# in #572 (honor-system gap).
#
# Fail-open: exits 0 if not in a git repo, if git is unavailable, or if
# on a feature branch (the happy path).

set -euo pipefail

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

if [ -z "$BRANCH" ]; then
    exit 0
fi

PROTECTED="^(main|master|develop|dev|development|staging|next|integration)$"

if [ "$BRANCH" = "HEAD" ]; then
    python3 -c "import json,sys; print(json.dumps({'continue': False, 'systemMessage': sys.argv[1]}))" \
        "BLOCKED: Working directory is in DETACHED HEAD state. Create a feature branch first: git checkout -b feat/<scope>-<description>. Ref: #261, #450, #572"
    exit 0
fi

if echo "$BRANCH" | grep -qE "$PROTECTED"; then
    python3 -c "import json,sys; print(json.dumps({'continue': False, 'systemMessage': sys.argv[1]}))" \
        "BLOCKED: Working directory is on protected branch '$BRANCH'. Do NOT commit directly. Create a feature branch first: git checkout -b feat/<scope>-<description>. Ref: #261, #450, #572"
    exit 0
fi

# Workaround tally check — reads the tally file written by
# hooks/bash/workaround-tally.sh and warns when patterns exceed threshold.
# Covers Craft Agent sessions where PreToolUse doesn't fire.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
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
