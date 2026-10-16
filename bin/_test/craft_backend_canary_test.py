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
PROPOSAL = ROOT / "examples" / "probe-matrices" / "craft-backend-canary" / "approval.proposal.json"
spec = importlib.util.spec_from_file_location("craft_backend_canary", SCRIPT)
canary = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(canary)


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
        self.assertTrue((self.temp / "fixture" / "repo" / "PROMPT_MARKER.txt").is_file())
        self.assertFalse(self.workspace.exists())
        approved = record_external_approval(self.value)
        approved["pins"]["craft_package_tree_sha256"] = materialized["package_observation"]["exact_tree_sha256"]
        approved["operator_approval"]["subject_sha256"] = canary.approval_subject_sha256(approved)
        attestation = canary.attest_materialized(approved)
        self.assertEqual(attestation["status"], "materialization-consistent-unverified")
        self.assertEqual(attestation["authorization_effect"], "none")
        with self.assertRaisesRegex(canary.PacketError, "existing temp root"):
            canary.materialize(self.value)

    def test_imported_evidence_is_consistent_unverified_and_never_model_report(self):
        approved = record_external_approval(self.value)
        facts = canary.validate_manifest(approved, require_approval_record=True)
        start = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
        runs = []
        for index, backend in enumerate(approved["backends"]):
            began = start + timedelta(minutes=20 * index)
            ended = began + timedelta(minutes=10)
            runs.append({
                "sequence": backend["sequence"],
                "connection": backend["connection"],
                "model": backend["model"],
                "started_at": began.isoformat(),
                "ended_at": ended.isoformat(),
                "outcome": "observed",
                "model_self_report_used": False,
                "host_events": [
                    {"name": name, "source": "host-observed", "artifact_sha256": "c" * 64}
                    for name in sorted(canary.EVENTS)
                ],
            })
        evidence = {
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
        result = canary.validate_evidence(approved, evidence)
        self.assertEqual(result["events"], 18)
        self.assertEqual(result["status"], "evidence-consistent-unverified")
        self.assertEqual(result["authorization_effect"], "none")
        evidence["backend_runs"][1]["model_self_report_used"] = True
        with self.assertRaisesRegex(canary.PacketError, "self-report"):
            canary.validate_evidence(approved, evidence)
        evidence["backend_runs"][1]["model_self_report_used"] = False
        evidence["provenance"]["kind"] = "synthetic"
        with self.assertRaisesRegex(canary.PacketError, "Synthetic|synthetic"):
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
