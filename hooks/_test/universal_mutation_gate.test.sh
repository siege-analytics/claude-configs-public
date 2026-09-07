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

# --- Class-2 false positive: quoted '>' / '->' must not be read as a redirect ---
# The redirect-family indicator scanned the raw command including quoted content,
# so any read-only command containing '->' (an arrow) or '>' inside a quoted
# grep pattern / echo string was wrongly blocked. Same #591-shape as the
# tee/committee bug above.

expect_pass "(i) grep \"a->b\" data.txt (arrow in grep pattern)" "$HOOK" "$(make_payload 'grep \"a->b\" data.txt')"
expect_pass "(j) grep flow->next app.log (bare arrow in grep args)" "$HOOK" "$(make_payload 'grep flow->next app.log')"
expect_pass "(k) echo \"migrate 2026->2027\" (arrow in echo string)" "$HOOK" "$(make_payload 'echo \"migrate 2026->2027\"')"
expect_pass "(l) grep \"cat .* >\" report.txt (literal redirect op in grep pattern)" "$HOOK" "$(make_payload 'grep \"cat .* >\" report.txt')"
expect_pass "(m) grep \"append >> file\" report.txt (literal >> in grep pattern)" "$HOOK" "$(make_payload 'grep \"append >> file\" report.txt')"

# --- True-positive preservation: real redirects must still block ---

expect_block "(n) echo hi > /tmp/out.txt (real redirect, spaced)" "$HOOK" "$(make_payload 'echo hi > /tmp/out.txt')"
expect_block "(o) cat a.txt > b.txt (real redirect via cat)" "$HOOK" "$(make_payload 'cat a.txt > b.txt')"
expect_block "(p) echo \"safe text\" > realfile.txt (redirect OUTSIDE quotes, quoted content present)" "$HOOK" "$(make_payload 'echo \"safe text\" > realfile.txt')"
expect_block "(q) echo x >> /tmp/out.txt (real append redirect)" "$HOOK" "$(make_payload 'echo x >> /tmp/out.txt')"
expect_block "(r) bash -c \"echo x > /tmp/out\" (eval-wrapper: quoted redirect IS executed)" "$HOOK" "$(make_payload 'bash -c \"echo x > /tmp/out\"')"

report
