#!/usr/bin/env python3
"""Selected registration through normal public commands and real local Git."""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('selection_tests', ROOT / 'bin/_test/package_selection_test.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
selected = fixtures.selected


class SelectedRegistrationTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.PackageSelectionTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.source = self.fixture.source
        self.output = self.fixture.output
        self.identity = self.fixture.fixture.identity
        self.policy_source = self.fixture.fixture.fixture.source
        self.policy_pin = self.fixture.fixture.fixture.pin
        self.fixture.selection['backend'] = 'claude-code-local'
        self.fixture.selection['required_capabilities'] = ['native-git', 'settings']
        self.definition = {
            'schema_version': 1, 'backend': 'claude-code-local', 'identity': self.identity,
            'workflow_profile': 'independent', 'selection_sha256': selected.effective.digest(self.fixture.selection),
            'policy_inputs': {'source': self.policy_source.as_posix(), 'sha256': self.policy_pin},
            'adapter': 'policy', 'protected_targets': ['release', 'trunk'],
            'runtime': None, 'settings_source': None,
        }
        self.registration_source = Path('project/registration.json')
        self.write_definition()

    def write_definition(self):
        self.registration_pin = selected.effective.digest(self.definition)
        p = self.source / self.registration_source
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.definition))

    def build(self):
        return self.fixture.build(extra=['--registration-inputs', str(self.registration_source),
                                        '--registration-inputs-sha256', self.registration_pin])

    def run_cmd(self, command, *, cwd=None, ok=True, input=None):
        result = subprocess.run(command, cwd=cwd or self.source, capture_output=True,
                                text=True, input=input, timeout=120)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def prepare(self):
        result = self.build()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.package = self.output / 'flat'
        self.consumer = self.output.parent / 'consumer'
        self.consumer.mkdir()
        for args in (['init', '--template=', '-q', '-b', 'feature'], ['config', 'user.name', 'Fixture'],
                     ['config', 'user.email', 'fixture@example.invalid'], ['config', 'commit.gpgsign', 'false']):
            self.run_cmd(['git', *args], cwd=self.consumer)
        self.settings = self.consumer / '.claude/settings.json'
        self.settings.parent.mkdir()
        self.original_settings = {'model': 'operator-choice', 'permissions': {'deny': ['fixture']},
            'hooks': {'UserPromptSubmit': [{'hooks': [{'type': 'command', 'command': 'operator-command'}]}]}}
        self.settings.write_text(json.dumps(self.original_settings))
        self.remote = self.output.parent / 'remote.git'
        self.run_cmd(['git', 'init', '--template=', '-q', '--bare', str(self.remote)])
        self.run_cmd(['git', 'remote', 'add', 'origin', str(self.remote)], cwd=self.consumer)

    def arguments(self):
        return ['--selected', '--source', str(self.source), '--selection', str(self.source / 'selected-build.json'),
                '--policy-root', str(self.source), '--policy-inputs', str(self.policy_source),
                '--policy-inputs-sha256', self.policy_pin, '--registration-inputs', str(self.registration_source),
                '--registration-inputs-sha256', self.registration_pin, '--identity', self.identity,
                '--backend', 'claude-code-local', '--hooks-root', str(self.package),
                '--workspace', str(self.consumer), '--git-repo', str(self.consumer)]

    def entry(self, action, *, ok=True, extra=()):
        commands = {'install': ['bash', str(self.source / 'bin/install-hooks.sh')],
                    'wire': [sys.executable, '-B', str(self.source / 'bin/wire-enforcement.py')],
                    'verify': ['bash', str(self.source / 'bin/verify-enforcement.sh')]}
        return self.run_cmd([*commands[action], *self.arguments(), *extra], ok=ok)

    def refs(self):
        return self.run_cmd(['git', 'ls-remote', '--heads', str(self.remote)]).stdout

    def test_normal_install_wire_verify_and_real_git_decisions(self):
        self.prepare()
        for action in ('install', 'wire', 'verify'):
            self.entry(action)
        first = self.settings.read_bytes()
        self.entry('install')
        self.assertEqual(self.settings.read_bytes(), first)
        settings = json.loads(first)
        for key in ('model', 'permissions'):
            self.assertEqual(settings[key], self.original_settings[key])
        self.assertEqual(settings['hooks']['UserPromptSubmit'][0]['hooks'][0], self.original_settings['hooks']['UserPromptSubmit'][0]['hooks'][0])
        self.run_cmd(['git', 'commit', '--allow-empty', '-qm', 'No ticket or review trailers'], cwd=self.consumer)
        head = self.run_cmd(['git', 'rev-parse', 'HEAD'], cwd=self.consumer).stdout.strip()
        self.run_cmd(['git', 'push', 'origin', 'HEAD:trunk'], cwd=self.consumer)
        self.assertIn(head + '\trefs/heads/trunk', self.refs())
        self.run_cmd(['git', 'push', 'origin', 'HEAD:develop'], cwd=self.consumer)
        before = self.refs()
        denied = self.run_cmd(['git', 'push', 'origin', 'HEAD:release'], cwd=self.consumer, ok=False)
        self.assertNotEqual(denied.returncode, 0, denied.stdout + denied.stderr)
        self.assertIn('policy denied', denied.stderr)
        self.assertEqual(self.refs(), before)

    def test_changed_inventory_receipts_and_commands_preserve_operator_state(self):
        self.prepare()
        before = self.settings.read_bytes()
        for name in ('bin/native_git.py', '.githooks/pre-push', 'selected-build.json', 'selected-registration.json'):
            path = self.package / name
            original = path.read_bytes()
            path.write_bytes(original + b'\nchanged')
            result = self.entry('install', ok=False)
            self.assertNotEqual(result.returncode, 0, name)
            self.assertIn('inventory/bytes differ', result.stderr)
            self.assertEqual(self.settings.read_bytes(), before)
            self.assertEqual(self.run_cmd(['git', 'config', '--get', 'core.hooksPath'], cwd=self.consumer, ok=False).returncode, 1)
            path.write_bytes(original)
        snippet = self.package / 'hooks/settings-snippet.json'
        original = snippet.read_bytes()
        for replacement in ('sh -c true', 'python3 -B ${package}/bin/native_git.py prompt; echo appended'):
            value = json.loads(original)
            value['hooks']['UserPromptSubmit'][0]['hooks'][0]['command'] = replacement
            snippet.write_text(json.dumps(value))
            self.assertNotEqual(self.entry('install', ok=False).returncode, 0)
            self.assertEqual(self.settings.read_bytes(), before)
        snippet.write_bytes(original)
        self.entry('install')
        installed = self.settings.read_bytes()
        for suffix in ('; echo appended', ' extra'):
            value = json.loads(installed)
            value['hooks']['UserPromptSubmit'][-1]['hooks'][-1]['command'] += suffix
            self.settings.write_text(json.dumps(value))
            changed = self.settings.read_bytes()
            for action in ('install', 'wire', 'verify'):
                self.assertNotEqual(self.entry(action, ok=False).returncode, 0)
                self.assertEqual(self.settings.read_bytes(), changed)
        self.settings.write_bytes(installed)

    def test_misplaced_or_duplicate_managed_commands_reject(self):
        self.prepare()
        self.entry('install')
        installed = json.loads(self.settings.read_text())
        command = installed['hooks']['UserPromptSubmit'][0]['hooks'][-1]
        for misplaced in ('Stop', 'UserPromptSubmit'):
            value = json.loads(json.dumps(installed))
            value['hooks'].setdefault(misplaced, []).append({'hooks': [command]})
            self.settings.write_text(json.dumps(value))
            before = self.settings.read_bytes()
            for action in ('install', 'wire', 'verify'):
                self.assertNotEqual(self.entry(action, ok=False).returncode, 0, misplaced)
                self.assertEqual(self.settings.read_bytes(), before)

    def test_wrong_missing_backend_capability_identity_and_pins(self):
        self.prepare()
        before = self.settings.read_bytes()
        for extra in (['--backend', 'pi'], ['--identity', 'github.example.invalid/foreign/repo'],
                      ['--registration-inputs-sha256', '0' * 64], ['--policy-inputs-sha256', '0' * 64]):
            result = self.entry('install', ok=False, extra=extra)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertEqual(self.settings.read_bytes(), before)
        shutil.rmtree(self.output)
        self.fixture.selection['required_capabilities'].append('missing-provider')
        self.definition['selection_sha256'] = selected.effective.digest(self.fixture.selection)
        self.write_definition()
        self.assertNotEqual(self.build().returncode, 0)
        self.assertFalse(self.output.exists())
        self.fixture.selection['required_capabilities'] = ['native-git', 'settings']
        self.definition['selection_sha256'] = selected.effective.digest(self.fixture.selection)
        for adapter in (None, 'missing-adapter'):
            self.definition['adapter'] = adapter
            self.write_definition()
            self.assertNotEqual(self.build().returncode, 0)
            self.assertFalse(self.output.exists())

    def test_symlinks_extra_paths_and_existing_native_hooks_reject(self):
        self.prepare()
        before = self.settings.read_bytes()
        extra = self.package / 'extra'
        extra.write_text('unexpected')
        self.assertNotEqual(self.entry('install', ok=False).returncode, 0)
        extra.unlink()
        helper = self.package / 'bin/native_git.py'
        original = helper.read_bytes()
        external = self.output.parent / 'external.py'; external.write_bytes(original)
        helper.unlink(); helper.symlink_to(external)
        self.assertNotEqual(self.entry('install', ok=False).returncode, 0)
        self.assertEqual(self.settings.read_bytes(), before)
        helper.unlink(); helper.write_bytes(original); helper.chmod((self.source / 'bin/native_git.py').stat().st_mode)
        prior = self.consumer / '.git/hooks/pre-push'; prior.parent.mkdir(exist_ok=True)
        prior.write_text('#!/bin/sh\nexit 1\n'); prior.chmod(0o755)
        self.assertNotEqual(self.entry('install', ok=False).returncode, 0)
        self.assertEqual(prior.read_text(), '#!/bin/sh\nexit 1\n')
        self.assertEqual(self.settings.read_bytes(), before)

    def test_runtime_binding_drift_and_prior_locks_fail_closed(self):
        self.prepare()
        before = self.settings.read_bytes()
        lock = self.consumer / '.git/config.lock'
        lock.write_text('operator lock')
        self.assertNotEqual(self.entry('install', ok=False).returncode, 0)
        self.assertEqual(lock.read_text(), 'operator lock')
        self.assertEqual(self.settings.read_bytes(), before)
        lock.unlink()
        self.entry('install')
        self.run_cmd(['git', 'commit', '--allow-empty', '-qm', 'Original no-ticket decision'], cwd=self.consumer)
        original = self.run_cmd(['git', 'rev-parse', 'HEAD'], cwd=self.consumer).stdout
        for name in ('selected-registration.json', 'hooks/settings-snippet.json'):
            path = self.package / name
            content = path.read_bytes()
            path.write_bytes(content + b' ')
            denied = self.run_cmd(['git', 'commit', '--allow-empty', '-qm', 'Must refuse changed inventory'], cwd=self.consumer, ok=False)
            self.assertNotEqual(denied.returncode, 0)
            self.assertIn('inventory/bytes changed', denied.stderr)
            self.assertEqual(self.run_cmd(['git', 'rev-parse', 'HEAD'], cwd=self.consumer).stdout, original)
            path.write_bytes(content)
        declaration = self.source / self.registration_source
        content = declaration.read_bytes()
        value = json.loads(content); value['identity'] = 'github.example.invalid/foreign/repo'
        declaration.write_text(json.dumps(value))
        self.assertNotEqual(self.run_cmd(['git', 'commit', '--allow-empty', '-qm', 'Mixed external input'], cwd=self.consumer, ok=False).returncode, 0)
        declaration.write_bytes(content)
        bound = self.run_cmd(['git', 'config', '--get', 'scaffold.registration'], cwd=self.consumer).stdout
        value = json.loads(bound); value['interpreter'] = '/wrong/python'
        self.run_cmd(['git', 'config', 'scaffold.registration', json.dumps(value)], cwd=self.consumer)
        self.assertNotEqual(self.run_cmd(['git', 'commit', '--allow-empty', '-qm', 'Wrong interpreter'], cwd=self.consumer, ok=False).returncode, 0)
        self.assertNotEqual(self.entry('verify', ok=False).returncode, 0)
        self.run_cmd(['git', 'config', 'scaffold.registration', bound.strip()], cwd=self.consumer)
        self.entry('verify')

    def test_selected_content_does_not_activate_its_profile(self):
        self.fixture.bundle('siege')
        self.fixture.selection['backend'] = 'claude-code-local'
        self.fixture.selection['required_capabilities'] = ['native-git', 'settings']
        self.definition['selection_sha256'] = selected.effective.digest(self.fixture.selection)
        self.write_definition()
        self.test_normal_install_wire_verify_and_real_git_decisions()
        self.assertIn('SIEGE_CONTENT_ONLY', (self.package / 'skills/siege--format/SKILL.md').read_text())

    def test_interrupted_publish_blocks_use_and_recovers_prior_bytes(self):
        self.prepare()
        before = self.settings.read_bytes()
        config = self.consumer / '.git/config'
        prior_config = config.read_bytes()
        journal = self.consumer / '.git/selected-registration-pending.json'
        # Exercise the ordinary exception rollback as well as abrupt death.
        code = """import os, sys
sys.path.insert(0, sys.argv[1])
import selected_registration as r
original = os.replace
def fail(source, target):
    if str(target) == sys.argv[2]:
        raise OSError('synthetic config publication failure')
    original(source, target)
os.replace = fail
raise SystemExit(r.main(['install', *sys.argv[3:]]))
"""
        failed = self.run_cmd([sys.executable, '-B', '-c', code, str(self.source / 'bin'), str(config),
                               *self.arguments()], ok=False)
        self.assertEqual(failed.returncode, 1)
        self.assertIn('synthetic config publication failure', failed.stderr)
        self.assertEqual(self.settings.read_bytes(), before)
        self.assertEqual(config.read_bytes(), prior_config)
        self.assertFalse(journal.exists())
        for checkpoint in (str(self.settings), str(config)):
            code = """import os, signal, sys
sys.path.insert(0, sys.argv[1])
import selected_registration as r
original = os.replace
checkpoint = sys.argv[2]
def interrupt(source, target):
    original(source, target)
    if str(target) == checkpoint:
        os.kill(os.getpid(), signal.SIGKILL)
os.replace = interrupt
raise SystemExit(r.main(['install', *sys.argv[3:]]))
"""
            stopped = self.run_cmd([sys.executable, '-B', '-c', code, str(self.source / 'bin'), checkpoint,
                                    *self.arguments()], ok=False)
            self.assertNotEqual(stopped.returncode, 0)
            self.assertTrue(journal.exists())
            for action in ('install', 'wire', 'verify'):
                result = self.entry(action, ok=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('interrupted registration', result.stderr)
            settings = json.loads(self.settings.read_text())
            hook = settings['hooks']['UserPromptSubmit'][0]['hooks'][-1]['command']
            import shlex
            blocked = self.run_cmd(shlex.split(hook), input='{"prompt":"inspect changes"}', ok=False)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn('interrupted registration', blocked.stderr)
            self.entry('install', extra=['--recover'])
            self.assertEqual(self.settings.read_bytes(), before)
            self.assertEqual(config.read_bytes(), prior_config)
            self.assertFalse(journal.exists())
        self.entry('install')
        self.entry('verify')

    def test_selected_protected_adapter_has_no_siege_source_or_promotion(self):
        for relative in ('scripts/ci/protected-policy-range.py', 'scripts/ci/check-branch-topology.sh'):
            destination = self.source / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
        workflow = self.source / '.github/workflows/pr-base-guard.yml'
        workflow.parent.mkdir(parents=True)
        workflow.write_text('name: synthetic configured workflow\n')
        revision = self.fixture.fixture.fixture.commit()
        self.prepare()
        self.run_cmd(['git', 'commit', '--allow-empty', '-qm', 'base'], cwd=self.consumer)
        base = self.run_cmd(['git', 'rev-parse', 'HEAD'], cwd=self.consumer).stdout.strip()
        self.run_cmd(['git', 'commit', '--allow-empty', '-qm', 'No ticket'], cwd=self.consumer)
        head = self.run_cmd(['git', 'rev-parse', 'HEAD'], cwd=self.consumer).stdout.strip()
        self.run_cmd(['git', 'remote', 'set-url', 'origin', 'https://' + self.identity + '.git'], cwd=self.consumer)
        args = [sys.executable, '-B', str(self.source / 'scripts/ci/protected-policy-range.py'),
            '--trusted-root', str(self.source), '--trusted-revision', revision, '--candidate-repo', str(self.consumer),
            '--base', base, '--head', head, '--head-branch', 'feature', '--canonical-identity', self.identity,
            '--executed-workflow-ref', 'independent-org/application/.github/workflows/pr-base-guard.yml@refs/heads/main',
            '--executed-workflow-revision', revision, '--policy-root', str(self.source),
            '--policy-inputs', str(self.policy_source), '--policy-inputs-sha256', self.policy_pin]
        allow = self.run_cmd([*args, '--target-branch', 'trunk'])
        receipt = json.loads(allow.stdout)
        self.assertEqual(receipt['state'], 'eligible')
        self.assertIsNone(receipt['trusted']['compatibility_wrapper'])
        for target in ('develop', 'main', 'release'):
            denied = self.run_cmd([*args, '--target-branch', target], ok=False)
            self.assertEqual(json.loads(denied.stdout)['state'], 'denied')
        missing = self.run_cmd([*args[:-2], '--target-branch', 'trunk'], ok=False)
        self.assertEqual(json.loads(missing.stdout)['state'], 'error')
        self.assertFalse((self.source / 'bundles').exists())

    def test_compatibility_adapter_rejects_a_different_adopted_workflow(self):
        sys.path.insert(0, str(ROOT / 'bin'))
        self.addCleanup(sys.path.remove, str(ROOT / 'bin'))
        registration = selected.module('compatibility_profile_test', ROOT, 'selected_registration.py')
        gc = selected.effective._gate_contract_module()
        definition = {'workflow_profile': 'synthetic-trunk', 'runtime': {
            'revision': self.run_cmd(['git', 'rev-parse', 'HEAD'], cwd=ROOT).stdout.strip()}}
        policy_registration = {'source': gc.SIEGE_INPUTS.as_posix(), 'sha256': gc.SIEGE_INPUTS_SHA256}
        with self.assertRaisesRegex(ValueError, 'cannot implement selected workflow profile'):
            registration.siege_compatibility_package(ROOT, definition, policy_registration, self.output.parent)

    def test_independent_registration_build(self):
        for name in ('bundles', 'skills', 'hooks', '.githooks', 'examples', 'craft-agent'):
            self.assertFalse((self.source / name).exists(), name)
        result = self.build()
        self.assertEqual(result.returncode, 0, result.stderr)
        for layout in ('nested', 'flat'):
            package = self.output / layout
            self.assertTrue((package / 'hooks/settings-snippet.json').is_file())
            self.assertTrue((package / '.githooks/commit-msg').is_file())
            self.assertTrue((package / '.githooks/pre-push').is_file())
            receipt = json.loads((package / 'selected-registration.json').read_text())
            self.assertEqual(receipt['authorization_effect'], 'none')
            self.assertEqual(receipt['state'], 'unregistered')


if __name__ == '__main__':
    unittest.main()
