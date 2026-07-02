#!/bin/bash
# Hook: no-attribution
# Enforces: attribution policy (all CLAUDE.md files, commit skill)
# Trigger: PreToolUse on Bash(git commit *)
#
# Blocks commits containing AI/agent attribution in the message.

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
