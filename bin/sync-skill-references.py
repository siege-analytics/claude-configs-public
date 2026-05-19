#!/usr/bin/env python3
"""Convert Markdown links targeting SKILL.md files into [skill:slug] tokens.

Run from any state to normalize cross-references back to token form. Used for the
one-time migration AND as an ongoing sync tool — contributors who slip into
path-form links by habit get caught and corrected.

Usage:
    python bin/sync-skill-references.py             # rewrite files in place
    python bin/sync-skill-references.py --check     # exit non-zero if any path-form refs found
    python bin/sync-skill-references.py --dry-run   # show what would change without writing

In CI: run with --check on every PR. Failure means a contributor used a path-form
reference instead of a token; they should re-run the script locally and re-push.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_SKILLS = REPO_ROOT / "skills"

# Match Markdown links to SKILL.md files. The captured slug is the immediate parent dir.
# Examples this matches:
#   [text](../../coding/code-review/SKILL.md)
#   [text](coding/code-review/SKILL.md)
#   [text](../shelves/engineering-principles/clean-code/SKILL.md)
SKILL_LINK = re.compile(
    r"""
    \[(?P<text>[^\]]+)\]                               # link text
    \(                                                 # opening paren
        (?P<prefix>(?:\.\./)*[^()]*?)                  # any prefix (relative path components)
        (?P<slug>[a-z0-9][a-z0-9-]*)                   # the skill slug (immediate parent dir)
        /SKILL\.md                                     # SKILL.md
        (?:\#[^)]*)?                                   # optional anchor
    \)
    """,
    re.VERBOSE,
)

# Match Markdown links to _*-rules.md files at skills root.
# Examples:
#   [text](../../_output-rules.md)
#   [text](_data-trust-rules.md)
RULE_LINK = re.compile(
    r"""
    \[(?P<text>[^\]]+)\]
    \(
        (?P<prefix>(?:\.\./)*[^()]*?)
        _(?P<slug>[a-z][a-z-]*?)-rules\.md
        (?:\#[^)]*)?
    \)
    """,
    re.VERBOSE,
)


def find_markdown_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.md") if "dist" not in p.parts]


def convert_skill_links(content: str) -> tuple[str, int]:
    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        slug = match.group("slug")
        # Don't convert if the link target is the source's own SKILL.md (no slug to extract)
        # — but our regex ensures `slug` is the immediate parent dir, so we're safe.
        count += 1
        return f"[skill:{slug}]"

    new_content = SKILL_LINK.sub(repl, content)
    return new_content, count


def convert_rule_links(content: str) -> tuple[str, int]:
    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        slug = match.group("slug")
        count += 1
        return f"[rule:{slug}]"

    new_content = RULE_LINK.sub(repl, content)
    return new_content, count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Exit 1 if any path-form refs would be converted")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    args = parser.parse_args()

    files = find_markdown_files(SOURCE_SKILLS)
    total_skill_conversions = 0
    total_rule_conversions = 0
    changed_files: list[Path] = []

    for path in files:
        original = path.read_text()
        converted = original
        converted, n_skill = convert_skill_links(converted)
        converted, n_rule = convert_rule_links(converted)
        if converted != original:
            changed_files.append(path)
            total_skill_conversions += n_skill
            total_rule_conversions += n_rule
            if args.dry_run or args.check:
                print(f"Would change: {path.relative_to(REPO_ROOT)} ({n_skill} skill, {n_rule} rule)")
            else:
                path.write_text(converted)
                print(f"Updated: {path.relative_to(REPO_ROOT)} ({n_skill} skill, {n_rule} rule)")

    print(
        f"\nSummary: {len(changed_files)} files, "
        f"{total_skill_conversions} skill refs, "
        f"{total_rule_conversions} rule refs converted"
    )

    if args.check and changed_files:
        print(
            "\nERROR: Path-form references found. Run `python bin/sync-skill-references.py` "
            "locally and commit the result.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
