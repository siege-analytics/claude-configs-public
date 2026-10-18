#!/usr/bin/env python3
"""Generate a deterministic inventory of skill/rule sources and their costs.

This is evidence collection, not a lifecycle authority. Fields without committed
metadata remain ``unknown``; a missing source reference is not treated as proof
that an item is unused at runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = Path("catalog/skills-inventory.json")
DEFAULT_REPORT = Path("catalog/skills-inventory.md")
CANONICAL_OUTPUTS = {DEFAULT_JSON.as_posix(), DEFAULT_REPORT.as_posix()}
SKILL_TOKEN = re.compile(r"\[skill:([a-z0-9-]+(?:--[a-z0-9-]+)*)\]")
RULE_TOKEN = re.compile(r"\[rule:([a-z0-9-]+(?:--[a-z0-9-]+)*)\]")
RULE_FILE = re.compile(r"^_([a-z][a-z0-9-]*)-rules\.md$")
RULE_DEFINITION = re.compile(r"(?m)^\s*(?:#{1,6}\s+)?(?:\*\*)?([a-z][a-z0-9-]*:\d+)\.")
TEXT_SUFFIXES = {".md", ".py", ".sh", ".json", ".yml", ".yaml", ".toml"}
TEST_PARTS = {"_test", "tests", "test"}


def tracked_files(root: Path) -> list[Path]:
    try:
        raw = subprocess.check_output(
            ["git", "-C", str(root), "ls-files", "-z"],
            timeout=30,
            stderr=subprocess.DEVNULL,
        )
        return [root / p.decode() for p in raw.split(b"\0") if p]
    except (OSError, subprocess.SubprocessError):  # noqa: writing-tests-5 best-effort fallback; exercised in bin/_test/skill_inventory_test.py
        return sorted(p for p in root.rglob("*") if p.is_file())


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):  # noqa: writing-tests-5 best-effort malformed-source fallback; exercised in bin/_test/skill_inventory_test.py
        return ""


def frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    result: dict[str, Any] = {}
    lines = text[4:end].splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line or line[:1].isspace() or ":" not in line:
            index += 1
            continue
        key, value = line.split(":", 1)
        value = value.strip().strip("\"'")
        if value in {">-", ">", "|-", "|"}:
            folded: list[str] = []
            index += 1
            while index < len(lines) and (not lines[index] or lines[index][:1].isspace()):
                folded.append(lines[index].strip())
                index += 1
            result[key] = " ".join(part for part in folded if part)
            continue
        result[key] = value
        index += 1
    return result


def project_metadata(root: Path) -> dict[str, dict[str, Any]]:
    projects: dict[str, dict[str, Any]] = {}
    for project_file in sorted((root / "projects").glob("*/PROJECT.md")):
        data = frontmatter(read_text(project_file))
        owners: list[str] = []
        text = read_text(project_file)
        match = re.search(r"(?m)^owners:[ \t]*\n((?:[ \t]+-.*(?:\n|$))+)", text)
        if match:
            owners = [line.split("-", 1)[1].strip().strip("\"'") for line in match.group(1).splitlines()]
        projects[project_file.parent.name] = {
            "owners": owners,
            "status": data.get("status", "active"),
        }
    return projects


def ignored_sources(root: Path) -> list[dict[str, str]]:
    ignored: list[dict[str, str]] = []
    skills_root = root / "skills"
    for path in sorted(skills_root.rglob("SKILL.md")):
        if "--" in path.parent.name:
            ignored.append({
                "path": path.relative_to(root).as_posix(),
                "reason": "directory slug contains reserved project separator '--'; build.py intentionally skips it",
            })
    for path in sorted(skills_root.rglob("_*-rules.md")):
        if path.parent != skills_root:
            ignored.append({
                "path": path.relative_to(root).as_posix(),
                "reason": "nested rule file is outside build.py's authoritative top-level rule input set",
            })
    projects = project_metadata(root)
    for project, metadata in sorted(projects.items()):
        if metadata["status"] == "active":
            continue
        project_dir = root / "projects" / project
        for path in sorted(project_dir.rglob("SKILL.md")):
            ignored.append({
                "path": path.relative_to(root).as_posix(),
                "reason": f"project status is {metadata['status']}; build.py publishes active projects only",
            })
        rule_path = project_dir / "_rules.md"
        if rule_path.exists():
            ignored.append({
                "path": rule_path.relative_to(root).as_posix(),
                "reason": f"project status is {metadata['status']}; build.py publishes active projects only",
            })
    return ignored


def source_items(root: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    skills_root = root / "skills"
    skill_paths: dict[str, Path] = {}
    for skill_md in sorted(skills_root.rglob("SKILL.md")):
        rel_dir = skill_md.parent.relative_to(skills_root)
        slug = skill_md.parent.name
        if "--" in slug:
            continue
        if len(rel_dir.parts) > 1 and rel_dir.parts[0] == "shelves":
            slug = f"shelves--{slug}"
        if slug in skill_paths:
            raise ValueError(f"duplicate general skill slug {slug}: {skill_paths[slug]} and {skill_md}")
        skill_paths[slug] = rel_dir

    for slug, rel_dir in sorted(skill_paths.items()):
        path = skills_root / rel_dir / "SKILL.md"
        descendants = [other for other in skill_paths.values() if other != rel_dir and rel_dir in other.parents]
        if rel_dir.parts[0] == "shelves" and len(rel_dir.parts) >= 3:
            kind, tier, basis = "reference-shelf", "reference", "path under skills/shelves/<topic>/<book>"
        elif rel_dir.parts[0] == "shelves":
            kind, tier, basis = "shelf-router", "on-demand", "shelf router path"
        elif descendants:
            kind, tier, basis = "skill-router", "unclassified", "contains descendant skills"
        else:
            kind, tier, basis = "skill", "unclassified", "no committed tier metadata"
        items.append(make_item(root, slug, path, kind, tier, basis, project=None, owners=[]))

    for path in sorted(skills_root.glob("_*-rules.md")):
        match = RULE_FILE.match(path.name)
        if match:
            items.append(make_item(root, match.group(1), path, "rule", "unclassified", "no committed tier metadata", project=None, owners=[]))

    projects = project_metadata(root)
    for project_dir in sorted((root / "projects").glob("*")):
        if not project_dir.is_dir() or project_dir.name not in projects:
            continue
        project = project_dir.name
        if projects[project]["status"] != "active":
            continue
        owners = projects[project]["owners"]
        for path in sorted((project_dir / "skills").rglob("SKILL.md")) if (project_dir / "skills").exists() else []:
            slug = f"{project}--{path.parent.name}"
            items.append(make_item(root, slug, path, "project-skill", "project", "project source path", project, owners))
        rule_path = project_dir / "_rules.md"
        if rule_path.exists():
            items.append(make_item(root, f"{project}--rules", rule_path, "project-rule", "project", "project source path", project, owners))
    skill_kinds = {"skill", "skill-router", "shelf-router", "reference-shelf", "project-skill"}
    rule_kinds = {"rule", "project-rule"}
    for namespace, kinds in (("skill", skill_kinds), ("rule", rule_kinds)):
        seen: dict[str, str] = {}
        for item in items:
            if item["kind"] not in kinds:
                continue
            previous = seen.get(item["slug"])
            if previous:
                raise ValueError(
                    f"duplicate {namespace} slug {item['slug']}: {previous} and {item['source_path']}"
                )
            seen[item["slug"]] = item["source_path"]
    return sorted(items, key=lambda item: (item["kind"], item["slug"], item["source_path"]))


def make_item(
    root: Path,
    slug: str,
    path: Path,
    kind: str,
    tier: str,
    tier_basis: str,
    project: str | None,
    owners: list[str],
) -> dict[str, Any]:
    text = read_text(path)
    metadata = frontmatter(text)
    rel = path.relative_to(root).as_posix()
    if kind in {"skill", "skill-router", "shelf-router", "reference-shelf", "project-skill"}:
        missing = [
            field for field in ("name", "description")
            if not (metadata.get(field) or "").strip()
        ]
        if missing:
            raise ValueError(f"skill frontmatter missing {', '.join(missing)}: {rel}")
    generated: list[str] = []
    return {
        "slug": slug,
        "kind": kind,
        "source_path": rel,
        "canonical_source": rel,
        "generated_outputs": generated,
        "generated_outputs_verified": False,
        "content_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "characters": len(text),
        "lines": text.count("\n") + (1 if text and not text.endswith("\n") else 0),
        "estimated_tokens": math.ceil(len(text) / 4),
        "frontmatter_name": metadata.get("name", "unknown"),
        "description": metadata.get("description", "unknown"),
        "project": project,
        "tier": tier,
        "tier_basis": tier_basis,
        "owner": owners if owners else ["unknown"],
        "lifecycle": metadata.get("status", "unknown"),
        "last_reviewed": metadata.get("last-reviewed", "unknown"),
        "verification": metadata.get("verification", "unknown"),
        "inbound_source_references": [],
        "test_evidence": [],
        "rule_definitions": sorted(set(RULE_DEFINITION.findall(text))),
        "quality": {"grade": "unknown", "reason": "not scored by current build rubric"},
    }


def load_build_module(root: Path) -> Any | None:
    build_path = root / "bin" / "build.py"
    if not build_path.exists():
        return None
    name = "inventory_build_module_" + hashlib.sha256(str(root).encode()).hexdigest()[:12]
    spec = importlib.util.spec_from_file_location(name, build_path)
    if not spec or not spec.loader:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def discovery_parity(root: Path, items: list[dict[str, Any]]) -> dict[str, Any]:
    """Prove catalog source discovery matches build.py's authoritative inputs."""
    module = load_build_module(root)
    if module is None:
        return {"status": "unavailable", "reason": "bin/build.py not present"}
    active = module.validate_project_manifests(root / "projects")
    general_skills = module.find_skills(root / "skills")
    general_rules = module.find_rules(root / "skills")
    project_skills, _ = module.find_project_skills(root / "projects", active)
    project_rules, _ = module.find_project_rules(root / "projects", active)
    authoritative = {
        *(f"skills/{rel.as_posix()}/SKILL.md" for rel in general_skills.values()),
        *(f"skills/{rel.as_posix()}" for rel in general_rules.values()),
        *((rel / "SKILL.md").as_posix() for rel in project_skills.values()),
        *(rel.as_posix() for rel in project_rules.values()),
    }
    catalog = {item["source_path"] for item in items}
    missing = sorted(authoritative - catalog)
    extra = sorted(catalog - authoritative)
    if missing or extra:
        raise ValueError(f"inventory/build discovery drift: missing={missing}, extra={extra}")
    return {"status": "matched", "source_count": len(authoritative), "missing": [], "extra": []}


def validate_output_collisions(outputs: dict[str, list[str]]) -> None:
    claims: dict[str, list[str]] = defaultdict(list)
    for source, destinations in outputs.items():
        for destination in destinations:
            claims[destination].append(source)
    collisions = {destination: sources for destination, sources in claims.items() if len(sources) > 1}
    if collisions:
        details = "; ".join(
            f"{destination} <- {', '.join(sorted(sources))}"
            for destination, sources in sorted(collisions.items())
        )
        raise ValueError(f"generated output collision: {details}")


def apply_build_outputs(root: Path, items: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive effective destinations from build.py's own mapping functions."""
    module = load_build_module(root)
    if module is None:
        return {"status": "unavailable", "reason": "bin/build.py not present"}
    active = module.validate_project_manifests(root / "projects")
    general_skills = module.find_skills(root / "skills")
    general_rules = module.find_rules(root / "skills")
    project_skills, _ = module.find_project_skills(root / "projects", active)
    project_rules, _ = module.find_project_rules(root / "projects", active)
    outputs: dict[str, list[str]] = {}
    for slug, rel in general_skills.items():
        nested = rel
        if rel.parts and rel.parts[0] == "shelves":
            flat = rel
        elif module.is_router(rel, general_skills):
            flat = rel
        else:
            flat = Path(slug)
        source = f"skills/{rel.as_posix()}/SKILL.md"
        outputs[source] = [f"dist/nested/skills/{nested.as_posix()}", f"dist/flat/skills/{flat.as_posix()}"]
    for slug, rel in project_skills.items():
        source = (rel / "SKILL.md").as_posix()
        outputs[source] = [f"dist/nested/skills/{slug}", f"dist/flat/skills/{slug}"]
    for _, rel in general_rules.items():
        source = f"skills/{rel.as_posix()}"
        outputs[source] = [f"dist/nested/skills/{rel.as_posix()}", f"dist/flat/skills/{rel.as_posix()}"]
    for slug, rel in project_rules.items():
        outputs[rel.as_posix()] = [f"dist/nested/skills/_{slug}.md", f"dist/flat/skills/_{slug}.md"]
    validate_output_collisions(outputs)
    for item in items:
        item["generated_outputs"] = outputs[item["source_path"]]
        item["generated_outputs_verified"] = True
    return {"status": "derived-from-build.py", "source_count": len(outputs), "destination_collisions": []}


def add_quality_scores(root: Path, items: list[dict[str, Any]]) -> None:
    """Attach the existing build.py rubric without creating a second rubric."""
    module = load_build_module(root)
    if module is None:
        return
    general = {
        item["slug"]: Path(item["source_path"]).parent.relative_to("skills")
        for item in items
        if item["kind"] in {"skill", "skill-router", "shelf-router", "reference-shelf"}
    }
    known_skills = {item["slug"] for item in items if "skill" in item["kind"] or item["kind"] in {"shelf-router", "reference-shelf"}}
    known_rules = {item["slug"] for item in items if item["kind"] in {"rule", "project-rule"}}
    scores = module.score_skill_quality(general, known_skills, known_rules, root / "skills")
    by_slug = {score.slug: score for score in scores}
    scoreable_kinds = {"skill", "skill-router", "shelf-router", "reference-shelf"}
    for item in items:
        if item["kind"] not in scoreable_kinds:
            continue
        score = by_slug.get(item["slug"])
        if not score:
            continue
        item["quality"] = {
            "grade": score.grade,
            "total": round(score.total, 2),
            "structure": round(score.structure, 2),
            "cross_references": round(score.cross_refs, 2),
            "provenance": round(score.provenance, 2),
            "completeness": round(score.completeness, 2),
        }


def add_evidence(root: Path, items: list[dict[str, Any]], files: list[Path]) -> None:
    skill_kinds = {"skill", "skill-router", "shelf-router", "reference-shelf", "project-skill"}
    rule_kinds = {"rule", "project-rule"}
    skill_by_slug = {item["slug"]: item for item in items if item["kind"] in skill_kinds}
    rule_by_slug = {item["slug"]: item for item in items if item["kind"] in rule_kinds}
    source_paths = {item["source_path"]: item for item in items}
    for path in files:
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        rel = path.relative_to(root).as_posix()
        text = read_text(path)
        if not text:
            continue
        for slug in set(SKILL_TOKEN.findall(text)):
            if slug in skill_by_slug and rel != skill_by_slug[slug]["source_path"]:
                skill_by_slug[slug]["inbound_source_references"].append(rel)
        for slug in set(RULE_TOKEN.findall(text)):
            if slug in rule_by_slug and rel != rule_by_slug[slug]["source_path"]:
                rule_by_slug[slug]["inbound_source_references"].append(rel)
        is_test = bool(TEST_PARTS.intersection(path.parts)) or path.name.startswith("test_") or ".test." in path.name
        if is_test:
            for item in items:
                slug = item["slug"]
                source_hint = item["source_path"].rsplit("/", 1)[0]
                if slug in text or source_hint in text or slug.replace("--", "/") in text:
                    item["test_evidence"].append(rel)
        for source_path, item in source_paths.items():
            if source_path in text and rel != source_path:
                item["inbound_source_references"].append(rel)
    for item in items:
        item["inbound_source_references"] = sorted(set(item["inbound_source_references"]))
        item["test_evidence"] = sorted(set(item["test_evidence"]))


def build_inventory(root: Path, excluded_paths: set[str] | None = None) -> dict[str, Any]:
    root = root.resolve()
    excluded = CANONICAL_OUTPUTS | (excluded_paths or set())
    files = [path for path in tracked_files(root) if path.relative_to(root).as_posix() not in excluded]
    items = source_items(root)
    parity = discovery_parity(root, items)
    output_plan = apply_build_outputs(root, items)
    add_evidence(root, items, files)
    add_quality_scores(root, items)
    duplicate_rule_ids: dict[str, list[str]] = defaultdict(list)
    for item in items:
        for rule_id in item["rule_definitions"]:
            duplicate_rule_ids[rule_id].append(item["source_path"])
    duplicate_rule_ids = {
        rule_id: sorted(paths)
        for rule_id, paths in sorted(duplicate_rule_ids.items())
        if len(set(paths)) > 1
    }
    kind_counts = Counter(item["kind"] for item in items)
    tier_counts = Counter(item["tier"] for item in items)
    tier_chars = Counter()
    tier_tokens = Counter()
    for item in items:
        tier_chars[item["tier"]] += item["characters"]
        tier_tokens[item["tier"]] += item["estimated_tokens"]
    quality_grades = Counter(item["quality"]["grade"] for item in items)
    summary = {
        "item_count": len(items),
        "kind_counts": dict(sorted(kind_counts.items())),
        "tier_counts": dict(sorted(tier_counts.items())),
        "characters": sum(item["characters"] for item in items),
        "estimated_tokens": sum(item["estimated_tokens"] for item in items),
        "tier_characters": dict(sorted(tier_chars.items())),
        "tier_estimated_tokens": dict(sorted(tier_tokens.items())),
        "unknown_owner_count": sum(item["owner"] == ["unknown"] for item in items),
        "unknown_lifecycle_count": sum(item["lifecycle"] == "unknown" for item in items),
        "without_source_references_count": sum(not item["inbound_source_references"] for item in items),
        "without_test_evidence_count": sum(not item["test_evidence"] for item in items),
        "duplicate_rule_id_count": len(duplicate_rule_ids),
        "quality_grade_counts": dict(sorted(quality_grades.items())),
        "quality_low_grade_count": sum(item["quality"]["grade"] in {"D", "F"} for item in items),
    }
    return {
        "schema_version": 1,
        "measurement_notes": {
            "estimated_tokens": "ceil(UTF-8 decoded character count / 4); directional, not tokenizer-exact",
            "inbound_source_references": "tracked source token/path references; absence is not proof of no runtime use",
            "test_evidence": "tracked test files containing the slug or source path; heuristic evidence only",
            "tier": "path-evidenced where possible; otherwise unclassified until lifecycle metadata is introduced",
            "generated_outputs": "logical build destinations; dist is generated and not required to be tracked",
        },
        "summary": summary,
        "diagnostics": {
            "duplicate_rule_ids": duplicate_rule_ids,
            "discovery_parity": parity,
            "generated_output_plan": output_plan,
            "ignored_sources": ignored_sources(root),
            "unclassified": [item["slug"] for item in items if item["tier"] == "unclassified"],
            "unknown_owners": [item["slug"] for item in items if item["owner"] == ["unknown"]],
            "unknown_lifecycle": [item["slug"] for item in items if item["lifecycle"] == "unknown"],
            "without_source_references": [item["slug"] for item in items if not item["inbound_source_references"]],
            "without_test_evidence": [item["slug"] for item in items if not item["test_evidence"]],
        },
        "items": items,
    }


def render_report(inventory: dict[str, Any]) -> str:
    summary = inventory["summary"]
    items = inventory["items"]
    lines = [
        "# Skill and Rule Inventory",
        "",
        "> Generated by `python3 bin/skill-inventory.py`. Do not edit manually.",
        "",
        "This report describes committed source evidence. Missing references or tests do not prove runtime non-use.",
        "",
        "## Summary",
        "",
        f"- Source items: **{summary['item_count']}**",
        f"- Characters: **{summary['characters']:,}**",
        f"- Estimated tokens: **{summary['estimated_tokens']:,}** (character/4 estimate)",
        f"- Unknown owners: **{summary['unknown_owner_count']}**",
        f"- Unknown lifecycle states: **{summary['unknown_lifecycle_count']}**",
        f"- Without tracked source references: **{summary['without_source_references_count']}**",
        f"- Without heuristic test evidence: **{summary['without_test_evidence_count']}**",
        f"- Duplicate rule IDs: **{summary['duplicate_rule_id_count']}**",
        f"- Current build-rubric D/F grades: **{summary['quality_low_grade_count']}**",
        "- Quality grades: " + ", ".join(f"{grade}: {count}" for grade, count in summary["quality_grade_counts"].items()),
        "",
        "### By kind",
        "",
        "| Kind | Count |",
        "|---|---:|",
    ]
    lines += [f"| {kind} | {count} |" for kind, count in summary["kind_counts"].items()]
    lines += ["", "### By proposed tier", "", "| Tier | Count | Characters | Est. tokens |", "|---|---:|---:|---:|"]
    for tier, count in summary["tier_counts"].items():
        lines.append(f"| {tier} | {count} | {summary['tier_characters'][tier]:,} | {summary['tier_estimated_tokens'][tier]:,} |")
    lines += ["", "## Largest source items", "", "| Slug | Kind | Characters | Est. tokens | Source |", "|---|---|---:|---:|---|"]
    for item in sorted(items, key=lambda entry: (-entry["characters"], entry["slug"]))[:25]:
        lines.append(f"| `{item['slug']}` | {item['kind']} | {item['characters']:,} | {item['estimated_tokens']:,} | `{item['source_path']}` |")
    lines += [
        "",
        "## Evidence gaps",
        "",
        f"- Unclassified tier: {len(inventory['diagnostics']['unclassified'])}",
        f"- Unknown owners: {len(inventory['diagnostics']['unknown_owners'])}",
        f"- Unknown lifecycle: {len(inventory['diagnostics']['unknown_lifecycle'])}",
        f"- No tracked source references: {len(inventory['diagnostics']['without_source_references'])}",
        f"- No heuristic test evidence: {len(inventory['diagnostics']['without_test_evidence'])}",
        "",
        "These are Phase 1 inputs, not automatic retirement decisions.",
        "",
        "## Duplicate rule identifiers",
        "",
    ]
    duplicates = inventory["diagnostics"]["duplicate_rule_ids"]
    if duplicates:
        for rule_id, paths in duplicates.items():
            lines.append(f"- `{rule_id}`: " + ", ".join(f"`{path}`" for path in paths))
    else:
        lines.append("None detected.")
    lines += ["", "## Complete catalog", "", "See [`skills-inventory.json`](skills-inventory.json) for item-level evidence and diagnostics.", ""]
    return "\n".join(lines)


def serialized(inventory: dict[str, Any]) -> tuple[str, str]:
    return json.dumps(inventory, indent=2, sort_keys=True) + "\n", render_report(inventory)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--check", action="store_true", help="fail if committed outputs differ from regeneration")
    args = parser.parse_args()
    root = args.root.resolve()
    json_path = args.json if args.json.is_absolute() else root / args.json
    report_path = args.report if args.report.is_absolute() else root / args.report
    output_excludes = {
        path.relative_to(root).as_posix()
        for path in (json_path, report_path)
        if path.is_relative_to(root)
    }
    json_text, report_text = serialized(build_inventory(root, output_excludes))
    if args.check:
        stale = []
        if read_text(json_path) != json_text:
            stale.append(json_path)
        if read_text(report_path) != report_text:
            stale.append(report_path)
        if stale:
            print("STALE skill inventory outputs:", file=sys.stderr)
            for path in stale:
                print(f"  {path}", file=sys.stderr)
            print("Run: python3 bin/skill-inventory.py", file=sys.stderr)
            return 1
        print("skill inventory: current")
        return 0
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json_text)
    report_path.write_text(report_text)
    print(f"wrote {json_path.relative_to(root)}")
    print(f"wrote {report_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
