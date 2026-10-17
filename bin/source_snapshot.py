"""Immutable local Git source files shared by build selection and generations."""
from __future__ import annotations
import re
import subprocess
from pathlib import Path, PurePosixPath


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args],
                                   stderr=subprocess.PIPE, timeout=60)


def relative(value):
    require(isinstance(value, str) and value and not value.startswith('/'), 'expected relative path')
    parts = PurePosixPath(value).parts
    require(value == '/'.join(parts) and all(p not in ('.', '..') and p.casefold() != '.git' for p in parts), 'unsafe path')
    return Path(*parts)


def exact_commit(root, revision):
    require(isinstance(revision, str) and re.fullmatch(r'[0-9a-f]{40}', revision), 'revision must be an exact commit')
    require(git(root, 'rev-parse', '--verify', revision + '^{commit}').decode().strip() == revision, 'revision is not the named commit')


def git_files(root, revision, prefix=''):
    """Read regular files from exact Git objects, never the mutable checkout."""
    exact_commit(root, revision)
    if prefix:
        relative(prefix)
    entries = git(root, 'ls-tree', '-rz', revision).split(b'\0')
    selected = []
    for record in entries:
        if not record:
            continue
        meta, raw = record.split(b'\t', 1)
        name = raw.decode(); relative(name)
        if prefix and name != prefix and not name.startswith(prefix + '/'):
            continue
        mode, kind, oid = meta.decode().split()
        require(kind == 'blob' and mode in ('100644', '100755'), f'unsupported Git input {name}')
        selected.append((name, oid, mode == '100755'))
    require(selected, f'no input files at {revision}:{prefix}')
    raw = subprocess.check_output(['git', '-C', str(root), 'cat-file', '--batch'],
                                  input=('\n'.join(oid for _, oid, _ in selected) + '\n').encode(),
                                  stderr=subprocess.PIPE, timeout=60)
    result, offset = {}, 0
    for name, oid, executable in selected:
        end = raw.index(b'\n', offset); header = raw[offset:end].decode().split()
        require(len(header) == 3 and header[:2] == [oid, 'blob'], 'missing Git blob')
        size = int(header[2]); start = end + 1
        require(raw[start + size:start + size + 1] == b'\n', 'truncated Git blob')
        result[name] = (raw[start:start + size], executable); offset = start + size + 1
    require(offset == len(raw), 'unexpected Git blob output')
    return result
