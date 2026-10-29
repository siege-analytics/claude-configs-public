#!/bin/bash
# PreToolUse hook (matcher: Bash) — block catalog-bypass patterns.
#
# Fires when a Bash tool call matches a dangerous pattern that suggests the
# agent is about to write to catalog-managed storage via a raw path instead
# of through Unity Catalog / Hive Metastore. Emits a hard STOP to stdout
# that the agent sees as feedback before the command runs.
#
# Matched patterns (case-insensitive):
#   - .write.save(...s3a://... or s3://...)
#   - .write.parquet(...s3a://...)
#   - .write.format("delta").save(...s3a://...)
#   - .write.format("iceberg").save(...s3a://...)
#   - mc cp/mirror ... s3://{hive-warehouse,silver,gold,bronze,...}/...
#   - aws s3 cp/sync ... s3://{hive-warehouse,silver,gold,bronze,...}/...
#
# Classification is invocation-aware: each pipeline/control-list segment is
# inspected by its effective program after supported wrappers. Quoted prose is
# not treated as execution, while active shell payloads and substitutions are
# recursively inspected without eval or shell execution.
#
# False-positive policy: err on the side of firing. The agent can re-read
# unity-catalog skill and confirm intent before proceeding; that's cheaper
# than another orphaned-file cleanup.

set -euo pipefail
export PATH="/home/craftagents/bin:$PATH"

# Claude Code sends the tool call JSON on stdin for PreToolUse.
INPUT=$(cat)

# Extract the command text. For Bash the tool input is like:
#   {"tool": "Bash", "tool_input": {"command": "...", "description": "..."}}
HOOKS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
set +e
COMMAND=$(printf '%s' "$INPUT" \
  | python3 "$HOOKS_DIR/lib/extract-json.py" tool_input.command \
  2>/dev/null)
EXTRACT_STATUS=$?
set -e

if [ "$EXTRACT_STATUS" -ne 0 ] || [ -z "$COMMAND" ]; then
  echo "[catalog-guard] STOP. Could not extract a nonempty Bash command from hook input." >&2
  exit 2
fi

# Classify the raw command as data. The classifier does not eval, expand, or
# execute any part of it. Exit 2 is a policy match; any other nonzero status is
# treated as a classifier failure and blocks rather than silently disabling the
# enforcement hook.
CLASSIFIER="$HOOKS_DIR/lib/classify-catalog-command.py"
set +e
REASON=$(printf '%s' "$COMMAND" | python3 "$CLASSIFIER")
CLASSIFIER_STATUS=$?
set -e

if [ "$CLASSIFIER_STATUS" -eq 0 ]; then
  exit 0
fi
if [ "$CLASSIFIER_STATUS" -ne 2 ] || [ -z "$REASON" ]; then
  echo "[catalog-guard] STOP. Command classification failed (exit $CLASSIFIER_STATUS)." >&2
  exit 2
fi

if [ -n "$REASON" ]; then
  cat >&2 <<EOF
[catalog-guard] STOP. The command matches a catalog-bypass pattern:

  $REASON

Before running this, confirm ALL of the following:

  1. Is the target path managed by a catalog (Unity Catalog / Hive Metastore)?
     -> If yes: use saveAsTable("schema.table") or INSERT OVERWRITE, NOT
        raw path writes. See:
        ~/git/electinfo/claude-configs-public/skills/infrastructure/unity-catalog/SKILL.md

  2. Did you query the catalog first to confirm the table's registered
     location, format, and column schema?

  3. Is this a deliberate raw-path write to a non-catalog-managed scratch
     location? If yes, confirm with the user and proceed.

  4. Have you re-read the unity-catalog SKILL.md in this session?

If any answer is "no" or "not sure" — DO NOT RUN THIS COMMAND. Stop, read
the skill, and revise.

Exit 2 blocks this tool call. To proceed anyway (with user authorization),
revise the command to use the catalog API.
EOF
  exit 2
fi

exit 0
