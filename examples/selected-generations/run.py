#!/usr/bin/env python3
"""Execute selected generation upgrade/rollback in a fresh disposable directory."""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import shlex
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'bin'))
import package_selection as selected
import selected_registration as registration

spec = importlib.util.spec_from_file_location('registration_example', ROOT / 'examples/selected-registration/run.py')
example = importlib.util.module_from_spec(spec)
spec.loader.exec_module(example)
command = example.command
ep = selected.effective


def run(case, output):
    output.mkdir(parents=True, exist_ok=False)
    # Retain the complete accepted registration/compatibility oracle as evidence.
    baseline = output / 'registration-baseline'
    parity = example.run(case, baseline)
    source = baseline / 'source'
    selection = ep.read_json(baseline / 'selection.json')
    definition_path = Path('selected-registration-inputs.json')
    definition = ep.read_json(source / definition_path)
    policy_source = Path(definition['policy_inputs']['source'])
    policy_pin = definition['policy_inputs']['sha256']
    store = output / 'store'
    corpus = output / 'operations.json'
    corpus.write_text(json.dumps([{'type': 'review-procedure'}, {'type': 'ticket-commit', 'message': 'Synthetic #1027'},
        {'type': 'feature-merge', 'target_branch': 'trunk'}, {'type': 'feature-merge', 'target_branch': 'release'}]))

    def cli(action, *args, ok=True):
        result = command([sys.executable, '-B', str(source / 'bin/package-generation.py'),
            '--store', str(store), action, *map(str, args)], source, ok=ok)
        return json.loads(result.stdout) if ok else result

    def pins(path, digest):
        return ['--policy-root', source, '--policy-inputs', policy_source, '--policy-inputs-sha256', policy_pin,
                '--registration-inputs', path, '--registration-inputs-sha256', digest]

    registration_pin = ep.digest(definition)
    first_pins = pins(definition_path, registration_pin)
    first = cli('stage-selected', '--source', source, '--selection', baseline / 'selection.json', *first_pins)['generation']
    first_state = cli('select', '--generation', first, '--expected-epoch', 0, *first_pins)
    resolved = cli('resolve')
    package = Path(resolved['package'])
    # Same selected build bytes, including native and settings inventory.
    selected.require(registration.package_inventory(package) == registration.package_inventory(baseline / 'package/flat'),
                     'generation package differs from accepted registration path')
    repo, remote = example.make_consumer(output, 'generation-consumer')
    args = ['--selected', '--source', str(source), '--selection', str(Path(resolved['payload']) / 'provenance/selected-build.json'),
        *map(str, first_pins), '--identity', selection['identity'], '--backend', 'claude-code-local',
        '--hooks-root', str(package), '--workspace', str(repo), '--git-repo', str(repo), '--generation-store', str(store)]
    for program in (['bash', 'bin/install-hooks.sh'], [sys.executable, '-B', 'bin/wire-enforcement.py'], ['bash', 'bin/verify-enforcement.sh']):
        command([*program, *args], source)
    original_settings = (repo / '.claude/settings.json').read_bytes()
    original_files = selected.file_inventory(registration.package_inventory(Path(resolved['payload'])))
    observations = []

    def exercise(label):
        message = ('No ticket or review required' if case == 'independent' else
                   'docs: generation fixture #1027\n\nReview-Tier: A\nSelf-Review: inspected synthetic fixture')
        command(['git', 'commit', '--allow-empty', '-qm', message], repo)
        valid = command(['git', 'rev-parse', 'HEAD'], repo).stdout.strip()
        target = 'trunk' if case == 'independent' else 'feature'
        command(['git', 'push', 'origin', 'HEAD:' + target], repo)
        command(['git', 'push', 'origin', 'HEAD:' + target], repo)
        if case == 'siege':
            command(['git', '-c', 'core.hooksPath=/dev/null', 'commit', '--allow-empty', '-qm', 'Invalid fixture interior'], repo)
            command(['git', 'commit', '--allow-empty', '-qm', message], repo)
        before = command(['git', 'ls-remote', '--heads', str(remote)], repo).stdout
        denied = command(['git', 'push', 'origin', 'HEAD:release'], repo, ok=False)
        selected.require(denied.returncode != 0 and command(['git', 'ls-remote', '--heads', str(remote)], repo).stdout == before,
                         'generation denial changed remote refs')
        if case == 'siege':
            command(['git', 'reset', '--hard', valid], repo)
        selected.require((repo / '.claude/settings.json').read_bytes() == original_settings, 'operator settings changed')
        bound = json.loads(command(['git', 'config', '--get', registration.BINDING_KEY], repo).stdout)
        with registration.generation_binding(bound) as (active, _, token):
            result = command([sys.executable, '-B', str(Path(active['hooks_root']) / 'bin/resolve-load-set.py'),
                '--repo', selection['identity'], '--prompt', 'inspect changes', '--render-hook', '--mode', 'on'], repo)
            selected.require(bool(result.stdout), 'selected resolver emitted no content')
            template = registration.render_settings(bound)
            if case == 'independent':
                vector = template['hooks']['UserPromptSubmit'][0]['hooks'][0]['command']
            else:
                raw = ep.read_json(Path(active['hooks_root']) / 'hooks/settings-snippet.json')
                group_index, hook_index = next((g, h) for g, group in enumerate(raw['hooks']['UserPromptSubmit'])
                    for h, hook in enumerate(group['hooks']) if hook['command'].endswith('/hooks/resolver/inject-resolver.sh'))
                vector = template['hooks']['UserPromptSubmit'][group_index]['hooks'][hook_index]['command']
            prompt = command(shlex.split(vector), repo, input=json.dumps({'prompt': 'inspect changes', 'cwd': str(repo)}))
            selected.require(bool(prompt.stdout), 'registered settings resolver emitted no content')
            observations.append({'phase': label, 'scope': cli('resolve'), 'activation_token': token,
                                 'allow': True, 'deny': True, 'refs_preserved': True})
    exercise('baseline')
    role = 'project' if case == 'independent' else 'scaffold'
    component = selection[role]
    if case == 'independent':
        changed = next((source / component['paths'][0] / 'skills').rglob('SKILL.md'))
        changed.write_text(changed.read_text() + '\nSynthetic project customization upgrade.\n')
    else:
        changed = source / 'bin/build.py'
        changed.write_text(changed.read_text() + '\n# Synthetic scaffold upgrade.\n')
    command(['git', 'add', str(changed.relative_to(source))], source)
    command(['git', 'commit', '-qm', 'Synthetic component upgrade'], source)
    revision = command(['git', 'rev-parse', 'HEAD'], source).stdout.strip()
    selection[role] = selected.describe_component(source, component['id'], revision, component['paths'])
    if case == 'siege':
        runtime = definition['runtime']
        definition['runtime'] = selected.describe_component(source, runtime['id'], revision, runtime['paths'])
    upgraded_selection = output / 'upgraded-selection.json'
    upgraded_selection.write_text(json.dumps(selection))
    definition = {**definition, 'selection_sha256': ep.digest(selection)}
    next_definition = Path('upgraded-registration-inputs.json')
    (source / next_definition).write_text(json.dumps(definition))
    next_pins = pins(next_definition, ep.digest(definition))
    second = cli('stage-selected', '--source', source, '--selection', upgraded_selection, *next_pins)['generation']
    observed = cli('observe', '--generation', second, '--operations', corpus)
    second_state = cli('select', '--generation', second, '--expected-epoch', 1, '--operations', corpus,
                       '--accepted-observation', observed['sha256'], *next_pins)
    exercise('upgrade')
    observed = cli('observe', '--generation', first, '--operations', corpus, '--rollback')
    restored = cli('rollback', '--generation', first, '--expected-epoch', 2, '--operations', corpus,
                   '--accepted-observation', observed['sha256'], *first_pins)
    exercise('rollback')
    selected.require(selected.file_inventory(registration.package_inventory(Path(resolved['payload']))) == original_files,
                     'rollback source/content/settings/native bytes differ')
    selected.require(first_state['generation_receipt'] != restored['generation_receipt']
                     and first_state['activation_token'] != restored['activation_token'], 'rollback revived old evidence')
    selected.require(cli('resolve', '--expected-token', first_state['activation_token'], ok=False).returncode != 0,
                     'old activation token accepted after rollback')
    result = {'case': case, 'registration_parity': parity, 'observations': observations,
        'first': first_state, 'upgrade': second_state, 'rollback': restored, 'rollback_inventory': original_files,
        'exact_rollback_bytes': True, 'settings_bytes_preserved': True,
        'authorization_effect': 'none', 'host_invocation': 'unobserved', 'provider_authority': 'unobserved'}
    (output / 'generation-evidence.json').write_text(json.dumps(result, indent=2) + '\n')
    return {'case': case, 'epochs': [first_state['epoch'], second_state['epoch'], restored['epoch']],
            'rollback_inventory_sha256': ep.digest(original_files), 'authorization_effect': 'none'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=('independent', 'siege'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.case, args.output.absolute()), sort_keys=True))
