#!/usr/bin/env python3
"""Execute synthetic selected builds; no host registration or authorization.

Both cases invoke bin/build.py --selection. All created Git repositories and
outputs are beneath the new --output directory. Independent policy receipts
are synthetic test setup, not evidence of a real organization's approval.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('example_selection', ROOT / 'bin/package_selection.py')
selected = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selected)
effective = selected.effective


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE,
                                   text=True, timeout=60).strip()


def write(root, path, value):
    destination = root / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(value, indent=2) + '\n')


def commit(root):
    git(root, 'add', '.')
    if git(root, 'status', '--porcelain'):
        git(root, 'commit', '-qm', 'Synthetic selected build fixture #1027')
    return git(root, 'rev-parse', 'HEAD')


def independent(source):
    identity = 'github.example.invalid/independent-org/application'
    project = source / 'projects/independent'
    skill = project / 'skills/review/SKILL.md'
    skill.parent.mkdir(parents=True)
    skill.write_text('# Independent review\n\nInspect the project changes.\n')
    (project / 'CLAUDE.md').write_text('')
    write(source, 'projects/independent/composition.json', {
        'bindings': {'replacements': [], 'extensions': [], 'aliases': []}, 'heading_map': {},
        'resident_budget': {'max_characters': 2500, 'max_estimated_tokens': 625}})
    contract = effective.read_json(ROOT / 'examples/selected-build/independent/contract.json')
    write(source, 'project/contract.json', contract)
    revision = commit(source)
    policy = {'schema_version': 1, 'resolver_version': '1.0.0',
        'contract_source': 'project/contract.json', 'contract_sha256': effective.digest(contract),
        'parent_contract_revision': revision,
        'parent_lock': {'host': 'github.com', 'owner': 'independent-fixture', 'repository': 'policies',
                        'revision': revision, 'import_mechanism': 'git',
                        'digest': effective.digest(contract), 'tool_version': 'effective-policy/1'},
        'organization_profiles': [{'id': 'independent', 'values': {}}],
        'projects': [{'id': 'independent', 'repository_identity': {
            'host': 'github.example.invalid', 'owner': 'independent-org', 'repository': 'application'},
            'organization_profile': 'independent', 'values': {}}]}
    write(source, 'project/policy.json', policy)
    revision = commit(source)
    policy_selection = {'schema_version': 1, 'policy_revision': revision, 'policy_path': 'project/policy.json',
        'git_blob': git(source, 'rev-parse', revision + ':project/policy.json'),
        'raw_sha256': hashlib.sha256((source / 'project/policy.json').read_bytes()).hexdigest(),
        'canonical_sha256': effective.digest(policy),
        'review_evidence': ['https://github.com/independent-fixture/policies/pull/1#pullrequestreview-1']}
    write(source, 'project/selection.json', policy_selection)
    targets = {c['id']: {k: c[k] for k in ('kind', 'registered_path', 'package_paths')}
               for c in contract['capabilities']}
    registration = {'schema_version': 1, 'selection_source': 'project/selection.json',
        'selection_sha256': effective.digest(policy_selection), 'contract_source': 'project/contract.json',
        'review_repository': 'github.com/independent-fixture/policies', 'capability_targets': targets, 'fixture_sources': []}
    write(source, 'project/policy-inputs.json', registration)
    content = {'schema_version': 1, 'publishers': [], 'policy_aliases': [], 'prerequisites': {},
        'routes': [{'id': 'inspect', 'priority': 100, 'terms': ['inspect changes'],
                    'skills': ['${policy.review_procedure}']}],
        'resident_blocks': [{'id': 'independent--instructions',
            'content': '# Project instructions\n\nPROJECT_RESIDENT\n\n${policy.resident_workflow}',
            'source': '${policy.source}', 'allow': []}]}
    return identity, content, Path('project/policy-inputs.json'), effective.digest(registration)


def run(case, output):
    output.mkdir(parents=True, exist_ok=False)
    source = output / 'source'
    if case == 'siege':
        subprocess.run(['git', 'clone', '-q', '--no-local', str(ROOT), str(source)], check=True, timeout=60)
    else:
        source.mkdir()
        git(source, 'init', '-q', '-b', 'trunk')
    # Disposable fixtures only; no user repository hook configuration changes.
    git(source, 'config', 'core.hooksPath', '/dev/null')
    git(source, 'config', 'user.name', 'Selected build fixture')
    git(source, 'config', 'user.email', 'fixture@example.invalid')
    git(source, 'config', 'commit.gpgsign', 'false')
    for name in selected.SCAFFOLD_FILES:
        destination = source / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    if case == 'independent':
        identity, content, policy_source, policy_pin = independent(source)
        content_root, project, profile, bundles = '.', 'independent', 'independent', []
        for name in ('bundles', 'skills', 'hooks', '.githooks', 'examples', 'craft-agent'):
            selected.require(not (source / name).exists(), 'unexpected independent source: ' + name)
    else:
        identity = 'github.example.invalid/synthetic-org/strict-release'
        content_root, project, profile = 'examples/composition', 'strict-release', 'strict-release'
        content = effective.read_json(source / 'bundles/siege/composition-inputs.json')
        descriptor = 'bundles/siege/build-bundle.json'
        shutil.copy2(ROOT / descriptor, source / descriptor)
        gc = effective._gate_contract_module()
        policy_source, policy_pin = gc.SIEGE_INPUTS, gc.SIEGE_INPUTS_SHA256
        bundles = [descriptor]
    revision = commit(source)
    declaration = {'schema_version': 1, 'identity': identity, 'content_root': content_root,
        'content': content, 'workflow_profile': profile, 'backend': 'resolver-only', 'required_capabilities': [],
        'scaffold': selected.describe_component(source, 'scaffold', revision, sorted(selected.SCAFFOLD_FILES)),
        'project': selected.describe_component(source, project, revision, [selected.prefix(content_root, 'projects/' + project)]),
        'bundles': [{'component': selected.describe_component(source, 'siege', revision,
                      sorted([descriptor, selected.prefix(content_root, 'skills')])), 'descriptor': descriptor}
                    for descriptor in bundles]}
    write(output, 'selection.json', declaration)
    command = [sys.executable, '-B', str(source / 'bin/build.py'), '--source', str(source),
        '--selection', str(output / 'selection.json'), '--dist', str(output / 'package'),
        '--policy-root', str(source), '--policy-inputs', str(policy_source), '--policy-inputs-sha256', policy_pin]
    result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)
    write(output, 'build-receipt.json', json.loads(result.stdout))
    resolver = subprocess.run([sys.executable, '-B', str(output / 'package/flat/bin/resolve-load-set.py'),
        '--repo', identity, '--prompt', 'inspect changes' if case == 'independent' else 'review candidate',
        '--render-hook', '--mode', 'on'], check=True, capture_output=True, text=True, timeout=30)
    (output / 'rendered.txt').write_text(resolver.stdout)
    if case == 'siege':
        composer = selected.module('example_compatibility_composer', source, 'compose-project.py')
        composer.package(source / content_root, output / 'compatibility', identity, policy_root=source)
        compared = []
        for p in sorted((output / 'compatibility').rglob('*')):
            if p.is_file():
                name = p.relative_to(output / 'compatibility')
                selected.require(p.read_bytes() == (output / 'package' / name).read_bytes(), 'compatibility differs: ' + str(name))
                compared.append(name.as_posix())
        added = ['flat/selected-build.json', 'nested/selected-build.json']
        actual = {p.relative_to(output / 'package').as_posix() for p in (output / 'package').rglob('*') if p.is_file()}
        selected.require(actual == set(compared + added), 'unexpected selected package inventory')
        contract, policy, policy_selection = effective.load_inputs(source)
        explicit = effective.load_registered_inputs(source, registration_source=policy_source, registration_sha256=policy_pin)
        operations = [{'type': 'feature-merge', 'target_branch': branch} for branch in ('develop', 'main')]
        operations += [{'type': 'ticket-commit', 'message': message} for message in ('change', 'change #1027')]
        operations += [{'type': 'review-procedure'}]
        decisions = []
        for state in ('unverified', 'unsupported', 'verified'):
            context = effective.default_context(identity, [])
            context['capabilities'] = {c['id']: state for c in contract['capabilities']}
            for operation in operations:
                baseline = effective.explain(contract, policy, policy_selection, context, operation)
                candidate = effective.explain(explicit['contract'], explicit['policy'], explicit['selection'], context, operation)
                selected.require(candidate == baseline, 'explicit policy differs from compatibility')
                decisions.append({'operation': operation, 'capabilities': state, 'decision': candidate['decision']})
        write(output, 'parity.json', {'equal_files': compared, 'added_files': added,
                                     'decisions': decisions, 'scope': 'composition only', 'authorization_effect': 'none'})
    return {'case': case, 'output': str(output), 'artifact_scope': 'composition-only', 'authorization_effect': 'none'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=('independent', 'siege'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.case, args.output.resolve()), sort_keys=True))
