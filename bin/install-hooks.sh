#!/usr/bin/env bash
# Generate a Claude Code settings file from hooks/settings-snippet.json
# with paths resolved to wherever the hooks actually live on disk.
#
# Two install modes:
#
# Direct-clone (default — for cloned-siege use):
#   bash bin/install-hooks.sh
#   → Generates $REPO_ROOT/.claude/settings.local.json
#   → Hook paths point at $REPO_ROOT/hooks/
#
# Workspace-consumer (Craft Agent, electinfo workspaces, etc.):
#   bash bin/install-hooks.sh --workspace <workspace-path> --hooks-root <path>
#   → Generates <workspace>/.claude/settings.json (or --target-file if specified)
#   → Hook paths point at <hooks-root>/hooks/
#
# Example for a Craft Agent workspace whose hooks are bind-mounted in via
# skills/siege/hooks/:
#   bash bin/install-hooks.sh \
#     --workspace ~/.craft-agent/workspaces/dheeraj-electinfo \
#     --hooks-root ~/.craft-agent/workspaces/dheeraj-electinfo/skills/siege
#
# This overwrites the target file. If you already have settings.json content
# you want to preserve, back it up first and merge by hand afterwards.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SNIPPET="$REPO_ROOT/hooks/settings-snippet.json"

# Defaults: direct-clone mode
TARGET="$REPO_ROOT/.claude/settings.local.json"
HOOKS_ROOT="$REPO_ROOT"

usage() {
    cat <<'USAGE'
Usage: bash bin/install-hooks.sh [options]

Direct-clone mode (default):
  No args. Generates $REPO_ROOT/.claude/settings.local.json with hook
  paths pointing at $REPO_ROOT/hooks/.

Workspace-consumer mode:
  --workspace <path>      Target <path>/.claude/settings.json
  --hooks-root <path>     Hook paths resolve to <path>/hooks/
  --target-file <path>    Explicit settings file path (overrides --workspace)

Other:
  -h, --help              Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --workspace)
            if [[ -z "${2:-}" ]]; then
                echo "ERROR: --workspace requires a path" >&2
                exit 2
            fi
            TARGET="${2%/}/.claude/settings.json"
            shift 2
            ;;
        --hooks-root)
            if [[ -z "${2:-}" ]]; then
                echo "ERROR: --hooks-root requires a path" >&2
                exit 2
            fi
            HOOKS_ROOT="${2%/}"
            shift 2
            ;;
        --target-file)
            if [[ -z "${2:-}" ]]; then
                echo "ERROR: --target-file requires a path" >&2
                exit 2
            fi
            TARGET="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: unknown arg: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ ! -f "$SNIPPET" ]]; then
    echo "ERROR: snippet not found at $SNIPPET" >&2
    exit 1
fi

# Validate the hooks actually exist at the resolved location before writing
# the settings file. Catches "wrong --hooks-root" mistakes at install time
# rather than at first-turn time when the hook silently exits 127.
EXPECTED="$HOOKS_ROOT/hooks/resolver/inject-resolver.sh"
if [[ ! -f "$EXPECTED" ]]; then
    echo "ERROR: hooks not found at $HOOKS_ROOT/hooks/" >&2
    echo "       expected $EXPECTED to exist" >&2
    echo "       (use --hooks-root to point at the actual hooks tree)" >&2
    exit 1
fi

mkdir -p "$(dirname "$TARGET")"

# Substitute the placeholder path. The snippet uses /path/to/claude-configs-public
# as the parent of hooks/, so HOOKS_ROOT must be the directory CONTAINING hooks/.
sed "s|/path/to/claude-configs-public|$HOOKS_ROOT|g" "$SNIPPET" > "$TARGET"

# Validate the generated JSON parses.
if ! python3 -c "import json; json.load(open('$TARGET'))" 2>/dev/null; then
    echo "ERROR: generated settings file does not parse as JSON: $TARGET" >&2
    exit 1
fi

echo "Installed hooks settings to: $TARGET"
echo "Hook paths point at:          $HOOKS_ROOT/hooks/"
echo

# Configure native git hooks (commit-msg, etc.) if .githooks/ exists.
# These fire for ALL commit sources (Craft Agent, Claude Code, manual git).
GITHOOKS_DIR="$REPO_ROOT/.githooks"
if [[ -d "$GITHOOKS_DIR" ]]; then
    CURRENT_HOOKS_PATH=$(cd "$REPO_ROOT" && git config core.hooksPath 2>/dev/null || true)
    if [[ "$CURRENT_HOOKS_PATH" != ".githooks" ]]; then
        (cd "$REPO_ROOT" && git config core.hooksPath .githooks)
        echo "Configured native git hooks: core.hooksPath = .githooks"
        echo "  (replaces .git/hooks/ — existing hooks there will not fire)"
    else
        echo "Native git hooks already configured: core.hooksPath = .githooks"
    fi
fi
echo
echo "Verify a hook fires (should print BLOCKED... and exit 2):"
echo "  echo '{\"tool_input\":{\"message\":\"see [skill:think]\"}}' | $HOOKS_ROOT/hooks/agent-comms/no-slug-form-outbound.sh"
echo "  echo \"exit=\$?\""
