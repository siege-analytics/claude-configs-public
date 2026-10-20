#!/bin/bash
# Hook: no-broad-staging
# Enforces: commit skill (staging patterns section)
# Trigger: PreToolUse on Bash(git add *)
#
# Blocks "git add -A", "git add .", and "git add --all" which can
# accidentally include sensitive files, build artifacts, or large binaries.
# Forces explicit file-by-file staging.

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
_FAST_RE='(^|[^[:alnum:]])git add([^[:alnum:]]|$)'
if [[ $_FAST_FULL == 0 && "$INPUT" =~ $_FAST_FIRST && "$_FAST_ESC" != *'\'* ]] && ! [[ "$_FAST_CMDS" =~ $_FAST_RE || "$_FAST_BUILT" =~ $_FAST_RE ]]; then exit 0; fi
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../lib/command-text.sh
source "$HOOK_DIR/../lib/command-text.sh"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)
CWD=$(printf '%s' "$INPUT" | python3 "$EXTRACT" cwd 2>/dev/null || true)

if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# Match git add anywhere in the command (not just at start) so
# `cd /path && git add` doesn't bypass. Uses portable word boundary
# via character-class form (see branch-guard.sh, issue #106).
# Match against CODE only: a heredoc body or quoted string that merely mentions
# the forbidden form (documentation, a fixture, an issue body) is not staging.
# ct_code_only takes the command as an ARGUMENT; piping to it returns empty and
# would turn this guard into a no-op (broad_staging.test.sh asserts the blocks).
COMMAND_CODE=$(ct_code_only "$COMMAND")

if ! echo "$COMMAND_CODE" | grep -qE '(^|[^[:alnum:]])git add([^[:alnum:]]|$)'; then
    exit 0
fi

# Content-scope check (#699). Skip out-of-scope repositories.
if [[ -f "$HOOK_DIR/../lib/scope-check.sh" ]]; then
    source "$HOOK_DIR/../lib/scope-check.sh"
    if ! _scope_in_scope "$COMMAND" "${CWD:-$PWD}"; then
        exit 0
    fi
fi

# Block broad staging patterns
if echo "$COMMAND_CODE" | grep -qE 'git add\s+(-A|--all|\.\s*$|\.\s+)'; then
    cat >&2 <<EOF
BLOCKED: Broad staging ('git add -A', 'git add .', 'git add --all') is not allowed.

Stage specific files by name instead:
  git add src/file1.py src/file2.py tests/test_file.py

This prevents accidentally committing sensitive files, build artifacts,
or large binaries.

This is enforced by the commit skill (staging patterns section).
EOF
    exit 2
fi

exit 0
