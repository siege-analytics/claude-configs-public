#!/usr/bin/env bash
# Generate .claude/settings.local.json from hooks/settings-snippet.json
# with paths resolved to the current repo location.
#
# Usage: bash bin/install-hooks.sh
#
# This creates a machine-local settings file that Claude Code reads.
# The file is .local.json (not committed) because paths are absolute.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SNIPPET="$REPO_ROOT/hooks/settings-snippet.json"
TARGET="$REPO_ROOT/.claude/settings.local.json"

if [[ ! -f "$SNIPPET" ]]; then
    echo "ERROR: $SNIPPET not found." >&2
    exit 1
fi

mkdir -p "$REPO_ROOT/.claude"

sed "s|/path/to/claude-configs-public|$REPO_ROOT|g" "$SNIPPET" > "$TARGET"

echo "Installed hooks to $TARGET"
echo "All hooks now point at: $REPO_ROOT/hooks/"
