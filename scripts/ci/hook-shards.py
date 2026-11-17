#!/usr/bin/env python3
"""Run exhaustive hook-file partitions and verify same-run/source job outputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

SHARDS = 4


def files(root):
    paths = sorted(root.glob('hooks/_test/*.test.sh'))
    if not paths:
        raise ValueError('No files matched hooks/_test/*.test.sh')
    tracked = subprocess.check_output(['git', 'ls-files', '-z', '--', 'hooks/_test/*.test.sh'],
                                      cwd=root, timeout=20).decode().split('\0')[:-1]
    if set(tracked) != {p.relative_to(root).as_posix() for p in paths}:
        raise ValueError('hook selection differs from tracked source')
    subprocess.run(['git', 'diff', '--exit-code', 'HEAD', '--', 'hooks/_test/*.test.sh'],
                   cwd=root, check=True, stdout=subprocess.DEVNULL, timeout=20)
    if any(not p.is_file() or p.is_symlink() for p in paths):
        raise ValueError('hook tests must be regular source files')
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def partition(manifest, shard):
    if type(shard) is not int or not 0 <= shard < SHARDS:
        raise ValueError('invalid shard index')
    return {p: manifest[p] for p in list(manifest)[shard::SHARDS]}


def identity(root, env):
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True, timeout=20).strip()
    if source != env['GITHUB_SHA']:
        raise ValueError('checkout differs from workflow source')
    run, attempt = env['GITHUB_RUN_ID'], int(env['GITHUB_RUN_ATTEMPT'])
    if not run.isdigit() or attempt < 1:
        raise ValueError('invalid workflow run identity')
    return source, run, attempt


def record(root, env, shard=None):
    source, run, attempt = identity(root, env)
    manifest = files(root)
    return {'source': source, 'run': run, 'attempt': attempt,
            'shard': shard, 'files': manifest if shard is None else partition(manifest, shard)}


def run(root, report):
    statuses = {}
    for path in report['files']:
        print('::group::' + path, flush=True)
        try:
            code = subprocess.run(['bash', path], cwd=root, timeout=21600).returncode
        except (OSError, subprocess.TimeoutExpired) as error:
            print(str(error), file=sys.stderr)
            code = 1
        statuses[path] = code
        print(('PASS ' if code == 0 else 'FAIL ') + path, flush=True)
        print('::endgroup::', flush=True)
    report['statuses'] = statuses
    return 0 if all(code == 0 for code in statuses.values()) else 1


def aggregate(root, env, needs):
    expected = {'validate', *(f'hooks-{i}' for i in range(SHARDS))}
    if not isinstance(needs, dict) or set(needs) != expected:
        raise ValueError('missing or unexpected validation dependencies')
    source, run_id, attempt = identity(root, env)
    manifest = files(root)
    for name in sorted(expected):
        job = needs[name]
        if job.get('result') != 'success':
            raise ValueError('validation dependency did not succeed: ' + name)
        report = json.loads(job.get('outputs', {}).get('report', ''))
        shard = None if name == 'validate' else int(name[-1])
        expected_files = manifest if shard is None else partition(manifest, shard)
        keys = {'source', 'run', 'attempt', 'shard', 'files'} | ({'statuses'} if shard is not None else set())
        if set(report) != keys or report['source'] != source or report['run'] != run_id:
            raise ValueError('wrong-source/run validation report: ' + name)
        # Rerun failed jobs may retain successful jobs from earlier attempts of
        # THIS run. Job outputs avoid cross-attempt artifact lookup/overwrite.
        if type(report['attempt']) is not int or not 1 <= report['attempt'] <= attempt:
            raise ValueError('invalid validation attempt: ' + name)
        if ((shard is not None and type(report['shard']) is not int) or
                report['shard'] != shard or report['files'] != expected_files):
            raise ValueError('incomplete or wrong-source coverage: ' + name)
        if shard is not None and (set(report['statuses']) != set(expected_files) or
                any(type(code) is not int or code != 0 for code in report['statuses'].values())):
            raise ValueError('hook files did not all succeed: ' + name)
    print(f'Preflight and all {len(manifest)} hook files passed across {SHARDS} partitions.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('preflight', 'run', 'aggregate'))
    parser.add_argument('--shard', type=int)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.mode == 'aggregate':
        aggregate(root, os.environ, json.loads(os.environ['VALIDATION_NEEDS']))
        return 0
    if (args.mode == 'run') != (args.shard is not None):
        raise ValueError('only run requires a shard index')
    report = record(root, os.environ, args.shard)
    code = run(root, report) if args.mode == 'run' else 0
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write('report=' + json.dumps(report, separators=(',', ':')) + '\n')
    return code


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (KeyError, OSError, ValueError, subprocess.SubprocessError) as error:
        print('Hook validation failed: ' + str(error), file=sys.stderr)
        sys.exit(1)
