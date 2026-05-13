#!/usr/bin/env python3
"""Build dist/nested/ and dist/flat/ from skills/ source.

Resolves [skill:slug] and [rule:slug] tokens to layout-appropriate paths.
Generates RESOLVER.md from RESOLVER.template.md for each layout.
Validates that every token references an existing skill/rule.

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
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_SKILLS = REPO_ROOT / "skills"
DIST = REPO_ROOT / "dist"

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

# Rules files at skills/ root
RULE_PATTERN = re.compile(r"^_(?P<slug>[a-z-]+)-rules\.md$")

# Token patterns
SKILL_TOKEN = re.compile(r"\[skill:(?P<slug>[a-z0-9-]+)\]")
RULE_TOKEN = re.compile(r"\[rule:(?P<slug>[a-z-]+)\]")


class BuildError(Exception):
    pass


# Track unknown slug references for warnings (per build run)
UNKNOWN_SKILLS: dict[str, set[str]] = {}
UNKNOWN_RULES: dict[str, set[str]] = {}


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
            # Forward-looking reference: skill doesn't exist yet. Emit as inline code
            # with no link, with the convention that a literate reader sees it as a
            # placeholder and a build log records it.
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
        # Skip if any ancestor between src_dir and src is itself another skill (has SKILL.md)
        skip = False
        for ancestor in rel.parents:
            if ancestor == Path("."):
                continue
            if is_other_skill_dir(src_dir / ancestor):
                skip = True
                break
        if skip:
            continue
        # Don't skip the src_dir's own root (its SKILL.md is what we want to copy)
        # Also skip if the src itself IS another skill's directory (and not the root)
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


def build_layout(layout: str, skills_src: dict[str, Path], rules_src: dict[str, Path]) -> dict[str, str]:
    """Build a single layout. Returns {slug: output-path-from-dist-root} for skills."""
    out_root = DIST / layout / "skills"
    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    # Compute output paths per layout
    if layout == "nested":
        # Mirror source layout: coding/code-review/, git-workflow/commit/, etc.
        skill_out_paths = {slug: str(src) for slug, src in skills_src.items()}
    elif layout == "flat":
        # Leaves flatten to skills/<slug>/. Routers stay nested (they own a category
        # subtree). Shelves stay nested entirely (per the design decision: keep
        # shelves consistent across layouts; book skills are library content, not
        # individual slash commands).
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

    rule_out_paths = {slug: str(src) for slug, src in rules_src.items()}

    # Copy skills with token resolution
    for slug, src_rel in skills_src.items():
        src_dir = SOURCE_SKILLS / src_rel
        dst_dir = out_root / skill_out_paths[slug]
        copy_skill_dir(src_dir, dst_dir, layout, skill_out_paths, rule_out_paths, skill_out_paths[slug])

    # Copy rules with token resolution
    for slug, rule_rel in rules_src.items():
        src = SOURCE_SKILLS / rule_rel
        dst = out_root / rule_rel
        write_resolved(src, dst, layout, skill_out_paths, rule_out_paths, rule_rel)

    # Generate RESOLVER.md from RESOLVER.template.md
    template = SOURCE_SKILLS / "RESOLVER.template.md"
    if template.exists():
        write_resolved(template, out_root / "RESOLVER.md", layout, skill_out_paths, rule_out_paths, Path("RESOLVER.md"))

    # Copy entry-point and matrix files at skills/ root (added v2.0.0; not matched by _*-rules.md pattern).
    # RULES.md is the human-facing entry point; _coverage.md is the queryable failure-mode matrix.
    # Both go through token resolution since they reference [skill:X] and [rule:X] tokens.
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


def write_build_info(layout: str, skills_src: dict[str, Path], skill_out_paths: dict[str, str]) -> None:
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
    }
    (DIST / layout / "build-info.json").write_text(json.dumps(info, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate tokens; do not write output")
    parser.add_argument("--layout", choices=("nested", "flat", "both"), default="both")
    args = parser.parse_args()

    print(f"Source: {SOURCE_SKILLS}")
    skills_src = find_skills(SOURCE_SKILLS)
    rules_src = find_rules(SOURCE_SKILLS)
    print(f"Discovered {len(skills_src)} leaf skills, {len(rules_src)} rules")

    if args.check:
        # Build to a tmp dir to validate tokens, then discard
        import tempfile
        global DIST
        DIST = Path(tempfile.mkdtemp(prefix="claude-configs-build-check-"))
        try:
            for layout in ("nested", "flat"):
                build_layout(layout, skills_src, rules_src)
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
        skill_out_paths = build_layout(layout, skills_src, rules_src)
        write_build_info(layout, skills_src, skill_out_paths)
        print(f"  → dist/{layout}/")

    warn_unknown()
    print(f"\nDone. Output: {DIST}/")
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
