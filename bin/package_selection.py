"""Verify local selected build inputs without establishing policy or host authority.

Resolver-only output remains composition-only. The explicit claude-code-local
backend adds an unregistered inventory for the selected installer to verify.
Neither output establishes policy authority, release or generation activation.
"""
from __future__ import annotations

import fcntl
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def module(name, root, filename):
    spec = importlib.util.spec_from_file_location(name, root / 'bin' / filename)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


snapshot = module('selection_snapshot', ROOT, 'source_snapshot.py')
effective = module('selection_policy', ROOT, 'effective_policy.py')
require = snapshot.require
SCAFFOLD_FILES = (
    'bin/build.py', 'bin/compose-project.py', 'bin/effective_policy.py',
    'bin/gate_contract.py', 'bin/package_selection.py',
    'bin/procedure_composition.py', 'bin/resolve-load-set.py',
    'bin/source_snapshot.py', 'catalog/gate-contract-schema.json',
    'bin/selected_registration.py', 'bin/native_git.py', 'bin/install-hooks.sh',
    'bin/wire-enforcement.py', 'bin/verify-enforcement.sh',
)


def path(value):
    require(isinstance(value, str) and '\\' not in value and '\x00' not in value,
            'invalid selected source path')
    return snapshot.relative(value).as_posix()


def prefix(root, name):
    return path(name if root == '.' else root + '/' + name)


def file_inventory(files):
    return {name: {'sha256': hashlib.sha256(data).hexdigest(), 'executable': executable}
            for name, (data, executable) in sorted(files.items())}


def component_files(root, revision, paths):
    require(isinstance(paths, list) and paths and all(isinstance(p, str) for p in paths),
            'component paths must be a nonempty list')
    require(paths == sorted(set(paths)), 'component paths must be unique and sorted')
    result = {}
    for selected in paths:
        path(selected)
        found = snapshot.git_files(root, revision, selected)
        require(not set(found) & set(result), 'overlapping component paths')
        result.update(found)
    return result


def describe_component(root, ident, revision, paths):
    """Create a content pin for review; this cannot create a trusted policy pin."""
    files = component_files(root, revision, paths)
    return {'id': ident, 'revision': revision, 'paths': paths,
            'sha256': effective.digest(file_inventory(files))}


def verify_component(root, value, label):
    effective.exact_fields(value, {'id', 'revision', 'paths', 'sha256'}, label)
    require(isinstance(value['id'], str) and effective.ID.fullmatch(value['id']),
            f'{label}: invalid component identity')
    files = component_files(root, value['revision'], value['paths'])
    require(effective.digest(file_inventory(files)) == value['sha256'],
            f'{label}: component digest differs from selected bytes')
    return files


def selected_inputs(root, selection, *, policy_root, policy_source, policy_sha256,
                    registration_source=None, registration_sha256=None):
    """Return verified source bytes and consistency receipts; never a trust root."""
    effective.exact_fields(selection, {'schema_version', 'identity', 'content_root', 'content',
                                     'scaffold', 'bundles', 'project', 'workflow_profile',
                                     'backend', 'required_capabilities'}, 'selected build')
    require(type(selection['schema_version']) is int and selection['schema_version'] == 1,
            'unsupported selected build schema')
    require(selection['backend'] in ('resolver-only', 'claude-code-local'), 'unsupported selected build backend')
    requirements = selection['required_capabilities']
    require(isinstance(requirements, list) and all(isinstance(item, str) for item in requirements),
            'required_capabilities must be a list of identifiers')
    require(policy_root is not None and policy_source is not None and policy_sha256 is not None,
            'independent policy registration root, source and digest are required')
    if selection['backend'] == 'resolver-only':
        require(not requirements, 'missing implemented registration adapter: ' + ', '.join(requirements))
        require(registration_source is None and registration_sha256 is None, 'resolver-only cannot register adapters')
    else:
        require(requirements == ['native-git', 'settings'], 'missing or unsupported selected registration capability')
        registration = module('selected_registration', ROOT, 'selected_registration.py')
        registration.load_definition(root, selection, policy_root, policy_source, policy_sha256,
                                     registration_source, registration_sha256)
    require(policy_source is not None and policy_sha256 is not None,
            'independent policy registration source and digest are required')
    require(isinstance(selection['identity'], str), 'selected identity must be a canonical repository string')
    loaded = effective.load_registered_inputs(policy_root, registration_source=policy_source,
                                              registration_sha256=policy_sha256)
    resolved = effective.explain(loaded['contract'], loaded['policy'], loaded['selection'],
                                 effective.default_context(selection['identity'], []),
                                 {'type': 'review-procedure'},
                                 selection_source=loaded['registration']['selection_source'])
    require(resolved['state'] == 'resolved', 'selected identity is not in independently approved policy')
    require(selection['identity'] == '/'.join(resolved['repository_identity'][key] for key in ('host', 'owner', 'repository')),
            'selected identity must be canonical')
    require(selection['workflow_profile'] == resolved['organization_profile'],
            'workflow profile differs from independently approved adoption')
    content_root = selection['content_root']
    if content_root != '.':
        path(content_root)
    files = verify_component(root, selection['scaffold'], 'scaffold')
    require(selection['scaffold']['paths'] == sorted(SCAFFOLD_FILES)
            and set(files) == set(SCAFFOLD_FILES), 'scaffold source closure differs')
    for name, (data, executable) in files.items():
        current = ROOT / name
        require(not current.is_symlink() and current.is_file()
                and current.read_bytes() == data
                and bool(current.stat().st_mode & 0o111) == executable,
                f'run matching selected scaffold tools: {name}')
    project = selection['project']
    require(isinstance(project, dict), 'project component must be an object')
    require(project.get('id') == resolved['project'], 'project identity differs from approved policy')
    require(project.get('paths') == [prefix(content_root, 'projects/' + resolved['project'])],
            'project source must be exactly the selected project directory')
    project_files = verify_component(root, project, 'project')
    require(not set(files) & set(project_files), 'project overlaps scaffold')
    files.update(project_files)
    require(isinstance(selection['bundles'], list), 'bundles must be an ordered list')
    ids, publishers, components = set(), [], [{'role': 'scaffold', **selection['scaffold']},
                                             {'role': 'project', **project}]
    for bundle in selection['bundles']:
        effective.exact_fields(bundle, {'component', 'descriptor'}, 'selected bundle')
        component = bundle['component']
        owned = verify_component(root, component, 'bundle')
        ident = component['id']
        require(ident not in ids, f'duplicate bundle identity: {ident}')
        ids.add(ident)
        descriptor = path(bundle['descriptor'])
        require(descriptor in owned, f'bundle {ident}: descriptor is outside pinned component')
        declared = effective.parse_json(owned[descriptor][0], descriptor)
        effective.exact_fields(declared, {'schema_version', 'id', 'publisher', 'requires_profiles'}, descriptor)
        require(type(declared['schema_version']) is int and declared['schema_version'] == 1,
                f'{descriptor}: unsupported bundle schema')
        require(declared['id'] == ident, f'{descriptor}: bundle identity differs')
        publisher = declared['publisher']
        effective.exact_fields(publisher, {'id', 'skills_root', 'qualified'}, 'bundle publisher')
        require(publisher['id'] == ident, f'{descriptor}: publisher differs from bundle identity')
        skills_root = prefix(content_root, path(publisher['skills_root']))
        require(component['paths'] == sorted([descriptor, skills_root]),
                f'{descriptor}: bundle must pin exactly its descriptor and published content')
        profiles = declared['requires_profiles']
        require(isinstance(profiles, list) and all(isinstance(p, str) and effective.ID.fullmatch(p) for p in profiles)
                and len(set(profiles)) == len(profiles), f'{descriptor}: invalid required profiles')
        require(set(profiles) <= {selection['workflow_profile']},
                f'{descriptor}: unmet workflow profile dependency: ' + ', '.join(sorted(set(profiles) - {selection['workflow_profile']})))
        require(not set(files) & set(owned), f'bundle {ident}: overlapping component ownership')
        files.update(owned)
        publishers.append(publisher)
        components.append({'role': 'bundle', **component, 'descriptor': descriptor})
    require(isinstance(selection['content'], dict)
            and selection['content'].get('publishers') == publishers,
            'selected content publishers differ from pinned bundle declarations')
    require(len({name.casefold() for name in files}) == len(files), 'case-colliding selected source paths')
    return files, {'schema_version': 1, 'selection_sha256': effective.digest(selection),
                   'identity': selection['identity'], 'components': components,
                   'workflow_profile': selection['workflow_profile'],
                   'policy_registration': loaded['registration'], 'policy': resolved,
                   'source_files': file_inventory(files), 'backend': selection['backend'],
                   'artifact_scope': 'composition-only', 'registration_state': 'unsupported-unverified',
                   'observed_capabilities': [], 'evidence_state': 'configured', 'authorization_effect': 'none'}


def build(root, destination, selection, *, policy_root, policy_source, policy_sha256, check=False,
          registration_source=None, registration_sha256=None):
    """Drive the existing composer with only the selected immutable source closure.

    Serialize cooperating publishers in the destination parent. Composer failure
    leaves no destination. Publication is one directory rename after validation.
    The receipt is consistency evidence, never an installation or generation lock.
    """
    files, receipt = selected_inputs(root, selection, policy_root=policy_root,
                                     policy_source=policy_source, policy_sha256=policy_sha256,
                                     registration_source=registration_source, registration_sha256=registration_sha256)
    definition = runtime = None
    if selection['backend'] != 'resolver-only':
        registration = module('selected_registration', ROOT, 'selected_registration.py')
        definition, runtime = registration.load_definition(root, selection, policy_root, policy_source,
            policy_sha256, registration_source, registration_sha256)
        receipt.update(artifact_scope='registration-package', registration_state='unregistered')
        registration.no_symlinks(destination)
        ownership = module('registration_source_ownership', ROOT, 'compose-project.py').GeneratedFiles()
        for name, (data, _) in files.items():
            ownership.add(name, data, 'selected source ' + name)
    destination = destination.absolute()
    require(not destination.is_symlink() and not destination.exists(), 'selected build destination already exists')
    destination.parent.mkdir(parents=True, exist_ok=True)
    parent = destination.parent.resolve()
    destination = parent / destination.name
    lock_path = parent / '.selected-build.lock'
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        require(not destination.exists() and not destination.is_symlink(), 'selected build destination already exists')
        with tempfile.TemporaryDirectory(prefix='.selected-build-', dir=parent) as temporary:
            temporary = Path(temporary)
            source = temporary / 'source'
            for name, (data, executable) in files.items():
                target = source / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                target.chmod(0o755 if executable else 0o644)
            composer = module('selected_composer', source, 'compose-project.py')
            output = temporary / 'output'
            composer.package(source / selection['content_root'], output, selection['identity'],
                             policy_root=policy_root, policy_registration_source=policy_source,
                             policy_registration_sha256=policy_sha256, content_selection=selection['content'])
            for layout in ('nested', 'flat'):
                composed = effective.read_json(output / layout / 'composition.json')
                require(composed['policy'] == receipt['policy'], 'composed policy differs from selected registration')
                (output / layout / 'selected-build.json').write_bytes(effective.canonical_json(receipt))
            if definition is not None:
                if definition['adapter'] == 'siege-compatibility':
                    runtime = registration.siege_compatibility_package(root, definition, receipt['policy_registration'], temporary)
                registration.extend_package(output, files, receipt, definition, runtime, composer,
                                            registration_source, registration_sha256)
            require(effective.load_registered_inputs(policy_root, registration_source=policy_source,
                                                     registration_sha256=policy_sha256)['registration']
                    == receipt['policy_registration'], 'policy registration changed during build')
            if definition is not None:
                current, _ = registration.load_definition(root, selection, policy_root, policy_source, policy_sha256,
                    registration_source, registration_sha256)
                require(current == definition, 'registration changed during build')
            if not check:
                require(not destination.exists() and not destination.is_symlink(), 'selected build destination appeared during build')
                os.rename(output, destination)
    return receipt
