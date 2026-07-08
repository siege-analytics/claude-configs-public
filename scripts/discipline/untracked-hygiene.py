#!/usr/bin/env python3
"""Inventory untracked workspace clutter without deleting anything.

This script is read-only. It classifies `git status --porcelain`
untracked paths so agents can separate known local/generated clutter from new
unexpected files. Use `--json` for machine-readable output.

Ref: claude-configs-public#617
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Entry:
    path: str
    category: str
    policy: str
    action: str


SPACE_COPY_RE = re.compile(r"(^|/)[^/]+ [0-9]+(\.[^/]+)?(/|$)")


def git_untracked(repo: Path) -> list[str]:
    out = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=repo,
        text=True,
    )
    paths: list[str] = []
    for line in out.splitlines():
        if line.startswith("?? "):
            paths.append(line[3:])
    return paths


def classify(path: str) -> Entry:
    normalized = path.strip('"')
    if normalized == ".idea" or normalized.startswith(".idea/"):
        return Entry(path, "IDE local config", "ignorable", "covered by .gitignore")
    if normalized.endswith(".pyc") or "/__pycache__/" in normalized or normalized.endswith("/__pycache__"):
        return Entry(path, "python cache", "ignorable", "covered by .gitignore")
    if normalized == "dist.stale" or normalized.startswith("dist.stale/"):
        return Entry(path, "stale generated output", "ignorable", "covered by .gitignore")
    if SPACE_COPY_RE.search(normalized):
        return Entry(path, "number-suffixed duplicate/copy", "review-before-delete", "inspect with --emit-delete-script")
    if normalized.startswith("plans/"):
        return Entry(path, "plan artifact", "review", "decide whether ticket artifact or local scratch")
    if normalized.startswith("skills/"):
        return Entry(path, "skill/rule tree", "review", "decide whether intentional new skill or local copy")
    if normalized.startswith("hooks/"):
        return Entry(path, "hook artifact", "review", "decide whether intentional hook or local copy")
    return Entry(path, "other", "review", "manual inspection required")


def shell_quote(path: str) -> str:
    return "'" + path.replace("'", "'\\''") + "'"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument(
        "--emit-delete-script",
        action="store_true",
        help="print a reviewed-by-human deletion script template for duplicate/copy paths only",
    )
    args = parser.parse_args()

    repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
    entries = [classify(p) for p in git_untracked(repo)]

    if args.json:
        print(json.dumps({"entries": [asdict(e) for e in entries]}, indent=2))
        return 0

    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry.category] = counts.get(entry.category, 0) + 1

    print(f"Untracked entries: {len(entries)}")
    for category, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        print(f"  {category}: {count}")

    print("\nDetails:")
    for entry in entries:
        print(f"  [{entry.policy}] {entry.category}: {entry.path} -- {entry.action}")

    if args.emit_delete_script:
        print("\n# Dry-run deletion template for number-suffixed duplicate/copy paths only.")
        print("# Review every path before removing the leading 'echo'.")
        for entry in entries:
            if entry.category == "number-suffixed duplicate/copy":
                print(f"echo rm -rf -- {shell_quote(entry.path)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
