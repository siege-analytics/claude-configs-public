#!/usr/bin/env bash
# Test: hooks/lib/gate-registry.sh (#873 P0, defect D6)
#
# The registry makes gate identity data (action_class, per-runtime policy)
# instead of strings hardcoded across hooks. Every accessor must fail soft: a
# missing manifest or unknown gate returns a documented default, never an error
# exit, so a missing file degrades rather than blocks a tool call.

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LIB="$ROOT/hooks/lib/gate-registry.sh"

_PASS=0; _FAIL=0; _FAILED=()
check() {
    local name="$1" want="$2" got="$3"
    if [[ "$got" == "$want" ]]; then
        _PASS=$((_PASS+1)); printf '  [PASS] %s\n' "$name"
    else
        _FAIL=$((_FAIL+1)); _FAILED+=("$name")
        printf '  [FAIL] %s (want "%s", got "%s")\n' "$name" "$want" "$got"
    fi
}

# Build a fixture manifest so the test does not depend on dist/ being current.
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
cat > "$TMP/manifest.json" <<'JSON'
{
  "gates": [
    {"id": "think-gate", "action_class": "design",
     "runtime_policy": {"craft": "advisory", "claude-code": "advisory", "codex-cli": "advisory", "unknown": "advisory"}},
    {"id": "branch-guard", "action_class": "branch-state",
     "runtime_policy": {"craft": "block", "claude-code": "block", "codex-cli": "block", "unknown": "block"}}
  ]
}
JSON
export CCP_ENFORCEMENT_MANIFEST="$TMP/manifest.json"

# Fixture: a gate that declares no action_class (governs everything).
cat > "$TMP/noclass.json" <<'JSON'
{"gates": [{"id": "nc", "runtime_policy": {"craft": "block", "unknown": "block"}}]}
JSON

run() { bash -c ". '$LIB'; $1"; }

# --- field accessors ---
check "action_class think-gate"  design        "$(run 'gate_action_class think-gate')"
check "action_class branch-guard" branch-state "$(run 'gate_action_class branch-guard')"

# --- runtime policy, explicit runtime ---
check "policy think-gate craft"     advisory "$(run 'gate_runtime_policy think-gate craft')"
check "policy branch-guard craft"   block    "$(run 'gate_runtime_policy branch-guard craft')"
check "policy branch-guard codex"   block    "$(run 'gate_runtime_policy branch-guard codex-cli')"

# --- fail-soft: unknown gate defaults to advisory, never errors ---
check "unknown gate -> advisory" advisory "$(run 'gate_runtime_policy nonexistent craft')"
check "unknown gate action_class empty" "" "$(run 'gate_action_class nonexistent')"

# --- fail-soft: runtime not in the policy map falls back to unknown key ---
check "policy unrecognised runtime -> unknown key" advisory \
    "$(run 'gate_runtime_policy think-gate some-future-host')"

# --- fail-soft: a readable manifest with no such gate -> advisory / empty ---
# An empty-gates manifest isolates the "manifest present, gate absent" path
# without the dist/ fallback interfering. (An UNREADABLE override path falls
# back to the repo dist/ manifest by design, so it is not a clean missing case.)
cat > "$TMP/empty.json" <<'JSON'
{"gates": []}
JSON
check "empty-gates manifest -> advisory" advisory \
    "$(CCP_ENFORCEMENT_MANIFEST=$TMP/empty.json run 'gate_runtime_policy think-gate craft')"
check "empty-gates manifest action_class empty" "" \
    "$(CCP_ENFORCEMENT_MANIFEST=$TMP/empty.json run 'gate_action_class think-gate')"

# accessor must not error-exit when the gate is absent (fail-soft contract)
CCP_ENFORCEMENT_MANIFEST="$TMP/empty.json" run 'gate_runtime_policy think-gate craft' >/dev/null 2>&1
check "absent gate exits 0 (no hard error)" 0 "$?"

# --- gate_applies: the task-relevance predicate (#873 P4, defect D1) ---
# branch-guard governs branch-state and blocks under craft. think-gate governs
# design and is advisory everywhere (per the fixture manifest above).

# In-class + block policy -> block.
check "branch-guard applies to branch-state action -> block" block \
    "$(run 'gate_applies branch-guard branch-state craft')"
# Out-of-class -> advisory even though the policy is block. This is the
# "research fishing rods gate does not block list *.pdf" case.
check "branch-guard does NOT govern a mutation action -> advisory" advisory \
    "$(run 'gate_applies branch-guard mutation craft')"
check "branch-guard does NOT govern a design action -> advisory" advisory \
    "$(run 'gate_applies branch-guard design craft')"
# In-class but advisory policy -> advisory.
check "think-gate in-class design -> advisory (policy)" advisory \
    "$(run 'gate_applies think-gate design craft')"
# Unknown/empty current action is treated as in-class (conservative).
check "empty action class -> in-class (block for branch-guard)" block \
    "$(run 'gate_applies branch-guard "" craft')"
# A gate with no declared action_class governs everything.
check "gate with no action_class governs any action" block \
    "$(CCP_ENFORCEMENT_MANIFEST=$TMP/noclass.json run 'gate_applies nc mutation craft')"

echo
if [[ $_FAIL -eq 0 ]]; then
    echo "Results: $_PASS passed, 0 failed"
    exit 0
else
    echo "Results: $_PASS passed, $_FAIL failed"
    printf '  FAILED: %s\n' "${_FAILED[@]}"
    exit 1
fi
