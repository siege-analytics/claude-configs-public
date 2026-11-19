#!/usr/bin/env bash
# A mis-tagged CRAFT_SESSION_DIR must not decide whose task gates apply (#1099).
#
# Session B holds an implementing task gate with all its artifacts. Session A
# holds none. Craft has been seen handing a hook the sibling's directory
# (electinfo/enterprise#2960); the payload's session_id is still the turn's own
# UUID, which each session records in meta/claude-turn-anchors.json. The gate
# must follow the anchor, and keep today's behaviour where no anchor exists.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
WS="$T/ws"; REPO="$T/repo"; mkdir -p "$WS" "$REPO"
cp -R "$ROOT/hooks" "$WS/hooks"; cp -R "$ROOT/bin" "$WS/bin"; cp -R "$ROOT/catalog" "$WS/catalog"
git -C "$REPO" init -q; : > "$REPO/x.py"; git -C "$REPO" add x.py
git -C "$REPO" -c user.email=a@b -c user.name=c commit -qm init
UA=aaaaaaaa-1111-4111-8111-111111111111; UB=bbbbbbbb-2222-4222-8222-222222222222
UC=cccccccc-3333-4333-8333-333333333333

slug() { python3 -c 'import importlib.util,os,sys
sys.path.insert(0,os.path.dirname(sys.argv[1]))
s=importlib.util.spec_from_file_location("r",sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);print(m.task_slug(sys.argv[2]))' "$WS/hooks/lib/resolve-think-gate.py" "$1"; }
anchor() {  # anchor <session> <sdk id>...: Craft's format, one record per final message
    local d="$WS/sessions/$1/meta" i=0 id body=""; shift; mkdir -p "$d"
    for id in "$@"; do body="$body${body:+,}\"msg-$i\":{\"sdkSessionId\":\"$id\",\"sdkMessageUuid\":\"msg_$i\"}"; i=$((i + 1)); done
    printf '{"version":1,"anchors":{%s}}\n' "$body" > "$d/claude-turn-anchors.json"
}
task_gate() {  # task_gate <session> <ticket>: an implementing gate with every artifact
    local td="$WS/sessions/$1/tasks/$(slug "$2")" g
    [[ "$td" != */tasks/ ]] || { echo "  FAIL  could not compute the task slug"; exit 1; }
    mkdir -p "$td" "$WS/sessions/$1/plans"
    g="\"ticket\":\"$2\",\"sessionId\":\"$1\",\"repo_root\":\"$REPO\",\"scope_paths\":[\"$REPO\"],\"status\":\"implementing\""
    printf '{%s}\n' "$g" > "$td/think-gate.json"
    printf '{%s,"findings":[{"claim":"verified"}]}\n' "$g" > "$td/investigate-gate.json"
    printf '{%s,"junior_found":true,"senior_found":true}\n' "$g" > "$td/junior-senior-gate.json"
    printf '{%s,"investigate_posted":true,"premortem_posted":true}\n' "$g" > "$td/artifacts-posted-gate.json"
    printf 'Ticket: %s\nSeverity: 50\nImplementation may proceed: YES\n' "$2" > "$WS/sessions/$1/plans/pre-mortem-$(basename "$td").md"
}

PASS=0; FAIL=0
# Stock macOS has no timeout(1); run unbounded there (#1109).
_tmo() { if command -v timeout >/dev/null 2>&1; then timeout "$@"; else shift; "$@"; fi; }
expect() {  # expect allow|block <label> <CRAFT_SESSION_DIR leaf> <payload uuid>
    python3 -c 'import json,sys
print(json.dumps({"session_id":sys.argv[1],"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"sed -i s/a/b/ "+sys.argv[2]+"/x.py"},"cwd":sys.argv[2]}))' "$4" "$REPO" > "$T/p.json"
    _tmo 30 env -i PATH="$PATH" HOME="$T" CRAFT_SESSION_DIR="$WS/sessions/$3" CRAFT_AGENT_WORKSPACE="$WS" \
        bash "$WS/hooks/bash/universal-mutation-gate.sh" < "$T/p.json" >/dev/null 2>"$T/err"
    local rc=$? got; got=$([[ $rc -eq 0 ]] && echo allow || echo block)
    if [[ "$got" == "$1" ]]; then PASS=$((PASS + 1)); printf '  ok    %s\n' "$2"
    else FAIL=$((FAIL + 1)); printf '  FAIL  %s (wanted %s, got %s rc=%s)\n' "$2" "$1" "$got" "$rc"; fi
}

task_gate B '#100'
mkdir -p "$WS/sessions/A"

echo "== no anchors anywhere: today's behaviour =="
expect allow "B's dir, any payload id: the env dir is trusted" B "$UA"
expect block "A's dir, no gate" A "$UA"

anchor A "$UA"; anchor B "$UB"
echo "== anchors present =="
expect allow "control: B tagged as itself" B "$UB"
expect block "control: A tagged as itself, no gate" A "$UA"
expect block "mis-tag: A's turn handed B's dir" B "$UA"
expect block "mis-tag to a session no anchor names" B "$UC"

UO=dddddddd-4444-4444-8444-444444444444
echo "== the SDK id rotates: every anchored id belongs to the session =="
anchor B "$UO" "$UB"
expect allow "B tagged as itself, current id recorded after an older one" B "$UB"
anchor B "$UO"
expect block "first turn after a rotation, new id not yet recorded: fails closed" B "$UB"
anchor B "$UB"

echo "== a mis-tag onto a sibling with no anchors =="
rm -rf "$WS/sessions/B/meta"
expect block "A's turn handed un-anchored B's dir; A is anchored, has no gate" B "$UA"
anchor B "$UB"

echo "== an anchor path that is not a regular file never hangs the hook =="
mkdir -p "$WS/sessions/0F/meta"; mkfifo "$WS/sessions/0F/meta/claude-turn-anchors.json"
start=$(date +%s)
expect block "mis-tag scan past a FIFO" B "$UA"
if (( $(date +%s) - start < 15 )); then PASS=$((PASS + 1)); echo '  ok    the scan did not block on the FIFO'
else FAIL=$((FAIL + 1)); echo '  FAIL  the scan blocked on the FIFO'; fi
rm -rf "$WS/sessions/0F"

task_gate A '#200'
echo "== the mis-tag resolves to the turn's own session =="
expect allow "A's turn handed B's dir, A has its own gate" B "$UA"
if grep -q 'named another session' "$T/err"; then PASS=$((PASS + 1)); echo '  ok    the correction is reported'
else FAIL=$((FAIL + 1)); echo '  FAIL  the correction is not reported'; fi

printf '%d passed, %d failed\n' "$PASS" "$FAIL"
(( FAIL == 0 ))
