#!/bin/bash
# Hook: no-sensitive-files
# Enforces: commit skill (sensitive files section)
# Trigger: PreToolUse on Bash(git add *)
#
# Blocks staging of files that should never be committed:
# .env, credentials, private keys, tokens.

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
_FAST_RE='(^|[^[:alnum:]])git add([^[:alnum:]]|$)'
if [[ "$INPUT" =~ $_FAST_FIRST && "$_FAST_ESC" != *'\'* ]] && ! [[ "$_FAST_CMDS" =~ $_FAST_RE ]]; then exit 0; fi
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)
CWD=$(printf '%s' "$INPUT" | python3 "$EXTRACT" cwd 2>/dev/null || true)

if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# Match git add anywhere in the command (not just at start) so
# `cd /path && git add` doesn't bypass. Uses portable word boundary
# via character-class form (see branch-guard.sh, issue #106).
# shellcheck source=../lib/command-text.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/command-text.sh"

# Paths this command would actually stage, taken from the staging
# segment only. Matching the verb anywhere in the raw text treated a
# commit message in the same line as filenames, so a message merely
# mentioning a config file was refused as an attempt to stage one (#67).
STAGE_TARGETS="$(ct_stage_args "$COMMAND")"
if [ -z "$STAGE_TARGETS" ]; then
    exit 0
fi

# Content-scope check (#699). Skip out-of-scope repositories.
if [[ -f "$HOOK_DIR/../lib/scope-check.sh" ]]; then
    source "$HOOK_DIR/../lib/scope-check.sh"
    if ! _scope_in_scope "$COMMAND" "${CWD:-$PWD}"; then
        exit 0
    fi
fi

# Sensitive file patterns (basename matching)
SENSITIVE_PATTERNS=(
    '\.env$'
    '\.env\.'
    'credentials\.json'
    'service-account.*\.json'
    '\.pem$'
    '\.key$'
    'id_rsa'
    'id_ed25519'
    '\.p12$'
    '\.pfx$'
    'token\.json'
    '\.secrets$'
    '\.secret$'
)

# Extract files from the git add command
# Strip everything before "git add", then remove "git add" and any flags
FILES="$STAGE_TARGETS"

for file in $FILES; do
    # `--` so a path beginning with a dash is a path, not a flag. Without
        # it every invocation printed "basename: invalid option".
        basename=$(basename -- "$file")
    for pattern in "${SENSITIVE_PATTERNS[@]}"; do
        if echo "$basename" | grep -qiE "$pattern"; then
            cat >&2 <<EOF
BLOCKED: Refusing to stage '$file' — this looks like a sensitive file.

Files matching these patterns should never be committed:
  .env, credentials.json, *.pem, *.key, private SSH keys, tokens

If this is intentional, stage the file manually outside Claude Code.

This is enforced by the commit skill (sensitive files section).
EOF
            exit 2
        fi
    done
done

exit 0
