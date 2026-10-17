"""Pinned selected registration on the existing build/install/wire/verify paths.

Configuration receipts are rebuildable facts. The caller supplies source,
selection and independent registration/policy pins at every verification boundary.
"""
from __future__ import annotations
from contextlib import contextmanager, ExitStack
import argparse
import copy
import fcntl
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

import package_selection as selected

ep = selected.effective
require = selected.require
BACKEND = 'claude-code-local'
CAPABILITIES = ['native-git', 'settings']
BINDING_KEY = 'scaffold.registration'
CORE_FILES = (
    'bin/package-generation.py', 'bin/build.py', 'bin/compose-project.py', 'bin/effective_policy.py',
    'bin/gate_contract.py', 'bin/package_selection.py', 'bin/source_snapshot.py',
    'bin/selected_registration.py', 'bin/native_git.py', 'bin/install-hooks.sh',
    'bin/wire-enforcement.py', 'bin/verify-enforcement.sh', 'catalog/gate-contract-schema.json',
)


def confined(root, relative):
    return ep._gate_contract_module().repository_path(root, selected.path(relative), 'registration path')


def no_symlinks(path):
    path = path.absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'registration path contains symlink')
    return path


def load_definition(root, selection, policy_root, policy_source, policy_pin, source, pin):
    require(source is not None and isinstance(pin, str) and ep.HEX64.fullmatch(pin),
            'independent registration source and digest are required')
    value = ep.read_json(confined(policy_root, source.as_posix()))
    require(ep.digest(value) == pin, 'registration digest differs from independent pin')
    ep.exact_fields(value, {'schema_version', 'backend', 'identity', 'workflow_profile',
                          'selection_sha256', 'policy_inputs', 'adapter', 'protected_targets',
                          'runtime', 'settings_source'}, 'registration definition')
    require(type(value['schema_version']) is int and value['schema_version'] == 1,
            'unsupported registration schema')
    require(value['backend'] == selection['backend'] == BACKEND, 'wrong registration backend')
    require(value['identity'] == selection['identity'] and value['workflow_profile'] == selection['workflow_profile'],
            'registration identity/profile differs from selected adoption')
    require(value['selection_sha256'] == ep.digest(selection), 'stale or mixed selected registration')
    require(value['policy_inputs'] == {'source': policy_source.as_posix(), 'sha256': policy_pin},
            'registration policy differs from independently supplied policy')
    require(value['adapter'] in ('policy', 'siege-compatibility'), 'missing implemented registration adapter')
    targets = value['protected_targets']
    require(isinstance(targets, list) and targets == sorted(set(targets))
            and all(isinstance(p, str) and ep.REPO_PART.fullmatch(p) for p in targets),
            'invalid protected adapter targets')
    runtime = {}
    if value['adapter'] == 'policy':
        require(value['runtime'] is None and value['settings_source'] is None,
                'policy adapter cannot import compatibility runtime')
    else:
        require(not targets, 'legacy adapter retains its declared branch feedback')
        runtime = selected.verify_component(root, value['runtime'], 'registration runtime')
        require(value['settings_source'] in runtime, 'missing registration settings source')
        complete = selected.snapshot.git_files(root, value['runtime']['revision'])
        require(runtime == complete, 'compatibility export requires its complete pinned source closure')
        for name in selected.SCAFFOLD_FILES:
            current = selected.ROOT / name
            require(name in runtime and runtime[name][0] == current.read_bytes(), 'compatibility scaffold differs: ' + name)
        for name in ('.githooks/commit-msg', '.githooks/pre-push', 'hooks/git/pre-push-self-review.sh',
                     'hooks/git/branch-guard.sh', 'hooks/git/test-guard.sh',
                     'bin/review-risk.py', 'catalog/review-risk-policy.json'):
            require(name in runtime, 'missing compatibility adapter/helper: ' + name)
            if name.startswith('.githooks/') or name.endswith('.sh'):
                require(runtime[name][1], 'non-executable compatibility adapter: ' + name)
    return value, runtime


def native_wrapper(kind):
    return ('#!/usr/bin/env python3\n'
            'import os, sys\nfrom pathlib import Path\n'
            'root = Path(__file__).resolve().parents[1]\n'
            'os.execv(sys.executable, [sys.executable, "-B", str(root / "bin/native_git.py"), '
            + repr(kind) + ', "--", *sys.argv[1:]])\n').encode()


def settings_template(definition, runtime):
    if definition['adapter'] == 'policy':
        return {'hooks': {'UserPromptSubmit': [{'hooks': [{'type': 'command', 'timeout': 15,
            'command': 'python3 -B ${package}/bin/native_git.py prompt'}]}]}}
    value = ep.parse_json(runtime[definition['settings_source']][0], 'pinned settings source')
    value.pop('_comment_', None)
    ep.exact_fields(value, {'hooks'}, 'selected settings')
    for groups in value['hooks'].values():
        require(isinstance(groups, list), 'invalid settings event groups')
        for group in groups:
            for hook in group['hooks']:
                require(hook['type'] == 'command', 'unsupported hook type')
                tokens = shlex.split(hook['command'])
                require(len(tokens) == 1 and tokens[0].startswith('/path/to/claude-configs-public/'),
                        'unsupported complete settings command vector')
                name = selected.path(tokens[0][len('/path/to/claude-configs-public/'):])
                require(name in runtime and runtime[name][1], 'missing executable settings adapter: ' + name)
                hook['command'] = '${package}/compatibility/' + name
    return value


def siege_compatibility_package(root, definition, policy_registration, parent):
    """Run the retained full exporter only for the pinned Siege compatibility descriptor."""
    require(definition['workflow_profile'] == 'strict-release',
            'compatibility adapter cannot implement selected workflow profile')
    gc = ep._gate_contract_module()
    gc.siege_policy_inputs(root)
    require(policy_registration['source'] == gc.SIEGE_INPUTS.as_posix()
            and policy_registration['sha256'] == gc.SIEGE_INPUTS_SHA256,
            'compatibility exporter requires the adopted Siege policy registration')
    revision = definition['runtime']['revision']
    with tempfile.TemporaryDirectory(prefix='.siege-compatibility-', dir=parent) as raw:
        temporary = Path(raw)
        source = temporary / 'source'
        subprocess.run(['git', 'clone', '--quiet', '--shared', '--no-checkout', str(root), str(source)], check=True, timeout=60,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        subprocess.run(['git', '-C', str(source), '-c', 'core.hooksPath=/dev/null', 'checkout', '--quiet', '--detach', revision],
                       check=True, timeout=60, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        epoch = git(source, 'show', '-s', '--format=%ct', revision)
        output = temporary / 'dist'
        result = subprocess.run([sys.executable, '-B', str(source / 'bin/build.py'), '--dist', str(output),
                                 '--source-date-epoch', epoch], capture_output=True, text=True, timeout=180)
        require(result.returncode == 0, 'compatibility export failed: ' + result.stdout[-2000:] + result.stderr[-2000:])
        runtime = {p.relative_to(output / 'claude-code').as_posix(): (p.read_bytes(), bool(p.stat().st_mode & 0o111))
                   for p in (output / 'claude-code').rglob('*') if p.is_file()}
        for name in ('commit-msg', 'pre-push'):
            path = output / 'craft-agent/.githooks' / name
            runtime['.githooks/' + name] = (path.read_bytes(), True)
        return runtime


def extend_package(output, files, receipt, definition, runtime, composer, registration_source, registration_pin):
    """Claim the entire registration inventory through the accepted ownership guard."""
    for layout in ('nested', 'flat'):
        package = output / layout
        owned = composer.GeneratedFiles()
        executable = {}
        for p in sorted(package.rglob('*')):
            if p.is_file():
                name = p.relative_to(package).as_posix()
                owned.add(name, p.read_bytes(), 'composed ' + name)
                executable[name] = bool(p.stat().st_mode & 0o111)
        def add(name, data, mode, owner):
            owned.add(name, data, owner)
            executable[name] = mode
        for name in CORE_FILES:
            require(name in files, 'missing scaffold registration helper: ' + name)
            data, mode = files[name]
            add(name, data, mode, 'scaffold ' + name)
        for name, (data, mode) in sorted(runtime.items()):
            add('compatibility/' + name, data, mode, 'registered compatibility ' + name)
        for kind in ('commit-msg', 'pre-push'):
            add('.githooks/' + kind, native_wrapper(kind), True, 'native adapter ' + kind)
        template = settings_template(definition, runtime)
        add('hooks/settings-snippet.json', ep.canonical_json(template), False, 'registered settings')
        inventory = selected.file_inventory({name: (data, executable[name]) for name, data in owned.files.items()})
        registration = {'schema_version': 1, 'state': 'unregistered', 'backend': BACKEND,
            'source': registration_source.as_posix(), 'sha256': registration_pin,
            'identity': receipt['identity'], 'selection_sha256': receipt['selection_sha256'],
            'native_hooks': ['commit-msg', 'pre-push'], 'files': inventory,
            'evidence_state': 'configured', 'authorization_effect': 'none'}
        add('selected-registration.json', ep.canonical_json(registration), False, 'registration receipt')
        for name, data in owned.files.items():
            p = package / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            p.chmod(0o755 if executable[name] else 0o644)


def git(repo, *args, optional=False):
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, timeout=30)
    require(optional or result.returncode == 0, result.stderr.strip() or 'Git registration command failed')
    return result.stdout.strip() if result.returncode == 0 else None


def binding(args):
    required = ('source', 'selection', 'policy_root', 'policy_inputs', 'policy_inputs_sha256',
                'registration_inputs', 'registration_inputs_sha256', 'identity', 'backend', 'hooks_root', 'git_repo')
    require(all(getattr(args, name, None) is not None for name in required), 'complete independent selected registration inputs are required')
    result = {name: str(getattr(args, name)) for name in required}
    for name in ('source', 'selection', 'policy_root', 'hooks_root', 'git_repo'):
        result[name] = str(no_symlinks(Path(result[name])).resolve(strict=True))
    return result


def package_inventory(root):
    result = {}
    for p in sorted(root.rglob('*')):
        require(not p.is_symlink(), 'package contains symlink')
        require(p.is_file() or p.is_dir(), 'package contains non-regular file')
        if p.is_file():
            result[p.relative_to(root).as_posix()] = (p.read_bytes(), bool(p.stat().st_mode & 0o111))
    return result


def verify_runtime(bound):
    """Check the externally registered package pin and independently adopted policy.

    Only install/wire/verify create this binding after a complete source rebuild.
    Neither the candidate package nor its receipt supplies the expected pin.
    A local operator can replace Git configuration or bypass hooks; this grants
    no protected-host authority.
    """
    require(bound['backend'] == BACKEND and bound['interpreter'] == str(Path(sys.executable).resolve()),
            'wrong registered backend/interpreter')
    package = no_symlinks(Path(bound['hooks_root']))
    require(ep.digest(selected.file_inventory(package_inventory(package))) == bound['package_sha256'],
            'registered package inventory/bytes changed')
    policy_root = Path(bound['policy_root'])
    value = ep.read_json(confined(policy_root, bound['registration_inputs']))
    require(ep.digest(value) == bound['registration_inputs_sha256'], 'registered definition changed')
    selection = ep.read_json(Path(bound['selection']))
    require(ep.digest(selection) == value['selection_sha256'], 'stale or mixed selected registration')
    require(value['policy_inputs'] == {'source': bound['policy_inputs'], 'sha256': bound['policy_inputs_sha256']},
            'registered policy binding differs')
    loaded = ep.load_registered_inputs(policy_root, registration_source=Path(bound['policy_inputs']),
                                       registration_sha256=bound['policy_inputs_sha256'])
    resolved = ep.explain(loaded['contract'], loaded['policy'], loaded['selection'],
        ep.default_context(bound['identity'], []), {'type': 'review-procedure'},
        selection_source=loaded['registration']['selection_source'])
    require(resolved['state'] == 'resolved' and resolved['organization_profile'] == value['workflow_profile']
            and bound['identity'] == value['identity'], 'registered adoption/identity differs')
    for component in (selection['scaffold'], selection['project'], *(b['component'] for b in selection['bundles'])):
        selected.snapshot.exact_commit(Path(bound['source']), component['revision'])
    return value


def verify_package(bound):
    """Rebuild from external inputs, never from generated expected digests."""
    require(bound['backend'] == BACKEND, 'wrong registration backend')
    source, policy_root = Path(bound['source']), Path(bound['policy_root'])
    selection = ep.read_json(Path(bound['selection']))
    require(selection['identity'] == bound['identity'], 'registration identity differs')
    package = no_symlinks(Path(bound['hooks_root']))
    require(package.name in ('flat', 'nested'), 'selected package must name an exact layout')
    with tempfile.TemporaryDirectory(prefix='.registration-verify-', dir=package.parent) as raw:
        output = Path(raw) / 'expected'
        selected.build(source, output, selection, policy_root=policy_root,
            policy_source=Path(bound['policy_inputs']), policy_sha256=bound['policy_inputs_sha256'],
            registration_source=Path(bound['registration_inputs']), registration_sha256=bound['registration_inputs_sha256'])
        actual = package_inventory(package)
        require(actual == package_inventory(output / package.name), 'selected package inventory/bytes differ from verified source')
        bound['package_sha256'] = ep.digest(selected.file_inventory(actual))
        bound['interpreter'] = str(Path(sys.executable).resolve())
    definition, _ = load_definition(source, selection, policy_root, Path(bound['policy_inputs']),
        bound['policy_inputs_sha256'], Path(bound['registration_inputs']), bound['registration_inputs_sha256'])
    return definition


def generation_module():
    return selected.module('registered_generation', selected.ROOT, 'package-generation.py')


@contextmanager
def generation_binding(bound):
    """Resolve once under the existing generation lock, retaining bootstrap trust."""
    package = no_symlinks(Path(bound['hooks_root']))
    require(ep.digest(selected.file_inventory(package_inventory(package))) == bound['package_sha256'],
            'generation bootstrap inventory changed')
    repo = Path(bound['git_repo'])
    require(git(repo, 'config', '--local', '--get', BINDING_KEY) == json.dumps(bound, sort_keys=True),
            'generation settings/native binding differs')
    with generation_module().consume(Path(bound['generation_store'])) as active:
        resolved = {**active['binding'], 'git_repo': bound['git_repo']}
        require(resolved['identity'] == bound['identity'], 'generation project identity changed')
        require(generation_module().settings_shape(Path(resolved['hooks_root'])) == bound['generation_settings_shape'],
                'generation settings shape differs from registered consumer')
        definition = verify_runtime(resolved)
        yield resolved, definition, active['activation_token']


def render_settings(bound):
    template = ep.read_json(Path(bound['hooks_root']) / 'hooks/settings-snippet.json')
    index = 0
    for _, groups in sorted(template['hooks'].items()):
        for group in groups:
            for hook in group['hooks']:
                if 'generation_store' in bound:
                    hook['command'] = shlex.join([sys.executable, '-B', str(Path(bound['hooks_root']) / 'bin/native_git.py'),
                        'settings', '--binding', json.dumps(bound, sort_keys=True), '--command', str(index)])
                    index += 1
                    continue
                tokens = shlex.split(hook['command'])
                tokens = [t.replace('${package}', bound['hooks_root']) for t in tokens]
                if tokens[:2] == ['python3', '-B']:
                    tokens[0] = sys.executable
                    tokens += ['--binding', json.dumps(bound, sort_keys=True)]
                else:
                    tokens = [sys.executable, '-B', str(Path(bound['hooks_root']) / 'bin/native_git.py'),
                              'settings', '--binding', json.dumps(bound, sort_keys=True),
                              '--command', json.dumps(tokens)]
                hook['command'] = shlex.join(tokens)
    return template


def merge_settings(existing, incoming):
    require(isinstance(existing, dict), 'settings must be an object')
    result = copy.deepcopy(existing)
    hooks = result.setdefault('hooks', {})
    require(isinstance(hooks, dict), 'settings hooks must be an object')
    # Validate all events before merging. A managed command under a different
    # event is still a registration conflict, including an unknown event name.
    for event, groups in hooks.items():
        require(isinstance(groups, list), 'invalid settings groups')
        for group in groups:
            require(isinstance(group, dict) and isinstance(group.get('hooks'), list), 'invalid operator hook group')
            metadata = {k:v for k,v in group.items() if k != 'hooks'}
            for prior in group['hooks']:
                require(isinstance(prior, dict), 'invalid operator hook')
                if isinstance(prior.get('command'), str) and 'native_git.py' in prior['command']:
                    require(any(prior == h and metadata == {k:v for k,v in a.items() if k != 'hooks'}
                                for a in incoming['hooks'].get(event, []) for h in a['hooks']),
                            'managed settings command has wrong vector or event')
    for event, additions in incoming['hooks'].items():
        groups = hooks.setdefault(event, [])
        require(isinstance(groups, list), 'invalid settings groups')
        for addition in additions:
            for new in addition['hooks']:
                vector = shlex.split(new['command'])
                script = next((t for t in vector if '/' in t and t.endswith(('.py', '.sh'))), vector[0])
                found = 0
                for group in groups:
                    require(isinstance(group, dict) and isinstance(group.get('hooks'), list), 'invalid operator hook group')
                    for prior in group['hooks']:
                        require(isinstance(prior, dict), 'invalid operator hook')
                        # Any occurrence of the managed script name is a conflict
                        # unless the entire command and group metadata agree.
                        if not isinstance(prior.get('command'), str) or Path(script).name not in prior['command']:
                            continue
                        metadata = {k:v for k,v in group.items() if k != 'hooks'}
                        expected_metadata = {k:v for k,v in addition.items() if k != 'hooks'}
                        require(any(prior == h and metadata == {k:v for k,v in a.items() if k != 'hooks'}
                                    for a in additions for h in a['hooks']), 'conflicting complete settings command vector')
                        if metadata == expected_metadata and prior == new:
                            found += 1
                require(found <= 1, 'duplicate managed settings command')
                if not found:
                    metadata = {k:v for k,v in addition.items() if k != 'hooks'}
                    match = next((g for g in groups if {k:v for k,v in g.items() if k != 'hooks'} == metadata), None)
                    if match is None:
                        match = {**metadata, 'hooks': []}
                        groups.append(match)
                    match['hooks'].append(copy.deepcopy(new))
    return result


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('install', 'wire', 'verify'))
    p.add_argument('--selected', action='store_true', required=True)
    p.add_argument('--generation-store', type=Path, help='bind this consumer to the existing generation selector')
    p.add_argument('--recover', action='store_true', help='restore prior state from an interrupted selected registration')
    for name in ('source', 'selection', 'policy-root', 'policy-inputs', 'registration-inputs', 'hooks-root', 'workspace', 'git-repo', 'target-file'):
        p.add_argument('--' + name, type=Path)
    for name in ('policy-inputs-sha256', 'registration-inputs-sha256', 'identity', 'backend'):
        p.add_argument('--' + name)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    stack = ExitStack()
    try:
        bound = binding(args)
        require(args.workspace is not None and args.git_repo is not None, 'selected registration requires workspace and exact Git repository')
        workspace = no_symlinks(args.workspace)
        repo = no_symlinks(args.git_repo)
        require(Path(git(repo, 'rev-parse', '--show-toplevel')).resolve() == repo.resolve(), 'git-repo must be exact worktree root')
        target = no_symlinks(args.target_file or workspace / '.claude/settings.json')
        require(target.resolve().is_relative_to(workspace.resolve()), 'settings path escapes selected workspace')
        if args.recover:
            require(args.action == 'install', 'recovery uses the installer')
            recover(repo, target)
            print(json.dumps({'state': 'recovered', 'authorization_effect': 'none'}))
            return 0
        pending = Path(git(repo, 'rev-parse', '--git-path', 'selected-registration-pending.json'))
        if not pending.is_absolute():
            pending = repo / pending
        require(not pending.exists(), 'interrupted registration requires installer --recover')
        definition = verify_package(bound)
        if args.generation_store is not None:
            generation = generation_module()
            active = stack.enter_context(generation.consume(no_symlinks(args.generation_store)))
            require(all(bound.get(k) == v for k, v in active['binding'].items()), 'registration differs from active generation')
            bound['generation_store'] = str(args.generation_store.absolute())
            bound['generation_settings_shape'] = generation.settings_shape(Path(bound['hooks_root']))
            prior = git(repo, 'config', '--local', '--get', BINDING_KEY, optional=True)
            if prior is not None:
                bootstrap = ep.parse_json(prior, 'registered generation bootstrap')
                require(bootstrap.get('generation_store') == bound['generation_store']
                        and bootstrap.get('identity') == bound['identity']
                        and bootstrap.get('git_repo') == bound['git_repo'], 'different generation registration')
                with generation_binding(bootstrap):
                    bound = bootstrap
        native = str(Path(bound['hooks_root']) / '.githooks')
        config = Path(git(repo, 'rev-parse', '--git-path', 'config'))
        if not config.is_absolute():
            config = repo / config
        config_before = no_symlinks(config).read_bytes()
        old_native = git(repo, 'config', '--get', 'core.hooksPath', optional=True)
        old_binding = git(repo, 'config', '--local', '--get', BINDING_KEY, optional=True)
        expected_binding = json.dumps(bound, sort_keys=True)
        require(old_native in (None, native), 'existing native registration differs')
        require(old_binding in (None, expected_binding), 'stale or mixed native registration')
        if old_native is None:
            default = Path(git(repo, 'rev-parse', '--git-path', 'hooks'))
            if not default.is_absolute():
                default = repo / default
            require(not any(p.is_file() and os.access(p, os.X_OK) and not p.name.endswith('.sample') for p in default.glob('*')),
                    'existing executable Git hooks would be displaced')
        settings_before = target.read_bytes() if target.exists() else None
        existing = ep.parse_json(settings_before, 'operator settings') if settings_before is not None else {}
        incoming = render_settings(bound)
        merged = merge_settings(existing, incoming)
        if args.action in ('wire', 'verify'):
            require(target.is_file() and merged == existing, 'selected settings are missing or changed')
            require(old_native == native and old_binding == expected_binding, 'native registration missing or changed')
        else:
            publish(repo, target, merged, native, expected_binding, settings_before, config_before)
        print(json.dumps({'state': 'configured', 'backend': BACKEND, 'adapter': definition['adapter'],
                          'identity': bound['identity'], 'authorization_effect': 'none',
                          'host_invocation': 'unobserved', 'provider_authority': 'unobserved'}, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(json.dumps({'state': 'error', 'diagnostic': str(exc), 'authorization_effect': 'none'}), file=sys.stderr)
        return 1
    finally:
        stack.close()


def publish(repo, target, merged, native, bound, settings_before, config_before):
    """Stage settings and Git config, restoring old bytes on a failed publication."""
    config = Path(git(repo, 'rev-parse', '--git-path', 'config'))
    if not config.is_absolute():
        config = repo / config
    no_symlinks(config)
    target.parent.mkdir(parents=True, exist_ok=True)
    journal = config.parent / 'selected-registration-pending.json'
    require(not journal.exists(), 'interrupted registration requires recovery before retry')
    lock_fd = os.open(config.parent / 'selected-registration.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not journal.exists(), 'interrupted registration requires recovery before retry')
        no_symlinks(target)
        no_symlinks(config)
        before = target.read_bytes() if target.exists() else None
        require(before == settings_before, 'operator settings changed before publication')
        old_config = config.read_bytes()
        require(old_config == config_before, 'Git config changed before publication')
        config_lock = config.with_name(config.name + '.lock')
        require(not config_lock.exists() and not config_lock.is_symlink(), 'Git config is locked')
        with tempfile.TemporaryDirectory(prefix='.registration-stage-', dir=config.parent) as raw:
            staged_config = Path(raw) / 'config'
            staged_config.write_bytes(old_config)
            staged_config.chmod(config.stat().st_mode & 0o777)
            for key, value in ((BINDING_KEY, bound), ('core.hooksPath', native)):
                subprocess.run(['git', 'config', '--file', str(staged_config), key, value], check=True, timeout=30)
            staged_settings = target.parent / ('.selected-settings-' + Path(raw).name)
            staged_settings.write_bytes(ep.canonical_json(merged) + b'\n')
            staged_settings.chmod(target.stat().st_mode & 0o777 if target.exists() else 0o600)
            with journal.open('xb') as stream:
                journal.chmod(0o600)
                stream.write(ep.canonical_json({'settings': str(target), 'settings_bytes': before.hex() if before is not None else None,
                    'config_bytes': old_config.hex(), 'new_settings': staged_settings.read_bytes().hex(),
                    'new_config': staged_config.read_bytes().hex(), 'staged_settings': str(staged_settings)}))
                stream.flush()
                os.fsync(stream.fileno())
            try:
                # An exclusive hard link acquires Git's lock with complete
                # staged bytes; interruption cannot leave a half-written lock.
                os.link(staged_config, config_lock)
                require(config.read_bytes() == old_config and (target.read_bytes() if target.exists() else None) == before,
                        'operator state changed during registration')
                os.replace(staged_settings, target)
                os.replace(config_lock, config)
                journal.unlink()
            except BaseException:
                # Restore on errors including an ordinary termination exception.
                # SIGKILL leaves the journal, which native entrypoints reject.
                # Do not overwrite a concurrent operator edit or a foreign lock.
                if config.read_bytes() == staged_config.read_bytes():
                    config.write_bytes(old_config)
                if target.exists() and target.read_bytes() == ep.canonical_json(merged) + b'\n':
                    if before is None:
                        target.unlink()
                    else:
                        target.write_bytes(before)
                journal.unlink(missing_ok=True)
                raise
            finally:
                staged_settings.unlink(missing_ok=True)
                if config_lock.is_file() and not config_lock.is_symlink() and config_lock.read_bytes() == staged_config.read_bytes():
                    config_lock.unlink()


def recover(repo, target):
    """Restore only the journaled prior state; a foreign edit blocks recovery."""
    config = Path(git(repo, 'rev-parse', '--git-path', 'config'))
    if not config.is_absolute():
        config = repo / config
    no_symlinks(config)
    journal = config.parent / 'selected-registration-pending.json'
    no_symlinks(journal)
    require(journal.is_file(), 'no interrupted registration journal')
    fd = os.open(config.parent / 'selected-registration.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        record = ep.read_json(journal)
        ep.exact_fields(record, {'settings', 'settings_bytes', 'config_bytes', 'new_settings', 'new_config', 'staged_settings'}, 'registration journal')
        require(record['settings'] == str(target), 'recovery target differs from pending registration')
        old_settings = bytes.fromhex(record['settings_bytes']) if record['settings_bytes'] is not None else None
        old_config = bytes.fromhex(record['config_bytes'])
        current = target.read_bytes() if target.exists() else None
        require(current in (old_settings, bytes.fromhex(record['new_settings']))
                and config.read_bytes() in (old_config, bytes.fromhex(record['new_config'])),
                'operator state changed after interruption; refusing recovery overwrite')
        staged = Path(record['staged_settings'])
        require(staged.parent == target.parent and staged.name.startswith('.selected-settings-'), 'invalid staged settings path')
        no_symlinks(staged)
        config_lock = config.with_name(config.name + '.lock')
        no_symlinks(config_lock)
        require(not config_lock.exists() or config_lock.read_bytes() == bytes.fromhex(record['new_config']),
                'foreign Git config lock blocks recovery')
        config.write_bytes(old_config)
        if old_settings is None:
            target.unlink(missing_ok=True)
        else:
            target.write_bytes(old_settings)
        staged.unlink(missing_ok=True)
        config_lock.unlink(missing_ok=True)
        journal.unlink()


if __name__ == '__main__':
    raise SystemExit(main())
