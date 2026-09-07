#!/bin/bash
# run-tests.sh — exercise check-trivial-claim.sh against the fixture
# matrix required by PR A (close invented-token escape).
#
# Usage:
#   scripts/discipline/tests/run-tests.sh
#
# Exits 0 if all fixtures behave as expected; exits 1 with a summary
# of failed cases otherwise. Prints one line per case: PASS / FAIL,
# fixture path, exit code, expected outcome.
#
# The runner invokes check-trivial-claim.sh with either the default
# (no --diff-files) or one of the diff-list fixtures. Cases where
# external-shape-modeling detection fires require a diff-list; cases
# that only exercise vocabulary use the default.

set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../check-trivial-claim.sh"
FIXTURES="$HERE/fixtures"

if [[ ! -x "$SCRIPT" ]]; then
    echo "runner: $SCRIPT is not executable" >&2
    exit 1
fi

# CASES: fixture-basename | expected-exit-code | diff-list-basename-or-none | diagnostic-substring-required
CASES=(
    "pass-trivial-against-state-local-only.md|0|none|"
    "fail-trivial-investigation-local-only.md|2|none|Category: 'local-only' is not in the self-review"
    "fail-trivial-investigation-internal-refactor.md|2|none|Category: 'internal-refactor' is not in the self-review"
    "fail-trivial-investigation-scoped-only.md|2|none|Category: 'scoped-only' is not in the self-review"
    "fail-trivial-investigation-invented-token.md|2|none|Category: 'repo-local-only' is not in the self-review"
    "pass-trivial-investigation-test-only.md|0|none|"
    "fail-esm-hook-diff-with-trivial-investigation.md|2|diff-list-hook-touching.txt|external-shape-modeling"
    "fail-esm-scanner-diff-with-trivial-change.md|2|diff-list-scanner-touching.txt|external-shape-modeling"
    "pass-trivial-change-prose-only-docs.md|0|none|"
    "pass-trivial-investigation-test-only.md|0|diff-list-benign.txt|"
)

RC_OVERALL=0
PASSED=0
FAILED=0

for row in "${CASES[@]}"; do
    IFS='|' read -r fixture expected diff_list required_diag <<<"$row"
    fixture_path="$FIXTURES/$fixture"
    if [[ ! -f "$fixture_path" ]]; then
        echo "FAIL   $fixture — fixture missing"
        FAILED=$((FAILED + 1))
        RC_OVERALL=1
        continue
    fi

    if [[ "$diff_list" == "none" ]]; then
        actual_stderr=$(bash "$SCRIPT" "$fixture_path" 2>&1 1>/dev/null)
        actual_rc=$?
    else
        actual_stderr=$(bash "$SCRIPT" "$fixture_path" --diff-files "$FIXTURES/$diff_list" 2>&1 1>/dev/null)
        actual_rc=$?
    fi

    outcome="PASS"
    reason=""
    if [[ "$actual_rc" != "$expected" ]]; then
        outcome="FAIL"
        reason="exit $actual_rc (expected $expected)"
    fi
    if [[ -n "$required_diag" ]] && ! grep -qF "$required_diag" <<<"$actual_stderr"; then
        outcome="FAIL"
        reason="${reason:+$reason; }diagnostic missing '$required_diag'"
    fi

    if [[ "$outcome" == "PASS" ]]; then
        PASSED=$((PASSED + 1))
        printf 'PASS   %s\n' "$fixture"
    else
        FAILED=$((FAILED + 1))
        RC_OVERALL=1
        printf 'FAIL   %s — %s\n' "$fixture" "$reason"
        printf '       stderr excerpt:\n%s\n' "$(printf '%s\n' "$actual_stderr" | sed 's/^/         /' | head -20)"
    fi
done

echo
echo "Summary: $PASSED passed, $FAILED failed."
exit "$RC_OVERALL"
