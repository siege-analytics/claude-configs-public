#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
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


def packet(run_id: str, temp_base: Path) -> dict:
    value = json.loads(PROPOSAL.read_text())
    temp = temp_base / run_id
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
        self.temp_base = Path(tempfile.gettempdir()).resolve()
        self.value = packet(self.run_id, self.temp_base)
        self.temp = Path(self.value["paths"]["temp_root"])
        self.workspace = Path(self.value["paths"]["workspace_root"])
        shutil.rmtree(self.temp, ignore_errors=True)
        self.assertFalse(self.workspace.exists())
        installed = tempfile.TemporaryDirectory(prefix="cc-1003-installed-builds-")
        self.addCleanup(installed.cleanup)
        installed_root = Path(installed.name)
        craft_manifest = installed_root / "craft-package.json"
        main_bundle = installed_root / "main.cjs"
        claude_manifest = installed_root / "claude-package.json"
        craft_manifest.write_text(json.dumps({"name": "@craft-agent/electron", "version": "0.15.2"}) + "\n")
        main_bundle.write_text("@earendil-works/pi-ai\nopenai-codex-responses\n")
        claude_manifest.write_text(json.dumps({"name": "@anthropic-ai/claude-agent-sdk", "version": "0.3.296"}) + "\n")
        self.discovery_manifest = copy.deepcopy(self.value)
        craft = self.discovery_manifest["installed_builds"]["craft_application"]
        craft.update({
            "package_manifest_path": str(craft_manifest),
            "package_manifest_sha256": canary.sha256_bytes(craft_manifest.read_bytes()),
            "main_bundle_path": str(main_bundle),
            "main_bundle_sha256": canary.sha256_bytes(main_bundle.read_bytes()),
        })
        claude = self.discovery_manifest["installed_builds"]["claude_sdk"]
        claude.update({
            "package_manifest_path": str(claude_manifest),
            "package_manifest_sha256": canary.sha256_bytes(claude_manifest.read_bytes()),
        })
        pi = self.discovery_manifest["installed_builds"]["pi_adapter"]
        pi.update({
            "discovery_artifact_path": str(main_bundle),
            "discovery_artifact_sha256": canary.sha256_bytes(main_bundle.read_bytes()),
        })
        self.installed_paths = {
            "craft_manifest": craft_manifest, "main_bundle": main_bundle, "claude_manifest": claude_manifest,
        }
        self._test_discovery_reader = lambda _manifest: canary.discover_installed_builds(self.discovery_manifest)

    def validate_manifest(self, value, *, require_approval_record=False):
        return canary.validate_manifest(
            value, require_approval_record=require_approval_record, _test_expected_temp_base=self.temp_base,
        )

    def validate_evidence(self, approved, evidence):
        return canary.validate_evidence(
            approved, evidence, _test_discovery_reader=self._test_discovery_reader, _test_expected_temp_base=self.temp_base,
        )

    def tearDown(self):
        shutil.rmtree(self.temp, ignore_errors=True)
        self.assertFalse(self.workspace.exists())

    def test_proposal_is_valid_but_has_no_external_approval(self):
        facts = self.validate_manifest(self.value)
        self.assertEqual(facts["run_id"], self.run_id)
        self.assertEqual(facts["authorization_effect"], "none")
        with self.assertRaisesRegex(canary.PacketError, "approval has not been recorded"):
            self.validate_manifest(self.value, require_approval_record=True)

    def test_installed_build_discovery_uses_portable_real_artifacts_and_fails_closed(self):
        observed = self._test_discovery_reader(self.value)
        self.assertEqual(observed["craft_application"]["state"], "artifact-match")
        self.assertEqual(observed["claude_sdk"]["state"], "artifact-match-active-selection-unverified")
        self.assertEqual(observed["pi_adapter"]["public_manifest_state"], "unavailable-unverified")
        main = self.installed_paths["main_bundle"]
        original_main = main.read_bytes()
        main.write_bytes(original_main + b"changed\n")
        with self.assertRaisesRegex(canary.PacketError, "main bundle digest mismatch"):
            self._test_discovery_reader(self.value)
        main.write_bytes(original_main)
        craft = self.installed_paths["craft_manifest"]
        original_craft = craft.read_bytes()
        craft.unlink()
        with self.assertRaisesRegex(canary.PacketError, "absent or symlinked"):
            self._test_discovery_reader(self.value)
        craft.write_bytes(original_craft)
        claude = self.installed_paths["claude_manifest"]
        original_claude = claude.read_bytes()
        claude.unlink()
        claude.symlink_to(craft)
        with self.assertRaisesRegex(canary.PacketError, "absent or symlinked"):
            self._test_discovery_reader(self.value)
        claude.unlink()
        claude.write_bytes(original_claude)
        unavailable = copy.deepcopy(self.discovery_manifest)
        main.write_text("@earendil-works/pi-ai\n")
        digest = canary.sha256_bytes(main.read_bytes())
        unavailable["installed_builds"]["craft_application"]["main_bundle_sha256"] = digest
        unavailable["installed_builds"]["pi_adapter"]["discovery_artifact_sha256"] = digest
        with self.assertRaisesRegex(canary.PacketError, "adapter marker is absent"):
            canary.discover_installed_builds(unavailable)

    def test_runtime_pin_versions_are_run_data_and_still_digest_bound(self):
        fresh = copy.deepcopy(self.value)
        before = canary.approval_subject_sha256(fresh)
        fresh['installed_builds']['craft_application']['version'] = '0.15.6'
        fresh['installed_builds']['claude_sdk']['version'] = '0.3.302'
        self.validate_manifest(fresh)
        self.assertNotEqual(before, canary.approval_subject_sha256(fresh))
        for key, value in [('version', ''), ('version', 'latest'), ('package_manifest_sha256', 'bad'), ('package_manifest_path', 'relative.json')]:
            invalid = copy.deepcopy(fresh)
            invalid['installed_builds']['craft_application'][key] = value
            with self.assertRaises(canary.PacketError):
                self.validate_manifest(invalid)

    def test_paths_are_exact_and_confined(self):
        broken = copy.deepcopy(self.value)
        broken["paths"]["temp_root"] = f"/private/tmp/{self.run_id}/../escape"
        with self.assertRaises(canary.PacketError):
            self.validate_manifest(broken)
        broken = copy.deepcopy(self.value)
        broken["paths"]["workspace_root"] = str(Path.home() / ".craft-agent" / "workspaces" / "shared")
        with self.assertRaises(canary.PacketError):
            self.validate_manifest(broken)

    def test_external_record_requires_prerequisites_and_matching_subject(self):
        prepared = copy.deepcopy(self.value)
        prepared["pins"].update({
            "provider_integration_revision": "a" * 40,
            "native_hooks_revision": "b" * 40,
            "craft_package_tree_sha256": "d" * 64,
            "composition_tree_sha256": "e" * 64,
            "workspace_payload_tree_sha256": "f" * 64,
        })
        proposal_subject = canary.approval_subject_sha256(prepared)
        approved = record_external_approval(prepared)
        self.assertEqual(canary.approval_subject_sha256(approved), proposal_subject)
        self.assertEqual(approved["operator_approval"]["subject_sha256"], proposal_subject)
        approved["pins"]["native_hooks_revision"] = None
        with self.assertRaisesRegex(canary.PacketError, "native_hooks_revision"):
            self.validate_manifest(approved, require_approval_record=True)
        approved = record_external_approval(self.value)
        approved["backends"][0]["model"] = "mutated-after-approval"
        with self.assertRaisesRegex(canary.PacketError, "subject digest mismatch"):
            self.validate_manifest(approved, require_approval_record=True)

    def test_readme_extraction_distinguishes_prefix_markers_and_keeps_tail(self):
        readme = (ROOT / "examples/probe-matrices/craft-backend-canary/README.md").read_text()
        match = re.search(r"python3 - \"\$EVIDENCE_ROOT\" \"\$BACKEND_SEQUENCE\" <<'PY'\n(.*?)\nPY", readme, re.S)
        self.assertIsNotNone(match)
        evidence = self.temp / "evidence"
        backend = evidence / "backend-1"
        backend.mkdir(parents=True)
        records = []
        def user(content): records.append({"type": "user", "content": content})
        def host(content): records.append({"type": "host", "content": content})
        for marker in ("STARTUP_RESOLVER", "PROMPT_HOOK", "WRITE_ALLOW", "WRITE_DENY", "PUSH_ALLOW", "PUSH_DENY", "RESUME"):
            user(f"CC1003_B1_{marker}. prescribed prompt")
            host(f"host record for {marker}")
        user("CC1003_B1_COMPACTION_BEFORE nonce=abc123. prescribed prompt")
        host("compaction boundary")
        user("CC1003_B1_COMPACTION_AFTER. prescribed prompt")
        host("post-compaction denial")
        user("CC1003_B1_NO_OP. prescribed prompt")
        host("zero-output invocation")
        user("CC1003_B1_NO_OP_RESTORED. prescribed prompt")
        host("restored resolver invocation")
        user("UNRELATED_END. boundary")
        (backend / "session.jsonl").write_text("".join(json.dumps(record) + "\n" for record in records))
        result = subprocess.run([sys.executable, "-", str(evidence), "1"], input=match.group(1), text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(list(backend.glob("*_*.jsonl"))), 9)
        no_op = (backend / "no_op_detection.jsonl").read_text()
        self.assertEqual(no_op.count("CC1003_B1_NO_OP. prescribed prompt"), 1)
        self.assertEqual(no_op.count("CC1003_B1_NO_OP_RESTORED. prescribed prompt"), 1)
        self.assertNotIn("UNRELATED_END", no_op)
        compaction = (backend / "compaction_context.jsonl").read_text()
        self.assertEqual(compaction.count("CC1003_B1_COMPACTION_BEFORE nonce=abc123"), 1)
        self.assertEqual(compaction.count("CC1003_B1_COMPACTION_AFTER. prescribed prompt"), 1)
        self.assertIn("post-compaction denial", compaction)
        self.assertNotIn("CC1003_B1_NO_OP.", compaction)

    def test_materialize_and_external_record_attest_exact_existing_bytes(self):
        # Probe execution must preserve the hashed payload even when the caller
        # has not globally disabled Python bytecode writes (the ordinary CI/CLI case).
        with mock.patch.dict(os.environ):
            os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
            receipt = canary.materialize(self.value, _test_discovery_reader=self._test_discovery_reader, _test_expected_temp_base=self.temp_base)
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
        self.assertEqual(list(payload.rglob("*.pyc")), [], "the read-only probe mutated the payload")
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
        self.assertEqual(materialized["resolver_probe"]["project"], "strict-release")
        self.assertTrue({"strict-release--review", "strict-release--checks"}.issubset(materialized["resolver_probe"]["selected"]))
        self.assertEqual(materialized["resolver_probe"]["resident_delivery"], "observed-local-payload-hook")
        self.assertEqual(materialized["resolver_probe"]["resident_marker_count"], 1)
        self.assertEqual(materialized["resolver_probe"]["canonical_kernel_count"], 1)
        self.assertTrue(materialized["resolver_probe"]["negative_controls_absent"])
        discovery = materialized["installed_build_discovery"]
        self.assertEqual(discovery["craft_application"]["state"], "artifact-match")
        self.assertEqual(discovery["claude_sdk"]["state"], "artifact-match-active-selection-unverified")
        self.assertEqual(discovery["pi_adapter"]["state"], "bundle-markers-match-active-selection-unverified")
        self.assertEqual(discovery["authorization_effect"], "none")
        bad_payload_pin = copy.deepcopy(self.value)
        bad_payload_pin["pins"]["workspace_payload_tree_sha256"] = "0" * 64
        shutil.rmtree(self.temp / "composition")
        shutil.rmtree(payload)
        with self.assertRaisesRegex(canary.PacketError, "workspace payload differs from approved exact digest"):
            canary.prepare_composition_and_payload(bad_payload_pin, self.temp / "source", self.temp)
        shutil.rmtree(self.temp / "composition")
        shutil.rmtree(payload)
        rebuilt = canary.prepare_composition_and_payload(self.value, self.temp / "source", self.temp)
        self.assertEqual(rebuilt["workspace_payload_tree_sha256"], materialized["package_observation"]["workspace_payload_tree_sha256"])
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
        materialization_path = self.temp / "materialization.json"
        original_materialization = materialization_path.read_bytes()
        stale = json.loads(original_materialization)
        stale["installed_build_discovery"]["craft_application"]["version"] = "stale"
        materialization_path.write_bytes(canary.canonical_bytes(stale))
        with self.assertRaisesRegex(canary.PacketError, "installed build discovery changed"):
            canary.attest_materialized(approved, _test_discovery_reader=self._test_discovery_reader, _test_expected_temp_base=self.temp_base)
        materialization_path.write_bytes(original_materialization)
        attestation = canary.attest_materialized(approved, _test_discovery_reader=self._test_discovery_reader, _test_expected_temp_base=self.temp_base)
        self.assertEqual(attestation["status"], "materialization-consistent-unverified")
        source = self.temp / "source"
        install_script = source / "bin/install-hooks.sh"
        untracked_source = source / "bin/untracked-setup-shadow.py"
        original_install = install_script.read_bytes()
        origin = canary.run_git(["config", "--get", "remote.origin.url"], cwd=fixture_repo)
        pushurl = canary.run_git(["remote", "get-url", "--push", "origin"], cwd=fixture_repo)
        for mutation, restore, diagnostic in (
            (lambda: install_script.write_bytes(original_install + b"# drift\n"),
             lambda: install_script.write_bytes(original_install), "tracked drift"),
            (lambda: untracked_source.write_text("shadow\n"),
             lambda: untracked_source.unlink(missing_ok=True), "untracked drift"),
            (lambda: canary.run_git(["remote", "set-url", "origin", "https://foreign.invalid/wrong/repo.git"], cwd=fixture_repo),
             lambda: canary.run_git(["remote", "set-url", "origin", origin], cwd=fixture_repo), "origin identity"),
            (lambda: canary.run_git(["remote", "set-url", "--push", "origin", "file:///private/tmp/foreign.git"], cwd=fixture_repo),
             lambda: canary.run_git(["remote", "set-url", "--push", "origin", pushurl], cwd=fixture_repo), "push transport"),
        ):
            with self.subTest(mutation=diagnostic):
                mutation()
                try:
                    with mock.patch.object(setup, "copy_payload") as copied, mock.patch.object(setup, "run") as command:
                        with self.assertRaises(canary.PacketError):
                            setup.configure(canary, approved, _test_discovery_reader=self._test_discovery_reader, _test_expected_temp_base=self.temp_base)
                        copied.assert_not_called()
                        command.assert_not_called()
                    self.assertFalse(self.workspace.exists())
                finally:
                    restore()
        canary.attest_materialized(approved, _test_discovery_reader=self._test_discovery_reader, _test_expected_temp_base=self.temp_base)
        self.assertEqual(attestation["authorization_effect"], "none")
        with self.assertRaisesRegex(canary.PacketError, "existing temp root"):
            canary.materialize(self.value, _test_discovery_reader=self._test_discovery_reader, _test_expected_temp_base=self.temp_base)

    def test_fixture_claude_registration_is_exact_atomic_and_fail_closed(self):
        receipt = canary.materialize(
            self.value, _test_discovery_reader=self._test_discovery_reader,
            _test_expected_temp_base=self.temp_base,
        )
        materialized = json.loads(Path(receipt["receipt"]).read_text())
        source = self.temp / "source"
        payload = self.temp / "workspace-payload"
        assembly = self.temp / "registration-assembly"
        assembly.mkdir()
        setup.copy_payload(canary, payload, assembly)
        subprocess.run([
            "bash", "bin/install-hooks.sh", "--workspace", str(assembly), "--hooks-root", str(assembly),
        ], cwd=source, check=True, text=True, capture_output=True)
        subprocess.run([
            sys.executable, "bin/wire-enforcement.py", "--workspace", str(assembly),
            "--dist", str(source / "dist"),
        ], cwd=source, check=True, text=True, capture_output=True)
        settings = assembly / ".claude/settings.json"
        original = settings.read_bytes()
        settings_bytes, settings_sha256, inventory = setup.verify_wired_settings(
            canary, payload, assembly, source,
        )
        self.assertEqual(settings_bytes, original)
        expected_count = sum(
            len(group["hooks"])
            for groups in json.loads(original)["hooks"].values()
            for group in groups
        )
        self.assertEqual(len(inventory), expected_count)
        self.assertTrue(all(item["argv"] == [str(assembly / item["payload_relative_path"])] for item in inventory))
        self.assertEqual(
            materialized["package_observation"]["workspace_payload_tree_sha256"],
            canary.tree_digest(payload),
        )

        def mutate_validated_bytes():
            settings.write_bytes(original + b"\n")
        with self.assertRaisesRegex(ValueError, "path or bytes changed during validation"):
            setup.verify_wired_settings(
                canary, payload, assembly, source, _test_after_snapshot=mutate_validated_bytes,
            )
        settings.write_bytes(original)

        replacement = settings.with_name("settings.replacement.json")
        def replace_validated_path():
            replacement.write_bytes(original)
            os.replace(replacement, settings)
        with self.assertRaisesRegex(ValueError, "path or bytes changed during validation"):
            setup.verify_wired_settings(
                canary, payload, assembly, source, _test_after_snapshot=replace_validated_path,
            )
        settings.write_bytes(original)

        fixtures = self.temp / "registration-fixtures"
        fixtures.mkdir()
        positive = fixtures / "positive"
        positive.mkdir()
        registration = setup.register_fixture_settings(canary, settings, positive, settings_sha256)
        target = positive / ".claude/settings.json"
        self.assertEqual(target.read_bytes(), original)
        self.assertEqual(registration["source_sha256"], registration["destination_sha256"])
        with self.assertRaisesRegex(canary.PacketError, "existing fixture Claude settings"):
            setup.register_fixture_settings(canary, settings, positive, settings_sha256)

        actual = json.loads(original)
        command = actual["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        for replacement in (command + " ; echo substituted", "sh " + command, "/foreign/inject-resolver.sh"):
            with self.subTest(command=replacement):
                changed = copy.deepcopy(actual)
                changed["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"] = replacement
                settings.write_text(json.dumps(changed, indent=2) + "\n")
                with self.assertRaisesRegex(canary.PacketError, "inventory differs"):
                    setup.verify_wired_settings(canary, payload, assembly, source)
        changed = copy.deepcopy(actual)
        changed["hooks"]["Unexpected"] = [{"hooks": []}]
        settings.write_text(json.dumps(changed, indent=2) + "\n")
        with self.assertRaisesRegex(canary.PacketError, "inventory differs"):
            setup.verify_wired_settings(canary, payload, assembly, source)
        settings.write_bytes(original)

        executable = assembly / inventory[0]["payload_relative_path"]
        executable_original = executable.read_bytes()
        executable.write_bytes(executable_original + b"# substitution\n")
        with self.assertRaisesRegex(canary.PacketError, "differs from pinned payload"):
            setup.verify_wired_settings(canary, payload, assembly, source)
        executable.write_bytes(executable_original)

        symlinked = fixtures / "symlinked"
        symlinked.mkdir()
        (symlinked / ".claude").symlink_to(positive / ".claude", target_is_directory=True)
        with self.assertRaisesRegex(canary.PacketError, "must not be a symlink"):
            setup.register_fixture_settings(canary, settings, symlinked, settings_sha256)

        raced = fixtures / "raced"
        raced.mkdir()
        race_target = raced / ".claude/settings.json"
        def create_race_target():
            race_target.write_text("operator-owned\n")
        with self.assertRaisesRegex(canary.PacketError, "appeared during registration"):
            setup.register_fixture_settings(
                canary, settings, raced, settings_sha256, _test_before_link=create_race_target,
            )
        self.assertEqual(race_target.read_text(), "operator-owned\n")
        self.assertEqual(list((raced / ".claude").glob(".cc-1003-settings-*")), [])

        parent_raced = fixtures / "parent-raced"
        parent_raced.mkdir()
        outside = fixtures / "outside-parent"
        outside.mkdir()
        def swap_parent_directory():
            directory = parent_raced / ".claude"
            temporary = next(directory.glob(".cc-1003-settings-*"))
            shutil.copy2(temporary, outside / temporary.name)
            directory.rename(parent_raced / ".claude-moved")
            directory.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(canary.PacketError, "parent changed during registration"):
            setup.register_fixture_settings(
                canary, settings, parent_raced, settings_sha256,
                _test_before_link=swap_parent_directory,
            )
        self.assertFalse((outside / "settings.json").exists())
        self.assertFalse((parent_raced / ".claude-moved/settings.json").exists())
        self.assertEqual(list((parent_raced / ".claude-moved").glob(".cc-1003-settings-*")), [])

        source_raced = fixtures / "source-raced"
        source_raced.mkdir()
        def mutate_source_settings():
            settings.write_bytes(original + b"\n")
        with self.assertRaisesRegex(canary.PacketError, "changed during fixture registration"):
            setup.register_fixture_settings(
                canary, settings, source_raced, settings_sha256,
                _test_before_link=mutate_source_settings,
            )
        self.assertFalse((source_raced / ".claude/settings.json").exists())
        self.assertFalse((source_raced / ".claude").exists())
        settings.write_bytes(original)

    def test_full_setup_registers_fixture_settings_under_isolated_test_home(self):
        isolated_home = tempfile.TemporaryDirectory(prefix="cc-1003-test-home-", dir=self.temp_base)
        self.addCleanup(isolated_home.cleanup)
        run_id = f"cc-1003-configure-{os.getpid()}"
        with mock.patch.dict(os.environ, {"HOME": isolated_home.name}):
            value = packet(run_id, self.temp_base)
            temp_root = Path(value["paths"]["temp_root"])
            workspace = Path(value["paths"]["workspace_root"])
            shutil.rmtree(temp_root, ignore_errors=True)
            shutil.rmtree(workspace, ignore_errors=True)
            try:
                materialization = canary.materialize(
                    value, _test_discovery_reader=self._test_discovery_reader,
                    _test_expected_temp_base=self.temp_base,
                )
                observed = json.loads(Path(materialization["receipt"]).read_text())["package_observation"]
                approved = record_external_approval(value)
                approved["pins"]["craft_package_tree_sha256"] = observed["exact_tree_sha256"]
                approved["pins"]["composition_tree_sha256"] = observed["composition_tree_sha256"]
                approved["pins"]["workspace_payload_tree_sha256"] = observed["workspace_payload_tree_sha256"]
                approved["operator_approval"]["subject_sha256"] = canary.approval_subject_sha256(approved)
                workspace.mkdir(parents=True)
                result = setup.configure(
                    canary, approved, _test_discovery_reader=self._test_discovery_reader,
                    _test_expected_temp_base=self.temp_base,
                )
                receipt = json.loads(Path(result["receipt"]).read_text())
                registration = receipt["claude_project_registration"]
                fixture_settings = temp_root / "fixture/repo/.claude/settings.json"
                workspace_settings = workspace / ".claude/settings.json"
                self.assertEqual(fixture_settings.read_bytes(), workspace_settings.read_bytes())
                self.assertEqual(
                    registration["destination_path"], str(fixture_settings),
                )
                self.assertEqual(
                    registration["destination_sha256"],
                    canary.sha256_bytes(fixture_settings.read_bytes()),
                )
                self.assertEqual(receipt["workspace_settings_role"], "assembly-evidence-only")
                self.assertEqual(receipt["pi_capability_state"], "unsupported-unverified")
                self.assertFalse(registration["host_invocation_observed"])
                self.assertTrue(registration["command_inventory"])
                self.assertFalse((workspace / "deploy-stamp.json").exists())
            finally:
                shutil.rmtree(workspace, ignore_errors=True)
                shutil.rmtree(temp_root, ignore_errors=True)

    def approved_evidence(self) -> tuple[dict, dict]:
        approved = record_external_approval(self.value)
        facts = self.validate_manifest(approved, require_approval_record=True)
        start = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
        runs = []
        discovery = self._test_discovery_reader(approved)
        evidence_root = Path(approved["paths"]["evidence_root"])
        evidence_root.mkdir(parents=True, exist_ok=True)
        fixture = Path(approved["paths"]["temp_root"]) / "fixture/repo"
        fixture_settings = fixture / ".claude/settings.json"
        registration_sha256 = "9" * 64
        (evidence_root / "workspace-setup.json").write_bytes(canary.canonical_bytes({
            "schema_version": canary.SCHEMA_VERSION,
            "run_id": self.run_id,
            "manifest_sha256": facts["manifest_sha256"],
            "workspace": approved["paths"]["workspace_root"],
            "fixture": str(fixture),
            "workspace_settings_role": "assembly-evidence-only",
            "claude_project_registration": {
                "source_path": str(Path(approved["paths"]["workspace_root"]) / ".claude/settings.json"),
                "destination_path": str(fixture_settings),
                "source_sha256": registration_sha256,
                "destination_sha256": registration_sha256,
                "sdk_cwd": str(fixture),
                "registration_state": "configured-unverified",
                "host_invocation_observed": False,
                "command_inventory": [{
                    "event": "UserPromptSubmit",
                    "matcher": None,
                    "group_index": 0,
                    "hook_index": 0,
                    "argv": [str(Path(approved["paths"]["workspace_root"]) / "hooks/resolver/inject-resolver.sh")],
                    "payload_relative_path": "hooks/resolver/inject-resolver.sh",
                    "executable_sha256": "8" * 64,
                }],
            },
            "standing_order_automations_enabled": False,
            "pi_capability_state": "unsupported-unverified",
            "authorization_effect": "none",
        }))
        for index, backend in enumerate(approved["backends"]):
            began = start + timedelta(minutes=11 * index)
            ended = began + timedelta(minutes=10)
            events = []
            for name in sorted(canary.EVENTS):
                reference = f"backend-{backend['sequence']}/{name}.jsonl"
                artifact = evidence_root / reference
                artifact.parent.mkdir(parents=True, exist_ok=True)
                artifact.write_bytes(f"host-export-fixture:{backend['sequence']}:{name}\n".encode())
                event = {
                    "name": name,
                    "source": "host-observed",
                    "artifact_reference": reference,
                    "artifact_sha256": canary.sha256_bytes(artifact.read_bytes()),
                }
                if backend["sequence"] == 1 and name in {"startup_resolver", "no_op_detection"}:
                    event.update({
                        "registered_settings_path": str(fixture_settings),
                        "registered_settings_sha256": registration_sha256,
                    })
                    if name == "no_op_detection":
                        event["settings_restored_sha256"] = registration_sha256
                events.append(event)
            runtime_event = next(event for event in events if event["name"] == "startup_resolver")
            runtime_identity = (
                "@anthropic-ai/claude-agent-sdk@0.3.296"
                if backend["installed_build_key"] == "claude_sdk"
                else "@earendil-works/pi-ai/openai-codex-responses"
            )
            runs.append({
                "sequence": backend["sequence"],
                "connection": backend["connection"],
                "model": backend["model"],
                "installed_build_key": backend["installed_build_key"],
                "installed_build_discovery_sha256": discovery["discovery_sha256"],
                "runtime_identity": {
                    "state": "observed", "source": "host-observed", "identity": runtime_identity,
                    "artifact_reference": runtime_event["artifact_reference"],
                    "artifact_sha256": runtime_event["artifact_sha256"],
                },
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
        result = self.validate_evidence(approved, evidence)
        self.assertEqual(result["events"], 18)
        self.assertEqual(result["timing_seconds"], {
            "backend_runs": [600.0, 600.0], "transitions": [60.0], "overall": 1260.0,
        })
        self.assertEqual(result["status"], "evidence-consistent-unverified")
        self.assertEqual(result["authorization_effect"], "none")
        evidence["backend_runs"][1]["model_self_report_used"] = True
        with self.assertRaisesRegex(canary.PacketError, "self-report"):
            self.validate_evidence(approved, evidence)
        evidence["backend_runs"][1]["model_self_report_used"] = False
        evidence["provenance"]["kind"] = "synthetic"
        with self.assertRaisesRegex(canary.PacketError, "Synthetic|synthetic"):
            self.validate_evidence(approved, evidence)
        approved, evidence = self.approved_evidence()
        evidence["backend_runs"][0]["outcome"] = "unsupported-unverified"
        with self.assertRaisesRegex(canary.PacketError, "unsupported/unverified"):
            self.validate_evidence(approved, evidence)
        approved, evidence = self.approved_evidence()
        evidence["backend_runs"][1]["runtime_identity"]["state"] = "unsupported-unverified"
        with self.assertRaisesRegex(canary.PacketError, "runtime identity is unsupported/unverified"):
            self.validate_evidence(approved, evidence)
        approved, evidence = self.approved_evidence()
        evidence["backend_runs"][0]["installed_build_discovery_sha256"] = "0" * 64
        with self.assertRaisesRegex(canary.PacketError, "installed build discovery mismatch"):
            self.validate_evidence(approved, evidence)
        approved, evidence = self.approved_evidence()
        startup = next(
            event for event in evidence["backend_runs"][0]["host_events"]
            if event["name"] == "startup_resolver"
        )
        startup["registered_settings_path"] = str(Path(approved["paths"]["workspace_root"]) / ".claude/settings.json")
        with self.assertRaisesRegex(canary.PacketError, "fixture-local registered settings path"):
            self.validate_evidence(approved, evidence)
        approved, evidence = self.approved_evidence()
        pi_startup = next(
            event for event in evidence["backend_runs"][1]["host_events"]
            if event["name"] == "startup_resolver"
        )
        pi_startup["registered_settings_path"] = str(Path(approved["paths"]["temp_root"]) / "fixture/repo/.claude/settings.json")
        with self.assertRaisesRegex(canary.PacketError, "cannot establish Pi"):
            self.validate_evidence(approved, evidence)
        approved, evidence = self.approved_evidence()
        setup_receipt_path = Path(approved["paths"]["evidence_root"]) / "workspace-setup.json"
        setup_receipt = json.loads(setup_receipt_path.read_text())
        setup_receipt["claude_project_registration"]["command_inventory"][0]["argv"] = ["/foreign/hook"]
        setup_receipt_path.write_bytes(canary.canonical_bytes(setup_receipt))
        with self.assertRaisesRegex(canary.PacketError, "argv differs from pinned workspace payload"):
            self.validate_evidence(approved, evidence)

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
                self.validate_evidence(approved, evidence)

    def test_evidence_requires_confined_unique_digest_bound_artifacts(self):
        approved, evidence = self.approved_evidence()
        event = evidence["backend_runs"][0]["host_events"][0]
        event["artifact_sha256"] = "0" * 64
        with self.assertRaisesRegex(canary.PacketError, "digest mismatch"):
            self.validate_evidence(approved, evidence)

        approved, evidence = self.approved_evidence()
        evidence["backend_runs"][0]["host_events"][0]["artifact_reference"] = "../escape.jsonl"
        with self.assertRaisesRegex(canary.PacketError, "confined"):
            self.validate_evidence(approved, evidence)

        approved, evidence = self.approved_evidence()
        first = evidence["backend_runs"][0]["host_events"][0]
        evidence["backend_runs"][1]["host_events"][0]["artifact_reference"] = first["artifact_reference"]
        with self.assertRaisesRegex(canary.PacketError, "unique"):
            self.validate_evidence(approved, evidence)

    def test_evidence_enforces_per_backend_transition_overlap_and_overall_budgets(self):
        approved, evidence = self.approved_evidence()
        evidence["backend_runs"][0]["ended_at"] = (
            datetime.fromisoformat(evidence["backend_runs"][0]["started_at"]) + timedelta(seconds=901)
        ).isoformat()
        with self.assertRaisesRegex(canary.PacketError, "per_backend"):
            self.validate_evidence(approved, evidence)

        approved, evidence = self.approved_evidence()
        first_end = datetime.fromisoformat(evidence["backend_runs"][0]["ended_at"])
        evidence["backend_runs"][1]["started_at"] = (first_end + timedelta(seconds=181)).isoformat()
        evidence["backend_runs"][1]["ended_at"] = (first_end + timedelta(seconds=781)).isoformat()
        with self.assertRaisesRegex(canary.PacketError, "transition"):
            self.validate_evidence(approved, evidence)

        approved, evidence = self.approved_evidence()
        first_end = datetime.fromisoformat(evidence["backend_runs"][0]["ended_at"])
        evidence["backend_runs"][1]["started_at"] = (first_end - timedelta(seconds=1)).isoformat()
        evidence["backend_runs"][1]["ended_at"] = (first_end + timedelta(seconds=599)).isoformat()
        with self.assertRaisesRegex(canary.PacketError, "overlap"):
            self.validate_evidence(approved, evidence)

        approved, evidence = self.approved_evidence()
        approved["timeouts_seconds"]["per_backend"] = 1000
        approved["timeouts_seconds"]["transition"] = 1000
        approved["timeouts_seconds"]["overall"] = 2400
        approved["operator_approval"]["subject_sha256"] = canary.approval_subject_sha256(approved)
        facts = self.validate_manifest(approved, require_approval_record=True)
        evidence["manifest_sha256"] = facts["manifest_sha256"]
        setup_receipt_path = Path(approved["paths"]["evidence_root"]) / "workspace-setup.json"
        setup_receipt = json.loads(setup_receipt_path.read_text())
        setup_receipt["manifest_sha256"] = facts["manifest_sha256"]
        setup_receipt_path.write_bytes(canary.canonical_bytes(setup_receipt))
        start = datetime.fromisoformat(evidence["backend_runs"][0]["started_at"])
        evidence["backend_runs"][0]["ended_at"] = (start + timedelta(seconds=900)).isoformat()
        evidence["backend_runs"][1]["started_at"] = (start + timedelta(seconds=1500)).isoformat()
        evidence["backend_runs"][1]["ended_at"] = (start + timedelta(seconds=2500)).isoformat()
        with self.assertRaisesRegex(canary.PacketError, "overall"):
            self.validate_evidence(approved, evidence)

    def test_cleanup_requires_receipt_and_real_absence(self):
        approved = record_external_approval(self.value)
        facts = self.validate_manifest(approved, require_approval_record=True)
        receipt = {
            "schema_version": canary.SCHEMA_VERSION,
            "run_id": self.run_id,
            "manifest_sha256": facts["manifest_sha256"],
            "workspace_absent": True,
            "workspace_setup_receipt_sha256": "7" * 64,
            "fixture_claude_settings_registered_sha256": "9" * 64,
            "fixture_claude_settings_observed_sha256_before_cleanup": "9" * 64,
            "fixture_claude_settings_digest_match": True,
            "fixture_claude_settings_absent": True,
            "temp_root_absent": True,
            "disposable_refs_absent": True,
            "outside_allowlist_unchanged": True,
        }
        result = canary.verify_cleanup(approved, receipt, _test_expected_temp_base=self.temp_base)
        self.assertEqual(result["status"], "local-cleanup-absence-observed")
        self.assertEqual(result["authorization_effect"], "none")
        mismatched = copy.deepcopy(receipt)
        mismatched["fixture_claude_settings_observed_sha256_before_cleanup"] = "8" * 64
        with self.assertRaisesRegex(canary.PacketError, "differs from setup registration"):
            canary.verify_cleanup(approved, mismatched, _test_expected_temp_base=self.temp_base)
        self.temp.mkdir(parents=True)
        with self.assertRaisesRegex(canary.PacketError, "temp root still exists"):
            canary.verify_cleanup(approved, receipt, _test_expected_temp_base=self.temp_base)

    def test_side_effect_set_backend_order_and_timeouts_are_closed(self):
        broken = copy.deepcopy(self.value)
        broken["allowed_side_effects"].append("publish_release")
        with self.assertRaises(canary.PacketError):
            self.validate_manifest(broken)
        broken = copy.deepcopy(self.value)
        broken["backends"].reverse()
        with self.assertRaises(canary.PacketError):
            self.validate_manifest(broken)
        broken = copy.deepcopy(self.value)
        broken["timeouts_seconds"]["overall"] = 100
        with self.assertRaises(canary.PacketError):
            self.validate_manifest(broken)


if __name__ == "__main__":
    unittest.main()
