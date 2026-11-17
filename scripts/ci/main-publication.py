#!/usr/bin/env python3
"""Suppress obsolete Main publishers while the existing publish mutex is held."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def canonical_main(repository):
    result = subprocess.run(['gh', 'api', '--hostname', 'github.com', '--method', 'GET',
                             '-H', 'Cache-Control: no-cache',
                             'repos/' + repository + '/git/ref/heads/main'],
                            capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise ValueError('cannot independently read canonical Main')
    value = json.loads(result.stdout)
    if (not isinstance(value, dict) or value.get('ref') != 'refs/heads/main' or
            not isinstance(value.get('object'), dict) or value['object'].get('type') != 'commit'):
        raise ValueError('canonical Main response is invalid')
    current = value['object'].get('sha', '')
    if not isinstance(current, str) or not re.fullmatch(r'[0-9a-f]{40}', current):
        raise ValueError('canonical Main did not resolve to a commit')
    return current


def git(root, *arguments):
    return subprocess.run(['git', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null',
                           '-C', str(root), *arguments], capture_output=True, text=True, timeout=45)


def checked(root, *arguments):
    result = git(root, *arguments)
    if result.returncode:
        raise ValueError('cannot independently verify canonical Main')
    return result.stdout.strip()


def decision(root, source, repository):
    if not re.fullmatch(r'[0-9a-f]{40}', source):
        raise ValueError('invalid event source commit')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}', repository):
        raise ValueError('invalid canonical repository identity')
    if checked(root, 'rev-parse', '--verify', 'HEAD^{commit}') != source:
        raise ValueError('publisher checkout differs from event source')
    # Read host authority independently of checkout refs and Git URL rewrites.
    current = canonical_main(repository)
    if source == current:
        status = 'current'
    else:
        # Fetch only the independently observed immutable object for ancestry.
        checked(root, 'fetch', '--no-tags', '--no-recurse-submodules',
                'https://github.com/' + repository + '.git', current)
        if checked(root, 'rev-parse', '--verify', 'FETCH_HEAD^{commit}') != current:
            raise ValueError('canonical Main object differs from host observation')
        if git(root, 'merge-base', '--is-ancestor', source, current).returncode != 0:
            raise ValueError('event source is not in canonical Main history')
        status = 'superseded'
    return {'status': status, 'source': source, 'current_main': current}


def emit(result, output, summary):
    with output.open('a') as stream:
        for key, value in result.items():
            stream.write(f'{key}={value}\n')
    with summary.open('a') as stream:
        stream.write(f'## Consumer publication: {result["status"].upper()}\n\n')
        stream.write(f'Event source: `{result["source"]}`; current canonical Main: `{result["current_main"]}`.\n\n')
        if result['status'] == 'superseded':
            stream.write('No version, consumer tags, output branches or release will be published by this run. '
                         'Validation success is not an immutable artifact handoff.\n')
    print(json.dumps(result, sort_keys=True))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    result = decision(ROOT, os.environ['GITHUB_SHA'], os.environ['GITHUB_REPOSITORY'])
    emit(result, Path(os.environ['GITHUB_OUTPUT']), Path(os.environ['GITHUB_STEP_SUMMARY']))


if __name__ == '__main__':
    try:
        main()
    except (KeyError, OSError, ValueError, subprocess.SubprocessError) as error:
        print('Main publication verification failed: ' + str(error), file=sys.stderr)
        sys.exit(2)
