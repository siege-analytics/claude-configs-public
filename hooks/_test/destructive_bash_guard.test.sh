#!/bin/bash
# Test: hooks/bash/destructive-guard.sh
#
# Exercises prod-destructive blocks, shared-resource and general-mutation
# blocks (v2), evidence-chain override, allow-list escape, trailer escape,
# env-var escape, and false-positive shapes.

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
HOOK="$REPO_ROOT/hooks/bash/destructive-guard.sh"

# shellcheck source=./run_scenarios.sh
source "$SCRIPT_DIR/run_scenarios.sh"

# Isolated git repo so the trailer-check has somewhere to read from.
TMP_REPO=$(mktemp -d)
trap 'rm -rf "$TMP_REPO"' EXIT
cd "$TMP_REPO"
git init -q -b main
git config user.email "t@example.test"
git config user.name "test"
echo seed > scratch.txt
git add -A
git commit -q -m "seed"

# Disable any inherited env-var escape that might leak from the parent shell.
unset CLAUDE_DESTRUCTIVE_BASH

make_payload() {
    printf '{"tool_input":{"command":"%s"},"cwd":"%s"}' "$1" "$TMP_REPO"
}

# --- prod-destructive blocks ---

expect_block "(a) rm -rf /" "$HOOK" "$(make_payload 'rm -rf /')"
expect_block "(b) git push --force origin main" "$HOOK" "$(make_payload 'git push --force origin main')"
expect_block "(c) git push --no-verify" "$HOOK" "$(make_payload 'git push --no-verify origin feature/x')"
expect_block "(d) chmod -R 777 ." "$HOOK" "$(make_payload 'chmod -R 777 .')"
expect_block "(e) aws s3 rm s3://prod-bucket/key" "$HOOK" "$(make_payload 'aws s3 rm s3://prod-bucket/key')"
expect_block "(f) kubectl apply -f manifest.yaml" "$HOOK" "$(make_payload 'kubectl apply -f manifest.yaml')"

# --- false-positive guards: commands that should NOT block ---

expect_pass "(g) ls" "$HOOK" "$(make_payload 'ls -la')"
expect_pass "(h) git push origin feature/x (no --force)" "$HOOK" "$(make_payload 'git push origin feature/x')"
expect_pass "(i) psql -h localhost -c DELETE  (localhost carve-out)" "$HOOK" "$(make_payload 'psql -h localhost -c \"DELETE FROM users WHERE id=1\"')"
expect_pass "(j) rm -rf /tmp/scratch (not root/home)" "$HOOK" "$(make_payload 'rm -rf /tmp/scratch')"

# --- v2 promoted tiers: shared-resource and general-mutation now block ---

expect_block "(k) gh issue create (shared-resource, blocks)" "$HOOK" "$(make_payload 'gh issue create --title test')"
expect_block "(l) curl -X POST (general-mutation, blocks)" "$HOOK" "$(make_payload 'curl -X POST https://example.com/api')"

# --- evidence-chain override escapes v2 blocks ---

expect_pass "(k2) gh issue create with evidence-chain override" "$HOOK" "$(make_payload 'gh issue create --title test [destructive-ok: Reason: posting artifact; Evidence: pipeline requires it; Falsification: if manual posting works, this is unnecessary]')"
expect_pass "(l2) curl -X POST with evidence-chain override" "$HOOK" "$(make_payload 'curl -X POST https://example.com/api [destructive-ok: Reason: webhook test; Evidence: endpoint is staging; Falsification: if prod URL, should not call]')"

# --- escape hatches ---

# Trailer escape: add an Authorized: trailer to the latest commit.
git commit -q --allow-empty -m "wip: prep for prod cleanup" -m "Authorized: prod data backfill per ticket #999"
expect_pass "(m) rm -rf / with Authorized: trailer" "$HOOK" "$(make_payload 'rm -rf /')"

# Reset trailer by adding a new commit without it.
git commit -q --allow-empty -m "wip: continue"
expect_block "(n) rm -rf / after trailer commit superseded" "$HOOK" "$(make_payload 'rm -rf /')"

# Allow-list escape (project-scoped).
mkdir -p .claude
echo '^aws s3 rm s3://dev-' > .claude/destructive-bash-allowlist.txt
expect_pass "(o) aws s3 rm s3://dev-bucket (allow-listed)" "$HOOK" "$(make_payload 'aws s3 rm s3://dev-bucket/key')"
expect_block "(p) aws s3 rm s3://prod-bucket (NOT allow-listed)" "$HOOK" "$(make_payload 'aws s3 rm s3://prod-bucket/key')"
rm -rf .claude

# Env-var escape.
expect_pass_env() {
    local name="$1" hook="$2" payload="$3"
    local out actual_exit
    out=$(printf '%s' "$payload" | CLAUDE_DESTRUCTIVE_BASH=allow bash "$hook" 2>&1)
    actual_exit=$?
    if [[ "$actual_exit" -eq 0 ]]; then
        _HARNESS_PASS=$((_HARNESS_PASS + 1))
        printf '  [PASS] %s (exit %d)\n' "$name" "$actual_exit"
    else
        _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
        _HARNESS_FAILED_NAMES+=("$name")
        printf '  [FAIL] %s (expected exit 0, got %d)\n' "$name" "$actual_exit"
        printf '         stderr/stdout: %s\n' "${out:0:300}"
    fi
}
expect_pass_env "(q) rm -rf / with CLAUDE_DESTRUCTIVE_BASH=allow" "$HOOK" "$(make_payload 'rm -rf /')"

report
