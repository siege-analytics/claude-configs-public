#!/usr/bin/env python3
"""Stage and select coherent package generations; never register a host or authorize a tool.

A selected generation is an artifact boundary. Host registration, cached context,
and protected operation acceptance remain separate evidence. Resolve once per
operation; never resolve current again between reading settings and runtime.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


composition = module('generation_composition', 'bin/compose-project.py')
effective = composition.effective
handoff = module('generation_handoff', 'scripts/ci/release-handoff.py')
require = handoff.require
canonical = effective.canonical_json
digest = effective.digest


snapshot = module('generation_snapshot', 'bin/source_snapshot.py')
relative = snapshot.relative
exact_commit = snapshot.exact_commit
git_files = snapshot.git_files


def canonical_root(path):
    # Explicit operator-selected roots may use OS directory aliases (/tmp and
    # /var on macOS). Resolve that root once; reject links inside its contents.
    require(not path.is_symlink(), 'symlink store/input unsupported')
    return path.resolve()


def no_symlinks(path):
    path = path.absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'symlink store/input unsupported')
    return path


def put(root, name, data, executable=False):
    path = root / relative(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not path.exists(), f'overlapping generation input: {name}')
    path.write_bytes(data)
    path.chmod(0o755 if executable else 0o644)


def inventory(root):
    result = {}
    require(root.is_dir() and not root.is_symlink(), 'missing generation payload')
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink(), f'symlink generation input: {path}')
        if path.is_dir():
            continue
        require(path.is_file(), f'nonregular generation input: {path}')
        name = path.relative_to(root).as_posix(); relative(name)
        result[name] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                        'executable': bool(path.stat().st_mode & 0o111)}
    require(result, 'empty generation')
    require(len({p.casefold() for p in result}) == len(result), 'case-colliding generation paths')
    return result


def generation(store, generation_id):
    store = canonical_root(store)
    require(isinstance(generation_id, str) and re.fullmatch(r'[0-9a-f]{64}', generation_id), 'invalid generation ID')
    root = no_symlinks(store / 'generations' / generation_id)
    manifest_path = no_symlinks(root / 'generation.json')
    manifest = effective.read_json(manifest_path)
    require(digest(manifest) == generation_id, 'generation manifest differs from selected ID')
    require(all(type(manifest[k]) is int and manifest[k] == 1 for k in ('schema_version', 'state_schema_version')), 'unsupported generation/state schema')
    require(manifest['authorization_effect'] == 'none', 'generation cannot grant authorization')
    require(set(manifest['ownership']) == set(manifest['files']) and set(manifest['ownership'].values()) <= {'parent-runtime', 'project-composition', 'operator', 'pinned-compatibility', 'provenance'}, 'invalid generation ownership')
    require(inventory(root / 'payload') == manifest['files'], 'generation drift: missing, extra, changed or mode-mismatched files')
    require(set(p.name for p in root.iterdir()) == {'generation.json', 'payload'}, 'unexpected generation entry')
    return root, manifest


@contextmanager
def locked(store):
    store = canonical_root(store)
    store.mkdir(parents=True, exist_ok=True)
    lock_path = no_symlinks(store / '.lock')
    with lock_path.open('a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        yield


def current(store, *, verify_payload=True):
    store = canonical_root(store)
    path = no_symlinks(store / 'current.json')
    if not path.exists():
        return None
    value = effective.read_json(path)
    effective.exact_fields(value, {'schema_version', 'generation', 'previous', 'epoch', 'observation', 'authorization_effect'}, 'selection')
    require(type(value['schema_version']) is int and value['schema_version'] == 1, 'unsupported selection schema')
    require(type(value['epoch']) is int and value['epoch'] > 0, 'invalid selection epoch')
    require(value['authorization_effect'] == 'none', 'selection cannot grant authorization')
    require(isinstance(value['generation'], str) and re.fullmatch(r'[0-9a-f]{64}', value['generation']), 'invalid selected generation')
    require(value['previous'] is None or isinstance(value['previous'], str) and re.fullmatch(r'[0-9a-f]{64}', value['previous']), 'invalid previous generation')
    if verify_payload:
        generation(store, value['generation'])
    return value


def stage(store, parent_root, assets, *, release_digest, repository, tag, source,
          consumer_root, consumer_revision, identity, declaration='siege-project.json',
          composition_source='examples/composition', runtime='craft-agent'):
    """Produce a content-addressed generation without changing current selection."""
    store, parent_root, consumer_root, assets = map(canonical_root, (store, parent_root, consumer_root, assets))
    require(runtime in ('craft-agent', 'claude-code'), 'unsupported runtime package')
    relative(composition_source); relative(declaration)
    exact_commit(parent_root, source); exact_commit(consumer_root, consumer_revision)
    require(handoff.revision(parent_root, 'HEAD') == source, 'policy checkout must be the exact release source')
    # The policy resolver verifies immutable approved snapshots using this Git
    # object database. Reject tracked checkout edits before it reads validators.
    require(not handoff.git(parent_root, 'diff', 'HEAD', '--name-only'), 'parent policy checkout is dirty')
    release = effective.read_json(assets / handoff.MANIFEST)
    require(digest(release) == release_digest, 'release manifest differs from explicit pin')
    handoff.verify(parent_root, release, assets, repository, tag, source)
    # A new release may need a newer composer/resolver. Never silently render
    # it with whichever implementation happens to be running this command.
    dependencies = ('bin/compose-project.py', 'bin/procedure_composition.py', 'bin/build.py',
                    'bin/effective_policy.py', 'bin/gate_contract.py', 'bin/resolve-load-set.py',
                    'bin/source_snapshot.py')
    source_bins = git_files(parent_root, source, 'bin')
    tool_hashes = {}
    for name in dependencies:
        data = (ROOT / name).read_bytes()
        require(name in source_bins and source_bins[name][0] == data,
                f'run matching trusted composition tools for this release: {name}')
        tool_hashes[name] = hashlib.sha256(data).hexdigest()
    contract, policy, selection = effective.load_inputs(parent_root)
    resolved = effective.explain(contract, policy, selection, effective.default_context(identity, []), {'type': 'review-procedure'})
    require(resolved['state'] == 'resolved', 'unknown project identity')
    project = resolved['project']
    consumer = git_files(consumer_root, consumer_revision, declaration)
    require(declaration in consumer, 'missing customization declaration')
    declared = effective.parse_json(consumer[declaration][0], declaration)
    effective.exact_fields(declared, {'schema_version', 'identity', 'project_source', 'preserve', 'settings', 'legacy_hooks'}, 'customization')
    require(type(declared['schema_version']) is int and declared['schema_version'] == 1, 'unsupported customization schema')
    require(declared['identity'] == identity, 'foreign customization identity')
    project_source = relative(declared['project_source']).as_posix()
    settings_path = relative(declared['settings']).as_posix()
    require(isinstance(declared['preserve'], list) and len(set(declared['preserve'])) == len(declared['preserve']), 'invalid preserve paths')
    require(isinstance(declared['legacy_hooks'], list), 'invalid compatibility declarations')
    for prefix in declared['preserve']:
        relative(prefix)
        require(prefix.startswith('operator/'), 'preserved content requires the operator/ namespace')
    prefixes = [project_source, settings_path, *declared['preserve']]
    for entry in declared['legacy_hooks']:
        effective.exact_fields(entry, {'path', 'sha256', 'origin_revision', 'origin_path', 'contract_sha256'}, 'compatibility hook')
        prefixes.append(entry['path'])
    for prefix in prefixes:
        consumer.update(git_files(consumer_root, consumer_revision, prefix))
    require(settings_path in consumer, 'declared settings missing')
    settings = effective.parse_json(consumer[settings_path][0], settings_path)
    with locked(store):
        generations = no_symlinks(store / 'generations'); generations.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.stage-', dir=store) as temporary:
            temporary = Path(temporary); inputs = temporary / 'inputs'; output = temporary / 'composition'
            parent_files = git_files(parent_root, source, composition_source + '/skills')
            for name, (data, executable) in parent_files.items():
                put(inputs, name[len(composition_source) + 1:], data, executable)
            projects = {n: v for n, v in consumer.items() if n.startswith(project_source + '/')}
            require(projects, 'declared project source missing')
            for name, (data, executable) in projects.items():
                put(inputs, f'projects/{project}/' + name[len(project_source) + 1:], data, executable)
            composition.package(inputs, output, identity, policy_root=parent_root)
            staged = temporary / 'generation'; payload = staged / 'payload'; payload.mkdir(parents=True)
            owners = {}
            def add(name, data, executable, owner):
                put(payload, name, data, executable); owners[name] = owner
            for name, (data, executable) in git_files(parent_root, release['outputs'][runtime]['commit']).items():
                add('runtime/' + name, data, executable, 'parent-runtime')
            for path in sorted((output / 'flat').rglob('*')):
                if path.is_file():
                    add('content/' + path.relative_to(output / 'flat').as_posix(), path.read_bytes(), bool(path.stat().st_mode & 0o111), 'project-composition')
            for prefix in declared['preserve']:
                relative(prefix)
                require(prefix.startswith('operator/'), 'preserved content requires the operator/ namespace')
                found = {n: v for n, v in consumer.items() if n == prefix or n.startswith(prefix + '/')}
                require(found, f'preserved input missing: {prefix}')
                for name, (data, executable) in found.items():
                    add(name, data, executable, 'operator')
            for entry in declared['legacy_hooks']:
                effective.exact_fields(entry, {'path', 'sha256', 'origin_revision', 'origin_path', 'contract_sha256'}, 'compatibility hook')
                path = relative(entry['path']).as_posix()
                require(path.startswith('compatibility/') and path in consumer, 'compatibility input requires a declared compatibility/ file')
                data, executable = consumer[path]
                require(hashlib.sha256(data).hexdigest() == entry['sha256'], 'copied hook digest differs')
                require(entry['contract_sha256'] == digest(contract), 'copied hook contract is incompatible')
                origin = git_files(parent_root, entry['origin_revision'], entry['origin_path'])
                require(origin.get(entry['origin_path']) == (data, executable), 'copied hook differs from pinned origin')
                add(path, data, executable, 'pinned-compatibility')
            add('operator-settings.json', canonical(settings), False, 'operator')
            for name, data in [('contract', contract), ('policy', policy), ('selection', selection), ('customization', declared), ('release', release)]:
                add('provenance/' + name + '.json', canonical(data), False, 'provenance')
            receipt = effective.read_json(payload / 'content/composition.json')
            manifest = {'schema_version': 1, 'state_schema_version': 1, 'identity': identity,
                        'parent_source': source, 'consumer_revision': consumer_revision,
                        'release_manifest_sha256': release_digest, 'runtime': runtime,
                        'runtime_commit': release['outputs'][runtime]['commit'],
                        'composition_source': composition_source,
                        'effective_policy_sha256': resolved['approved_policy']['effective_digest'],
                        'parent_content_sha256': receipt['parent_content_sha256'],
                        'policy_selection': selection, 'contract_sha256': digest(contract),
                        'composition_tools': tool_hashes,
                        'files': inventory(payload), 'ownership': owners,
                        'evidence_state': 'artifact-verified', 'authorization_effect': 'none'}
            generation_id = digest(manifest)
            put(staged, 'generation.json', canonical(manifest))
            destination = generations / generation_id
            if destination.exists():
                generation(store, generation_id)
            else:
                os.rename(staged, destination)
            generation(store, generation_id)
            return {'generation': generation_id, 'evidence_state': 'artifact-verified', 'authorization_effect': 'none'}


def decisions(root, manifest, operations):
    for name in ('bin/effective_policy.py', 'bin/gate_contract.py'):
        require(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == manifest['composition_tools'][name],
                'observation requires the generation-compatible policy evaluator')
    payload = root / 'payload'
    contract, policy, selection = [effective.read_json(payload / f'provenance/{name}.json') for name in ('contract', 'policy', 'selection')]
    return [effective.explain(contract, policy, selection, effective.default_context(manifest['identity'], []), op)['decision'] for op in operations]


def observe(store, candidate, operations, *, rollback=False):
    require(isinstance(operations, list) and operations, 'observation corpus must be nonempty')
    for operation in operations:
        effective.validate_operation(operation)
    active = current(store, verify_payload=not rollback)
    require(active is not None, 'observation requires an existing selected generation')
    if rollback:
        require(candidate == active['previous'], 'rollback must select the exact previous generation')
    new_root, new = generation(store, candidate)
    previous_verification = {'state': 'artifact-verified'}
    try:
        old_root, old = generation(store, active['generation'])
        require(old['identity'] == new['identity'], 'cannot switch project identity')
        before = decisions(old_root, old, operations)
    except (ValueError, OSError) as error:
        if not rollback:
            raise
        # A broken active set must not prevent recovery to the exact intact
        # previous set. Do not execute or call the broken set verified.
        previous_verification = {'state': 'unknown', 'diagnostic': str(error)}
        before = [{'policy': 'unknown', 'final': 'unknown'} for _ in operations]
    after = decisions(new_root, new, operations)
    result = {'schema_version': 1, 'previous': active['generation'], 'previous_epoch': active['epoch'],
              'candidate': candidate, 'rollback': rollback, 'previous_verification': previous_verification,
              'operations': operations, 'before': before, 'after': after,
              'differences': [i for i, pair in enumerate(zip(before, after)) if pair[0] != pair[1]],
              'authoritative_stack': 'existing-host-registration', 'evidence_state': 'configured', 'authorization_effect': 'none'}
    return {**result, 'sha256': digest(result)}


def atomic_json(path, value):
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.selection-', delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(canonical(value)); handle.flush(); os.fsync(handle.fileno())
            os.replace(temporary, path)
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if temporary.exists():
                temporary.unlink()


def select(store, candidate, *, expected_epoch, operations=None, accepted_observation=None, rollback=False):
    """Select artifact bytes only; host authority never changes in this function."""
    store = canonical_root(store)
    with locked(store):
        active = current(store, verify_payload=not rollback)
        epoch = active['epoch'] if active else 0
        require(epoch == expected_epoch, 'stale selection epoch')
        root, manifest = generation(store, candidate)
        observation = None
        if active:
            require(candidate != active['generation'], 'generation already selected')
            if rollback:
                require(candidate == active['previous'], 'rollback must select the exact previous generation')
            observation = observe(store, candidate, operations, rollback=rollback)
            require(accepted_observation == observation['sha256'], 'review and accept the exact observation before selection')
        else:
            require(not rollback, 'cannot rollback an empty store')
        value = {'schema_version': 1, 'generation': candidate,
                 'previous': active['generation'] if active else None,
                 'epoch': epoch + 1, 'observation': observation,
                 'authorization_effect': 'none'}
        # An old approval is never copied. Even rollback receives a new epoch.
        # Readers bind operation evidence to this complete token, not just files.
        atomic_json(store / 'current.json', value)
        return value


def resolve(store):
    """Read one selection and return its immutable payload path and receipt scope."""
    selected = current(store)
    require(selected is not None, 'no selected generation')
    root, manifest = generation(store, selected['generation'])
    return {'payload': str(root / 'payload'), 'generation': selected['generation'],
            'epoch': selected['epoch'], 'identity': manifest['identity'], 'authorization_effect': 'none'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', type=Path, required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    stage_parser = sub.add_parser('stage')
    for name in ('parent-root', 'assets', 'consumer-root'):
        stage_parser.add_argument('--' + name, type=Path, required=True)
    for name in ('release-digest', 'repository', 'tag', 'source', 'consumer-revision', 'identity'):
        stage_parser.add_argument('--' + name, required=True)
    stage_parser.add_argument('--declaration', default='siege-project.json')
    stage_parser.add_argument('--composition-source', default='examples/composition')
    stage_parser.add_argument('--runtime', default='craft-agent', choices=('craft-agent', 'claude-code'))
    for command in ('verify', 'observe', 'select', 'rollback'):
        child = sub.add_parser(command); child.add_argument('--generation', required=True)
        if command == 'observe':
            child.add_argument('--rollback', action='store_true', help='observe recovery to the exact previous generation, including damaged active files')
        if command != 'verify':
            child.add_argument('--operations', type=Path, required=command != 'select')
        if command in ('select', 'rollback'):
            child.add_argument('--expected-epoch', type=int, required=True)
            child.add_argument('--accepted-observation')
    sub.add_parser('resolve')
    args = vars(parser.parse_args()); command = args.pop('command'); store = args.pop('store')
    if command == 'stage':
        result = stage(store, **args)
    elif command == 'resolve':
        result = resolve(store)
    elif command == 'verify':
        _, result = generation(store, args['generation'])
    else:
        operations = json.loads(args.pop('operations').read_text()) if args.get('operations') else None
        args.pop('operations', None); candidate = args.pop('generation')
        result = observe(store, candidate, operations, **args) if command == 'observe' else select(store, candidate, operations=operations, rollback=command == 'rollback', **args)
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError, KeyError, TypeError) as exc:
        print(json.dumps({'state': 'error', 'diagnostic': str(exc), 'authorization_effect': 'none'}), file=sys.stderr)
        raise SystemExit(1)
