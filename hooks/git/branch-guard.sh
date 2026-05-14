#!/bin/bash
# Hook: branch-guard
# Enforces: develop-guard skill, branch skill, commit skill (step 0)
# Trigger: PreToolUse on Bash(git commit *)
#
# Blocks commits to protected branches (main, develop, master, etc.).
# The agent must create a feature branch first.

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)

# Only check git commit commands
if ! echo "$COMMAND" | grep -qE '^git commit\b'; then
    exit 0
fi

if [[ -z "$CWD" ]]; then
    exit 0  # Can't determine directory, allow
fi

BRANCH=$(git -C "$CWD" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

if [[ -z "$BRANCH" ]]; then
    exit 0  # Not a git repo, allow
fi

# Protected branch patterns
PROTECTED="^(main|master|develop|dev|development|staging|next|integration)$"

if [[ "$BRANCH" =~ $PROTECTED ]]; then
    cat >&2 <<EOF
BLOCKED: Direct commit to '$BRANCH' is not allowed.

Create a feature branch first:
  git checkout -b feature/your_description

This is enforced by the develop-guard and branch skills.
EOF
    exit 2
fi

exit 0
