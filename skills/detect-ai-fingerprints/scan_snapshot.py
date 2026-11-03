#!/usr/bin/env python3
"""Select scanner input bytes; never execute code from the selected repository."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys


def require(condition, message):
    if not condition:
        raise ValueError(message)


def command(args, *, cwd, input=None):
    return subprocess.check_output(args, cwd=cwd, input=input, stderr=subprocess.PIPE, timeout=60)


def git(root, *args, input=None):
    return command(['git', '-c', 'core.quotepath=false', *args], cwd=root, input=input)


def relevant(path):
    return path.endswith('.py') or path in {'.claude/scanner-config.toml', '.claude/scanner-test-map.json'}


def safe_path(path):
    parts = PurePosixPath(path).parts
    require(path and not path.startswith('/') and path == '/'.join(parts), 'non-canonical snapshot path')
    require(all(part not in ('.', '..') and part.casefold() != '.git' for part in parts), 'unsupported snapshot path')
    return Path(*parts)


def blob_contents(root, entries):
    if not entries:
        return {}
    output = git(root, 'cat-file', '--batch', input=('\n'.join(oid for _, oid in entries) + '\n').encode())
    offset, result = 0, {}
    for path, oid in entries:
        end = output.index(b'\n', offset)
        fields = output[offset:end].decode().split()
        require(len(fields) == 3 and fields[:2] == [oid, 'blob'], 'missing/non-blob snapshot object')
        size = int(fields[2]); start = end + 1
        require(output[start + size:start + size + 1] == b'\n', 'truncated snapshot object')
        result[path] = output[start:start + size]
        offset = start + size + 1
    require(offset == len(output), 'unexpected snapshot object data')
    return result


def tree_files(root, tree):
    entries = []
    for record in git(root, 'ls-tree', '-r', '-z', tree).split(b'\0'):
        if not record:
            continue
        metadata, raw_path = record.split(b'\t', 1)
        path = raw_path.decode(); mode, kind, oid = metadata.decode().split()
        if relevant(path):
            require(mode in ('100644', '100755') and kind == 'blob', f'unsupported symlink/non-file scanner input: {path}')
            entries.append((path, oid))
    return blob_contents(root, entries)


def head_or_empty(root):
    head = subprocess.run(['git', 'rev-parse', '--verify', 'HEAD'], cwd=root, capture_output=True, timeout=60)
    if head.returncode == 0:
        return head.stdout.decode().strip()
    branch = git(root, 'symbolic-ref', '--quiet', 'HEAD').decode().strip()
    exists = subprocess.run(['git', 'show-ref', '--verify', '--quiet', branch], cwd=root, capture_output=True, timeout=60)
    require(exists.returncode == 1, 'cannot establish unborn repository baseline')
    return git(root, 'hash-object', '-w', '-t', 'tree', '--stdin', input=b'').decode().strip()


def snapshot(mode, destination, *, pr=None, cwd=None):
    cwd = Path.cwd() if cwd is None else Path(cwd)
    root = Path(git(cwd, 'rev-parse', '--show-toplevel').decode().strip())
    require(not destination.exists(), 'snapshot destination already exists')
    identity = {'mode': mode}
    diff_options = ['--no-ext-diff', '--no-textconv', '--no-renames']
    if mode == 'staged':
        # write-tree names the index contents once. Both diff and AST use this
        # object; subsequent index/worktree edits cannot change the selection.
        selected = git(root, 'write-tree').decode().strip()
        base = head_or_empty(root)
        identity.update(base=base, tree=selected)
        comparison = [base, selected]
        files = tree_files(root, selected)
    elif mode == 'pr':
        require(isinstance(pr, str) and re.fullmatch(r'[1-9][0-9]*', pr), 'invalid PR number')
        metadata = json.loads(command(['gh', 'pr', 'view', pr, '--json', 'baseRefOid,headRefOid'], cwd=root))
        refs = [metadata.get('baseRefOid'), metadata.get('headRefOid')]
        require(all(isinstance(ref, str) and re.fullmatch(r'[0-9a-f]{40}', ref) for ref in refs), 'PR metadata lacks exact base/head')
        for ref in refs:
            present = subprocess.run(['git', 'cat-file', '-e', ref + '^{commit}'], cwd=root, capture_output=True, timeout=60)
            if present.returncode:
                git(root, 'fetch', '--no-tags', 'origin', ref)
            require(git(root, 'rev-parse', ref + '^{commit}').decode().strip() == ref, 'PR ref is not an exact commit')
        base, selected = refs
        merge_base = git(root, 'merge-base', base, selected).decode().strip()
        identity.update(pr=pr, base=base, head=selected, merge_base=merge_base)
        comparison = [merge_base, selected]
        files = tree_files(root, selected)
    elif mode == 'working':
        comparison = []
        paths = git(root, 'ls-files', '--cached', '--others', '--exclude-standard', '-z').split(b'\0')
        files = {}
        for raw in paths:
            if not raw:
                continue
            path = raw.decode()
            if not relevant(path):
                continue
            relative = safe_path(path); source = root
            for part in relative.parts:
                source = source / part
                require(not source.is_symlink(), f'unsupported symlink scanner input: {path}')
            if source.exists():
                require(source.is_file(), f'non-file scanner input: {path}')
                files[path] = source.read_bytes()
    else:
        raise ValueError('unknown source mode')
    diff = git(root, 'diff', *diff_options, '--unified=3', *comparison)
    changed = git(root, 'diff', *diff_options, '--name-only', '-z', '--diff-filter=ACMRT', *comparison)
    python_paths = [path.decode() for path in changed.split(b'\0') if path.endswith(b'.py')]
    require(all(path in files for path in python_paths), 'selected Python input missing from snapshot')
    if mode == 'working':
        # Working mode is explicitly mutable. Refuse observed changes while
        # copying rather than silently mixing the two observed views.
        require(diff == git(root, 'diff', *diff_options, '--unified=3'), 'working diff changed during scan selection')
        require(all((root / safe_path(path)).read_bytes() == content for path, content in files.items()), 'working input changed during scan selection')
    seen = set()
    for path in files:
        safe_path(path)
        require(path.casefold() not in seen, 'case-colliding snapshot inputs unsupported')
        seen.add(path.casefold())
    source_root = destination / 'source'
    source_root.mkdir(parents=True)
    # Only a marker: cross-file test discovery stops here. No candidate Git
    # configuration, hooks, or executable code is loaded from this directory.
    (source_root / '.git').mkdir()
    for path, content in files.items():
        output = source_root / safe_path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(content)
    (destination / 'diff').write_bytes(diff)
    (destination / 'python-paths').write_bytes(b''.join(path.encode() + b'\0' for path in python_paths))
    identity['files_sha256'] = {path: hashlib.sha256(content).hexdigest() for path, content in sorted(files.items())}
    (destination / 'selection.json').write_text(json.dumps(identity, sort_keys=True, indent=2) + '\n')
    return identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('staged', 'working', 'pr'), required=True)
    parser.add_argument('--pr')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    snapshot(args.mode, args.output, pr=args.pr)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as exc:  # noqa: writing-tests-5 bootstrap metadata/missing-Git/failed-gh CLI fixtures in bin/_test/scanner_source_test.py
        print(f'scan-source-error: {exc}', file=sys.stderr)
        raise SystemExit(2)
