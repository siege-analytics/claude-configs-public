#!/bin/bash
# UserPromptSubmit hook -- block when the agent is on a protected branch.
#
# This is the UserPromptSubmit equivalent of hooks/git/branch-guard.sh
# (which is PreToolUse and does not fire in Craft Agent sessions).
# Fires every turn. Emits {"continue": false} JSON block until the
# agent switches to a feature branch.
#
# Always active — no env var required. CLAUDE_CA_ENFORCE gate removed
# in #572 (honor-system gap).
#
# Fail-open: if git is unavailable or not in a repo, exit silently.
# Ref: claude-configs-public#261, #572

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Try to determine git state from the workspace root
BRANCH=$(git -C "$WORKSPACE_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

if [ -z "$BRANCH" ]; then
    exit 0
fi

PROTECTED="^(main|master|develop|dev|development|staging|next|integration)$"

if [[ "$BRANCH" =~ $PROTECTED ]]; then
    python3 -c "import json,sys; print(json.dumps({'continue': False, 'systemMessage': sys.argv[1]}))" \
        "BLOCKED: On protected branch '$BRANCH'. Do NOT commit directly. Create a feature branch: git checkout -b feat/<description>. Ref: #261, #450, #572"
    exit 0
fi

exit 0
