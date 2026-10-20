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

# shellcheck source=../lib/command-text.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/command-text.sh"
set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
# Fast skip (#1083): exit before starting python3 when the tool payload's
# command cannot match this hook's trigger. Only taken when tool_input's first
# key is a non-empty "command" (an empty or missing command keeps the git-push
# fallback) and the command uses no JSON escape other than \n \t \r \" \\ \/
# (\u, \f, \b could hide letters or whitespace). \n \t \r become spaces, so an
# escaped newline before the trigger still counts as a boundary. Git-hook
# invocations (refs on stdin, no JSON) take the full path.
_FAST_CMDS=$(printf '%s' "$INPUT" | grep -oE '"command"[[:space:]]*:[[:space:]]*"(\\.|[^"\\])*"' 2>/dev/null || true)
# A long command takes the full path (#1098): bash substitutions slow down
# superlinearly under a UTF-8 locale, and past the hook timeout a skip check
# would let the command through. 16 KiB keeps the check in milliseconds.
_FAST_FULL=0; (( ${#_FAST_CMDS} > 16384 )) && { _FAST_FULL=1; _FAST_CMDS=""; }
_FAST_ESC="${_FAST_CMDS//'\\'/}"; _FAST_ESC="${_FAST_ESC//'\"'/}"; _FAST_ESC="${_FAST_ESC//'\/'/}"
_FAST_ESC="${_FAST_ESC//'\n'/}"; _FAST_ESC="${_FAST_ESC//'\t'/}"; _FAST_ESC="${_FAST_ESC//'\r'/}"
_FAST_CMDS="${_FAST_CMDS//'\n'/ }"; _FAST_CMDS="${_FAST_CMDS//'\t'/ }"; _FAST_CMDS="${_FAST_CMDS//'\r'/ }"
# The shell rebuilds words from quotes and backslashes (#1098): `git "add"`,
# `g\it add` and `git  add` all run git add. Match the trigger against the text
# as written and against a copy with quote and backslash characters dropped and
# blanks squeezed; skip only if neither matches. A command containing ANSI-C
# $'...' (which can spell any byte) takes the full path.
[[ "$_FAST_CMDS" == *"\$'"* ]] && _FAST_FULL=1
# A quote or backslash between two letters or digits (`pr"x"`, `x\git`) joins
# words; only the full path's quote handling decides what that runs. In the
# JSON text a shell `"` or `\` is itself escaped, hence the leading backslash.
[[ "$_FAST_CMDS" == *[[:alnum:]]\\[\"\\][[:alnum:]]* || "$_FAST_CMDS" == *[[:alnum:]]\'[[:alnum:]]* ]] && _FAST_FULL=1
_FAST_BUILT="${_FAST_CMDS//[\"\'\\]/}"
while [[ "$_FAST_BUILT" == *"  "* ]]; do _FAST_BUILT="${_FAST_BUILT//  / }"; done
_FAST_FIRST='"tool_input"[[:space:]]*:[[:space:]]*[{][[:space:]]*"command"[[:space:]]*:[[:space:]]*"[^"]'
_FAST_RE='(^|[^[:alnum:]])git commit([^[:alnum:]]|$)'
if [[ $_FAST_FULL == 0 && "$INPUT" =~ $_FAST_FIRST && "$_FAST_ESC" != *'\'* ]] && ! [[ "$_FAST_CMDS" =~ $_FAST_RE || "$_FAST_BUILT" =~ $_FAST_RE ]]; then exit 0; fi
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)
CWD=$(printf '%s' "$INPUT" | python3 "$EXTRACT" cwd 2>/dev/null || true)

# If parse fails or command is empty, allow
if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# Match git commit anywhere in the command (not just at start) so
# `cd /path && git commit` doesn't bypass. Uses portable word boundary
# via character-class form (see branch-guard.sh, issue #106).
if ! ct_is_git_commit "$COMMAND"; then
    exit 0
fi

# Content-scope check (#699). Skip out-of-scope repositories.
if [[ -f "$HOOK_DIR/../lib/scope-check.sh" ]]; then
    source "$HOOK_DIR/../lib/scope-check.sh"
    if ! _scope_in_scope "$COMMAND" "${CWD:-$PWD}"; then
        exit 0
    fi
fi

# Skip if this is an amend (message already exists) or merge commit
if echo "$COMMAND" | grep -qE -- '--amend|--no-edit'; then
    exit 0
fi

# Structured override with evidence chain: accepted per writing-rules:4.
# Bare [no-ticket] without evidence: blocked. Ref: #580.
if echo "$COMMAND" | grep -qE '\[no-ticket:[[:space:]]+Reason:[^]]+;[[:space:]]*Evidence:[^]]+;[[:space:]]*Falsification:[^]]+\]'; then
    exit 0
fi
if echo "$COMMAND" | grep -qE '\[no-ticket\]|\[no-ticket:[[:space:]]*\]'; then
    cat >&2 <<HOOKEOF
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

  Override with evidence (requires Reason/Evidence/Falsification):
    [no-ticket: Reason: <why>; Evidence: <obs>; Falsification: <disproof>]

This is enforced by the commit skill (ticket enforcement section).
Ref: claude-configs-public#320, #580
HOOKEOF
exit 2
