#!/usr/bin/env bash
# Test: branch-state-guard.sh and pre-action-guard.sh are ADVISORY, not blocking.
# #873 P1 (defects D5, D1). These UserPromptSubmit hooks previously emitted
# {"continue": false}, which Craft honors as a hard turn-halt -- the root cause
# of craft-agents#49 (a detached-HEAD workspace hard-halted every Claude turn).
# They must now narrate an advisory and never emit continue:false.

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

# A workspace whose hooks/resolver holds the guards + lib, so WORKSPACE_ROOT
# (script/../..) is our fixture and log-block writes here.
WS="$TMP/ws"
mkdir -p "$WS/hooks/resolver" "$WS/hooks/lib"
cp "$ROOT/hooks/resolver/branch-state-guard.sh" "$WS/hooks/resolver/"
cp "$ROOT/hooks/resolver/pre-action-guard.sh" "$WS/hooks/resolver/"
cp -R "$ROOT/hooks/lib/." "$WS/hooks/lib/"

git -C "$WS" init -q -b main
git -C "$WS" config user.email t@e.test; git -C "$WS" config user.name t
printf 'x\n' > "$WS/f"; git -C "$WS" add f; git -C "$WS" commit -q --no-verify -m seed

# --- branch-state-guard on protected branch 'main' ---
bsg_out="$(cd "$WS" && bash hooks/resolver/branch-state-guard.sh </dev/null 2>&1)"
echo "$bsg_out" | grep -q '"continue"' && bsg_block=yes || bsg_block=no
echo "$bsg_out" | grep -qi 'advisory' && bsg_adv=yes || bsg_adv=no
check "branch-state-guard: no continue:false on protected branch" \
    "$([ "$bsg_block" = no ] && echo yes || echo no)"
check "branch-state-guard: emits an advisory" "$bsg_adv"

# --- pre-action-guard on protected branch 'main' ---
pag_out="$(cd "$WS" && bash hooks/resolver/pre-action-guard.sh </dev/null 2>&1)"
echo "$pag_out" | grep -q '"continue"' && pag_block=yes || pag_block=no
echo "$pag_out" | grep -qi 'advisory' && pag_adv=yes || pag_adv=no
check "pre-action-guard: no continue:false on protected branch" \
    "$([ "$pag_block" = no ] && echo yes || echo no)"
check "pre-action-guard: emits an advisory" "$pag_adv"

# --- pre-action-guard in DETACHED HEAD (the craft-agents#49 trigger) ---
git -C "$WS" checkout -q --detach HEAD
pag_det="$(cd "$WS" && bash hooks/resolver/pre-action-guard.sh </dev/null 2>&1)"
echo "$pag_det" | grep -q '"continue"' && det_block=yes || det_block=no
echo "$pag_det" | grep -qi 'detached' && det_msg=yes || det_msg=no
check "pre-action-guard: no continue:false in detached HEAD (#49 root cause)" \
    "$([ "$det_block" = no ] && echo yes || echo no)"
check "pre-action-guard: names detached HEAD in advisory" "$det_msg"

# --- audit log: the would-have-blocked event is recorded ---
[ -f "$WS/enforcement-blocks.jsonl" ] && log_written=yes || log_written=no
check "audit log records would-have-blocked events" "$log_written"

# --- feature branch: silent (no advisory, no block) ---
git -C "$WS" checkout -q -b feat/x
feat_out="$(cd "$WS" && bash hooks/resolver/pre-action-guard.sh </dev/null 2>&1)"
[ -z "$feat_out" ] && feat_silent=yes || feat_silent=no
check "pre-action-guard: silent on a feature branch" "$feat_silent"

echo
if [[ $_FAIL -eq 0 ]]; then
    echo "Results: $_PASS passed, 0 failed"; exit 0
else
    echo "Results: $_PASS passed, $_FAIL failed"
    printf '  FAILED: %s\n' "${_FAILED[@]}"
    printf '  bsg: %s\n  pag: %s\n  det: %s\n' "${bsg_out:0:200}" "${pag_out:0:200}" "${pag_det:0:200}"
    exit 1
fi
