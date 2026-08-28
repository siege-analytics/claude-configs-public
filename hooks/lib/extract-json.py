#!/usr/bin/env python3
"""Extract dotted-path values from JSON on stdin.

Usage: extract-json.py PATH [PATH ...]

Reads JSON from stdin, walks each dotted PATH in order, and prints the
first non-empty scalar value found. Prints empty string if none match.

Examples:
    echo "$INPUT" | extract-json.py tool_input.command
    echo "$INPUT" | extract-json.py tool_input.message tool_input.body tool_input.text

Exit code is always 0 unless stdin is unreadable, so callers can rely on
`VALUE=$(extract-json.py ...)` semantics that previously used
`jq -r '... // empty' 2>/dev/null || true`.

This exists because jq is not installed on every machine the hooks run on
(Craft Agent worker images, fresh dev boxes). python3 is universally
available where Claude Code runs.
"""
import json
import sys


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    for path in sys.argv[1:]:
        cur = data
        ok = True
        for key in path.split("."):
            if isinstance(cur, dict) and key in cur:
                cur = cur[key]
            else:
                ok = False
                break
        if not ok:
            continue
        if cur is None or cur == "":
            continue
        if isinstance(cur, (dict, list)):
            print(json.dumps(cur))
        else:
            print(cur)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
