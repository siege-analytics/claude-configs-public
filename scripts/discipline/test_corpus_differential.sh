#!/bin/bash
# Test: scripts/discipline/corpus-differential.py
#
# AC3: fail-closed on unclassifiable artifact
# AC4: deliberate divergence exits non-zero
# Test-before-bulk: --limit N works so we can sanity-check without full run

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
SCRIPT="$SCRIPT_DIR/corpus-differential.py"

PASS=0
FAIL=0
FAILED=()

ok() { PASS=$((PASS + 1)); printf '  [PASS] %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); FAILED+=("$1"); printf '  [FAIL] %s\n' "$1"; printf '         %s\n' "$2"; }

# ---- (a) test-before-bulk: --limit 3 processes only 3 files
OUT=$(cd "$REPO_ROOT" && python3 "$SCRIPT" HEAD HEAD --limit 3 2>&1)
RC=$?
if [ "$RC" = "0" ] && echo "$OUT" | grep -q "3 files"; then
    ok "(a) --limit 3 processes only 3 files"
else
    bad "(a) --limit 3 processes only 3 files" "rc=$RC out=$OUT"
fi

# ---- (b) identical revs: 0 differing, exit 0
OUT=$(cd "$REPO_ROOT" && python3 "$SCRIPT" HEAD HEAD --limit 5 2>&1)
RC=$?
if [ "$RC" = "0" ] && echo "$OUT" | grep -q "0 differing"; then
    ok "(b) identical revs: 0 differing, exit 0"
else
    bad "(b) identical revs" "rc=$RC out=$OUT"
fi

# ---- (c) AC4: deliberate divergence exits non-zero
# Compare a known-divergent pair: pre-#688 guard (dda1c35) vs post-#688 (dd9db33)
if cd "$REPO_ROOT" && git rev-parse --verify dda1c35^{commit} >/dev/null 2>&1 \
    && git rev-parse --verify dd9db33^{commit} >/dev/null 2>&1; then
    OUT=$(cd "$REPO_ROOT" && python3 "$SCRIPT" dda1c35 dd9db33 --limit 5 2>&1)
    RC=$?
    if [ "$RC" != "0" ] && echo "$OUT" | grep -q "differing"; then
        ok "(c) AC4: deliberate divergence between #688 pre/post exits non-zero"
    else
        bad "(c) AC4: deliberate divergence" "rc=$RC out=$OUT"
    fi
else
    ok "(c) AC4: skipped (test revs not in this checkout's history)"
fi

# ---- (d) AC3: unresolvable rev fails closed with exit 2
OUT=$(cd "$REPO_ROOT" && python3 "$SCRIPT" deadbeefdeadbeef0000000000000000deadbeef HEAD --limit 3 2>&1)
RC=$?
if [ "$RC" = "2" ] && echo "$OUT" | grep -q "could not extract"; then
    ok "(d) AC3: unresolvable OLD_REV fails closed with exit 2"
else
    bad "(d) AC3: unresolvable OLD_REV" "rc=$RC out=$OUT"
fi

echo
printf 'Results: %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
    for n in "${FAILED[@]}"; do printf '  - %s\n' "$n"; done
    exit 1
fi
exit 0
