#!/usr/bin/env python3
"""Run local validation from the CI workflow, or refresh its generated inputs.

Local results do not replace protected, head-bound CI. Full mode uses the same
run steps; GitHub checkout/setup/provenance actions remain CI responsibilities.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import signal
import shutil
import subprocess
import sys
import tempfile

import yaml
from frontmatter_validation import check_dependency

ROOT = Path(__file__).resolve().parents[1]
REFRESH = [
    ['bin/skill-inventory.py'], ['bin/build.py'],
    ['bin/generated-source-authority.py'], ['bin/kernel-budget.py'],
    ['bin/progressive-loading-metrics.py'], ['bin/review-risk-metrics.py'],
    ['bin/language-scope.py', '--write'], ['bin/data-scope.py', '--write'],
]


def workflow_steps():
    workflow = yaml.safe_load((ROOT / '.github/workflows/build-and-publish.yml').read_text())
    if not isinstance(workflow, dict):
        raise ValueError('CI workflow must be a mapping')
    jobs = workflow.get('jobs')
    if not isinstance(jobs, dict) or not isinstance(jobs.get('validate'), dict):
        raise ValueError('CI workflow must define a validation job')
    steps = jobs['validate']['steps']
    if not isinstance(steps, list):
        raise ValueError('CI validation steps must be an array')
    for step in steps:
        if not isinstance(step, dict) or 'run' in step and not isinstance(step['run'], str):
            raise ValueError('CI validation step has an invalid command shape')
        if 'env' in step and not isinstance(step['env'], dict):
            raise ValueError('CI step environment must be a mapping')
    return steps


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
        if not step['run'].strip():
            raise ValueError('empty CI validation command: ' + step['name'])
        env = {}
        for key, value in step.get('env', {}).items():
            if '${{' in str(value):
                if not key.startswith('LIFECYCLE_'):
                    raise ValueError('unknown GitHub-only environment binding: ' + key)
                # Local ratchet defaults infer the repository base. GitHub event
                # provenance is not fabricated by this command.
                env[key] = ''
            else:
                env[key] = str(value)
        result.append((step['name'], step['run'], env))
    if not result:
        raise ValueError('CI validation has no executable run steps')
    return result


def run_step(command, environment, timeout):
    process = subprocess.Popen(
        ['bash', '--noprofile', '--norc', '-e', '-o', 'pipefail', '-c', command],
        cwd=ROOT, env=environment, start_new_session=True,
    )
    try:
        return process.wait(timeout=timeout)
    except BaseException:
        # An interrupted shell may own background jobs. Cancel its isolated group
        # before returning so those jobs cannot keep modifying validation state.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            if process.poll() is None:
                process.kill()  # Cancellation raced with the group exit.
        process.wait(timeout=5)
        raise


def probe(argv, environment, *, input=None):
    """Bounded feature probe; never source shell startup or operator Git config."""
    process = subprocess.Popen(argv, cwd=ROOT, env=environment, text=True,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    try:
        stdout, stderr = process.communicate(input, timeout=10)
    except BaseException:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate(timeout=5)
        raise
    if process.returncode:
        raise ValueError(shlex.join(argv[:2]) + ': ' + stderr.strip()[:500])
    return stdout


def full_prerequisites(command):
    # This is a small adapter for the selected CI entrypoints, not a shell parser.
    # In particular, synthetic workflows must not inherit unused suite tools.
    try:
        whole = shlex.split(command, comments=True)
    except ValueError:
        return False, False, False, False
    if any('\n' in token or '\r' in token or '<<' in token for token in whole):
        # Heredocs/here-strings and multiline quoted tokens can contain apparent
        # commands as data. Unsupported complex shapes lose early diagnostics;
        # their actual workflow commands and tests still execute unchanged.
        return False, False, False, False
    entrypoints = set()
    hooks = False
    for line in command.splitlines():
        try:
            tokens = shlex.split(line, comments=True)
        except ValueError:
            continue  # Unsupported line shape: do not infer extra prerequisites.
        if not tokens:
            continue
        if tokens[0] in ('python3', 'bash') and len(tokens) > 1:
            entrypoints.add(tokens[1])
        hooks |= tokens[0] == 'files=(hooks/_test/*.test.sh)'
    hooks |= 'hooks/_test/*.test.sh' in entrypoints
    ticket = hooks or 'hooks/_test/ticket_required.test.sh' in entrypoints
    reader = hooks or any(path in entrypoints for path in (
        'hooks/_test/reader_git_safety.test.sh', 'hooks/_test/reader_git_safety.py'))
    registration = any(path in entrypoints for path in (
        'bin/_test/selected_registration_test.py', 'examples/selected-registration/run.py'))
    # Build and registration consume the pinned frontmatter parser. Only the
    # registration fixtures compare the outer interpreter's literal command vector.
    python = registration or 'bin/build.py' in entrypoints
    return python, registration, ticket, reader


def full_environment(environment, bindings):
    child = {**environment, **bindings}
    # Fixtures reject symlink aliases. Normalize only this invocation's children,
    # including steps that supply their own temporary-directory bindings.
    child['TMPDIR'] = child['RUNNER_TEMP'] = environment['RUNNER_TEMP']
    return child


def preflight_full(commands, environment):
    """Fail before workflow side effects when a selected suite cannot run."""
    seen = set()
    for name, command, bindings in commands:
        child = full_environment(environment, bindings)
        python, registration, ticket, reader = full_prerequisites(command)
        signature = (python, registration, ticket, reader, tuple(sorted(child.items())))
        if signature in seen:
            continue
        seen.add(signature)
        feature = 'Bash shell features'
        try:
            # Every full step uses this dispatch shell.
            probe(['bash', '--noprofile', '--norc', '-e', '-o', 'pipefail', '-c',
                   "if (false | true); then exit 1; fi"], child)
            if ticket or reader:
                # Actual hook suites need these Bash features, not a guessed version.
                probe(['bash', '--noprofile', '--norc', '-e', '-o', 'pipefail', '-c',
                       "a=(ok); [[ ${a[0]} == ok ]]; shopt -s nullglob; "
                       'missing=("$RUNNER_TEMP"/.preflight-unmatched-*); [[ ${#missing[@]} == 0 ]]; '
                       "[[ $(cat <<<ok) == ok ]]; "
                       "IFS= read -r -d '' value < <(printf 'ok\\0'); [[ $value == ok ]]"], child)
            if python:
                feature = 'PATH python3 interpreter and pinned YAML dependency'
                code = ("import json,sys; sys.path.insert(0, 'bin'); "
                        "from frontmatter_validation import check_dependency; "
                        "check_dependency(); print(json.dumps(sys.executable))")
                executable = json.loads(probe(['python3', '-c', code], child))
                if registration and os.path.abspath(executable) != os.path.abspath(sys.executable):
                    raise ValueError('PATH python3 reports ' + str(executable) +
                                     '; adapter uses ' + sys.executable +
                                     '. Invoke the adapter with that exact python3 executable; '
                                     'symlink spellings are significant to command-vector fixtures.')
            if ticket:
                feature = 'Git multi-character core.commentString stripping'
                output = probe(['git', '-c', 'core.commentString=;;', 'stripspace',
                                '--strip-comments'], child, input=';; hidden\nkept\n')
                if output != 'kept\n':
                    raise ValueError('Git did not strip the multi-character comment prefix; '
                                     'select a Git executable supporting core.commentString.')
            if reader and sys.platform == 'darwin':
                feature = 'Darwin base64 -D -i/-o behavior'
                with tempfile.TemporaryDirectory(dir=child['RUNNER_TEMP']) as raw:
                    source, target = Path(raw) / 'input', Path(raw) / 'output'
                    source.write_text('YWJj\n')
                    output = probe(['base64', '-D', '-i', str(source)], child)
                    probe(['base64', '-D', '-i', str(source), '-o', str(target)], child)
                    if output != 'abc' or target.read_bytes() != b'abc':
                        raise ValueError('decode did not produce abc')
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            tool = {'Bash': 'bash', 'PATH': 'python3', 'Git': 'git', 'Darwin': 'base64'}[feature.split()[0]]
            resolved = shutil.which(tool, path=child.get('PATH')) or '(not found)'
            raise ValueError('full preflight failed for ' + name + ': ' + feature +
                             ' [' + resolved + ']: ' + str(error) +
                             '. Select compatible tools in the invocation environment; '
                             'the adapter does not install tools or rewrite PATH.') from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('check', 'refresh', 'full'), default='check')
    parser.add_argument('--list', action='store_true', help='show commands without executing them')
    parser.add_argument('--step-timeout', type=int, default=3600, help='per-step budget in seconds, 1..3600')
    args = parser.parse_args()
    if not 1 <= args.step_timeout <= 3600:
        parser.error('--step-timeout must be between 1 and 3600 seconds')
    check_dependency()
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
        if args.mode == 'full' and not args.list:
            environment['TMPDIR'] = environment['RUNNER_TEMP']
            preflight_full(commands, environment)
        for name, command, bindings in commands:
            print('\n== ' + name + ' ==\n' + command, flush=True)
            if args.list:
                continue
            child = (full_environment(environment, bindings) if args.mode == 'full'
                     else {**environment, **bindings})
            returncode = run_step(command, child, args.step_timeout)
            if returncode:
                print('FAILED: ' + name, file=sys.stderr)
                return returncode
    print('Local validation ' + ('listed.' if args.list else 'passed; protected CI remains required.'))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (KeyError, OSError, ValueError, yaml.YAMLError, subprocess.SubprocessError) as error:
        print('Local validation error: ' + str(error), file=sys.stderr)
        sys.exit(2)
