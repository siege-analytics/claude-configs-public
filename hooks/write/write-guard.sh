#!/usr/bin/env bash
# PreToolUse guard for Write and Edit tool calls.
# Blocks writes to paths that require skill consultation before editing.
# Exit 2 = block with message. Exit 0 = allow.
set -uo pipefail
source "$(f="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/hook-path.sh"; [[ -f "$f" ]] && printf '%s' "$f" || printf /dev/null)"

HOOKS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INPUT=$(cat)
FILE_PATH=$(printf '%s' "$INPUT" \
  | python3 "$HOOKS_DIR/lib/extract-json.py" tool_input.file_path tool_input.path tool_input.notebook_path \
  2>/dev/null || echo "")

[[ -z "$FILE_PATH" ]] && exit 0

require_skill_read() {
  local skill="$1"
  local skill_path="$2"
  local reason="$3"
  local transcript="${CRAFT_SESSION_DIR:-}/session.jsonl"

  # The hook must not create an unsatisfiable gate when the host has no
  # transcript. In that case, leave a visible advisory and let normal review
  # and repository checks govern the write.
  if [[ ! -f "$transcript" ]]; then
    echo "NOTE: Review [skill:${skill}] before editing ${FILE_PATH}. ${reason}"
    return 0
  fi

  if python3 - "$transcript" "$skill_path" <<'PY'
import json
import sys

transcript, expected = sys.argv[1:]
suffix = expected.lstrip("./")
try:
    with open(transcript, encoding="utf-8") as stream:
        for line in stream:
            try:
                record = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if record.get("toolName") != "Read":
                continue
            tool_input = record.get("toolInput", {})
            if isinstance(tool_input, str):
                try:
                    tool_input = json.loads(tool_input)
                except (json.JSONDecodeError, ValueError):
                    continue
            path = str(tool_input.get("file_path", "")).replace("\\", "/")
            if path == suffix or path.endswith("/" + suffix):
                raise SystemExit(0)
except OSError:
    pass
raise SystemExit(1)
PY
  then
    return 0
  fi

  echo "STOP: Non-trivial file write to: $FILE_PATH"
  echo "Required skill: [skill:${skill}] (${skill_path})"
  echo "Reason: ${reason}"
  echo "Read the named skill with the Read tool in this session, then retry."
  exit 2
}

# Rundeck enterprise Spark CRDs — memory allocation rules are mandatory
echo "$FILE_PATH" | grep -qE "rundeck/jobs/fec-enterprise/.*\.yaml" \
  && require_skill_read "spark" "skills/spark/SKILL.md" "Enterprise Spark CRDs require memory allocation review. No hard memory limits on enterprise pods."

# Hydra configs — field naming source of truth
echo "$FILE_PATH" | grep -qE "parsers/conf/.*\.yaml" \
  && require_skill_read "spark" "skills/spark/SKILL.md" "Check parser configuration against the official FEC field names and preserve snake_case."

# Pydantic schema files
echo "$FILE_PATH" | grep -qE "parsers/schemas/.*\.py" \
  && require_skill_read "effective-python" "skills/shelves/languages/effective-python/SKILL.md" "Schema changes require type hints and NumPy docstrings."

# Delta / Parquet writes to catalog-managed locations
echo "$FILE_PATH" | grep -qE "\.(parquet|delta)$|/(silver|gold|bronze|hive-warehouse|bullion|platinum|quicksilver)/.*(_delta_log|\.delta)" \
  && require_skill_read "unity-catalog" "skills/unity-catalog/SKILL.md" "Delta/Parquet writes to catalog paths must go through Unity Catalog."

# NOTE: the workspace skill/source-config backup block was extracted to the
# opt-in hooks/write/workspace-backup-guard.sh — it was workspace-specific
# discipline and false-fired cross-workspace from this always-on chain.

exit 0
