#!/usr/bin/env bash
# Test: hub-concurrency-gate  (claude-configs-public#898)
#   AC1 -- reject a verified 4th-thread-open; allow the 3-thread case.
#   AC2 -- a hub over cap (drain-grandfathered) is not retroactively penalised;
#          only NEW opens are blocked, already-open peers always pass.
#   AC3 -- regression: the rejection condition trips (block scenarios below).
#          Fail-before is inherent (no hook -> no block); this proves pass-after.
# Plus the fail-open safety invariant: every error path allows (exit 0).
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/hooks/_test/run_scenarios.sh"
HOOK="$ROOT/hooks/agent-comms/hub-concurrency-gate.sh"
TMPD="$(mktemp -d)"
trap 'rm -rf "$TMPD"' EXIT

make_state() { # out N  -> hub-threads.json with N open peers (peer-1..peer-N)
  local out="$1" n="$2" i peers=""
  for ((i=1; i<=n; i++)); do
    peers="${peers}{\"peer_session\":\"peer-$i\",\"topic\":\"t\",\"kind\":\"dispatch\",\"opened_at\":\"x\",\"last_activity\":\"x\"},"
  done
  peers="${peers%,}"
  printf '{"hub_session":"hub-A","cap":3,"open_threads":[%s]}' "$peers" > "$out"
}
payload() { printf '{"session_id":"hub-A","tool_input":{"sessionId":"%s","message":"dispatch work"}}' "$1"; }
scen() { export HUB_THREADS_FILE="$1"; export HUB_THREAD_CAP="$2"; }   # state file + cap for the next assertion
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

report
