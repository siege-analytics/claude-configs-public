#!/usr/bin/env bash
# Test: KB-consultation is advisory by default, blocking only on opt-in.
# #873 P5, defect D2.
#
# think-gate-guard.sh's Level-3 KB check previously emitted "BLOCKED: ..." for
# any think-gate lacking a kb section when a PROJECT.md declared knowledge_base:.
# ca-enforcement-gate.sh converts BLOCKED: into a turn halt, so an unrelated task
# got hard-stopped. P5 makes it advisory unless the project declares
# kb_enforcement: blocking.

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GUARD_SRC="$ROOT/hooks/resolver/think-gate-guard.sh"

_PASS=0; _FAIL=0; _FAILED=()
check() {
    local name="$1" cond="$2"
    if [[ "$cond" == "yes" ]]; then
        _PASS=$((_PASS+1)); printf '  [PASS] %s\n' "$name"
    else
        _FAIL=$((_FAIL+1)); _FAILED+=("$name"); printf '  [FAIL] %s\n' "$name"
    fi
}

# Build a temp workspace whose hooks/resolver holds the guard and lib, so the
# guard's WORKSPACE_ROOT (script/../..) points at our fixture.
make_ws() {
    local ws="$1" enforcement="$2"
    mkdir -p "$ws/hooks/resolver" "$ws/hooks/lib" "$ws/projects/demo"
    cp "$GUARD_SRC" "$ws/hooks/resolver/think-gate-guard.sh"
    cp -R "$ROOT/hooks/lib/." "$ws/hooks/lib/"
    # PROJECT.md that declares a knowledge base; optionally opts into blocking.
    {
        echo "---"
        echo "name: demo"
        echo "repo: demo/demo"
        echo "knowledge_base:"
        echo "  - https://kb.example/demo"
        [ "$enforcement" = "blocking" ] && echo "kb_enforcement: blocking"
        echo "---"
    } > "$ws/projects/demo/PROJECT.md"
    # A think-gate with NO kb section -> triggers the KB check.
    cat > "$ws/think-gate.json" <<JSON
{"ticket":"#demo","status":"implementing","repo_root":"$ws","claims":[{"id":"C1","claim":"x","falsifier":"y"}]}
JSON
}

run_guard() {
    local ws="$1"
    printf '{"cwd":"%s"}' "$ws" | env -u CRAFT_SESSION_ID -u CLAUDE_SESSION_ID \
        CLAUDE_THINK_GATE="$ws/think-gate.json" \
        bash "$ws/hooks/resolver/think-gate-guard.sh" 2>&1
}

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

# Default: advisory. Must mention the KB reminder but NOT print a BLOCKED: line
# that ca-enforcement would catch.
make_ws "$TMP/advisory" "default"
out_adv="$(run_guard "$TMP/advisory")"
echo "$out_adv" | grep -q "consultation" && kb_seen=yes || kb_seen=no
echo "$out_adv" | grep -q "^BLOCKED: knowledge-base" && blocked=yes || blocked=no
check "default: KB reminder is shown" "$kb_seen"
check "default: no BLOCKED: prefix (advisory)" "$([ "$blocked" = no ] && echo yes || echo no)"

# Opt-in: kb_enforcement: blocking -> BLOCKED: prefix present.
make_ws "$TMP/blocking" "blocking"
out_blk="$(run_guard "$TMP/blocking")"
echo "$out_blk" | grep -q "^BLOCKED: knowledge-base" && blocked2=yes || blocked2=no
check "opt-in: BLOCKED: prefix present when kb_enforcement blocking" "$blocked2"

echo
if [[ $_FAIL -eq 0 ]]; then
    echo "Results: $_PASS passed, 0 failed"; exit 0
else
    echo "Results: $_PASS passed, $_FAIL failed"
    printf '  FAILED: %s\n' "${_FAILED[@]}"
    printf '  --- advisory output ---\n%s\n' "${out_adv:0:400}"
    printf '  --- blocking output ---\n%s\n' "${out_blk:0:400}"
    exit 1
fi
