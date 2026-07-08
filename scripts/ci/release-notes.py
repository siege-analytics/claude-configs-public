#!/usr/bin/env python3
"""Generate release notes from CHANGELOG.md and fail on empty entries.

Usage:
  release-notes.py --version 3.5.19 --out /tmp/release-notes.md
  release-notes.py --check --version 3.5.19

If CHANGELOG.md already has a section for the version, that section is used.
Otherwise a non-empty [Unreleased] section is promoted for release-note text.
The script does not edit CHANGELOG.md.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

HEADER_RE = re.compile(r"^## \[(?P<name>[^\]]+)\]")


def sections(text: str) -> dict[str, str]:
    lines = text.splitlines()
    found: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        match = HEADER_RE.match(line)
        if match:
            current = match.group("name")
            found[current] = []
            continue
        if current is not None:
            found[current].append(line)
    return {key: "\n".join(value).strip() for key, value in found.items()}


def meaningful(body: str) -> bool:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("<!--"):
            return True
    return False


def notes_for(version: str, changelog: Path) -> str:
    data = sections(changelog.read_text())
    body = data.get(version, "")
    source = version
    if not meaningful(body):
        body = data.get("Unreleased", "")
        source = "Unreleased"
    if not meaningful(body):
        raise SystemExit(
            f"CHANGELOG.md has no non-empty [{version}] section and no non-empty [Unreleased] section"
        )
    return f"Release v{version}\n\nSource: CHANGELOG.md [{source}]\n\n{body}\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--changelog", default="CHANGELOG.md")
    parser.add_argument("--out", default="")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    notes = notes_for(args.version.removeprefix("v"), Path(args.changelog))
    if args.out:
        Path(args.out).write_text(notes)
    if not args.check:
        print(notes, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
