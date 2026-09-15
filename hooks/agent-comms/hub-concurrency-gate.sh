#!/usr/bin/env bash
# Hook: hub-concurrency-gate
# Enforces: the hub concurrency cap -- a hub may not open a 4th concurrent
#           send_agent_message thread while it already has `cap` (default 3) open.
# Trigger: PreToolUse on mcp__session__send_agent_message
#
# Sibling of no-slug-form-outbound.sh (same tool, same exit-2 block mechanism).
#
# State-file convention (the contract this gate reads):
#   The gate reads a session-scoped JSON state file, hub-threads.json, whose
#   contract is documented in the electinfo hub/SKILL.md "Part 5: Concurrency Cap"
#   (electinfo/electinfo_claude_skills). Shape:
#       { "cap": 3, "open_threads": [ {"peer_session": "<id>", ...}, ... ] }
#   The gate is the AUTHORITATIVE COUNTER: on an allowed *new-thread* send it
#   appends the target peer, so the count never depends on a hub remembering to
#   record it under load. The hub's only remaining job is to DRAIN -- remove an
#   entry when a thread concludes (baton hand-off, or completed work). This makes
#   under-restriction structurally impossible; a forgotten drain fails toward the
#   safe side (over-restriction: the hub sheds new work to the board backlog).
#
#   A message to a peer that is ALREADY an open thread always passes (it continues
#   a thread, it does not open a new one) -- so a hub grandfathered over cap by the
#   drain provision is never retroactively penalised.
#
# FAIL-OPEN by construction: every error path exits 0. The cap sheds load; it is
# never a wall that can wedge the session. Only a verified 4th-new-thread-open
# produces a block (exit 2).
#
# State file resolution (first hit wins):
#   1. $HUB_THREADS_FILE           (explicit override, used by tests)
#   2. $CRAFT_SESSION_DIR/hub-threads.json
#   3. $CRAFT_AGENT_WORKSPACE/sessions/<session-id>/hub-threads.json
# Cap resolution: $HUB_THREAD_CAP > file "cap" > 3.
#
# Staleness pruning (#915): an open_threads entry whose last_activity is
# older than the staleness window is dropped from the count -- and from the
# persisted state -- BEFORE the cap/allow decision, on every invocation
# (continuing or new-target). This is a pure time-based prune, not a
# work-type categorization (#896 decision 1 explicitly rejects categorizing
# by kind of work; this change does not reopen that -- it only changes how
# long an untouched entry survives). It answers the inactivity-window
# candidate #898 named but never implemented. A pruned-but-still-blocked
# call still persists the pruned state, so the file stays accurate even
# when the outcome is a block.
# Staleness resolution: $HUB_THREAD_STALE_SECONDS > file "stale_seconds" > 3600.
# An entry with a missing or unparseable last_activity is treated as stale
# (pruned) -- consistent with this file's fail-open ethos: ambiguous state
# resolves toward allowing more sends, never toward a stuck cap slot.
#
# NOTE (#335): under Craft Agent, PreToolUse exit 2 has been advisory in some
# contexts. This gate uses the identical mechanism as the deployed
# no-slug-form-outbound.sh sibling on the same tool, so it inherits whatever
# blocking semantics that gate has; even if advisory it is the paired
# enforcement-of-record for the hub/SKILL.md Part 5 doctrine (writing-rules:1).
#
# Refs: siege-analytics/claude-configs-public#896, #898, #915; electinfo hub/SKILL.md Part 5.

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH:/usr/local/bin:/opt/homebrew/bin"

# Fail open if python3 is unavailable -- never block on a missing interpreter.
command -v python3 >/dev/null 2>&1 || exit 0

INPUT=$(cat 2>/dev/null || true)

HUB_GATE_INPUT="$INPUT" python3 - <<'PY'
import os, sys, json, datetime, tempfile

def allow():
    sys.exit(0)

def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def parse_iso(s):
    # Returns an aware datetime, or None if s is missing/unparseable.
    # Every timestamp this script itself writes comes from now_dt.isoformat(),
    # which always emits a +00:00 offset, never a bare 'Z' suffix -- so
    # internal round-trips are safe on any Python 3.7+. A hand-edited or
    # externally-written 'Z'-suffixed timestamp would raise on Python <3.11
    # and fall through to the except below, which is fine: unparseable is
    # already documented to mean "treated as stale."
    if not s or not isinstance(s, str):
        return None
    try:
        dt = datetime.datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except Exception:
        return None

def prune_stale(open_threads, now_dt, stale_seconds):
    # Drop entries whose last_activity is older than stale_seconds, or whose
    # last_activity is missing/unparseable. Returns (kept, dropped_count).
    kept = []
    dropped = 0
    for t in open_threads:
        parsed = parse_iso(t.get("last_activity"))
        if parsed is None or (now_dt - parsed).total_seconds() >= stale_seconds:
            dropped += 1
            continue
        kept.append(t)
    return kept, dropped

def atomic_write(path, obj):
    # Best-effort atomic write; never raise to the caller.
    tmp = None
    try:
        d = os.path.dirname(path) or "."
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".hub-threads.", suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            json.dump(obj, f, indent=2)
        os.replace(tmp, path)
    except Exception:
        # A bookkeeping failure must never block the send.
        try:
            if tmp:
                os.unlink(tmp)
        except Exception:
            pass

def log_block(workspace, cap, n, target):
    if not workspace:
        return
    try:
        rec = {
            "timestamp": now_iso(),
            "gate_id": "hub-concurrency-gate",
            "invariant": "hub carries at most %d open send_agent_message threads" % cap,
            "detail": "blocked new thread to %s at %d/%d open" % (target, n, cap),
            "classified": False,
        }
        with open(os.path.join(workspace, "enforcement-blocks.jsonl"), "a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass

raw = os.environ.get("HUB_GATE_INPUT", "")
try:
    payload = json.loads(raw)
except Exception:
    allow()  # unparseable payload -> fail open

if not isinstance(payload, dict):
    allow()

tool_input = payload.get("tool_input") or {}
if not isinstance(tool_input, dict):
    allow()

# Target peer we are messaging. On mcp__session__send_agent_message this is `sessionId`.
target = str(tool_input.get("sessionId") or "").strip()
if not target:
    allow()  # cannot identify a thread -> fail open

# Resolve the state file path.
state_path = os.environ.get("HUB_THREADS_FILE") or ""
if not state_path:
    sd = os.environ.get("CRAFT_SESSION_DIR") or ""
    if sd and os.path.isdir(sd):
        state_path = os.path.join(sd, "hub-threads.json")
if not state_path:
    ws = os.environ.get("CRAFT_AGENT_WORKSPACE") or ""
    sid = str(payload.get("session_id") or payload.get("sessionId") or "").strip()
    if ws and sid:
        state_path = os.path.join(ws, "sessions", sid, "hub-threads.json")
if not state_path:
    allow()  # nowhere to track -> fail open

# Load current state; malformed or absent -> treat as zero open threads.
state = {}
open_threads = []
try:
    if os.path.exists(state_path):
        with open(state_path) as f:
            state = json.load(f) or {}
        if not isinstance(state, dict):
            state = {}
        ot = state.get("open_threads")
        if isinstance(ot, list):
            open_threads = [t for t in ot if isinstance(t, dict) and t.get("peer_session")]
except Exception:
    state, open_threads = {}, []

# Resolve cap: env override > file value > default 3.
cap = None
env_cap = os.environ.get("HUB_THREAD_CAP")
if env_cap not in (None, ""):
    try:
        cap = int(env_cap)
    except Exception:
        cap = None
if cap is None:
    try:
        cap = int(state.get("cap", 3))
    except Exception:
        cap = 3

# Resolve staleness window: env override > file value > default 3600 (#915).
stale_seconds = None
env_stale = os.environ.get("HUB_THREAD_STALE_SECONDS")
if env_stale not in (None, ""):
    try:
        stale_seconds = int(env_stale)
    except Exception:
        stale_seconds = None
if stale_seconds is None:
    try:
        stale_seconds = int(state.get("stale_seconds", 3600))
    except Exception:
        stale_seconds = 3600

hub_session = str(payload.get("session_id") or payload.get("sessionId") or "").strip()
workspace = os.environ.get("CRAFT_AGENT_WORKSPACE") or ""
now_dt = datetime.datetime.now(datetime.timezone.utc)
now = now_dt.isoformat()

# Continuing-thread check MUST happen against the PRE-prune peer list.
# A grandfathered/continuing thread is guaranteed to pass regardless of its
# own staleness (that guarantee predates #915 and is tested by AC2); pruning
# the target's own entry before this check would demote a stale-but-still-
# being-messaged peer into "new thread" territory and could block + drop it,
# contradicting the "already-open peer is never blocked" invariant. Hostile
# review (#915) caught this ordering bug before ship.
pre_prune_peers = [t.get("peer_session") for t in open_threads]

if target in pre_prune_peers:
    # Continuing an already-open thread -> always allow, unconditionally,
    # regardless of staleness (messaging it makes it fresh again). Prune
    # OTHER stale entries for on-disk hygiene, but never the target's own.
    kept_others, _ = prune_stale(
        [t for t in open_threads if t.get("peer_session") != target],
        now_dt, stale_seconds,
    )
    target_entry = next(t for t in open_threads if t.get("peer_session") == target)
    target_entry["last_activity"] = now
    open_threads = kept_others + [target_entry]
    state["open_threads"] = open_threads
    state["lastUpdated"] = now
    atomic_write(state_path, state)
    allow()

# New target: only now does staleness pruning apply to the cap decision --
# the target has no entry of its own to protect, so pruning the whole list
# is safe (#915).
open_threads, pruned_count = prune_stale(open_threads, now_dt, stale_seconds)
peers = [t.get("peer_session") for t in open_threads]

# New thread. Block iff at/over cap (post-prune).
if len(open_threads) >= cap:
    # Persist the prune even on the block path, but only when something
    # actually changed -- a block with zero pruned entries is a true no-op
    # and shouldn't write-amplify or bump lastUpdated for nothing (#915
    # hostile review finding 2).
    if pruned_count:
        state["open_threads"] = open_threads
        state["lastUpdated"] = now
        atomic_write(state_path, state)
    peer_lines = "\n".join("  - " + str(p) for p in peers) or "  (none recorded)"
    sys.stderr.write(
        "BLOCKED: hub concurrency cap reached -- %d/%d open send_agent_message threads.\n\n"
        "hub/SKILL.md Part 5: a hub does not open a new thread while it already carries %d.\n"
        "Currently open threads (peers):\n%s\n\n"
        "(Threads inactive for %d+s auto-prune on the next call -- HUB_THREAD_STALE_SECONDS.)\n\n"
        "To proceed, do ONE of:\n"
        "  1. Drain a concluded thread -- hand off the baton (session-coordination:4)\n"
        "     or mark it complete, then remove its entry from the hub-threads.json\n"
        "     state file so a slot frees. (Messages to an already-open peer are\n"
        "     never blocked.)\n"
        "  2. Wait for the board backlog (#899/#900) to ship, then route overflow\n"
        "     work there instead of opening a 4th ad hoc thread -- not available yet.\n\n"
        "This is a load-shedding cap, not a hard wall: it only stops opening NEW threads.\n"
        % (len(open_threads), cap, cap, peer_lines, stale_seconds)
    )
    log_block(workspace, cap, len(open_threads), target)
    sys.exit(2)

# Under cap -> record the open (authoritative count) and allow.
topic = (str(tool_input.get("message") or "").replace("\n", " ").strip()[:60]) or "(unspecified)"
open_threads.append({
    "peer_session": target,
    "topic": topic,
    "kind": "dispatch",
    "opened_at": now,
    "last_activity": now,
})
state["open_threads"] = open_threads
if "cap" not in state:
    state["cap"] = cap
if hub_session and not state.get("hub_session"):
    state["hub_session"] = hub_session
state["lastUpdated"] = now
atomic_write(state_path, state)
allow()
PY
exit $?
