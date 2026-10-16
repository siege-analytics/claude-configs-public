#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("effective_policy", ROOT / "bin/effective_policy.py")
assert spec and spec.loader
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class EffectivePolicyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract, cls.approved = policy.load_inputs(ROOT)

    def context(self, repository="strict-release", *, capabilities=None, identities=None):
        if identities is None:
            identities = [{
                "source": "explicit-target", "host": "github.example.invalid",
                "owner": "synthetic-org", "repository": repository,
            }]
        return {
            "identities": identities,
            "capabilities": capabilities or {},
            "install_configuration": {},
            "task_evidence": [],
        }

    def operation(self, kind="feature-merge", **extra):
        value = {"type": kind}
        if kind == "feature-merge":
            value["target_branch"] = extra.get("target_branch", "develop")
        elif kind == "ticket-commit":
            value["message"] = extra.get("message", "feat: change #42")
        return value

    def explain(self, repository="strict-release", *, operation=None, capabilities=None, identities=None, candidate=None):
        return policy.explain(
            self.contract, self.approved,
            self.context(repository, capabilities=capabilities, identities=identities),
            operation or self.operation(), candidate,
        )

    def all_verified(self):
        return {item["id"]: "verified" for item in self.contract["capabilities"]}

    def test_catalog_valid_and_sealed_to_contract(self):
        self.assertEqual(policy.digest(self.contract), self.approved["contract_sha256"])
        self.assertEqual("34f014bd8aaf55e545a6a2fe3094242aa40cb182", self.approved["approved_policy_revision"])

    def test_strict_feature_to_develop_policy_allows_but_enforcement_is_unproved(self):
        result = self.explain(capabilities=self.all_verified())
        self.assertEqual("allow", result["decision"]["policy"])
        self.assertEqual("unknown", result["decision"]["final"])
        self.assertIn("unauthenticated evaluator inputs", result["decision"]["reasons"][-1])
        self.assertEqual("develop", result["values"]["branch-policy"]["integration_branch"])
        self.assertEqual("github.com", result["approved_policy"]["parent_lock"]["host"])
        self.assertEqual(self.approved["contract_sha256"], result["approved_policy"]["parent_lock"]["digest"])

    def test_strict_feature_to_main_denies(self):
        result = self.explain(operation=self.operation(target_branch="main"), capabilities=self.all_verified())
        self.assertEqual("deny", result["decision"]["final"])

    def test_trunk_feature_to_main_policy_allows_but_enforcement_is_unproved(self):
        result = self.explain("synthetic-trunk", operation=self.operation(target_branch="main"), capabilities=self.all_verified())
        self.assertEqual("allow", result["decision"]["policy"])
        self.assertEqual("unknown", result["decision"]["final"])
        self.assertEqual("main", result["values"]["branch-policy"]["integration_branch"])
        self.assertEqual("hostile-review", result["values"]["review-procedure-binding"]["procedure"])

    def test_trunk_feature_to_develop_denies(self):
        result = self.explain("synthetic-trunk", operation=self.operation(target_branch="develop"), capabilities=self.all_verified())
        self.assertEqual("deny", result["decision"]["final"])

    def test_org_and_project_provenance_is_complete(self):
        result = self.explain("synthetic-trunk", operation=self.operation(target_branch="main"), capabilities=self.all_verified())
        branch = result["provenance"]["branch-policy"]["integration_branch"]
        review = result["provenance"]["review-procedure-binding"]["procedure"]
        locked = result["provenance"]["ticket-requirement"]["required"]
        self.assertEqual(("organization-profile", "synthetic-trunk"), (branch["layer"], branch["source"]))
        self.assertEqual("develop", branch["replaced"][0]["value"])
        self.assertEqual("repository", branch["scope"])
        self.assertEqual(["native-branch-pre-push", "protected-range-validation"], branch["required_capabilities"])
        self.assertEqual(("project", "synthetic-trunk"), (review["layer"], review["source"]))
        self.assertEqual("review-procedure", review["scope"])
        self.assertEqual(["procedure-binding-resolution"], review["required_capabilities"])
        self.assertTrue(locked["locked"])

    def test_missing_identity_is_unknown_but_explainable(self):
        result = self.explain(identities=[])
        self.assertEqual("unknown", result["state"])
        self.assertEqual("unknown", result["decision"]["final"])

    def test_foreign_host_owner_and_basename_are_unknown(self):
        for host, owner, repository in [
            ("foreign.example", "synthetic-org", "strict-release"),
            ("github.example.invalid", "foreign-owner", "strict-release"),
            ("github.example.invalid", "synthetic-org", "other"),
        ]:
            identities = [{"source": "explicit-target", "host": host, "owner": owner, "repository": repository}]
            with self.subTest(identity=(host, owner, repository)):
                self.assertEqual("unknown", self.explain(identities=identities)["state"])

    def test_disagreeing_identity_sources_are_ambiguous(self):
        identities = [
            {"source": "explicit-target", "host": "github.example.invalid", "owner": "synthetic-org", "repository": "strict-release"},
            {"source": "git-origin", "host": "github.example.invalid", "owner": "synthetic-org", "repository": "synthetic-trunk"},
        ]
        result = self.explain(identities=identities)
        self.assertEqual("ambiguous", result["state"])
        self.assertEqual("unknown", result["decision"]["final"])

    def test_agreeing_identity_sources_are_retained(self):
        identities = [
            {"source": "explicit-target", "host": "GITHUB.EXAMPLE.INVALID.", "owner": "Synthetic-Org", "repository": "strict-release.git"},
            {"source": "git-origin", "host": "github.example.invalid", "owner": "synthetic-org", "repository": "strict-release"},
        ]
        result = self.explain(identities=identities, capabilities=self.all_verified())
        self.assertEqual("resolved", result["state"])
        self.assertEqual(2, len(result["identity_sources"]))

    def test_duplicate_identity_sources_reject(self):
        identities = [
            {"source": "git-origin", "host": "github.example.invalid", "owner": "synthetic-org", "repository": "strict-release"},
            {"source": "git-origin", "host": "github.example.invalid", "owner": "synthetic-org", "repository": "strict-release"},
        ]
        with self.assertRaisesRegex(ValueError, "duplicate identity source"):
            self.explain(identities=identities)

    def test_unknown_policy_field_rejects(self):
        candidate = copy.deepcopy(self.approved)
        candidate["organization_profiles"][0]["values"]["new-policy"] = {"x": True}
        with self.assertRaisesRegex(ValueError, "unknown policy fields"):
            policy.validate_policy(candidate, self.contract, "candidate")

    def test_unknown_path_rejects(self):
        candidate = copy.deepcopy(self.approved)
        candidate["organization_profiles"][0]["values"]["branch-policy"] = {"mystery": "main"}
        with self.assertRaisesRegex(ValueError, "unknown paths"):
            policy.validate_policy(candidate, self.contract, "candidate")

    def test_locked_org_override_rejects(self):
        candidate = copy.deepcopy(self.approved)
        candidate["organization_profiles"][0]["values"]["ticket-requirement"] = {"required": False}
        with self.assertRaisesRegex(ValueError, "unauthorized organization-profile override"):
            policy.validate_policy(candidate, self.contract, "candidate")

    def test_org_value_at_project_layer_rejects(self):
        candidate = copy.deepcopy(self.approved)
        candidate["projects"][0]["values"]["branch-policy"] = {"integration_branch": "main"}
        with self.assertRaisesRegex(ValueError, "unauthorized project override"):
            policy.validate_policy(candidate, self.contract, "candidate")

    def test_invalid_override_value_rejects(self):
        candidate = copy.deepcopy(self.approved)
        candidate["organization_profiles"][0]["values"]["branch-policy"] = {"integration_branch": "trunk"}
        with self.assertRaisesRegex(ValueError, "outside enum"):
            policy.validate_policy(candidate, self.contract, "candidate")

    def test_reordered_duplicate_project_identity_rejects(self):
        candidate = copy.deepcopy(self.approved)
        duplicate = copy.deepcopy(candidate["projects"][0])
        duplicate["id"] = "duplicate-strict"
        duplicate["repository_identity"] = {"repository": "strict-release", "host": "GITHUB.EXAMPLE.INVALID.", "owner": "Synthetic-Org"}
        candidate["projects"].append(duplicate)
        with self.assertRaisesRegex(ValueError, "duplicate repository identity"):
            policy.validate_policy(candidate, self.contract, "candidate")

    def test_wrong_contract_digest_rejects(self):
        candidate = copy.deepcopy(self.approved)
        candidate["contract_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "digest disagrees"):
            policy.validate_policy(candidate, self.contract, "candidate")

    def test_alternate_approved_policy_path_rejects(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "policy.json"
            path.write_text(json.dumps(self.approved))
            with self.assertRaisesRegex(ValueError, "canonical checked-in source"):
                policy.load_inputs(ROOT, path)

    def test_approved_source_and_fixtures_cannot_drift(self):
        changed = copy.deepcopy(self.approved)
        changed["organization_profiles"][0]["values"]["branch-policy"] = {"integration_branch": "main"}
        policy.validate_policy(changed, self.contract, "changed")
        with self.assertRaisesRegex(ValueError, "resolved values disagree"):
            policy.validate_fixture_agreement(ROOT, self.contract, changed, policy._gate_contract_module())
        changed = copy.deepcopy(self.approved)
        changed["approved_policy_revision"] = "a" * 40
        with self.assertRaisesRegex(ValueError, "revision disagrees"):
            policy.validate_policy(changed, self.contract, "changed")
        changed["parent_lock"]["revision"] = "a" * 40
        policy.validate_policy(changed, self.contract, "changed")
        with self.assertRaisesRegex(ValueError, "parent lock disagrees"):
            policy.validate_fixture_agreement(ROOT, self.contract, changed, policy._gate_contract_module())

    def test_valid_unapproved_loosening_never_selects_itself(self):
        candidate = copy.deepcopy(self.approved)
        candidate["organization_profiles"][0]["values"]["branch-policy"] = {"integration_branch": "main"}
        result = self.explain(operation=self.operation(target_branch="main"), capabilities=self.all_verified(), candidate=candidate)
        self.assertEqual("deny", result["decision"]["final"])
        self.assertEqual("develop", result["values"]["branch-policy"]["integration_branch"])
        self.assertEqual("schema-valid-proposal", result["proposed_policy"]["state"])
        self.assertEqual("not-evaluated-for-unapproved-proposal", result["proposed_policy"]["fixture_agreement"])
        self.assertEqual("none", result["proposed_policy"]["authorization_effect"])
        self.assertEqual("main", result["proposed_policy"]["changes"][0]["proposed"])

    def test_invalid_candidate_is_diagnostic_not_active(self):
        candidate = copy.deepcopy(self.approved)
        candidate["organization_profiles"][0]["values"]["ticket-requirement"] = {"required": False}
        result = self.explain(capabilities=self.all_verified(), candidate=candidate)
        self.assertEqual("allow", result["decision"]["policy"])
        self.assertEqual("unknown", result["decision"]["final"])
        self.assertEqual("rejected", result["proposed_policy"]["state"])

    def test_unverified_and_unsupported_capabilities_never_allow(self):
        result = self.explain(capabilities={})
        self.assertEqual("unknown", result["decision"]["final"])
        self.assertEqual("unverified", result["decision"]["capability_readiness"])
        capabilities = self.all_verified(); capabilities["protected-range-validation"] = "unsupported"
        result = self.explain(capabilities=capabilities)
        self.assertEqual("unknown", result["decision"]["final"])
        self.assertEqual("unsupported", result["decision"]["capability_readiness"])

    def test_configured_is_not_a_capability_state(self):
        with self.assertRaisesRegex(ValueError, "unsupported state"):
            self.explain(capabilities={"native-branch-pre-push": "configured"})

    def test_install_and_task_evidence_cannot_grant_authority(self):
        context = self.context(capabilities={})
        context["install_configuration"] = {"force_allow": True, "integration_branch": "main"}
        context["task_evidence"] = ["approved", "all-capabilities-verified"]
        result = policy.explain(self.contract, self.approved, context, self.operation(target_branch="main"))
        self.assertEqual("deny", result["decision"]["final"])
        self.assertEqual("none", result["install_configuration"]["authorization_effect"])
        self.assertEqual("none", result["task_evidence"]["authorization_effect"])

    def test_ticket_policy_and_capability_boundary(self):
        capabilities = self.all_verified()
        allow = self.explain(operation=self.operation("ticket-commit", message="fix: correct parser (#84)"), capabilities=capabilities)
        deny = self.explain(operation=self.operation("ticket-commit", message="fix: no ticket"), capabilities=capabilities)
        decoy = self.explain(operation=self.operation("ticket-commit", message="fix: token abc#84def"), capabilities=capabilities)
        self.assertEqual("allow", allow["decision"]["policy"])
        self.assertEqual("unknown", allow["decision"]["final"])
        self.assertEqual("deny", deny["decision"]["final"])
        self.assertEqual("deny", decoy["decision"]["final"])

    def test_review_binding_has_no_authorization_effect(self):
        capabilities = self.all_verified()
        result = self.explain("synthetic-trunk", operation=self.operation("review-procedure"), capabilities=capabilities)
        self.assertEqual("allow", result["decision"]["policy"])
        self.assertEqual("unknown", result["decision"]["final"])
        self.assertIn("authorization effect remains none", result["decision"]["reasons"][0])
        self.assertIn("hostile-review", result["resident_workflow"])

    def test_same_value_override_remains_visible_in_provenance(self):
        changed = copy.deepcopy(self.approved)
        changed["organization_profiles"][0]["values"]["branch-policy"] = {"integration_branch": "develop"}
        policy.validate_policy(changed, self.contract, "changed")
        project = changed["projects"][0]
        values, provenance = policy.resolve_values(self.contract, changed, project)
        item = provenance["branch-policy"]["integration_branch"]
        self.assertEqual("organization-profile", item["layer"])
        self.assertEqual("develop", item["replaced"][0]["value"])
        self.assertEqual("develop", values["branch-policy"]["integration_branch"])

    def test_cli_exit_codes_fail_closed_until_protected_adapter(self):
        script = str(ROOT / "bin/effective_policy.py")
        main_op = str(ROOT / "examples/scaffolding/feature-to-main-operation.json")
        develop_op = str(ROOT / "examples/scaffolding/feature-to-develop-operation.json")
        verified = ["--capability", "native-branch-pre-push=verified", "--capability", "protected-range-validation=verified"]
        allow_policy = subprocess.run([sys.executable, script, "check", "--identity", "github.example.invalid/synthetic-org/strict-release", "--operation", develop_op, *verified], capture_output=True, text=True)
        deny = subprocess.run([sys.executable, script, "check", "--identity", "github.example.invalid/synthetic-org/strict-release", "--operation", main_op, *verified], capture_output=True, text=True)
        unknown = subprocess.run([sys.executable, script, "check", "--operation", main_op], capture_output=True, text=True)
        explain_deny = subprocess.run([sys.executable, script, "explain", "--identity", "github.example.invalid/synthetic-org/strict-release", "--operation", main_op, *verified], capture_output=True, text=True)
        malformed = subprocess.run([sys.executable, script, "check", "--identity", "basename-only", "--operation", main_op], capture_output=True, text=True)
        self.assertEqual((1, 1, 1, 0, 2), (allow_policy.returncode, deny.returncode, unknown.returncode, explain_deny.returncode, malformed.returncode))
        self.assertEqual("unknown", json.loads(allow_policy.stdout)["decision"]["final"])

    def test_generated_manifest_requires_exact_source_and_configured_label(self):
        manifest = {
            "effective_policy_source": policy.POLICY.as_posix(),
            "effective_policy_sha256": policy.digest(self.approved),
            "effective_policy": self.approved,
            "effective_policy_evidence_state": "configured",
        }
        policy.validate_generated(manifest, self.approved)
        for key, value in [
            ("effective_policy_source", "other.json"),
            ("effective_policy_sha256", "0" * 64),
            ("effective_policy_evidence_state", "verified"),
        ]:
            changed = copy.deepcopy(manifest); changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                policy.validate_generated(changed, self.approved)

    def test_duplicate_json_key_rejects(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.json"
            path.write_text('{"schema_version":1,"schema_version":1}')
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                policy.read_json(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
