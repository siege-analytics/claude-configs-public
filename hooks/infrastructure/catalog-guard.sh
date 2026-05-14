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
#   - mc cp ... s3://{hive-warehouse,silver,gold,bronze}/...
#   - aws s3 cp ... s3://{hive-warehouse,silver,gold,bronze}/...
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
COMMAND=$(printf '%s' "$INPUT" \
  | /usr/local/bun-node-fallback-bin/node -e \
    'const d=JSON.parse(require("fs").readFileSync("/dev/stdin","utf8")); process.stdout.write(d.tool_input?.command||"")' \
  2>/dev/null || echo "")

if [ -z "$COMMAND" ]; then
  exit 0
fi

# The guard only fires when the command EXECUTES code that performs a write.
# It skips commands that merely *contain* a dangerous-looking pattern as text
# (git commits, gh issue/pr bodies, echo/printf/cat building docs or JSON,
#  sed/awk manipulations). The heuristic: require the command to START with
# a Python/Spark execution prefix AND contain the dangerous pattern. This
# is conservative — false negatives (missing a truly dangerous command) are
# worse than false positives, but the latter have bitten us repeatedly.

# First token — what's actually being executed
FIRST_TOKEN=$(printf '%s' "$COMMAND" | awk '{print $1}')

# Only scan when the command is clearly executing code
EXECUTES_CODE=0
case "$FIRST_TOKEN" in
  python|python3|pyspark|spark-submit|spark-sql|bash|sh|/snap/bin/kubectl|kubectl)
    EXECUTES_CODE=1
    ;;
esac

# Also match when python is invoked via a common wrapper with -c / heredoc
if echo "$COMMAND" | grep -qE '(^|\s)(python3?\s+(-c|-m|<<|/tmp/.*\.py))'; then
  EXECUTES_CODE=1
fi

if [ "$EXECUTES_CODE" -eq 0 ]; then
  exit 0
fi

# Dangerous pattern matches. Use grep -iE with alternation.
DANGER=0
REASON=""

# 1. Raw-path writes from Python/Spark code
if echo "$COMMAND" | grep -qiE '\.write\.(save|parquet|text|json|csv)\s*\(.*s3a?://'; then
  DANGER=1
  REASON="Python/Spark raw-path write (.write.save/parquet/etc. with s3 path)"
fi
if echo "$COMMAND" | grep -qiE '\.write\.format\s*\(\s*"?(delta|iceberg|parquet)"?\s*\)\.(save|mode)'; then
  if echo "$COMMAND" | grep -qiE 'save\s*\(.*s3a?://'; then
    DANGER=1
    REASON="Spark write.format().save() with raw s3 path — bypasses catalog"
  fi
fi

# 2. s3/mc direct copies into catalog-managed buckets
if echo "$COMMAND" | grep -qiE '(aws s3 cp|aws s3 sync|mc cp|mc mirror).*(s3a?://(hive-warehouse|silver|gold|bronze|bullion|platinum|quicksilver)/)'; then
  DANGER=1
  REASON="Direct S3 copy into catalog-managed bucket"
fi

# 3. kubectl exec + python3 + .write.save pattern (the one that bit us)
if echo "$COMMAND" | grep -qiE 'kubectl.*exec.*python3' && \
   echo "$COMMAND" | grep -qiE '\.write\.format\s*\(\s*"?(delta|iceberg|parquet)"?\s*\)'; then
  DANGER=1
  REASON="kubectl exec + Python + Spark Delta write — likely catalog bypass"
fi

if [ "$DANGER" -eq 1 ]; then
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
