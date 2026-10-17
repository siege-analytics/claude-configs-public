#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "bin" / "generated-source-authority.py"
SPEC = importlib.util.spec_from_file_location("generated_source_authority", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write(root: Path, rel: str, content: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def item(slug: str, source: str, nested: str, flat: str, kind: str = "skill") -> dict:
    return {
        "slug": slug,
        "kind": kind,
        "canonical_source": source,
        "generated_outputs": [nested, flat],
    }


def inventory(items: list[dict]) -> dict:
    return {
        "diagnostics": {
            "discovery_parity": {"source_count": len(items), "status": "matched"},
            "generated_output_plan": {"status": "derived-from-build.py"},
        },
        "items": items,
    }


def dump(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def copy_owned(root: Path, source_dir: str, destination: str, names: list[str]) -> None:
    for name in names:
        src = root / source_dir / name
        dst = root / destination / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        write(root, "skills/router/SKILL.md", "# router\n")
        write(root, "skills/router/guide.md", "router guide\n")
        write(root, "skills/router/child/SKILL.md", "# child\n")
        write(root, "skills/_safety-rules.md", "# safety\n")
        write(root, "skills/KERNEL.md", "kernel source\n")
        write(root, "skills/RULES.md", "rules entry\n")
        write(root, "skills/_coverage.md", "coverage source\n")
        items = [
            item("router", "skills/router/SKILL.md", "dist/nested/skills/router", "dist/flat/skills/router"),
            item("router--child", "skills/router/child/SKILL.md", "dist/nested/skills/router/child", "dist/flat/skills/router--child"),
            item("safety", "skills/_safety-rules.md", "dist/nested/skills/_safety-rules.md", "dist/flat/skills/_safety-rules.md", "rule"),
        ]
        inv = root / "catalog" / "skills-inventory.json"
        dump(inv, inventory(items))

        for form in ("nested", "flat"):
            parent = f"dist/{form}/skills/router"
            child = f"dist/{form}/skills/router/child" if form == "nested" else f"dist/{form}/skills/router--child"
            copy_owned(root, "skills/router", parent, ["SKILL.md", "guide.md"])
            copy_owned(root, "skills/router/child", child, ["SKILL.md"])
            write(root, f"dist/{form}/skills/_safety-rules.md", "# safety\n")
            write(root, f"dist/{form}/skills/KERNEL.md", "kernel output\n")
            write(root, f"dist/{form}/skills/RULES.md", "rules output\n")
            write(root, f"dist/{form}/skills/_coverage.md", "coverage output\n")
        for consumer in ("claude-code", "craft-agent"):
            shutil.copytree(root / "dist" / "flat" / "skills", root / "dist" / consumer / "skills")

        generated = MODULE.build_catalog(root, inv, root / "dist")
        assert generated["summary"] == {
            "canonical_source_count": 3,
            "support_source_count": 3,
            "source_owned_file_count": 7,
            "artifact_snapshot_count": 24,
            "generated_file_mapping_count": 28,
            "destination_collision_count": 0,
            "unowned_generated_file_count": 0,
        }
        by_source = {entry["canonical_source"]: entry for entry in generated["items"]}
        assert by_source["skills/router/SKILL.md"]["source_file_count"] == 2
        assert by_source["skills/router/child/SKILL.md"]["source_file_count"] == 1
        assert MODULE.serialize(generated) == MODULE.serialize(MODULE.build_catalog(root, inv, root / "dist"))

        # Fresh-build enforcement: an existing stale dist cannot be certified after
        # a source edit because build_fresh_catalog creates and hashes a new tree.
        write(root, "bin/skill-inventory.py", "raise SystemExit(0)\n")
        write(root, "bin/build.py", '''
import argparse, shutil
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument("--dist", required=True); a=p.parse_args()
r=Path(__file__).resolve().parents[1]; d=Path(a.dist)
for form in ("nested", "flat"):
    parent=d/form/"skills/router"; child=(parent/"child") if form=="nested" else d/form/"skills/router--child"
    parent.mkdir(parents=True, exist_ok=True); child.mkdir(parents=True, exist_ok=True)
    shutil.copy2(r/"skills/router/SKILL.md", parent/"SKILL.md")
    shutil.copy2(r/"skills/router/guide.md", parent/"guide.md")
    shutil.copy2(r/"skills/router/child/SKILL.md", child/"SKILL.md")
    shutil.copy2(r/"skills/_safety-rules.md", d/form/"skills/_safety-rules.md")
    (d/form/"skills/KERNEL.md").write_text("kernel output\\n")
    (d/form/"skills/RULES.md").write_text("rules output\\n")
    (d/form/"skills/_coverage.md").write_text("coverage output\\n")
for consumer in ("claude-code", "craft-agent"):
    shutil.copytree(d/"flat/skills", d/consumer/"skills")
''')
        fresh_before = MODULE.build_fresh_catalog(root, inv)
        write(root, "skills/router/guide.md", "changed current source\n")
        fresh_after = MODULE.build_fresh_catalog(root, inv)
        assert MODULE.serialize(fresh_before) != MODULE.serialize(fresh_after)
        assert (root / "dist/flat/skills/router/guide.md").read_text() == "router guide\n"
        write(root, "skills/router/guide.md", "router guide\n")

        external = root.parent / f"{root.name}-external.txt"
        external.write_text("outside\n")
        source_link = root / "skills/router/link.md"
        source_link.symlink_to(external)
        try:
            MODULE.build_catalog(root, inv, root / "dist")
        except ValueError as exc:
            assert "source contains a symlink" in str(exc)
        else:
            raise AssertionError("symlinked source member was accepted")
        source_link.unlink()

        output_link = root / "dist/craft-agent/skills/router/link.md"
        output_link.symlink_to(external)
        try:
            MODULE.build_catalog(root, inv, root / "dist")
        except ValueError as exc:
            assert "skills tree contains a symlink" in str(exc)
        else:
            raise AssertionError("symlinked generated member was accepted")
        output_link.unlink()
        external_dir = root.parent / f"{root.name}-external-dir"
        external_dir.mkdir()
        directory_link = root / "dist/craft-agent/skills/linked-dir"
        directory_link.symlink_to(external_dir, target_is_directory=True)
        try:
            MODULE.build_catalog(root, inv, root / "dist")
        except ValueError as exc:
            assert "skills tree contains a symlink" in str(exc)
        else:
            raise AssertionError("symlinked generated directory was accepted")
        directory_link.unlink()
        external_dir.rmdir()
        external.unlink()

        malformed = [dict(entry) for entry in items]
        malformed[0]["generated_outputs"] = ["other/nested/skills/router", "dist/flat/skills/router"]
        dump(inv, inventory(malformed))
        try:
            MODULE.build_catalog(root, inv, root / "dist")
        except ValueError as exc:
            assert "must be under dist/nested/skills" in str(exc)
        else:
            raise AssertionError("malformed generated destination was accepted")
        traversal = [dict(entry) for entry in items]
        traversal[0]["generated_outputs"] = [
            "dist/nested/skills/../../flat/skills/router",
            "dist/flat/skills/router",
        ]
        dump(inv, inventory(traversal))
        try:
            MODULE.build_catalog(root, inv, root / "dist")
        except ValueError as exc:
            assert "must be under dist/nested/skills" in str(exc)
        else:
            raise AssertionError("cross-layout traversal destination was accepted")
        dump(inv, inventory(items))

        craft_child = root / "dist/craft-agent/skills/router--child/SKILL.md"
        craft_child.write_text("manually drifted\n")
        drifted = MODULE.build_catalog(root, inv, root / "dist")
        assert MODULE.serialize(drifted) != MODULE.serialize(generated)
        craft_child.write_text("# child\n")

        missing = root / "dist/claude-code/skills/router/guide.md"
        missing.unlink()
        try:
            MODULE.build_catalog(root, inv, root / "dist")
        except ValueError as exc:
            assert "generated output is missing" in str(exc)
        else:
            raise AssertionError("missing generated output was accepted")
        write(root, "dist/claude-code/skills/router/guide.md", "router guide\n")

        write(root, "dist/craft-agent/skills/unowned.md", "manual artifact\n")
        try:
            MODULE.build_catalog(root, inv, root / "dist")
        except ValueError as exc:
            assert "lack canonical owners" in str(exc)
        else:
            raise AssertionError("unowned generated file was accepted")
        (root / "dist/craft-agent/skills/unowned.md").unlink()

        write(root, "skills/other/SKILL.md", "# other\n")
        collided = items + [item(
            "other", "skills/other/SKILL.md",
            "dist/nested/skills/router", "dist/flat/skills/router",
        )]
        dump(inv, inventory(collided))
        try:
            MODULE.build_catalog(root, inv, root / "dist")
        except ValueError as exc:
            assert "collision" in str(exc)
        else:
            raise AssertionError("generated output collision was accepted")

        bad = [item("escape", "../escape/SKILL.md", "dist/nested/skills/x", "dist/flat/skills/x")]
        dump(inv, inventory(bad))
        try:
            MODULE.build_catalog(root, inv, root / "dist")
        except ValueError as exc:
            assert "unsafe authority path" in str(exc)
        else:
            raise AssertionError("unsafe canonical source was accepted")

    print("generated_source_authority_test: PASS")


if __name__ == "__main__":
    main()
