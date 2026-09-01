#!/usr/bin/env python3
"""Split YAML frontmatter from a markdown document read on stdin.

Usage: split-frontmatter.py {frontmatter|body}

A document has frontmatter only when its first line is `---`, a later line is
exactly `---`, and every line between them is shaped like YAML. Without the
shape check, the first Markdown horizontal rule in the body closes a block that
was never opened as frontmatter, and the prose above it is read as metadata.
That is a bypass, not just a parsing error: a `propagation-deferred:` line
quoted anywhere in that region would satisfy the caller's check.

When there is no valid frontmatter, `frontmatter` prints nothing and `body`
prints the whole document, so an unterminated `---` fails closed.
"""

import re
import sys

KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*:")


def is_yaml_shaped(line: str) -> bool:
    if not line.strip() or line.lstrip().startswith("#"):
        return True
    if line[:1] in (" ", "\t"):
        return True
    return bool(KEY.match(line))


def split(text: str) -> "tuple[list[str], list[str]]":
    lines = text.split("\n")
    if not lines or lines[0] != "---":
        return [], lines
    for i in range(1, len(lines)):
        if lines[i] == "---":
            candidate = lines[1:i]
            if candidate and all(is_yaml_shaped(x) for x in candidate):
                return candidate, lines[i + 1:]
            return [], lines
    return [], lines


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ("frontmatter", "body"):
        print(__doc__, file=sys.stderr)
        return 64
    frontmatter, body = split(sys.stdin.read())
    sys.stdout.write("\n".join(frontmatter if sys.argv[1] == "frontmatter" else body))
    return 0


if __name__ == "__main__":
    sys.exit(main())
