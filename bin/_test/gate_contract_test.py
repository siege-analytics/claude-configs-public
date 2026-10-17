#!/usr/bin/env python3
"""Focused hostile tests for the bounded #851 gate contract."""
from __future__ import annotations

import copy
import json
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bin"))
import gate_contract as gc  # noqa: E402


class GateContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = gc.load_contract(ROOT)
        cls.fixtures = gc.load_fixtures(ROOT, cls.contract)

    def mutation(self) -> dict:
        return copy.deepcopy(self.contract)

    def assert_invalid(self, data: dict, needle: str) -> None:
        with self.assertRaisesRegex(ValueError, needle):
            gc.validate_contract(data, ROOT, check_paths=False)

    def write_generated_fixture(self, dist: Path, *, omit: str = "") -> None:
        ca = dist / "craft-agent"; ca.mkdir(parents=True)
        digest = gc.contract_digest(self.contract)
        (ca / "enforcement-manifest.json").write_text(json.dumps({
            "gate_contract_source": gc.CONTRACT.as_posix(),
            "gate_contract_sha256": digest,
            "gate_contract": self.contract,
            "gates": [{"id": "branch-guard", "hook": "hooks/git/branch-guard.sh",
                       "surface": "native-git-pre-push", "blocking": True}],
        }))
        (ca / "settings-enforcement.json").write_text(json.dumps({
            "_gate_contract": {"schema_version": self.contract["schema_version"],
                               "contract_version": self.contract["contract_version"],
                               "source": gc.CONTRACT.as_posix(), "sha256": digest,
                               "evidence_state": "configured"},
            "hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command",
                "command": "/path/to/hooks/resolver/ca-enforcement-gate.sh", "timeout": 15}]}]},
            "env": {"CLAUDE_CA_ENFORCE": "1"},
        }))
        for capability in self.contract["capabilities"]:
            if capability["id"] == omit:
                continue
            for package in capability["package_paths"]:
                path = dist / Path(*Path(package).parts[1:])
                path.parent.mkdir(parents=True, exist_ok=True)
                if capability["id"] == "native-ticket-commit-msg":
                    shutil.copy2(ROOT / ".githooks/commit-msg", path)
                elif capability["id"] == "native-branch-pre-push":
                    path.write_text("#!/usr/bin/env bash\nset -u\n"
                                    'HOOKS_ROOT="$(cd "$(dirname "$0")/../hooks" && pwd)"\n'
                                    "# Gate: branch-guard — Commit to protected branch\n"
                                    'GATE_SCRIPT="$HOOKS_ROOT/git/branch-guard.sh"\n'
                                    'if [[ -x "$GATE_SCRIPT" ]] && ! bash "$GATE_SCRIPT" "$@"; then\n'
                                    '  echo "pre-push: branch-guard gate BLOCKED push" >&2\n'
                                    "  exit 1\nfi\nexit 0\n")
                    path.chmod(path.stat().st_mode | stat.S_IXUSR)
                else:
                    path.write_text("fixture")
        (ca / "bin").mkdir(exist_ok=True)
        (ca / "catalog").mkdir(exist_ok=True)
        shutil.copy2(ROOT / "bin/review-risk.py", ca / "bin/review-risk.py")
        shutil.copy2(ROOT / "catalog/review-risk-policy.json", ca / "catalog/review-risk-policy.json")

    def test_source_and_two_fixtures_validate(self):
        self.assertEqual(3, len(self.contract["policy_fields"]))
        self.assertEqual(4, len(self.contract["capabilities"]))
        self.assertEqual(["strict-release", "synthetic-trunk"], [item["fixture_id"] for item in self.fixtures])

    def test_schema_drift_rejects(self):
        canonical_schema = gc.read_json(ROOT / gc.SCHEMA)
        gc.validate_json_schema_instance(self.contract, canonical_schema, canonical_schema)
        schema = gc.read_json(ROOT / gc.SCHEMA)
        schema["properties"]["decision_values"]["const"] = ["allow", "deny"]
        with self.assertRaisesRegex(ValueError, "decision values disagree"):
            gc.validate_schema_document(schema)
        schema = gc.read_json(ROOT / gc.SCHEMA)
        schema["properties"]["unreviewed"] = {"type": "string"}
        with self.assertRaisesRegex(ValueError, "root fields disagree"):
            gc.validate_schema_document(schema)
        schema = gc.read_json(ROOT / gc.SCHEMA)
        schema["$defs"]["capability"]["properties"]["configured_evidence_only"]["const"] = False
        with self.assertRaisesRegex(ValueError, "configured evidence constraint disagrees"):
            gc.validate_schema_document(schema)
        schema = gc.read_json(ROOT / gc.SCHEMA)
        schema["$defs"]["override_policy"]["properties"]["project_paths"] = {"type": "string"}
        with self.assertRaisesRegex(ValueError, "override path types disagree"):
            gc.validate_schema_document(schema)
        for mutate in (
            lambda value: value["properties"]["contract_version"].update({"pattern": "^not-the-current-version$"}),
            lambda value: value["$defs"]["result_contract"]["properties"]["type"].update({"enum": ["other"]}),
            lambda value: value["$defs"]["capability"]["properties"]["registered_path"].update({"minLength": 99}),
        ):
            schema = gc.read_json(ROOT / gc.SCHEMA); mutate(schema)
            with self.assertRaisesRegex(ValueError, "complete schema digest differs"):
                gc.validate_schema_document(schema)

    def test_unknown_top_level_and_nested_fields_reject(self):
        data = self.mutation(); data["surprise"] = True
        self.assert_invalid(data, "unknown=.*surprise")
        data = self.mutation(); data["policy_fields"][0]["surprise"] = True
        self.assert_invalid(data, "unknown=.*surprise")
        data = self.mutation(); data["capabilities"][0]["result_contract"]["surprise"] = []
        self.assert_invalid(data, "unknown=.*surprise")

    def test_duplicate_and_conflicting_declarations_reject(self):
        data = self.mutation(); data["policy_fields"].append(copy.deepcopy(data["policy_fields"][0]))
        self.assert_invalid(data, "duplicate policy field id")
        data = self.mutation(); data["capabilities"].append(copy.deepcopy(data["capabilities"][0]))
        self.assert_invalid(data, "duplicate capability id")
        data = self.mutation(); data["capabilities"][1]["acceptance_probe_ids"] = data["capabilities"][0]["acceptance_probe_ids"]
        self.assert_invalid(data, "duplicate acceptance probe id")
        data = self.mutation(); data["policy_fields"][0]["override_policy"]["project_paths"] = ["protected_acceptance"]
        self.assert_invalid(data, "contradictory override/lock")
        data = self.mutation(); data["capabilities"][0]["result_contract"]["deny"] = [0]
        self.assert_invalid(data, "result codes overlap")

    def test_absent_capability_and_nonconfigured_claim_reject(self):
        data = self.mutation(); data["policy_fields"][0]["required_capability_ids"] = ["missing-capability"]
        self.assert_invalid(data, "unknown required capabilities")
        data = self.mutation(); data["capabilities"][0]["configured_evidence_only"] = False
        self.assert_invalid(data, "configured evidence only")

    def test_wrong_declared_registration_and_extra_packages_reject(self):
        data = self.mutation()
        branch = next(value for value in data["capabilities"] if value["id"] == "native-branch-pre-push")
        branch["registered_path"] = "dist/craft-agent/.githooks/not-installed"
        self.assert_invalid(data, "registration/package declaration differs")
        data = self.mutation()
        protected = next(value for value in data["capabilities"] if value["id"] == "protected-range-validation")
        protected["registered_path"] = "README.md"
        self.assert_invalid(data, "registration/package declaration differs")
        for prepend in (True, False):
            data = self.mutation()
            ticket = next(value for value in data["capabilities"] if value["id"] == "native-ticket-commit-msg")
            broken = "dist/craft-agent/.githooks/broken-commit-msg"
            ticket["package_paths"] = ([broken] + ticket["package_paths"] if prepend
                                       else ticket["package_paths"] + [broken])
            self.assert_invalid(data, "registration/package declaration differs")

    def test_unsafe_missing_and_nonexecutable_registered_paths_reject(self):
        data = self.mutation(); data["capabilities"][0]["registered_path"] = "../outside"
        with self.assertRaisesRegex(ValueError, "stay within repository"):
            gc.validate_contract(data, ROOT)
        data = self.mutation(); data["capabilities"][0]["registered_path"] = "missing-hook"
        with self.assertRaisesRegex(ValueError, "path is missing"):
            gc.validate_contract(data, ROOT)
        data = self.mutation(); data["capabilities"][0]["registered_path"] = "catalog/gate-contracts.json"
        with self.assertRaisesRegex(ValueError, "not executable"):
            gc.validate_contract(data, ROOT)

    def test_fixture_unknown_value_and_undeclared_change_reject(self):
        fixture = copy.deepcopy(self.fixtures[0]); fixture["values"]["branch-policy"]["other"] = "main"
        with self.assertRaisesRegex(ValueError, "value fields differ"):
            gc.validate_fixture(fixture, self.contract, "fixture")
        fixture = copy.deepcopy(self.fixtures[0]); fixture["values"]["branch-policy"]["integration_branch"] = "main"
        with self.assertRaisesRegex(ValueError, "declared overrides do not match"):
            gc.validate_fixture(fixture, self.contract, "fixture")

    def test_fixture_project_cannot_unlock_parent_floor(self):
        fixture = copy.deepcopy(self.fixtures[0])
        fixture["values"]["ticket-requirement"]["required"] = False
        fixture["declared_overrides"] = [{"field_id": "ticket-requirement", "path": "required", "layer": "project"}]
        with self.assertRaisesRegex(ValueError, "unauthorized project override"):
            gc.validate_fixture(fixture, self.contract, "fixture")

    def test_fixture_missing_procedure_rejects(self):
        fixture = copy.deepcopy(self.fixtures[0])
        fixture["values"]["review-procedure-binding"]["procedure"] = "missing-review"
        fixture["declared_overrides"] = [{"field_id": "review-procedure-binding", "path": "procedure", "layer": "project"}]
        with self.assertRaisesRegex(ValueError, "path is missing"):
            gc.validate_fixture(fixture, self.contract, "fixture")

    def test_reordered_duplicate_repository_identity_rejects(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for relative in gc.FIXTURES:
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text((ROOT / relative).read_text())
            for procedure in ("self-review", "hostile-review"):
                skill = root / f"skills/{procedure}/SKILL.md"
                skill.parent.mkdir(parents=True, exist_ok=True); skill.write_text("fixture")
            first = json.loads((root / gc.FIXTURES[0]).read_text())
            second = json.loads((root / gc.FIXTURES[1]).read_text())
            identity = first["repository_identity"]
            second["repository_identity"] = {
                "repository": identity["repository"],
                "owner": identity["owner"],
                "host": identity["host"],
            }
            (root / gc.FIXTURES[1]).write_text(json.dumps(second))
            with self.assertRaisesRegex(ValueError, "repository identities are ambiguous"):
                gc.load_fixtures(root, self.contract)

    def test_mixed_parent_locks_reject(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for relative in gc.FIXTURES:
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text((ROOT / relative).read_text())
            for procedure in ("self-review", "hostile-review"):
                skill = root / f"skills/{procedure}/SKILL.md"
                skill.parent.mkdir(parents=True, exist_ok=True); skill.write_text("fixture")
            changed = json.loads((root / gc.FIXTURES[1]).read_text())
            changed["parent_lock"]["revision"] = "a" * 40
            (root / gc.FIXTURES[1]).write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, "mixed parent locks"):
                gc.load_fixtures(root, self.contract)

    def test_generated_manifest_settings_and_packages_agree(self):
        with tempfile.TemporaryDirectory() as raw:
            dist = Path(raw); self.write_generated_fixture(dist)
            gc.validate_generated(ROOT, dist, self.contract)
            manifest_path = dist / "craft-agent/enforcement-manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["gate_contract_sha256"] = "0" * 64
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "manifest disagrees"):
                gc.validate_generated(ROOT, dist, self.contract)

    def test_conditional_or_early_exit_ci_step_rejects(self):
        valid = """      - name: Gate contract and generated agreement
        run: |
          python3 bin/_test/gate_contract_test.py
          python3 bin/gate_contract.py --check --probe --generated-root dist
          python3 bin/_test/effective_policy_test.py
          python3 bin/effective_policy.py validate --generated-root dist

      - name: Next step
        run: true
"""
        gc.validate_protected_workflow(valid)
        for mutation in (
            valid.replace("        run: |", "        if: ${{ false }}\n        run: |"),
            valid.replace("        run: |", "        run: |\n          exit 0"),
            valid.replace("--generated-root dist", "--generated-root dist || true"),
        ):
            with self.subTest(mutation=mutation):
                with self.assertRaisesRegex(ValueError, "conditional, altered, or non-exact"):
                    gc.validate_protected_workflow(mutation)

    def test_base_controlled_adapter_registration_and_old_guard_are_both_required(self):
        valid = (ROOT / ".github/workflows/pr-base-guard.yml").read_text()
        gc.validate_protected_adapter_workflow(valid)
        mutations = (
            valid.replace("fetch-depth: 0  # selected policy snapshot must be an available ancestor", "fetch-depth: 1"),
            valid.replace("ref: ${{ github.event.pull_request.base.sha }}", "ref: ${{ github.event.pull_request.head.sha }}"),
            valid.replace("run: bash ../policy/scripts/ci/check-branch-topology.sh", "run: true"),
            valid.replace("HEAD_REPO: ${{ github.event.pull_request.head.repo.full_name }}", "HEAD_REPO: untrusted/example"),
            valid.replace("persist-credentials: false", "persist-credentials: true", 1),
            valid.replace("branches: [main, develop]", "branches: [main]"),
            valid.replace("    runs-on: ubuntu-latest", "    if: false\n    runs-on: ubuntu-latest"),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.assertNotEqual(valid, mutation)
                with self.assertRaisesRegex(ValueError, "reviewed complete registration"):
                    gc.validate_protected_adapter_workflow(mutation)

    def test_generated_registration_removal_rejects(self):
        with tempfile.TemporaryDirectory() as raw:
            dist = Path(raw); self.write_generated_fixture(dist)
            settings_path = dist / "craft-agent/settings-enforcement.json"
            settings = json.loads(settings_path.read_text()); settings["hooks"] = {}
            settings_path.write_text(json.dumps(settings))
            with self.assertRaisesRegex(ValueError, "lost or changed the registered wrapper"):
                gc.validate_generated(ROOT, dist, self.contract)
        with tempfile.TemporaryDirectory() as raw:
            dist = Path(raw); self.write_generated_fixture(dist)
            manifest_path = dist / "craft-agent/enforcement-manifest.json"
            manifest = json.loads(manifest_path.read_text()); manifest["gates"] = []
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "lost gate registrations"):
                gc.validate_generated(ROOT, dist, self.contract)

    def test_generated_missing_package_rejects(self):
        with tempfile.TemporaryDirectory() as raw:
            dist = Path(raw); self.write_generated_fixture(dist, omit="procedure-binding-resolution")
            with self.assertRaisesRegex(ValueError, "path is missing"):
                gc.validate_generated(ROOT, dist, self.contract)

    def test_packaged_noop_pre_push_rejects(self):
        with tempfile.TemporaryDirectory() as raw:
            dist = Path(raw); self.write_generated_fixture(dist)
            pre_push = dist / "craft-agent/.githooks/pre-push"
            original = pre_push.read_text()
            pre_push.write_text("#!/usr/bin/env bash\nexit 0\n" + original)
            pre_push.chmod(0o755)
            with self.assertRaisesRegex(ValueError, "packaged pre-push accepted"):
                gc.validate_generated(ROOT, dist, self.contract)

    def test_packaged_noop_and_symlink_ticket_reject(self):
        with tempfile.TemporaryDirectory() as raw:
            dist = Path(raw); self.write_generated_fixture(dist)
            ticket = dist / "craft-agent/.githooks/commit-msg"
            ticket.write_text("#!/usr/bin/env bash\nexit 0\n"); ticket.chmod(0o755)
            with self.assertRaisesRegex(ValueError, "bytes disagree"):
                gc.validate_generated(ROOT, dist, self.contract)
        with tempfile.TemporaryDirectory() as raw:
            dist = Path(raw); self.write_generated_fixture(dist)
            ticket = dist / "craft-agent/.githooks/commit-msg"; ticket.unlink()
            ticket.symlink_to(ROOT / ".githooks/commit-msg")
            with self.assertRaisesRegex(ValueError, "symlink"):
                gc.validate_generated(ROOT, dist, self.contract)

    def test_real_ticket_executable_rejects_invalid_candidate(self):
        gc.run_ticket_probe(ROOT, self.contract)

    def test_noop_registered_executable_cannot_claim_live_enforcement(self):
        with tempfile.TemporaryDirectory() as raw:
            noop = Path(raw) / "noop"
            noop.write_text("#!/usr/bin/env bash\nexit 0\n")
            noop.chmod(noop.stat().st_mode | stat.S_IXUSR)
            with self.assertRaisesRegex(ValueError, "accepted or misclassified the invalid candidate"):
                gc.run_ticket_probe(ROOT, self.contract, executable_override=noop)


if __name__ == "__main__":
    unittest.main(verbosity=2)
