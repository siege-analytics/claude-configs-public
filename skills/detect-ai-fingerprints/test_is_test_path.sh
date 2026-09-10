#!/bin/bash
# Test: _is_test_path segment-anchored boundary check (#771 m-6)
#
# Regression against a substring-match bug where `test_` matched anywhere
# in a path, false-classifying `tester_lib.py`, `tests_helper.py`,
# `test_bench.py`-in-middle-of-name as test paths.

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SCAN="$SCRIPT_DIR/scan_ast.py"

PASS=0
FAIL=0
FAILED=()

ok() { PASS=$((PASS + 1)); printf '  [PASS] %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); FAILED+=("$1"); printf '  [FAIL] %s\n' "$1"; printf '         %s\n' "$2"; }

check() {
    local path="$1"
    local expected="$2"  # "true" or "false"
    local label="$3"
    local got
    got=$(python3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location('scan_ast', '$SCAN')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print('true' if m._is_test_path('$path') else 'false')
")
    if [ "$got" = "$expected" ]; then
        ok "$label ($path -> $got)"
    else
        bad "$label ($path)" "got=$got want=$expected"
    fi
}

# True cases: canonical test paths
check "tests/test_foo.py"        "true"  "(a) tests/test_foo.py"
check "foo/tests/test_bar.py"    "true"  "(b) foo/tests/test_bar.py"
check "test/quick.py"            "true"  "(c) test/ leading dir"
check "test_foo.py"              "true"  "(d) test_ basename"
check "foo_test.py"              "true"  "(e) _test.py suffix"
check "foo/test_bench.py"        "true"  "(f) subdir test_bench.py"

# False cases: NOT test paths (m-6 regressions)
check "tests_helper.py"          "false" "(g) tests_helper.py (m-6)"
check "tester_lib.py"            "false" "(h) tester_lib.py (m-6)"
check "foo/tests_helper.py"      "false" "(i) foo/tests_helper.py (m-6)"
check "foo/tester_lib.py"        "false" "(j) foo/tester_lib.py (m-6)"
check "src/foo.py"               "false" "(k) src/foo.py"
check "src/testing.py"           "false" "(l) testing.py (no _ after test)"
check "src/testfoo.py"           "false" "(m) testfoo.py (no _ after test)"

echo
printf 'Results: %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
    for n in "${FAILED[@]}"; do printf '  - %s\n' "$n"; done
    exit 1
fi
exit 0
