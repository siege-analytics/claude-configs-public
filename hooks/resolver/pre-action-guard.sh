#!/bin/bash
# UserPromptSubmit hook — inject branch and ticket warnings.
#
# Closes the enforcement gap where PreToolUse hooks (branch-guard,
# ticket-required) do not fire in Craft Agent sessions.
# See: claude-configs-public#261
#
# On every turn:
# 1. If cwd is a git repo on a protected branch → inject branch warning
# 2. If detached HEAD → inject detached HEAD warning
# 3. Otherwise → silent exit
#
# Advisory, not blocking. Fires every turn so the directive is present
# before every action, not just at commit time.
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
    cat <<EOF
<pre-action-guard>
WARNING: Your working directory is in DETACHED HEAD state.

Do NOT write code or commit in this state. Create or switch to a
feature branch first:
  git checkout -b feat/<scope>-<description>

This warning fires every turn because PreToolUse branch-guard does
not fire in Craft Agent sessions. Ref: #261
</pre-action-guard>
EOF
    exit 0
fi

if echo "$BRANCH" | grep -qE "$PROTECTED"; then
    cat <<EOF
<pre-action-guard>
WARNING: Working directory is on protected branch '$BRANCH'.

Do NOT commit directly to '$BRANCH'. Create a feature branch first:
  git checkout -b feat/<scope>-<description>

Every commit needs a ticket reference (#NNN, PROJ-NNN).
Override: [no-ticket] in the commit message (use sparingly).

This warning fires every turn because PreToolUse branch-guard and
ticket-required do not fire in Craft Agent sessions. Ref: #261
</pre-action-guard>
EOF
    exit 0
fi

exit 0
