#!/usr/bin/env bash
# Regression tests for scripts/ci/check-branch-topology.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CHECK="$ROOT/scripts/ci/check-branch-topology.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
REPO="$TMP/repo"

pass=0
fail=0

expect() {
  local name="$1" expected="$2" base="$3" head="$4"
  shift 4
  set +e
  local head_repo="${1:-test/repo}"
  (cd "$REPO" && BASE_BRANCH="$base" HEAD_BRANCH="$head" HEAD_REPO="$head_repo" CANONICAL_REPO=test/repo MAIN_REF=main bash "$CHECK") >"$TMP/out" 2>&1
  local actual=$?
  set -e
  if [[ "$actual" == "$expected" ]]; then
    printf 'PASS: %s\n' "$name"
    pass=$((pass + 1))
  else
    printf 'FAIL: %s expected %s got %s\n' "$name" "$expected" "$actual" >&2
    cat "$TMP/out" >&2
    fail=$((fail + 1))
  fi
}

git init -q -b main "$REPO"
git -C "$REPO" config user.email test@example.test
git -C "$REPO" config user.name Test
printf 'base\n' > "$REPO/file"
git -C "$REPO" add file
git -C "$REPO" commit -q -m base

git -C "$REPO" switch -q -c develop
printf 'develop\n' >> "$REPO/file"
git -C "$REPO" commit -qam develop
expect 'canonical develop to main allowed' 0 main develop
expect 'feature to main blocked' 1 main feature/x
expect 'promote branch to main blocked' 1 main promote/scoped
expect 'release branch to main blocked' 1 main release/v1
expect 'hotfix branch to main blocked' 1 main hotfix/x
expect 'fork develop impersonation blocked' 1 main develop fork/repo

git -C "$REPO" switch -q -c feature/current
printf 'feature\n' >> "$REPO/file"
git -C "$REPO" commit -qam feature
expect 'feature from reconciled develop allowed into develop' 0 develop feature/current

git -C "$REPO" switch -q main
printf 'main advanced\n' > "$REPO/main-only"
git -C "$REPO" add main-only
git -C "$REPO" commit -q -m main-advanced
git -C "$REPO" switch -q feature/current
expect 'behind-main feature blocked from develop' 1 develop feature/current

git -C "$REPO" switch -q develop
git -C "$REPO" merge -q --no-edit main
expect 'reconciled develop allowed into main' 0 main develop

git -C "$REPO" switch -q main
expect 'main back-sync allowed into develop' 0 develop main

if [[ "$fail" -gt 0 ]]; then
  printf '\nbranch topology policy: %d passed, %d failed\n' "$pass" "$fail" >&2
  exit 1
fi
printf '\nbranch topology policy: %d passed, 0 failed\n' "$pass"
