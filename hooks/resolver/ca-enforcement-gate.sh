#!/usr/bin/env bash
# UserPromptSubmit hook — Craft Agent enforcement wrapper.
#
# Calls existing gate hooks (think-gate-guard, investigate-gate-guard) and
# converts their advisory output into a blocking {"continue": false} signal
# when running under Craft Agent enforcement mode.
#
# Under Claude Code CLI, the PreToolUse hooks block via exit 2. Under Craft
# Agent, exit 2 is advisory only (#335). This wrapper provides the CA
# enforcement surface by:
#   1. Running each gate and capturing its output
#   2. Scanning for blocking keywords (STALE DESIGN, BLOCKED, STALE INVESTIGATION)
#   3. Emitting a SINGLE {"continue": false, "systemMessage": ...} JSON object as
#      the sole stdout when any gate blocks. NB: mixed human-text + JSON on stdout
#      does NOT parse and does NOT block under Craft Agent (empirically verified,
#      #416) — the JSON must be the only thing on stdout.
#
# The wrapper always exits 0 — blocking is done via continue:false, not exit code.
#
# Activation: set CLAUDE_CA_ENFORCE=1 in the environment (the installer does this).
# When CLAUDE_CA_ENFORCE is unset or empty, this hook is a no-op (the original
# hooks still fire and produce advisory output via their own settings entries).
#
# Refs: #409, #335, #325, #416

set -euo pipefail

# Only enforce when CA enforcement mode is active.
if [[ "${CLAUDE_CA_ENFORCE:-}" != "1" ]]; then
    exit 0
fi

HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"

# Blocking keyword patterns.  These match the output of existing gates.
# If a gate changes its output format, the enforcement-manifest.json (generated
# by build.py) documents the expected patterns for auditability.
BLOCK_PATTERNS=(
    "STALE DESIGN"
    "STALE INVESTIGATION"
    "^BLOCKED:"
    "investigation has been completed.*missing"
    "EXPIRED SIGNAL"
    "SCOPE MISMATCH"
)

# Collect output from each gate, check for blocking signals.
blocking=false
gate_output=""

run_gate() {
    local gate_script="$1"
    local label="$2"

    if [[ ! -x "$gate_script" ]]; then
        return 0
    fi

    local output
    output="$(bash "$gate_script" 2>/dev/null)" || true

    if [[ -z "$output" ]]; then
        return 0
    fi

    gate_output="${gate_output}${output}"$'\n'

    for pattern in "${BLOCK_PATTERNS[@]}"; do
        if echo "$output" | grep -qE "$pattern"; then
            blocking=true
            return 0
        fi
    done
}

# Run gates that should block under CA enforcement.
# These are the real-time gates (fire every turn, catch before work begins).
# Push-time gates (self-review, branch-guard) are handled by native git hooks.
run_gate "$HOOK_DIR/think-gate-guard.sh" "think-gate"
run_gate "$HOOK_DIR/investigate-gate-guard.sh" "investigate-gate"
run_gate "$HOOK_DIR/skill-enforcement-gate.sh" "skill-enforcement"

if [[ "$blocking" == "true" ]]; then
    # Emit a SINGLE clean JSON object as the sole stdout. Mixed human-text + a
    # later JSON line does NOT parse and does NOT block under Craft Agent
    # (empirically verified, #416). The gate explanation rides in systemMessage.
    printf '%s' "$gate_output" | python3 -c 'import json,sys; print(json.dumps({"continue": False, "systemMessage": (sys.stdin.read().strip() or "Blocked by CA enforcement gate.")}))'
fi
