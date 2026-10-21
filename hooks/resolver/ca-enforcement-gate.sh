#!/usr/bin/env bash
# UserPromptSubmit hook — enforcement wrapper.
#
# Calls existing gate hooks (think-gate-guard, investigate-gate-guard) and
# converts their advisory output into a blocking {"continue": false} signal.
#
# Blocking mechanism:
#   1. Running each gate and capturing its output
#   2. Scanning for blocking keywords (STALE DESIGN, BLOCKED, STALE INVESTIGATION)
#   3. Emitting a SINGLE {"continue": false, "systemMessage": ...} JSON object as
#      the sole stdout when any gate blocks. NB: mixed human-text + JSON on stdout
#      does NOT parse and does NOT block under Craft Agent (empirically verified,
#      #416) — the JSON must be the only thing on stdout.
#
# The wrapper always exits 0 — blocking is done via continue:false, not exit code.
#
# Always active — no env var required. The CLAUDE_CA_ENFORCE gate was removed
# in #572 because an opt-in enforcement switch is an honor-system gap.
#
# Refs: #409, #335, #325, #416, #572

set -euo pipefail

HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"

# Runtime-aware enforcement (#892 FU1). The same block is recoverable in Claude
# Code (the systemMessage is injected and the turn proceeds) but FATAL in Craft
# (continue:false hard-halts the turn before the model runs -- the craft-agents#49
# deadlock). Rather than hardcode that here, consult each gate's runtime_policy
# from the manifest via gate-registry.sh: a gate whose policy is "block" in the
# current runtime hard-halts (continue:false); "advisory" narrates only. The
# manifest sets the UserPromptSubmit design/investigation/skill gates to block in
# claude-code/codex/unknown (recoverable) and advisory in craft (fatal).
#
# FAIL-CLOSED to the PRIOR behavior (hard-block): we only DOWNGRADE a block to
# advisory when we can POSITIVELY resolve that this gate's policy is advisory in
# a POSITIVELY-detected runtime. If the registry is unavailable, detect-host is
# missing, or the runtime is not identifiable, we keep the historical
# continue:false. That way a missing manifest can never silently switch
# enforcement off -- it only ever costs us the Craft anti-deadlock, never the
# block itself. (Getting this backwards regressed the enforcement suite: the
# tests run the hook from a copy without the manifest, so a default-advisory
# turned every hard block into a narration.)
_REG="$HOOK_DIR/../lib/gate-registry.sh"
_CA_RUNTIME=""
if [ -r "$HOOK_DIR/../lib/detect-host.sh" ]; then
    # shellcheck disable=SC1090
    . "$HOOK_DIR/../lib/detect-host.sh" 2>/dev/null || true
    command -v detect_host >/dev/null 2>&1 && _CA_RUNTIME="$(detect_host)"
fi
if [ -r "$_REG" ]; then
    # shellcheck disable=SC1090
    . "$_REG" 2>/dev/null || true
fi

# Map a run_gate label to its manifest gate id.
_ca_gate_id() {
    case "$1" in
        think-gate)        echo "think-gate" ;;
        investigate-gate)  echo "investigate-gate" ;;
        skill-enforcement) echo "skill-enforcement-gate" ;;
        *)                 echo "$1" ;;
    esac
}

# Does this gate hard-block in the current runtime? TRUE FAIL-CLOSED: returns 0
# (block) UNLESS we can POSITIVELY resolve a literal "advisory" policy from a
# present, parseable manifest for a positively-detected runtime. Every other
# path -- undetected runtime, registry not sourced, manifest unreadable, gate or
# policy absent, garbage value -- returns 0 (block), i.e. the prior behavior. A
# missing manifest can therefore never switch enforcement off; it can only cost
# the Craft anti-deadlock. Uses gate_runtime_policy_strict (echoes empty, not a
# default, when unresolved) -- NOT gate_runtime_policy, whose advisory-default
# was the review-found disablement bug (#892 FU1 review).
#
# Craft-forcing guard (#892 FU1 review f4): a spoofed CRAFT_* var in a real
# Claude Code session (CLAUDECODE set) must not downgrade enforcement. When both
# a craft marker and CLAUDECODE are present we do NOT downgrade -- treat it as
# the recoverable claude-code path and block.
_ca_gate_blocks() {
    [ -n "$_CA_RUNTIME" ] || return 0
    command -v gate_runtime_policy_strict >/dev/null 2>&1 || return 0
    # Do not honor a craft downgrade when a competing child-runtime marker is
    # ALSO present (ambiguous / spoofable). detect_host tests craft first, so a
    # stray CRAFT_* var in a real claude-code OR codex session would otherwise
    # force craft and downgrade enforcement. Reuse detect-host's OWN marker
    # arrays via _detect_host_any_set so this guard can never drift from the
    # detector's claude-code/codex marker sets -- the round-2 fix hardcoded a
    # 3-var subset and missed CLAUDE_CODE_ENTRYPOINT / CLAUDE_PROJECT_DIR
    # (#892 FU1 review r3 finding #2).
    # Guard the array expansions for `set -u`: on bash 3.2 (macOS) an empty or
    # unset array expands to an unbound-variable error, which under this hook's
    # `set -euo pipefail` would ABORT before emitting any block/advisory JSON --
    # silently dropping enforcement in the craft runtime this feature targets.
    # `${arr[@]-}` yields nothing (not an error) for an empty/unset array.
    # (#892 FU1 review r4 latent finding.)
    if [ "$_CA_RUNTIME" = "craft" ] && command -v _detect_host_any_set >/dev/null 2>&1; then
        if _detect_host_any_set "${_DETECT_HOST_CLAUDE_VARS[@]-}" 2>/dev/null \
           || _detect_host_any_set "${_DETECT_HOST_CODEX_VARS[@]-}" 2>/dev/null; then
            return 0
        fi
    fi
    local gid; gid="$(_ca_gate_id "$1")"
    [ "$(gate_runtime_policy_strict "$gid" "$_CA_RUNTIME")" != "advisory" ]
}

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

# Capture the submitted payload once and replay it to every child gate. Shell
# hooks commonly read stdin; piping the original stream directly to each child
# lets the first consumer starve later gates (#843).
INPUT_PAYLOAD="$(cat || true)"

# Collect output from each gate, check for blocking signals.
blocking=false          # any gate produced a block signal (advisory or hard)
hard_block=false        # at least one blocking gate's runtime policy is "block"
child_block_json=""     # a child's own continue:false JSON, preserved verbatim
gate_output=""

# Record a block, escalating to hard_block if this gate blocks in this runtime.
_note_block() {
    local label="$1"
    blocking=true
    if _ca_gate_blocks "$label"; then
        hard_block=true
    fi
}

run_gate() {
    local gate_script="$1"
    local label="$2"

    if [[ ! -x "$gate_script" ]]; then
        return 0
    fi

    local output rc
    set +e
    output="$(printf '%s' "$INPUT_PAYLOAD" | bash "$gate_script" 2>&1)"
    rc=$?
    set -e

    if [[ -z "$output" && "$rc" -eq 0 ]]; then
        return 0
    fi

    if [[ -n "$output" ]]; then
        gate_output="${gate_output}${label}: ${output}"$'\n'
    fi
    if [[ "$rc" -ne 0 ]]; then
        gate_output="${gate_output}${label}: exited with status ${rc}"$'\n'
        _note_block "$label"
    fi

    # Child gates may already speak Craft Agent hook JSON. A child-emitted
    # continue:false is an EXPLICIT hard-stop decision by that child and is
    # preserved UNCONDITIONALLY -- it is never subject to the runtime-policy
    # downgrade (that governs pattern/exit-code blocks this wrapper infers, not a
    # child's own structured signal). We keep the child JSON verbatim and emit it
    # as the block, honoring #843's guarantee regardless of runtime. (#892 FU1
    # review f3.)
    if [[ -n "$output" ]] && printf '%s' "$output" | python3 -c 'import json,sys
try:
    d=json.loads(sys.stdin.read())
except Exception:
    sys.exit(1)
sys.exit(0 if d.get("continue") is False else 1)' 2>/dev/null; then
        blocking=true
        hard_block=true
        [ -z "$child_block_json" ] && child_block_json="$output"
        return 0
    fi

    for pattern in "${BLOCK_PATTERNS[@]}"; do
        if echo "$output" | grep -qE "$pattern"; then
            _note_block "$label"
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

if [[ -n "$child_block_json" ]]; then
    # A child gate emitted its own continue:false (#843). Pass it through
    # VERBATIM as the sole stdout -- do not re-wrap or downgrade it. This
    # preserves the child's structured signal and systemMessage exactly, in
    # every runtime. (#892 FU1 review f3.)
    printf '%s\n' "$child_block_json"
elif [[ "$hard_block" == "true" ]]; then
    # A blocking gate's runtime policy is "block" in this runtime -> hard-halt.
    # Emit a SINGLE clean JSON object as the sole stdout. Mixed human-text + a
    # later JSON line does NOT parse and does NOT block under Craft Agent
    # (empirically verified, #416). The gate explanation rides in systemMessage.
    printf '%s' "$gate_output" | python3 -c 'import json,sys; print(json.dumps({"continue": False, "systemMessage": (sys.stdin.read().strip() or "Blocked by CA enforcement gate.")}))'
elif [[ "$blocking" == "true" ]]; then
    # A gate blocked but its runtime policy is "advisory" here (e.g. Craft, where
    # continue:false is fatal-without-recovery -- the craft-agents#49 deadlock).
    # Narrate the reason WITHOUT continue:false so the agent can act on it. This
    # is plain text (not the block JSON), so Craft does not halt the turn.
    printf '<ca-enforcement-advisory>\n%s\nThis gate is advisory in the current runtime; act on it before proceeding.\n</ca-enforcement-advisory>\n' "$(printf '%s' "$gate_output" | sed 's/[[:space:]]*$//')"
fi
