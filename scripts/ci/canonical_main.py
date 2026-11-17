#!/usr/bin/env python3
"""Prove Main coverage, including a content-identical promotion merge."""
from pathlib import Path
import subprocess
import sys


def git(repo: Path, *arguments: str) -> str:
    return subprocess.check_output(
        ['git', '-C', str(repo), *arguments], text=True,
        stderr=subprocess.DEVNULL, timeout=20,
    ).strip()


def ancestor(repo: Path, base: str, head: str) -> bool:
    result = subprocess.run(
        ['git', '-C', str(repo), 'merge-base', '--is-ancestor', base, head],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20,
    )
    if result.returncode not in (0, 1):
        raise ValueError('canonical Main ancestry could not be verified')
    return result.returncode == 0


def covers_main(repo: Path, main: str, head: str) -> bool:
    main = git(repo, 'rev-parse', '--verify', '--end-of-options', main + '^{commit}')
    head = git(repo, 'rev-parse', '--verify', '--end-of-options', head + '^{commit}')
    visited = set()
    while not ancestor(repo, main, head):
        if main in visited:
            raise ValueError('canonical Main history repeats')
        visited.add(main)
        parents = git(repo, 'rev-list', '--parents', '-n', '1', main).split()
        if len(parents) != 3:
            return False
        _, previous_main, promoted = parents
        if (not ancestor(repo, promoted, head)
                or git(repo, 'rev-parse', main + '^{tree}')
                != git(repo, 'rev-parse', promoted + '^{tree}')):
            return False
        # Earlier promotions may also have introduced only a merge wrapper.
        # Prove their coverage in this promoted source before accepting it.
        main, head = previous_main, promoted
    return True


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('usage: canonical_main.py MAIN_REF HEAD_REF', file=sys.stderr)
        sys.exit(2)
    try:
        eligible = covers_main(Path.cwd(), sys.argv[1], sys.argv[2])
    except (OSError, ValueError, subprocess.SubprocessError):
        print('canonical Main coverage could not be verified', file=sys.stderr)
        sys.exit(2)
    sys.exit(0 if eligible else 1)
