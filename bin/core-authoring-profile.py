#!/usr/bin/env python3
"""Enroll released canonical Core guards without changing CLI or Git settings."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
IDENTITY = 'github.com/siege-analytics/claude-configs-public'
PURPOSE = 'canonical-core-authoring/v1'
POLICY = 'core-authoring-policy.json'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n').encode()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def physical(path):
    path = path.absolute()
    require(not any(parent.is_symlink() for parent in (path, *path.parents)), 'profile path must be physical')
    return path


def verify_runtime(bound):
    """Check the installed adoption snapshot after the bootstrap's package hash."""
    require(bound['profile'] == PURPOSE and bound['identity'] == IDENTITY,
            'not an enrolled canonical Core authoring profile')
    interpreter = Path(bound['interpreter'])
    require(interpreter.is_absolute() and interpreter.is_file() and os.access(interpreter, os.X_OK),
            'installed profile interpreter is unavailable')
    require(re.fullmatch(r'[0-9a-f]{40}', bound['revision']), 'invalid installed Core source revision')
    package = physical(Path(bound['hooks_root']))
    require(package == ROOT, 'profile verifier is outside its enrolled package')
    raw = (package / POLICY).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == bound['policy_snapshot_sha256'], 'installed policy snapshot changed')
    policy = json.loads(raw)
    require(policy['purpose'] == PURPOSE and policy['identity'] == IDENTITY and policy['revision'] == bound['revision'],
            'installed Core policy identity/revision differs')
    require(policy['registration']['source'] == 'bundles/siege/policy-inputs.json'
            and policy['registration']['sha256'] == bound['policy_inputs_sha256'], 'installed policy pin differs')
    resolved = policy['resolved']
    require(resolved['state'] == 'resolved' and resolved['project'] == 'claude-configs-public'
            and resolved['organization_profile'] == 'strict-release', 'installed canonical Core adoption differs')
    template = (package / 'hooks/settings-snippet.json').read_bytes()
    require(hashlib.sha256(template).hexdigest() == bound['settings_sha256'], 'installed canonical settings changed')
    require(set(json.loads(template)['hooks']) == {'UserPromptSubmit', 'PreToolUse', 'PostToolUse', 'PostToolUseFailure'},
            'installed Core profile lacks canonical events')
    return {'adapter': 'siege-compatibility', 'settings_source': 'hooks/settings-snippet.json'}


def prepared_package(destination):
    """Use the existing full exporter and actual adopted Core policy, not composition."""
    sys.path.insert(0, str(ROOT / 'bin'))
    try:
        build = load(ROOT / 'bin/build.py', 'core_authoring_build')
        def current_revision():
            try:
                revision = build.validate_deploy_source(ROOT)
            except build.BuildError as error:
                raise ValueError(str(error)) from error
            require(revision, 'Core profile publication requires clean exact-main source')
            return revision
        revision = current_revision()
        def fresh():
            require(current_revision() == revision, 'Main changed during Core profile preparation')
        source = build._deploy_source_files(ROOT, revision)
        registration = load(ROOT / 'bin/selected_registration.py', 'core_authoring_export')
        ep = registration.ep
        gc = ep._gate_contract_module()
        adopted = ep.load_registered_inputs(ROOT, registration_source=gc.SIEGE_INPUTS,
                                            registration_sha256=gc.SIEGE_INPUTS_SHA256)
        resolved = ep.explain(adopted['contract'], adopted['policy'], adopted['selection'],
                              ep.default_context(IDENTITY, []), {'type': 'review-procedure'},
                              selection_source=adopted['registration']['selection_source'])
        require(resolved['state'] == 'resolved' and resolved['project'] == 'claude-configs-public'
                and resolved['organization_profile'] == 'strict-release', 'canonical Core policy is not adopted')
        definition = {'adapter': 'siege-compatibility', 'workflow_profile': 'strict-release',
                      'settings_source': 'hooks/settings-snippet.json', 'runtime': {'revision': revision}}
        with tempfile.TemporaryDirectory(prefix='.core-authoring-export-', dir=destination.parent) as raw:
            runtime = registration.siege_compatibility_package(ROOT, definition, adopted['registration'], Path(raw))
        # Authoring retains all canonical source events, including CA failure
        # callbacks omitted from the ordinary Claude Code consumer snippet.
        runtime['hooks/settings-snippet.json'] = source['hooks/settings-snippet.json']
        settings = encoded(registration.settings_template(definition, runtime))
        policy = encoded({'purpose': PURPOSE, 'identity': IDENTITY, 'revision': revision,
                          'registration': adopted['registration'], 'resolved': resolved})
        files = {'compatibility/' + name: value for name, value in runtime.items()}
        files['bin/core-authoring-profile.py'] = source['bin/core-authoring-profile.py']
        files['hooks/settings-snippet.json'] = (settings, False)
        files[POLICY] = (policy, False)
        bound = {'profile': PURPOSE, 'identity': IDENTITY, 'revision': revision,
                       'interpreter': str(Path(sys.executable).absolute()),
                       'policy_inputs_sha256': gc.SIEGE_INPUTS_SHA256,
                       'policy_snapshot_sha256': hashlib.sha256(policy).hexdigest(),
                       'settings_sha256': hashlib.sha256(settings).hexdigest()}
        return files, bound, source['bin/project-settings-bootstrap.py'][0], fresh
    finally:
        sys.path.pop(0)


def publish_package(destination, files):
    require(not destination.exists(), 'use a new versioned Core profile package path')
    temporary = Path(tempfile.mkdtemp(prefix='.core-authoring-', dir=destination.parent))
    try:
        for name, (data, executable) in files.items():
            path = temporary / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            path.chmod(0o755 if executable else 0o644)
        os.rename(temporary, destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)




def require_core_target(repo, revision, bootstrap):
    """Accept Core forks/local remotes, not an unrelated repo holding Core objects."""
    try:
        shared = bootstrap.git(repo, 'merge-base', 'HEAD', revision).strip()
    except ValueError as error:
        raise ValueError('authoring target has no shared Core history') from error
    require(shared, 'authoring target has no shared Core history')
    required = ('bin/build.py', 'hooks/settings-snippet.json', 'catalog/effective-policy.json',
                'bundles/siege/policy-inputs.json')
    for name in required:
        entry = bootstrap.git(repo, 'ls-tree', 'HEAD', '--', name).decode().split()
        require(len(entry) == 4 and entry[0] in {'100644', '100755'} and entry[1] == 'blob' and entry[3] == name,
                'authoring target is not a Core repository root: ' + name)
    adoption = json.loads(bootstrap.git(repo, 'show', 'HEAD:bundles/siege/policy-inputs.json'))
    require(isinstance(adoption, dict) and adoption.get('review_repository') == IDENTITY,
            'authoring target does not declare the Core repository identity')


def project_file_states(roots, bootstrap):
    states = {}
    for root in roots:
        path = root / '.claude/settings.json'
        try:
            value = json.loads(bootstrap.regular(path))
            state = 'prepared-file' if not bootstrap.profile_problems(value) else 'legacy-or-custom-file'
        except (OSError, ValueError, KeyError, TypeError):
            state = 'absent-or-unreadable-file'
        states[str(root)] = {'project': state, 'local_settings_present': (root / '.claude/settings.local.json').exists()}
    return states


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'verify'))
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--workspace', type=Path, help='explicit physical headless policy workspace')
    args = parser.parse_args()
    try:
        repo = physical(args.repo).resolve(strict=True)
        home = physical(args.home).resolve(strict=True)
        package = physical(args.package.parent).resolve(strict=True) / args.package.name
        require(package.name not in {'', '.', '..'} and not package.is_symlink(), 'invalid or symlink profile package path')
        prepared = prepared_package(package) if args.action == 'install' else None
        bootstrap = load(ROOT / 'bin/project-settings-bootstrap.py', 'core_authoring_bootstrap')
        require(Path(os.fsdecode(bootstrap.git(repo, 'rev-parse', '--show-toplevel')).strip()).resolve() == repo,
                'repo must be the actual authoring Git root')
        primary = bootstrap.primary_repository(repo)
        require(args.action != 'install' or primary == repo, 'enroll from the primary repository; linked worktrees reuse it')
        roots = [Path(os.fsdecode(part[len(b'worktree '):])).resolve(strict=True)
                 for part in bootstrap.git(primary, 'worktree', 'list', '--porcelain', '-z').split(b'\0')
                 if part.startswith(b'worktree ')]
        require(not any(package.is_relative_to(root) for root in (*roots, ROOT)),
                'profile package must be outside authoring worktrees and installer source')
        workspace = primary if args.workspace is None else physical(args.workspace).resolve(strict=True)
        require(workspace == primary or not any(workspace.is_relative_to(root) for root in (*roots, ROOT)),
                'headless policy workspace must be outside authoring worktrees and installer source')
        require(workspace.is_dir(), 'policy workspace must be a directory')
        common = bootstrap.common_directory(primary)
        location = bootstrap.anchor_path(home, common, None if workspace == primary else workspace)
        scope = {'mode': 'native-cli'} if workspace == primary else {'mode': 'headless-craft', 'workspace': str(workspace)}
        if args.action == 'verify':
            anchor = json.loads(bootstrap.regular(location))
            require(anchor['schema_version'] == 1 and anchor['purpose'] == 'core-authoring-profile/v1'
                    and anchor['git_common_dir'] == str(common) and anchor['scope'] == scope,
                    'Core authoring enrollment context differs')
            bound = anchor['binding']
            require(bound['git_repo'] == str(primary) and bound['hooks_root'] == str(package),
                    'Core authoring enrollment target differs')
            require(bootstrap.package_digest(package) == bound['package_sha256'], 'installed package bytes changed')
            bootstrap.verify_published(home)
            verifier = load(package / 'bin/core-authoring-profile.py', 'verified_installed_core_profile')
            verifier.verify_runtime(bound)
            require_core_target(primary, bound['revision'], bootstrap)
        else:
            files, bound, helper, fresh = prepared
            fresh()
            require_core_target(primary, bound['revision'], bootstrap)
            if package.exists():
                require(package.is_dir() and not package.is_symlink(), 'profile package must be physical')
                expected = {name: {'sha256': hashlib.sha256(data).hexdigest(), 'executable': executable}
                            for name, (data, executable) in files.items()}
                expected_digest = hashlib.sha256(json.dumps(expected, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
                require(bootstrap.package_digest(package) == expected_digest, 'installed package differs from exact-main export')
            else:
                fresh()
                publish_package(package, files)
            bound.update(git_repo=str(primary), hooks_root=str(package), package_sha256=bootstrap.package_digest(package))
            fresh()
            bootstrap.publish(home, helper, before_publish=fresh)
            bootstrap.publish_anchor(home, bound, workspace)
        print(json.dumps({'state': 'verified' if args.action == 'verify' else 'configured',
                          'identity': IDENTITY, 'revision': bound['revision'],
                          'native_git_registration': 'unchanged', 'global_settings': 'unchanged',
                          'project_settings': 'unchanged', 'authorization_effect': 'none',
                          'enrollment_ready': True, 'project_profile_files': project_file_states(roots, bootstrap),
                          'sdk_profile_active': 'unobserved', 'host_invocation': 'unobserved'}, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, ImportError, subprocess.SubprocessError) as error:
        print('Core authoring profile failed closed: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
