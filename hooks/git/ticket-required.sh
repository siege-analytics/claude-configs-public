#!/bin/bash
# Hook: ticket-required
# Enforces: commit skill (ticket enforcement section)
# Trigger: PreToolUse on Bash(git commit *)
#
# Blocks commits that don't reference a ticket in the message.
# Accepts: #NNN, repo#NNN, owner/repo#NNN, PROJ-NNN, ELE-NNN, SU-NNN
# Override: [no-ticket] in the message body (per commit skill convention)

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)

# If jq fails to parse or command is empty, allow
if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# Only check git commit commands
if ! echo "$COMMAND" | grep -qE '^git commit\b'; then
    exit 0
fi

# Skip if this is an amend (message already exists) or merge commit
if echo "$COMMAND" | grep -qE -- '--amend|--no-edit'; then
    exit 0
fi

# Search the entire command for the override marker
if echo "$COMMAND" | grep -q '\[no-ticket\]'; then
    exit 0
fi

# Search the entire command for ticket reference patterns
# #NNN, repo#NNN, owner/repo#NNN, PROJ-NNN (Jira/Linear)
if echo "$COMMAND" | grep -qE '(#[0-9]+|[A-Z]+-[0-9]+)'; then
    exit 0
fi

cat >&2 <<HOOKEOF
BLOCKED: Commit message has no ticket reference.

Every commit must reference a ticket. Add one of:
  Refs: #42
  Fixes: electinfo/enterprise#42
  Part-of: ELE-42

Or override with [no-ticket] in the message body (use sparingly).

This is enforced by the commit skill (ticket enforcement section).
HOOKEOF
exit 2
