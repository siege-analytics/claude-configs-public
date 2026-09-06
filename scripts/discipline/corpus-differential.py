#!/usr/bin/env python3
"""Compare two revisions of the ticket-propagation guard over the artifact corpus.

For each governed artifact in the repository, simulate a Write of the current
file content and run both the OLD-rev and NEW-rev of
`hooks/write/ticket-propagation-guard.sh` against the payload. Compare the two
exit codes. Report `N files, M differing`.

Usage:
    python3 corpus-differential.py OLD_REV NEW_REV [--repo-root DIR]

Exits 0 when every artifact produces the same verdict under both guards.
Exits non-zero when at least one artifact's verdicts differ. Fail-closed on
any artifact whose verdict cannot be determined under either revision (per
#711 AC3): the script cannot report a stable differential over data it could
not classify, so an unclassifiable artifact aborts the pass rather than being
counted as zero-diff.

Corpus scope (falsifiable, per #711 AC5):
- `git ls-files` output filtered by the two governed prefixes
- Extensions restricted to `.md`
- Files whose basename starts with `scratch-` are excluded
- The corpus is derived from the repository at HEAD, not hardcoded

The corpus decision is documented above and can be checked by reading this
docstring against the code below.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


GOVERNED_PREFIXES = ("plans/", "docs/investigations/")
GUARD_PATH = "hooks/write/ticket-propagation-guard.sh"


def git(args, cwd, check=False):
    result = subprocess.run(
        ["git", "-C", str(cwd)] + args,
        capture_output=True, text=True, timeout=30,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.returncode, result.stdout, result.stderr


def find_repo_root(start: Path) -> Path:
    p = start.resolve()
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    return start.resolve()


def corpus_at_head(repo_root: Path):
    """Return governed artifact paths at HEAD, filtered per docstring rules."""
    _, out, _ = git(["ls-files"], repo_root, check=True)
    paths = []
    for line in out.splitlines():
        if not line.endswith(".md"):
            continue
        if not any(line.startswith(pref) for pref in GOVERNED_PREFIXES):
            continue
        basename = os.path.basename(line)
        if basename.startswith("scratch-"):
            continue
        paths.append(line)
    return paths


def extract_guard(repo_root: Path, rev: str, tmpdir: Path, tag: str) -> Path:
    """git show <rev>:<guard_path> to a temp file; return its Path.

    Fail-closed if the guard cannot be extracted at the given rev (AC3).
    """
    _, out, err = git(["show", f"{rev}:{GUARD_PATH}"], repo_root, check=False)
    if not out:
        raise RuntimeError(f"could not extract {GUARD_PATH} at {rev}: {err.strip()}")
    dst = tmpdir / f"guard-{tag}.sh"
    dst.write_text(out)
    dst.chmod(0o755)

    # The guard also depends on hooks/lib/after-image.py at that rev. Extract
    # it and stage a hooks/lib/ tree so the guard's `HOOK_DIR/../lib/` lookup
    # resolves.
    _, lib_out, _ = git(
        ["show", f"{rev}:hooks/lib/after-image.py"], repo_root, check=False
    )
    lib_dir = tmpdir / tag / "hooks" / "lib"
    lib_dir.mkdir(parents=True, exist_ok=True)
    (lib_dir / "after-image.py").write_text(lib_out)
    (lib_dir / "after-image.py").chmod(0o755)

    # Copy the guard into the same tag-specific tree so its HOOK_DIR resolves.
    guard_in_tree = tmpdir / tag / "hooks" / "write" / "ticket-propagation-guard.sh"
    guard_in_tree.parent.mkdir(parents=True, exist_ok=True)
    guard_in_tree.write_text(out)
    guard_in_tree.chmod(0o755)

    return guard_in_tree


def run_guard(guard: Path, payload: dict) -> int:
    """Run a guard against a payload, return exit code."""
    try:
        result = subprocess.run(
            ["bash", str(guard)],
            input=json.dumps(payload),
            capture_output=True, text=True, timeout=15,
        )
        return result.returncode
    except subprocess.TimeoutExpired:
        return -1


def build_payload(repo_root: Path, path: str) -> dict:
    """Build a Write-shaped payload with the file's current content."""
    abs_path = repo_root / path
    content = abs_path.read_text(errors="replace") if abs_path.is_file() else ""
    return {
        "tool_name": "Write",
        "tool_input": {
            "file_path": str(abs_path),
            "content": content,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("old_rev", help="Old guard revision (e.g. HEAD~10)")
    parser.add_argument("new_rev", help="New guard revision (e.g. HEAD)")
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=0,
                        help="Test-before-bulk: only compare first N files")
    args = parser.parse_args()

    repo_root = args.repo_root or find_repo_root(Path.cwd())

    tmpdir = Path(tempfile.mkdtemp())
    try:
        try:
            old_guard = extract_guard(repo_root, args.old_rev, tmpdir, "old")
            new_guard = extract_guard(repo_root, args.new_rev, tmpdir, "new")
        except RuntimeError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2

        corpus = corpus_at_head(repo_root)
        if args.limit > 0:
            corpus = corpus[:args.limit]

        differing = []
        aborts = []
        for path in corpus:
            payload = build_payload(repo_root, path)
            old_rc = run_guard(old_guard, payload)
            new_rc = run_guard(new_guard, payload)
            if old_rc == -1 or new_rc == -1:
                aborts.append((path, old_rc, new_rc))
                continue
            # Normalize: any non-zero exit is a block; distinguish block-vs-allow
            old_verdict = "allow" if old_rc == 0 else "block"
            new_verdict = "allow" if new_rc == 0 else "block"
            if old_verdict != new_verdict:
                differing.append((path, old_verdict, new_verdict))

        n = len(corpus)
        m = len(differing)
        print(f"{n} files, {m} differing")
        for path, ov, nv in differing:
            print(f"  DIFFER {path}: old={ov} new={nv}")

        if aborts:
            print(f"\n{len(aborts)} artifacts could not be classified (fail-closed per AC3):")
            for path, ov, nv in aborts:
                print(f"  ABORT {path}: old_rc={ov} new_rc={nv}")
            return 2

        return 0 if m == 0 else 1

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
