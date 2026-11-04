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
# Override: [no-ticket: Reason: ...; Evidence: ...; Falsification: ...] in the
#   message body. The bare [no-ticket] form is blocked (#580).
#
# Ref: claude-configs-public#320

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"
# Hook-local text transport must not turn valid Unicode into an empty command.
export PYTHONUTF8=1

INPUT=$(cat)
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
GIT_POLICY="$HOOK_DIR/../lib/git_command.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)
CWD=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.cwd 2>/dev/null || true)
if [[ -z "$CWD" ]]; then
    CWD=$(printf '%s' "$INPUT" | python3 "$EXTRACT" cwd 2>/dev/null || true)
fi
CWD="${CWD:-$PWD}"
[[ -z "$COMMAND" ]] && exit 0
# No lexical git-commit prefilter: literal aliases and wrappers need structured
# dispatch. Released routine reads are proved before message inspection.
[[ -f "$GIT_POLICY" ]] || { echo "BLOCKED: Git ticket dispatcher unavailable." >&2; exit 2; }
DETAIL=$(printf '%s' "$COMMAND" | python3 "$GIT_POLICY" --cwd "$CWD" --policy ticket 2>&1)
STATUS=$?
if [[ "$STATUS" -ne 0 || "$DETAIL" != "handled" ]]; then
    printf '%s\n' "${DETAIL:-BLOCKED: Git ticket dispatch failed closed.}" >&2
    exit 2
fi
exit 0
