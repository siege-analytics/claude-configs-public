#!/usr/bin/env python3
"""Build dist/nested/ and dist/flat/ from skills/ source.

Resolves [skill:slug] and [rule:slug] tokens to layout-appropriate paths.
Generates RESOLVER.md from RESOLVER.template.md for each layout.
Generates dist/RULES_BUNDLE.md and dist/RULES_BUNDLE.json for non-hook runtimes.
Validates that every token references an existing skill/rule.
Validates project manifests: required frontmatter, repo uniqueness, status lifecycle.

Usage:
    python bin/build.py            # build both layouts + rules bundle
    python bin/build.py --check    # validate tokens only, no output
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_SKILLS = REPO_ROOT / "skills"
SOURCE_PROJECTS = REPO_ROOT / "projects"
SOURCE_SOLUTIONS = REPO_ROOT / "solutions"
DIST = REPO_ROOT / "dist"

CRAFT_WORKSPACE = Path.home() / ".craft-agent" / "workspaces" / "my-workspace"

# Frontmatter keys that Craft Agent misinterprets (e.g. as a hide signal).
# Stripped during --deploy. Matches electinfo_claude_skills/scripts/build.py.
CRAFT_INCOMPATIBLE_KEYS = {"disable-model-invocation", "argument-hint"}

# Separator joining project slug and skill/rule slug in the prefix-flatten convention.
# Project skill `hostile-review` in project `siege-utilities` becomes flat slug
# `siege-utilities--hostile-review`. Project rules file becomes `<project>--rules`
# (rendered to `_<project>--rules.md` at the flat skills root).
PROJECT_SEP = "--"

# Categories that hold leaf skills (not the meta-router itself)
SKILL_CATEGORIES = (
    "coding",
    "git-workflow",
    "planning",
    "session",
    "analysis",
    "infrastructure",
    "maintenance",
    "documentation",
    "thinking",
    "meta",
    "shelves",
    "testing",
)

# Top-level files that travel with each layout
ROOT_FILES = (
    "README.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
)

# Rules files at skills/ root. Slug may contain the project separator (e.g.
# `siege-utilities--rules` for a flattened project rules file).
RULE_PATTERN = re.compile(r"^_(?P<slug>[a-z][a-z0-9-]*)-rules\.md$")

# Token patterns. Slugs may contain `--` to address prefix-flattened project content.
SKILL_TOKEN = re.compile(r"\[skill:(?P<slug>[a-z0-9-]+)\]")
RULE_TOKEN = re.compile(r"\[rule:(?P<slug>[a-z0-9-]+)\]")


class BuildError(Exception):
    pass


# Track unknown slug references for warnings (per build run)
UNKNOWN_SKILLS: dict[str, set[str]] = {}
UNKNOWN_RULES: dict[str, set[str]] = {}


# ---------------------------------------------------------------------------
# Project manifest — parsed from PROJECT.md frontmatter
# ---------------------------------------------------------------------------

@dataclass
class ProjectManifest:
    """Parsed and validated PROJECT.md frontmatter for a single project."""
    slug: str
    name: str
    description: str
    repo: str
    owners: list[str]
    scope: list[str] = field(default_factory=list)
    status: str = "active"
    retired_at: Optional[str] = None
    successor: Optional[str] = None
    source_path: Path = field(default_factory=lambda: Path("."))

    VALID_STATUSES = ("active", "archived", "retired")
    REQUIRED_FIELDS = ("name", "description", "repo", "owners")


def _parse_yaml_frontmatter(content: str) -> dict[str, str | list[str]]:
    """Minimal YAML frontmatter parser — handles the fields we care about.

    Not a full YAML parser. Handles scalar values and simple list values
    (lines starting with '  - '). Good enough for PROJECT.md validation
    without pulling in PyYAML as a build dependency.
    """
    if not content.startswith("---\n"):
        return {}
    end = content.find("\n---\n", 4)
    if end == -1:
        return {}
    fm_block = content[4:end]

    result: dict[str, str | list[str]] = {}
    current_key: Optional[str] = None
    current_list: Optional[list[str]] = None

    for line in fm_block.splitlines():
        list_match = re.match(r"^\s+-\s+(.+)$", line)
        if list_match and current_key is not None and current_list is not None:
            val = list_match.group(1).strip().strip('"').strip("'")
            current_list.append(val)
            continue

        kv_match = re.match(r"^([a-z_-]+):\s*(.*)$", line)
        if kv_match:
            if current_key and current_list is not None:
                result[current_key] = current_list
            key = kv_match.group(1)
            val = kv_match.group(2).strip().strip('"').strip("'")
            if val:
                result[key] = val
                current_key = key
                current_list = None
            else:
                current_key = key
                current_list = []
            continue

    if current_key and current_list is not None:
        result[current_key] = current_list

    return result


def parse_project_manifest(project_dir: Path) -> Optional[ProjectManifest]:
    """Parse and validate a PROJECT.md, returning a ProjectManifest or raising BuildError."""
    project_md = project_dir / "PROJECT.md"
    if not project_md.exists():
        return None

    content = project_md.read_text()
    fm = _parse_yaml_frontmatter(content)
    slug = project_dir.name

    missing = [f for f in ProjectManifest.REQUIRED_FIELDS if f not in fm]
    if missing:
        raise BuildError(
            f"PROJECT.md for '{slug}' is missing required frontmatter fields: {missing}\n"
            f"  File: {project_md.relative_to(REPO_ROOT)}"
        )

    owners = fm["owners"]
    if isinstance(owners, str):
        owners = [owners]

    scope = fm.get("scope", [])
    if isinstance(scope, str):
        scope = [scope]

    status = str(fm.get("status", "active")).lower()
    if status not in ProjectManifest.VALID_STATUSES:
        raise BuildError(
            f"PROJECT.md for '{slug}' has invalid status: '{status}'. "
            f"Must be one of: {ProjectManifest.VALID_STATUSES}\n"
            f"  File: {project_md.relative_to(REPO_ROOT)}"
        )

    return ProjectManifest(
        slug=slug,
        name=str(fm["name"]),
        description=str(fm["description"]),
        repo=str(fm["repo"]),
        owners=owners,
        scope=scope,
        status=status,
        retired_at=str(fm["retired_at"]) if "retired_at" in fm else None,
        successor=str(fm["successor"]) if "successor" in fm else None,
        source_path=project_md,
    )


def validate_project_manifests(projects_root: Path) -> dict[str, ProjectManifest]:
    """Parse all PROJECT.md files, enforce cross-project invariants.

    Returns {slug: manifest} for active projects only.
    Raises BuildError on: missing required fields, invalid status, duplicate repo.
    Prints warnings for: archived/retired projects (excluded from build output).
    """
    if not projects_root.exists():
        return {}

    all_manifests: dict[str, ProjectManifest] = {}
    active_manifests: dict[str, ProjectManifest] = {}

    for project_dir in sorted(projects_root.iterdir()):
        if not project_dir.is_dir():
            continue
        manifest = parse_project_manifest(project_dir)
        if manifest is None:
            continue
        all_manifests[manifest.slug] = manifest

    # Enforce repo uniqueness across ALL projects (including archived).
    repos_seen: dict[str, str] = {}
    for slug, m in all_manifests.items():
        if m.repo in repos_seen:
            raise BuildError(
                f"Duplicate repo claim: projects '{repos_seen[m.repo]}' and '{slug}' "
                f"both declare repo: {m.repo}. Each repo may belong to at most one project."
            )
        repos_seen[m.repo] = slug

    # Partition by status.
    for slug, m in all_manifests.items():
        if m.status == "active":
            active_manifests[slug] = m
        elif m.status == "archived":
            print(f"  [skip] Project '{slug}' is archived — excluded from build output")
        elif m.status == "retired":
            print(f"  [skip] Project '{slug}' is retired — excluded from build output")
            if not m.successor:
                print(f"  [warn] Retired project '{slug}' has no successor: field")

    return active_manifests


# ---------------------------------------------------------------------------
# Solutions catalog validation (#421)
# ---------------------------------------------------------------------------

VALID_CATEGORIES = (
    "conventions",
    "data-integrity",
    "packaging-truth",
    "pipeline-operations",
    "spatial-domain",
    "architecture-patterns",
    "security-issues",
    "performance-issues",
)

VALID_SEVERITIES = ("S1", "S2", "S3", "enhancement")

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_solutions(solutions_root: Path) -> int:
    """Validate YAML frontmatter of all solutions/*.md files (excluding README.md).

    Returns the number of valid entries. Raises BuildError on validation failures.
    """
    if not solutions_root.exists():
        return 0

    errors: list[str] = []
    count = 0

    for entry in sorted(solutions_root.iterdir()):
        if not entry.is_file() or entry.suffix.lower() != ".md":
            continue
        if entry.name.lower() == "readme.md":
            continue

        content = entry.read_text()
        fm = _parse_yaml_frontmatter(content)
        rel = entry.relative_to(REPO_ROOT)

        if not fm:
            errors.append(f"{rel}: missing or unparseable YAML frontmatter")
            continue

        for field in ("title", "category", "date", "severity"):
            if field not in fm or not fm[field]:
                errors.append(f"{rel}: missing required field '{field}'")

        if "category" in fm:
            cat = str(fm["category"])
            if cat not in VALID_CATEGORIES:
                errors.append(
                    f"{rel}: invalid category '{cat}'. "
                    f"Must be one of: {', '.join(VALID_CATEGORIES)}"
                )

        if "severity" in fm:
            sev = str(fm["severity"])
            if sev not in VALID_SEVERITIES:
                errors.append(
                    f"{rel}: invalid severity '{sev}'. "
                    f"Must be one of: {', '.join(VALID_SEVERITIES)}"
                )

        if "date" in fm:
            date_val = str(fm["date"])
            if not _DATE_RE.match(date_val):
                errors.append(f"{rel}: invalid date format '{date_val}'. Must be YYYY-MM-DD")

        count += 1

    if errors:
        raise BuildError(
            "Solutions catalog validation failed:\n  " + "\n  ".join(errors)
        )

    return count


# ---------------------------------------------------------------------------
# Skill and rule discovery
# ---------------------------------------------------------------------------

def find_skills(source: Path) -> dict[str, Path]:
    """Walk source/, return {slug: source_dir_relative_to_skills} for every SKILL.md.

    Includes both leaf skills AND routers (skills that have child SKILL.md files). The
    distinction matters at runtime (routers dispatch; leaves act) but not at build time
    (both need slug-token resolution). Slugs must be globally unique.

    Shelf-class skills under `skills/shelves/<slug>/` are namespaced as
    `shelves--<slug>` so they can coexist with a top-level skill of the same
    name (e.g. `django` top-level vs the `shelves/django` shelf). Token
    references resolve by their full namespaced slug.
    """
    skills: dict[str, Path] = {}
    for skill_md in source.rglob("SKILL.md"):
        skill_dir = skill_md.parent
        rel = skill_dir.relative_to(source)
        slug = skill_dir.name
        if PROJECT_SEP in slug:
            continue
        # Shelves-class skills get the `shelves--` namespace prefix to prevent
        # collision with top-level skills of the same directory name.
        if len(rel.parts) > 1 and rel.parts[0] == "shelves":
            slug = f"shelves{PROJECT_SEP}{slug}"
        if slug in skills:
            raise BuildError(
                f"Slug collision on '{slug}':\n"
                f"  {skills[slug]}\n"
                f"  {rel}\n"
                f"Slugs must be globally unique across categories."
            )
        skills[slug] = rel
    return skills


def is_router(skill_relpath: Path, all_skill_paths: dict[str, Path]) -> bool:
    """Return True if this skill has child SKILL.md descendants (i.e., it's a router)."""
    for other_path in all_skill_paths.values():
        if other_path != skill_relpath and skill_relpath in other_path.parents:
            return True
    return False


def find_rules(source: Path) -> dict[str, Path]:
    """Return {slug: source_path_relative_to_skills} for every _*-rules.md file at skills root."""
    rules: dict[str, Path] = {}
    for rule_path in source.iterdir():
        if not rule_path.is_file():
            continue
        m = RULE_PATTERN.match(rule_path.name)
        if not m:
            continue
        rules[m.group("slug")] = rule_path.relative_to(source)
    return rules


def find_project_skills(
    projects_root: Path, active_projects: dict[str, ProjectManifest],
) -> tuple[dict[str, Path], dict[str, str]]:
    """Walk projects/<project>/skills/<skill>/SKILL.md for active projects only.

    Returns (skills_dict, provenance_dict) where:
      - skills_dict: {prefixed_slug: src_path_relative_to_repo}
      - provenance_dict: {prefixed_slug: project_slug}
    """
    skills: dict[str, Path] = {}
    provenance: dict[str, str] = {}
    if not projects_root.exists():
        return skills, provenance
    for project_dir in sorted(projects_root.iterdir()):
        if not project_dir.is_dir():
            continue
        project_slug = project_dir.name
        if project_slug not in active_projects:
            continue
        if PROJECT_SEP in project_slug:
            raise BuildError(
                f"Project slug must not contain the project separator '{PROJECT_SEP}': {project_slug}"
            )
        project_skills_dir = project_dir / "skills"
        if not project_skills_dir.exists():
            continue
        for skill_md in project_skills_dir.rglob("SKILL.md"):
            skill_slug = skill_md.parent.name
            if PROJECT_SEP in skill_slug:
                raise BuildError(
                    f"Skill slug must not contain the project separator '{PROJECT_SEP}': "
                    f"{skill_md.parent.relative_to(REPO_ROOT)}"
                )
            prefixed = f"{project_slug}{PROJECT_SEP}{skill_slug}"
            if prefixed in skills:
                raise BuildError(
                    f"Project skill collision on '{prefixed}':\n"
                    f"  {skills[prefixed]}\n"
                    f"  {skill_md.parent.relative_to(REPO_ROOT)}"
                )
            skills[prefixed] = skill_md.parent.relative_to(REPO_ROOT)
            provenance[prefixed] = project_slug
    return skills, provenance


def find_project_rules(
    projects_root: Path, active_projects: dict[str, ProjectManifest],
) -> tuple[dict[str, Path], dict[str, str]]:
    """Walk projects/<project>/_rules.md for active projects only.

    Returns (rules_dict, provenance_dict) where:
      - rules_dict: {prefixed_slug: src_path_relative_to_repo}
      - provenance_dict: {prefixed_slug: project_slug}
    """
    rules: dict[str, Path] = {}
    provenance: dict[str, str] = {}
    if not projects_root.exists():
        return rules, provenance
    for project_dir in sorted(projects_root.iterdir()):
        if not project_dir.is_dir():
            continue
        if project_dir.name not in active_projects:
            continue
        rules_path = project_dir / "_rules.md"
        if not rules_path.exists():
            continue
        prefixed = f"{project_dir.name}{PROJECT_SEP}rules"
        rules[prefixed] = rules_path.relative_to(REPO_ROOT)
        provenance[prefixed] = project_dir.name
    return rules, provenance


# ---------------------------------------------------------------------------
# Frontmatter injection
# ---------------------------------------------------------------------------

def inject_project_frontmatter(content: str, project_slug: str) -> str:
    """Add `project: <slug>` to YAML frontmatter of a SKILL.md, idempotently.

    If no frontmatter exists, do nothing (the SKILL.md is malformed; build will surface
    that elsewhere). If `project:` already present, leave as-is.
    """
    if not content.startswith("---\n"):
        return content
    end = content.find("\n---\n", 4)
    if end == -1:
        return content
    frontmatter = content[4:end]
    if re.search(r"(?m)^project:\s*", frontmatter):
        return content
    new_frontmatter = frontmatter.rstrip() + f"\nproject: {project_slug}\n"
    return "---\n" + new_frontmatter + content[end + 1:]


# ---------------------------------------------------------------------------
# Token resolution
# ---------------------------------------------------------------------------

def resolve_tokens(content: str, layout: str, skill_paths: dict[str, str], rule_paths: dict[str, str], from_path: Path) -> str:
    """Expand [skill:slug] and [rule:slug] tokens to layout-appropriate Markdown links.

    `from_path` is the SKILL.md (or .md) file's path relative to skills/, used to compute
    relative links to the target.
    """
    def link_to(target_relpath: str) -> str:
        # Compute relative path from from_path's directory to target
        from_dir = from_path.parent
        target = Path(target_relpath)
        # `..` chain from from_dir to skills/ root, then down to target
        depth = len(from_dir.parts)
        prefix = "../" * depth if depth else ""
        return prefix + target_relpath

    def replace_skill(match: re.Match[str]) -> str:
        slug = match.group("slug")
        if slug not in skill_paths:
            UNKNOWN_SKILLS.setdefault(str(from_path), set()).add(slug)
            return f"`{slug}` (planned)"
        target = skill_paths[slug] + "/SKILL.md"
        return f"[`{slug}`]({link_to(target)})"

    def replace_rule(match: re.Match[str]) -> str:
        slug = match.group("slug")
        if slug not in rule_paths:
            UNKNOWN_RULES.setdefault(str(from_path), set()).add(slug)
            return f"`_{slug}-rules.md` (planned)"
        return f"[`{slug}`]({link_to(rule_paths[slug])})"

    content = SKILL_TOKEN.sub(replace_skill, content)
    content = RULE_TOKEN.sub(replace_rule, content)
    return content


def write_resolved(src_file: Path, dst_file: Path, layout: str, skill_paths: dict[str, str], rule_paths: dict[str, str], rel_to_skills: Path) -> None:
    """Read source markdown file, resolve tokens, write to destination."""
    content = src_file.read_text()
    resolved = resolve_tokens(content, layout, skill_paths, rule_paths, rel_to_skills)
    dst_file.parent.mkdir(parents=True, exist_ok=True)
    dst_file.write_text(resolved)


# ---------------------------------------------------------------------------
# Directory copy helpers
# ---------------------------------------------------------------------------

def copy_skill_dir(
    src_dir: Path,
    dst_dir: Path,
    layout: str,
    skill_paths: dict[str, str],
    rule_paths: dict[str, str],
    output_skill_relpath: str,
) -> None:
    """Copy a skill directory's own content, resolving tokens in markdown files.

    Skips subdirectories that contain a SKILL.md (those are other skills with their own
    copy step in the build loop). This is what lets routers and leaves coexist without
    duplicating leaves under the router's destination tree.
    """
    if dst_dir.exists():
        shutil.rmtree(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)

    def is_other_skill_dir(path: Path) -> bool:
        if not path.is_dir():
            return False
        return (path / "SKILL.md").exists()

    for src in src_dir.rglob("*"):
        rel = src.relative_to(src_dir)
        skip = False
        for ancestor in rel.parents:
            if ancestor == Path("."):
                continue
            if is_other_skill_dir(src_dir / ancestor):
                skip = True
                break
        if skip:
            continue
        if src.is_dir() and src != src_dir and is_other_skill_dir(src):
            continue

        dst = dst_dir / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue
        if src.suffix.lower() == ".md":
            output_rel = Path(output_skill_relpath) / rel
            write_resolved(src, dst, layout, skill_paths, rule_paths, output_rel)
        else:
            shutil.copy2(src, dst)


def copy_project_skill_dir(
    src_dir: Path,
    dst_dir: Path,
    layout: str,
    skill_paths: dict[str, str],
    rule_paths: dict[str, str],
    output_skill_relpath: str,
    project_slug: str,
) -> None:
    """Like copy_skill_dir, but injects `project: <slug>` frontmatter into the SKILL.md.

    Project skills never have nested child skills, so we don't replicate the
    is-other-skill-dir filtering. If a project skill ever contains a nested SKILL.md
    that's a design break — surface it loudly.
    """
    if dst_dir.exists():
        shutil.rmtree(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    for src in src_dir.rglob("*"):
        rel = src.relative_to(src_dir)
        if src.is_dir():
            (dst_dir / rel).mkdir(parents=True, exist_ok=True)
            continue
        if src.name == "SKILL.md" and src.parent != src_dir:
            raise BuildError(
                f"Nested SKILL.md inside a project skill is not supported: {src.relative_to(REPO_ROOT)}"
            )
        dst = dst_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix.lower() == ".md":
            content = src.read_text()
            if src.name == "SKILL.md":
                content = inject_project_frontmatter(content, project_slug)
            output_rel = Path(output_skill_relpath) / rel
            resolved = resolve_tokens(content, layout, skill_paths, rule_paths, output_rel)
            dst.write_text(resolved)
        else:
            shutil.copy2(src, dst)


# ---------------------------------------------------------------------------
# Layout builder
# ---------------------------------------------------------------------------

def build_layout(
    layout: str,
    skills_src: dict[str, Path],
    rules_src: dict[str, Path],
    project_skills_src: dict[str, Path],
    project_rules_src: dict[str, Path],
    skill_provenance: dict[str, str],
    active_projects: dict[str, ProjectManifest],
) -> dict[str, str]:
    """Build a single layout. Returns {slug: output-path-from-dist-root} for skills.

    Project skills (under projects/<project>/skills/<skill>/) are prefix-flattened
    to skills/<project>--<skill>/ in BOTH layouts — projects don't have categories,
    so there's no "nested" project layout. Project rules become _<project>--rules.md
    at the flat skills root. PROJECT.md files travel to dist/<layout>/projects/<project>/.
    Only active projects are published.
    """
    out_root = DIST / layout / "skills"
    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    # Compute output paths per layout
    if layout == "nested":
        skill_out_paths = {slug: str(src) for slug, src in skills_src.items()}
    elif layout == "flat":
        skill_out_paths = {}
        for slug, src in skills_src.items():
            if src.parts and src.parts[0] == "shelves":
                skill_out_paths[slug] = str(src)
            elif is_router(src, skills_src):
                skill_out_paths[slug] = str(src)
            else:
                skill_out_paths[slug] = slug
    else:
        raise BuildError(f"Unknown layout: {layout}")

    # Project skills: always flat-named (<project>--<skill>) in both layouts.
    for prefixed_slug in project_skills_src:
        if prefixed_slug in skill_out_paths:
            raise BuildError(
                f"Project skill slug collides with general skill slug: '{prefixed_slug}'. "
                f"Choose a different skill name within the project."
            )
        skill_out_paths[prefixed_slug] = prefixed_slug

    rule_out_paths = {slug: str(src) for slug, src in rules_src.items()}
    for prefixed_slug in project_rules_src:
        if prefixed_slug in rule_out_paths:
            raise BuildError(
                f"Project rule slug collides with general rule slug: '{prefixed_slug}'."
            )
        rule_out_paths[prefixed_slug] = f"_{prefixed_slug}.md"

    # Copy general skills with token resolution
    for slug, src_rel in skills_src.items():
        src_dir = SOURCE_SKILLS / src_rel
        dst_dir = out_root / skill_out_paths[slug]
        copy_skill_dir(src_dir, dst_dir, layout, skill_out_paths, rule_out_paths, skill_out_paths[slug])

    # Copy project skills with token resolution + frontmatter injection
    for prefixed_slug, src_rel in project_skills_src.items():
        project_slug = skill_provenance[prefixed_slug]
        src_dir = REPO_ROOT / src_rel
        dst_dir = out_root / skill_out_paths[prefixed_slug]
        copy_project_skill_dir(
            src_dir, dst_dir, layout, skill_out_paths, rule_out_paths,
            skill_out_paths[prefixed_slug], project_slug,
        )

    # Copy general rules with token resolution
    for slug, rule_rel in rules_src.items():
        src = SOURCE_SKILLS / rule_rel
        dst = out_root / rule_rel
        write_resolved(src, dst, layout, skill_out_paths, rule_out_paths, rule_rel)

    # Copy project rules with token resolution
    for prefixed_slug, src_rel in project_rules_src.items():
        src = REPO_ROOT / src_rel
        dst = out_root / rule_out_paths[prefixed_slug]
        write_resolved(src, dst, layout, skill_out_paths, rule_out_paths, Path(rule_out_paths[prefixed_slug]))

    # Copy PROJECT.md for active projects only.
    for slug, manifest in active_projects.items():
        project_md = SOURCE_PROJECTS / slug / "PROJECT.md"
        if not project_md.exists():
            continue
        dst = DIST / layout / "projects" / slug / "PROJECT.md"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(project_md, dst)

    # Generate RESOLVER.md from RESOLVER.template.md
    template = SOURCE_SKILLS / "RESOLVER.template.md"
    if template.exists():
        write_resolved(template, out_root / "RESOLVER.md", layout, skill_out_paths, rule_out_paths, Path("RESOLVER.md"))

    # Copy entry-point and matrix files at skills/ root.
    for fname in ("RULES.md", "_coverage.md"):
        src = SOURCE_SKILLS / fname
        if src.exists():
            write_resolved(src, out_root / fname, layout, skill_out_paths, rule_out_paths, Path(fname))

    # Copy top-level repo files
    for fname in ROOT_FILES:
        src = REPO_ROOT / fname
        if src.exists():
            shutil.copy2(src, DIST / layout / fname)

    # Copy hooks/ unchanged (same in both layouts)
    src_hooks = REPO_ROOT / "hooks"
    dst_hooks = DIST / layout / "hooks"
    if src_hooks.exists():
        if dst_hooks.exists():
            shutil.rmtree(dst_hooks)
        shutil.copytree(src_hooks, dst_hooks)

    return skill_out_paths


def write_build_info(
    layout: str,
    skills_src: dict[str, Path],
    skill_out_paths: dict[str, str],
    active_projects: dict[str, ProjectManifest],
) -> None:
    """Write dist/<layout>/build-info.json."""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
        ).strip()
    except Exception:
        commit = "unknown"

    info = {
        "layout": layout,
        "source_commit": commit,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "skill_count": len(skills_src),
        "slugs": sorted(skills_src.keys()),
        "active_projects": {
            slug: {"repo": m.repo, "status": m.status}
            for slug, m in active_projects.items()
        },
    }
    (DIST / layout / "build-info.json").write_text(json.dumps(info, indent=2) + "\n")


# ---------------------------------------------------------------------------
# Rules bundle (runtime-agnostic)
# ---------------------------------------------------------------------------

def _strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter (--- ... ---) from markdown content."""
    if not content.startswith("---\n"):
        return content
    end = content.find("\n---\n", 4)
    if end == -1:
        return content
    return content[end + 5:].lstrip("\n")


def _get_version() -> str:
    """Read VERSION file, fall back to 'dev'."""
    version_file = REPO_ROOT / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "dev"


def build_rules_bundle(
    rules_src: dict[str, Path],
    project_rules_src: Optional[dict[str, Path]] = None,
    rule_provenance: Optional[dict[str, str]] = None,
) -> None:
    """Concatenate RULES.md + general _*-rules.md + project _rules.md into a bundle.

    `rules_src` carries the general rule cohort discovered by `find_rules`
    (paths relative to SOURCE_SKILLS). `project_rules_src` and
    `rule_provenance` carry the active-project rule files discovered by
    `find_project_rules` (paths relative to REPO_ROOT; provenance maps each
    prefixed key like `siege-utilities--rules` to its project slug).

    Both project params default to None so consumers calling the bundle
    without project awareness (older callsites, wrapper repos that don't
    use the `projects/` convention) keep working unchanged.

    Layout of the bundle:
      banner -> RULES.md entry -> general rules (sorted) ->
      optional `## Project rules` section -> per-project rule sections (sorted).

    Emits:
      dist/RULES_BUNDLE.md  -- for system-prompt mounting
      dist/RULES_BUNDLE.json -- for selective injection / staleness hashing
    """
    DIST.mkdir(parents=True, exist_ok=True)

    project_rules_src = project_rules_src or {}
    rule_provenance = rule_provenance or {}

    version = _get_version()
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
        ).strip()
    except Exception:
        commit = "unknown"
    built_at = datetime.now(timezone.utc).isoformat()

    # Read RULES.md (entry point)
    rules_entry = SOURCE_SKILLS / "RULES.md"
    entry_content = ""
    if rules_entry.exists():
        entry_content = _strip_frontmatter(rules_entry.read_text())

    # Read each general rule (path is relative to SOURCE_SKILLS).
    general_contents: dict[str, str] = {}
    for slug in sorted(rules_src.keys()):
        src_path = SOURCE_SKILLS / rules_src[slug]
        if src_path.exists():
            general_contents[slug] = _strip_frontmatter(src_path.read_text())

    # Read each project rule (path is relative to REPO_ROOT).
    project_contents: dict[str, str] = {}
    for prefixed_slug in sorted(project_rules_src.keys()):
        src_path = REPO_ROOT / project_rules_src[prefixed_slug]
        if src_path.exists():
            project_contents[prefixed_slug] = _strip_frontmatter(src_path.read_text())

    # Provenance: every key marked as 'general' or '<project-slug>'. Consumers
    # who want to filter to one cohort (e.g. drop project rules for a session
    # that isn't working in any project's domain) read this dict.
    provenance: dict[str, str] = {slug: "general" for slug in general_contents}
    for prefixed_slug in project_contents:
        provenance[prefixed_slug] = rule_provenance.get(prefixed_slug, "unknown-project")

    # ---- Markdown bundle ----

    project_note = ""
    if project_contents:
        project_summary = ", ".join(sorted({rule_provenance.get(k, "?") for k in project_contents}))
        project_note = (
            f"\nIncludes project-namespaced rules for active project(s): "
            f"**{project_summary}**. Project rules apply only when the session is\n"
            f"working in that project's domain; treat them as scoped extensions of\n"
            f"the general cohort, not always-on rules across every project.\n"
        )

    banner = (
        f"# Rules Bundle\n"
        f"\n"
        f"**Version:** {version} | **Commit:** {commit} | **Built:** {built_at}\n"
        f"\n"
        f"This file concatenates the always-on rule set from claude-configs-public.\n"
        f"Mount it as a system-prompt addendum if your runtime does not run\n"
        f"`.claude/settings.json` hooks (e.g. Craft Agent, Cursor, Cody).\n"
        f"\n"
        f"**Craft Agent (verified 2026-06-07):** rename this file to `CLAUDE.md`\n"
        f"(or symlink it) and place it in the session's working directory. CA\n"
        f"auto-injects CLAUDE.md / AGENTS.md content from cwd and its\n"
        f"subdirectories. CA does NOT walk parent directories, so the file\n"
        f"must be at or below the session's cwd. For workspace-wide coverage,\n"
        f"set Settings -> Workspace Settings -> Default Working Directory to\n"
        f"the directory that contains the CLAUDE.md. `bin/install.sh --deploy`\n"
        f"handles the symlink automatically.\n"
        f"\n"
        f"For hook-capable runtimes (Claude Code CLI), hooks remain the preferred\n"
        f"path. This bundle is a fallback, not a replacement.\n"
        f"{project_note}"
        f"\n"
        f"Source: siege-analytics/claude-configs-public @ {commit}\n"
        f"\n"
        f"---\n"
    )

    sections = [banner]

    if entry_content:
        sections.append(f"\n{entry_content}\n")

    for slug in sorted(general_contents.keys()):
        sections.append(f"\n---\n\n## `_{slug}-rules`\n\n{general_contents[slug]}\n")

    if project_contents:
        sections.append(
            "\n---\n\n## Project rules\n\n"
            "The rule files below ship with active projects. Each applies only\n"
            "when the session is working in that project's domain (e.g. editing\n"
            "code in the project's repo, running its CI, deploying its\n"
            "artifacts). When working outside any project's domain, treat these\n"
            "sections as reference rather than active discipline.\n"
        )
        for prefixed_slug in sorted(project_contents.keys()):
            project = rule_provenance.get(prefixed_slug, "unknown-project")
            sections.append(
                f"\n---\n\n### `{prefixed_slug}` (project: `{project}`)\n\n"
                f"{project_contents[prefixed_slug]}\n"
            )

    md_bundle = "".join(sections)
    (DIST / "RULES_BUNDLE.md").write_text(md_bundle)

    # ---- JSON bundle ----

    merged_rules: dict[str, str] = {**general_contents, **project_contents}
    json_bundle = {
        "version": version,
        "source_commit": commit,
        "built_at": built_at,
        "rule_count": len(merged_rules),
        "general_rule_count": len(general_contents),
        "project_rule_count": len(project_contents),
        "rules": merged_rules,
        "provenance": provenance,
    }
    if entry_content:
        json_bundle["entry_point"] = entry_content

    (DIST / "RULES_BUNDLE.json").write_text(json.dumps(json_bundle, indent=2) + "\n")

    project_suffix = f" (+{len(project_contents)} project)" if project_contents else ""
    print(
        f"  Rules bundle: {len(general_contents)} general{project_suffix} rules, "
        f"{len(md_bundle)} chars"
    )
    print(f"  -> dist/RULES_BUNDLE.md")
    print(f"  -> dist/RULES_BUNDLE.json")


# ---------------------------------------------------------------------------
# Craft Agent enforcement artifact
# ---------------------------------------------------------------------------

# Gate definitions: maps gate ID → hook script, enforcement surface, blocking condition.
# This is the single source of truth; the generated manifest + settings derive from it.
CA_ENFORCEMENT_GATES = [
    {
        "id": "think-gate",
        "rule_source": "_definition-of-done-rules.md",
        "hook": "hooks/resolver/think-gate-guard.sh",
        "surface": "UserPromptSubmit",
        "blocking": True,
        "condition": "No design note registered before non-trivial work",
    },
    {
        "id": "investigate-gate",
        "rule_source": "_definition-of-done-rules.md",
        "hook": "hooks/resolver/investigate-gate-guard.sh",
        "surface": "UserPromptSubmit",
        "blocking": True,
        "condition": "Think gate exists but no investigation artifact",
    },
    {
        "id": "self-review",
        "rule_source": "_definition-of-done-rules.md",
        "hook": "hooks/git/self-review.sh",
        "surface": "native-git-pre-push",
        "blocking": True,
        "condition": "Push without Self-Review trailers",
    },
    {
        "id": "branch-guard",
        "rule_source": "_writing-code-rules.md",
        "hook": "hooks/git/branch-guard.sh",
        "surface": "native-git-pre-push",
        "blocking": True,
        "condition": "Commit to protected branch",
    },
]


def build_ca_enforcement() -> None:
    """Generate Craft Agent enforcement artifacts.

    Emits:
      dist/craft-agent/enforcement-manifest.json  -- gate definitions for auditability
      dist/craft-agent/settings-enforcement.json   -- hook settings fragment for merge
      dist/craft-agent/.githooks/pre-push           -- native git hook for push-time gates
    """
    ca_dist = DIST / "craft-agent"
    ca_dist.mkdir(parents=True, exist_ok=True)

    version = _get_version()
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT, text=True,
        ).strip()
    except Exception:
        commit = "unknown"

    # 1. Enforcement manifest — documents which gates block and why.
    manifest = {
        "version": version,
        "source_commit": commit,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "gates": CA_ENFORCEMENT_GATES,
    }
    (ca_dist / "enforcement-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )

    # 2. Settings enforcement fragment — the CA enforcement wrapper as a
    #    UserPromptSubmit hook.  The installer merges this into the workspace's
    #    .claude/settings.json.
    settings_fragment = {
        "_comment_": (
            "Generated by build.py for Craft Agent enforcement (#409). "
            "The ca-enforcement-gate.sh wrapper converts advisory gate output "
            "into blocking continue:false signals.  Merge into workspace "
            ".claude/settings.json — do not replace the full file."
        ),
        "hooks": {
            "UserPromptSubmit": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "/path/to/hooks/resolver/ca-enforcement-gate.sh",
                            "timeout": 15,
                        }
                    ]
                }
            ]
        },
        "env": {
            "CLAUDE_CA_ENFORCE": "1"
        },
    }
    (ca_dist / "settings-enforcement.json").write_text(
        json.dumps(settings_fragment, indent=2) + "\n"
    )

    # 3. Native git pre-push hook — calls push-time gates.
    githooks_dir = ca_dist / ".githooks"
    githooks_dir.mkdir(parents=True, exist_ok=True)

    push_gates = [g for g in CA_ENFORCEMENT_GATES if g["surface"] == "native-git-pre-push"]
    pre_push_lines = [
        "#!/usr/bin/env bash",
        "# Generated by build.py — do not edit manually.",
        "# Native git pre-push hook for Craft Agent enforcement.",
        "# Runs push-time gates that need to block in CA where PreToolUse exit 2",
        "# is advisory only.  Native git hooks exit 1 → push is rejected.",
        "#",
        "# Refs: #409",
        "",
        'set -euo pipefail',
        "",
        '# Resolve hooks directory relative to this script.',
        '# When installed: .githooks/pre-push → ../hooks/',
        'HOOKS_ROOT="$(cd "$(dirname "$0")/../hooks" && pwd 2>/dev/null || echo "")"',
        "",
        'if [[ -z "$HOOKS_ROOT" || ! -d "$HOOKS_ROOT" ]]; then',
        '    echo "pre-push: hooks/ directory not found, skipping enforcement" >&2',
        '    exit 0',
        'fi',
        "",
    ]

    for gate in push_gates:
        hook_path = gate["hook"]
        script_name = hook_path.split("/")[-1]
        gate_dir = "/".join(hook_path.split("/")[1:-1])
        pre_push_lines.extend([
            f'# Gate: {gate["id"]} — {gate["condition"]}',
            f'GATE_SCRIPT="$HOOKS_ROOT/{gate_dir}/{script_name}"',
            f'if [[ -x "$GATE_SCRIPT" ]]; then',
            f'    if ! bash "$GATE_SCRIPT" "$@" 2>/dev/null; then',
            f'        echo "pre-push: {gate["id"]} gate BLOCKED push" >&2',
            f'        exit 1',
            f'    fi',
            f'fi',
            "",
        ])

    pre_push_lines.append('exit 0')
    pre_push_content = "\n".join(pre_push_lines) + "\n"
    pre_push_path = githooks_dir / "pre-push"
    pre_push_path.write_text(pre_push_content)
    pre_push_path.chmod(0o755)

    print(f"  CA enforcement: {len(CA_ENFORCEMENT_GATES)} gates")
    print(f"    {sum(1 for g in CA_ENFORCEMENT_GATES if g['surface'] == 'UserPromptSubmit')} UserPromptSubmit (continue:false)")
    print(f"    {len(push_gates)} native git pre-push")
    print(f"  -> dist/craft-agent/enforcement-manifest.json")
    print(f"  -> dist/craft-agent/settings-enforcement.json")
    print(f"  -> dist/craft-agent/.githooks/pre-push")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def strip_craft_incompatible_keys(text: str) -> str:
    """Remove frontmatter keys that Craft Agent misinterprets.

    Matches electinfo_claude_skills/scripts/build.py pattern.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text
    result = [lines[0]]
    closed = False
    for line in lines[1:]:
        if not closed:
            if line.strip() == "---":
                closed = True
                result.append(line)
                continue
            key = line.split(":")[0].strip() if ":" in line else ""
            if key in CRAFT_INCOMPATIBLE_KEYS:
                continue
        result.append(line)
    return "".join(result)


def _merge_ca_enforcement_settings(src: Path, dst: Path) -> None:
    """Merge CA enforcement hook into existing .claude/settings.json.

    Adds the ca-enforcement-gate.sh UserPromptSubmit entry and the
    CLAUDE_CA_ENFORCE env var.  Preserves all operator-owned settings.
    If the enforcement hook is already present (by command path match),
    it is replaced with the build-generated version.
    """
    try:
        existing = json.loads(dst.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        existing = {}

    generated = json.loads(src.read_text())

    if "hooks" not in existing:
        existing["hooks"] = {}
    if "UserPromptSubmit" not in existing["hooks"]:
        existing["hooks"]["UserPromptSubmit"] = []

    # The generated fragment has one UserPromptSubmit entry with the
    # enforcement wrapper.  Resolve the path placeholder.
    ws_root = dst.parent.parent  # .claude/settings.json → workspace root
    gen_hooks = generated.get("hooks", {}).get("UserPromptSubmit", [])
    for entry in gen_hooks:
        for hook in entry.get("hooks", []):
            if "command" in hook:
                hook["command"] = hook["command"].replace(
                    "/path/to", str(ws_root)
                )

    # Remove any existing ca-enforcement-gate entry (idempotent reinstall).
    for ups_group in existing["hooks"]["UserPromptSubmit"]:
        if "hooks" in ups_group:
            ups_group["hooks"] = [
                h for h in ups_group["hooks"]
                if "ca-enforcement-gate" not in h.get("command", "")
            ]

    # Append the enforcement entry.
    existing["hooks"]["UserPromptSubmit"].extend(gen_hooks)

    # Set the enforcement env var.
    if "env" not in existing:
        existing["env"] = {}
    existing["env"]["CLAUDE_CA_ENFORCE"] = "1"

    dst.write_text(json.dumps(existing, indent=2) + "\n")
    print(f"  Merged CA enforcement into {dst}")


def deploy_to_workspace() -> None:
    """Sync flat layout to the Craft Agent workspace.

    Copies dist/flat/skills/ → ~/.craft-agent/workspaces/my-workspace/skills/,
    dist/flat/hooks/ → ~/.craft-agent/workspaces/my-workspace/hooks/,
    and RESOLVER.md → ~/.craft-agent/workspaces/my-workspace/RESOLVER.md.
    Strips Craft-incompatible frontmatter keys from .md files during copy.
    """
    ws_skills = CRAFT_WORKSPACE / "skills"
    flat_skills = DIST / "flat" / "skills"
    if not flat_skills.exists():
        raise BuildError("dist/flat/skills/ does not exist — run build first")
    if not CRAFT_WORKSPACE.exists():
        print(f"  Workspace not found at {CRAFT_WORKSPACE}, skipping deploy")
        return
    preserved_root_files: dict[str, str] = {}
    if ws_skills.exists():
        for f in ws_skills.iterdir():
            if f.is_file() and f.suffix.lower() == ".md":
                preserved_root_files[f.name] = f.read_text()
        shutil.rmtree(ws_skills)

    stripped_count = 0
    for src_path in flat_skills.rglob("*"):
        rel = src_path.relative_to(flat_skills)
        dst_path = ws_skills / rel
        if src_path.is_dir():
            dst_path.mkdir(parents=True, exist_ok=True)
            continue
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        if src_path.suffix.lower() == ".md":
            original = src_path.read_text()
            processed = strip_craft_incompatible_keys(original)
            dst_path.write_text(processed)
            if processed != original:
                stripped_count += 1
        else:
            shutil.copy2(src_path, dst_path)

    for name, content in preserved_root_files.items():
        target = ws_skills / name
        if not target.exists():
            target.write_text(content)

    resolver_src = REPO_ROOT / "RESOLVER.md"
    if resolver_src.exists():
        original = resolver_src.read_text()
        (CRAFT_WORKSPACE / "RESOLVER.md").write_text(
            strip_craft_incompatible_keys(original)
        )

    # Sync hooks/ to workspace (closes #261: hooks were missing from deploy).
    src_hooks = DIST / "flat" / "hooks"
    ws_hooks = CRAFT_WORKSPACE / "hooks"
    if src_hooks.exists():
        if ws_hooks.exists():
            shutil.rmtree(ws_hooks)
        shutil.copytree(src_hooks, ws_hooks)
        hooks_count = sum(1 for _ in ws_hooks.rglob("*.sh"))
        print(f"  Synced {hooks_count} hook script(s) to {ws_hooks}/")

    # Deploy rules bundle to workspace.
    bundle_md = DIST / "RULES_BUNDLE.md"
    if bundle_md.exists():
        bundle_dst = CRAFT_WORKSPACE / "RULES_BUNDLE.md"
        shutil.copy2(bundle_md, bundle_dst)
        print(f"  Copied RULES_BUNDLE.md to {CRAFT_WORKSPACE}/")

        # Craft Agent auto-injects CLAUDE.md / AGENTS.md content from cwd and
        # its subdirectories on every session start. Wire the bundle into that
        # mechanism by symlinking CLAUDE.md -> RULES_BUNDLE.md at the workspace
        # root. Sessions whose cwd is set to the workspace root (via Settings
        # -> Workspace Settings -> Default Working Directory) pick up the
        # bundle automatically. Empirically verified 2026-06-07 against a
        # probe session reporting `# claudeMd` content injection in its
        # initial system prompt.
        claudemd_dst = CRAFT_WORKSPACE / "CLAUDE.md"
        if claudemd_dst.is_symlink() or not claudemd_dst.exists():
            # Safe to (re)create: either it's already our symlink, or no file
            # exists at that path. Replace to point at the freshly deployed bundle.
            if claudemd_dst.is_symlink():
                claudemd_dst.unlink()
            claudemd_dst.symlink_to("RULES_BUNDLE.md")
            print(f"  Symlinked CLAUDE.md -> RULES_BUNDLE.md (CA auto-mount)")
        else:
            # A non-symlink CLAUDE.md already exists. Don't clobber operator
            # content; surface the situation and let them resolve it.
            print(
                f"  [warn] {claudemd_dst} exists as a regular file; not overwriting.\n"
                f"         To wire the bundle into CA auto-inject, either rename your\n"
                f"         existing CLAUDE.md and re-run --deploy, or append the\n"
                f"         contents of RULES_BUNDLE.md to your CLAUDE.md manually."
            )

    # Deploy CA enforcement artifacts.
    ca_dist = DIST / "craft-agent"
    if ca_dist.exists():
        # Copy enforcement manifest for auditability.
        manifest_src = ca_dist / "enforcement-manifest.json"
        if manifest_src.exists():
            shutil.copy2(manifest_src, CRAFT_WORKSPACE / "enforcement-manifest.json")

        # Install native git hooks (.githooks/pre-push).
        githooks_src = ca_dist / ".githooks"
        ws_githooks = CRAFT_WORKSPACE / ".githooks"
        if githooks_src.exists():
            ws_githooks.mkdir(parents=True, exist_ok=True)
            for hook_file in githooks_src.iterdir():
                dst = ws_githooks / hook_file.name
                shutil.copy2(hook_file, dst)
                dst.chmod(0o755)
            print(f"  Installed {sum(1 for _ in githooks_src.iterdir())} native git hook(s) to {ws_githooks}/")

        # Merge CA enforcement settings into .claude/settings.json.
        settings_src = ca_dist / "settings-enforcement.json"
        settings_dst = CRAFT_WORKSPACE / ".claude" / "settings.json"
        if settings_src.exists() and settings_dst.exists():
            _merge_ca_enforcement_settings(settings_src, settings_dst)

    print(f"  Deployed to {CRAFT_WORKSPACE}/ ({stripped_count} files stripped)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate tokens; do not write output")
    parser.add_argument("--layout", choices=("nested", "flat", "both"), default="both")
    parser.add_argument("--deploy", action="store_true", help="After building, sync flat layout to Craft Agent workspace")
    args = parser.parse_args()

    # Phase 1: Validate project manifests (repo uniqueness, required fields, status).
    print("Validating project manifests...")
    try:
        active_projects = validate_project_manifests(SOURCE_PROJECTS)
    except BuildError as e:
        print(f"BUILD ERROR: {e}", file=sys.stderr)
        return 1
    print(f"  {len(active_projects)} active project(s)")

    # Phase 1b: Validate solutions catalog (#421).
    print("Validating solutions catalog...")
    try:
        solutions_count = validate_solutions(SOURCE_SOLUTIONS)
    except BuildError as e:
        print(f"BUILD ERROR: {e}", file=sys.stderr)
        return 1
    print(f"  {solutions_count} solution(s) validated")

    # Phase 2: Discover general skills and rules.
    print(f"Source: {SOURCE_SKILLS}")
    skills_src = find_skills(SOURCE_SKILLS)
    rules_src = find_rules(SOURCE_SKILLS)

    # Phase 3: Discover project skills and rules (active projects only).
    project_skills_src, skill_provenance = find_project_skills(SOURCE_PROJECTS, active_projects)
    project_rules_src, rule_provenance = find_project_rules(SOURCE_PROJECTS, active_projects)
    print(
        f"Discovered {len(skills_src)} leaf skills, {len(rules_src)} rules, "
        f"{len(project_skills_src)} project skills, {len(project_rules_src)} project rules"
    )

    # Phase 4: Early collision check.
    overlap = set(skills_src) & set(project_skills_src)
    if overlap:
        print(f"BUILD ERROR: project skill slug collides with general skill: {sorted(overlap)}", file=sys.stderr)
        return 1
    overlap = set(rules_src) & set(project_rules_src)
    if overlap:
        print(f"BUILD ERROR: project rule slug collides with general rule: {sorted(overlap)}", file=sys.stderr)
        return 1

    if args.check:
        import tempfile
        global DIST
        DIST = Path(tempfile.mkdtemp(prefix="claude-configs-build-check-"))
        try:
            for layout in ("nested", "flat"):
                build_layout(
                    layout, skills_src, rules_src,
                    project_skills_src, project_rules_src,
                    skill_provenance, active_projects,
                )
            warn_unknown()
            print("Build check complete.")
            return 0
        except BuildError as e:
            print(f"BUILD ERROR: {e}", file=sys.stderr)
            return 1
        finally:
            shutil.rmtree(DIST, ignore_errors=True)

    layouts = ("nested", "flat") if args.layout == "both" else (args.layout,)
    for layout in layouts:
        print(f"\nBuilding {layout}...")
        skill_out_paths = build_layout(
            layout, skills_src, rules_src,
            project_skills_src, project_rules_src,
            skill_provenance, active_projects,
        )
        write_build_info(layout, {**skills_src, **project_skills_src}, skill_out_paths, active_projects)
        print(f"  → dist/{layout}/")

    warn_unknown()

    print("\nBuilding rules bundle...")
    build_rules_bundle(rules_src, project_rules_src, rule_provenance)

    print("\nBuilding CA enforcement artifacts...")
    build_ca_enforcement()

    print(f"\nDone. Output: {DIST}/")

    if args.deploy:
        print("\nDeploying to Craft Agent workspace...")
        if "flat" not in layouts:
            print("  Building flat layout for deploy...")
            build_layout(
                "flat", skills_src, rules_src,
                project_skills_src, project_rules_src,
                skill_provenance, active_projects,
            )
        deploy_to_workspace()

    return 0


def warn_unknown() -> None:
    """Print a summary of unknown slugs (forward-looking references)."""
    if UNKNOWN_SKILLS or UNKNOWN_RULES:
        print("\n--- Forward-looking references (placeholders, not errors) ---")
        for path, slugs in sorted(UNKNOWN_SKILLS.items()):
            for slug in sorted(slugs):
                print(f"  {path}: [skill:{slug}]")
        for path, slugs in sorted(UNKNOWN_RULES.items()):
            for slug in sorted(slugs):
                print(f"  {path}: [rule:{slug}]")


if __name__ == "__main__":
    sys.exit(main())
