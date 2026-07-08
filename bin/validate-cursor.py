#!/usr/bin/env python3
"""Validate dist/cursor/ consumer package.

Usage:
    python3 bin/validate-cursor.py dist/cursor/

Checks:
    1. build-info.json skill_count matches skill directories
    2. Each SKILL.md has name + description frontmatter
    3. No loose rule files at skills/ root
    4. RESOLVER.md and RULES_BUNDLE.{md,json} present
    5. install-cursor.sh exists and is executable
    6. cursor/CURSOR.md and templates/ present
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

LOOSE_ROOT_PATTERN = re.compile(r"^(_[a-z0-9-]+-rules\.md|RULES\.md|_coverage\.md)$")


def parse_frontmatter(content: str) -> dict[str, str]:
    if not content.startswith("---\n"):
        return {}
    end = content.find("\n---\n", 4)
    if end == -1:
        return {}
    block = content[4:end]
    result: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip().strip('"').strip("'")
    return result


def validate(package_dir: Path) -> int:
    errors: list[str] = []
    warnings: list[str] = []

    skills_dir = package_dir / "skills"
    if not skills_dir.is_dir():
        errors.append(f"skills/ directory missing in {package_dir}")
        return 1

    skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]
    skill_count = len(skill_dirs)

    build_info_path = package_dir / "build-info.json"
    if build_info_path.exists():
        build_info = json.loads(build_info_path.read_text())
        declared = build_info.get("skill_count")
        if declared != skill_count:
            errors.append(
                f"build-info.json skill_count={declared} but found {skill_count} directories"
            )
    else:
        warnings.append("build-info.json missing")

    loose_at_root = [
        f.name for f in skills_dir.iterdir()
        if f.is_file() and LOOSE_ROOT_PATTERN.match(f.name)
    ]
    if loose_at_root:
        errors.append(f"loose rule files at skills root: {sorted(loose_at_root)}")

    for skill_dir in skill_dirs:
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            warnings.append(f"{skill_dir.name}/: no SKILL.md (directory-only router?)")
            continue
        fm = parse_frontmatter(skill_md.read_text())
        if not fm.get("name"):
            errors.append(f"{skill_dir.name}/SKILL.md: missing 'name' frontmatter")
        if not fm.get("description"):
            errors.append(f"{skill_dir.name}/SKILL.md: missing 'description' frontmatter")

    for required in ("RESOLVER.md", "RULES_BUNDLE.md", "RULES_BUNDLE.json"):
        if not (package_dir / required).exists():
            errors.append(f"missing {required}")

    install_script = package_dir / "bin" / "install-cursor.sh"
    if not install_script.exists():
        install_script = package_dir / "install-cursor.sh"
    if not install_script.exists():
        errors.append("install-cursor.sh not found in package")
    elif not install_script.stat().st_mode & 0o111:
        warnings.append("install-cursor.sh is not executable")

    if not (package_dir / "cursor" / "CURSOR.md").exists():
        cursor_doc = package_dir / "CURSOR.md"
        if cursor_doc.exists():
            warnings.append("CURSOR.md at package root but not cursor/CURSOR.md")
        else:
            errors.append("cursor/CURSOR.md missing")

    templates = package_dir / "cursor" / "templates"
    if not templates.is_dir():
        errors.append("cursor/templates/ missing")
    else:
        for tpl in ("user-rule.md", "project-rule.mdc"):
            if not (templates / tpl).exists():
                errors.append(f"cursor/templates/{tpl} missing")

    print(f"Validating {package_dir}/")
    print(f"  skill directories: {skill_count}")
    print(f"  SKILL.md files: {sum(1 for _ in skills_dir.rglob('SKILL.md'))}")

    for w in warnings:
        print(f"  WARN: {w}")

    if errors:
        print(f"FAIL: {len(errors)} error(s)", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print("PASS: cursor package valid")
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 bin/validate-cursor.py dist/cursor/", file=sys.stderr)
        return 2
    package_dir = Path(sys.argv[1])
    if not package_dir.is_dir():
        print(f"FAIL: {package_dir} is not a directory", file=sys.stderr)
        return 1
    return validate(package_dir)


if __name__ == "__main__":
    sys.exit(main())
