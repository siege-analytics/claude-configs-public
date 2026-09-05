#!/bin/bash
# Generic hook test harness. Used by per-hook test scripts to assert that
# a hook produces the expected exit code on a given JSON payload.
#
# Usage from a test script:
#   source hooks/_test/run_scenarios.sh
#   expect_block "scenario name" /path/to/hook.sh '<json>'
#   expect_pass  "scenario name" /path/to/hook.sh '<json>'
#   report                                # prints summary, exits non-zero on any failure
#
# A scenario passes when the hook's actual exit code matches the expected
# semantic outcome (block = exit 2; pass = exit 0). Any other exit is
# treated as a scenario failure with stderr captured.

set -uo pipefail

_HARNESS_PASS=0
_HARNESS_FAIL=0
_HARNESS_FAILED_NAMES=()

_run() {
    local expected_exit="$1"
    local name="$2"
    local hook="$3"
    local payload="$4"
    local out
    local actual_exit
    out=$(printf '%s' "$payload" | bash "$hook" 2>&1)
    actual_exit=$?
    if [[ "$actual_exit" -eq "$expected_exit" ]]; then
        _HARNESS_PASS=$((_HARNESS_PASS + 1))
        printf '  [PASS] %s (exit %d)\n' "$name" "$actual_exit"
    else
        _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
        _HARNESS_FAILED_NAMES+=("$name")
        printf '  [FAIL] %s (expected exit %d, got %d)\n' "$name" "$expected_exit" "$actual_exit"
        printf '         stderr/stdout: %s\n' "${out:0:300}"
    fi
}

expect_block() {
    _run 2 "$1" "$2" "$3"
}

expect_pass() {
    _run 0 "$1" "$2" "$3"
}

report() {
    echo
    printf 'Results: %d passed, %d failed\n' "$_HARNESS_PASS" "$_HARNESS_FAIL"
    if [[ "$_HARNESS_FAIL" -gt 0 ]]; then
        printf 'Failed scenarios:\n'
        for n in "${_HARNESS_FAILED_NAMES[@]}"; do
            printf '  - %s\n' "$n"
        done
        exit 1
    fi
    exit 0
}
