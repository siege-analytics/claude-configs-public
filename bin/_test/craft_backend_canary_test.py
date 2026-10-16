#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import os
import shutil
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "canary" / "craft-backend-canary.py"
SETUP_SCRIPT = ROOT / "scripts" / "canary" / "setup-disposable-workspace.py"
PROPOSAL = ROOT / "examples" / "probe-matrices" / "craft-backend-canary" / "approval.proposal.json"
spec = importlib.util.spec_from_file_location("craft_backend_canary", SCRIPT)
canary = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(canary)
setup_spec = importlib.util.spec_from_file_location("setup_disposable_workspace", SETUP_SCRIPT)
setup = importlib.util.module_from_spec(setup_spec)
assert setup_spec and setup_spec.loader
setup_spec.loader.exec_module(setup)


def packet(run_id: str) -> dict:
    value = json.loads(PROPOSAL.read_text())
    temp = Path("/private/tmp") / run_id
    workspace = Path.home() / ".craft-agent" / "workspaces" / run_id
    value["run"]["id"] = run_id
    value["paths"] = {
        "temp_root": str(temp),
        "workspace_root": str(workspace),
        "evidence_root": str(temp / "evidence"),
        "source_root": str(temp / "source"),
    }
    value["cleanup"]["verify_absent"] = [str(workspace), str(temp)]
    return value


def record_external_approval(value: dict) -> dict:
    value = copy.deepcopy(value)
    value["status"] = "approval-recorded"
    value["pins"]["provider_integration_revision"] = "a" * 40
    value["pins"]["native_hooks_revision"] = "b" * 40
    value["pins"]["craft_package_tree_sha256"] = "d" * 64
    value["pins"]["composition_tree_sha256"] = "e" * 64
    value["pins"]["workspace_payload_tree_sha256"] = "f" * 64
    value["operator_approval"] = {
        "state": "externally-supplied",
        "source_kind": "direct-user-instruction",
        "source_reference": "unit-fixture-only",
        "approved_by": "test-reviewer",
        "approved_at": "2026-10-16T12:00:00Z",
        "subject_sha256": None,
    }
    value["operator_approval"]["subject_sha256"] = canary.approval_subject_sha256(value)
    return value


class CanaryPacketTest(unittest.TestCase):
    def setUp(self):
        self.run_id = f"cc-1003-unit-{os.getpid()}"
        self.value = packet(self.run_id)
        self.temp = Path(self.value["paths"]["temp_root"])
        self.workspace = Path(self.value["paths"]["workspace_root"])
        shutil.rmtree(self.temp, ignore_errors=True)
        self.assertFalse(self.workspace.exists())

    def tearDown(self):
        shutil.rmtree(self.temp, ignore_errors=True)
        self.assertFalse(self.workspace.exists())

    def test_proposal_is_valid_but_has_no_external_approval(self):
        facts = canary.validate_manifest(self.value)
        self.assertEqual(facts["run_id"], self.run_id)
        self.assertEqual(facts["authorization_effect"], "none")
        with self.assertRaisesRegex(canary.PacketError, "approval has not been recorded"):
            canary.validate_manifest(self.value, require_approval_record=True)

    def test_paths_are_exact_and_confined(self):
        broken = copy.deepcopy(self.value)
        broken["paths"]["temp_root"] = f"/private/tmp/{self.run_id}/../escape"
        with self.assertRaises(canary.PacketError):
            canary.validate_manifest(broken)
        broken = copy.deepcopy(self.value)
        broken["paths"]["workspace_root"] = str(Path.home() / ".craft-agent" / "workspaces" / "shared")
        with self.assertRaises(canary.PacketError):
            canary.validate_manifest(broken)

    def test_external_record_requires_prerequisites_and_matching_subject(self):
        approved = record_external_approval(self.value)
        approved["pins"]["native_hooks_revision"] = None
        with self.assertRaisesRegex(canary.PacketError, "native_hooks_revision"):
            canary.validate_manifest(approved, require_approval_record=True)
        approved = record_external_approval(self.value)
        approved["backends"][0]["model"] = "mutated-after-approval"
        with self.assertRaisesRegex(canary.PacketError, "subject digest mismatch"):
            canary.validate_manifest(approved, require_approval_record=True)

    def test_materialize_and_external_record_attest_exact_existing_bytes(self):
        receipt = canary.materialize(self.value)
        materialized = json.loads(Path(receipt["receipt"]).read_text())
        self.assertTrue((self.temp / "fixture" / "remote.git").is_dir())
        fixture_repo = self.temp / "fixture" / "repo"
        self.assertTrue((fixture_repo / "PROMPT_MARKER.txt").is_file())
        self.assertEqual(
            canary.run_git(["config", "--get", "remote.origin.url"], cwd=fixture_repo),
            "https://github.example.invalid/synthetic-org/strict-release.git",
        )
        message = canary.run_git(["show", "-s", "--format=%B", "HEAD"], cwd=fixture_repo)
        self.assertIn("Review-Tier: A", message)
        self.assertIn("Self-Review: disposable canary fixture only", message)
        composition = self.temp / "composition" / "flat"
        self.assertIn(self.value["fixture"]["resident_marker"], (composition / "skills/RESIDENT.md").read_text())
        control = self.temp / "control"
        self.assertTrue((control / "FOREIGN_PROJECT_MARKER.txt").is_file())
        self.assertTrue((control / "GLOBAL_BUNDLE_MARKER.txt").is_file())
        payload = self.temp / "workspace-payload"
        payload_text = "\n".join(
            path.read_text(errors="ignore") for path in payload.rglob("*") if path.is_file()
        )
        self.assertNotIn("FOREIGN_PROJECT_CONTROL_MUST_NOT_BE_INJECTED", payload_text)
        self.assertNotIn("GLOBAL_BUNDLE_CONTROL_MUST_NOT_BE_INJECTED", payload_text)
        self.assertFalse((payload / "deploy-stamp.json").exists())
        fake_workspace = self.temp / "fake-workspace"
        fake_workspace.mkdir()
        setup.validate_payload(canary, payload, materialized["package_observation"]["workspace_payload_tree_sha256"])
        setup.copy_payload(canary, payload, fake_workspace)
        self.assertEqual(canary.tree_digest(fake_workspace), canary.tree_digest(payload))
        self.assertFalse((fake_workspace / "deploy-stamp.json").exists())
        (payload / "unexpected.txt").write_text("not allowlisted\n")
        with self.assertRaisesRegex(canary.PacketError, "allowlist mismatch"):
            setup.validate_payload(canary, payload, canary.tree_digest(payload))
        (payload / "unexpected.txt").unlink()
        self.assertFalse(self.workspace.exists())
        approved = record_external_approval(self.value)
        approved["pins"]["craft_package_tree_sha256"] = materialized["package_observation"]["exact_tree_sha256"]
        approved["pins"]["composition_tree_sha256"] = materialized["package_observation"]["composition_tree_sha256"]
        approved["pins"]["workspace_payload_tree_sha256"] = materialized["package_observation"]["workspace_payload_tree_sha256"]
        approved["operator_approval"]["subject_sha256"] = canary.approval_subject_sha256(approved)
        attestation = canary.attest_materialized(approved)
        self.assertEqual(attestation["status"], "materialization-consistent-unverified")
        self.assertEqual(attestation["authorization_effect"], "none")
        with self.assertRaisesRegex(canary.PacketError, "existing temp root"):
            canary.materialize(self.value)

    def approved_evidence(self) -> tuple[dict, dict]:
        approved = record_external_approval(self.value)
        facts = canary.validate_manifest(approved, require_approval_record=True)
        start = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
        runs = []
        evidence_root = Path(approved["paths"]["evidence_root"])
        evidence_root.mkdir(parents=True, exist_ok=True)
        for index, backend in enumerate(approved["backends"]):
            began = start + timedelta(minutes=11 * index)
            ended = began + timedelta(minutes=10)
            events = []
            for name in sorted(canary.EVENTS):
                reference = f"backend-{backend['sequence']}/{name}.jsonl"
                artifact = evidence_root / reference
                artifact.parent.mkdir(parents=True, exist_ok=True)
                artifact.write_bytes(f"host-export-fixture:{backend['sequence']}:{name}\n".encode())
                events.append({
                    "name": name,
                    "source": "host-observed",
                    "artifact_reference": reference,
                    "artifact_sha256": canary.sha256_bytes(artifact.read_bytes()),
                })
            runs.append({
                "sequence": backend["sequence"],
                "connection": backend["connection"],
                "model": backend["model"],
                "started_at": began.isoformat(),
                "ended_at": ended.isoformat(),
                "outcome": "observed",
                "model_self_report_used": False,
                "host_events": events,
            })
        return approved, {
            "schema_version": canary.SCHEMA_VERSION,
            "run_id": self.run_id,
            "manifest_sha256": facts["manifest_sha256"],
            "provenance": {"kind": "external-host-export", "reference": "unit-fixture-only"},
            "backend_runs": runs,
            "side_effect_observations": {
                "outside_allowlist_unchanged": True,
                "credentials_unread": True,
                "main_unchanged": True,
                "protections_unchanged": True,
                "release_state_unchanged": True,
            },
        }

    def test_imported_evidence_is_consistent_unverified_and_never_model_report(self):
        approved, evidence = self.approved_evidence()
        result = canary.validate_evidence(approved, evidence)
        self.assertEqual(result["events"], 18)
        self.assertEqual(result["timing_seconds"], {
            "backend_runs": [600.0, 600.0], "transitions": [60.0], "overall": 1260.0,
        })
        self.assertEqual(result["status"], "evidence-consistent-unverified")
        self.assertEqual(result["authorization_effect"], "none")
        evidence["backend_runs"][1]["model_self_report_used"] = True
        with self.assertRaisesRegex(canary.PacketError, "self-report"):
            canary.validate_evidence(approved, evidence)
        evidence["backend_runs"][1]["model_self_report_used"] = False
        evidence["provenance"]["kind"] = "synthetic"
        with self.assertRaisesRegex(canary.PacketError, "Synthetic|synthetic"):
            canary.validate_evidence(approved, evidence)
        approved, evidence = self.approved_evidence()
        evidence["backend_runs"][0]["outcome"] = "unsupported-unverified"
        with self.assertRaisesRegex(canary.PacketError, "unsupported/unverified"):
            canary.validate_evidence(approved, evidence)

    def test_evidence_requires_exactly_nine_unique_expected_events_per_backend(self):
        for mutation, diagnostic in (
            (lambda events: events.append(copy.deepcopy(events[0])), "exactly 9"),
            (lambda events: events.pop(), "exactly 9"),
            (lambda events: events.__setitem__(-1, {**events[-1], "name": "unexpected_event"}), "event set mismatch"),
            (lambda events: events.__setitem__(-1, {**events[-1], "name": events[0]["name"]}), "duplicate"),
        ):
            approved, evidence = self.approved_evidence()
            mutation(evidence["backend_runs"][0]["host_events"])
            with self.assertRaisesRegex(canary.PacketError, diagnostic):
                canary.validate_evidence(approved, evidence)

    def test_evidence_requires_confined_unique_digest_bound_artifacts(self):
        approved, evidence = self.approved_evidence()
        event = evidence["backend_runs"][0]["host_events"][0]
        event["artifact_sha256"] = "0" * 64
        with self.assertRaisesRegex(canary.PacketError, "digest mismatch"):
            canary.validate_evidence(approved, evidence)

        approved, evidence = self.approved_evidence()
        evidence["backend_runs"][0]["host_events"][0]["artifact_reference"] = "../escape.jsonl"
        with self.assertRaisesRegex(canary.PacketError, "confined"):
            canary.validate_evidence(approved, evidence)

        approved, evidence = self.approved_evidence()
        first = evidence["backend_runs"][0]["host_events"][0]
        evidence["backend_runs"][1]["host_events"][0]["artifact_reference"] = first["artifact_reference"]
        with self.assertRaisesRegex(canary.PacketError, "unique"):
            canary.validate_evidence(approved, evidence)

    def test_evidence_enforces_per_backend_transition_overlap_and_overall_budgets(self):
        approved, evidence = self.approved_evidence()
        evidence["backend_runs"][0]["ended_at"] = (
            datetime.fromisoformat(evidence["backend_runs"][0]["started_at"]) + timedelta(seconds=901)
        ).isoformat()
        with self.assertRaisesRegex(canary.PacketError, "per_backend"):
            canary.validate_evidence(approved, evidence)

        approved, evidence = self.approved_evidence()
        first_end = datetime.fromisoformat(evidence["backend_runs"][0]["ended_at"])
        evidence["backend_runs"][1]["started_at"] = (first_end + timedelta(seconds=181)).isoformat()
        evidence["backend_runs"][1]["ended_at"] = (first_end + timedelta(seconds=781)).isoformat()
        with self.assertRaisesRegex(canary.PacketError, "transition"):
            canary.validate_evidence(approved, evidence)

        approved, evidence = self.approved_evidence()
        first_end = datetime.fromisoformat(evidence["backend_runs"][0]["ended_at"])
        evidence["backend_runs"][1]["started_at"] = (first_end - timedelta(seconds=1)).isoformat()
        evidence["backend_runs"][1]["ended_at"] = (first_end + timedelta(seconds=599)).isoformat()
        with self.assertRaisesRegex(canary.PacketError, "overlap"):
            canary.validate_evidence(approved, evidence)

        approved, evidence = self.approved_evidence()
        approved["timeouts_seconds"]["per_backend"] = 1000
        approved["timeouts_seconds"]["transition"] = 1000
        approved["timeouts_seconds"]["overall"] = 2400
        approved["operator_approval"]["subject_sha256"] = canary.approval_subject_sha256(approved)
        facts = canary.validate_manifest(approved, require_approval_record=True)
        evidence["manifest_sha256"] = facts["manifest_sha256"]
        start = datetime.fromisoformat(evidence["backend_runs"][0]["started_at"])
        evidence["backend_runs"][0]["ended_at"] = (start + timedelta(seconds=900)).isoformat()
        evidence["backend_runs"][1]["started_at"] = (start + timedelta(seconds=1500)).isoformat()
        evidence["backend_runs"][1]["ended_at"] = (start + timedelta(seconds=2500)).isoformat()
        with self.assertRaisesRegex(canary.PacketError, "overall"):
            canary.validate_evidence(approved, evidence)

    def test_cleanup_requires_receipt_and_real_absence(self):
        approved = record_external_approval(self.value)
        facts = canary.validate_manifest(approved, require_approval_record=True)
        receipt = {
            "schema_version": canary.SCHEMA_VERSION,
            "run_id": self.run_id,
            "manifest_sha256": facts["manifest_sha256"],
            "workspace_absent": True,
            "temp_root_absent": True,
            "disposable_refs_absent": True,
            "outside_allowlist_unchanged": True,
        }
        result = canary.verify_cleanup(approved, receipt)
        self.assertEqual(result["status"], "local-cleanup-absence-observed")
        self.assertEqual(result["authorization_effect"], "none")
        self.temp.mkdir(parents=True)
        with self.assertRaisesRegex(canary.PacketError, "temp root still exists"):
            canary.verify_cleanup(approved, receipt)

    def test_side_effect_set_backend_order_and_timeouts_are_closed(self):
        broken = copy.deepcopy(self.value)
        broken["allowed_side_effects"].append("publish_release")
        with self.assertRaises(canary.PacketError):
            canary.validate_manifest(broken)
        broken = copy.deepcopy(self.value)
        broken["backends"].reverse()
        with self.assertRaises(canary.PacketError):
            canary.validate_manifest(broken)
        broken = copy.deepcopy(self.value)
        broken["timeouts_seconds"]["overall"] = 100
        with self.assertRaises(canary.PacketError):
            canary.validate_manifest(broken)


if __name__ == "__main__":
    unittest.main()
