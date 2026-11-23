#!/usr/bin/env python3
"""Canonicalize a write target's path so the guard's scope filter sees one
string per file.

The ticket-propagation guard decides whether a path names a governed artifact.
Round 3 answered a bare-relative bypass by adding `case` arms, and round 4 then
found upper-case components and symlink aliases naming the same governed files.
Arms cannot close that class: the set of strings naming a given file is
unbounded. Resolving first collapses it.

Reads the path on stdin, writes the resolved absolute path on stdout. Exits
non-zero on any input the resolver cannot reduce to a single filesystem name,
so the caller can fail closed rather than fall through with an empty path.

The target need not exist: this runs before the write, and os.path.realpath
resolves the symlinks that do exist on the way down.
"""

import os
import sys


def fold_existing_case(path: str) -> str:
    """Resolve existing path components case-insensitively.

    The write target may not exist yet, but governed directories such as
    `plans/` and `docs/investigations/` do. On case-sensitive CI filesystems,
    `PLANS/foo.md` otherwise remains `PLANS/foo.md` and misses a lower-case
    scope filter even though the operator-visible path names the same governed
    category.
    """
    absolute = os.path.abspath(path)
    drive, rest = os.path.splitdrive(absolute)
    parts = [p for p in rest.split(os.sep) if p]
    current = drive + os.sep
    for part in parts:
        candidate = os.path.join(current, part)
        if os.path.exists(candidate):
            current = candidate
            continue
        try:
            entries = os.listdir(current)
        except OSError:
            current = candidate
            continue
        lowered = part.lower()
        match = next((entry for entry in entries if entry.lower() == lowered), None)
        current = os.path.join(current, match if match is not None else part)
    return current


def main():
    raw = sys.stdin.read()
    if not raw:
        return 1
    try:
        resolved = os.path.realpath(fold_existing_case(raw))
    except (ValueError, OSError):
        return 1
    if not resolved:
        return 1
    sys.stdout.write(resolved)
    return 0


if __name__ == "__main__":
    sys.exit(main())
