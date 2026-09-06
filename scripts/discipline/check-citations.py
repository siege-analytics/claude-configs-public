#!/usr/bin/env python3
"""Check backticked file:line citations in prose artifacts.

Scope: extracts every token matching `path.ext:N` or `path.ext:N-M` inside
backticks from the input files, resolves the path (as-is, then via
git ls-files fallback when the path is a bare basename), and verifies that
BOTH bounds of a range fall within the file's line count.

Prints:
    N entries, M unresolved
    UNRESOLVED at <path>:<line-cite>: <reason>
    ...

Exits 0 when all entries resolve, non-zero otherwise. Suitable for calling
from a hook or CI.

Resolution is not support (#691). Three finding classes this script CANNOT
catch and does not claim to:

- 1-2: a citation whose file:line resolves and whose sentence contradicts
  the code at that line. The check verifies the LINE EXISTS, not that it
  supports the surrounding prose. No mechanical pass catches this class.
- 9-4: identical shape to 1-2 but with additional site-drift (function
  boundary at :145 vs the two eval sites at :166 and :179).
- Section drift: a citation resolves to a line whose meaning changed since
  the citation was written. The line-number match is a floor, not proof.

Read the script header before quoting its output.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


CITATION_RE = re.compile(
    r"`([^\s`]+\.(?:md|py|sh|js|ts|yaml|yml|json|toml|sql|txt|rst|tmpl|conf|cfg|ini|xml)):(\d+)(?:-(\d+))?`"
)

REPO_ROOT: Path | None = None


def find_repo_root(start: Path) -> Path | None:
    """Walk up from start looking for a .git directory."""
    p = start.resolve()
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    return None


def resolve_path(cite_path: str, artifact_path: Path) -> Path | None:
    """Resolve a cited path against (a) as-given, (b) artifact dir,
    (c) git ls-files basename lookup. Return None if not resolvable."""
    # As given (relative to cwd)
    p = Path(cite_path)
    if p.is_file():
        return p
    # Relative to the artifact's directory
    p = artifact_path.parent / cite_path
    if p.is_file():
        return p
    # Relative to the repo root (repo-relative citation, common in md prose)
    if REPO_ROOT is not None:
        p = REPO_ROOT / cite_path
        if p.is_file():
            return p
    # Bare basename via git ls-files
    if "/" not in cite_path and REPO_ROOT is not None:
        try:
            result = subprocess.run(
                ["git", "-C", str(REPO_ROOT), "ls-files"],
                capture_output=True, text=True, timeout=10, check=True,
            )
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return None
        matches = [
            REPO_ROOT / line for line in result.stdout.splitlines()
            if Path(line).name == cite_path
        ]
        if len(matches) == 1:
            return matches[0]
    return None


def count_lines(p: Path) -> int:
    """Return the number of lines in a file, counting the final line even
    when unterminated."""
    with open(p, "rb") as f:
        data = f.read()
    if not data:
        return 0
    n = data.count(b"\n")
    if not data.endswith(b"\n"):
        n += 1
    return n


def check_file(artifact_path: Path):
    """Yield (cite_str, reason_or_None) for every citation in artifact."""
    text = artifact_path.read_text()
    for m in CITATION_RE.finditer(text):
        cite_path = m.group(1)
        lo = int(m.group(2))
        hi = int(m.group(3)) if m.group(3) else lo
        cite_str = m.group(0)

        # Bounds sanity
        if lo < 1:
            yield cite_str, f"lower bound {lo} is < 1"
            continue
        if hi < lo:
            yield cite_str, f"upper bound {hi} < lower bound {lo}"
            continue

        target = resolve_path(cite_path, artifact_path)
        if target is None:
            yield cite_str, f"path not resolved: {cite_path}"
            continue

        line_count = count_lines(target)
        if lo > line_count:
            yield cite_str, f"lower bound {lo} exceeds file length {line_count}"
            continue
        if hi > line_count:
            yield cite_str, f"upper bound {hi} exceeds file length {line_count}"
            continue

        # Resolved successfully
        yield cite_str, None


def main():
    global REPO_ROOT

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", nargs="+", type=Path,
                        help="Artifact files to scan (usually plans/*.md)")
    parser.add_argument("--repo-root", type=Path, default=None,
                        help="Repo root for git ls-files (default: walk up)")
    args = parser.parse_args()

    REPO_ROOT = args.repo_root or find_repo_root(args.files[0])

    total = 0
    unresolved = []
    for f in args.files:
        if not f.is_file():
            print(f"ERROR: input file not found: {f}", file=sys.stderr)
            return 2
        for cite, reason in check_file(f):
            total += 1
            if reason:
                unresolved.append((f, cite, reason))

    print(f"{total} entries, {len(unresolved)} unresolved")
    for f, cite, reason in unresolved:
        print(f"  UNRESOLVED at {f}: {cite}: {reason}")

    return 0 if not unresolved else 1


if __name__ == "__main__":
    sys.exit(main())
