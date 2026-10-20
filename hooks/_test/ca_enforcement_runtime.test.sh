#!/usr/bin/env bash
# Test: ca-enforcement-gate is runtime-aware (#892 FU1).
# A blocking gate hard-halts (continue:false) in a runtime whose manifest policy
# is "block" (claude-code / codex / unknown), and narrates an advisory WITHOUT
# continue:false in a runtime whose policy is "advisory" (craft). This is the
# central fix for the craft-agents#49 deadlock: continue:false is fatal in Craft.

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

_PASS=0; _FAIL=0; _FAILED=()
check() {
    local name="$1" cond="$2"
    if [[ "$cond" == "yes" ]]; then
        _PASS=$((_PASS+1)); printf '  [PASS] %s\n' "$name"
    else
        _FAIL=$((_FAIL+1)); _FAILED+=("$name"); printf '  [FAIL] %s\n' "$name"
    fi
}

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/hooks/resolver" "$TMP/hooks/lib" "$TMP/dist/craft-agent"
cp "$ROOT/hooks/resolver/ca-enforcement-gate.sh" "$TMP/hooks/resolver/"
cp "$ROOT/hooks/resolver/investigate-gate-guard.sh" "$TMP/hooks/resolver/" 2>/dev/null || true
cp "$ROOT/hooks/resolver/skill-enforcement-gate.sh" "$TMP/hooks/resolver/" 2>/dev/null || true
cp -R "$ROOT/hooks/lib/." "$TMP/hooks/lib/"
cp "$ROOT/dist/craft-agent/enforcement-manifest.json" "$TMP/dist/craft-agent/" 2>/dev/null || {
    echo "  [SKIP] no built manifest; run bin/build.py first"; exit 0; }

# Stub think-gate-guard to emit a block signal deterministically.
cat > "$TMP/hooks/resolver/think-gate-guard.sh" <<'EOF'
#!/bin/bash
echo "STALE DESIGN: premise no longer holds"
exit 0
EOF
chmod +x "$TMP"/hooks/resolver/*.sh

# Run the hook with ALL runtime markers scrubbed first, then only the ones this
# call sets. The test runner's own environment may carry CLAUDE_CODE_ENTRYPOINT /
# CLAUDECODE / CRAFT_* (we run under Claude Code), which would leak into detect_host
# and the anti-spoof guard and make results nondeterministic. Scrubbing the full
# marker set makes each scenario's runtime purely a function of what it passes.
_CA_MARKERS=(CLAUDECODE CLAUDE_CODE_ENTRYPOINT CLAUDE_PROJECT_DIR
             CRAFT_SESSION_DIR CRAFT_IS_PACKAGED CRAFT_RESOURCES_PATH
             CRAFT_BUNDLED_ASSETS_ROOT CRAFT_RPC_PORT
             CODEX_SANDBOX CODEX_SANDBOX_NETWORK_DISABLED
             CRAFT_SESSION_ID CLAUDE_SESSION_ID SESSION_ID CCP_HOOK_INPUT_JSON)
run_ca() {
    local unset_args=()
    local m
    for m in "${_CA_MARKERS[@]}"; do unset_args+=(-u "$m"); done
    printf '{}' | env "${unset_args[@]}" "$@" bash "$TMP/hooks/resolver/ca-enforcement-gate.sh" 2>&1
}

# craft -> advisory, no continue:false
craft_out="$(run_ca -u CLAUDECODE -u CODEX_SANDBOX CRAFT_RPC_PORT=9100)"
echo "$craft_out" | grep -q '"continue"' && craft_block=yes || craft_block=no
echo "$craft_out" | grep -qi 'advisory' && craft_adv=yes || craft_adv=no
check "craft: STALE DESIGN does NOT emit continue:false" \
    "$([ "$craft_block" = no ] && echo yes || echo no)"
check "craft: emits a ca-enforcement advisory" "$craft_adv"

# claude-code -> continue:false (recoverable, block preserved)
cc_out="$(run_ca -u CRAFT_RPC_PORT -u CODEX_SANDBOX CLAUDECODE=1)"
echo "$cc_out" | grep -q '"continue": false' && cc_block=yes || cc_block=no
check "claude-code: STALE DESIGN emits continue:false" "$cc_block"

# unknown runtime -> continue:false (fail-closed to prior behavior)
unk_out="$(run_ca -u CRAFT_RPC_PORT -u CLAUDECODE -u CODEX_SANDBOX -u CODEX_SANDBOX_NETWORK_DISABLED)"
echo "$unk_out" | grep -q '"continue": false' && unk_block=yes || unk_block=no
check "unknown runtime: continue:false (fail-closed to block)" "$unk_block"

# --- Review fixes (#892 FU1 review) ---------------------------------------

# F2: manifest MISSING -> fail closed to block (must NOT downgrade to advisory).
# Remove EVERY place the resolver could find a manifest under $TMP, and point the
# env override at a nonexistent path, so gate_runtime_policy_strict truly cannot
# resolve. Even a craft runtime must then block (fail-closed), not downgrade.
find "$TMP" -name enforcement-manifest.json -delete 2>/dev/null || true
missing_out="$(run_ca CCP_ENFORCEMENT_MANIFEST=/nonexistent/x.json CRAFT_RPC_PORT=9100)"
echo "$missing_out" | grep -q '"continue": false' && missing_block=yes || missing_block=no
check "F2: missing manifest fails CLOSED even in craft (continue:false)" "$missing_block"
# restore the colocated manifest for the remaining cases
cp "$ROOT/dist/craft-agent/enforcement-manifest.json" "$TMP/hooks/enforcement-manifest.json" 2>/dev/null || true

# F4: a spoofed CRAFT_* var in a CLAUDECODE session must NOT downgrade.
f4_out="$(run_ca CLAUDECODE=1 CRAFT_RPC_PORT=9100)"
echo "$f4_out" | grep -q '"continue": false' && f4_block=yes || f4_block=no
check "F4: CLAUDECODE + spoofed CRAFT_* still blocks (no downgrade)" "$f4_block"

# F4 (r3): the guard uses detect-host's FULL claude-code/codex marker arrays,
# not a hardcoded subset. CLAUDE_CODE_ENTRYPOINT and CLAUDE_PROJECT_DIR (without
# CLAUDECODE) + a spoofed CRAFT_* must also block.
f4b_out="$(run_ca -u CLAUDECODE CLAUDE_CODE_ENTRYPOINT=cli CRAFT_RPC_PORT=9100)"
echo "$f4b_out" | grep -q '"continue": false' && f4b_block=yes || f4b_block=no
check "F4: CLAUDE_CODE_ENTRYPOINT + CRAFT_* still blocks" "$f4b_block"
f4c_out="$(run_ca -u CLAUDECODE CLAUDE_PROJECT_DIR=/x CRAFT_RPC_PORT=9100)"
echo "$f4c_out" | grep -q '"continue": false' && f4c_block=yes || f4c_block=no
check "F4: CLAUDE_PROJECT_DIR + CRAFT_* still blocks" "$f4c_block"

# F3: a child-emitted continue:false passes through verbatim, hard, even in craft.
cat > "$TMP/hooks/resolver/think-gate-guard.sh" <<'EOF'
#!/bin/bash
echo '{"continue": false, "systemMessage": "child hard stop"}'
exit 0
EOF
chmod +x "$TMP/hooks/resolver/think-gate-guard.sh"
f3_out="$(run_ca -u CLAUDECODE CRAFT_RPC_PORT=9100)"
echo "$f3_out" | grep -q 'child hard stop' && echo "$f3_out" | grep -q '"continue": false' && f3_ok=yes || f3_ok=no
check "F3: child continue:false passes through verbatim under craft" "$f3_ok"

echo
if [[ $_FAIL -eq 0 ]]; then
    echo "Results: $_PASS passed, 0 failed"; exit 0
else
    echo "Results: $_PASS passed, $_FAIL failed"
    printf '  FAILED: %s\n' "${_FAILED[@]}"
    printf '  craft: %s\n  cc: %s\n  unk: %s\n' "${craft_out:0:150}" "${cc_out:0:150}" "${unk_out:0:150}"
    exit 1
fi
