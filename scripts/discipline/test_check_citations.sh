#!/bin/bash
# Test: scripts/discipline/check-citations.py
#
# Covers AC3 (each failure mode separately) and AC4 (correct-by-design negative).

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SCRIPT="$SCRIPT_DIR/check-citations.py"

PASS=0
FAIL=0
FAILED=()

ok() { PASS=$((PASS + 1)); printf '  [PASS] %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); FAILED+=("$1"); printf '  [FAIL] %s\n' "$1"; printf '         %s\n' "$2"; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# Create a fixture repo with a small file
mkdir -p "$TMP/repo/tests"
git init -q "$TMP/repo" 2>&1 >/dev/null
cd "$TMP/repo"
git config user.email test@test
git config user.name test
printf 'line1\nline2\nline3\nline4\nline5\n' > tests/existing.py
git add -A
git commit -q -m "seed"
cd - >/dev/null

# (a) valid citation resolves cleanly
cat > "$TMP/case_a.md" <<'EOF'
See `tests/existing.py:3` for the anchor.
EOF
OUT=$(python3 "$SCRIPT" --repo-root "$TMP/repo" "$TMP/case_a.md" 2>&1)
RC=$?
if [ "$RC" = "0" ] && echo "$OUT" | grep -q "1 entries, 0 unresolved"; then
    ok "(a) valid citation resolves and exits 0"
else
    bad "(a) valid citation resolves and exits 0" "rc=$RC out=$OUT"
fi

# (b) citation to a file that does not exist
cat > "$TMP/case_b.md" <<'EOF'
See `tests/missing.py:3` for the anchor.
EOF
OUT=$(python3 "$SCRIPT" --repo-root "$TMP/repo" "$TMP/case_b.md" 2>&1)
RC=$?
if [ "$RC" != "0" ] && echo "$OUT" | grep -q "path not resolved"; then
    ok "(b) missing-file citation surfaces as unresolved and exits non-zero"
else
    bad "(b) missing-file citation surfaces as unresolved" "rc=$RC out=$OUT"
fi

# (c) range whose upper bound exceeds the file (finding 9-4 shape)
cat > "$TMP/case_c.md" <<'EOF'
See `tests/existing.py:1-99` for the anchor.
EOF
OUT=$(python3 "$SCRIPT" --repo-root "$TMP/repo" "$TMP/case_c.md" 2>&1)
RC=$?
if [ "$RC" != "0" ] && echo "$OUT" | grep -q "upper bound 99 exceeds file length 5"; then
    ok "(c) upper-bound-exceeds surfaces as unresolved (finding 9-4 shape)"
else
    bad "(c) upper-bound-exceeds surfaces" "rc=$RC out=$OUT"
fi

# (d) range whose lower bound is below 1
cat > "$TMP/case_d.md" <<'EOF'
See `tests/existing.py:0-3` for the anchor.
EOF
OUT=$(python3 "$SCRIPT" --repo-root "$TMP/repo" "$TMP/case_d.md" 2>&1)
RC=$?
if [ "$RC" != "0" ] && echo "$OUT" | grep -q "lower bound 0 is < 1"; then
    ok "(d) lower-bound-below-one surfaces as unresolved"
else
    bad "(d) lower-bound-below-one surfaces" "rc=$RC out=$OUT"
fi

# (e) bare basename resolves via git ls-files
cat > "$TMP/case_e.md" <<'EOF'
See `existing.py:2` for the anchor.
EOF
OUT=$(python3 "$SCRIPT" --repo-root "$TMP/repo" "$TMP/case_e.md" 2>&1)
RC=$?
if [ "$RC" = "0" ] && echo "$OUT" | grep -q "1 entries, 0 unresolved"; then
    ok "(e) bare-basename citation resolves via git ls-files"
else
    bad "(e) bare-basename resolves via git ls-files" "rc=$RC out=$OUT"
fi

# (f) AC4 correct-by-design negative: a token WITHOUT a line number is NOT counted
cat > "$TMP/case_f.md" <<'EOF'
See `tests/existing.py` (no line number) for the anchor.
EOF
OUT=$(python3 "$SCRIPT" --repo-root "$TMP/repo" "$TMP/case_f.md" 2>&1)
RC=$?
if [ "$RC" = "0" ] && echo "$OUT" | grep -q "0 entries"; then
    ok "(f) token without line number is not counted as citation (AC4)"
else
    bad "(f) token-without-line-number-not-counted" "rc=$RC out=$OUT"
fi

echo
printf 'Results: %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
    for n in "${FAILED[@]}"; do printf '  - %s\n' "$n"; done
    exit 1
fi
exit 0
