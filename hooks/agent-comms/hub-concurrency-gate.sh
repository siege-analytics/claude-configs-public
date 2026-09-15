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
# NOTE (#335): under Craft Agent, PreToolUse exit 2 has been advisory in some
# contexts. This gate uses the identical mechanism as the deployed
# no-slug-form-outbound.sh sibling on the same tool, so it inherits whatever
# blocking semantics that gate has; even if advisory it is the paired
# enforcement-of-record for the hub/SKILL.md Part 5 doctrine (writing-rules:1).
#
# Refs: siege-analytics/claude-configs-public#896, #898; electinfo hub/SKILL.md Part 5.

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

hub_session = str(payload.get("session_id") or payload.get("sessionId") or "").strip()
workspace = os.environ.get("CRAFT_AGENT_WORKSPACE") or ""
peers = [t.get("peer_session") for t in open_threads]
now = now_iso()

# Continuing an already-open thread -> always allow (never penalise grandfathered
# over-cap hubs). Touch last_activity, best-effort.
if target in peers:
    for t in open_threads:
        if t.get("peer_session") == target:
            t["last_activity"] = now
    state["open_threads"] = open_threads
    state["lastUpdated"] = now
    atomic_write(state_path, state)
    allow()

# New thread. Block iff at/over cap.
if len(open_threads) >= cap:
    peer_lines = "\n".join("  - " + str(p) for p in peers) or "  (none recorded)"
    sys.stderr.write(
        "BLOCKED: hub concurrency cap reached -- %d/%d open send_agent_message threads.\n\n"
        "hub/SKILL.md Part 5: a hub does not open a new thread while it already carries %d.\n"
        "Currently open threads (peers):\n%s\n\n"
        "To proceed, do ONE of:\n"
        "  1. Drain a concluded thread -- hand off the baton (session-coordination:4)\n"
        "     or mark it complete, then remove its entry from the hub-threads.json\n"
        "     state file so a slot frees. (Messages to an already-open peer are\n"
        "     never blocked.)\n"
        "  2. Route this new work to the board backlog (#899/#900) instead of\n"
        "     opening a 4th ad hoc thread, and pick it up when a slot frees.\n\n"
        "This is a load-shedding cap, not a hard wall: it only stops opening NEW threads.\n"
        % (len(open_threads), cap, cap, peer_lines)
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
