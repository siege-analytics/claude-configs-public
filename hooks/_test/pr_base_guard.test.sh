#!/bin/bash
# Test: hooks/git/pr-base-guard.sh
#
# Exercises the develop-guard mechanical enforcement at PreToolUse on
# the GitHub CLI PR-create command. Blocks when base is main-role and
# head is not develop-role / release/* / promote/* / hotfix/* AND no
# bypass label is present.

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
HOOK="$REPO_ROOT/hooks/git/pr-base-guard.sh"

# shellcheck source=./run_scenarios.sh
source "$SCRIPT_DIR/run_scenarios.sh"

# Isolated git repo so the head-branch check has somewhere to read from.
TMP_REPO=$(mktemp -d)
trap 'rm -rf "$TMP_REPO"' EXIT
cd "$TMP_REPO"
git init -q -b main
git config user.email "t@example.test"
git config user.name "test"
echo seed > scratch.txt
git add -A
git commit -q -m "seed"

make_payload() {
    # $1 = command, $2 = HEAD branch to switch to before checking
    git checkout -q -B "$2" 2>/dev/null
    printf '{"tool_input":{"command":"%s"},"cwd":"%s"}' "$1" "$TMP_REPO"
}

# --- BLOCKS: feature head + main-role base, no bypass ---

expect_block "(a) feature/foo -> main" "$HOOK" \
    "$(make_payload 'gh pr create --base main --title x' 'feature/foo')"
expect_block "(b) feature/foo -> main with --base=main equals form" "$HOOK" \
    "$(make_payload 'gh pr create --base=main --title x' 'feature/foo')"
expect_block "(c) feature/foo -> master" "$HOOK" \
    "$(make_payload 'gh pr create --base master --title x' 'feature/foo')"
expect_block "(d) feature/foo -> production" "$HOOK" \
    "$(make_payload 'gh pr create --base production --title x' 'feature/foo')"
expect_block "(e) bugfix/123 -> main with -B short form" "$HOOK" \
    "$(make_payload 'gh pr create -B main --title x' 'bugfix/123')"
expect_block "(f) docs/architecture -> main (the actual SW#251/#252 shape)" "$HOOK" \
    "$(make_payload 'gh pr create --base main --title x' 'docs/architecture-warehouse-first')"

# --- ALLOWS: develop-role heads ---

expect_pass "(g) develop -> main (canonical promote)" "$HOOK" \
    "$(make_payload 'gh pr create --base main --title x' 'develop')"
expect_pass "(h) dev -> main (synonym)" "$HOOK" \
    "$(make_payload 'gh pr create --base main --title x' 'dev')"
expect_pass "(i) staging -> main (synonym)" "$HOOK" \
    "$(make_payload 'gh pr create --base main --title x' 'staging')"
expect_pass "(j) next -> main (synonym)" "$HOOK" \
    "$(make_payload 'gh pr create --base main --title x' 'next')"

# --- ALLOWS: release/promote/hotfix shapes ---

expect_pass "(k) release/v2.1.0 -> main" "$HOOK" \
    "$(make_payload 'gh pr create --base main --title x' 'release/v2.1.0')"
expect_pass "(l) promote/develop-to-main -> main" "$HOOK" \
    "$(make_payload 'gh pr create --base main --title x' 'promote/develop-to-main')"
expect_pass "(m) hotfix/critical-bug -> main" "$HOOK" \
    "$(make_payload 'gh pr create --base main --title x' 'hotfix/critical-bug')"

# --- ALLOWS: explicit bypass label ---

expect_pass "(n) feature/foo -> main WITH hotfix-direct-to-main label" "$HOOK" \
    "$(make_payload 'gh pr create --base main --title x --label hotfix-direct-to-main' 'feature/foo')"
expect_pass "(o) feature/foo -> main WITH --label=hotfix-direct-to-main equals form" "$HOOK" \
    "$(make_payload 'gh pr create --base main --label=hotfix-direct-to-main --title x' 'feature/foo')"

# --- ALLOWS: non-main-role base (feature -> develop) ---

expect_pass "(p) feature/foo -> develop" "$HOOK" \
    "$(make_payload 'gh pr create --base develop --title x' 'feature/foo')"
expect_pass "(q) feature/foo -> integration" "$HOOK" \
    "$(make_payload 'gh pr create --base integration --title x' 'feature/foo')"

# --- ALLOWS: non-gh-pr-create commands ---

expect_pass "(r) git status (not a PR-create)" "$HOOK" \
    "$(make_payload 'git status' 'feature/foo')"
expect_pass "(s) gh pr list (not pr create)" "$HOOK" \
    "$(make_payload 'gh pr list --base main' 'feature/foo')"
expect_pass "(t) gh pr merge (not pr create)" "$HOOK" \
    "$(make_payload 'gh pr merge 99 --base main' 'feature/foo')"

# --- YIELDS: multi-cd / chained commands (safety posture) ---

expect_pass "(u) chained command with newline yields" "$HOOK" \
    "$(make_payload $'cd /tmp\ngh pr create --base main' 'feature/foo')"

# --- GitLab parity (CCP#201): glab mr create ---

expect_block "(v) glab feature/foo -> main (--target-branch)" "$HOOK" \
    "$(make_payload 'glab mr create --target-branch main --title x' 'feature/foo')"
expect_block "(w) glab feature/foo -> main (--target-branch=)" "$HOOK" \
    "$(make_payload 'glab mr create --target-branch=main --title x' 'feature/foo')"
expect_block "(x) glab feature/foo -> master (--target-branch)" "$HOOK" \
    "$(make_payload 'glab mr create --target-branch master --title x' 'feature/foo')"
expect_block "(y) glab feature/foo -> main with -b short" "$HOOK" \
    "$(make_payload 'glab mr create -b main --title x' 'feature/foo')"
expect_pass "(z) glab develop -> main" "$HOOK" \
    "$(make_payload 'glab mr create --target-branch main --title x' 'develop')"
expect_pass "(aa) glab release/v1 -> main" "$HOOK" \
    "$(make_payload 'glab mr create --target-branch main --title x' 'release/v1')"
expect_pass "(ab) glab promote/develop-to-main -> main" "$HOOK" \
    "$(make_payload 'glab mr create --target-branch main --title x' 'promote/develop-to-main')"
expect_pass "(ac) glab feature/foo -> main WITH hotfix-direct-to-main label" "$HOOK" \
    "$(make_payload 'glab mr create --target-branch main --title x --label hotfix-direct-to-main' 'feature/foo')"
expect_pass "(ad) glab feature/foo -> develop" "$HOOK" \
    "$(make_payload 'glab mr create --target-branch develop --title x' 'feature/foo')"
expect_pass "(ae) glab mr list (not mr create)" "$HOOK" \
    "$(make_payload 'glab mr list --target-branch main' 'feature/foo')"

if [[ "${_HARNESS_FAIL:-0}" -gt 0 ]]; then
    printf '\nFAIL: %d test(s) failed.\n' "$_HARNESS_FAIL" >&2
    exit 1
fi
printf '\nALL PASS: %d scenarios passed.\n' "${_HARNESS_PASS:-0}"
