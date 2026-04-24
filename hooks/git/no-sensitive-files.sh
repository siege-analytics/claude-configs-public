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
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)

if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# Only check git add commands
if ! echo "$COMMAND" | grep -qE '^git add\b'; then
    exit 0
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
# Remove "git add" prefix and any flags
FILES=$(echo "$COMMAND" | sed 's/^git add\s*//' | sed 's/\s*-[a-zA-Z]\+\s*//g')

for file in $FILES; do
    basename=$(basename "$file")
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
