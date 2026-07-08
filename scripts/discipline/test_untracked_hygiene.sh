#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$SCRIPT_DIR/untracked-hygiene.py"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

cd "$TMP"
git init -q
git config user.email test@example.com
git config user.name Test
printf 'tracked\n' > README.md
git add README.md
git commit -q -m init

printf 'copy\n' > 'example 2.md'
OUT=$(python3 "$SCRIPT" --emit-delete-script)

if echo "$OUT" | grep -Fq "echo rm -rf -- 'example 2.md'"; then
  echo "PASS: space-containing duplicate path is emitted without Git quote wrapping"
else
  echo "FAIL: expected deletion template for real path without embedded double quotes" >&2
  echo "$OUT" >&2
  exit 1
fi

if echo "$OUT" | grep -Fq "'\"example 2.md\"'"; then
  echo "FAIL: deletion template contains Git's human-facing double quote wrapping" >&2
  echo "$OUT" >&2
  exit 1
fi
