#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import shutil
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
        cls.contract, cls.approved, cls.selection = policy.load_inputs(ROOT)

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
            self.contract, self.approved, self.selection,
            self.context(repository, capabilities=capabilities, identities=identities),
            operation or self.operation(), candidate,
        )

    def all_verified(self):
        return {item["id"]: "verified" for item in self.contract["capabilities"]}

    def test_catalog_valid_and_sealed_to_contract(self):
        self.assertEqual(policy.digest(self.contract), self.approved["contract_sha256"])
        self.assertEqual("f0b6ea8c428a9de089b09e2f79062cf57677140f", self.approved["parent_contract_revision"])

    def test_strict_feature_to_develop_policy_allows_but_enforcement_is_unproved(self):
        result = self.explain(capabilities=self.all_verified())
        self.assertEqual("allow", result["decision"]["policy"])
        self.assertEqual("unknown", result["decision"]["final"])
        self.assertIn("unauthenticated evaluator inputs", result["decision"]["reasons"][-1])
        self.assertEqual("develop", result["values"]["branch-policy"]["integration_branch"])
        self.assertEqual("github.com", result["approved_policy"]["parent_lock"]["host"])
        self.assertEqual(self.approved["contract_sha256"], result["approved_policy"]["parent_lock"]["digest"])

    def test_canonical_repository_uses_the_reviewed_strict_profile(self):
        identities = [{
            "source": "protected-target", "host": "github.com",
            "owner": "siege-analytics", "repository": "claude-configs-public",
        }]
        result = self.explain(identities=identities, capabilities=self.all_verified())
        self.assertEqual(("resolved", "claude-configs-public", "strict-release"),
                         (result["state"], result["project"], result["organization_profile"]))
        self.assertEqual(("allow", "unknown"),
                         (result["decision"]["policy"], result["decision"]["final"]))
        self.assertIn("targets `develop`", result["resident_workflow"])
        self.assertIn("Ticket evidence is required", result["resident_workflow"])

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

    def test_selected_snapshot_identifiers_and_review_are_explicit(self):
        self.assertEqual("ecef9e8620f477cdea4962cd3d737e16873f06fa", self.selection["policy_revision"])
        self.assertEqual("086e7bda8e9f588c57294ed0899f9ff2ffa982c5", self.selection["git_blob"])
        self.assertEqual("cf45e80b063d58501ca6dd297c4fcec3c99273507cef8dce7e566d3377a253ea", self.selection["raw_sha256"])
        result = self.explain(capabilities=self.all_verified())
        self.assertEqual(self.selection["policy_revision"], result["approved_policy"]["revision"])
        self.assertEqual(self.selection["review_evidence"], result["policy_selection"]["review_evidence"])

    def test_selection_tampering_and_missing_revision_reject(self):
        for key, value in (("policy_revision", "f" * 40), ("git_blob", "0" * 40), ("raw_sha256", "0" * 64), ("review_evidence", ["https://example.invalid/review"])):
            changed = copy.deepcopy(self.selection); changed[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "receipt digest"):
                policy.validate_selection(changed)
        with self.assertRaisesRegex(ValueError, "unavailable|not an ancestor"):
            policy.git_snapshot_bytes(ROOT, "f" * 40, policy.POLICY)

    def test_sealed_but_inconsistent_receipt_still_rejects(self):
        with tempfile.TemporaryDirectory() as temporary:
            clone = Path(temporary) / "repo"
            subprocess.run(["git", "clone", "--quiet", "--shared", str(ROOT), str(clone)], check=True)
            gc = policy._gate_contract_module()
            for key, value, diagnostic in (
                ("raw_sha256", "0" * 64, "raw-byte digest"),
                ("canonical_sha256", "0" * 64, "canonical digest"),
                ("git_blob", "0" * 40, "Git blob"),
            ):
                changed = copy.deepcopy(self.selection); changed[key] = value
                (clone / policy.SELECTION).write_text(json.dumps(changed))
                inputs = gc.siege_policy_inputs(ROOT)
                inputs["selection_sha256"] = policy.digest(changed)
                source = Path("test-policy-inputs.json")
                (clone / source).write_text(json.dumps(inputs))
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, diagnostic):
                    policy.load_registered_inputs(clone, registration_source=source,
                                                  registration_sha256=policy.digest(inputs))

    def test_dual_working_edit_cannot_replace_selected_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            clone = Path(temporary) / "repo"
            subprocess.run(["git", "clone", "--quiet", "--shared", str(ROOT), str(clone)], check=True)
            # The imported module may be the current working implementation;
            # supply its unchanged explicit compatibility registration too.
            gc = policy._gate_contract_module()
            registration = clone / gc.SIEGE_INPUTS
            registration.parent.mkdir(parents=True, exist_ok=True)
            registration.write_bytes((ROOT / gc.SIEGE_INPUTS).read_bytes())
            (clone / policy.SELECTION).write_bytes((ROOT / policy.SELECTION).read_bytes())
            working = json.loads((clone / policy.POLICY).read_text())
            working["organization_profiles"][0]["values"] = {"branch-policy": {"integration_branch": "main"}}
            (clone / policy.POLICY).write_text(json.dumps(working))
            fixture_path = clone / "examples/scaffolding/strict-release-policy.json"
            fixture = json.loads(fixture_path.read_text())
            fixture["values"]["branch-policy"]["integration_branch"] = "main"
            fixture["declared_overrides"].append({"field_id": "branch-policy", "path": "integration_branch", "layer": "organization-profile"})
            fixture_path.write_text(json.dumps(fixture))
            contract, approved, selection = policy.load_inputs(clone)
            result = policy.explain(contract, approved, selection, self.context(), self.operation(target_branch="main"), working)
            self.assertEqual("deny", result["decision"]["policy"])
            self.assertIn("`develop`", result["resident_workflow"])
            self.assertEqual("schema-valid-proposal", result["proposed_policy"]["state"])
            self.assertEqual("main", result["proposed_policy"]["changes"][0]["proposed"])

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
        result = policy.explain(self.contract, self.approved, self.selection, context, self.operation(target_branch="main"))
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
            "effective_policy_source": f"git:{self.selection['policy_revision']}:{self.selection['policy_path']}",
            "effective_policy_sha256": policy.digest(self.approved),
            "effective_policy": self.approved,
            "effective_policy_selection": self.selection,
            "effective_policy_evidence_state": "configured",
        }
        policy.validate_generated(manifest, self.approved, self.selection)
        for key, value in [
            ("effective_policy_source", "other.json"),
            ("effective_policy_sha256", "0" * 64),
            ("effective_policy_selection", {}),
            ("effective_policy_evidence_state", "verified"),
        ]:
            changed = copy.deepcopy(manifest); changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                policy.validate_generated(changed, self.approved, self.selection)

    def test_duplicate_json_key_rejects(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.json"
            path.write_text('{"schema_version":1,"schema_version":1}')
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                policy.read_json(path)


class RegisteredPolicyInputsTest(unittest.TestCase):
    """Independent input closure; this is not package/host independence proof."""

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True).strip()

    def write_json(self, relative, data):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + '\n')

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'Synthetic independent policy #1027')
        return self.git('rev-parse', 'HEAD')

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='registered-policy-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.git('init', '-q', '-b', 'trunk')
        self.git('config', 'core.hooksPath', '/dev/null')
        self.git('config', 'user.name', 'Policy fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        # Copy only the two actual engine modules and their bounded schema.
        # There is no bundles/, skills/, hooks/, examples/ or Siege catalog.
        for relative in ['bin/effective_policy.py', 'bin/gate_contract.py', 'catalog/gate-contract-schema.json']:
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
        self.contract = policy.read_json(ROOT / policy.CONTRACT)
        fields = {item['id']: item for item in self.contract['policy_fields']}
        fields['branch-policy']['value_schema']['properties']['integration_branch']['enum'] = ['trunk', 'release']
        fields['branch-policy']['default']['integration_branch'] = 'trunk'
        fields['ticket-requirement']['default']['required'] = False
        fields['review-procedure-binding']['default']['procedure'] = 'independent--review'
        self.targets = {}
        for field in fields.values():
            field['owner'] = 'project-profile'
            field['required_capability_ids'] = ['project-' + ident for ident in field['required_capability_ids']]
        for capability in self.contract['capabilities']:
            capability['id'] = 'project-' + capability['id']
            # Declarations deliberately do not pretend to be implemented host
            # adapters. Caller-supplied verified states still cannot authorize.
            capability['kind'] = 'declarative'
            capability['registered_path'] = 'project/requirements.md'
            if capability['id'] == 'project-procedure-binding-resolution':
                capability['registered_path'] = 'projects/independent/skills/review/SKILL.md'
            capability['package_paths'] = []
            self.targets[capability['id']] = {key: capability[key] for key in ('kind', 'registered_path', 'package_paths')}
        self.write_json('project/contract.json', self.contract)
        (self.root / 'project/requirements.md').write_text('Project adapter requirements, not observations.\n')
        review = self.root / 'projects/independent/skills/review/SKILL.md'
        review.parent.mkdir(parents=True)
        review.write_text('# Independent review\n\nReview the project changes.\n')
        revision = self.commit()
        self.approved = {
            'schema_version': 1, 'resolver_version': '1.0.0',
            'contract_source': 'project/contract.json', 'contract_sha256': policy.digest(self.contract),
            'parent_contract_revision': revision,
            'parent_lock': {'host': 'github.com', 'owner': 'independent-fixture', 'repository': 'policies',
                            'revision': revision, 'import_mechanism': 'git',
                            'digest': policy.digest(self.contract), 'tool_version': 'effective-policy/1'},
            'organization_profiles': [{'id': 'independent', 'values': {}}],
            'projects': [{'id': 'independent', 'repository_identity': {
                'host': 'github.example.invalid', 'owner': 'independent-org', 'repository': 'application'},
                'organization_profile': 'independent', 'values': {}}],
        }
        self.write_json('project/policy.json', self.approved)
        revision = self.commit()
        self.selection = {
            'schema_version': 1, 'policy_revision': revision, 'policy_path': 'project/policy.json',
            'git_blob': self.git('rev-parse', revision + ':project/policy.json'),
            'raw_sha256': hashlib.sha256((self.root / 'project/policy.json').read_bytes()).hexdigest(),
            'canonical_sha256': policy.digest(self.approved),
            'review_evidence': ['https://github.com/independent-fixture/policies/pull/1#pullrequestreview-1'],
        }
        self.write_json('project/selection.json', self.selection)
        self.inputs = {
            'schema_version': 1, 'selection_source': 'project/selection.json',
            'selection_sha256': policy.digest(self.selection), 'contract_source': 'project/contract.json',
            'review_repository': 'github.com/independent-fixture/policies',
            'capability_targets': self.targets, 'fixture_sources': [],
        }
        self.source = Path('project/policy-inputs.json')
        self.write_json(self.source, self.inputs)
        # The test host holds this independently of subsequent candidate writes.
        self.pin = policy.digest(self.inputs)

    def load(self):
        return policy.load_registered_inputs(self.root, registration_source=self.source, registration_sha256=self.pin)

    def explain(self, operation, candidate=None):
        loaded = self.load()
        context = policy.default_context('github.example.invalid/independent-org/application', [])
        context['capabilities'] = {ident: 'verified' for ident in self.targets}
        return policy.explain(loaded['contract'], loaded['policy'], loaded['selection'], context,
                              operation, candidate, selection_source=loaded['registration']['selection_source'])

    def test_independent_profile_loads_with_all_siege_inputs_absent(self):
        for relative in ['bundles', 'skills', 'hooks', 'examples', 'catalog/gate-contracts.json',
                         'catalog/effective-policy.json', 'catalog/effective-policy-selection.json']:
            self.assertFalse((self.root / relative).exists(), relative)
        # Run the copied engine itself, so a hidden import/read from this source
        # checkout cannot satisfy the independent source-closure assertion.
        code = ('import json,sys; from pathlib import Path; sys.path.insert(0,"bin"); '
                'import effective_policy as p; '
                'print(json.dumps(p.load_registered_inputs(Path.cwd(), '
                'registration_source=Path(sys.argv[1]),registration_sha256=sys.argv[2])))')
        result = subprocess.run([sys.executable, '-B', '-c', code, str(self.source), self.pin],
                                cwd=self.root, capture_output=True, text=True, check=True)
        loaded = json.loads(result.stdout)
        self.assertEqual((loaded['evidence_state'], loaded['authorization_effect']), ('configured', 'none'))
        self.assertEqual(loaded['registration']['contract_sha256'], policy.digest(self.contract))
        self.assertEqual(loaded['registration']['sha256'], self.pin)
        for operation, decision in [
            ({'type': 'feature-merge', 'target_branch': 'trunk'}, 'allow'),
            ({'type': 'feature-merge', 'target_branch': 'release'}, 'deny'),
            ({'type': 'ticket-commit', 'message': 'Project change without a ticket'}, 'allow'),
            ({'type': 'review-procedure'}, 'allow'),
        ]:
            with self.subTest(operation=operation):
                explained = self.explain(operation)
                self.assertEqual(explained['decision']['policy'], decision)
                self.assertEqual(explained['decision']['final'], 'deny' if decision == 'deny' else 'unknown')
                self.assertEqual(explained['policy_selection']['source'], 'project/selection.json')
                self.assertIn('independent--review', explained['resident_workflow'])

    def test_untrusted_replacement_registration_cannot_select_itself(self):
        changed = copy.deepcopy(self.approved)
        changed['organization_profiles'][0]['values'] = {'branch-policy': {'integration_branch': 'release'}}
        before = self.explain({'type': 'feature-merge', 'target_branch': 'release'}, changed)
        self.assertEqual(before['decision']['final'], 'deny')
        self.assertEqual(before['proposed_policy']['authorization_effect'], 'none')
        self.write_json('project/policy.json', changed)
        revision = self.commit()
        self.selection.update(policy_revision=revision, git_blob=self.git('rev-parse', revision + ':project/policy.json'),
                              raw_sha256=hashlib.sha256((self.root / 'project/policy.json').read_bytes()).hexdigest(),
                              canonical_sha256=policy.digest(changed))
        self.write_json('project/selection.json', self.selection)
        self.inputs['selection_sha256'] = policy.digest(self.selection)
        self.write_json(self.source, self.inputs)
        with self.assertRaisesRegex(ValueError, 'registration digest differs from independent pin'):
            self.load()

    def test_unselected_working_policy_is_ignored(self):
        changed = copy.deepcopy(self.approved)
        changed['organization_profiles'][0]['values'] = {'branch-policy': {'integration_branch': 'release'}}
        self.write_json('project/policy.json', changed)
        self.assertEqual(self.explain({'type': 'feature-merge', 'target_branch': 'release'})['decision']['final'], 'deny')
        self.assertEqual(self.load()['policy'], self.approved)

    def test_contract_tampering_cannot_follow_working_policy(self):
        self.contract['policy_fields'][1]['default']['required'] = True
        self.write_json('project/contract.json', self.contract)
        with self.assertRaisesRegex(ValueError, 'contract digest disagrees'):
            self.load()

    def test_selection_and_registration_tampering_reject(self):
        self.selection['review_evidence'] = ['https://github.com/independent-fixture/policies/pull/2#issuecomment-2']
        self.write_json('project/selection.json', self.selection)
        with self.assertRaisesRegex(ValueError, 'receipt digest differs'):
            self.load()
        self.inputs['fixture_sources'] = ['candidate-fixture.json']
        self.write_json(self.source, self.inputs)
        with self.assertRaisesRegex(ValueError, 'registration digest differs'):
            self.load()

    def test_missing_and_symlink_inputs_reject(self):
        for relative in [self.source, 'project/selection.json', 'project/contract.json']:
            with self.subTest(path=str(relative)):
                original = self.root / relative
                saved = original.with_suffix('.saved')
                original.rename(saved)
                with self.assertRaisesRegex(ValueError, 'path is missing'):
                    self.load()
                original.symlink_to(saved)
                with self.assertRaisesRegex(ValueError, 'symlink'):
                    self.load()
                original.unlink()
                saved.rename(original)

    def test_sealed_but_unsafe_or_unknown_inputs_reject(self):
        gc = policy._gate_contract_module()
        for field, value, diagnostic in [
            ('selection_source', '../outside.json', 'stay within repository'),
            ('contract_source', '/tmp/outside.json', 'stay within repository'),
            ('fixture_sources', ['project/../outside.json'], 'stay within repository'),
            ('review_repository', 'github.com/independent-fixture/policies.evil/extra', 'canonical GitHub'),
            ('review_repository', 'github.com/../..', 'canonical GitHub'),
            ('unexpected_authorization', True, 'fields differ'),
        ]:
            changed = copy.deepcopy(self.inputs); changed[field] = value
            self.write_json(self.source, changed)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, diagnostic):
                gc.load_policy_inputs(self.root, self.source, policy.digest(changed))

    def test_explicit_siege_selection_uses_same_loader_and_preserves_receipts(self):
        gc = policy._gate_contract_module()
        explicit = policy.load_registered_inputs(ROOT, registration_source=gc.SIEGE_INPUTS,
                                                 registration_sha256=gc.SIEGE_INPUTS_SHA256)
        legacy = policy.load_inputs(ROOT)
        self.assertEqual(tuple(explicit[key] for key in ('contract', 'policy', 'selection')), legacy)
        self.assertEqual(explicit['authorization_effect'], 'none')
        with self.assertRaisesRegex(ValueError, 'path is missing'):
            policy.load_inputs(self.root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
