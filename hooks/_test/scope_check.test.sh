#!/bin/bash
# Test: hooks/lib/scope-check.sh (#699)
#
# Verifies:
#   (a) siege-analytics-owned cwd: in scope
#   (b) other-owner cwd: out of scope
#   (c) -R other/repo: out of scope regardless of cwd
#   (d) -R siege-analytics/repo: in scope regardless of cwd
#   (e) no origin resolvable: out of scope
#   (f) CLAUDE_SCOPED_OWNERS override

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
HELPER="$REPO_ROOT/hooks/lib/scope-check.sh"

PASS=0
FAIL=0
FAILED=()

ok() { PASS=$((PASS + 1)); printf '  [PASS] %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); FAILED+=("$1"); printf '  [FAIL] %s\n' "$1"; printf '         %s\n' "$2"; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# Fixture repos
mkdir -p "$TMP/siege-repo" "$TMP/moshi-repo" "$TMP/no-origin-repo"

git init -q "$TMP/siege-repo"
git -C "$TMP/siege-repo" remote add origin "git@github.com:siege-analytics/some-repo.git"

git init -q "$TMP/moshi-repo"
git -C "$TMP/moshi-repo" remote add origin "https://github.com/moshi-ai/frontend.git"

git init -q "$TMP/no-origin-repo"
# Deliberately no remote

# --- (a) siege-analytics cwd: in scope
result=$(source "$HELPER"; _scope_in_scope "git commit -m x" "$TMP/siege-repo" && echo in || echo out)
if [[ "$result" == "in" ]]; then
    ok "(a) siege-analytics cwd: in scope"
else
    bad "(a) siege-analytics cwd: in scope" "got $result"
fi

# --- (b) moshi-ai cwd: out of scope
result=$(source "$HELPER"; _scope_in_scope "git commit -m x" "$TMP/moshi-repo" && echo in || echo out)
if [[ "$result" == "out" ]]; then
    ok "(b) moshi-ai cwd: out of scope"
else
    bad "(b) moshi-ai cwd: out of scope" "got $result"
fi

# --- (c) -R other/repo from ANY cwd: out of scope
result=$(source "$HELPER"; _scope_in_scope "gh issue create -R moshi-ai/backend --title x" "$TMP/siege-repo" && echo in || echo out)
if [[ "$result" == "out" ]]; then
    ok "(c) -R moshi-ai/backend from siege cwd: out of scope"
else
    bad "(c) -R moshi-ai/backend" "got $result"
fi

# --- (d) -R siege-analytics/repo from ANY cwd: in scope
result=$(source "$HELPER"; _scope_in_scope "gh issue create --repo siege-analytics/some --title x" "$TMP/moshi-repo" && echo in || echo out)
if [[ "$result" == "in" ]]; then
    ok "(d) --repo siege-analytics from moshi cwd: in scope"
else
    bad "(d) --repo siege-analytics" "got $result"
fi

# --- (e) no origin resolvable: out of scope
result=$(source "$HELPER"; _scope_in_scope "git commit -m x" "$TMP/no-origin-repo" && echo in || echo out)
if [[ "$result" == "out" ]]; then
    ok "(e) no origin resolvable: out of scope"
else
    bad "(e) no origin resolvable" "got $result"
fi

# --- (f) CLAUDE_SCOPED_OWNERS override
result=$(
    export CLAUDE_SCOPED_OWNERS="moshi-ai"
    source "$HELPER"
    _scope_in_scope "git commit -m x" "$TMP/moshi-repo" && echo in || echo out
)
if [[ "$result" == "in" ]]; then
    ok "(f) CLAUDE_SCOPED_OWNERS=moshi-ai: moshi cwd now in scope"
else
    bad "(f) env override" "got $result"
fi

# --- (g) same override: siege cwd now OUT
result=$(
    export CLAUDE_SCOPED_OWNERS="moshi-ai"
    source "$HELPER"
    _scope_in_scope "git commit -m x" "$TMP/siege-repo" && echo in || echo out
)
if [[ "$result" == "out" ]]; then
    ok "(g) CLAUDE_SCOPED_OWNERS=moshi-ai: siege cwd now out of scope"
else
    bad "(g) env override reverses siege" "got $result"
fi

echo
printf 'Results: %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
    for n in "${FAILED[@]}"; do printf '  - %s\n' "$n"; done
    exit 1
fi
exit 0
