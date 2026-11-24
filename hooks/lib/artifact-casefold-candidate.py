#!/usr/bin/env python3
"""Print a path with only governed artifact directory components case-folded.

This preserves case-sensitive parent directories (for example mktemp names on
Linux) while letting hooks recognize paths like PLANS/a.md and
Docs/Investigations/a.md as names for the lower-case governed artifact surface.
"""

import os
import sys

path = sys.stdin.read()
if not path:
    sys.exit(0)

sep = os.sep
absolute = path.startswith(sep)
parts = path.split(sep)
if absolute:
    parts = parts[1:]

changed = False
out = list(parts)
for idx, part in enumerate(parts):
    if part.lower() == "plans" and part != "plans":
        out[idx] = "plans"
        changed = True
    if idx + 1 < len(parts) and part.lower() == "docs" and parts[idx + 1].lower() == "investigations":
        if out[idx] != "docs" or out[idx + 1] != "investigations":
            out[idx] = "docs"
            out[idx + 1] = "investigations"
            changed = True

if not changed:
    sys.exit(0)

candidate = sep.join(out)
if absolute:
    candidate = sep + candidate
sys.stdout.write(candidate)
