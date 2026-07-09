#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SANITIZER="$REPO_ROOT/scripts/discipline/skill-token-chat-safe.py"

input='Use [skill:code-review], [rule:writing-prose], and [skill:shelves--team]. Leave /skill:commit and skill:plain alone.'
expected='Use [skill colon code-review], [rule colon writing-prose], and [skill colon shelves--team]. Leave /skill:commit and skill:plain alone.'
actual="$(printf '%s' "$input" | python3 "$SANITIZER")"

if [[ "$actual" != "$expected" ]]; then
  printf 'unexpected sanitizer output\nexpected: %s\nactual:   %s\n' "$expected" "$actual" >&2
  exit 1
fi

if printf '%s' "$actual" | grep -Eq '\[(skill|rule):[A-Za-z0-9_.-]+\]'; then
  printf 'sanitizer left resolver-looking token in output: %s\n' "$actual" >&2
  exit 1
fi

printf 'skill-token-chat-safe: ok\n'
