#!/bin/bash
# UserPromptSubmit hook -- warn when the agent is on a protected branch.
#
# This is the UserPromptSubmit companion of hooks/git/branch-guard.sh, which is
# PreToolUse and does not fire in Craft Agent sessions. Fires every turn.
#
# #873 P1 (defects D5, D1): ADVISORY, not blocking. This hook previously emitted
# {"continue": false}, which Craft Agents honors as a hard turn-halt BEFORE the
# model runs -- so a workspace sitting on a protected branch (or detached HEAD,
# see pre-action-guard.sh) hard-halted every Claude turn, including read-only
# questions (root cause of craft-agents#49). The hard block belongs at the
# PreToolUse mutation point (branch-guard.sh blocks the actual commit); at
# prompt-submit we narrate. Every would-have-blocked event is still logged, so
# relaxing the block does not lose enforcement visibility.
#
# Fail-open: if git is unavailable or not in a repo, exit silently.
# Ref: claude-configs-public#261, #572, #873

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

BRANCH=$(git -C "$WORKSPACE_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

if [ -z "$BRANCH" ]; then
    exit 0
fi

PROTECTED="^(main|master|develop|dev|development|staging|next|integration)$"

if [[ "$BRANCH" =~ $PROTECTED ]]; then
    # Audit log: record the would-have-blocked event even though we narrate.
    _lb="$SCRIPT_DIR/../lib/log-block.sh"
    if [ -r "$_lb" ]; then
        # shellcheck disable=SC1090
        . "$_lb" 2>/dev/null || true
        if command -v log_block_event >/dev/null 2>&1; then
            log_block_event "branch-state-guard" "protected branch '$BRANCH' (advisory)" "UserPromptSubmit" 2>/dev/null || true
        fi
    fi
    cat <<EOF
<branch-state-guard>
Advisory: on protected branch '$BRANCH'. Do NOT commit directly here. Create a
feature branch before making changes: git checkout -b feat/<description>.
The commit itself is still hard-blocked at push/commit time by branch-guard.
Ref: #261, #450, #873
</branch-state-guard>
EOF
    exit 0
fi

exit 0
