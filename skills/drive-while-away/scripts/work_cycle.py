#!/usr/bin/env python3
"""Durable coordination checkpoints; never an authorization or review verifier.

One local journal per bounded work item. Replay validates every event; flock,
optimistic revisions and atomic replacement prevent competing writers from
silently losing a handoff. The host owns scheduling and message delivery.
"""
from __future__ import annotations

import argparse
import copy
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time

STATES = {"working", "waiting", "blocked", "needs-input", "complete-for-review"}
FIELDS = {
    "init": {"objective", "scope", "owner", "coordinator", "heartbeat_seconds",
             "chunk_seconds", "failure_budget", "next_action"},
    "checkpoint": {"state", "summary", "next_action", "dependency", "wait_seconds", "evidence"},
    "candidate": {"sha"},
    "review": {"sha", "verdict", "evidence", "failure_class"},
    "checks": {"sha", "status", "evidence"},
    "finding": {"finding_id", "summary", "evidence"},
    "resolve-finding": {"finding_id", "evidence"},
    "decision": {"failure_class", "choice", "evidence"},
    "interrupt": {"reason"},
    "resume": set(),
    "supersede": {"owner", "reason"},
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def string(value, name, *, empty=False):
    require(isinstance(value, str) and (empty or bool(value.strip())), f"{name}: expected text")
    require(len(value) <= 8000, f"{name}: text too long")


def integer(value, name, minimum=0):
    require(type(value) is int and value >= minimum, f"{name}: expected integer >= {minimum}")


def sha(value):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value), "expected exact 40-character SHA")


def evidence(value, *, empty=False):
    require(isinstance(value, list) and (empty or bool(value)), "evidence: expected references")
    for item in value:
        string(item, "evidence reference")
    require(len(value) == len(set(value)), "duplicate evidence reference")


def transition(previous, event):
    """Pure transition; timestamps are explicit for deterministic replay/tests."""
    require(isinstance(event, dict) and set(event) == {"id", "actor", "generation", "at", "kind", "data"},
            "invalid event fields")
    for key in ("id", "actor", "kind"):
        string(event[key], key)
    integer(event["at"], "at")
    integer(event["generation"], "generation", 1)
    kind, data = event["kind"], event["data"]
    require(kind in FIELDS, "unknown event kind")
    require(isinstance(data, dict) and set(data) == FIELDS[kind], f"invalid {kind} fields")
    if kind == "init":
        require(previous is None and event["generation"] == 1, "already initialized")
        for name in ("objective", "scope", "owner", "coordinator", "next_action"):
            string(data[name], name)
        require(event["actor"] == data["coordinator"], "initial actor must be coordinator")
        for name in ("heartbeat_seconds", "chunk_seconds", "failure_budget"):
            integer(data[name], name, 1)
        return {
            **data, "state": "working", "generation": 1, "candidate_sha": None,
            "review": {"verdict": "pending", "evidence": []},
            "checks": {"status": "pending", "evidence": []},
            "review_history": [], "findings": {}, "failures": {}, "decisions": [],
            "suspended_approaches": [], "ownership_history": [], "interrupted": False,
            "summary": "Work initialized", "dependency": "", "evidence": [],
            "last_checkpoint_at": event["at"], "last_progress_at": event["at"],
            "chunk_started_at": event["at"], "last_event_at": event["at"],
        }
    require(previous is not None, "initialize first")
    require(event["generation"] == previous["generation"], "stale ownership generation")
    require(event["at"] >= previous["last_event_at"], "timestamp moved backwards")
    coordinator_action = kind in {"decision", "supersede"}
    require(event["actor"] == previous["coordinator" if coordinator_action else "owner"], "wrong actor")
    s = copy.deepcopy(previous)
    if kind == "checkpoint":
        require(data["state"] in STATES, "unknown work state")
        for name in ("summary", "next_action"):
            string(data[name], name)
        string(data["dependency"], "dependency", empty=True)
        integer(data["wait_seconds"], "wait_seconds")
        evidence(data["evidence"], empty=True)
        if data["state"] in {"waiting", "blocked", "needs-input"}:
            require(bool(data["dependency"].strip()), "name the dependency or decision")
        if data["wait_seconds"]:
            require(data["state"] == "waiting", "planned wait requires waiting state")
        if s["interrupted"]:
            require(data["state"] != "working", "resume before working")
        if data["state"] == "complete-for-review":
            require(s["candidate_sha"] is not None and data["evidence"], "review handoff needs candidate and evidence")
            require(not any(v["resolved_by"] is None for v in s["findings"].values()), "unresolved findings remain")
        # Polling, repeated acknowledgements and rewording an update are not progress.
        s.update({key: data[key] for key in ("state", "summary", "next_action", "dependency", "evidence")})
        s["last_checkpoint_at"] = event["at"]
        if s["state"] == "working":
            s["chunk_started_at"] = event["at"]
    elif kind == "candidate":
        sha(data["sha"])
        if data["sha"] != s["candidate_sha"]:
            if s["candidate_sha"] is not None:
                s["review_history"].append({"sha": s["candidate_sha"], **s["review"], "invalidated": True})
            s["candidate_sha"] = data["sha"]
            s["review"] = {"verdict": "pending", "evidence": []}
            s["checks"] = {"status": "pending", "evidence": []}
            s["state"] = "waiting" if s["interrupted"] else "working"
            s["next_action"] = "Obtain review and checks for the new candidate"
    elif kind in {"review", "checks"}:
        sha(data["sha"])
        require(data["sha"] == s["candidate_sha"], "result belongs to a different candidate")
        evidence(data["evidence"])
        if kind == "checks":
            require(data["status"] in {"pending", "passed", "failed"}, "unknown check status")
            s["checks"] = {"status": data["status"], "evidence": data["evidence"]}
        else:
            verdict = data["verdict"]
            require(verdict in {"queued", "active", "accepted", "changes-required", "unavailable"}, "unknown review verdict")
            string(data["failure_class"], "failure_class", empty=True)
            require(bool(data["failure_class"]) == (verdict == "changes-required"), "failure class required only for rejection")
            require(not (verdict == "accepted" and any(v["resolved_by"] is None for v in s["findings"].values())),
                    "unresolved falsification cannot be accepted")
            record = {"verdict": verdict, "evidence": data["evidence"]}
            # Re-delivery under a new transport ID must not consume the budget twice.
            receipt = {"sha": data["sha"], **record, "failure_class": data["failure_class"], "invalidated": False}
            if receipt not in s["review_history"]:
                s["review_history"].append(receipt)
                s["review"] = record
                if verdict == "changes-required":
                    failure = data["failure_class"]
                    count = s["failures"].get(failure, 0) + 1
                    s["failures"][failure] = count
                    if count >= s["failure_budget"]:
                        if failure not in s["suspended_approaches"]:
                            s["suspended_approaches"].append(failure)
                        s["state"] = "needs-input"
                        s["dependency"] = f"Design decision for repeated failure class: {failure}"
                        s["next_action"] = "Present redesign, scope reduction, or continued repair with trade-offs"
    elif kind == "finding":
        for name in ("finding_id", "summary"):
            string(data[name], name)
        evidence(data["evidence"])
        require(data["finding_id"] not in s["findings"], "finding already exists")
        s["findings"][data["finding_id"]] = {"summary": data["summary"], "evidence": data["evidence"], "resolved_by": None}
        if s["review"]["verdict"] == "accepted":
            s["review_history"].append({"sha": s["candidate_sha"], **s["review"], "invalidated": True})
        s["review"] = {"verdict": "changes-required", "evidence": data["evidence"]}
        s["state"] = "blocked"
        s["dependency"] = "Resolve reproduced finding: " + data["finding_id"]
    elif kind == "resolve-finding":
        string(data["finding_id"], "finding_id")
        evidence(data["evidence"])
        require(data["finding_id"] in s["findings"], "unknown finding")
        s["findings"][data["finding_id"]]["resolved_by"] = data["evidence"]
        # Resolution evidence does not itself accept review.
    elif kind == "decision":
        string(data["failure_class"], "failure_class")
        string(data["choice"], "choice")
        evidence(data["evidence"])
        require(data["failure_class"] in s["suspended_approaches"], "approach is not suspended")
        s["suspended_approaches"].remove(data["failure_class"])
        s["failures"][data["failure_class"]] = 0
        s["decisions"].append(data)
        s["state"] = "waiting"
        s["dependency"] = "Plan the selected approach"
    elif kind == "interrupt":
        string(data["reason"], "reason")
        s["interrupted"] = True
        s["state"] = "waiting"
        s["dependency"] = data["reason"]
    elif kind == "resume":
        require(s["interrupted"], "work is not interrupted")
        s["interrupted"] = False
        s["state"] = "needs-input" if s["suspended_approaches"] else "waiting"
        s["dependency"] = "Reconcile live candidate, review, checks and unresolved decisions"
        s["next_action"] = "Verify external state, then checkpoint before continuing"
    elif kind == "supersede":
        string(data["owner"], "owner")
        string(data["reason"], "reason")
        require(data["owner"] != s["owner"], "successor must differ")
        s["ownership_history"].append({"owner": s["owner"], "generation": s["generation"], "reason": data["reason"]})
        s["owner"] = data["owner"]
        s["generation"] += 1
        s["interrupted"] = True
        s["state"] = "waiting"
        s["dependency"] = "Successor must resume and reconcile live state"
    # An exhausted approach stays suspended even if other work continues.
    if s["suspended_approaches"] and s["state"] == "complete-for-review":
        raise ValueError("suspended approach still requires a design decision")
    if s != previous:
        s["last_event_at"] = event["at"]
        progress = kind in {"candidate", "finding", "resolve-finding", "decision"}
        progress |= kind == "review" and data["verdict"] in {"accepted", "changes-required"}
        progress |= kind == "checks" and data["status"] in {"passed", "failed"}
        if progress:
            s["last_progress_at"] = event["at"]
    return s


def replay(journal):
    require(isinstance(journal, dict) and set(journal) == {"version", "events"} and journal["version"] == 1,
            "unsupported journal")
    require(isinstance(journal["events"], list), "events must be a list")
    state, seen = None, set()
    for event in journal["events"]:
        require(isinstance(event, dict) and isinstance(event.get("id"), str), "invalid stored event")
        require(event["id"] not in seen, "duplicate stored event id")
        seen.add(event["id"])
        state = transition(state, event)
    return state


def status(state, revision, now):
    require(state is not None, "initialize first")
    integer(now, "now")
    return {
        "revision": revision, **state,
        "checkpoint_due": now - state["last_checkpoint_at"] >= state["heartbeat_seconds"],
        "next_checkpoint_at": min(
            state["last_checkpoint_at"] + state["heartbeat_seconds"],
            state["chunk_started_at"] + state["chunk_seconds"]
            if state["state"] == "working" else state["last_checkpoint_at"] + state["heartbeat_seconds"],
        ),
        "chunk_due": state["state"] == "working" and now - state["chunk_started_at"] >= state["chunk_seconds"],
        "authorization": "not-evaluated",
        "delivery": "caller-must-publish",
        "timing": "observed-on-invocation; no background timer",
    }


def update(path, event, expected_revision):
    """Local file ownership is coordination only, not a security boundary."""
    require(path.parent.is_dir(), "journal directory must already exist")
    require(isinstance(event, dict), "event must be an object")
    with path.with_name(path.name + ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        journal = json.loads(path.read_text()) if path.exists() else {"version": 1, "events": []}
        state = replay(journal)
        for old in journal["events"]:
            if old["id"] == event.get("id"):
                require(old == event, "event id reused with different content")
                return status(state, len(journal["events"]), event["at"]), False
        require(len(journal["events"]) == expected_revision, "stale revision; reload before writing")
        new_state = transition(state, event)
        if new_state == state:
            return status(state, len(journal["events"]), event["at"]), False
        journal["events"].append(event)
        fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
        try:
            with os.fdopen(fd, "w") as out:
                json.dump(journal, out, indent=2, sort_keys=True)
                out.write("\n")
                out.flush()
                os.fsync(out.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return status(new_state, len(journal["events"]), event["at"]), True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("journal", type=Path)
    parser.add_argument("--event", type=Path, help="JSON event; omit to read without mutation")
    parser.add_argument("--expect", type=int, help="required journal revision for mutation")
    args = parser.parse_args()
    try:
        if args.event:
            require(args.expect is not None, "--event requires --expect")
            result, changed = update(args.journal, json.loads(args.event.read_text()), args.expect)
            result["changed"] = changed
        else:
            journal = json.loads(args.journal.read_text())
            result = status(replay(journal), len(journal["events"]), int(time.time()))
        print(json.dumps(result, indent=2, sort_keys=True))
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(f"work-cycle: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
