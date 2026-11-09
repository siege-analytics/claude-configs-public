"""Normal development branches originate at the resolved develop tip (cached refs remain valid offline).

Inspection only. Release backports require an exact source supplied by a trusted
caller for that explicitly authorized task; branch names never grant exceptions.
"""
from __future__ import annotations

import re
import os

from task_actions import UnknownShape

MAIN_NAMES = {'main', 'master', 'prod', 'production', 'trunk', 'stable', 'release'}


def creation(args):
    """Return (new branch, source) for bounded Git branch-creation syntax.

    None means no branch is created. Missing source means Git's implicit HEAD.
    Resetting an existing branch is deliberately outside this creation route.
    """
    sub, rest = args[0], list(args[1:])
    if sub == 'branch' and ('-c' in rest or '--copy' in rest):
        values = [arg for arg in rest if arg not in {'-c', '--copy'}]
        if len(values) not in {1, 2} or any(arg.startswith('-') for arg in values):
            raise UnknownShape('ambiguous branch copy')
        return values[-1], values[0] if len(values) == 2 else 'HEAD'
    if sub not in {'branch', 'checkout', 'switch', 'worktree'}:
        return None
    if sub == 'worktree':
        if not rest or rest.pop(0) != 'add':
            return None
    branch, operands, detached = None, [], False
    tracking = False
    listing = False
    i = 0
    while i < len(rest):
        arg = rest[i]
        if arg == '--':
            if sub == 'checkout' and branch is None:
                return None  # Explicit path restoration does not create a branch.
            operands.extend(rest[i + 1:])
            break
        if arg in {'-B', '-C', '--force-create'} or arg.startswith(('-B', '-C', '--force-create=')) or (arg in {'-f', '--force'} and sub in {'branch', 'worktree'}):
            raise UnknownShape('branch reset/overwrite is not ordinary branch creation; preserve existing work')
        if arg in {'-b', '-c', '--create'} and sub != 'branch':
            i += 1
            if i >= len(rest):
                raise UnknownShape('new branch name is missing')
            branch = rest[i]
        elif ((arg.startswith('-b') or arg.startswith('-c')) and len(arg) > 2 and sub != 'branch'):
            branch = arg[2:]
        elif arg.startswith('--create=') and sub == 'switch':
            branch = arg.partition('=')[2]
        elif arg in {'--detach', '-d'} and sub in {'checkout', 'switch', 'worktree'}:
            detached = True
        elif arg in {'-q', '--quiet', '-f', '--force', '--no-track', '--no-guess', '--no-checkout', '--lock', '--orphan'}:
            if arg == '--orphan':
                raise UnknownShape('orphan creation does not originate at develop')
        elif arg in {'-t', '--track'}:
            tracking = True
        elif arg.startswith('--track='):
            tracking = True
        elif sub == 'branch' and arg in {'--list', '-l', '-a', '-r', '--all', '--remotes', '--show-current', '-d', '-D', '-m', '-M', '-c', '-C', '--delete', '--move', '--copy', '--edit-description', '--set-upstream-to', '-u', '--unset-upstream'}:
            listing = True
        elif arg.startswith('-'):
            # Plain checkout/switch paths are outside branch creation. Unknown
            # creation options cannot establish a safe startpoint.
            if branch is not None or sub in {'branch', 'worktree'}:
                raise UnknownShape('unsupported branch creation option: ' + arg)
        else:
            operands.append(arg)
        i += 1
    if sub == 'branch':
        if listing or not operands:
            return None
        if len(operands) > 2:
            raise UnknownShape('ambiguous branch creation operands')
        return operands[0], operands[1] if len(operands) == 2 else 'HEAD'
    if sub == 'worktree':
        if not operands:
            raise UnknownShape('worktree path is missing')
        if detached:
            return None  # Exact-commit detached review does not create a branch.
        if len(operands) > 2:
            raise UnknownShape('ambiguous worktree creation operands')
        if branch is None:
            # Existing-branch checkout is checked by the caller; without a ref,
            # Git derives a new branch from the path and starts it at HEAD.
            return ('<existing-or-guessed>', operands[1]) if len(operands) == 2 else ('<path-derived:' + os.path.basename(operands[0].rstrip('/')) + '>', 'HEAD')
        return branch, operands[1] if len(operands) == 2 else 'HEAD'
    if branch is None:
        if not detached and len(operands) == 1:
            return '<tracking-derived>' if tracking else '<existing-or-guessed>', operands[0]
        return None
    if detached or len(operands) > 1:
        raise UnknownShape('ambiguous branch creation source')
    return branch, operands[0] if operands else 'HEAD'


def check(item, inspect, *, release_source=None):
    candidate = creation(item['args'])
    if candidate is None:
        return
    name, source = candidate
    cwd = item['cwd']
    if name.startswith('<path-derived:'):
        derived = name[len('<path-derived:'):-1]
        if inspect(cwd, 'rev-parse', '--verify', '--quiet', 'refs/heads/' + derived + '^{commit}'):
            return  # Git reuses an existing basename branch without creating it.
    if name == '<existing-or-guessed>':
        local = inspect(cwd, 'rev-parse', '--verify', '--quiet', 'refs/heads/' + source + '^{commit}')
        if local:
            return  # Switching an existing branch preserves its existing work.
        if item['args'][0] == 'checkout' and inspect(cwd, 'ls-files', '--error-unmatch', '--', source):
            return  # Existing tracked-path restoration is not branch creation.
        if item['args'][0] == 'worktree' and inspect(cwd, 'rev-parse', '--verify', '--quiet', source + '^{commit}'):
            return  # Explicit remote ref/tag/SHA without -b creates detached review.
        # Git's DWIM can create a branch from a uniquely named remote branch.
        # Treat that as creation; never certify it from the command name alone.
        if '/' not in source:
            source = 'origin/' + source
    if name in MAIN_NAMES or name == 'develop':
        raise UnknownShape('protected branch creation uses the verified bootstrap/release procedure')
    resolved = inspect(cwd, 'rev-parse', '--verify', '--quiet', source + '^{commit}')
    if release_source and resolved == release_source:
        return  # Trusted caller's exact release grant is independent of develop.
    role = re.sub(r'^(?:refs/heads/|refs/remotes/[^/]+/|origin/)', '', source)
    if source == 'HEAD':
        role = inspect(cwd, 'symbolic-ref', '--quiet', '--short', 'HEAD')
    if role in MAIN_NAMES:
        raise UnknownShape('normal development cannot branch from main; use verified origin/develop or bin/prepare-task-branch.py')
    tips = {value for ref in ('refs/remotes/origin/develop', 'refs/heads/develop')
            if (value := inspect(cwd, 'rev-parse', '--verify', '--quiet', ref + '^{commit}'))}
    if not tips:
        raise UnknownShape('develop is unavailable locally; run bin/prepare-task-branch.py (it verifies remote absence before bootstrap)')
    if resolved not in tips:
        raise UnknownShape('normal development must branch from known develop; use develop/origin/develop or bin/prepare-task-branch.py')
