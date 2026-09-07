#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCAN="$SCRIPT_DIR/scan.sh"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

cat > "$TMP/bad-message.txt" <<'MSG'
fix: cite rule without execution

This follows writing-code:19 for the dry-run requirement.
MSG

if bash "$SCAN" --message-file "$TMP/bad-message.txt" >/tmp/rule-citation-bad.out 2>&1; then
  echo 'FAIL: rule citation without Rule-executed passed' >&2
  cat /tmp/rule-citation-bad.out >&2
  exit 1
fi
grep -Fq 'writing-claims-rule-citation-no-rule-executed' /tmp/rule-citation-bad.out

cat > "$TMP/mismatch-message.txt" <<'MSG'
fix: cite rule with wrong execution

This follows writing-code:19 for the dry-run requirement.
Rule-executed: writing-tests:3 plans/skip-output.md
MSG

if bash "$SCAN" --message-file "$TMP/mismatch-message.txt" >/tmp/rule-citation-mismatch.out 2>&1; then
  echo 'FAIL: mismatched Rule-executed trailer passed' >&2
  cat /tmp/rule-citation-mismatch.out >&2
  exit 1
fi
grep -Fq 'writing-claims-rule-citation-no-rule-executed(writing-code:19)' /tmp/rule-citation-mismatch.out

cat > "$TMP/smuggle-message.txt" <<'MSG'
fix: cite rule with smuggled execution

This follows writing-code:19 for the dry-run requirement.
Rule-executed: writing-tests:3 plans/skip-output.md writing-code:19
MSG

if bash "$SCAN" --message-file "$TMP/smuggle-message.txt" >/tmp/rule-citation-smuggle.out 2>&1; then
  echo 'FAIL: smuggled cited rule on Rule-executed line passed' >&2
  cat /tmp/rule-citation-smuggle.out >&2
  exit 1
fi
grep -Fq 'writing-claims-rule-citation-no-rule-executed(writing-code:19)' /tmp/rule-citation-smuggle.out

cat > "$TMP/good-message.txt" <<'MSG'
fix: cite rule with execution

This follows writing-code:19 for the dry-run requirement.
Rule-executed: writing-code:19 plans/dry-run-output.md
MSG

bash "$SCAN" --message-file "$TMP/good-message.txt" >/tmp/rule-citation-good.out 2>&1

cat > "$TMP/ordinary-colons.txt" <<'MSG'
fix: mention ordinary colon tokens

The service uses localhost:8000, redis:6379, and python:3.12 in test fixtures.
MSG

bash "$SCAN" --message-file "$TMP/ordinary-colons.txt" >/tmp/rule-citation-ordinary.out 2>&1

echo 'PASS: rule citations require matching Rule-executed evidence in messages'
