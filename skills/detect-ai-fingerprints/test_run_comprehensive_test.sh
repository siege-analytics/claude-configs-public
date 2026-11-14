#!/bin/bash
# Test: scan.sh flags run_comprehensive_test() calls inside tests/ test_*.py
# (siege-utilities SU-4 suite-runner-in-test guard, CCP#933).
#
# Hermetic temp repos (core.excludesFile=/dev/null) + `scan.sh --staged`.
set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SCAN_SH="$SCRIPT_DIR/scan.sh"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

PASS=0
FAIL=0
FAILED=()
ok()  { PASS=$((PASS + 1)); printf '  [PASS] %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); FAILED+=("$1"); printf '  [FAIL] %s\n' "$1"; printf '         %s\n' "${2:0:200}"; }

mkrepo() {
  local d="$WORK/$1"; mkdir -p "$d"
  git -C "$d" init -q
  git -C "$d" config user.email t@t
  git -C "$d" config user.name t
  git -C "$d" config core.excludesFile /dev/null
  printf 'seed\n' > "$d/README.md"; git -C "$d" add README.md; git -C "$d" commit -q -m seed
  echo "$d"
}

RULE='siege-utilities-SU4-suite-runner-in-test'

# --- Positive: call inside tests/ test_*.py -> flagged, exit 1 ---
R1=$(mkrepo pos); mkdir -p "$R1/tests"
printf 'def test_a():\n    run_comprehensive_test()\n' > "$R1/tests/test_a.py"
git -C "$R1" add tests/test_a.py
OUT1=$(cd "$R1" && bash "$SCAN_SH" 2>&1); EC1=$?
if [[ "$EC1" -eq 1 ]] && printf '%s' "$OUT1" | grep -q "$RULE"; then
  ok "call in tests/test_a.py is flagged (exit 1, rule tag present)"
else
  bad "call in tests/test_a.py should be flagged" "exit=$EC1 out=$OUT1"
fi

# --- Negative: call in a non-test source file -> not flagged ---
R2=$(mkrepo neg_src); mkdir -p "$R2/src"
printf 'def run_comprehensive_test():\n    pass\n\ndef go():\n    run_comprehensive_test()\n' > "$R2/src/mod.py"
git -C "$R2" add src/mod.py
OUT2=$(cd "$R2" && bash "$SCAN_SH" 2>&1); EC2=$?
if printf '%s' "$OUT2" | grep -q "$RULE"; then
  bad "call in src/mod.py should NOT be flagged" "exit=$EC2 out=$OUT2"
else
  ok "call in non-test src/mod.py is not flagged"
fi

# --- Negative: comment-only mention inside a test -> not flagged ---
R3=$(mkrepo neg_comment); mkdir -p "$R3/tests"
printf 'def test_b():\n    # do not call run_comprehensive_test() from here\n    assert True\n' > "$R3/tests/test_b.py"
git -C "$R3" add tests/test_b.py
OUT3=$(cd "$R3" && bash "$SCAN_SH" 2>&1); EC3=$?
if printf '%s' "$OUT3" | grep -q "$RULE"; then
  bad "comment mention should NOT be flagged" "exit=$EC3 out=$OUT3"
else
  ok "comment-only mention in test is not flagged"
fi

# --- Positive: nested pkg/tests/ test file -> flagged ---
R4=$(mkrepo pos_nested); mkdir -p "$R4/pkg/tests"
printf 'def test_c():\n    run_comprehensive_test( )\n' > "$R4/pkg/tests/test_c.py"
git -C "$R4" add pkg/tests/test_c.py
OUT4=$(cd "$R4" && bash "$SCAN_SH" 2>&1); EC4=$?
if printf '%s' "$OUT4" | grep -q "$RULE"; then
  ok "call in nested pkg/tests/test_c.py is flagged"
else
  bad "nested tests/ call should be flagged" "exit=$EC4 out=$OUT4"
fi

echo
printf 'Results: %d passed, %d failed\n' "$PASS" "$FAIL"
if [[ "$FAIL" -gt 0 ]]; then printf 'Failed:\n'; for n in "${FAILED[@]}"; do printf '  - %s\n' "$n"; done; exit 1; fi
