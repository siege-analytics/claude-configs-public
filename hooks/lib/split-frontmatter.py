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

KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*:(?=\s|$)")
ITEM = re.compile(r"^-(?=\s|$)")
BLOCK_SCALAR = re.compile(r"^[|>][+-]?$")


def is_yaml_shaped(lines: "list[str]") -> bool:
    """Whether the candidate region is a YAML block mapping.

    Accepting every indented line makes the check vacuous. CommonMark permits a
    fenced code block indented by up to three spaces, so indentation alone does
    not distinguish metadata from quoted prose. An indented line is metadata
    only while the mapping is open -- that is, when the preceding top-level key
    had no inline value. Block scalars are rejected rather than modelled: no key
    in this schema takes one, and they would admit arbitrary prose as a value.
    """
    mapping_open = False
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1] in (" ", "\t"):
            if not mapping_open:
                return False
            inner = line.strip()
            if not (ITEM.match(inner) or KEY.match(inner)):
                return False
            continue
        if not KEY.match(line):
            return False
        if BLOCK_SCALAR.match(line.split(":", 1)[1].strip()):
            return False
        mapping_open = line.split(":", 1)[1].strip() == ""
    return True


def split(text: str) -> "tuple[list[str], list[str]]":
    lines = text.split("\n")
    if not lines or lines[0] != "---":
        return [], lines
    for i in range(1, len(lines)):
        if lines[i] == "---":
            candidate = lines[1:i]
            if candidate and is_yaml_shaped(candidate):
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
