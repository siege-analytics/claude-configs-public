#!/usr/bin/env python3
"""Negative and CLI acceptance tests for the shared terminology contract (#1007)."""
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
SPEC = importlib.util.spec_from_file_location("ontology", ROOT / "bin/ontology.py")
assert SPEC and SPEC.loader
ontology = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ontology)


class OntologyTest(unittest.TestCase):
    def setUp(self):
        self.registry = ontology.read_json(ROOT / ontology.REGISTRY)
        self.bindings = ontology.read_json(ROOT / ontology.BINDINGS)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write(ontology.REGISTRY, self.registry)
        self.write(ontology.BINDINGS, self.bindings)
        self.write("catalog/resolver-manifest.json", {
            "routes": [{"skills": ["code-review"]}],
            "projects": [{"repos": ["github.com/example/project"], "routes": [{"skills": ["project--review"]}]}],
        })
        contract = ontology.read_json(ROOT / "catalog/gate-contracts.json")
        effective_policy = ontology.read_json(ROOT / "catalog/effective-policy.json")
        effective_selection = ontology.read_json(ROOT / "catalog/effective-policy-selection.json")
        self.write("catalog/gate-contracts.json", contract)
        self.write("catalog/effective-policy.json", effective_policy)
        self.write("catalog/effective-policy-selection.json", effective_selection)
        self.write("examples/scaffolding/strict-release-policy.json", ontology.read_json(ROOT / "examples/scaffolding/strict-release-policy.json"))
        self.write("examples/scaffolding/synthetic-trunk-policy.json", ontology.read_json(ROOT / "examples/scaffolding/synthetic-trunk-policy.json"))
        self.write("dist/craft-agent/enforcement-manifest.json", {
            "gates": [{"id": "ticket", "runtime_policy": {"craft": "advisory"}, "blocking": True}],
            "gate_contract": contract,
            "effective_policy": effective_policy,
            "effective_policy_selection": effective_selection,
            "effective_policy_evidence_state": "configured",
        })

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "bin/ontology.py"), "--root", str(self.root), *args], text=True, capture_output=True)

    def test_real_registry_and_existing_artifact_bindings(self):
        terms = ontology.validate_registry(self.registry)
        self.assertNotEqual(terms["host-capability"], terms["procedure-binding"])
        self.assertEqual(ontology.validate_bindings(self.bindings, self.registry, self.root), 51)

    def test_duplicate_ids_labels_and_json_keys_reject(self):
        for field in ("id", "label"):
            with self.subTest(field=field):
                registry = copy.deepcopy(self.registry)
                registry["terms"][1][field] = registry["terms"][0][field]
                with self.assertRaisesRegex(ValueError, "duplicate|collision"):
                    ontology.validate_registry(registry)
        path = self.root / "duplicate.json"
        path.write_text('{"term":"skill","term":"policy"}')
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            ontology.read_json(path)

    def test_unknown_fields_types_and_versions_reject(self):
        for key, value in (("unexpected", True), ("schema_version", True), ("ontology_version", "latest"), ("terms", []), ("terms", None)):
            with self.subTest(key=key, value=value):
                registry = copy.deepcopy(self.registry)
                registry[key] = value
                with self.assertRaises(ValueError):
                    ontology.validate_registry(registry)
        self.bindings["ontology_version"] = "2.0.0"
        with self.assertRaisesRegex(ValueError, "ontology_version differs"):
            ontology.validate_bindings(self.bindings, self.registry, self.root)

    def test_alias_collision_and_ambiguous_single_target_reject(self):
        for alias in (
            {"name": "HOST CAPABILITY", "status": "deprecated", "targets": ["skill"]},
            {"name": "ambiguous-example", "status": "ambiguous", "targets": ["skill"]},
            {"name": "old-example", "status": "deprecated", "targets": ["skill", "policy"]},
            {"name": "missing-example", "status": "deprecated", "targets": ["absent"]},
        ):
            with self.subTest(alias=alias):
                registry = copy.deepcopy(self.registry)
                registry["aliases"].append(alias)
                with self.assertRaises(ValueError):
                    ontology.validate_registry(registry)

    def test_dangling_and_duplicate_relationships_reject(self):
        for field in ("subject", "object"):
            registry = copy.deepcopy(self.registry)
            registry["relationships"][0][field] = "absent"
            with self.assertRaisesRegex(ValueError, "unknown"):
                ontology.validate_registry(registry)
        self.registry["relationships"].append(copy.deepcopy(self.registry["relationships"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate relationship"):
            ontology.validate_registry(self.registry)

    def test_configuration_and_replacement_cannot_create_authorization(self):
        for subject in ("skill-replacement", "configured", "policy-override", "procedure-binding"):
            for verb in ("authorizes", "creates", "grants", "permits", "binds", "invented-verb"):
                for target in ("authorization-record", "authorization-scope"):
                    with self.subTest(subject=subject, verb=verb, target=target):
                        registry = copy.deepcopy(self.registry)
                        registry["relationships"].append({
                            "id": "invalid-authority-edge", "subject": subject,
                            "verb": verb, "object": target, "definition": "Invalid authority claim.",
                        })
                        with self.assertRaisesRegex(ValueError, "unsupported authority relationship"):
                            ontology.validate_registry(registry)

    def test_authority_relationships_require_exact_approved_signature(self):
        for subject, verb, target in (
            ("authorization-record", "creates", "authorization-scope"),
            ("authorization-scope", "binds", "authorization-record"),
            ("authorization-record", "authorizes", "skill"),
            ("authorization-record", "creates", "authorization-record"),
        ):
            with self.subTest(subject=subject, verb=verb, target=target):
                registry = copy.deepcopy(self.registry)
                registry["relationships"].append({
                    "id": "invalid-authority-edge", "subject": subject,
                    "verb": verb, "object": target, "definition": "Invalid authority claim.",
                })
                with self.assertRaisesRegex(ValueError, "unsupported authority relationship"):
                    ontology.validate_registry(registry)
        # The existing record-to-scope binding remains a valid vocabulary relationship.
        self.assertIn("authorization-record", ontology.validate_registry(self.registry))

    def test_maintenance_owner_cannot_grant_or_remove_authority_qualification(self):
        for changed_term, owner in (("skill-replacement", "authority"), ("authorization-record", "composition")):
            with self.subTest(changed_term=changed_term):
                registry = copy.deepcopy(self.registry)
                next(term for term in registry["terms"] if term["id"] == changed_term)["owner"] = owner
                registry["relationships"].append({
                    "id": "invalid-owner-edge", "subject": "skill-replacement",
                    "verb": "binds", "object": "authorization-record", "definition": "Invalid owner qualification.",
                })
                with self.assertRaisesRegex(ValueError, "unsupported authority relationship"):
                    ontology.validate_registry(registry)

    def test_new_authority_owned_term_does_not_bypass_boundary(self):
        term = copy.deepcopy(next(term for term in self.registry["terms"] if term["id"] == "authorization-record"))
        term.update(id="additional-approval", label="Additional approval", owner="Authority")
        self.registry["terms"].append(term)
        self.registry["relationships"].append({
            "id": "invalid-new-target", "subject": "configured", "verb": "creates",
            "object": "additional-approval", "definition": "Invalid authority claim under another term ID.",
        })
        with self.assertRaisesRegex(ValueError, "unsupported authority relationship"):
            ontology.validate_registry(self.registry)

    def test_required_authority_terms_and_relationship_cannot_be_removed(self):
        registry = copy.deepcopy(self.registry)
        registry["terms"] = [term for term in registry["terms"] if term["id"] != "authorization-record"]
        with self.assertRaisesRegex(ValueError, "missing required authority terms"):
            ontology.validate_registry(registry)
        self.registry["relationships"] = [edge for edge in self.registry["relationships"] if edge["id"] != "authorization-binds-scope"]
        with self.assertRaisesRegex(ValueError, "missing required authority relationship"):
            ontology.validate_registry(self.registry)

    def test_non_authority_relationships_remain_extensible(self):
        self.registry["relationships"].append({
            "id": "project-documents-skill", "subject": "project", "verb": "documents",
            "object": "skill", "definition": "A project documents a procedure it uses.",
        })
        self.assertEqual(len(ontology.validate_registry(self.registry)), len(self.registry["terms"]))

    def test_cli_rejects_authority_claim_without_rewriting_wiki(self):
        self.assertEqual(self.cli("--write").returncode, 0)
        wiki = self.root / ontology.WIKI
        before = wiki.read_bytes()
        self.registry["relationships"].append({
            "id": "invalid-cli-authority", "subject": "configured", "verb": "creates",
            "object": "authorization-record", "definition": "Invalid authority claim.",
        })
        self.write(ontology.REGISTRY, self.registry)
        for mode in ("--check", "--write"):
            with self.subTest(mode=mode):
                result = self.cli(mode)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("unsupported authority relationship", result.stderr)
                self.assertEqual(wiki.read_bytes(), before)

    def test_distinction_cannot_reference_missing_or_same_term(self):
        for target in ("absent", self.registry["terms"][0]["id"]):
            registry = copy.deepcopy(self.registry)
            registry["terms"][0]["distinguished_from"] = [target]
            with self.assertRaisesRegex(ValueError, "invalid distinguished_from"):
                ontology.validate_registry(registry)

    def test_structured_references_require_canonical_ids(self):
        for term in ("capability", "verified", "override", "enforcement-live", "native-shadow", "Host Capability", "absent"):
            with self.subTest(term=term):
                binding = copy.deepcopy(self.bindings)
                binding["bindings"][0]["fields"][0]["term"] = term
                with self.assertRaisesRegex(ValueError, "canonical"):
                    ontology.validate_bindings(binding, self.registry, self.root)

    def test_renamed_field_and_incomplete_wildcard_branch_fail(self):
        path = self.root / "catalog/resolver-manifest.json"
        data = ontology.read_json(path)
        data["projects"].append({"repos": ["github.com/other/project"], "routes": [{"procedures": ["review"]}]})
        self.write("catalog/resolver-manifest.json", data)
        with self.assertRaisesRegex(ValueError, "missing or empty bound field"):
            ontology.validate_bindings(self.bindings, self.registry, self.root)

    def test_empty_bound_collection_and_wrong_json_type_reject(self):
        for gates in ([], [{"runtime_policy": {"craft": "block"}, "blocking": "true"}]):
            self.write("dist/craft-agent/enforcement-manifest.json", {"gates": gates})
            with self.assertRaises(ValueError):
                ontology.validate_bindings(self.bindings, self.registry, self.root)

    def test_missing_artifact_does_not_skip_successfully(self):
        (self.root / "dist/craft-agent/enforcement-manifest.json").unlink()
        result = self.cli("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ONTOLOGY ERROR", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_duplicate_bindings_and_unknown_value_type_reject(self):
        self.bindings["bindings"].append(copy.deepcopy(self.bindings["bindings"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate artifact binding"):
            ontology.validate_bindings(self.bindings, self.registry, self.root)
        self.bindings["bindings"].pop()
        fields = self.bindings["bindings"][0]["fields"]
        fields.append(copy.deepcopy(fields[0]))
        with self.assertRaisesRegex(ValueError, "duplicate field binding"):
            ontology.validate_bindings(self.bindings, self.registry, self.root)
        fields.pop()
        fields[0]["value_type"] = "anything"
        with self.assertRaisesRegex(ValueError, "unknown value_type"):
            ontology.validate_bindings(self.bindings, self.registry, self.root)

    def test_artifact_paths_cannot_escape_checkout(self):
        outside = self.root.parent / "outside.json"
        for path in (str(outside), "../outside.json"):
            with self.assertRaisesRegex(ValueError, "within the repository"):
                ontology.repository_path(self.root, path)
        (self.root / "escape").symlink_to(self.root.parent, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "escapes the repository"):
            ontology.repository_path(self.root, "escape/outside.json")

    def test_pointer_escaping_and_array_index(self):
        self.assertEqual(ontology.pointer_values({"a/b": {"~key": [1]}}, "/a~1b/~0key/0"), [1])
        for pointer in ("not-a-pointer", "/~2", "/a~1b/~0key/01", "/a~1b/~0key/2"):
            with self.assertRaises(ValueError):
                ontology.pointer_values({"a/b": {"~key": [1]}}, pointer)

    def test_write_cannot_follow_internal_symlink_over_unrelated_work(self):
        victim = self.root / "unrelated.md"
        victim.write_text("preserve this work\n")
        wiki = self.root / ontology.WIKI
        wiki.parent.mkdir()
        wiki.symlink_to(victim)
        result = self.cli("--write")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", result.stderr)
        self.assertEqual(victim.read_text(), "preserve this work\n")

    def test_generated_wiki_detects_edit_and_check_never_rewrites(self):
        result = self.cli("--write")
        self.assertEqual(result.returncode, 0, result.stderr)
        path = self.root / ontology.WIKI
        original = path.read_bytes()
        self.assertEqual(self.cli("--check").returncode, 0)
        self.assertEqual(self.cli("--write").returncode, 0)
        self.assertEqual(path.read_bytes(), original)
        path.write_text(path.read_text() + "unreviewed manual definition\n")
        changed = path.read_bytes()
        result = self.cli("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stale or missing", result.stderr)
        self.assertEqual(path.read_bytes(), changed)

    def test_definition_change_invalidates_generated_wiki(self):
        self.assertEqual(self.cli("--write").returncode, 0)
        self.registry["terms"][0]["definition"] += " Clarified meaning."
        self.write(ontology.REGISTRY, self.registry)
        self.assertNotEqual(self.cli("--check").returncode, 0)

    def test_additional_bindings_checked_without_wiki_generation(self):
        result = self.cli("--validate-bindings", ontology.BINDINGS)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / ontology.WIKI).exists())

    def test_explain_and_prose_lint_preserve_advisory_boundary(self):
        result = self.cli("--explain", "host-capability")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["id"], "host-capability")
        self.assertNotEqual(self.cli("--explain", "capability").returncode, 0)
        prose = self.root / "design.md"
        prose.write_text("host capability and procedure binding\ncapability is verified\n")
        result = self.cli("--lint", "design.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("design.md:1:", result.stdout)
        self.assertIn("design.md:2: ambiguous 'capability'", result.stdout)
        self.assertIn("design.md:2: ambiguous 'verified'", result.stdout)


if __name__ == "__main__":
    unittest.main()
