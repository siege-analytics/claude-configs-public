#!/usr/bin/env python3
"""Versioned, content-bound test receipts. Report-only never authorizes a hook."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tempfile

SCHEMA_VERSION = 2
MAX_RECEIPT_BYTES = 4 * 1024 * 1024
MAX_SOURCE_BYTES = 64 * 1024 * 1024
SOURCE_SUFFIXES = {'.py', '.js', '.ts', '.jsx', '.tsx', '.scala', '.java', '.kt', '.rs', '.sql'}


def git(repo: Path, *args: str, data: bytes | None = None) -> bytes:
    return subprocess.run(['git', '-C', str(repo), *args], input=data,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout


def relative_source(value: str) -> str:
    if not isinstance(value, str) or not value or '\x00' in value:
        raise ValueError('source must be a nonempty repository-relative path')
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in {'.', '..'} for p in value.split('/')) or str(path) != value:
        raise ValueError(f'noncanonical source path: {value!r}')
    return value


def source_paths(repo: Path, base: str) -> list[str]:
    raw = git(repo, 'diff', '--no-ext-diff', '--no-textconv', '--name-only', '-z', '--no-renames', base + '...HEAD')
    paths = raw.decode('utf-8', 'surrogateescape').split('\x00')
    return [relative_source(p) for p in paths if p and PurePosixPath(p).suffix in SOURCE_SUFFIXES
            and not (p.startswith(('test_', 'tests/', '__tests__/'))
                     or any(marker in p for marker in ('.test.', '.spec.'))
                     or PurePosixPath(p).name.startswith('test_')
                     or '_test.' in PurePosixPath(p).name)]


def working_blob(repo: Path, source: str) -> str:
    path = repo / relative_source(source)
    # Ancestor symlinks must not read outside the repository.
    if not path.parent.resolve().is_relative_to(repo):
        raise ValueError(f'source escapes repository: {source!r}')
    try:
        if path.is_symlink():
            data = os.fsencode(os.readlink(path))
            return git(repo, 'hash-object', '--stdin', data=data).decode().strip()
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as source_file:
            info = os.fstat(source_file.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_SOURCE_BYTES:
                raise ValueError(f'source must be a regular file of at most 64 MiB: {source!r}')
            data = source_file.read(MAX_SOURCE_BYTES + 1)
        if len(data) > MAX_SOURCE_BYTES:
            raise ValueError(f'source exceeds 64 MiB: {source!r}')
    except FileNotFoundError:
        return 'deleted'
    return git(repo, 'hash-object', '--stdin', data=data).decode().strip()


def committed_blob(repo: Path, source: str) -> str:
    result = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--verify', 'HEAD:' + source],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return result.stdout.decode().strip() if result.returncode == 0 else 'deleted'


def read_json(path: Path) -> dict:
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as source:
        st = os.fstat(source.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_size > MAX_RECEIPT_BYTES:
            raise ValueError('receipt must be a bounded regular singly linked file')
        raw = source.read(MAX_RECEIPT_BYTES + 1)
    if len(raw) > MAX_RECEIPT_BYTES:
        raise ValueError('receipt exceeds size limit')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('receipt must be a JSON object')
    return value


def check(repo: Path, receipt: Path, paths: list[str]) -> list[str]:
    document = read_json(receipt)
    if document.get('schema_version') != SCHEMA_VERSION:
        return ['legacy or missing schema_version: rerun affected tests to produce a version 2 receipt']
    problems = []
    if document.get('repo_root') != str(repo):
        problems.append('receipt repo_root does not match the target repository')
    revision = document.get('tested_revision')
    if not isinstance(revision, str) or len(revision) not in {40, 64} or any(c not in '0123456789abcdef' for c in revision):
        problems.append('missing canonical tested_revision')
    elif subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', revision, 'HEAD'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
        problems.append('tested_revision is not an ancestor of HEAD; rerun affected tests')
    command = document.get('command')
    if not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
        problems.append('missing executed test command argv')
    if type(document.get('exit_code')) is not int or document['exit_code'] != 0:
        problems.append('test command did not record exit_code=0')
    evidence = document.get('evidence')
    if not isinstance(evidence, list):
        return problems + ['evidence must be an array']
    indexed = {}
    for entry in evidence:
        if not isinstance(entry, dict):
            problems.append('evidence entry must be an object')
            continue
        try:
            source = relative_source(entry.get('source'))
        except ValueError as error:
            problems.append(str(error))
            continue
        if source in indexed:
            problems.append(f'duplicate source evidence: {source!r}')
        if entry.get('result') != 'pass' and entry.get('result') != 'passed':
            problems.append(f'unsuccessful source evidence: {source!r}')
        blob = entry.get('source_blob')
        if not isinstance(blob, str) or (blob != 'deleted' and
                (len(blob) not in {40, 64} or any(c not in '0123456789abcdef' for c in blob))):
            problems.append(f'missing or malformed source_blob: {source!r}')
        indexed[source] = entry
    for source in paths:
        entry = indexed.get(source)
        if not entry:
            problems.append(f'missing exact source evidence: {source!r}')
        elif entry.get('result') != 'pass' and entry.get('result') != 'passed':
            problems.append(f'unsuccessful source evidence: {source!r}')
        elif entry.get('source_blob') != committed_blob(repo, source):
            problems.append(f'stale committed source evidence: {source!r}')
        elif entry.get('source_blob') != working_blob(repo, source):
            problems.append(f'source changed after testing: {source!r}')
    return problems


def write_receipt(output: Path, document: dict) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.test-gate-', dir=output.parent)
    try:
        with os.fdopen(fd, 'w') as target:
            json.dump(document, target, indent=2, ensure_ascii=True)
            target.write('\n')
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def record(args) -> int:
    repo = Path(args.repo).resolve()
    sources = [relative_source(s) for s in args.source]
    if not sources or len(set(sources)) != len(sources):
        raise ValueError('supply unique --source paths for every affected source')
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        raise ValueError('supply the actual test command after --')
    before = {s: working_blob(repo, s) for s in sources}
    revision = git(repo, 'rev-parse', 'HEAD').decode().strip()
    document = {}
    if args.think_gate:
        gate = read_json(Path(args.think_gate))
        if Path(gate.get('repo_root', '')).resolve() != repo:
            raise ValueError('think gate repo_root does not match --repo')
        document.update({k: gate[k] for k in ('ticket', 'task_id', 'task', 'sessionId', 'session', 'scope_paths') if k in gate})
        if not any(document.get(k) for k in ('ticket', 'task_id', 'task')):
            raise ValueError('think gate requires an explicit task identity')
    document.update(schema_version=SCHEMA_VERSION, repo_root=str(repo), tested_revision=revision,
                    command=command, exit_code=None, framework=args.framework,
                    lastUpdated=datetime.now(timezone.utc).isoformat(),
                    evidence=[dict(source=s, source_blob=before[s], result='pending') for s in sources])
    output = Path(args.output)
    # Invalidate an older pass before executing: crashes/failures must not leave
    # an apparently current successful receipt behind.
    write_receipt(output, document)
    result = subprocess.run(command, cwd=repo)
    document['exit_code'] = result.returncode
    if result.returncode != 0:
        for entry in document['evidence']:
            entry['result'] = 'fail'
        write_receipt(output, document)
        print('Tests failed; receipt records failure. Rerun after fixing the failure.', file=sys.stderr)
        return result.returncode if 0 < result.returncode < 126 else 1
    if revision != git(repo, 'rev-parse', 'HEAD').decode().strip() or before != {s: working_blob(repo, s) for s in sources}:
        raise ValueError('source or HEAD changed during tests; pending receipt cannot authorize a push')
    for entry in document['evidence']:
        entry['result'] = 'pass'
    write_receipt(output, document)
    print(f'Recorded successful test evidence: {output}')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    listing = sub.add_parser('sources', help='list exact touched source paths as JSON')
    listing.add_argument('--repo', required=True)
    listing.add_argument('--base', required=True)
    validate = sub.add_parser('check', help='strict validation; --report-only diagnoses without authorizing')
    validate.add_argument('--repo', required=True)
    validate.add_argument('--receipt', required=True)
    validate.add_argument('--base', required=True)
    validate.add_argument('--report-only', action='store_true')
    produce = sub.add_parser('record', help='execute tests and atomically record successful content receipts')
    produce.add_argument('--repo', required=True)
    produce.add_argument('--output', required=True)
    produce.add_argument('--think-gate')
    produce.add_argument('--source', action='append', required=True)
    produce.add_argument('--framework', required=True)
    produce.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        if args.action == 'record':
            return record(args)
        repo = Path(args.repo).resolve()
        if args.action == 'sources':
            print(json.dumps(source_paths(repo, args.base), ensure_ascii=True))
            return 0
        problems = check(repo, Path(args.receipt), source_paths(repo, args.base))
        if problems:
            print('Test evidence is not current:\n' + '\n'.join('  - ' + p for p in problems), file=sys.stderr)
            print('Rerun affected tests with test-evidence.py record; old receipts are never auto-upgraded.', file=sys.stderr)
        return 0 if args.report_only else (2 if problems else 0)
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
        print(f'Test evidence validation failed: {error}', file=sys.stderr)
        return 0 if getattr(args, 'report_only', False) else 2


if __name__ == '__main__':
    sys.exit(main())
