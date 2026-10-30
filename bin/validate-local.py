#!/usr/bin/env python3
"""Run local validation from the CI workflow, or refresh its generated inputs.

Local results do not replace protected, head-bound CI. Full mode uses the same
run steps; GitHub checkout/setup/provenance actions remain CI responsibilities.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
REFRESH = [
    ['bin/skill-inventory.py'], ['bin/build.py'],
    ['bin/generated-source-authority.py'], ['bin/kernel-budget.py'],
    ['bin/progressive-loading-metrics.py'], ['bin/review-risk-metrics.py'],
    ['bin/language-scope.py', '--write'], ['bin/data-scope.py', '--write'],
]


def workflow_steps():
    workflow = yaml.safe_load((ROOT / '.github/workflows/build-and-publish.yml').read_text())
    return workflow['jobs']['validate']['steps']


def check_steps(steps):
    result = [('Build validation inputs', 'python3 bin/build.py', {})]
    for step in steps:
        for line in step.get('run', '').splitlines():
            if not line.strip().startswith('python3 bin/'):
                continue
            words = shlex.split(line.strip())
            if words[:1] == ['python3'] and len(words) > 2 and words[1].startswith('bin/') and '--check' in words:
                result.append((step['name'], shlex.join(words), {}))
    if len(result) < 10:
        raise ValueError('CI freshness commands could not be identified; update this adapter')
    return result


def full_steps(steps):
    result = []
    for step in steps:
        if 'run' not in step:
            continue
        if step['name'] == 'Install pinned frontmatter validation dependency':
            print('Dependency prerequisite: use requirements-validation.txt; no automatic environment changes.', flush=True)
            continue
        if 'if' in step or '${{' in step['run']:
            raise ValueError('conditional CI run step requires an explicit local adapter: ' + step['name'])
        env = {}
        for key, value in step.get('env', {}).items():
            if '${{' in str(value):
                if not key.startswith('LIFECYCLE_'):
                    raise ValueError('unknown GitHub-only environment binding: ' + key)
                # Local ratchet defaults infer the repository base. GitHub event
                # provenance is deliberately not fabricated by this command.
                env[key] = ''
            else:
                env[key] = str(value)
        result.append((step['name'], step['run'], env))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('check', 'refresh', 'full'), default='check')
    parser.add_argument('--list', action='store_true', help='show commands without executing them')
    args = parser.parse_args()
    steps = workflow_steps()
    commands = full_steps(steps) if args.mode == 'full' else check_steps(steps)
    if args.mode == 'refresh':
        commands = [('Refresh ' + argv[0], shlex.join(['python3', *argv]), {}) for argv in REFRESH] + commands
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(('CRAFT_', 'CLAUDE_', 'CCP_', 'HUB_', 'GIT_'))
                   and key not in {'BASH_ENV', 'ENV', 'CDPATH'}}
    environment.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                       GIT_CONFIG_SYSTEM=os.devnull)
    with tempfile.TemporaryDirectory(prefix='configs-validation-') as raw:
        environment['RUNNER_TEMP'] = str(Path(raw).resolve())
        for name, command, bindings in commands:
            print('\n== ' + name + ' ==\n' + command, flush=True)
            if args.list:
                continue
            result = subprocess.run(['bash', '--noprofile', '--norc', '-e', '-o', 'pipefail', '-c', command],
                                    cwd=ROOT, env={**environment, **bindings})
            if result.returncode:
                print('FAILED: ' + name, file=sys.stderr)
                return result.returncode
    print('Local validation ' + ('listed.' if args.list else 'passed; protected CI remains required.'))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (KeyError, OSError, ValueError, yaml.YAMLError) as error:
        print('Local validation error: ' + str(error), file=sys.stderr)
        sys.exit(2)
