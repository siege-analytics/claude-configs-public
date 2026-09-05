#!/bin/bash
# Test: hooks/bash/universal-mutation-gate.sh
#
# Regression coverage for enterprise#2572 (Class-2, #591-shape false
# positive): the unanchored 'tee ' mutation indicator substring-matches
# inside "committee ", so any read-only command mentioning a committee
# (a table/column noun throughout the electinfo DW) is wrongly treated
# as a mutation and blocked, even when it would otherwise pass via
# SAFE_PATTERNS. Also confirms real `tee` usage is still caught
# (true-positive preservation, per the enforcement-fix guardrails).

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
HOOK="$REPO_ROOT/hooks/bash/universal-mutation-gate.sh"

# shellcheck source=./run_scenarios.sh
source "$SCRIPT_DIR/run_scenarios.sh"

# No think-gate.json anywhere reachable from this cwd, so the only way a
# command can pass is via SAFE_PATTERNS (before any think-gate lookup even
# runs) -- exactly the code path the tee/committee bug short-circuits.
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

make_payload() {
    printf '{"tool_input":{"command":"%s"},"cwd":"%s"}' "$1" "$TMP_DIR"
}

# --- Class-2 false positive: "committee " must not be read as mutating ---

expect_pass "(a) grep committee (safelisted grep, contains 'committee ')" "$HOOK" "$(make_payload 'grep committee report.txt')"
expect_pass "(b) cat committee-list.txt (safelisted cat, 'committee' word)" "$HOOK" "$(make_payload 'cat committee-list.txt')"
expect_pass "(c) echo committee spending report (safelisted echo)" "$HOOK" "$(make_payload 'echo committee spending report')"
expect_pass "(d) git log --grep=committee (safelisted git log)" "$HOOK" "$(make_payload 'git log --grep=committee')"

# --- True-positive preservation: real `tee` usage must still block ---

expect_block "(e) echo x | tee /tmp/out.txt (real tee, piped)" "$HOOK" "$(make_payload 'echo x | tee /tmp/out.txt')"
expect_block "(f) tee /tmp/out.txt < input (real tee, command position)" "$HOOK" "$(make_payload 'tee /tmp/out.txt < input')"
expect_block "(g) ls; tee /tmp/out.txt (real tee, after semicolon)" "$HOOK" "$(make_payload 'ls; tee /tmp/out.txt')"

# --- Boundary sanity: substrings that look similar but aren't "tee " ---

expect_pass "(h) cat attendee-list.txt ('tee' mid-word, no following space match)" "$HOOK" "$(make_payload 'cat attendee-list.txt')"

report
