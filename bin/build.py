#!/usr/bin/env python3
"""Build dist/nested/ and dist/flat/ from skills/ source.

Resolves [skill:slug] and [rule:slug] tokens to layout-appropriate paths.
Generates RESOLVER.md from RESOLVER.template.md for each layout.
Validates that every token references an existing skill/rule.
Validates project manifests: required frontmatter, repo uniqueness, status lifecycle.

Usage:
    python bin/build.py            # build both layouts
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
DIST = REPO_ROOT / "dist"

CRAFT_WORKSPACE = Path.home() / ".craft-agent" / "workspaces" / "my-workspace"

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
# Skill and rule discovery
# ---------------------------------------------------------------------------

def find_skills(source: Path) -> dict[str, Path]:
    """Walk source/, return {slug: source_dir_relative_to_skills} for every SKILL.md.

    Includes both leaf skills AND routers (skills that have child SKILL.md files). The
    distinction matters at runtime (routers dispatch; leaves act) but not at build time
    (both need slug-token resolution). Slugs must be globally unique.
    """
    skills: dict[str, Path] = {}
    for skill_md in source.rglob("SKILL.md"):
        skill_dir = skill_md.parent
        slug = skill_dir.name
        if slug in skills:
            raise BuildError(
                f"Slug collision on '{slug}':\n"
                f"  {skills[slug]}\n"
                f"  {skill_dir.relative_to(source)}\n"
                f"Slugs must be globally unique across categories."
            )
        skills[slug] = skill_dir.relative_to(source)
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
# Entry point
# ---------------------------------------------------------------------------

def deploy_to_workspace() -> None:
    """Sync flat layout to the Craft Agent workspace.

    Copies dist/flat/skills/ → ~/.craft-agent/workspaces/my-workspace/skills/
    and RESOLVER.md → ~/.craft-agent/workspaces/my-workspace/RESOLVER.md.
    """
    ws_skills = CRAFT_WORKSPACE / "skills"
    flat_skills = DIST / "flat" / "skills"
    if not flat_skills.exists():
        raise BuildError("dist/flat/skills/ does not exist — run build first")
    if not CRAFT_WORKSPACE.exists():
        print(f"  Workspace not found at {CRAFT_WORKSPACE}, skipping deploy")
        return
    if ws_skills.exists():
        shutil.rmtree(ws_skills)
    shutil.copytree(flat_skills, ws_skills)
    resolver_src = REPO_ROOT / "RESOLVER.md"
    if resolver_src.exists():
        shutil.copy2(resolver_src, CRAFT_WORKSPACE / "RESOLVER.md")
    print(f"  Deployed to {CRAFT_WORKSPACE}/")


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
