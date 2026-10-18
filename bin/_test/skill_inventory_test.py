#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "bin" / "skill-inventory.py"
SPEC = importlib.util.spec_from_file_location("skill_inventory", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write(root: Path, rel: str, content: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def skill(name: str, body: str = "") -> str:
    return f"---\nname: {name}\ndescription: fixture {name}\n---\n\n# {name}\n{body}\n"


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        fallback_root = Path(td)
        write(fallback_root, "untracked.txt", "fallback\n")
        assert MODULE.tracked_files(fallback_root) == [fallback_root / "untracked.txt"]
        malformed = fallback_root / "malformed.md"
        malformed.write_bytes(b"\xff")
        assert MODULE.read_text(malformed) == ""

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write(root, "skills/alpha/SKILL.md", skill("alpha"))
        write(root, "skills/router/SKILL.md", skill("router"))
        write(root, "skills/router/child/SKILL.md", skill("child"))
        write(root, "skills/shelves/SKILL.md", skill("shelves"))
        write(root, "skills/shelves/topic/SKILL.md", skill("topic"))
        write(root, "skills/shelves/topic/book/SKILL.md", skill("book"))
        write(root, "skills/_writing-rules-rules.md", "# Rules\n**writing-rules:1. first**\n")
        write(root, "skills/_claims-rules.md", "# Claims\nwriting-rules:1. duplicate\n")
        write(root, "skills/_alpha-rules.md", "# Alpha rule\n")
        write(root, "skills/generated--copy/SKILL.md", skill("generated-copy"))
        write(root, "skills/nested/_hidden-rules.md", "# Unsupported nested rule\n")
        write(
            root,
            "projects/demo/PROJECT.md",
            "---\nname: demo\ndescription: demo\nrepo: org/demo\nowners:\n  - owner@example.test\n---\n",
        )
        write(root, "projects/demo/skills/reviewer/SKILL.md", skill("demo--reviewer"))
        write(root, "projects/demo/_rules.md", "# Demo rules\n")
        write(
            root,
            "projects/old/PROJECT.md",
            "---\nname: old\ndescription: archived fixture\nrepo: org/old\nowners:\n  - old@example.test\nstatus: archived\n---\n",
        )
        write(root, "projects/old/skills/legacy/SKILL.md", skill("old--legacy"))
        write(root, "docs/consumer.md", "Use [skill:alpha], [rule:alpha], and [rule:writing-rules].\n")
        (root / "bin").mkdir(exist_ok=True)
        shutil.copy2(ROOT / "bin" / "build.py", root / "bin" / "build.py")
        write(root, "hooks/_test/alpha.test.sh", "# alpha behavior\n")
        subprocess.run(["git", "init", "-q", str(root)], check=True, timeout=30)
        subprocess.run(["git", "-C", str(root), "add", "."], check=True, timeout=30)

        inventory = MODULE.build_inventory(root)
        by_key = {(item["kind"], item["slug"]): item for item in inventory["items"]}

        assert inventory["summary"]["item_count"] == 11, inventory["summary"]
        assert by_key[("skill-router", "router")]["kind"] == "skill-router"
        assert by_key[("shelf-router", "shelves--topic")]["kind"] == "shelf-router"
        assert by_key[("reference-shelf", "shelves--book")]["tier"] == "reference"
        assert by_key[("project-skill", "demo--reviewer")]["tier"] == "project"
        assert by_key[("project-skill", "demo--reviewer")]["owner"] == ["owner@example.test"]
        assert by_key[("skill", "alpha")]["inbound_source_references"] == ["docs/consumer.md"]
        assert by_key[("rule", "alpha")]["inbound_source_references"] == ["docs/consumer.md"]
        assert by_key[("skill", "alpha")]["test_evidence"] == ["hooks/_test/alpha.test.sh"]
        assert by_key[("project-rule", "demo--rules")]["generated_outputs"] == [
            "dist/nested/skills/_demo--rules.md",
            "dist/flat/skills/_demo--rules.md",
        ]
        assert {entry["path"] for entry in inventory["diagnostics"]["ignored_sources"]} == {
            "projects/old/skills/legacy/SKILL.md",
            "skills/generated--copy/SKILL.md",
            "skills/nested/_hidden-rules.md",
        }
        assert inventory["diagnostics"]["discovery_parity"]["status"] == "matched"
        assert inventory["diagnostics"]["generated_output_plan"]["status"] == "derived-from-build.py"
        assert inventory["diagnostics"]["duplicate_rule_ids"] == {
            "writing-rules:1": ["skills/_claims-rules.md", "skills/_writing-rules-rules.md"]
        }
        first = MODULE.serialized(inventory)
        second = MODULE.serialized(MODULE.build_inventory(root))
        assert first == second, "inventory output is not deterministic"

        generate = [sys.executable, str(SCRIPT), "--root", str(root)]
        assert subprocess.run(generate, capture_output=True, text=True, timeout=30).returncode == 0
        json_path = root / "catalog" / "skills-inventory.json"
        report_path = root / "catalog" / "skills-inventory.md"
        subprocess.run(["git", "-C", str(root), "add", "catalog"], check=True, timeout=30)
        check = [*generate, "--check"]
        assert subprocess.run(check, capture_output=True, text=True, timeout=30).returncode == 0
        tracked_catalog = __import__("json").loads(json_path.read_text())
        assert all(
            not any(ref.startswith("catalog/skills-inventory") for ref in item["inbound_source_references"])
            for item in tracked_catalog["items"]
        ), "generated catalog supplied its own source-reference evidence"
        report_path.write_text("stale\n")
        stale = subprocess.run(check, capture_output=True, text=True, timeout=30)
        assert stale.returncode == 1
        assert "STALE skill inventory outputs" in stale.stderr

    try:
        MODULE.validate_output_collisions({
            "skills/one/SKILL.md": ["dist/flat/skills/shared"],
            "projects/demo/skills/shared/SKILL.md": ["dist/flat/skills/shared"],
        })
    except ValueError as exc:
        assert "generated output collision" in str(exc)
    else:
        raise AssertionError("duplicate generated destinations were marked verified")

    with tempfile.TemporaryDirectory() as td:
        collision = Path(td)
        write(collision, "skills/shelves/a/book/SKILL.md", skill("book-a"))
        write(collision, "skills/shelves/b/book/SKILL.md", skill("book-b"))
        try:
            MODULE.source_items(collision)
        except ValueError as exc:
            assert "duplicate general skill slug shelves--book" in str(exc)
        else:
            raise AssertionError("same-named books in different shelves silently collapsed")

    assert MODULE._yaml_scalar('"# pending"') == "# pending"
    assert MODULE._yaml_scalar("real name # operator note") == "real name"
    assert MODULE._yaml_scalar("'null'") == "null"

    invalid_fixtures = {
        "skills/missing-all/SKILL.md": (
            "# Missing metadata\n",
            "skill frontmatter invalid in skills/missing-all/SKILL.md: missing frontmatter block",
        ),
        "projects/demo/skills/missing-description/SKILL.md": (
            "---\nname: demo--missing-description\n---\n\n# Missing description\n",
            "skill frontmatter invalid in projects/demo/skills/missing-description/SKILL.md: missing required description",
        ),
        "skills/quoted-whitespace/SKILL.md": (
            "---\nname: \"   \"\ndescription: whitespace name\n---\n\n# Whitespace name\n",
            "skill frontmatter invalid in skills/quoted-whitespace/SKILL.md: name must be a non-empty string, got blank",
        ),
        "skills/comment-name/SKILL.md": (
            "---\nname: # pending\ndescription: comment name\n---\n\n# Comment name\n",
            "skill frontmatter invalid in skills/comment-name/SKILL.md: name must be a non-empty string, got NoneType None",
        ),
        "skills/comment-description/SKILL.md": (
            "---\nname: comment-description\ndescription: # pending\n---\n\n# Comment description\n",
            "skill frontmatter invalid in skills/comment-description/SKILL.md: description must be a non-empty string, got NoneType None",
        ),
        "skills/null-name/SKILL.md": (
            "---\nname: null\ndescription: null name\n---\n\n# Null name\n",
            "skill frontmatter invalid in skills/null-name/SKILL.md: name must be a non-empty string, got NoneType None",
        ),
        "skills/tilde-description/SKILL.md": (
            "---\nname: tilde-description\ndescription: ~\n---\n\n# Tilde description\n",
            "skill frontmatter invalid in skills/tilde-description/SKILL.md: description must be a non-empty string, got NoneType None",
        ),
        # #1046: presence-only parsing accepted these; a real YAML parse must not.
        "skills/pipeline-jobs/SKILL.md": (
            "---\nname: pipeline-jobs\ndescription: Pipeline job pattern. TRIGGER: writing data pipeline scripts, "
            "Rundeck jobs, Airflow DAGs, or scheduled data processing. Python first, scheduler second.\n"
            "routed-by: coding-standards\n---\n\n# Pipeline Jobs\n",
            "skill frontmatter invalid in skills/pipeline-jobs/SKILL.md: invalid YAML: "
            "mapping values are not allowed here at line 3, column 43",
        ),
        "skills/_ticket-lifecycle-rules.md": (
            "---\ndescription: Always-on ticket lifecycle status discipline. Ticket state must move at the point "
            "of action: work start, PR open, test/UAT handoff, blocker, unblock/resume, merge/verified close. "
            "Platform-agnostic; requires a comment when a platform lacks a mutable Status field.\n---\n\n# Rule\n",
            "rule frontmatter invalid in skills/_ticket-lifecycle-rules.md: invalid YAML: "
            "mapping values are not allowed here at line 2, column 105",
        ),
        "skills/bool-description/SKILL.md": (
            "---\nname: bool-description\ndescription: false\n---\n\n# Bool\n",
            "skill frontmatter invalid in skills/bool-description/SKILL.md: description must be a non-empty string, got bool False",
        ),
        "skills/list-description/SKILL.md": (
            "---\nname: list-description\ndescription: [release]\n---\n\n# List\n",
            "skill frontmatter invalid in skills/list-description/SKILL.md: description must be a non-empty string, got list ['release']",
        ),
        "skills/unterminated/SKILL.md": (
            "---\nname: unterminated\ndescription: \"unterminated\n---\n\n# Unterminated\n",
            "skill frontmatter invalid in skills/unterminated/SKILL.md: invalid YAML: found unexpected end of stream at line 3, column 27",
        ),
        "projects/demo/skills/yes-name/SKILL.md": (
            "---\nname: yes\ndescription: lint\n---\n\n# Yes\n",
            "skill frontmatter invalid in projects/demo/skills/yes-name/SKILL.md: YAML 1.1/1.2 incompatible frontmatter: "
            "line 2: unquoted 'yes' resolves as bool under YAML 1.1 but str under YAML 1.2; quote it",
        ),
    }
    for rel, (content, expected) in invalid_fixtures.items():
        with tempfile.TemporaryDirectory() as td:
            invalid = Path(td)
            if rel.startswith("projects/"):
                write(
                    invalid,
                    "projects/demo/PROJECT.md",
                    "---\nname: demo\ndescription: demo\nrepo: org/demo\nstatus: active\n---\n",
                )
            write(invalid, rel, content)
            try:
                MODULE.source_items(invalid)
            except ValueError as exc:
                assert str(exc) == expected, exc
            else:
                raise AssertionError(f"invalid skill frontmatter was accepted: {rel}")

    # #1046: an undecodable rule must not pass as "no frontmatter".
    with tempfile.TemporaryDirectory() as td:
        undecodable = Path(td)
        (undecodable / "skills").mkdir()
        (undecodable / "skills" / "_bad-rules.md").write_bytes(b"---\ndescription: \xff\n---\n")
        try:
            MODULE.source_items(undecodable)
        except ValueError as exc:
            assert str(exc).startswith("rule frontmatter unreadable in skills/_bad-rules.md: "), exc
        else:
            raise AssertionError("undecodable rule frontmatter was accepted")

    # #1046/#1048: valid YAML the catalog parser would record differently is refused.
    divergent = {
        "flow mapping": "---\n{name: flow, description: flow style}\n---\n",
        "explicit key": "---\n? name\n: explicit\ndescription: explicit key\n---\n",
        "multi-line plain": "---\nname: multi\ndescription: first\n  second line\n---\n",
        "keep block": "---\nname: keep\ndescription: |+\n  kept\n---\n",
    }
    for label, content in divergent.items():
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write(root, "skills/divergent/SKILL.md", content + "\n# Divergent\n")
            try:
                MODULE.source_items(root)
            except ValueError as exc:
                assert "uses YAML the catalog parser reads differently" in str(exc), (label, exc)
            else:
                raise AssertionError(f"catalog/YAML divergence accepted: {label}")

    print("skill_inventory_test: PASS")


if __name__ == "__main__":
    main()
