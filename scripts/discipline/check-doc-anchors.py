#!/usr/bin/env python3
"""Definition-site uniqueness check for named cross-references (#686 round 5).

A named anchor replaces a line number. It is only an improvement if it names
exactly one place. Counting raw substring occurrences does not measure that,
because a reference to an anchor contains the anchor. What has to be unique is
the DEFINITION site, and the only thing that makes a definition site
recognisable is a stated lexical convention.

The convention, now written down rather than held in the author's head:

  heading      the anchor text follows a leading run of '#'
  bold-lead    the line begins '**' and the anchor follows
  bullet       the line begins '- ' (after indent) and the anchor follows
  para-lead    the line begins with the anchor text itself

Two properties make this checkable rather than decorative:

1. The anchor set is DERIVED from the documents, not listed here. A hardcoded
   list is a claim about coverage that nothing checks, which is the exact
   defect this script exists to prevent. Anchors are found by scanning for a
   backticked phrase followed by a structural noun.

2. It is FAIL-CLOSED. An anchor with no definition site under any permitted
   form is an error, not a skip, so a cross-reference written in a form the
   convention does not cover exits non-zero rather than passing in silence.
"""
import re
import sys
from pathlib import Path

DOCS = [
    "plans/pre-mortem-682-python-rewrite.md",
    "plans/self-review-685.md",
]

# A named cross-reference: a backticked phrase followed by a structural noun.
REF = re.compile(
    r"`([^`\n]{8,90})`\s+(?:paragraph|section|bullet|row|table|heading|block)\b"
)

# `[skill:foo]` is a skill invocation, not a reference into these documents.
EXCLUDE = re.compile(r"^\[skill:")

# Each form means the anchor LEADS the line's content once the marker is
# stripped. "Contains" is not good enough: a bullet that cites an anchor also
# begins with "- ", so a contains-test reports references as definitions.
FORMS = {
    "heading": lambda s, a: re.match(r"#+\s*" + re.escape(a), s) is not None,
    "bold-lead": lambda s, a: re.match(r"\*\*\s*" + re.escape(a), s) is not None,
    "bullet": lambda s, a: re.match(r"-\s+(?:\*\*|[\"'`])?" + re.escape(a), s) is not None,
    "para-lead": lambda s, a: s.startswith(a),
}


def strip_fences(lines):
    """Blank out fenced code blocks.

    Fences hold transcripts, including this checker's own output and the
    falsification cases in the round-5 write-up. Text there is a quotation of a
    run, not a live cross-reference, and scanning it makes the document's
    record of a past failure into a present one.
    """
    out = []
    inside = False
    for line in lines:
        if line.lstrip().startswith("```"):
            inside = not inside
            out.append("")
            continue
        out.append("" if inside else line)
    return out


def collect_anchors(bodies):
    anchors = set()
    for text in bodies.values():
        for m in REF.finditer("\n".join(strip_fences(text.splitlines()))):
            a = m.group(1).strip()
            if not EXCLUDE.match(a):
                anchors.add(a)
    return sorted(anchors)


def definition_sites(lines, anchor):
    """Return [(form, lineno)] for every permitted form that matches."""
    bare = anchor.lstrip("#").strip()
    out = []
    for form, pred in FORMS.items():
        for i, line in enumerate(lines, 1):
            if pred(line.lstrip(), bare):
                out.append((form, i))
    return out


def main():
    bodies = {d: Path(d).read_text() for d in DOCS}
    lines = {d: strip_fences(bodies[d].splitlines()) for d in DOCS}
    anchors = collect_anchors(bodies)

    bad = 0
    for anchor in anchors:
        sites = []
        for d in DOCS:
            for form, ln in definition_sites(lines[d], anchor):
                sites.append((Path(d).name, form, ln))
        refs = sum(bodies[d].count(anchor) for d in DOCS)

        if len(sites) == 1:
            where, form, ln = sites[0]
            print("OK   %-10s def=1 ref=%-2d %s:%d  %s"
                  % (form, refs, where, ln, anchor))
        else:
            bad += 1
            why = "no definition site under any permitted form" if not sites else "ambiguous"
            print("FAIL %-10s def=%d ref=%-2d %s  %s"
                  % ("-", len(sites), refs, why, anchor))
            for where, form, ln in sites:
                print("       candidate %s %s:%d" % (form, where, ln))

    print("\n%d anchors derived from %d documents, %d without a unique definition site"
          % (len(anchors), len(DOCS), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
