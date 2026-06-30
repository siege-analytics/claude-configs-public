#!/bin/bash
# Hook: ticket-required
# Enforces: commit skill (ticket enforcement section)
# Trigger: PreToolUse on Bash(git commit *)
#
# Blocks commits that don't reference a ticket in the message.
# Accepts (platform-agnostic):
#   GitHub/GitLab:  #NNN, repo#NNN, owner/repo#NNN
#   Jira/Linear:    PROJ-NNN, ELE-NNN, SU-NNN
#   URL:            https://jira.example.com/browse/PROJ-123, etc.
#   Spreadsheet:    [task: <description>] marker for non-tracker work
# Override: [no-ticket] in the message body (per commit skill convention)
#
# Ref: claude-configs-public#320

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)

# If parse fails or command is empty, allow
if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# Match git commit anywhere in the command (not just at start) so
# `cd /path && git commit` doesn't bypass. Uses portable word boundary
# via character-class form (see branch-guard.sh, issue #106).
if ! echo "$COMMAND" | grep -qE '(^|[^[:alnum:]])git commit([^[:alnum:]]|$)'; then
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

# [task: ...] marker for work tracked outside issue trackers (spreadsheets,
# shared docs, etc.). Lighter than [no-ticket] — still requires a description.
if echo "$COMMAND" | grep -qE '\[task:[[:space:]]+[^]]+\]'; then
    exit 0
fi

# Ticket reference patterns (platform-agnostic):
#   #NNN, repo#NNN, owner/repo#NNN  — GitHub, GitLab
#   PROJ-NNN                        — Jira, Linear, Shortcut
#   URL containing /issues/, /browse/, /tickets/, /merge_requests/, /pull/
if echo "$COMMAND" | grep -qE '(#[0-9]+|[A-Z]+-[0-9]+)'; then
    exit 0
fi
if echo "$COMMAND" | grep -qE 'https?://[^[:space:]]+(/(issues|browse|tickets|merge_requests|pull|stories|tasks)/[^[:space:]]+)'; then
    exit 0
fi

cat >&2 <<HOOKEOF
BLOCKED: Commit message has no ticket reference.

Every commit must reference a ticket or task. Accepted formats:

  Issue tracker (GitHub/GitLab):
    Refs: #42
    Fixes: electinfo/enterprise#42

  Issue tracker (Jira/Linear):
    Part-of: ELE-42
    Refs: PROJ-123

  URL (any tracker):
    Refs: https://jira.example.com/browse/PROJ-123

  Non-tracker work (spreadsheet, shared doc, etc.):
    [task: Sprint Q2 sheet row 14 — geocoder refactor]

  Nuclear override (use sparingly):
    [no-ticket]

This is enforced by the commit skill (ticket enforcement section).
Ref: claude-configs-public#320
HOOKEOF
exit 2
