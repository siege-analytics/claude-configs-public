#!/usr/bin/env bash
# OPT-IN PreToolUse guard — workspace config backup discipline.
#
# NOT part of the default write-guard chain. A workspace that versions its
# Craft Agent config (skills/, sources/) to a backup repo wires this hook into
# its OWN settings (PreToolUse) so that config changes are routed through the
# [skill:workspace-backup] discipline before they land.
#
# Scoped per-workspace via WB_WORKSPACE_GLOB so it NEVER fires cross-workspace.
# Set WB_WORKSPACE_GLOB to the workspace-slug prefix the wiring workspace owns
# (default: electinfo). Example for a pour-now backup: WB_WORKSPACE_GLOB=pour-now.
#
# Exit 2 = block with message. Exit 0 = allow.
set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

HOOKS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INPUT=$(cat)
FILE_PATH=$(printf '%s' "$INPUT" \
  | python3 "$HOOKS_DIR/lib/extract-json.py" tool_input.file_path tool_input.path \
  2>/dev/null || echo "")

[[ -z "$FILE_PATH" ]] && exit 0

WB_WORKSPACE_GLOB="${WB_WORKSPACE_GLOB:-electinfo}"

# Only guard config writes within the wiring workspace's own tree.
echo "$FILE_PATH" \
  | grep -qE "\.craft-agent/workspaces/${WB_WORKSPACE_GLOB}[^/]*/(skills|sources)/" \
  || exit 0

echo "STOP: Workspace config change to: $FILE_PATH"
echo "Required skill: [skill:workspace-backup]"
echo "Reason: Workspace config changes should be versioned via the workspace-backup skill."
echo "Read the skill before proceeding."
exit 2
