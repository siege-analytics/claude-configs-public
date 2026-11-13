#!/usr/bin/env python3
"""Controlled SDK callbacks retain installed policy while candidate code is broken."""
import contextlib
import importlib.util
import io
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import craft_hook_router_test as fixtures

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('project_bootstrap_fixture', ROOT / 'bin/project-settings-bootstrap.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
sys.path.insert(0, str(ROOT / 'hooks/_test'))
import task_keyed_gates as gates


class Bootstrap(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.Router(methodName='runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.home, self.workspace = self.f.home, self.f.workspace
        self.repo = self.f.fixture.base / 'candidate'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True, timeout=20)
        shutil.copytree(ROOT / 'hooks', self.repo / 'hooks')
        for name in ('task_actions.py', 'resolve-think-gate.py'):
            (self.repo / 'hooks/lib' / name).write_text('else:\nelse:\n')
        self.f.activate()
        self.env = dict(self.f.env, CCP_TASK_ID='example/project#1286')
        self.f.ws, self.f.repo = self.workspace, self.repo
        gates.Gates.task(self.f, 'example/project#1286', self.repo, artifacts=False)
        self.target = self.repo / 'hooks/lib/task_actions.py'

    def payload(self, target=None):
        value = json.loads(self.f.payload(tool='Edit'))
        value['cwd'] = str(self.repo)
        value['tool_input'] = {'file_path': str(target or self.target), 'old_string': 'else:', 'new_string': ''}
        return json.dumps(value).encode()

    def callback(self, raw):
        # Only host ancestry is synthetic. The registered router and actual UMG
        # execute unchanged against real installed bytes and task files.
        original = b.subprocess.run
        def run(vector, **kwargs):
            if len(vector) > 3 and vector[3] == str(self.f.target):
                code, output, error = self.f.main(kwargs['input'])
                if output:
                    print(output, end='')
                if error:
                    print(error, file=sys.stderr, end='')
                return subprocess.CompletedProcess(vector, code)
            return original(vector, **kwargs)
        out, err = io.StringIO(), io.StringIO()
        with patch.object(b, 'craft_process', return_value=True), patch.dict(os.environ, self.env, clear=True), \
             patch.object(b.subprocess, 'run', side_effect=run), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = b.dispatch(raw, 'PreToolUse')
        return code, out.getvalue(), err.getvalue()

    def test_headless_ancestry_requires_exact_executable_and_server_arguments(self):
        proc = self.f.home / 'synthetic-proc'
        process = proc / '42'
        process.mkdir(parents=True)
        (process / 'exe').symlink_to('/app/vendor/bun/bun')
        (process / 'status').write_text('PPid: 0\n')
        argv = ['/app/vendor/bun/bun', 'run', '/app/packages/server/src/index.ts', '--allow-insecure-bind']
        (process / 'cmdline').write_bytes(('\0'.join(argv) + '\0').encode())
        with patch.object(b.sys, 'platform', 'linux'):
            self.assertTrue(b.headless_process(proc, 42))
            (proc / '1').symlink_to(process, target_is_directory=True)
            self.assertTrue(b.headless_process(proc, 1))
            (process / 'cmdline').write_bytes(b'/app/vendor/bun/bun\0run\0other.ts\0')
            self.assertFalse(b.headless_process(proc, 42))
            (process / 'exe').unlink()
            (process / 'exe').symlink_to('/usr/bin/bun')
            (process / 'cmdline').write_bytes(('\0'.join(argv) + '\0').encode())
            self.assertFalse(b.headless_process(proc, 42))

    def test_headless_ancestry_handles_inaccessible_init_without_hiding_other_errors(self):
        with patch.object(b.sys, 'platform', 'linux'), patch.object(b.os, 'readlink', side_effect=PermissionError('init metadata unavailable')) as readlink:
            self.assertFalse(b.headless_process(pid=1))
            readlink.assert_called_once()
            with self.assertRaises(PermissionError):
                b.headless_process(pid=42)

    def test_managed_profile_preserves_operator_policy_and_rejects_duplicates(self):
        settings = b.profile()
        settings['model'] = 'operator-choice'
        settings['hooks']['PreToolUse'].append({'matcher': 'Read', 'hooks': [
            {'type': 'command', 'command': '/bin/sh -c "exit 2"'}]})
        self.assertEqual(b.profile_problems(settings), [])
        settings['hooks']['PreToolUse'].append(b.profile()['hooks']['PreToolUse'][0])
        self.assertTrue(b.profile_problems(settings))

    def test_prepared_profile_remains_inert_before_rollout(self):
        settings = json.loads((ROOT / '.claude/settings.authoring.json').read_text())
        self.assertEqual(settings, b.profile())
        legacy = subprocess.check_output(['/usr/bin/git', 'show', 'bd433bdf5cc8f885ed2a879be269ba8055ba9a20:.claude/settings.json'], cwd=ROOT, timeout=20)
        self.assertEqual((ROOT / '.claude/settings.json').read_bytes(), legacy)

    def test_broken_candidate_does_not_brick_owned_repair_but_real_holds_remain(self):
        result = subprocess.run(['bash', str(self.repo / 'hooks/bash/universal-mutation-gate.sh')],
                                input=self.payload(), capture_output=True, env=self.env, timeout=20)
        self.assertEqual(result.returncode, 2, 'red control must reproduce candidate syntax self-brick')
        self.assertEqual(self.callback(self.payload())[0], 0)
        foreign = self.workspace / 'foreign.py'
        self.assertEqual(self.callback(self.payload(foreign))[0], 2)
        directory = self.workspace / 'sessions/one/tasks' / gates.r.task_slug('example/project#1286')
        data = json.loads((directory / 'think-gate.json').read_text())
        for field, value in (('sessionId', 'foreign-owner'), ('status', 'designing')):
            changed = dict(data, **{field: value})
            (directory / 'think-gate.json').write_text(json.dumps(changed))
            self.assertEqual(self.callback(self.payload())[0], 2, field)
        self.assertEqual(self.target.read_text(), 'else:\nelse:\n', 'candidate code must never be restored or executed')

    def test_missing_startup_and_interpreter_failure_are_sdk_blocking(self):
        command = b.command_for('PreToolUse')
        env = dict(self.env, HOME=str(self.home))
        for text in (None, 'raise RuntimeError("startup fault")\n'):
            target = self.home / b.RELATIVE
            target.parent.mkdir(parents=True, exist_ok=True)
            if text is None:
                target.unlink(missing_ok=True)
            else:
                target.write_text(text)
            result = subprocess.run(command, shell=True, input=self.payload(), capture_output=True, env=env, timeout=20)
            self.assertEqual(result.returncode, 2, result.stderr)
        result = subprocess.run(command, shell=True, input=self.payload(), capture_output=True, env=dict(env, PATH=''), timeout=20)
        self.assertEqual(result.returncode, 2)

    def test_compatibility_json_denial_is_one_preserved_sdk_response(self):
        package = self.f.fixture.base / 'verified-cli-package'
        target = package / 'compatibility/hooks/lib/craft-settings-router.py'
        target.parent.mkdir(parents=True)
        shutil.copy2(ROOT / 'hooks/lib/craft-settings-router.py', target)
        deny = subprocess.run(['/bin/sh', '-c', "printf '%s' '{\"continue\":false,\"systemMessage\":\"policy denial\"}'"], capture_output=True, text=True, timeout=10)
        outputs = [(deny.returncode, deny.stdout, deny.stderr), (0, 'installed context', '')]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = b.emit('UserPromptSubmit', outputs, {'adapter': 'siege-compatibility'}, package)
        self.assertEqual(code, 0)
        value = json.loads(output.getvalue())
        self.assertFalse(value['continue'])
        self.assertIn('policy denial', value['systemMessage'])
        self.assertIn('installed context', value['hookSpecificOutput']['additionalContext'])

    def test_operator_bootstrap_conflict_is_rejected_before_registration_changes(self):
        receipt = self.f.receipt_path.read_bytes()
        target = self.home / b.RELATIVE
        target.write_text('operator-owned code\n')
        with self.assertRaisesRegex(ValueError, 'operator-owned'):
            self.f.activate()
        self.assertEqual(target.read_text(), 'operator-owned code\n')
        self.assertEqual(self.f.receipt_path.read_bytes(), receipt)

    def test_shared_helper_integrity_rejects_stale_publisher_snapshot(self):
        helper, receipt = self.home / b.RELATIVE, self.home / b.RECEIPT
        old = (helper.read_bytes(), receipt.read_bytes())
        replacement = old[0] + b'\n# New verified common ABI generation.\n'
        b.publish(self.home, replacement, expected=old)
        fresh = (helper.read_bytes(), receipt.read_bytes())
        with self.assertRaisesRegex(ValueError, 'changed during activation'):
            b.publish(self.home, old[0] + b'\n# Stale publisher.\n', expected=old)
        self.assertEqual((helper.read_bytes(), receipt.read_bytes()), fresh)
        self.assertEqual(b.verify_published(self.home)['sha256'], hashlib.sha256(replacement).hexdigest())

    def test_shared_dispatcher_upgrade_does_not_change_workspace_policy_binding(self):
        receipt = self.f.receipt_path.read_bytes()
        target = self.home / b.RELATIVE
        # A later reviewed dispatcher generation keeps the fixed event ABI;
        # individual router/policy generations remain independently pinned.
        b.publish(self.home, target.read_bytes() + b'\n')
        self.assertEqual(self.f.receipt_path.read_bytes(), receipt)
        self.assertEqual(self.callback(self.payload())[0], 0)
        self.assertEqual(self.callback(self.payload(self.workspace / 'foreign.py'))[0], 2)

    def test_normal_exports_carry_the_exact_bootstrap(self):
        output = self.f.fixture.base / 'normal-dist'
        result = subprocess.run([sys.executable, str(ROOT / 'bin/build.py'), '--dist', str(output)],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        expected = (ROOT / 'bin/project-settings-bootstrap.py').read_bytes()
        for layout in ('nested', 'flat', 'claude-code', 'craft-agent'):
            self.assertEqual((output / layout / 'bin/project-settings-bootstrap.py').read_bytes(), expected)

    def test_event_and_command_are_not_project_authority(self):
        with self.assertRaises(ValueError):
            b.command_for('Arbitrary')
        with self.assertRaises(ValueError):
            b.dispatch(self.payload(), 'PostToolUse')
        result = subprocess.run([sys.executable, str(ROOT / 'bin/project-settings-bootstrap.py'),
                                 '--event', 'PreToolUse', '--command', 'true'], input=self.payload(), capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 2)

    def test_installer_migration_preserves_operator_deny_and_rejects_wrong_managed_event(self):
        legacy = json.loads((ROOT / 'hooks/settings-snippet.json').read_text())
        for groups in legacy['hooks'].values():
            for group in groups:
                for hook in group['hooks']:
                    hook['command'] = hook['command'].replace('/path/to/claude-configs-public/', '')
        operator = {'matcher': 'Edit', 'hooks': [{'type': 'command', 'command': '/bin/sh -c "exit 2"'}]}
        legacy['hooks']['PreToolUse'].append(operator)
        managed = json.loads(json.dumps(legacy))
        managed['hooks']['PreToolUse'].pop()
        result = b.retire_source(legacy, managed)
        self.assertEqual(result['hooks']['PreToolUse'], [operator])
        destination = self.f.fixture.base / 'project-settings.json'
        destination.write_text(json.dumps(legacy))
        installed = subprocess.run(['bash', str(ROOT / 'bin/install-hooks.sh'), '--relative', '--target-file', str(destination)], capture_output=True, text=True, timeout=20)
        self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)
        actual = json.loads(destination.read_text())
        self.assertIn(operator, actual['hooks']['PreToolUse'])
        self.assertTrue(any(hook.get('command') == 'hooks/bash/universal-mutation-gate.sh'
                            for group in actual['hooks']['PreToolUse'] for hook in group['hooks']))
        self.assertTrue(b.profile_problems(actual), 'legacy installation must not activate an uninstalled bootstrap')
        actual = b.profile()
        actual['hooks']['PostToolUse'].append(actual['hooks']['PreToolUse'][0])
        with self.assertRaisesRegex(ValueError, 'conflicting event'):
            b.retire_source(actual, managed)
        self.assertEqual(self.callback(self.payload())[0], 0)
        denied = subprocess.run(operator['hooks'][0]['command'], shell=True, timeout=10)
        self.assertEqual(denied.returncode, 2)
        wrong = json.loads(json.dumps(managed))
        wrong['hooks']['PostToolUse'] = [wrong['hooks']['PreToolUse'][0]]
        with self.assertRaisesRegex(ValueError, 'conflicting event'):
            b.retire_source(wrong, managed)

    def test_sibling_project_verifier_cannot_execute_before_trusted_selection(self):
        sibling = self.f.fixture.base / 'attacker-package'
        (sibling / 'bin').mkdir(parents=True)
        marker = self.f.fixture.base / 'attacker-executed'
        (sibling / 'bin/core-authoring-profile.py').write_text(
            'from pathlib import Path\nPath(' + repr(str(marker)) + ').write_text("executed")\n')
        fake = {'hooks_root': str(sibling), 'git_repo': str(self.repo), 'package_sha256': '0' * 64}
        subprocess.run(['/usr/bin/git', '-C', str(self.repo), 'config', '--local', 'scaffold.registration', json.dumps(fake)],
                       check=True, timeout=10)
        result = subprocess.run(b.command_for('PreToolUse'), shell=True, input=self.payload(), capture_output=True,
                                cwd=self.repo, env={k: v for k, v in self.env.items() if not k.startswith('CRAFT_')}, timeout=20)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(marker.exists(), 'project config must not select executable verifier code')

    def test_native_cli_missing_profile_fails_without_borrowing_craft(self):
        with patch.object(b, 'craft_process', return_value=False), patch.dict(os.environ, {k: v for k, v in self.env.items() if not k.startswith('CRAFT_')}, clear=True):
            original = Path.cwd()
            try:
                os.chdir(self.repo)
                with self.assertRaisesRegex(ValueError, 'not registered'):
                    b.dispatch(self.payload(), 'PreToolUse')
            finally:
                os.chdir(original)


class CanonicalCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='core1286-canonical-', dir=str(Path(tempfile.gettempdir()).resolve()))
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.base = Path(cls.temporary.name)
        cls.source, cls.package = cls.base / 'source', cls.base / 'runtime-package'
        cls.environment = {k: v for k, v in os.environ.items() if not k.startswith(('CRAFT_', 'CLAUDE_', 'CCP_', 'GIT_'))}
        cls.environment.update(PYTHONDONTWRITEBYTECODE='1', GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1')
        subprocess.run(['/usr/bin/git', 'clone', '--quiet', '--shared', str(ROOT), str(cls.source)],
                       check=True, env=cls.environment, timeout=40)
        def source_git(*args):
            return subprocess.run(['/usr/bin/git', '-C', str(cls.source), *args], check=True,
                                  env=cls.environment, capture_output=True, text=True, timeout=40)
        source_git('config', 'user.name', 'Controlled Core fixture')
        source_git('config', 'user.email', 'fixture@example.invalid')
        source_git('checkout', '-q', '-B', 'main')
        changed = subprocess.check_output(['/usr/bin/git', 'diff', 'HEAD', '--name-only'], cwd=ROOT, timeout=20).decode().splitlines()
        added = subprocess.check_output(['/usr/bin/git', 'ls-files', '--others', '--exclude-standard'], cwd=ROOT, timeout=20).decode().splitlines()
        for name in sorted(set(changed + added)):
            target = cls.source / name
            if (ROOT / name).is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / name, target)
            elif target.exists():
                target.unlink()
        source_git('add', '--all')
        source_git('commit', '--allow-empty', '-qm', 'Controlled reviewed Core source snapshot')
        canonical = cls.base / 'canonical-source.git'
        subprocess.run(['/usr/bin/git', 'init', '-q', '--bare', str(canonical)], check=True, env=cls.environment, timeout=20)
        source_git('remote', 'set-url', 'origin', str(canonical))
        source_git('push', '-q', 'origin', 'HEAD:main')
        cls.revision = source_git('rev-parse', 'HEAD').stdout.strip()
        home = cls.base / 'bootstrap-build-home'
        home.mkdir()
        result = subprocess.run([sys.executable, '-B', str(cls.source / 'bin/core-authoring-profile.py'), 'install',
                                 '--repo', str(cls.source), '--package', str(cls.package), '--home', str(home)],
                                env=cls.environment, capture_output=True, text=True, timeout=240)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)

    def setUp(self):
        self.repo = self.base / self._testMethodName
        self.remote = self.base / (self._testMethodName + '.git')
        subprocess.run(['/usr/bin/git', 'clone', '--quiet', '--shared', str(self.source), str(self.repo)], check=True, env=self.environment, timeout=40)
        subprocess.run(['/usr/bin/git', 'init', '-q', '--bare', str(self.remote)], check=True, env=self.environment, timeout=20)
        self.home = self.base / (self._testMethodName + '-home')
        self.home.mkdir()
        (self.home / '.claude').mkdir()
        self.global_settings = self.home / '.claude/settings.json'
        self.global_settings.write_text('{"operator":"preserve","hooks":{}}')
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(('CRAFT_', 'CLAUDE_', 'CCP_', 'GIT_'))}
        self.env.update(HOME=str(self.home), PYTHONDONTWRITEBYTECODE='1')
        self.git(self.repo, 'config', 'user.name', 'Controlled Core fixture')
        self.git(self.repo, 'config', 'user.email', 'fixture@example.invalid')
        self.git(self.repo, 'checkout', '-q', '-B', 'feature')
        self.git(self.repo, 'remote', 'set-url', 'origin', str(self.remote))
        self.settings = self.repo / '.claude/settings.json'
        value = json.loads((ROOT / '.claude/settings.authoring.json').read_text())
        value['model'] = 'operator-choice'
        value['hooks']['PreToolUse'].append({'matcher': 'Read', 'hooks': [{'type': 'command', 'command': '/bin/sh -c "exit 2"'}]})
        self.settings.write_text(json.dumps(value))
        self.session = self.home / 'native-sessions/native-one'
        self.session.mkdir(parents=True)
        self.env.update(CLAUDE_SESSION_DIR=str(self.session), CLAUDE_SESSION_ID='native-one')
        self.git(self.repo, 'add', '.claude/settings.json')
        self.git(self.repo, 'commit', '-qm', 'historical fixture baseline')

    def git(self, repo, *args, ok=True):
        result = subprocess.run(['/usr/bin/git', '-C', str(repo), *args], capture_output=True, text=True,
                                env=self.env, timeout=40)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def arguments(self, repo):
        return ['--repo', str(repo), '--package', str(self.package), '--home', str(self.home)]

    def install(self, repo=None, ok=True):
        result = subprocess.run([sys.executable, '-B', str(self.source / 'bin/core-authoring-profile.py'), 'install',
                                 *self.arguments(repo or self.repo)], capture_output=True, text=True, env=self.env, timeout=240)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_actual_core_adoption_and_all_canonical_event_vectors(self):
        prepared = self.settings.read_bytes()
        legacy = json.loads((ROOT / '.claude/settings.json').read_text())
        legacy['model'] = 'operator-choice'
        self.settings.write_text(json.dumps(legacy))
        before = self.settings.read_bytes()
        installed = self.install()
        status = json.loads(installed.stdout)
        self.assertTrue(status['enrollment_ready'])
        self.assertEqual(status['sdk_profile_active'], 'unobserved')
        self.assertEqual(status['project_profile_files'][str(self.repo)]['project'], 'legacy-or-custom-file')
        self.assertEqual(self.settings.read_bytes(), before)
        self.settings.write_bytes(prepared)
        checked = subprocess.run([sys.executable, '-B', str(self.source / 'bin/core-authoring-profile.py'), 'verify',
                                  *self.arguments(self.repo)], capture_output=True, text=True, env=self.env, timeout=240)
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        status = json.loads(checked.stdout)
        self.assertEqual(status['project_profile_files'][str(self.repo)]['project'], 'prepared-file')
        self.assertEqual(status['sdk_profile_active'], 'unobserved')
        anchor = json.loads(b.anchor_path(self.home, b.common_directory(self.repo)).read_text())
        self.assertEqual(anchor['binding']['identity'], 'github.com/siege-analytics/claude-configs-public')
        policy = json.loads((self.package / 'core-authoring-policy.json').read_text())
        self.assertEqual(policy['resolved']['project'], 'claude-configs-public')
        self.assertEqual(policy['resolved']['organization_profile'], 'strict-release')
        canonical = json.loads((self.package / 'compatibility/hooks/settings-snippet.json').read_text())
        canonical.pop('_comment_', None)
        for groups in canonical['hooks'].values():
            for group in groups:
                for hook in group['hooks']:
                    hook['command'] = hook['command'].replace('/path/to/claude-configs-public/', '${package}/compatibility/')
        self.assertEqual(json.loads((self.package / 'hooks/settings-snippet.json').read_text()), canonical)
        self.assertEqual(set(canonical['hooks']), set(b.EVENTS))
        self.assertFalse((self.package / 'selected-registration.json').exists())
        # Enrollment has no project-controlled identity/profile/command selector.
        refused = subprocess.run([sys.executable, '-B', str(self.source / 'bin/core-authoring-profile.py'), 'install',
                                  *self.arguments(self.repo), '--identity', 'foreign/repository'],
                                 capture_output=True, text=True, env=self.env, timeout=20)
        self.assertEqual(refused.returncode, 2)

    def test_fetched_core_objects_and_subtree_history_do_not_adopt_core_identity(self):
        foreign = self.base / 'foreign-object-and-subtree-consumer'
        foreign.mkdir()
        self.git(foreign, 'init', '--template=', '-q', '-b', 'feature')
        self.git(foreign, 'config', 'user.name', 'Foreign fixture')
        self.git(foreign, 'config', 'user.email', 'fixture@example.invalid')
        (foreign / 'README.md').write_text('Independent client repository.\n')
        self.git(foreign, 'add', 'README.md')
        self.git(foreign, 'commit', '-qm', 'Independent history')
        self.git(foreign, 'fetch', '-q', str(self.source), self.revision)
        self.git(foreign, 'cat-file', '-e', self.revision + '^{commit}')
        refused = self.install(foreign, ok=False)
        self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
        self.assertIn('no shared Core history', refused.stderr)
        # A real second-parent subtree import shares history but not root identity.
        for name in ('bin/build.py', 'hooks/settings-snippet.json', 'catalog/effective-policy.json',
                     'bundles/siege/policy-inputs.json'):
            destination = foreign / 'vendor/siege' / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.source / name, destination)
        self.git(foreign, 'add', 'vendor')
        tree = self.git(foreign, 'write-tree').stdout.strip()
        parent = self.git(foreign, 'rev-parse', 'HEAD').stdout.strip()
        imported = self.git(foreign, 'commit-tree', tree, '-p', parent, '-p', self.revision,
                            '-m', 'Import Core below vendor prefix').stdout.strip()
        self.git(foreign, 'update-ref', 'refs/heads/feature', imported)
        self.git(foreign, 'merge-base', '--is-ancestor', self.revision, 'HEAD')
        refused = self.install(foreign, ok=False)
        self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
        self.assertIn('not a Core repository root', refused.stderr)
        self.assertFalse((self.home / b.RELATIVE).exists())
        self.assertFalse(b.anchor_path(self.home, b.common_directory(foreign)).exists())

    def test_existing_generation_health_survives_new_main_and_shared_helper(self):
        self.install()
        anchor = b.anchor_path(self.home, b.common_directory(self.repo))
        anchor_a = anchor.read_bytes()
        helper_source = self.source / 'bin/project-settings-bootstrap.py'
        original = helper_source.read_bytes()
        workspace = self.base / 'new-main-independent-workspace'
        workspace.mkdir()
        package_b = self.base / 'new-main-independent-package'
        def verify():
            return subprocess.run([sys.executable, '-B', str(self.source / 'bin/core-authoring-profile.py'), 'verify',
                                   *self.arguments(self.repo)], capture_output=True, text=True, env=self.env, timeout=60)
        def unchanged_files():
            paths = [self.settings, self.global_settings, self.repo / '.git/config', anchor,
                     self.home / b.RELATIVE, self.home / b.RECEIPT, self.home / b.PUBLISH_LOCK]
            return {str(path): (path.read_bytes(), path.stat().st_mtime_ns) for path in paths}
        try:
            helper_source.write_bytes(original + b'\n# Compatible shared bootstrap generation.\n')
            self.git(self.source, 'add', 'bin/project-settings-bootstrap.py')
            self.git(self.source, 'commit', '-qm', 'Private Main advances with compatible helper')
            revision_b = self.git(self.source, 'rev-parse', 'HEAD').stdout.strip()
            self.git(self.source, 'push', '-q', 'origin', 'HEAD:main')
            before = unchanged_files()
            checked = verify()
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertEqual(json.loads(checked.stdout)['revision'], self.revision)
            self.assertEqual(unchanged_files(), before, 'health verification must not republish or upgrade')
            args = self.arguments(self.repo)
            args[args.index('--package') + 1] = str(package_b)
            installed = subprocess.run([sys.executable, '-B', str(self.source / 'bin/core-authoring-profile.py'), 'install',
                                       *args, '--workspace', str(workspace)], capture_output=True, text=True,
                                      env=self.env, timeout=240)
            self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)
            self.assertEqual(json.loads(installed.stdout)['revision'], revision_b)
            self.assertEqual(anchor.read_bytes(), anchor_a)
            before = unchanged_files()
            checked = verify()
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            status = json.loads(checked.stdout)
            self.assertEqual(status['revision'], self.revision)
            self.assertEqual(status['sdk_profile_active'], 'unobserved')
            self.assertEqual(unchanged_files(), before)
            helper = self.home / b.RELATIVE
            valid = helper.read_bytes()
            try:
                helper.write_bytes(valid + b'\n# Unregistered tamper.\n')
                before = unchanged_files()
                checked = verify()
                self.assertEqual(checked.returncode, 2)
                self.assertIn('bootstrap bytes changed', checked.stderr)
                self.assertEqual(unchanged_files(), before, 'health must not repair or bless tampered code')
            finally:
                helper.write_bytes(valid)
        finally:
            # This private fixture Main only; production Main is never mutated.
            self.git(self.source, 'reset', '--hard', '-q', self.revision)
            self.git(self.source, 'push', '-q', '--force', 'origin', self.revision + ':main')

    def test_sdk_python_path_cannot_replace_the_enrolled_interpreter(self):
        self.install()
        ticket = 'example/interpreter#1286'
        target, _, _ = self.task(self.repo, ticket)
        raw = json.dumps({'hook_event_name': 'PreToolUse', 'session_id': 'native-one', 'cwd': str(self.repo),
                          'tool_name': 'Edit', 'tool_input': {'file_path': str(target)}})
        env = dict(self.env, CCP_TASK_ID=ticket, PATH='/usr/bin:/bin')
        owned = subprocess.run(b.command_for('PreToolUse'), shell=True, input=raw, capture_output=True,
                               text=True, cwd=self.repo, env=env, timeout=90)
        self.assertEqual(owned.returncode, 0, owned.stdout + owned.stderr)
        anchor = b.anchor_path(self.home, b.common_directory(self.repo))
        original = anchor.read_bytes()
        value = json.loads(original)
        value['binding']['interpreter'] = str(self.home / 'missing-installed-python')
        try:
            anchor.write_text(json.dumps(value))
            refused = subprocess.run(b.command_for('PreToolUse'), shell=True, input=raw, capture_output=True,
                                     text=True, cwd=self.repo, env=env, timeout=90)
            self.assertEqual(refused.returncode, 2)
            self.assertIn('interpreter is unavailable', refused.stderr)
        finally:
            anchor.write_bytes(original)

    def test_all_four_events_match_direct_canonical_guard_results(self):
        self.install()
        ticket = 'example/event-parity#1286'
        target, _, _ = self.task(self.repo, ticket)
        template = json.loads((self.package / 'hooks/settings-snippet.json').read_text())
        combiner = b.load(self.package / 'compatibility/hooks/lib/craft-settings-router.py', 'canonical_event_parity')
        for event in b.EVENTS:
            tool = 'Edit' if event == 'PreToolUse' else 'mcp__session__spawn_session'
            payload = {'hook_event_name': event, 'session_id': 'native-one', 'cwd': str(self.repo),
                       'prompt': 'inspect owned work', 'tool_name': tool,
                       'tool_input': {'file_path': str(target)}, 'tool_response': {'error': 'controlled failure'}}
            raw = json.dumps(payload)
            env = dict(self.env, CCP_TASK_ID=ticket,
                       CCP_HOOK_STATE_DIR=str(b.state_path(self.home, b.common_directory(self.repo))))
            outputs = []
            for hook in b.matching(template, event, payload):
                script = hook['command'].replace('${package}', str(self.package))
                result = subprocess.run([script], input=raw, capture_output=True, text=True,
                                        cwd=self.repo, env=env, timeout=40)
                outputs.append((result.returncode, result.stdout, result.stderr))
            self.assertTrue(outputs, 'each canonical event must execute its actual guard')
            expected_code, expected, _ = combiner.aggregate(event, outputs)
            actual = subprocess.run(b.command_for(event), shell=True, input=raw, capture_output=True, text=True,
                                    cwd=self.repo, env=env, timeout=90)
            self.assertEqual(actual.returncode, 0 if expected_code == 0 else 2, actual.stdout + actual.stderr)
            self.assertEqual(json.loads(actual.stdout) if actual.stdout.strip() else None, expected or None)

    def task(self, repo, ticket):
        target = repo / 'hooks/lib/task_actions.py'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('else:\nelse:\n')
        resolver = target.parent / 'resolve-think-gate.py'
        resolver.write_text('else:\nelse:\n')
        directory = self.session / 'tasks' / gates.r.task_slug(ticket)
        directory.mkdir(parents=True)
        data = {'ticket': ticket, 'sessionId': 'native-one', 'repo_root': str(repo), 'scope_paths': [str(target)], 'status': 'implementing'}
        (directory / 'think-gate.json').write_text(json.dumps(data))
        return target, directory, data

    def callback(self, repo, target, ticket, tool='Edit'):
        raw = json.dumps({'hook_event_name': 'PreToolUse', 'session_id': 'native-one', 'cwd': str(repo),
                          'tool_name': tool, 'tool_input': {'file_path': str(target), 'old_string': 'else:', 'new_string': ''}})
        return subprocess.run(b.command_for('PreToolUse'), shell=True, input=raw, capture_output=True, text=True,
                              cwd=repo, env=dict(self.env, CCP_TASK_ID=ticket), timeout=40)

    def test_linked_worktree_repair_and_existing_native_publication_survive_enrollment(self):
        # Existing canonical legacy native hooks already work across worktrees.
        self.git(self.repo, 'push', '-q', 'origin', 'HEAD:feature')
        self.git(self.repo, 'config', '--local', 'core.hooksPath', str(self.package / 'compatibility/.githooks'))
        message = 'docs: fixture #1286\n\nReview-Tier: A\nSelf-Review: inspected controlled fixture'
        self.git(self.repo, 'commit', '--allow-empty', '-qm', message)
        self.git(self.repo, 'push', '-q', 'origin', 'HEAD:feature')
        worktree = self.base / 'linked-worktree'
        self.git(self.repo, 'worktree', 'add', '-q', '-b', 'linked-feature', str(worktree))
        nested = self.arguments(self.repo)
        nested[nested.index('--package') + 1] = str(worktree / 'mutable-policy-package')
        refused = subprocess.run([sys.executable, '-B', str(self.source / 'bin/core-authoring-profile.py'), 'install', *nested],
                                 capture_output=True, text=True, env=self.env, timeout=240)
        self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
        self.assertIn('outside authoring worktrees', refused.stderr)
        self.assertFalse((worktree / 'mutable-policy-package').exists())
        self.assertFalse((self.home / b.RELATIVE).exists())
        before_config = (self.repo / '.git/config').read_bytes()
        before_settings, before_global = self.settings.read_bytes(), self.global_settings.read_bytes()
        self.install()
        self.assertEqual((self.repo / '.git/config').read_bytes(), before_config)
        self.assertEqual(self.settings.read_bytes(), before_settings)
        self.assertEqual(self.global_settings.read_bytes(), before_global)
        for repo, ticket in ((self.repo, 'example/main#1286'), (worktree, 'example/worktree#1286')):
            target, directory, data = self.task(repo, ticket)
            owned = self.callback(repo, target, ticket)
            self.assertEqual(owned.returncode, 0, owned.stdout + owned.stderr)
            foreign = self.callback(repo, self.base / 'foreign.py', ticket)
            self.assertEqual(foreign.returncode, 2, foreign.stdout + foreign.stderr)
            for field, value in (('sessionId', 'foreign-owner'), ('status', 'designing')):
                (directory / 'think-gate.json').write_text(json.dumps(dict(data, **{field: value})))
                denied = self.callback(repo, target, ticket)
                self.assertEqual(denied.returncode, 2, denied.stdout + denied.stderr)
            (directory / 'think-gate.json').write_text(json.dumps(data))
            self.assertEqual(target.read_text(), 'else:\nelse:\n')
        anchor = b.anchor_path(self.home, b.common_directory(self.repo))
        original_anchor = anchor.read_bytes()
        log = b.state_path(self.home, b.common_directory(self.repo)) / 'enforcement-blocks.jsonl'
        self.assertTrue(log.is_file(), 'real refusals must retain audit evidence outside immutable code')
        self.assertFalse((self.package / 'compatibility/enforcement-blocks.jsonl').exists())
        refused = self.install(worktree, ok=False)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn('primary repository', refused.stderr)
        self.assertEqual(anchor.read_bytes(), original_anchor)
        self.assertEqual((self.repo / '.git/config').read_bytes(), before_config)
        # Audit availability is not permission; a missing state directory must
        # neither mutate pinned code nor block independent authorized work.
        shutil.rmtree(b.state_path(self.home, b.common_directory(self.repo)))
        for repo, ticket in ((self.repo, 'example/main#1286'), (worktree, 'example/worktree#1286')):
            self.assertEqual(self.callback(repo, repo / 'hooks/lib/task_actions.py', ticket).returncode, 0)
            self.git(repo, 'commit', '--allow-empty', '-qm', message)
            self.git(repo, 'push', '-q', 'origin', 'HEAD:' + ('feature' if repo == self.repo else 'linked-feature'))
        operator = json.loads(self.settings.read_text())['hooks']['PreToolUse'][-1]['hooks'][0]['command']
        self.assertEqual(subprocess.run(operator, shell=True, env=self.env, timeout=10).returncode, 2)

    def test_dirty_trusted_installer_cannot_publish_home_policy(self):
        helper = self.source / 'README.md'
        original = helper.read_bytes()
        try:
            helper.write_bytes(original + b'\n# unreviewed fixture edit\n')
            refused = self.install(ok=False)
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn('tracked deployment inputs differ', refused.stderr)
            self.assertFalse((self.home / b.RELATIVE).exists())
        finally:
            helper.write_bytes(original)

    def test_main_advance_during_export_cannot_publish_enrollment(self):
        profile = b.load(self.source / 'bin/core-authoring-profile.py', 'main_advance_profile')
        prepare = profile.prepared_package
        tree = self.git(self.source, 'rev-parse', 'HEAD^{tree}').stdout.strip()
        advanced = self.git(self.source, 'commit-tree', tree, '-p', self.revision,
                            '-m', 'Advance private fixture Main').stdout.strip()
        def advance(destination):
            result = prepare(destination)
            self.git(self.source, 'push', '-q', 'origin', advanced + ':main')
            return result
        try:
            with patch.object(profile, 'prepared_package', side_effect=advance), \
                 patch.object(sys, 'argv', ['core-authoring-profile.py', 'install', *self.arguments(self.repo)]), \
                 patch.dict(os.environ, self.env, clear=True), contextlib.redirect_stderr(io.StringIO()) as diagnostic:
                self.assertEqual(profile.main(), 2)
            self.assertIn('origin/main', diagnostic.getvalue())
            self.assertFalse((self.home / b.RELATIVE).exists())
            self.assertFalse(b.anchor_path(self.home, b.common_directory(self.repo)).exists())
        finally:
            # Only this test's private bare Main; no public/protected ref effects.
            self.git(self.source, 'push', '-q', '--force', 'origin', self.revision + ':main')

    def test_headless_enrollment_seals_real_session_policy_without_candidate_imports(self):
        self.install()
        cli_anchor = b.anchor_path(self.home, b.common_directory(self.repo))
        cli_anchor_bytes = cli_anchor.read_bytes()
        cli_ticket = 'example/native-coexist#1286'
        cli_target, _, _ = self.task(self.repo, cli_ticket)
        self.assertEqual(self.callback(self.repo, cli_target, cli_ticket).returncode, 0)
        workspace = self.base / 'headless-workspace'
        session = workspace / 'sessions/one'
        session.mkdir(parents=True)
        sdk = 'aaa0010a-0000-4000-8000-000000000000'
        header = session / 'session.jsonl'
        header.write_text(json.dumps({'id': 'one', 'sdkSessionId': sdk}) + '\n')
        args = self.arguments(self.repo)
        args += ['--workspace', str(workspace)]
        enrolled = subprocess.run([sys.executable, '-B', str(self.source / 'bin/core-authoring-profile.py'), 'install', *args],
                                 capture_output=True, text=True, env=self.env, timeout=90)
        self.assertEqual(enrolled.returncode, 0, enrolled.stdout + enrolled.stderr)
        self.assertEqual(cli_anchor.read_bytes(), cli_anchor_bytes)
        native = self.callback(self.repo, cli_target, cli_ticket)
        self.assertEqual(native.returncode, 0, native.stdout + native.stderr)
        self.session = session
        ticket = 'example/headless#1286'
        target, directory, data = self.task(self.repo, ticket)
        data['sessionId'] = 'one'
        (directory / 'think-gate.json').write_text(json.dumps(data))
        launcher = ('import importlib.util,sys; '
                    's=importlib.util.spec_from_file_location("stable",sys.argv[1]); '
                    'b=importlib.util.module_from_spec(s); s.loader.exec_module(b); '
                    'b.craft_process=lambda:False; b.headless_process=lambda:True; '
                    'sys.argv=sys.argv[1:]; sys.exit(b.main())')
        def callback(path=target, identity=sdk, **updates):
            raw = json.dumps({'hook_event_name': 'PreToolUse', 'session_id': identity, 'cwd': str(self.repo),
                              'tool_name': 'Edit', 'tool_input': {'file_path': str(path)}})
            env = dict(self.env, CRAFT_WORKSPACE_PATH=str(workspace), CRAFT_SESSION_DIR=str(session), CCP_TASK_ID=ticket)
            env.update(updates)
            return subprocess.run([sys.executable, '-I', '-B', '-c', launcher,
                                   str(self.home / b.RELATIVE), '--event', 'PreToolUse'],
                                  cwd=self.repo, input=raw, capture_output=True, text=True, env=env, timeout=40)
        own = callback()
        self.assertEqual(own.returncode, 0, own.stdout + own.stderr)
        for result in (callback(self.base / 'foreign.py'), callback(identity='invalid'),
                       callback(CRAFT_WORKSPACE_PATH=str(self.repo))):
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        for field, value in (('sessionId', 'foreign-owner'), ('status', 'designing')):
            (directory / 'think-gate.json').write_text(json.dumps(dict(data, **{field: value})))
            result = callback()
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        (directory / 'think-gate.json').write_text(json.dumps(data))
        header.write_text(json.dumps({'id': 'other', 'sdkSessionId': sdk}) + '\n')
        result = callback()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        header.write_text(json.dumps({'id': 'one', 'sdkSessionId': sdk}) + '\n')
        result = callback()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        duplicate = workspace / 'sessions/two'
        duplicate.mkdir()
        (duplicate / 'session.jsonl').write_text(json.dumps({'id': 'two', 'sdkSessionId': sdk}) + '\n')
        result = callback()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        shutil.rmtree(duplicate)
        external = self.base / 'external-headless-header'
        external.write_bytes(header.read_bytes())
        header.unlink()
        header.symlink_to(external)
        result = callback()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        header.unlink()
        header.write_bytes(external.read_bytes())
        linked = self.base / 'headless-linked-worktree'
        self.git(self.repo, 'worktree', 'add', '-q', '-b', 'headless-linked', str(linked))
        previous_repo = self.repo
        self.repo = linked
        try:
            linked_target, linked_directory, linked_data = self.task(linked, 'example/headless-linked#1286')
            # Same session's Task can cover the linked worktree.
            linked_data['sessionId'] = 'one'
            (linked_directory / 'think-gate.json').write_text(json.dumps(linked_data))
            prior_ticket = ticket
            ticket = 'example/headless-linked#1286'
            result = callback(path=linked_target)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            ticket = prior_ticket
        finally:
            self.repo = previous_repo
        self.assertEqual(target.read_text(), 'else:\nelse:\n')

    def test_package_code_is_hashed_before_any_verifier_import(self):
        self.install()
        target, _, _ = self.task(self.repo, 'example/main#1286')
        module = self.package / 'bin/core-authoring-profile.py'
        original = module.read_bytes()
        marker = self.base / 'modified-verifier-executed'
        try:
            module.write_bytes(original + ('\nfrom pathlib import Path\nPath(' + repr(str(marker)) + ').write_text("executed")\n').encode())
            denied = self.callback(self.repo, target, 'example/main#1286')
            self.assertEqual(denied.returncode, 2, denied.stdout + denied.stderr)
            self.assertFalse(marker.exists())
        finally:
            module.write_bytes(original)
        owned = self.callback(self.repo, target, 'example/main#1286')
        self.assertEqual(owned.returncode, 0, owned.stdout + owned.stderr)




if __name__ == '__main__':
    unittest.main()
