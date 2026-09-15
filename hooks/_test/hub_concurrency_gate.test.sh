#!/usr/bin/env bash
# Test: hub-concurrency-gate  (claude-configs-public#898, #915)
#   AC1 -- reject a verified 4th-thread-open; allow the 3-thread case.
#   AC2 -- a hub over cap (drain-grandfathered) is not retroactively penalised;
#          only NEW opens are blocked, already-open peers always pass.
#   AC3 -- regression: the rejection condition trips (block scenarios below).
#          Fail-before is inherent (no hook -> no block); this proves pass-after.
#   AC4 (#915) -- a stale entry (last_activity older than the staleness
#          window, or missing/unparseable) is excluded from the cap count
#          and pruned from the persisted state; a fresh entry still counts.
# Plus the fail-open safety invariant: every error path allows (exit 0).
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/hooks/_test/run_scenarios.sh"
HOOK="$ROOT/hooks/agent-comms/hub-concurrency-gate.sh"
TMPD="$(mktemp -d)"
trap 'rm -rf "$TMPD"' EXIT

now_iso() { python3 -c 'import datetime; print(datetime.datetime.now(datetime.timezone.utc).isoformat())'; }
old_iso() { python3 -c 'import datetime; print((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=7200)).isoformat())'; }

make_state() { # out N [last_activity]  -> hub-threads.json with N open peers (peer-1..peer-N)
  local out="$1" n="$2" la="${3:-$(now_iso)}" i peers=""
  for ((i=1; i<=n; i++)); do
    peers="${peers}{\"peer_session\":\"peer-$i\",\"topic\":\"t\",\"kind\":\"dispatch\",\"opened_at\":\"$la\",\"last_activity\":\"$la\"},"
  done
  peers="${peers%,}"
  printf '{"hub_session":"hub-A","cap":3,"open_threads":[%s]}' "$peers" > "$out"
}
payload() { printf '{"session_id":"hub-A","tool_input":{"sessionId":"%s","message":"dispatch work"}}' "$1"; }
scen() { export HUB_THREADS_FILE="$1"; export HUB_THREAD_CAP="$2"; export HUB_THREAD_STALE_SECONDS="${3:-3600}"; }
CAP_MSG='concurrency cap reached'

# --- AC1: allow the 3-thread case, reject the 4th ---
sf="$TMPD/ac1a.json"; make_state "$sf" 2; scen "$sf" 3
expect_pass "AC1: 2 open + new peer -> allow (opening the 3rd)" "$HOOK" "$(payload peer-new)"
sf="$TMPD/ac1b.json"; make_state "$sf" 3; scen "$sf" 3
expect_block_because "AC1: 3 open + new peer -> BLOCK (would be the 4th)" "$HOOK" "$(payload peer-new)" "$CAP_MSG"

# --- boundary ---
sf="$TMPD/b1.json"; make_state "$sf" 3; scen "$sf" 3
expect_block_because "exactly at cap (3) + new peer -> BLOCK" "$HOOK" "$(payload peer-new)" "$CAP_MSG"
sf="$TMPD/b2.json"; make_state "$sf" 2; scen "$sf" 3
expect_pass "1 below cap (2) + new peer -> allow" "$HOOK" "$(payload peer-new)"
sf="$TMPD/b3.json"; make_state "$sf" 0; scen "$sf" 0
expect_block_because "cap=0 + new peer -> BLOCK (any new thread)" "$HOOK" "$(payload peer-new)" "$CAP_MSG"

# --- AC2: over-cap grandfathering -- only NEW opens blocked ---
sf="$TMPD/ac2a.json"; make_state "$sf" 5; scen "$sf" 3
expect_pass "5 open (over cap) + EXISTING peer -> allow" "$HOOK" "$(payload peer-2)"
sf="$TMPD/ac2b.json"; make_state "$sf" 5; scen "$sf" 3
expect_block_because "5 open (over cap) + new peer -> BLOCK" "$HOOK" "$(payload peer-new)" "$CAP_MSG"
sf="$TMPD/ac2c.json"; make_state "$sf" 3; scen "$sf" 3
expect_pass "3 open (at cap) + EXISTING peer -> allow" "$HOOK" "$(payload peer-1)"

# --- fail-open safety (every error path allows) ---
sf="$TMPD/absent.json"; rm -f "$sf"; scen "$sf" 3
expect_pass "missing state file + new peer -> allow" "$HOOK" "$(payload peer-new)"
sf="$TMPD/bad.json"; printf '{ this is not valid json' > "$sf"; scen "$sf" 3
expect_pass "malformed state file + new peer -> allow" "$HOOK" "$(payload peer-new)"
sf="$TMPD/empty.json"; make_state "$sf" 3; scen "$sf" 3
expect_pass "empty target sessionId -> allow" "$HOOK" '{"session_id":"hub-A","tool_input":{"sessionId":"","message":"x"}}'
sf="$TMPD/np.json"; scen "$sf" 3
expect_pass "unparseable payload -> allow" "$HOOK" 'not even json'

# --- authoritative counter: an allowed new-thread send is recorded, then cap engages ---
sf="$TMPD/append.json"; make_state "$sf" 2; scen "$sf" 3
expect_pass "auto-append: allowed new thread (2->3)" "$HOOK" "$(payload peer-fresh)"
# the previous allow appended peer-fresh (now 3); a further new peer is now at cap.
# This block assertion IS the proof the auto-append persisted: it only trips
# because the prior allow wrote peer-fresh into the state file, taking it to 3.
expect_block_because "after auto-append reached cap, next new peer BLOCK" "$HOOK" "$(payload peer-another)" "$CAP_MSG"

# --- AC4 (#915): stale-entry pruning ---
OLD="$(old_iso)"  # ~2h old; well past the 3600s default staleness window

# All 3 open entries are stale -> pruned before the cap check -> effectively
# 0 open -> a new peer is allowed even though the file still says cap=3, 3 entries.
sf="$TMPD/stale_all.json"; make_state "$sf" 3 "$OLD"; scen "$sf" 3
expect_pass "3 stale entries (2h old, default 3600s window) + new peer -> allow (pruned)" \
  "$HOOK" "$(payload peer-new)"

# Mixed: 2 fresh + this call itself would append a 3rd -- construct the mixed
# file directly (one fresh, one stale) since make_state only sets one la value.
sf="$TMPD/stale_mixed.json"
printf '{"hub_session":"hub-A","cap":3,"open_threads":[
  {"peer_session":"peer-fresh","topic":"t","kind":"dispatch","opened_at":"%s","last_activity":"%s"},
  {"peer_session":"peer-stale","topic":"t","kind":"dispatch","opened_at":"%s","last_activity":"%s"}
]}' "$(now_iso)" "$(now_iso)" "$OLD" "$OLD" > "$sf"
scen "$sf" 3
expect_pass "1 fresh + 1 stale (of cap 3) + new peer -> allow (stale pruned, 1 fresh + 1 new = 2)" \
  "$HOOK" "$(payload peer-another)"

# 3 genuinely fresh entries still count -- staleness pruning must not touch
# active threads. This re-proves AC1's boundary using real timestamps instead
# of the placeholder "x" the pre-#915 fixture used.
sf="$TMPD/fresh3.json"; make_state "$sf" 3; scen "$sf" 3
expect_block_because "3 fresh entries + new peer -> still BLOCK (freshness preserved)" \
  "$HOOK" "$(payload peer-new)" "$CAP_MSG"

# Missing last_activity entirely -> treated as stale -> pruned.
sf="$TMPD/missing_la.json"
printf '{"hub_session":"hub-A","cap":3,"open_threads":[{"peer_session":"peer-1","topic":"t","kind":"dispatch","opened_at":"%s"}]}' "$(now_iso)" > "$sf"
scen "$sf" 1
expect_pass "missing last_activity field -> treated as stale -> pruned -> allow" \
  "$HOOK" "$(payload peer-new)"

# Malformed (unparseable) last_activity -> treated as stale -> pruned.
sf="$TMPD/bad_la.json"; make_state "$sf" 1 "not-a-timestamp"; scen "$sf" 1
expect_pass "unparseable last_activity -> treated as stale -> pruned -> allow" \
  "$HOOK" "$(payload peer-new)"

# HUB_THREAD_STALE_SECONDS override: a 2h-old entry survives under a looser
# window, and is pruned under a tighter one -- proves the env override wires
# through to the prune decision, mirroring the existing HUB_THREAD_CAP test.
sf="$TMPD/window_loose.json"; make_state "$sf" 1 "$OLD"; scen "$sf" 1 999999
expect_block_because "2h-old entry within a looser (999999s) window -> still counts -> BLOCK" \
  "$HOOK" "$(payload peer-new)" "$CAP_MSG"
sf="$TMPD/window_tight.json"; make_state "$sf" 1 "$OLD"; scen "$sf" 1 60
expect_pass "2h-old entry past a tighter (60s) window -> pruned -> allow" \
  "$HOOK" "$(payload peer-new)"

# Regression (#915 hostile-review finding 1): a stale-but-CONTINUING thread
# must still pass unconditionally, even when 3 OTHER fresh peers already
# fill the cap (this is the exact shape that reproduced the bug: 3 fresh
# at cap + 1 grandfathered-stale over cap -- pruning-before-continuation-
# check would drop the stale peer, see it's no longer "in peers", fall to
# the new-thread branch, and find 3 fresh >= cap=3 -> wrongly BLOCK it and
# lose its record. With only 2 fresh + 1 stale (under cap post-prune) the
# old bug would have silently re-created the entry instead of blocking --
# less dramatic but still wrong; this 3-fresh-plus-1 shape is the one that
# actually blocks under the pre-fix ordering, so it's the faithful repro).
sf="$TMPD/stale_continue.json"
printf '{"hub_session":"hub-A","cap":3,"open_threads":[
  {"peer_session":"peer-fresh-1","topic":"t","kind":"dispatch","opened_at":"%s","last_activity":"%s"},
  {"peer_session":"peer-fresh-2","topic":"t","kind":"dispatch","opened_at":"%s","last_activity":"%s"},
  {"peer_session":"peer-fresh-3","topic":"t","kind":"dispatch","opened_at":"%s","last_activity":"%s"},
  {"peer_session":"peer-stale-continuing","topic":"t","kind":"dispatch","opened_at":"%s","last_activity":"%s"}
]}' "$(now_iso)" "$(now_iso)" "$(now_iso)" "$(now_iso)" "$(now_iso)" "$(now_iso)" "$OLD" "$OLD" > "$sf"
scen "$sf" 3
expect_pass "cap full of fresh peers + message to a STALE-but-open peer -> still allow (continuation, not new-thread)" \
  "$HOOK" "$(payload peer-stale-continuing)"
# And its record must survive on disk (not pruned away by its own staleness).
if python3 -c "
import json
d = json.load(open('$sf'))
peers = [t['peer_session'] for t in d.get('open_threads', [])]
import sys
sys.exit(0 if 'peer-stale-continuing' in peers else 1)
"; then
  _HARNESS_PASS=$((_HARNESS_PASS + 1))
  printf '  [PASS] %s\n' "stale-but-continuing peer's own entry survives on disk"
else
  _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
  _HARNESS_FAILED_NAMES+=("stale-but-continuing peer's own entry survives on disk")
  printf '  [FAIL] %s\n' "stale-but-continuing peer's own entry survives on disk"
fi

# Boundary: prune uses >= , so an entry exactly at (or past) the window is
# pruned, and an entry just under it is not. Avoids razor-exact timing by
# using a wide enough margin (a few seconds) around a short window.
just_over_iso() { python3 -c 'import datetime; print((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=61)).isoformat())'; }
just_under_iso() { python3 -c 'import datetime; print((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=59)).isoformat())'; }
sf="$TMPD/boundary_over.json"; make_state "$sf" 1 "$(just_over_iso)"; scen "$sf" 1 60
expect_pass "61s-old entry vs 60s window -> at/past boundary -> pruned -> allow" \
  "$HOOK" "$(payload peer-new)"
sf="$TMPD/boundary_under.json"; make_state "$sf" 1 "$(just_under_iso)"; scen "$sf" 1 60
expect_block_because "59s-old entry vs 60s window -> under boundary -> still counts -> BLOCK" \
  "$HOOK" "$(payload peer-new)" "$CAP_MSG"

# Persisted-state check: after a prune, the stale entry must actually be gone
# from the on-disk file, not just excluded from this one decision.
sf="$TMPD/persist.json"; make_state "$sf" 1 "$OLD"; scen "$sf" 1
: | HUB_THREADS_FILE="$sf" HUB_THREAD_CAP=1 HUB_THREAD_STALE_SECONDS=3600 \
    bash "$HOOK" <<<"$(payload peer-new)" >/dev/null 2>&1 || true
if python3 -c "import json,sys; d=json.load(open('$sf')); sys.exit(0 if len(d.get('open_threads',[]))==1 and d['open_threads'][0]['peer_session']=='peer-new' else 1)"; then
  _HARNESS_PASS=$((_HARNESS_PASS + 1))
  printf '  [PASS] %s\n' "prune persists to disk: stale peer-1 gone, peer-new appended"
else
  _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
  _HARNESS_FAILED_NAMES+=("prune persists to disk")
  printf '  [FAIL] %s\n' "prune persists to disk: stale peer-1 gone, peer-new appended"
fi

report
