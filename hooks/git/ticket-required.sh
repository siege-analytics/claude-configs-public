#!/bin/bash
# Hook: ticket-required
# Enforces: commit skill (ticket enforcement section)
# Trigger: PreToolUse on Bash(git commit *)
#
# Resolves the effective commit message instead of scanning incidental argv.
# Deterministic sources: -m/--message, repository-confined -F/--file,
# literal quoted heredoc stdin for -F -, -C/--reuse-message, -c with
# --no-edit, and --amend --no-edit. Editor-dependent, opaque-stdin, unsafe
# path, shell-expansion, and unsupported message-mutating forms fail closed.
#
# Accepted references (shared with .githooks/commit-msg):
#   GitHub/GitLab:  #NNN, repo#NNN, owner/repo#NNN
#   Jira/Linear:    PROJ-NNN, ELE-NNN, SU-NNN
#   URL:            https://jira.example.com/browse/PROJ-123, etc.
#   Spreadsheet:    [task: <description>] marker for non-tracker work
# Override: [no-ticket: Reason: ...; Evidence: ...; Falsification: ...] in the
#   message body. The bare [no-ticket] form is blocked (#580).
#
# Ref: claude-configs-public#320, #994

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(python3 -c 'import sys
limit = 1024 * 1024
payload = sys.stdin.buffer.read(limit + 1)
if len(payload) > limit:
    raise SystemExit(65)
sys.stdout.buffer.write(payload)')
INPUT_STATUS=$?
if [[ "$INPUT_STATUS" -ne 0 ]]; then
    echo "BLOCKED: hook input exceeds the 1 MiB safety limit." >&2
    exit 2
fi
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
MESSAGE_HELPER="$HOOK_DIR/../lib/commit-message.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)
CWD=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.cwd 2>/dev/null || true)
if [[ -z "$CWD" ]]; then
    CWD=$(printf '%s' "$INPUT" | python3 "$EXTRACT" cwd 2>/dev/null || true)
fi
CWD="${CWD:-$PWD}"

# If parse fails or command is empty, allow. The helper independently returns
# NOT_COMMIT for well-formed commands outside this hook's enforcement surface.
if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# Content-scope check (#699). Skip out-of-scope repositories.
if [[ -f "$HOOK_DIR/../lib/scope-check.sh" ]]; then
    source "$HOOK_DIR/../lib/scope-check.sh"
    if ! _scope_in_scope "$COMMAND" "$CWD"; then
        exit 0
    fi
fi

if [[ ! -f "$MESSAGE_HELPER" ]]; then
    echo "BLOCKED: effective commit-message parser is unavailable." >&2
    exit 2
fi

DETAIL=$(printf '%s' "$COMMAND" | python3 "$MESSAGE_HELPER" check-command --cwd "$CWD" 2>&1)
STATUS=$?
case "$STATUS" in
    0)
        exit 0
        ;;
    3)
        # Not a git commit invocation.
        exit 0
        ;;
    4)
        cat >&2 <<'HOOKEOF'
BLOCKED: '[no-ticket]' override now requires evidence chain.

Per writing-rules:4, every "this doesn't apply" claim requires the
evidence chain. Replace bare '[no-ticket]' with:

  [no-ticket: Reason: <falsifiable why no ticket applies>;
              Evidence: <observable supporting the claim>;
              Falsification: <what would prove a ticket IS needed>]

Alternatives that don't need the evidence chain:
  - #NNN or PROJ-NNN in the commit message (any tracker)
  - [task: <description>] for non-tracker work (spreadsheet, shared doc)

Ref: #580
HOOKEOF
        exit 2
        ;;
    2)
        cat >&2 <<HOOKEOF
BLOCKED: Cannot safely determine the effective commit message.

Reason: ${DETAIL:-unknown parser failure}

Use a deterministic message source: -m/--message, a repository-confined
-F/--file path, -F - with one quoted literal heredoc, -C/--reuse-message,
-c/--reedit-message with --no-edit, or --amend --no-edit. Commands whose
message can still be changed by an editor or shell expansion fail closed.

Ref: claude-configs-public#994
HOOKEOF
        exit 2
        ;;
    1|*)
        cat >&2 <<'HOOKEOF'
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
    [task: Sprint Q2 sheet row 14 - geocoder refactor]

  Override with evidence (requires Reason/Evidence/Falsification):
    [no-ticket: Reason: <why>; Evidence: <obs>; Falsification: <disproof>]

This is enforced by the commit skill (ticket enforcement section).
Ref: claude-configs-public#320, #580, #994
HOOKEOF
        exit 2
        ;;
esac
