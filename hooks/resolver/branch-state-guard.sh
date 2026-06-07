#!/bin/bash
# UserPromptSubmit hook -- warn when the agent is on a protected branch.
#
# This is the UserPromptSubmit equivalent of hooks/git/branch-guard.sh
# (which is PreToolUse and does not fire in Craft Agent sessions).
# Fires every turn. Injects a persistent warning until the agent
# switches to a feature branch.
#
# Fail-open: if git is unavailable or not in a repo, exit silently.
# Ref: claude-configs-public#261 (workaround for PreToolUse gap)

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
    cat <<EOF
<branch-state>
WARNING: You are on protected branch '$BRANCH'.

Do NOT commit directly to this branch. Create a feature branch first:
  git checkout -b feat/your-description
  git checkout -b fix/your-description

This warning will repeat every turn until you switch branches.
Ref: develop-guard skill, branch-guard hook (#261 workaround)
</branch-state>
EOF
fi

exit 0
