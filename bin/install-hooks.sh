#!/usr/bin/env bash
# Merge hook settings without replacing project customization. Register native
# Git hooks only for a no-option direct clone or an explicit --git-repo root.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
for argument in "$@"; do
    if [[ "$argument" == "--selected" ]]; then
        exec python3 -B "$REPO_ROOT/bin/selected_registration.py" install "$@"
    fi
done
exec python3 - "$REPO_ROOT" "$@" <<'PY'
import argparse
import copy
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

root = Path(sys.argv[1]).resolve()
parser = argparse.ArgumentParser(description='Merge project hook settings; register native hooks only in an explicit consumer or a no-option direct clone.')
parser.add_argument('--workspace', type=Path)
parser.add_argument('--hooks-root', type=Path)
parser.add_argument('--target-file', type=Path)
parser.add_argument('--git-repo', type=Path, help='exact consumer worktree root for native registration')
parser.add_argument('--relative', action='store_true', help='generate relative tool settings only, without implicit Git registration')
args = parser.parse_args(sys.argv[2:])

def git(repo, *argv, optional=False):
    result = subprocess.run(['git', '-C', str(repo), *argv], text=True, capture_output=True)
    if result.returncode and not optional:
        raise ValueError(result.stderr.strip() or 'Git command failed')
    return result.stdout.strip() if result.returncode == 0 else None

def merge_settings(existing, incoming):
    if not isinstance(existing, dict):
        raise ValueError('settings must be an object')
    result = copy.deepcopy(existing)
    groups = result.setdefault('hooks', {})
    if not isinstance(groups, dict):
        raise ValueError('settings hooks must be an object')
    for event, additions in incoming['hooks'].items():
        current = groups.setdefault(event, [])
        if not isinstance(current, list):
            raise ValueError(f'settings hooks.{event} must be an array')
        for addition in additions:
            metadata = {k: v for k, v in addition.items() if k != 'hooks'}
            for hook in addition['hooks']:
                command = hook['command']
                basename = Path(shlex.split(command)[0]).name
                present = False
                for group in current:
                    if not isinstance(group, dict) or not isinstance(group.get('hooks'), list):
                        raise ValueError(f'invalid hook group in {event}')
                    for prior in group['hooks']:
                        if not isinstance(prior, dict):
                            raise ValueError(f'invalid hook in {event}')
                        prior_command = prior.get('command', '')
                        try:
                            tokens = shlex.split(prior_command)
                        except ValueError:
                            tokens = []
                        if not tokens or Path(tokens[0]).name != basename:
                            continue
                        prior_metadata = {k: v for k, v in group.items() if k != 'hooks'}
                        if prior_metadata != metadata:
                            continue
                        if prior != hook:
                            raise ValueError(f'conflicting existing {event} hook {basename}; reconcile it explicitly before installation')
                        present = True
                if not present:
                    match = next((g for g in current if {k: v for k, v in g.items() if k != 'hooks'} == metadata), None)
                    if match is None:
                        match = dict(metadata, hooks=[])
                        current.append(match)
                    match['hooks'].append(hook)
    return result

try:
    if args.relative and (args.workspace or args.hooks_root):
        raise ValueError('--relative is incompatible with --hooks-root and --workspace')
    hooks_root = (args.hooks_root or root).resolve(strict=True)
    target = args.target_file or (args.workspace / '.claude/settings.json' if args.workspace else root / ('.claude/settings.json' if args.relative else '.claude/settings.local.json'))
    target = target.absolute()
    if target.is_symlink():
        raise ValueError('settings target must not be a symlink')
    snippet = json.loads((hooks_root / 'hooks/settings-snippet.json').read_text())
    snippet.pop('_comment_', None)
    placeholder = '/path/to/claude-configs-public/'
    for entries in snippet['hooks'].values():
        for group in entries:
            for hook in group['hooks']:
                command = hook['command']
                if not command.startswith(placeholder):
                    raise ValueError('unsupported snippet command')
                relative = command[len(placeholder):]
                script = hooks_root / relative
                if not script.is_file() or not os.access(script, os.X_OK):
                    raise ValueError(f'hook missing or not executable: {script}')
                hook['command'] = shlex.quote(relative if args.relative else str(script))
    existing = json.loads(target.read_text()) if target.exists() else {}
    merged = merge_settings(existing, snippet)
    repo = args.git_repo or (root if not sys.argv[2:] else None)
    hooks_value = None
    previous_local = None
    if repo is not None:
        repo = repo.resolve(strict=True)
        top = git(repo, 'rev-parse', '--show-toplevel')
        if Path(top).resolve() != repo:
            raise ValueError('--git-repo must name an exact Git worktree root')
        native = hooks_root / '.githooks'
        for relative in ('.githooks/commit-msg', '.githooks/pre-push', 'hooks/git/pre-push-self-review.sh', 'hooks/git/branch-guard.sh', 'hooks/git/test-guard.sh', 'bin/review-risk.py', 'catalog/review-risk-policy.json'):
            path = hooks_root / relative
            if not path.is_file() or (relative.endswith('.sh') or relative.startswith('.githooks/')) and not os.access(path, os.X_OK):
                raise ValueError(f'native dependency missing or not executable: {path}')
        configured = git(repo, 'config', '--get', 'core.hooksPath', optional=True)
        if configured and (repo / configured).resolve() != native.resolve():
            raise ValueError(f'existing core.hooksPath {configured!r} differs; reconcile native registration explicitly')
        if not configured:
            default_hooks = Path(git(repo, 'rev-parse', '--git-path', 'hooks'))
            if not default_hooks.is_absolute():
                default_hooks = repo / default_hooks
            if any(p.is_file() and os.access(p, os.X_OK) and not p.name.endswith('.sample') for p in default_hooks.glob('*')):
                raise ValueError('existing executable Git hooks would be displaced; reconcile them explicitly')
        hooks_value = '.githooks' if repo == hooks_root else str(native)
        previous_local = git(repo, 'config', '--local', '--get', 'core.hooksPath', optional=True)

    # All settings, target, registration and dependency validation precedes writes.
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.siege-hooks-', dir=target.parent)
    registered = False
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(merged, stream, indent=2)
            stream.write('\n')
        os.chmod(temporary, target.stat().st_mode & 0o777 if target.exists() else 0o600)
        if repo is not None:
            git(repo, 'config', '--local', 'core.hooksPath', hooks_value)
            registered = True
        os.replace(temporary, target)
    except BaseException:
        if registered:
            if previous_local is None:
                git(repo, 'config', '--local', '--unset-all', 'core.hooksPath')
            else:
                git(repo, 'config', '--local', 'core.hooksPath', previous_local)
        raise
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print(f'Merged hook settings into: {target}')
    if repo is not None:
        print(f'Configured native Git hooks in {repo}: {hooks_value}')
        print('Local hooks are bypassable feedback; protected acceptance is separate.')
    else:
        print('Native Git hooks not registered. Use --git-repo <exact-consumer-root> to register them.')
except (OSError, ValueError, KeyError, TypeError) as error:
    print(f'ERROR: {error}', file=sys.stderr)
    sys.exit(1)
PY
