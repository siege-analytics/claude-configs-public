#!/usr/bin/env python3
"""Deterministic long-chain/restart and competing-writer coordination scenarios."""
import concurrent.futures
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

# This helper is also a packaged skill asset: importing tests must not add a
# machine-specific .pyc file to its canonical source tree.
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/drive-while-away/scripts/work_cycle.py"
spec = importlib.util.spec_from_file_location("work_cycle", SCRIPT)
wc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wc)
SHA_A, SHA_B, SHA_C = "a" * 40, "b" * 40, "c" * 40


class WorkCycleTest(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.state = None
        self.step("init", {
            "objective": "Finish #1005", "scope": "coordination only", "owner": "worker",
            "coordinator": "hub", "heartbeat_seconds": 60, "chunk_seconds": 120,
            "failure_budget": 2, "next_action": "Implement a checkpoint",
        }, actor="hub")

    def event(self, kind, data, actor=None):
        return {"id": str(len(self.events)), "at": 1000 + len(self.events) * 10,
                "actor": actor or self.state["owner"], "generation": self.state["generation"] if self.state else 1,
                "kind": kind, "data": data}

    def step(self, kind, data, actor=None):
        event = self.event(kind, data, actor)
        self.state = wc.transition(self.state, event)
        self.events.append(event)
        return event

    def candidate(self, value=SHA_A):
        self.step("candidate", {"sha": value})

    def review(self, verdict="accepted", failure="", proof="pr/review/1"):
        return self.step("review", {"sha": self.state["candidate_sha"], "verdict": verdict,
                                    "failure_class": failure, "evidence": [proof]})

    def checkpoint(self, state="working", wait=0):
        return self.step("checkpoint", {"state": state, "summary": "Focused tests finished",
                         "next_action": "Read reviewer result", "dependency": "reviewer", "wait_seconds": wait,
                         "evidence": ["tests.log"]})

    def test_changed_head_invalidates_review_and_checks(self):
        self.candidate(); self.review()
        self.step("checks", {"sha": SHA_A, "status": "passed", "evidence": ["ci/1"]})
        self.candidate(SHA_B)
        self.assertEqual(self.state["review"]["verdict"], "pending")
        self.assertEqual(self.state["checks"]["status"], "pending")
        self.assertTrue(any(r["sha"] == SHA_A and r["invalidated"] for r in self.state["review_history"]))
        with self.assertRaisesRegex(ValueError, "different candidate"):
            self.step("review", {"sha": SHA_A, "verdict": "accepted", "failure_class": "", "evidence": ["stale"]})

    def test_recurring_class_escalates_across_heads_and_restart(self):
        for head in (SHA_A, SHA_B):
            self.candidate(head); self.review("changes-required", "parser ambiguity", head)
        self.assertEqual(self.state["state"], "needs-input")
        self.assertEqual(self.state["suspended_approaches"], ["parser ambiguity"])
        self.assertEqual(wc.replay(json.loads(json.dumps({"version": 1, "events": self.events}))), self.state)
        self.step("interrupt", {"reason": "context exhausted"}); self.step("resume", {})
        self.assertEqual(self.state["state"], "needs-input")
        # Independent work may proceed, while the failing approach stays suspended.
        self.checkpoint()
        self.assertEqual(self.state["suspended_approaches"], ["parser ambiguity"])
        self.step("decision", {"failure_class": "parser ambiguity", "choice": "Reduce grammar to supported cases",
                              "evidence": ["issue/decision"]}, actor="hub")
        self.candidate(SHA_C); self.review(); self.checkpoint("complete-for-review")
        self.assertEqual(self.state["state"], "complete-for-review")
        self.assertEqual(wc.status(self.state, len(self.events), 1500)["authorization"], "not-evaluated")

    def test_new_head_alone_does_not_consume_failure_budget(self):
        for head in (SHA_A, SHA_B, SHA_C):
            self.candidate(head)
        self.assertEqual(self.state["failures"], {})

    def test_published_synthetic_journal_replays_as_queued(self):
        journal = json.loads((ROOT / "examples/coordination/work-cycle.json").read_text())
        state = wc.replay(journal)
        self.assertEqual(state["review"]["verdict"], "queued")
        self.assertEqual(state["last_progress_at"], 1010)

    def test_repeated_receipt_after_other_review_does_not_consume_budget(self):
        self.candidate(); self.review("changes-required", "parser")
        self.review("active", proof="queue/2")
        self.review("changes-required", "parser")
        self.assertEqual(self.state["failures"], {"parser": 1})

    def test_green_checks_do_not_erase_falsification(self):
        self.candidate(); self.review()
        self.step("finding", {"finding_id": "F1", "summary": "Reproducer bypasses declared guard", "evidence": ["repro.log"]})
        self.step("checks", {"sha": SHA_A, "status": "passed", "evidence": ["ci/green"]})
        with self.assertRaisesRegex(ValueError, "falsification"):
            self.review()
        self.candidate(SHA_B)
        with self.assertRaisesRegex(ValueError, "unresolved findings"):
            self.checkpoint("complete-for-review")
        self.step("resolve-finding", {"finding_id": "F1", "evidence": ["regression.log"]})
        self.assertEqual(self.state["review"]["verdict"], "pending")
        self.review(proof="pr/review/2")

    def test_supersession_preserves_pending_evidence_and_fences_old_owner(self):
        self.candidate(); self.review("queued", proof="review/request")
        self.step("finding", {"finding_id": "F1", "summary": "Open finding", "evidence": ["repro"]})
        stale = self.event("checkpoint", {"state": "complete-for-review", "summary": "done", "next_action": "review",
                                          "dependency": "", "wait_seconds": 0, "evidence": ["stale"]})
        self.step("supersede", {"owner": "successor", "reason": "worker context exhausted"}, actor="hub")
        with self.assertRaisesRegex(ValueError, "stale ownership"):
            wc.transition(self.state, stale)
        self.step("resume", {})
        self.assertEqual(self.state["candidate_sha"], SHA_A)
        self.assertIsNone(self.state["findings"]["F1"]["resolved_by"])
        self.assertEqual(self.state["objective"], "Finish #1005")
        self.assertNotEqual(self.state["review"]["verdict"], "accepted")

    def test_queued_and_polling_are_not_progress(self):
        self.candidate(); progress = self.state["last_progress_at"]
        self.review("queued", proof="queue/1"); self.review("active", proof="queue/2")
        for _ in range(5):
            self.checkpoint("waiting", wait=90)
        self.assertEqual(self.state["last_progress_at"], progress)
        status = wc.status(self.state, len(self.events), 2000)
        self.assertTrue(status["checkpoint_due"])
        self.assertFalse(status["chunk_due"])

    def test_clock_due_does_not_invent_a_stall_or_deliver_message(self):
        status = wc.status(self.state, 1, 1200)
        self.assertTrue(status["chunk_due"])
        self.assertTrue(status["checkpoint_due"])
        self.assertEqual(status["state"], "working")
        self.assertEqual(status["delivery"], "caller-must-publish")

    def test_wait_requires_named_dependency_and_checkpoint(self):
        event = self.event("checkpoint", {"state": "waiting", "summary": "CI pending", "next_action": "Read terminal CI",
                      "dependency": "", "wait_seconds": 180, "evidence": []})
        with self.assertRaisesRegex(ValueError, "dependency"):
            wc.transition(self.state, event)
        event["data"]["dependency"] = "ci/run/1"
        result = wc.transition(self.state, event)
        self.assertEqual(result["last_checkpoint_at"], event["at"])

    def test_invalid_event_types_and_authority_fields_reject(self):
        for name, value in (("failure_budget", True), ("heartbeat_seconds", 0), ("chunk_seconds", -2)):
            event = json.loads(json.dumps(self.events[0])); event["data"][name] = value
            with self.assertRaises(ValueError): wc.transition(None, event)
        event = self.event("resume", {"authorized": True})
        with self.assertRaisesRegex(ValueError, "invalid resume fields"):
            wc.transition(self.state, event)
        with self.assertRaisesRegex(ValueError, "exact 40"):
            self.candidate("main")

    def test_duplicate_atomic_write_and_revision_conflict(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "work.json"
            event = self.events[0]
            result, changed = wc.update(path, event, 0)
            self.assertTrue(changed)
            before = path.read_bytes()
            self.assertFalse(wc.update(path, event, 0)[1])
            self.assertEqual(path.read_bytes(), before)
            altered = {**event, "at": event["at"] + 1}
            with self.assertRaisesRegex(ValueError, "reused"):
                wc.update(path, altered, 1)
            candidate = self.event("candidate", {"sha": SHA_A})
            with self.assertRaisesRegex(ValueError, "stale revision"):
                wc.update(path, candidate, 0)
            self.assertEqual(path.read_bytes(), before)

    def test_competing_writers_cannot_both_claim_revision(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "work.json"
            wc.update(path, self.events[0], 0)
            events = [self.event("candidate", {"sha": head}) for head in (SHA_A, SHA_B)]
            events[1]["id"] = "other"
            def attempt(event):
                try:
                    wc.update(path, event, 1)
                    return "written"
                except ValueError:
                    return "conflict"
            with concurrent.futures.ThreadPoolExecutor(2) as pool:
                self.assertCountEqual(list(pool.map(attempt, events)), ["written", "conflict"])
            journal = json.loads(path.read_text())
            self.assertEqual(len(journal["events"]), 2)
            wc.replay(journal)

    def test_cli_restart_read_and_error_never_mutate_journal(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "work.json"
            wc.update(path, self.events[0], 0)
            before = path.read_bytes()
            command = [sys.executable, str(SCRIPT), str(path)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["owner"], "worker")
            event = Path(folder) / "event.json"; event.write_text(json.dumps(self.event("resume", {})))
            result = subprocess.run(command + ["--event", str(event), "--expect", "1"], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
