#!/usr/bin/env python3
"""Rewrite resolver-looking skill/rule tokens for safe chat display.

Craft Agent host parsing can treat bracketed skill/rule tokens in ordinary chat
as resolver directives. This filter preserves the human-readable reference while
removing the exact raw token shape.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TOKEN_RE = re.compile(r"\[(skill|rule):([A-Za-z0-9_.-]+)\]")


def sanitize(text: str) -> str:
    """Return text with bracketed resolver tokens converted to display-only form."""

    return TOKEN_RE.sub(lambda match: f"[{match.group(1)} colon {match.group(2)}]", text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Files to sanitize. Reads stdin when omitted or '-' is used.")
    args = parser.parse_args(argv)

    if not args.paths:
        sys.stdout.write(sanitize(sys.stdin.read()))
        return 0

    for raw_path in args.paths:
        if raw_path == "-":
            sys.stdout.write(sanitize(sys.stdin.read()))
            continue
        sys.stdout.write(sanitize(Path(raw_path).read_text(encoding="utf-8")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
