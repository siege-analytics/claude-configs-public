#!/usr/bin/env bash
# Test the policy logic embedded in .github/workflows/pr-base-guard.yml.
# This mirrors the shell conditions so changes to the workflow's promotion
# contract can be reviewed locally.

set -uo pipefail

pass=0
fail=0

check() {
  local name="$1" expected="$2" head="$3" body="${4:-}" labels="${5:-[]}" actual
  actual=$(HEAD="$head" BODY="$body" LABELS="$labels" bash -c '
    if echo "$LABELS" | grep -q "\"hotfix-direct-to-main\""; then exit 0; fi
    if echo "$HEAD" | grep -qE "^develop$"; then exit 0; fi
    if echo "$HEAD" | grep -qE "^promote/"; then
      if printf "%s" "$BODY" | grep -qE "(^|[[:space:]])Self-Review-Source:[[:space:]]+\S"; then exit 0; fi
      exit 1
    fi
    if echo "$HEAD" | grep -qE "^release/"; then exit 0; fi
    exit 1
  '; echo $?)
  if [[ "$actual" == "$expected" ]]; then
    printf 'PASS: %s\n' "$name"
    pass=$((pass+1))
  else
    printf 'FAIL: %s expected %s got %s\n' "$name" "$expected" "$actual" >&2
    fail=$((fail+1))
  fi
}

check 'develop direct promotion allowed' 0 'develop' ''
check 'promote with Self-Review-Source allowed' 0 'promote/develop-to-main-resolved' 'Self-Review-Source: plans/self-review.md'
check 'promote without Self-Review-Source blocked' 1 'promote/develop-to-main-resolved' 'no durable source here'
check 'feature to main blocked' 1 'feature/x' ''
check 'release branch allowed' 0 'release/v1.2.3' ''
check 'hotfix label bypass allowed' 0 'feature/x' '' '["hotfix-direct-to-main"]'

if [[ "$fail" -gt 0 ]]; then
  printf '\npr-base-guard workflow policy: %d passed, %d failed\n' "$pass" "$fail" >&2
  exit 1
fi
printf '\npr-base-guard workflow policy: %d passed, 0 failed\n' "$pass"
