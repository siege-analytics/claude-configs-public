#!/usr/bin/env python3
"""Create an isolated task worktree from develop, refreshing when available.

A missing remote develop is bootstrapped with create-if-absent compare-and-swap.
Existing branches, active worktrees, default branch and deployment targets are
never changed. This is the normal development route, not a release-backport tool.
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys


class PreparationError(RuntimeError):
    pass


def git(repo, *args, allowed=(0,)):
    result = subprocess.run(['git', '-C', str(repo), *args], text=True, capture_output=True)
    if result.returncode not in allowed:
        raise PreparationError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def remote_heads(repo, remote, *names):
    output = git(repo, 'ls-remote', '--heads', remote, *('refs/heads/' + n for n in names))
    heads = {}
    for line in output.splitlines():
        sha, ref = line.split('\t', 1)
        heads[ref.removeprefix('refs/heads/')] = sha
    return heads


def prepare(repo, branch, worktree, remote='origin'):
    repo = pathlib.Path(repo).resolve()
    worktree = pathlib.Path(worktree).resolve()
    git(repo, 'check-ref-format', '--branch', branch)
    if remote.startswith('-') or remote not in git(repo, 'remote').splitlines():
        raise PreparationError('select a configured repository remote, not an arbitrary URL')
    if branch in {'main', 'master', 'develop'}:
        raise PreparationError('choose a unique task branch, not a protected branch')
    # Preflight before remote mutation; never overwrite existing local work.
    if worktree.exists():
        raise PreparationError('worktree destination already exists; preserve it and choose another path')
    if git(repo, 'rev-parse', '--verify', '--quiet', 'refs/heads/' + branch, allowed=(0, 1)):
        raise PreparationError('task branch already exists; preserve it and choose another name')
    # Failure is not evidence of absence. The successful fetch and successful
    # exact remote query are both required before any bootstrap attempt.
    try:
        git(repo, 'fetch', '--prune', remote)
        heads = remote_heads(repo, remote, 'develop', 'main')
    except PreparationError:
        cached = git(repo, 'rev-parse', '--verify', '--quiet',
                     'refs/remotes/' + remote + '/develop^{commit}', allowed=(0, 1))
        if not cached:
            cached = git(repo, 'rev-parse', '--verify', '--quiet',
                         'refs/heads/develop^{commit}', allowed=(0, 1))
        if not cached:
            raise  # Network failure does not prove remote develop is absent.
        git(repo, 'worktree', 'add', '-b', branch, str(worktree), cached)
        print('Using cached develop ' + cached + '; fetch failed, remote freshness is unverified. No bootstrap attempted.', file=sys.stderr)
        return cached
    if 'develop' not in heads:
        source = heads.get('main')
        if source is None:
            advertised = git(repo, 'ls-remote', '--symref', remote, 'HEAD')
            defaults = [line.split('\t')[0].removeprefix('ref: refs/heads/')
                        for line in advertised.splitlines() if line.startswith('ref: refs/heads/')]
            if len(defaults) != 1 or defaults[0] == 'develop':
                raise PreparationError('cannot verify remote bootstrap source')
            source = remote_heads(repo, remote, defaults[0]).get(defaults[0])
        if not source:
            raise PreparationError('remote has no verified bootstrap commit')
        git(repo, 'cat-file', '-e', source + '^{commit}')
        # An empty expected old value is an atomic create-only condition.
        # A racing creator wins; their existing develop is never overwritten.
        result = subprocess.run(['git', '-C', str(repo), 'push',
                                 '--force-with-lease=refs/heads/develop:', remote,
                                 source + ':refs/heads/develop'], text=True, capture_output=True)
        if result.returncode:
            raced = remote_heads(repo, remote, 'develop')
            if 'develop' not in raced:
                raise PreparationError('develop bootstrap failed: ' + result.stderr.strip())
        heads = remote_heads(repo, remote, 'develop', 'main')
    if 'develop' not in heads:
        raise PreparationError('remote develop could not be verified after bootstrap')
    # Explicit refspec covers clones whose fetch refspec tracks main only.
    git(repo, 'fetch', remote, 'refs/heads/develop:refs/remotes/' + remote + '/develop')
    tip = git(repo, 'rev-parse', '--verify', 'refs/remotes/' + remote + '/develop^{commit}')
    latest = remote_heads(repo, remote, 'develop', 'main')
    if latest.get('develop') != tip:
        raise PreparationError('develop moved during preparation; rerun to use its current tip')
    if latest.get('main'):
        result = subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', latest['main'], tip], capture_output=True)
        if result.returncode:
            raise PreparationError('develop does not contain current main; use the reviewed sync procedure before branching')
    # Startpoint is pinned to the exact verified develop commit. This does not
    # checkout, stash, reset or clean the caller's active worktree.
    git(repo, 'worktree', 'add', '-b', branch, str(worktree), tip)
    return tip


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default='.')
    parser.add_argument('--branch', required=True)
    parser.add_argument('--worktree', required=True)
    parser.add_argument('--remote', default='origin')
    args = parser.parse_args()
    try:
        tip = prepare(args.repo, args.branch, args.worktree, args.remote)
    except (PreparationError, OSError) as error:
        print('BLOCKED: ' + str(error), file=sys.stderr)
        return 2
    print(f'Created {args.branch} at selected develop {tip} in {args.worktree}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
