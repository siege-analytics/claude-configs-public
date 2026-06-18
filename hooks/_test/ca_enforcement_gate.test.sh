#!/usr/bin/env bash
# Tests for hooks/resolver/ca-enforcement-gate.sh
#
# Verifies that the CA enforcement wrapper:
#   1. Is a no-op when CLAUDE_CA_ENFORCE is unset
#   2. Blocks when think-gate outputs STALE DESIGN
#   3. Blocks when investigate-gate outputs investigation missing
#   4. Passes when all gates produce clean output
#   5. Passes when gates produce no output (no signal files)
#
# Uses mock gate scripts to simulate gate output without needing
# actual signal files or git state.
#
# Refs: #409

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK_UNDER_TEST="$SCRIPT_DIR/../resolver/ca-enforcement-gate.sh"

pass=0
fail=0

# Create a temp directory for mock gates
TMPDIR_TEST="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_TEST"' EXIT

# Create mock resolver directory structure
MOCK_RESOLVER="$TMPDIR_TEST/hooks/resolver"
mkdir -p "$MOCK_RESOLVER"

# Copy the actual hook under test
cp "$HOOK_UNDER_TEST" "$MOCK_RESOLVER/ca-enforcement-gate.sh"
chmod +x "$MOCK_RESOLVER/ca-enforcement-gate.sh"

# --- Scenario helpers ---

make_mock_gate() {
    local name="$1"
    local output="$2"
    cat > "$MOCK_RESOLVER/$name" << MOCK
#!/usr/bin/env bash
echo "$output"
MOCK
    chmod +x "$MOCK_RESOLVER/$name"
}

make_mock_gate_empty() {
    local name="$1"
    cat > "$MOCK_RESOLVER/$name" << 'MOCK'
#!/usr/bin/env bash
# no output
MOCK
    chmod +x "$MOCK_RESOLVER/$name"
}

run_test() {
    local desc="$1"
    local expected="$2"  # "pass" or "block"
    shift 2

    local output
    output="$(env "$@" bash "$MOCK_RESOLVER/ca-enforcement-gate.sh" 2>/dev/null)" || true

    if [[ "$expected" == "block" ]]; then
        if echo "$output" | grep -q '"continue": false'; then
            echo "  PASS: $desc"
            pass=$((pass + 1))
        else
            echo "  FAIL: $desc — expected continue:false, got: $(echo "$output" | tail -1)"
            fail=$((fail + 1))
        fi
    else
        if echo "$output" | grep -q '"continue": false'; then
            echo "  FAIL: $desc — unexpected continue:false in output"
            fail=$((fail + 1))
        else
            echo "  PASS: $desc"
            pass=$((pass + 1))
        fi
    fi
}

# --- Scenarios ---

echo "=== CA enforcement gate tests ==="
echo

# 1. No-op when CLAUDE_CA_ENFORCE is unset
make_mock_gate "think-gate-guard.sh" "STALE DESIGN for test#1: 1 claim(s) no longer hold."
run_test "no-op when CLAUDE_CA_ENFORCE unset" "pass" CLAUDE_CA_ENFORCE=""

# 2. Blocks on STALE DESIGN
make_mock_gate "think-gate-guard.sh" "STALE DESIGN for test#2: 2 claim(s) no longer hold."
make_mock_gate_empty "investigate-gate-guard.sh"
run_test "blocks on STALE DESIGN" "block" CLAUDE_CA_ENFORCE=1

# 3. Blocks on investigation missing
make_mock_gate_empty "think-gate-guard.sh"
make_mock_gate "investigate-gate-guard.sh" "BLOCKED: investigation has been completed (investigate-gate.json missing)."
run_test "blocks on investigation missing" "block" CLAUDE_CA_ENFORCE=1

# 4. Passes when all gates are clean
make_mock_gate "think-gate-guard.sh" "Design for test#4 is current (3 verified, 0 prose). Proceed."
make_mock_gate "investigate-gate-guard.sh" "Investigation for test#4 is current."
run_test "passes when all gates clean" "pass" CLAUDE_CA_ENFORCE=1

# 5. Passes when gates produce no output (no signal files)
make_mock_gate_empty "think-gate-guard.sh"
make_mock_gate_empty "investigate-gate-guard.sh"
run_test "passes when gates silent" "pass" CLAUDE_CA_ENFORCE=1

# 6. Blocks on EXPIRED SIGNAL
make_mock_gate "think-gate-guard.sh" "EXPIRED SIGNAL: think-gate.json for test#6 has not been updated in 48h."
make_mock_gate_empty "investigate-gate-guard.sh"
run_test "blocks on EXPIRED SIGNAL" "block" CLAUDE_CA_ENFORCE=1

# 7. Blocks on STALE INVESTIGATION
make_mock_gate_empty "think-gate-guard.sh"
make_mock_gate "investigate-gate-guard.sh" "STALE INVESTIGATION: investigate-gate.json is older than think-gate.json."
run_test "blocks on STALE INVESTIGATION" "block" CLAUDE_CA_ENFORCE=1

echo
echo "Results: $pass passed, $fail failed"

if [[ $fail -gt 0 ]]; then
    exit 1
fi
