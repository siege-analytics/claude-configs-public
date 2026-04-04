#!/bin/bash
# Hook: no-broad-staging
# Enforces: commit skill (staging patterns section)
# Trigger: PreToolUse on Bash(git add *)
#
# Blocks "git add -A", "git add .", and "git add --all" which can
# accidentally include sensitive files, build artifacts, or large binaries.
# Forces explicit file-by-file staging.

set -uo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)

if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# Only check git add commands
if ! echo "$COMMAND" | grep -qE '^git add\b'; then
    exit 0
fi

# Block broad staging patterns
if echo "$COMMAND" | grep -qE 'git add\s+(-A|--all|\.\s*$|\.\s+)'; then
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
