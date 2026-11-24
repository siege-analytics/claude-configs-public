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
# Build a disposable manifest fixture from the checked-in source contract. This
# test exercises runtime resolution; the separate manifest test checks generated
# artifact drift. It must not silently skip on a clean checkout with no dist/.
python3 - "$ROOT" "$TMP/dist/craft-agent/enforcement-manifest.json" <<'PY'
import importlib.util, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("build", root / "bin" / "build.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
pathlib.Path(sys.argv[2]).write_text(json.dumps({"gates": mod.CA_ENFORCEMENT_GATES}))
PY
cp "$TMP/dist/craft-agent/enforcement-manifest.json" "$TMP/source-manifest.json"

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
cp "$TMP/source-manifest.json" "$TMP/hooks/enforcement-manifest.json"

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

# Mixed markers from a real packaged Craft ancestor must permit recovery.
# ps is stubbed at the OS-observation boundary, not with an enforcement bypass.
mkdir -p "$TMP/process-fixture"
cat > "$TMP/process-fixture/ps" <<'EOF'
#!/bin/bash
ancestor=$(/bin/ps -p "$PPID" -o ppid= | tr -d ' ')
printf '%s 1 /Applications/Craft Agents.app/Contents/MacOS/Craft Agents\n' "$ancestor"
EOF
chmod +x "$TMP/process-fixture/ps"
# A PATH-provided ps must not establish host identity in the production copy.
spoof_out="$(run_ca PATH="$TMP/process-fixture:$PATH" CRAFT_IS_PACKAGED=true CLAUDE_CODE_ENTRYPOINT=sdk-ts)"
echo "$spoof_out" | grep -q '"continue": false' && spoof_ok=yes || spoof_ok=no
check "PATH-provided ps cannot forge Craft ancestry" "$spoof_ok"
# Redirect only this disposable test copy's absolute observation boundary.
# Production never reads an environment override for the process probe.
python3 - "$TMP/hooks/resolver/ca-enforcement-gate.sh" "$TMP/process-fixture/ps" <<'PY'
from pathlib import Path
import json, sys
p = Path(sys.argv[1])
s = p.read_text()
assert s.count('["/bin/ps",') == 1
p.write_text(s.replace('["/bin/ps",', '[' + json.dumps(sys.argv[2]) + ','))
PY
for marker in CLAUDE_CODE_ENTRYPOINT=sdk-ts CLAUDECODE=1 CODEX_SANDBOX=seatbelt; do
    nested_out="$(run_ca PATH="$TMP/process-fixture:$PATH" CRAFT_IS_PACKAGED=true CRAFT_SESSION_DIR=/session "$marker")"
    echo "$nested_out" | grep -q '<ca-enforcement-advisory>' && nested_ok=yes || nested_ok=no
    check "verified Craft ancestor + $marker permits advisory recovery" "$nested_ok"
done
# A Craft server on Linux runs as Bun from the server package entry point, not
# under the macOS app-bundle executable. This exact process ancestry must also
# downgrade prompt-time blocks to advisories when Claude's child marker is set.
cat > "$TMP/process-fixture/ps" <<'EOF'
#!/bin/bash
ancestor=$(/bin/ps -p "$PPID" -o ppid= | tr -d ' ')
printf '%s 1 /app/vendor/bun/bun run /app/packages/server/src/index.ts --allow-insecure-bind\n' "$ancestor"
EOF
linux_out="$(run_ca PATH="$TMP/process-fixture:$PATH" CRAFT_RPC_PORT=9100 CLAUDECODE=1)"
echo "$linux_out" | grep -q '<ca-enforcement-advisory>' && linux_ok=yes || linux_ok=no
check "verified Linux Craft server ancestor + Claude marker permits advisory recovery" "$linux_ok"
cat > "$TMP/process-fixture/ps" <<'EOF'
#!/bin/bash
ancestor=$(/bin/ps -p "$PPID" -o ppid= | tr -d ' ')
printf '%s 1 bun /app/packages/server/src/index.ts/other.ts --allow-insecure-bind\n' "$ancestor"
EOF
bare_prefix_out="$(run_ca PATH="$TMP/process-fixture:$PATH" CRAFT_RPC_PORT=9100 CLAUDECODE=1)"
echo "$bare_prefix_out" | grep -q '"continue": false' && bare_prefix_ok=yes || bare_prefix_ok=no
check "Linux Craft bare-bun entrypoint rejects a path-prefix lookalike" "$bare_prefix_ok"
cat > "$TMP/process-fixture/ps" <<'EOF'
#!/bin/bash
ancestor=$(/bin/ps -p "$PPID" -o ppid= | tr -d ' ')
printf '%s 1 /app/vendor/bun/bun run /app/packages/server/src/index.ts/other.ts\n' "$ancestor"
EOF
vendor_prefix_out="$(run_ca PATH="$TMP/process-fixture:$PATH" CRAFT_RPC_PORT=9100 CLAUDECODE=1)"
echo "$vendor_prefix_out" | grep -q '"continue": false' && vendor_prefix_ok=yes || vendor_prefix_ok=no
check "Linux vendor-bun entrypoint rejects a path-prefix lookalike" "$vendor_prefix_ok"
cat > "$TMP/process-fixture/ps" <<'EOF'
#!/bin/bash
ancestor=$(/bin/ps -p "$PPID" -o ppid= | tr -d ' ')
printf '%s 1 /Applications/Other.app/Contents/MacOS/Other\n' "$ancestor"
printf '999999 1 /Applications/Craft Agents.app/Contents/MacOS/Craft Agents\n'
EOF
foreign_out="$(run_ca PATH="$TMP/process-fixture:$PATH" CRAFT_IS_PACKAGED=true CLAUDE_CODE_ENTRYPOINT=sdk-ts)"
echo "$foreign_out" | grep -q '"continue": false' && foreign_ok=yes || foreign_ok=no
check "unrelated Craft process cannot establish ancestry" "$foreign_ok"
cat > "$TMP/process-fixture/ps" <<'EOF'
#!/bin/bash
ancestor=$(/bin/ps -p "$PPID" -o ppid= | tr -d ' ')
printf '%s 1 /tmp/Craft Agents.app/Contents/MacOS/Craft Agents\n' "$ancestor"
EOF
lookalike_out="$(run_ca PATH="$TMP/process-fixture:$PATH" CRAFT_IS_PACKAGED=true CLAUDE_CODE_ENTRYPOINT=sdk-ts)"
echo "$lookalike_out" | grep -q '"continue": false' && lookalike_ok=yes || lookalike_ok=no
check "a lookalike temporary app path cannot establish host identity" "$lookalike_ok"
printf '#!/bin/bash\nexit 1\n' > "$TMP/process-fixture/ps"
failed_ps="$(run_ca PATH="$TMP/process-fixture:$PATH" CRAFT_IS_PACKAGED=true CLAUDE_CODE_ENTRYPOINT=sdk-ts)"
echo "$failed_ps" | grep -q '"continue": false' && failed_ok=yes || failed_ok=no
check "failed ancestry probe keeps standalone block" "$failed_ok"

# Linux Craft may run without /bin/ps, with the Craft server as PID 1. Exercise
# the procfs fallback in a disposable copy; production has no path override.
PROC_FIXTURE="$TMP/proc-fixture"
mkdir -p "$PROC_FIXTURE/1" "$PROC_FIXTURE/2"
cp "$ROOT/hooks/resolver/ca-enforcement-gate.sh" "$TMP/hooks/resolver/ca-enforcement-gate.sh"
printf '1 (bun) S 0 1 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0\n' > "$PROC_FIXTURE/1/stat"
printf 'bun\0/app/packages/server/src/index.ts\0' > "$PROC_FIXTURE/1/cmdline"
printf '2 (claude child) S 1 2 2 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0\n' > "$PROC_FIXTURE/2/stat"
printf 'claude\0--session-id\0test\0' > "$PROC_FIXTURE/2/cmdline"
python3 - "$TMP/hooks/resolver/ca-enforcement-gate.sh" "$PROC_FIXTURE" <<'PY'
from pathlib import Path
import json, sys
p = Path(sys.argv[1])
s = p.read_text()
assert s.count('["/bin/ps",') == 1
assert s.count('proc_root = "/proc"') == 1
assert s.count('pid = os.getppid()') == 2
s = s.replace('["/bin/ps",', '["/missing/ps",')
s = s.replace('proc_root = "/proc"', 'proc_root = ' + json.dumps(sys.argv[2]))
s = s.replace('pid = os.getppid()', 'pid = 2')
p.write_text(s)
PY
proc_craft_out="$(run_ca PATH="$TMP/process-fixture:$PATH" CRAFT_IS_PACKAGED=true CLAUDE_CODE_ENTRYPOINT=sdk-ts CRAFT_SESSION_DIR=/session)"
echo "$proc_craft_out" | grep -q '<ca-enforcement-advisory>' && proc_craft_ok=yes || proc_craft_ok=no
check "no-ps Linux Craft fallback recognizes server at PID 1" "$proc_craft_ok"
printf 'bun\0/app/packages/server/src/index.ts/other.ts\0' > "$PROC_FIXTURE/1/cmdline"
proc_prefix_out="$(run_ca PATH="$TMP/process-fixture:$PATH" CRAFT_IS_PACKAGED=true CLAUDE_CODE_ENTRYPOINT=sdk-ts CRAFT_SESSION_DIR=/session)"
echo "$proc_prefix_out" | grep -q '"continue": false' && proc_prefix_ok=yes || proc_prefix_ok=no
check "no-ps fallback rejects a bare-bun path-prefix lookalike" "$proc_prefix_ok"
printf '/app/vendor/bun/bun\0run\0/app/packages/server/src/index.ts/other.ts\0' > "$PROC_FIXTURE/1/cmdline"
proc_vendor_prefix_out="$(run_ca PATH="$TMP/process-fixture:$PATH" CRAFT_IS_PACKAGED=true CLAUDE_CODE_ENTRYPOINT=sdk-ts CRAFT_SESSION_DIR=/session)"
echo "$proc_vendor_prefix_out" | grep -q '"continue": false' && proc_vendor_prefix_ok=yes || proc_vendor_prefix_ok=no
check "no-ps fallback rejects a vendor-bun path-prefix lookalike" "$proc_vendor_prefix_ok"
printf '1 (init) S 0 1 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0\n' > "$PROC_FIXTURE/1/stat"
printf '/sbin/init\0' > "$PROC_FIXTURE/1/cmdline"
ordinary_init_out="$(run_ca PATH="$TMP/process-fixture:$PATH" CRAFT_IS_PACKAGED=true CLAUDE_CODE_ENTRYPOINT=sdk-ts CRAFT_SESSION_DIR=/session)"
echo "$ordinary_init_out" | grep -q '"continue": false' && ordinary_init_ok=yes || ordinary_init_ok=no
check "no-ps fallback inspects PID 1 and rejects ordinary init" "$ordinary_init_ok"
noncraft_out="$(run_ca PATH="$TMP/process-fixture:$PATH" CRAFT_IS_PACKAGED=true CLAUDECODE=1 CRAFT_RPC_PORT=9100)"
echo "$noncraft_out" | grep -q '"continue": false' && noncraft_ok=yes || noncraft_ok=no
check "no-ps fallback does not treat non-Craft ancestry as Craft" "$noncraft_ok"

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
