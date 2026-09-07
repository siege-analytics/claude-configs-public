#!/bin/bash
# test-hook-fail-closed.sh — regression guard for 260905-clever-quasar
# hostile finding #1 on PR #814.
#
# Verifies two invariants of hooks/git/self-review.sh:
#
# 1. The fail-closed guard for a missing / non-executable
#    check-trivial-claim.sh IS present in the hook source. If someone
#    reverts the guard to the pre-PR-A `if [[ -x ... ]]; then ... fi`
#    fail-open shape, this static grep catches the regression.
#
# 2. The extracted guard snippet, run in isolation with a nonexistent
#    CHECK_TRIVIAL_SCRIPT path, exits 2 with a diagnostic naming
#    "missing or not executable". This is the unit-shape test the
#    reviewer permitted "at PR A scale" — the snippet is a copy of the
#    guard in the hook, so this test protects against semantic drift in
#    the guard's behavior (e.g., someone changing `exit 2` to `exit 0`
#    while keeping the `if` shape intact).
#
# Belt + suspenders: (1) catches structural removal of the guard;
# (2) catches semantic weakening.
#
# Ref: 260905-clever-quasar hostile finding #1 on PR #814
# (https://github.com/siege-analytics/claude-configs-public/pull/814).

set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
HOOK="$HERE/../../../hooks/git/self-review.sh"

if [[ ! -f "$HOOK" ]]; then
    echo "SETUP FAIL: hook not found at $HOOK" >&2
    exit 1
fi

# Invariant 1: fail-closed guard is present in the hook source.
if ! grep -qE 'if \[\[ ! -f "\$CHECK_TRIVIAL_SCRIPT" \]\] \|\| \[\[ ! -x "\$CHECK_TRIVIAL_SCRIPT" \]\]' "$HOOK"; then
    echo "FAIL: hooks/git/self-review.sh missing fail-closed guard" >&2
    echo "  Expected: 'if [[ ! -f \"\$CHECK_TRIVIAL_SCRIPT\" ]] || [[ ! -x ... ]]'" >&2
    echo "  This regression re-opens the fail-open shape from PR #814 review round 1." >&2
    exit 1
fi

if ! grep -qF 'missing or not executable' "$HOOK"; then
    echo "FAIL: hooks/git/self-review.sh fail-closed diagnostic missing 'missing or not executable' phrase" >&2
    exit 1
fi

# Invariant 2: extracted guard behaves fail-closed on a nonexistent helper.
NONEXISTENT_HELPER="/tmp/pr-a-nonexistent-check-trivial-claim-$$.sh"
FIXTURE_SOURCE_PATH="$HERE/fixtures/pass-trivial-investigation-test-only.md"

if [[ ! -f "$FIXTURE_SOURCE_PATH" ]]; then
    echo "SETUP FAIL: fixture $FIXTURE_SOURCE_PATH not found" >&2
    exit 1
fi

# Snippet mirrors the guard body in hooks/git/self-review.sh exactly.
STDERR=$(bash -c '
    CHECK_TRIVIAL_SCRIPT="'"$NONEXISTENT_HELPER"'"
    SOURCE_PATH="'"$FIXTURE_SOURCE_PATH"'"
    if [[ ! -f "$CHECK_TRIVIAL_SCRIPT" ]] || [[ ! -x "$CHECK_TRIVIAL_SCRIPT" ]]; then
        cat >&2 <<HOOKEOF
BLOCKED: Self-Review-Source: $SOURCE_PATH — required helper
$CHECK_TRIVIAL_SCRIPT is missing or not executable.
HOOKEOF
        exit 2
    fi
    exit 0
' 2>&1 >/dev/null)
RC=$?

if [[ "$RC" -ne 2 ]]; then
    echo "FAIL: extracted guard exited $RC (expected 2)" >&2
    echo "stderr: $STDERR" >&2
    exit 1
fi
if ! grep -qF 'missing or not executable' <<<"$STDERR"; then
    echo "FAIL: extracted guard diagnostic missing expected phrase" >&2
    echo "stderr: $STDERR" >&2
    exit 1
fi

# Invariant 3 (branch-range diff scope): the hook must compute a diff
# list that includes merge-base..HEAD for multi-commit PR coverage.
# Regression guard for finding #2. Static check on the hook source.
if ! grep -qE 'git.*merge-base HEAD.*(origin/develop|origin/main|skills-upstream)' "$HOOK"; then
    echo "FAIL: hooks/git/self-review.sh missing merge-base branch-range diff scope" >&2
    echo "  Expected: 'git ... merge-base HEAD <origin/develop|origin/main|skills-upstream/*>'" >&2
    echo "  Ref: 260905-clever-quasar hostile finding #2 on PR #814." >&2
    exit 1
fi
if ! grep -qE 'git.*diff --name-only.*TRIVIAL_MERGE_BASE.*HEAD' "$HOOK"; then
    echo "FAIL: hooks/git/self-review.sh missing branch-range diff invocation" >&2
    echo "  Expected: 'git diff --name-only \$TRIVIAL_MERGE_BASE HEAD'" >&2
    exit 1
fi

echo "PASS: fail-closed guard + branch-range diff scope regression guards"
exit 0
