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
_FAST_ESC="${_FAST_CMDS//'\\'/}"; _FAST_ESC="${_FAST_ESC//'\"'/}"; _FAST_ESC="${_FAST_ESC//'\/'/}"
_FAST_ESC="${_FAST_ESC//'\n'/}"; _FAST_ESC="${_FAST_ESC//'\t'/}"; _FAST_ESC="${_FAST_ESC//'\r'/}"
_FAST_CMDS="${_FAST_CMDS//'\n'/ }"; _FAST_CMDS="${_FAST_CMDS//'\t'/ }"; _FAST_CMDS="${_FAST_CMDS//'\r'/ }"
_FAST_FIRST='"tool_input"[[:space:]]*:[[:space:]]*[{][[:space:]]*"command"[[:space:]]*:[[:space:]]*"[^"]'
_FAST_RE='(^|[^[:alnum:]])git commit([^[:alnum:]]|$)'
if [[ "$INPUT" =~ $_FAST_FIRST && "$_FAST_ESC" != *'\'* ]] && ! [[ "$_FAST_CMDS" =~ $_FAST_RE ]]; then exit 0; fi
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
if ! echo "$COMMAND" | grep -qE '(^|[^[:alnum:]])git commit([^[:alnum:]]|$)'; then
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

# Extract everything after "git commit" as the message area
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
