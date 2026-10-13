#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "bin" / "skill-lifecycle.py"
SPEC = importlib.util.spec_from_file_location("skill_lifecycle", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write(root: Path, rel: str, content: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def skill(name: str, metadata: str = "") -> str:
    return f"---\nname: {name}\ndescription: fixture\n{metadata}---\n\n# {name}\n"


def item(slug: str, path: str, kind: str = "skill", tier: str = "unclassified", owner=None, project=None):
    return {
        "slug": slug,
        "source_path": path,
        "kind": kind,
        "tier": tier,
        "owner": owner or ["unknown"],
        "project": project,
    }


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        (root / "bin").mkdir()
        shutil.copy2(ROOT / "bin" / "skill-inventory.py", root / "bin" / "skill-inventory.py")
        schema_path = root / "catalog" / "skill-lifecycle-schema.json"
        schema_path.parent.mkdir()
        shutil.copy2(ROOT / "catalog" / "skill-lifecycle-schema.json", schema_path)

        complete_meta = (
            "tier: on-demand\nowner: owner@example.test\nstatus: active\n"
            "last-reviewed: 2026-10-12\nverification: tests/complete.test.sh\n"
        )
        lifecycle_meta = "status: active\nlast-reviewed: 2026-10-12\nverification: tests/project.test.sh\n"
        deprecated_meta = (
            "tier: on-demand\nowner: owner@example.test\nstatus: deprecated\n"
            "last-reviewed: 2026-10-12\nverification: tests/deprecated.test.sh\n"
        )
        uppercase_meta = complete_meta.replace("status: active", "status: ACTIVE")
        project_conflict_meta = lifecycle_meta + "tier: kernel\n"

        sources = {
            "skills/complete/SKILL.md": skill("complete", complete_meta),
            "skills/legacy/SKILL.md": skill("legacy"),
            "skills/deprecated/SKILL.md": skill("deprecated", deprecated_meta),
            "skills/reference/SKILL.md": skill("reference", lifecycle_meta),
            "skills/uppercase/SKILL.md": skill("uppercase", uppercase_meta),
            "projects/demo/skills/reviewer/SKILL.md": skill("demo--reviewer", lifecycle_meta),
            "projects/demo/skills/conflict/SKILL.md": skill("demo--conflict", project_conflict_meta),
        }
        for path, content in sources.items():
            write(root, path, content)

        inventory = {
            "items": [
                item("complete", "skills/complete/SKILL.md"),
                item("legacy", "skills/legacy/SKILL.md"),
                item("deprecated", "skills/deprecated/SKILL.md"),
                item("reference", "skills/reference/SKILL.md", tier="reference", owner=["inferred@example.test"]),
                item("uppercase", "skills/uppercase/SKILL.md"),
                item(
                    "demo--reviewer", "projects/demo/skills/reviewer/SKILL.md",
                    kind="project-skill", tier="project", owner=["project-owner@example.test"], project="demo",
                ),
                item(
                    "demo--conflict", "projects/demo/skills/conflict/SKILL.md",
                    kind="project-skill", tier="project", owner=["project-owner@example.test"], project="demo",
                ),
            ]
        }
        inventory_path = root / "catalog" / "skills-inventory.json"
        dump(inventory_path, inventory)
        bootstrap_path = root / "catalog" / "skill-lifecycle-bootstrap.json"
        bootstrap_paths = sorted([
            "skills/legacy/SKILL.md",
            "skills/deprecated/SKILL.md",
            "skills/reference/SKILL.md",
            "skills/uppercase/SKILL.md",
            "projects/demo/skills/conflict/SKILL.md",
        ])
        dump(bootstrap_path, {"baseline_reference": "fixture", "source_paths": bootstrap_paths})
        approvals_path = root / "catalog" / "skill-lifecycle-approved-exceptions.json"
        dump(approvals_path, {"entries": []})
        completed_path = root / "catalog" / "skill-lifecycle-completed.json"
        dump(completed_path, {"entries": []})

        generated = MODULE.build_allowlist(
            root, inventory_path, schema_path, bootstrap_path, approvals_path, completed_path,
            verify_inventory=False, enforce_bootstrap_digest=False, allow_initial_bootstrap=True,
        )
        by_path = {entry["source_path"]: entry for entry in generated["entries"]}
        assert "skills/complete/SKILL.md" not in by_path
        assert "projects/demo/skills/reviewer/SKILL.md" not in by_path
        assert {"tier", "owner"}.issubset(by_path["skills/reference/SKILL.md"]["missing_fields"])
        assert "superseded-by" in by_path["skills/deprecated/SKILL.md"]["missing_fields"]
        assert "status:ACTIVE" in by_path["skills/uppercase/SKILL.md"]["invalid_fields"]
        assert "tier-conflict:kernel" in by_path["projects/demo/skills/conflict/SKILL.md"]["invalid_fields"]

        prior_gaps = {
            entry["source_path"]: {
                *(f"missing:{field}" for field in entry["missing_fields"]),
                *(f"invalid:{field}" for field in entry["invalid_fields"]),
            }
            for entry in generated["entries"]
        }
        write(root, "skills/reference/SKILL.md", skill("reference", lifecycle_meta.replace("status: active", "status: ACTIVE")))
        try:
            MODULE.build_allowlist(
                root, inventory_path, schema_path, bootstrap_path, approvals_path, completed_path,
                verify_inventory=False, enforce_bootstrap_digest=False,
                previous_gap_state=prior_gaps,
            )
        except ValueError as exc:
            assert "gap sets expanded" in str(exc)
        else:
            raise AssertionError("an existing exception gained an unapproved invalid field")
        write(root, "skills/reference/SKILL.md", skill("reference", lifecycle_meta))

        old = MODULE.serialize(generated)
        write(root, "skills/legacy/SKILL.md", skill("legacy", complete_meta))
        try:
            MODULE.build_allowlist(
                root, inventory_path, schema_path, bootstrap_path, approvals_path, completed_path,
                verify_inventory=False, enforce_bootstrap_digest=False, allow_initial_bootstrap=True,
            )
        except ValueError as exc:
            assert "must be recorded" in str(exc)
        else:
            raise AssertionError("bootstrap completion was removed without a monotonic record")
        dump(completed_path, {"entries": [{
            "source_path": "skills/legacy/SKILL.md",
            "completed_on": "2026-10-12",
            "completion_reference": "PR #122",
        }]})
        refreshed = MODULE.build_allowlist(
            root, inventory_path, schema_path, bootstrap_path, approvals_path, completed_path,
            verify_inventory=False, enforce_bootstrap_digest=False, allow_initial_bootstrap=True,
        )
        assert old != MODULE.serialize(refreshed)
        assert "skills/legacy/SKILL.md" not in {entry["source_path"] for entry in refreshed["entries"]}
        write(root, "skills/legacy/SKILL.md", skill("legacy"))
        try:
            MODULE.build_allowlist(
                root, inventory_path, schema_path, bootstrap_path, approvals_path, completed_path,
                verify_inventory=False, enforce_bootstrap_digest=False, allow_initial_bootstrap=True,
                previous_completed_paths={"skills/legacy/SKILL.md"},
            )
        except ValueError as exc:
            assert "metadata regressed" in str(exc)
        else:
            raise AssertionError("completed metadata regression re-entered bootstrap exceptions")
        write(root, "skills/legacy/SKILL.md", skill("legacy", complete_meta))
        dump(completed_path, {"entries": []})
        write(root, "skills/legacy/SKILL.md", skill("legacy"))
        try:
            MODULE.build_allowlist(
                root, inventory_path, schema_path, bootstrap_path, approvals_path, completed_path,
                verify_inventory=False, enforce_bootstrap_digest=False, allow_initial_bootstrap=True,
                previous_completed_paths={"skills/legacy/SKILL.md"},
            )
        except ValueError as exc:
            assert "append-only" in str(exc)
        else:
            raise AssertionError("completion record deletion reopened a bootstrap exception")
        dump(completed_path, {"entries": [{
            "source_path": "skills/legacy/SKILL.md",
            "completed_on": "2026-10-12",
            "completion_reference": "PR #122",
        }]})
        write(root, "skills/legacy/SKILL.md", skill("legacy", complete_meta))

        write(root, "skills/new/SKILL.md", skill("new"))
        inventory["items"].append(item("new", "skills/new/SKILL.md"))
        dump(inventory_path, inventory)
        try:
            MODULE.build_allowlist(
                root, inventory_path, schema_path, bootstrap_path, approvals_path, completed_path,
                verify_inventory=False, enforce_bootstrap_digest=False, allow_initial_bootstrap=True,
            )
        except ValueError as exc:
            assert "explicit approval records" in str(exc)
        else:
            raise AssertionError("new lifecycle gap could be admitted by regeneration")

        dump(approvals_path, {"entries": [{
            "source_path": "skills/new/SKILL.md",
            "reason": "fixture exception",
            "approval_reference": "PR #123",
            "approved_on": "2026-10-12",
        }]})
        approved = MODULE.build_allowlist(
            root, inventory_path, schema_path, bootstrap_path, approvals_path, completed_path,
            verify_inventory=False, enforce_bootstrap_digest=False, allow_initial_bootstrap=True,
        )
        assert any(entry["source_path"] == "skills/new/SKILL.md" for entry in approved["entries"])

        traversal_inventory = {"items": [item("escape", "../escape/SKILL.md")]}
        dump(inventory_path, traversal_inventory)
        try:
            MODULE.build_allowlist(
                root, inventory_path, schema_path, bootstrap_path, approvals_path, completed_path,
                verify_inventory=False, enforce_bootstrap_digest=False, allow_initial_bootstrap=True,
            )
        except ValueError as exc:
            assert "unsafe inventory source_path" in str(exc)
        else:
            raise AssertionError("path traversal was accepted")

    print("skill_lifecycle_test: PASS")


if __name__ == "__main__":
    main()
