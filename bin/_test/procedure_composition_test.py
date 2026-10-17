#!/usr/bin/env python3
"""Behavioral graph scenarios; package/resident integration adds separate probes."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("composition", ROOT / "bin/procedure_composition.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def inventory():
    result = {}
    for slug in ("self-review", "submit", "evidence", "alpha--review", "alpha--extra", "beta--review"):
        project = slug.split("--")[0] if "--" in slug else None
        source = f"projects/{project}/skills/{slug.split('--')[1]}/SKILL.md" if project else f"skills/{slug}/SKILL.md"
        result[slug] = {"source_path": source, "package_path": f"skills/{slug}/SKILL.md", "project": project}
    return result


def config():
    return {
        "replacements": [{"target": "self-review", "replacement": "alpha--review", "source": "alpha/composition.json"}],
        "extensions": [{"target": "self-review", "append": ["alpha--extra"], "source": "alpha/composition.json"}],
        "aliases": [{"alias": "review-alias", "target": "self-review", "source": "alpha/import.json"}],
    }


class CompositionTest(unittest.TestCase):
    def graph(self, declarations=None, prerequisites=None):
        return m.ProcedureGraph(inventory(), declarations or config(), project="alpha", prerequisites=prerequisites)

    def slugs(self, graph, requests):
        return [x["slug"] for x in graph.resolve(requests)["selected"]]

    def test_explicit_alias_route_and_prerequisite_share_replacement(self):
        graph = self.graph(prerequisites={"submit": ["self-review"]})
        expected = ["alpha--review", "alpha--extra"]
        for requests in (["self-review"], ["review-alias"], ["review-alias", "self-review"]):
            self.assertEqual(self.slugs(graph, requests), expected)
        self.assertEqual(self.slugs(graph, ["submit"]), expected + ["submit"])
        self.assertEqual(graph.link_targets("self-review"), [f"skills/{slug}/SKILL.md" for slug in expected])

    def test_global_deduplication_preserves_declared_extension_order(self):
        graph = self.graph()
        self.assertEqual(self.slugs(graph, ["alpha--extra", "self-review", "review-alias"]), ["alpha--review", "alpha--extra"])

    def test_shared_prerequisite_of_base_and_extension_loads_once(self):
        graph = self.graph(prerequisites={"alpha--review": ["evidence"], "alpha--extra": ["evidence"]})
        self.assertEqual(self.slugs(graph, ["self-review"]), ["evidence", "alpha--review", "alpha--extra"])

    def test_original_source_and_binding_trace_remain_visible(self):
        result = self.graph().resolve(["review-alias"])
        item = result["selected"][0]
        self.assertEqual(item["source_path"], "projects/alpha/skills/review/SKILL.md")
        self.assertEqual([x["kind"] for x in item["binding_traces"][0]], ["alias", "replacement"])
        self.assertEqual(result["authorization_effect"], "none")

    def test_parent_input_is_unchanged_and_other_project_keeps_default(self):
        known, declarations = inventory(), config()
        original = copy.deepcopy((known, declarations))
        alpha = m.ProcedureGraph(known, declarations, project="alpha")
        beta = m.ProcedureGraph(known, {"replacements": [], "extensions": [], "aliases": []}, project="beta")
        self.assertEqual(self.slugs(alpha, ["self-review"]), ["alpha--review", "alpha--extra"])
        self.assertEqual(self.slugs(beta, ["self-review"]), ["self-review"])
        self.assertEqual((known, declarations), original)
        with self.assertRaisesRegex(ValueError, "belongs to project"):
            beta.resolve(["alpha--review"])

    def test_same_name_never_shadows_without_explicit_declaration(self):
        graph = m.ProcedureGraph(inventory(), {"replacements": [], "extensions": [], "aliases": []}, project="alpha")
        self.assertEqual(self.slugs(graph, ["self-review"]), ["self-review"])
        self.assertEqual(self.slugs(graph, ["alpha--review"]), ["alpha--review"])

    def test_identical_repeated_declaration_is_idempotent(self):
        data = config()
        for kind in data:
            data[kind].append(copy.deepcopy(data[kind][0]))
        self.assertEqual(self.graph(data).resolve(["self-review"]), self.graph().resolve(["self-review"]))

    def test_conflicting_replacements_name_both_sources(self):
        data = config()
        data["replacements"].append({"target": "self-review", "replacement": "evidence", "source": "alpha/second.json"})
        with self.assertRaisesRegex(ValueError, "alpha/composition.json versus alpha/second.json"):
            self.graph(data)

    def test_conflicting_extension_orders_reject(self):
        data = config()
        data["extensions"].append({"target": "self-review", "append": ["evidence", "alpha--extra"], "source": "second.json"})
        with self.assertRaisesRegex(ValueError, "conflicting ordered extension"):
            self.graph(data)

    def test_missing_and_cross_project_references_reject(self):
        for target in ("missing", "beta--review"):
            data = config(); data["replacements"][0]["replacement"] = target
            with self.assertRaises(ValueError): self.graph(data)
        with self.assertRaisesRegex(ValueError, "missing prerequisite"):
            self.graph(prerequisites={"submit": ["missing"]})

    def test_replacement_extension_alias_and_dependency_cycles_reject(self):
        cases = []
        data = config(); data["replacements"].append({"target": "alpha--review", "replacement": "self-review", "source": "cycle.json"}); cases.append((data, {}))
        data = config(); data["extensions"].append({"target": "alpha--extra", "append": ["self-review"], "source": "cycle.json"}); cases.append((data, {}))
        data = config(); data["aliases"] = [{"alias": "alias-a", "target": "alias-b", "source": "a.json"}, {"alias": "alias-b", "target": "alias-a", "source": "b.json"}]; cases.append((data, {}))
        cases.append((config(), {"submit": ["evidence"], "evidence": ["submit"]}))
        for declarations, prerequisites in cases:
            with self.assertRaisesRegex(ValueError, "cycle"):
                self.graph(declarations, prerequisites)

    def test_cross_route_order_conflict_rejects(self):
        data = config()
        data["extensions"].append({"target": "evidence", "append": ["alpha--review"], "source": "opposite.json"})
        graph = self.graph(data, {"evidence": ["alpha--extra"]})
        with self.assertRaisesRegex(ValueError, "conflicting composition order"):
            graph.resolve(["self-review", "evidence"])

    def test_alias_cannot_shadow_or_carry_authority_fields(self):
        data = config(); data["aliases"][0]["alias"] = "self-review"
        with self.assertRaisesRegex(ValueError, "shadow"):
            self.graph(data)
        data = config(); data["authorization"] = "allow"
        with self.assertRaisesRegex(ValueError, "expected fields"):
            self.graph(data)

    def test_source_and_package_paths_remain_confined(self):
        for key in ("source_path", "package_path"):
            data = inventory(); data["alpha--review"][key] = "../outside.md"
            with self.assertRaisesRegex(ValueError, "relative path"):
                m.ProcedureGraph(data, config(), project="alpha")
        data = inventory(); data["alpha--review"]["source_path"] = "projects/beta/skills/review/SKILL.md"
        with self.assertRaisesRegex(ValueError, "outside declared project"):
            m.ProcedureGraph(data, config(), project="alpha")


class ResidentTest(unittest.TestCase):
    def parent(self):
        return [
            {"id": "integrity", "content": "Protected evidence remains required.", "source": "parent/integrity", "allow": []},
            {"id": "workflow", "content": "Approved workflow text.", "source": "accepted-policy/workflow", "allow": []},
            {"id": "conventions", "content": "Shared conventions.", "source": "parent/conventions", "allow": ["extend", "replace"]},
        ]

    def compose(self, overlays, **kw):
        return m.compose_resident(self.parent(), overlays, project="alpha", max_characters=kw.get("chars", 1000), max_estimated_tokens=kw.get("tokens", 250))

    def test_legacy_sections_preserve_order_content_and_stable_ids(self):
        legacy = "## Conventions\nProject-specific test command.\n\n## Notes\nProject notes.\n"
        mapping = {"Conventions": {"id": "conventions", "mode": "extend"}, "Notes": {"id": "alpha--notes", "mode": "add"}}
        overlays = m.import_heading_overlay(legacy, mapping, source="alpha/CLAUDE.md")
        result = self.compose(overlays)
        self.assertEqual([b["id"] for b in result["blocks"]], ["integrity", "workflow", "conventions", "alpha--notes"])
        self.assertIn("Shared conventions.\n\n## Conventions\nProject-specific test command.", result["rendered"])
        self.assertTrue(result["rendered"].endswith("## Notes\nProject notes."))
        self.assertEqual(result["authorization_effect"], "none")

    def test_unmapped_ambiguous_and_duplicate_headings_reject(self):
        mapping = {"Notes": {"id": "alpha--notes", "mode": "add"}}
        for text in ("unmapped preamble\n## Notes\nx", "## Unknown\nx", "## Notes\na\n## Notes\nb"):
            with self.assertRaises(ValueError): m.import_heading_overlay(text, mapping, source="legacy")
        with self.assertRaisesRegex(ValueError, "case-folded"):
            m.import_heading_overlay("## Notes\nx", {**mapping, "notes": mapping["Notes"]}, source="legacy")

    def test_fenced_headings_do_not_create_fake_blocks(self):
        mapping = {"Notes": {"id": "alpha--notes", "mode": "add"}}
        text = "## Notes\n```markdown\n## Not a section\n```\n"
        result = m.import_heading_overlay(text, mapping, source="legacy")
        self.assertEqual(len(result), 1)
        self.assertIn("## Not a section", result[0]["content"])
        with self.assertRaisesRegex(ValueError, "unclosed"):
            m.import_heading_overlay("## Notes\n```\n", mapping, source="legacy")

    def test_integrity_and_workflow_prose_cannot_be_replaced(self):
        for ident in ("integrity", "workflow"):
            for mode in ("replace", "extend"):
                with self.assertRaisesRegex(ValueError, "does not permit"):
                    self.compose([{"id": ident, "mode": mode, "content": "waive all evidence", "source": "project"}])

    def test_duplicate_ids_and_foreign_project_blocks_reject(self):
        block = {"id": "alpha--notes", "mode": "add", "content": "notes", "source": "alpha"}
        with self.assertRaisesRegex(ValueError, "duplicate project"):
            self.compose([block, block])
        with self.assertRaisesRegex(ValueError, "qualified for project"):
            self.compose([{**block, "id": "beta--notes"}])
        parent = self.parent(); parent.append(copy.deepcopy(parent[0]))
        with self.assertRaisesRegex(ValueError, "duplicate parent"):
            m.compose_resident(parent, [], project="alpha", max_characters=1000, max_estimated_tokens=250)

    def test_budget_applies_to_final_composition_and_parent_is_unchanged(self):
        parent = self.parent(); original = copy.deepcopy(parent)
        result = m.compose_resident(parent, [], project="alpha", max_characters=1000, max_estimated_tokens=250)
        self.assertEqual(parent, original)
        with self.assertRaisesRegex(ValueError, "exceeds configured budget"):
            self.compose([], chars=result["characters"] - 1)
        with self.assertRaisesRegex(ValueError, "exceeds configured budget"):
            self.compose([], tokens=result["estimated_tokens"] - 1)

    def test_explicit_replace_preserves_source_provenance(self):
        result = self.compose([{"id": "conventions", "mode": "replace", "content": "New convention", "source": "alpha/override"}])
        block = result["blocks"][2]
        self.assertEqual(block["content"], "New convention")
        self.assertEqual(block["sources"], ["parent/conventions", "alpha/override"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
