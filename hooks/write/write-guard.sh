#!/usr/bin/env bash
# PreToolUse guard for Write and Edit tool calls.
# Blocks writes to paths that require skill consultation before editing.
# Exit 2 = block with message. Exit 0 = allow.
set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" \
  | /usr/local/bun-node-fallback-bin/node -e \
    'const d=JSON.parse(require("fs").readFileSync("/dev/stdin","utf8")); process.stdout.write((d.tool_input?.file_path||d.tool_input?.path||""))' \
  2>/dev/null || echo "")

[[ -z "$FILE_PATH" ]] && exit 0

block() {
  local skill="$1"
  local reason="$2"
  echo "STOP: Non-trivial file write to: $FILE_PATH"
  echo "Required skill: [skill:${skill}]"
  echo "Reason: ${reason}"
  echo "Read the skill before proceeding."
  exit 2
}

# Rundeck enterprise Spark CRDs — memory allocation rules are mandatory
echo "$FILE_PATH" | grep -qE "rundeck/jobs/fec-enterprise/.*\.yaml" \
  && block "enterprise-spark-jobs" "Enterprise Spark CRDs require memory allocation review. No hard memory limits on enterprise pods."

# Hydra configs — field naming source of truth
echo "$FILE_PATH" | grep -qE "parsers/conf/.*\.yaml" \
  && block "infrastructure" "Hydra configs are the source of truth for field naming. Verify snake_case FEC official names before editing."

# Pydantic schema files
echo "$FILE_PATH" | grep -qE "parsers/schemas/.*\.py" \
  && block "coding/python" "Schema changes require type hint compliance and NumPy docstring review."

# Delta / Parquet writes
echo "$FILE_PATH" | grep -qE "\.(parquet|delta)$|/delta/" \
  && block "infrastructure/unity-catalog" "Delta/Parquet writes to catalog paths must go through Unity Catalog skill."

# Workspace skill or source config changes
echo "$FILE_PATH" | grep -qE "\.craft-agent/workspaces/.+/skills/|\.craft-agent/workspaces/.+/sources/" \
  && block "workspace-backup" "Workspace config changes should use the workspace-backup skill to ensure changes are versioned."

exit 0
