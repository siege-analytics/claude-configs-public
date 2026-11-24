#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOOK="$ROOT/hooks/write/write-guard.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0
record() {
  local expected="$1" name="$2" path="$3" transcript="$4" status output
  output=$(printf '{"tool_input":{"file_path":"%s"}}' "$path" | CRAFT_SESSION_DIR="$transcript" bash "$HOOK" 2>&1)
  status=$?
  if [[ "$status" -eq "$expected" ]]; then
    PASS=$((PASS + 1))
    printf '  [PASS] %s (exit %s)\n' "$name" "$status"
  else
    FAIL=$((FAIL + 1))
    printf '  [FAIL] %s (expected %s, got %s): %s\n' "$name" "$expected" "$status" "$output"
  fi
}

mkdir -p "$TMP/session"
printf '{"id":"test"}\n' > "$TMP/session/session.jsonl"
record 2 "unread parser skill blocks scoped YAML write" "parsers/conf/base.yaml" "$TMP/session"
printf '%s\n' '{"toolName":"Read","toolInput":{"file_path":"/workspace/skills/unity-catalog/SKILL.md"}}' > "$TMP/session/session.jsonl"
record 2 "unrelated skill receipt does not clear parser guard" "parsers/conf/base.yaml" "$TMP/session"
printf '{"id":"test"}\n' > "$TMP/session/session.jsonl"
printf '{"toolName":"Read","toolInput":{"file_path":"/workspace/skills/spark/SKILL.md"}}\n' >> "$TMP/session/session.jsonl"
record 0 "Read tool receipt allows parser YAML write" "parsers/conf/base.yaml" "$TMP/session"

printf '{"id":"test"}\n' > "$TMP/session/session.jsonl"
record 2 "unread Unity Catalog skill blocks catalog data write" "s3://silver/table.delta" "$TMP/session"
printf '%s\n' '{"toolName":"Read","toolInput":"{\"file_path\":\"/workspace/skills/unity-catalog/SKILL.md\"}"}' >> "$TMP/session/session.jsonl"
record 0 "serialized Read receipt allows catalog data write" "s3://silver/table.delta" "$TMP/session"

record 0 "missing transcript remains advisory, not an unsatisfiable gate" "parsers/conf/base.yaml" "$TMP/missing-session"

printf '\nResults: %s passed, %s failed\n' "$PASS" "$FAIL"
[[ "$FAIL" -eq 0 ]]
