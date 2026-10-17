#!/usr/bin/env python3
"""Synthetic selected registration and actual disposable local Git effects.

All repositories remain under --output. Pins are synthetic fixture inputs;
these examples establish neither organizational approval nor live host authority.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'bin'))
import package_selection as selected


def command(argv, cwd, *, ok=True, input=None):
    result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, input=input, timeout=240)
    if ok:
        selected.require(result.returncode == 0, result.stdout + result.stderr)
    return result


def definition(source, selection, policy_source, policy_pin, case):
    value = {'schema_version': 1, 'backend': 'claude-code-local', 'identity': selection['identity'],
        'workflow_profile': selection['workflow_profile'], 'selection_sha256': selected.effective.digest(selection),
        'policy_inputs': {'source': policy_source.as_posix(), 'sha256': policy_pin},
        'adapter': 'policy', 'protected_targets': ['release', 'trunk'], 'runtime': None, 'settings_source': None}
    if case == 'siege':
        profile = selected.effective.read_json(ROOT / 'bundles/siege/registration-profile.json')
        for name in ('adapter', 'protected_targets', 'settings_source'):
            value[name] = profile[name]
        revision = selection['scaffold']['revision']
        paths = command(['git', 'ls-tree', '--name-only', revision], source).stdout.splitlines()
        value['runtime'] = selected.describe_component(source, 'siege-compatibility', revision, sorted(paths))
    relative = Path('selected-registration-inputs.json')
    (source / relative).write_text(json.dumps(value, indent=2) + '\n')
    return relative, selected.effective.digest(value)


def make_consumer(output, name):
    repo = output / name
    repo.mkdir()
    command(['git', 'init', '--template=', '-q', '-b', 'feature'], repo)
    for key, value in (('user.name', 'Synthetic Fixture'), ('user.email', 'fixture@example.invalid'), ('commit.gpgsign', 'false')):
        command(['git', 'config', key, value], repo)
    settings = repo / '.claude/settings.json'
    settings.parent.mkdir()
    settings.write_text(json.dumps({'model': 'operator-choice', 'permissions': {'deny': ['fixture']}}))
    remote = output / (name + '-remote with spaces \u540d\u524d.git')
    command(['git', 'init', '--template=', '-q', '--bare', str(remote)], repo)
    command(['git', 'remote', 'add', 'origin', str(remote)], repo)
    return repo, remote


def operations(repo, remote, case):
    def refs():
        return command(['git', 'ls-remote', '--heads', str(remote)], repo).stdout
    initial = refs()
    message = 'No ticket or review obligations' if case == 'independent' else 'docs: selected fixture #1027\n\nReview-Tier: A\nSelf-Review: inspected disposable changes'
    hook_root = Path(command(['git', 'config', '--get', 'core.hooksPath'], repo).stdout.strip())
    for name in ('--help', '--selected', '--binding', '--command', '-h', '--', 'space name', '\u540d\u524d'):
        (repo / name).write_text(message)
        command([str(hook_root / 'commit-msg'), name], repo)
        if case == 'siege':
            (repo / name).write_text('Missing required review and ticket')
            denied = command([str(hook_root / 'commit-msg'), name], repo, ok=False)
            selected.require(denied.returncode != 0, 'option-like message path bypassed commit policy')
        (repo / name).unlink()
    if (hook_root.parent / 'selected-registration.json').exists():
        for event, payload in (('commit-msg', []), ('commit-msg', ['--help', 'extra']),
                               ('pre-push', []), ('pre-push', ['--help']),
                               ('pre-push', ['origin', str(remote), '--help'])):
            malformed = command([str(hook_root / event), *payload], repo, ok=False, input='')
            selected.require(malformed.returncode != 0, 'malformed native arguments accepted')
    if case == 'siege':
        bad = command(['git', 'commit', '--allow-empty', '-qm', 'Missing required review and ticket'], repo, ok=False)
        selected.require(bad.returncode != 0 and refs() == initial, 'compatibility accepted an invalid commit')
    target = 'trunk' if case == 'independent' else 'feature'
    aliases = ('origin', '--help', '--selected', '--binding', '--command', '-h', '--', '\u540d\u524d')
    probes = []
    for alias in aliases:
        if alias != 'origin':
            command(['git', 'remote', 'add', '--', alias, 'file://' + str(remote)], repo)
        command(['git', 'commit', '--allow-empty', '-qm', message], repo)
        allowed = command(['git', 'push', '--', alias, 'HEAD:' + target], repo)
        head = command(['git', 'rev-parse', 'HEAD'], repo).stdout.strip()
        selected.require(head + '\trefs/heads/' + target in refs(), 'allowed push did not publish head')
        before = refs()
        command(['git', 'push', '--', alias, 'HEAD:' + target], repo)
        selected.require(refs() == before, 'up-to-date push changed destination refs')
        probes.append({'remote': alias, 'allow_exit': allowed.returncode, 'allowed_head': head})
    if case == 'siege':
        # A bypassed fixture commit makes the range gate independently observable.
        command(['git', '-c', 'core.hooksPath=/dev/null', 'commit', '--allow-empty', '-qm', 'Invalid interior'], repo)
        command(['git', 'commit', '--allow-empty', '-qm', message], repo)
    for probe in probes:
        before = refs()
        denied = command(['git', 'push', '--', probe['remote'], 'HEAD:release'], repo, ok=False)
        after = refs()
        selected.require(denied.returncode != 0 and after == before, 'denied push changed destination refs')
        probe.update(deny_exit=denied.returncode, refs_before=before, refs_after=after, stderr=denied.stderr)
    (repo.parent / (repo.name + '-native-arguments.json')).write_text(json.dumps(probes, indent=2) + '\n')
    return {'commit_allow': True, 'commit_deny': case == 'siege', 'push_allow': True,
            'push_deny': True, 'remote_unchanged_on_deny': True}


def exercise(output, selection, policy_source, policy_pin, registration_source, registration_pin, case):
    source, package = output / 'source', output / 'package/flat'
    repo, remote = make_consumer(output, 'consumer')
    arguments = ['--selected', '--source', str(source), '--selection', str(output / 'selection.json'),
        '--policy-root', str(source), '--policy-inputs', str(policy_source), '--policy-inputs-sha256', policy_pin,
        '--registration-inputs', str(registration_source), '--registration-inputs-sha256', registration_pin,
        '--identity', selection['identity'], '--backend', 'claude-code-local', '--hooks-root', str(package),
        '--workspace', str(repo), '--git-repo', str(repo)]
    observations = []
    for program in (['bash', 'bin/install-hooks.sh'], [sys.executable, '-B', 'bin/wire-enforcement.py'], ['bash', 'bin/verify-enforcement.sh']):
        observations.append(json.loads(command([*program, *arguments], source).stdout))
    decisions = operations(repo, remote, case)
    loaded = selected.effective.load_registered_inputs(source, registration_source=policy_source,
                                                       registration_sha256=policy_pin)
    operation_corpus = [{'type': 'review-procedure'}, {'type': 'ticket-commit', 'message': 'No ticket'},
        {'type': 'ticket-commit', 'message': 'Synthetic #1027'},
        *({'type': 'feature-merge', 'target_branch': branch} for branch in ('trunk', 'develop', 'main', 'release'))]
    def explanations(inputs):
        return [selected.effective.explain(inputs['contract'], inputs['policy'], inputs['selection'],
            selected.effective.default_context(selection['identity'], []), operation,
            selection_source=inputs['registration']['selection_source']) for operation in operation_corpus]
    policy_explanations = explanations(loaded)
    result = {'case': case, 'observations': observations, 'decisions': decisions,
              'effective_policy_explanations': policy_explanations,
              'authorization_effect': 'none', 'host_invocation': 'unobserved', 'provider_authority': 'unobserved'}
    if case == 'siege':
        legacy_policy = selected.effective.load_inputs(source)
        legacy_explanations = [selected.effective.explain(*legacy_policy,
            selected.effective.default_context(selection['identity'], []), operation) for operation in operation_corpus]
        selected.require(legacy_explanations == policy_explanations, 'complete effective-policy explanations differ')
        baseline, baseline_remote = make_consumer(output, 'compatibility-consumer')
        command(['bash', 'bin/install-hooks.sh', '--workspace', str(baseline), '--hooks-root', str(package / 'compatibility'),
                 '--git-repo', str(baseline)], source)
        expected = selected.effective.read_json(baseline / '.claude/settings.json')
        actual = selected.effective.read_json(repo / '.claude/settings.json')
        payloads = json.loads(json.dumps(actual))
        native_binding = json.loads(command(['git', 'config', '--get', 'scaffold.registration'], repo).stdout)
        expected_binding = {key[2:].replace('-', '_'): value for key, value in zip(arguments[1::2], arguments[2::2])
                            if key != '--workspace'}
        files = {p.relative_to(package).as_posix(): (p.read_bytes(), bool(p.stat().st_mode & 0o111))
                 for p in package.rglob('*') if p.is_file()}
        expected_binding.update(interpreter=str(Path(sys.executable).resolve()),
                                package_sha256=selected.effective.digest(selected.file_inventory(files)))
        selected.require(native_binding == expected_binding, 'complete host binding differs from supplied inputs')
        # Independent vector oracle from the legacy install and supplied inputs;
        # do not call the selected renderer to assert its own output.
        for event, groups in payloads['hooks'].items():
            selected.require(len(groups) == len(expected['hooks'][event]), 'settings group count differs')
            for group, legacy_group in zip(groups, expected['hooks'][event]):
                selected.require(len(group['hooks']) == len(legacy_group['hooks']), 'settings command count differs')
                for hook, legacy_hook in zip(group['hooks'], legacy_group['hooks']):
                    vector = shlex.split(hook['command'])
                    expected_vector = [sys.executable, '-B', str(package / 'bin/native_git.py'), 'settings',
                        '--binding', json.dumps(expected_binding, sort_keys=True),
                        '--command', json.dumps(shlex.split(legacy_hook['command']))]
                    selected.require(vector == expected_vector, 'complete registered wrapper vector differs')
                    hook['command'] = shlex.join(json.loads(vector[vector.index('--command') + 1]))
        selected.require(expected == payloads, 'complete compatibility payload vectors differ')
        pending = repo / '.git/selected-registration-pending.json'
        pending.write_text('{}')
        try:
            for groups in actual['hooks'].values():
                for group in groups:
                    for hook in group['hooks']:
                        vector = shlex.split(hook['command'])
                        refused = command(vector, repo, input='{}', ok=False)
                        selected.require(refused.returncode != 0 and 'interrupted registration' in refused.stderr,
                                         'settings vector escaped pending registration')
        finally:
            pending.unlink()
        selected.require(operations(baseline, baseline_remote, case) == decisions, 'actual compatibility decisions differ')
        spec = selected.effective.read_json(source / registration_source)
        baseline_dist = output / 'compatibility-export'
        epoch = command(['git', 'show', '-s', '--format=%ct', spec['runtime']['revision']], source).stdout.strip()
        command([sys.executable, '-B', 'bin/build.py', '--dist', str(baseline_dist), '--source-date-epoch', epoch], source)
        expected_files = {p.relative_to(baseline_dist / 'claude-code').as_posix(): (p.read_bytes(), bool(p.stat().st_mode & 0o111))
                          for p in (baseline_dist / 'claude-code').rglob('*') if p.is_file()}
        for name in ('commit-msg', 'pre-push'):
            p = baseline_dist / 'craft-agent/.githooks' / name
            expected_files['.githooks/' + name] = (p.read_bytes(), True)
        actual_files = {p.relative_to(package / 'compatibility').as_posix(): (p.read_bytes(), bool(p.stat().st_mode & 0o111))
                        for p in (package / 'compatibility').rglob('*') if p.is_file()}
        selected.require(expected_files == actual_files, 'complete compatibility managed inventory/bytes differ')
        result['compatibility'] = {'complete_wrapper_vectors_verified': True, 'complete_payload_vectors_equal': True, 'decisions_equal': True,
            'complete_effective_policy_explanations_equal': len(policy_explanations),
            'managed_files': len(expected_files), 'executable_files': sum(mode for _, mode in expected_files.values()),
            'inventory_sha256': selected.effective.digest(selected.file_inventory(expected_files)),
            'native_hooks': ['commit-msg', 'pre-push']}
    (output / 'registration-evidence.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def run(case, output):
    spec = importlib.util.spec_from_file_location('selected_build_example', ROOT / 'examples/selected-build/run.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run(case, output, register=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=('independent', 'siege'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.case, args.output.absolute()), sort_keys=True))
