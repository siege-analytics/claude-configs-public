#!/bin/bash
# Hook: no-attribution
# Enforces: attribution policy (all CLAUDE.md files, commit skill)
# Trigger: PreToolUse on Bash(git commit *)
#
# Blocks commits containing AI/agent attribution in the message.

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
# shellcheck source=../lib/command-text.sh
source "$HOOK_DIR/../lib/command-text.sh"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)
CWD=$(printf '%s' "$INPUT" | python3 "$EXTRACT" cwd 2>/dev/null || true)

# If parse fails or command is empty, allow
if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# A real `git commit` anywhere in the command (so `cd /path && git commit`
# doesn't bypass), matched as code: the verb inside a heredoc body or a quoted
# string (an issue body that mentions git commit) is not a commit (#55).
if ! ct_is_git_commit "$COMMAND"; then
    exit 0
fi

# Content-scope check (#699). Skip out-of-scope repositories so this
# guard doesn't fire in moshi-ai / Ringer-Sciences / etc. workspaces
# on a shared Craft server. CLAUDE_SCOPED_OWNERS can override the
# default (siege-analytics).
if [[ -f "$HOOK_DIR/../lib/scope-check.sh" ]]; then
    source "$HOOK_DIR/../lib/scope-check.sh"
    if ! _scope_in_scope "$COMMAND" "${CWD:-$PWD}"; then
        exit 0
    fi
fi

# Extract everything after "git commit" as the message area. This is the RAW
# text: the commit message lives in quotes, so it must not go through
# ct_code_only (which strips quoted spans). ct_is_git_commit above already
# rejected non-commits, so this scan only runs on a real commit.
MESSAGE_AREA=$(echo "$COMMAND" | sed 's/.*git commit//')

# Case-insensitive check for attribution patterns
PATTERNS=(
    'co-authored-by.*claude'
    'co-authored-by.*cursor'
    'co-authored-by.*copilot'
    'co-authored-by.*anthropic'
    'co-authored-by.*openai'
    'co-authored-by.*codex'
    'co-authored-by.*craft'
    'generated with claude'
    'made with cursor'
    'built with codex'
    'built with claude'
    'claude code'
    'noreply@anthropic\.com'
)

for pattern in "${PATTERNS[@]}"; do
    if echo "$MESSAGE_AREA" | grep -iqE "$pattern"; then
        cat >&2 <<HOOKEOF
BLOCKED: Commit message contains AI/agent attribution.

Remove any mention of Claude, Cursor, Copilot, Anthropic, OpenAI,
Co-Authored-By lines referencing AI tools, or "Generated with" markers.

This is enforced by the attribution policy in CLAUDE.md.
HOOKEOF
        exit 2
    fi
done

exit 0
