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


def main():
    raw = sys.stdin.read()
    if not raw:
        return 1
    try:
        resolved = os.path.realpath(raw)
    except (ValueError, OSError):
        return 1
    if not resolved:
        return 1
    sys.stdout.write(resolved)
    return 0


if __name__ == "__main__":
    sys.exit(main())
