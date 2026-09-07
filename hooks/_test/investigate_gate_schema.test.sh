#!/bin/bash
# Test: the worked example in skills/investigate/SKILL.md satisfies the gate
# that reads investigate-gate.json.
#
# Ref: claude-configs-public#709.
#
# The defect this covers: the skill documented `verifiedShapes` and not
# `findings`. An operator who transcribed the example got a file that passed
# investigate-gate-guard.sh, which only warns about verifiedShapes, and was
# refused by universal-mutation-gate.sh, which hard-blocks on empty findings
# with "investigation has no findings". The documentation named the advisory
# key and omitted the blocking one.
#
# The example is extracted from SKILL.md at run time rather than copied here.
# A copy would let the two drift, which is the same failure the test exists to
# catch, one level up.
#
# Assertions are on the gate's message, not on its exit code. The gate
# accumulates several independent artifact checks into one blocked exit, so
# both scenarios below exit 2 and the exit code distinguishes nothing. See the
# scenario (c) comment for why the pair is required rather than just (b).

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
MUTATION_GATE="$REPO_ROOT/hooks/bash/universal-mutation-gate.sh"
GUARD="$REPO_ROOT/hooks/resolver/investigate-gate-guard.sh"
SKILL="$REPO_ROOT/skills/investigate/SKILL.md"

PASS=0
FAIL=0
FAILED_NAMES=()

ok() {
    PASS=$((PASS + 1))
    printf '  [PASS] %s\n' "$1"
}

bad() {
    FAIL=$((FAIL + 1))
    FAILED_NAMES+=("$1")
    printf '  [FAIL] %s\n' "$1"
    printf '         %s\n' "$2"
}

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

WS="$TMP_DIR/ws"
CWD_DIR="$TMP_DIR/cwd"
mkdir -p "$WS" "$CWD_DIR"

# --- Setup: transcribe the skill's worked example, and nothing else ---

if [ ! -f "$SKILL" ]; then
    echo "SETUP FAILED: $SKILL does not exist." >&2
    exit 1
fi

BLOCK_COUNT=$(grep -c '^```json$' "$SKILL" || true)
if [ "$BLOCK_COUNT" != "1" ]; then
    echo "SETUP FAILED: expected exactly 1 json block in $SKILL, found $BLOCK_COUNT." >&2
    echo "The extraction below would take the wrong block. Update this test." >&2
    exit 1
fi

sed -n '/^```json$/,/^```$/p' "$SKILL" | sed '1d;$d' > "$WS/investigate-gate.json"

if ! python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$WS/investigate-gate.json" 2>/dev/null; then
    echo "SETUP FAILED: the json block in $SKILL is not valid JSON." >&2
    echo "An operator transcribing it cannot produce a loadable signal file." >&2
    exit 1
fi

# The gate only inspects a signal file whose ticket matches the think-gate's.
# Read the ticket out of the example rather than hardcoding it, so a change to
# the example's placeholder does not silently stop the gate from reaching the
# check. Without this the gate reports "investigate-gate.json for #X" (not
# found) and every message assertion below passes for the wrong reason.
EXAMPLE_TICKET=$(python3 -c "
import json, sys
print(json.load(open(sys.argv[1])).get('ticket', ''))
" "$WS/investigate-gate.json")

if [ -z "$EXAMPLE_TICKET" ]; then
    echo "SETUP FAILED: the documented example has no 'ticket' key." >&2
    exit 1
fi

python3 -c "
import json, sys
json.dump({'ticket': sys.argv[2], 'status': 'implementing'}, open(sys.argv[1], 'w'))
" "$WS/think-gate.json" "$EXAMPLE_TICKET"

# A command that is neither safelisted nor read-only, so the gate proceeds to
# the artifact checks instead of short-circuiting.
PAYLOAD=$(printf '{"tool_input":{"command":"tee /tmp/investigate-gate-schema-test.txt"},"cwd":"%s"}' "$CWD_DIR")

NO_FINDINGS='investigation has no findings'

run_gate() {
    printf '%s' "$PAYLOAD" \
        | CLAUDE_THINK_GATE="$WS/think-gate.json" \
          CRAFT_AGENT_WORKSPACE="$WS" \
          bash "$MUTATION_GATE" 2>&1
}

# Setup assertion: the gate must reach the investigate check at all. If the
# signal file is not found the gate says so, and every message assertion below
# would be measuring the absence of a check rather than its result.
#
# The pattern is anchored to the bullet. The gate emits the not-found case as
# its own bullet, "  - investigate-gate.json for #X", and the found-but-empty
# case as "  - investigation has no findings (investigate-gate.json for #X)".
# An unanchored match hits both, which turns this setup check into a false
# alarm on exactly the fixture scenario (c) needs.
SETUP_OUT=$(run_gate)
if printf '%s' "$SETUP_OUT" | grep -q '^  - investigate-gate\.json for'; then
    echo "SETUP FAILED: the gate did not find the signal file at $WS." >&2
    echo "Scenarios would assert against a check the gate never reached." >&2
    printf '%s\n' "$SETUP_OUT" >&2
    exit 1
fi

# --- (a) the documented example is transcribable at all ---

if grep -q '"findings"' "$WS/investigate-gate.json"; then
    ok "(a) the worked example in SKILL.md contains a findings key"
else
    bad "(a) the worked example in SKILL.md contains a findings key" \
        "The example documents verifiedShapes only. This is #709: an operator following it is blocked by universal-mutation-gate with '$NO_FINDINGS'."
fi

# --- (b) the example passes the check that hard-blocks ---

OUT_WITH=$(run_gate)
if printf '%s' "$OUT_WITH" | grep -q "$NO_FINDINGS"; then
    bad "(b) mutation gate does not report '$NO_FINDINGS' for the documented example" \
        "$(printf '%s' "$OUT_WITH" | grep "$NO_FINDINGS")"
else
    ok "(b) mutation gate does not report '$NO_FINDINGS' for the documented example"
fi

# --- (c) removing findings produces the message, so (b) is not vacuous ---
#
# This is the load-bearing scenario. Scenario (b) asserts a string is absent,
# and a string is absent from output the gate never produced. If the gate stops
# short of the investigate check, (b) passes and measures nothing. (c) mutates
# the fixture and requires the message to appear; the pair is what makes (b) an
# assertion rather than a coincidence.

python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
d.pop('findings', None)
json.dump(d, open(sys.argv[1], 'w'))
" "$WS/investigate-gate.json"

OUT_WITHOUT=$(run_gate)
if printf '%s' "$OUT_WITHOUT" | grep -q "$NO_FINDINGS"; then
    ok "(c) mutation gate reports '$NO_FINDINGS' once findings is removed"
else
    bad "(c) mutation gate reports '$NO_FINDINGS' once findings is removed" \
        "The gate did not produce the message with findings absent, so scenario (b) proves nothing. The fixture is not reaching the check."
fi

# --- (e) entry shape is not validated, only non-emptiness ---
#
# The skill tells the reader that the three recommended fields are a
# convention rather than a contract, and that a differently-shaped array still
# passes. That is a claim about the readers, so it gets a test. If a future
# change starts validating entry shape, this goes red and the skill's wording
# needs to follow.

python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
d['findings'] = [{'id': 'f1', 'statement': 'shape differs from the recommendation', 'status': 'CONFIRMED'}]
json.dump(d, open(sys.argv[1], 'w'))
" "$WS/investigate-gate.json"

OUT_OTHER=$(run_gate)
if printf '%s' "$OUT_OTHER" | grep -q "$NO_FINDINGS"; then
    bad "(e) a findings array with different entry keys still satisfies the gate" \
        "The gate rejected it, so entry shape is validated after all and the skill's 'recommended, not validated' wording is wrong."
else
    ok "(e) a findings array with different entry keys still satisfies the gate"
fi

# --- (d) the guard that reads verifiedShapes only warns, never blocks ---
#
# Records the asymmetry the skill now documents: the key with the elaborate
# validation is the advisory one. If this ever exits non-zero, the skill's
# table is wrong and #709's analysis needs revisiting.

sed -n '/^```json$/,/^```$/p' "$SKILL" | sed '1d;$d' > "$WS/investigate-gate.json"
GUARD_OUT=$(CLAUDE_THINK_GATE="$WS/think-gate.json" \
    CLAUDE_INVESTIGATE_GATE="$WS/investigate-gate.json" \
    bash "$GUARD" </dev/null 2>&1)
GUARD_EXIT=$?

if [ "$GUARD_EXIT" -eq 0 ]; then
    ok "(d) investigate-gate-guard exits 0 on the documented example (advisory, not blocking)"
else
    bad "(d) investigate-gate-guard exits 0 on the documented example (advisory, not blocking)" \
        "Exit $GUARD_EXIT. The skill documents this guard as warn-only; that claim is now false."
fi

echo
printf 'Results: %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
    printf 'Failed scenarios:\n'
    for n in "${FAILED_NAMES[@]}"; do
        printf '  - %s\n' "$n"
    done
    exit 1
fi
exit 0
