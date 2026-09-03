#!/usr/bin/env python3
"""Definition-site uniqueness check for named anchors (#686 round 5).

A named anchor replaces a line number. It is only an improvement if it names
exactly one place. Counting raw substring occurrences does not measure that,
because a reference to an anchor contains the anchor. What has to be unique is
the DEFINITION site, and the only thing that makes a definition site
recognisable is a stated lexical convention.

The convention this repository uses, now written down:

  heading      the anchor text follows a leading '#' run
  bold-lead    the line begins '**' and the anchor follows
  bullet       the line begins '- ' (after indent) and the anchor follows
  para-lead    the line begins with the anchor text itself

Every anchor must declare its form and must have exactly one line matching
that form in the file it points at. Exit 1 on any anchor that does not.
"""
import sys
from pathlib import Path

SR = "plans/self-review-685.md"
PM = "plans/pre-mortem-682-python-rewrite.md"

# (target file, form, anchor text)
ANCHORS = [
    (PM, "heading", "Every composite is derived"),
    (SR, "bullet", "eleven moved down, two up"),
    (PM, "bold-lead", "What the round-2 correction costs this argument"),
    (SR, "bold-lead", "Did the severity scoring do any work"),
    (SR, "bullet", "7 Launch-Blocking, 8 Fast-Follow, 1 Track"),
    (SR, "bullet", "5 of 16 tiers override their band"),
    (SR, "para-lead", "F-N14 is not FM-3's fact-sheet basis"),
    (SR, "para-lead", "L-6 and L-7 are P1 and P0"),
]


def matches(line, form, anchor):
    s = line.lstrip()
    if form == "heading":
        return s.startswith("#") and anchor in s
    if form == "bold-lead":
        return s.startswith("**") and anchor in s
    if form == "bullet":
        return s.startswith("- ") and anchor in s
    if form == "para-lead":
        return s.startswith(anchor)
    raise ValueError(form)


def main():
    bad = 0
    for target, form, anchor in ANCHORS:
        lines = Path(target).read_text().splitlines()
        defs = [i for i, l in enumerate(lines, 1) if matches(l, form, anchor)]
        refs = [i for i, l in enumerate(lines, 1) if anchor in l]
        ok = len(defs) == 1
        if not ok:
            bad += 1
        print(
            "%-4s %-10s def=%d ref=%d  %s -> %s"
            % ("OK" if ok else "FAIL", form, len(defs), len(refs),
               Path(target).name, anchor)
        )
    print("\n%d anchors, %d with a non-unique definition site" % (len(ANCHORS), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
