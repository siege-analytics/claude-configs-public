#!/usr/bin/env python3
"""Promote CHANGELOG.md [Unreleased] to a versioned section at tag time.

The release workflow cuts release notes from CHANGELOG.md. Before #633, the
[Unreleased] block was never promoted to a versioned section at tag time,
so every auto-cut release read from the same growing [Unreleased] block:
each release body then described its own changes plus everyone else's since
the last manual backfill. See #625 (one-time manual backfill) and #633
(the same regression reappearing on every subsequent auto-cut).

This script mutates CHANGELOG.md: it moves the current [Unreleased] content
under a new [<version>] --- <date> header, then resets [Unreleased] to a
placeholder. Run with --check to dry-run and report what the promotion would
do without modifying the file. Run with --version and --date to promote.

Idempotent: if [<version>] already exists, do nothing and exit 0. If
[Unreleased] is empty (no meaningful content), do nothing and exit 0 --
there is nothing to promote, and creating an empty versioned section
would poison future promotions.

Exit codes:
  0  Promoted successfully, or nothing to do (idempotent success).
  1  CHANGELOG.md is malformed (no [Unreleased] header found at all).
  2  Argument error.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path


HEADER_RE = re.compile(r"^## \[(?P<name>[^\]]+)\](?P<rest>.*)$")


def find_section_bounds(lines: list[str], name: str) -> tuple[int, int] | None:
    """Return (start_line, end_line_exclusive) of the section headed by
    `## [<name>]`. Returns None if not found."""
    start = None
    for i, line in enumerate(lines):
        m = HEADER_RE.match(line)
        if m and m.group("name") == name:
            start = i
            continue
        if start is not None and HEADER_RE.match(line):
            return (start, i)
    if start is not None:
        return (start, len(lines))
    return None


def section_body_meaningful(lines: list[str], bounds: tuple[int, int]) -> bool:
    """A section is meaningful if any body line has non-whitespace non-comment
    content."""
    start, end = bounds
    for line in lines[start + 1:end]:
        stripped = line.strip()
        if stripped and not stripped.startswith("<!--"):
            return True
    return False


def promote(text: str, version: str, when: str) -> tuple[str, str]:
    """Return (new_text, action) where action is one of:
        promoted        — Unreleased content moved under [<version>]
        already-exists  — [<version>] already exists; no-op
        empty-unreleased — nothing to promote; no-op
        no-unreleased    — CHANGELOG has no [Unreleased] header at all
    """
    lines = text.splitlines(keepends=False)

    # Idempotent no-op if [<version>] already exists
    if find_section_bounds(lines, version) is not None:
        return text, "already-exists"

    unreleased = find_section_bounds(lines, "Unreleased")
    if unreleased is None:
        return text, "no-unreleased"

    if not section_body_meaningful(lines, unreleased):
        return text, "empty-unreleased"

    ur_start, ur_end = unreleased
    body_lines = lines[ur_start + 1:ur_end]
    # Strip trailing empty lines from the body to avoid stray blanks
    while body_lines and not body_lines[-1].strip():
        body_lines.pop()

    new_unreleased = [
        f"## [Unreleased]",
        "",
        "<!-- next release entries go here -->",
        "",
    ]
    new_version_section = [
        f"## [{version}] --- {when}",
        "",
        *body_lines,
        "",
    ]

    new_lines = (
        lines[:ur_start]
        + new_unreleased
        + new_version_section
        + lines[ur_end:]
    )
    result = "\n".join(new_lines)
    if not result.endswith("\n"):
        result += "\n"
    return result, "promoted"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--version", required=True,
                        help="Version to promote to (e.g. 3.5.21 or v3.5.21)")
    parser.add_argument("--date", default=None,
                        help="Release date (YYYY-MM-DD). Default: today (UTC).")
    parser.add_argument("--changelog", default="CHANGELOG.md")
    parser.add_argument("--check", action="store_true",
                        help="Dry-run: report action without modifying the file")
    args = parser.parse_args()

    version = args.version.removeprefix("v")
    when = args.date or date.today().isoformat()

    path = Path(args.changelog)
    if not path.is_file():
        print(f"ERROR: CHANGELOG not found: {path}", file=sys.stderr)
        return 2

    text = path.read_text()
    new_text, action = promote(text, version, when)

    if action == "no-unreleased":
        print(f"ERROR: {path} has no [Unreleased] header", file=sys.stderr)
        return 1

    if args.check:
        print(f"{action} (dry-run): {path} version=[{version}] date={when}")
        return 0

    if new_text != text:
        path.write_text(new_text)
    print(f"{action}: {path} version=[{version}] date={when}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
