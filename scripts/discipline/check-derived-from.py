#!/usr/bin/env python3
"""Check derived_from: frontmatter drift on plans/*.md artifacts.

Scope: reads YAML-style derived_from: entries from an artifact's frontmatter
and reports one of three outcomes per entry:

    current    — the declared rev is the current tip for the declared path
    superseded — the declared rev exists but has commits after it that touch
                 the declared path
    unresolved — the declared rev does not exist, or exists but never touched
                 the declared path

Exits 0 when every entry reports current, non-zero otherwise. Suitable for
calling from CI or a hook.

Frontmatter shape (YAML-ish, parsed as a shallow list, not a full YAML load):

    ---
    ticket_refs:
      - siege-analytics/claude-configs-public#687
    derived_from:
      - path: plans/investigate-682-executable-path.md
        rev: 7d50cce
      - path: plans/pre-mortem-682-python-rewrite.md
        rev: a9e8600
    ---

Drift is not staleness (#695 AC4). An upstream artifact can move without
touching any figure this one consumes; most commits will be exactly that.
This script reports the drift; the reader decides whether re-derivation is
required. A moved upstream requires re-deriving rather than bumping the
declared rev — bumping-without-re-deriving manufactures evidence of a check
that did not happen.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def parse_derived_from(path: Path):
    """Parse the derived_from: block out of an artifact's frontmatter.

    Yields dicts with 'path' and 'rev' keys. Non-strict: unrecognised keys
    on an entry are ignored.
    """
    text = path.read_text()
    m = FRONTMATTER_RE.match(text)
    if not m:
        return
    fm = m.group(1)

    in_derived = False
    entry = {}
    for line in fm.split("\n"):
        if line.rstrip() == "derived_from:":
            in_derived = True
            continue
        if in_derived and line and not line[0].isspace():
            # Another top-level key ends the derived_from block
            if entry:
                yield entry
                entry = {}
            in_derived = False
            continue
        if not in_derived:
            continue

        stripped = line.strip()
        if stripped.startswith("- "):
            if entry:
                yield entry
                entry = {}
            stripped = stripped[2:].strip()

        if ":" in stripped:
            k, _, v = stripped.partition(":")
            entry[k.strip()] = v.strip()

    if entry:
        yield entry


def git(args, cwd):
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd)] + args,
            capture_output=True, text=True, timeout=15, check=False,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "git timeout"


def classify(entry, repo_root: Path):
    """Return ('current' | 'superseded' | 'unresolved', message)."""
    p = entry.get("path")
    rev = entry.get("rev")
    if not p or not rev:
        return "unresolved", f"missing path or rev: {entry!r}"

    # Verify the rev exists as some commit hash / ref
    rc, _, _ = git(["rev-parse", "--verify", f"{rev}^{{commit}}"], repo_root)
    if rc != 0:
        return "unresolved", f"rev {rev} does not exist"

    # Verify rev itself (not just an ancestor) touched the path. A typo that
    # names an unrelated commit would pass a `log -1 rev -- path` check
    # because that returns the closest ancestor that touched path, not the
    # commit itself. Use `show --name-only` to list only rev's own changes.
    rc, out, _ = git(
        ["show", "--format=", "--name-only", rev], repo_root,
    )
    if rc != 0:
        return "unresolved", f"git show failed for {rev}"
    touched = {line.strip() for line in out.splitlines() if line.strip()}
    if p not in touched:
        return "unresolved", f"rev {rev} does not touch {p}"

    # Any commits AFTER rev that also touch path?
    rc, out, _ = git(
        ["log", "--format=%H", f"{rev}..HEAD", "--", p], repo_root,
    )
    if rc != 0:
        return "unresolved", f"git log rev..HEAD failed for {p}"

    later = [h for h in out.splitlines() if h.strip()]
    if not later:
        # rev is the current tip for this path (or path unchanged since rev)
        return "current", f"{p} at {rev} is current"

    return "superseded", f"{p} at {rev} superseded by {len(later)} commit(s)"


def find_repo_root(start: Path) -> Path:
    p = start.resolve()
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    return start.resolve()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", nargs="+", type=Path,
                        help="Artifact files to check (usually plans/*.md)")
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args()

    repo_root = args.repo_root or find_repo_root(args.files[0])

    outcomes = {"current": 0, "superseded": 0, "unresolved": 0}
    problems = []

    for f in args.files:
        if not f.is_file():
            print(f"ERROR: input file not found: {f}", file=sys.stderr)
            return 2
        entries = list(parse_derived_from(f))
        if not entries:
            continue
        for entry in entries:
            outcome, msg = classify(entry, repo_root)
            outcomes[outcome] += 1
            if outcome != "current":
                problems.append((f, outcome, msg))

    total = sum(outcomes.values())
    print(
        f"{total} entries: {outcomes['current']} current, "
        f"{outcomes['superseded']} superseded, {outcomes['unresolved']} unresolved"
    )
    for f, outcome, msg in problems:
        print(f"  {outcome.upper()} in {f}: {msg}")
    if problems:
        print(
            "\nDrift is not staleness (#695). A moved upstream requires "
            "re-deriving, not bumping the declared rev — bumping without "
            "re-deriving manufactures evidence of a check that did not happen."
        )
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
