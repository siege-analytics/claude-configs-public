#!/usr/bin/env python3
"""Controlled SDK callbacks retain installed policy while candidate code is broken."""
import contextlib
import importlib.util
import io
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
            (process / 'cmdline').write_bytes(b'/app/vendor/bun/bun\0run\0other.ts\0')
            self.assertFalse(b.headless_process(proc, 42))
            (process / 'exe').unlink()
            (process / 'exe').symlink_to('/usr/bin/bun')
            (process / 'cmdline').write_bytes(('\0'.join(argv) + '\0').encode())
            self.assertFalse(b.headless_process(proc, 42))

    def test_managed_profile_preserves_operator_policy_and_rejects_duplicates(self):
        settings = b.profile()
        settings['model'] = 'operator-choice'
        settings['hooks']['PreToolUse'].append({'matcher': 'Read', 'hooks': [
            {'type': 'command', 'command': '/bin/sh -c "exit 2"'}]})
        self.assertEqual(b.profile_problems(settings), [])
        settings['hooks']['PreToolUse'].append(b.profile()['hooks']['PreToolUse'][0])
        self.assertTrue(b.profile_problems(settings))

    def test_source_profile_never_executes_candidate_guards(self):
        settings = json.loads((ROOT / '.claude/settings.json').read_text())
        self.assertEqual(settings, b.profile())

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
        self.assertEqual(actual['hooks']['PreToolUse'][-1], b.profile()['hooks']['PreToolUse'][0])
        actual['hooks']['PostToolUse'].append(actual['hooks']['PreToolUse'][-1])
        destination.write_text(json.dumps(actual))
        bad = destination.read_bytes()
        refused = subprocess.run(['bash', str(ROOT / 'bin/install-hooks.sh'), '--relative', '--target-file', str(destination)], capture_output=True, text=True, timeout=20)
        self.assertEqual(refused.returncode, 1, refused.stdout + refused.stderr)
        self.assertEqual(destination.read_bytes(), bad)
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
        (sibling / 'bin/selected_registration.py').write_text(
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


class CLI(unittest.TestCase):
    def test_independent_profile_remains_valid_but_cannot_replace_core_guards(self):
        import selected_registration_test as selected_fixture
        case = selected_fixture.SelectedRegistrationTest(methodName='runTest')
        with patch.object(tempfile, 'tempdir', str(Path(tempfile.gettempdir()).resolve())):
            case.setUp()
        self.addCleanup(case.doCleanups)
        case.prepare()
        case.entry('install')
        home = case.output.parent / 'native-home'
        home.mkdir()
        prior = (case.consumer / '.git/config').read_bytes()
        refused = case.entry('install', ok=False, extra=['--bootstrap-home', str(home)])
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn('Siege-compatibility', refused.stderr)
        self.assertEqual((case.consumer / '.git/config').read_bytes(), prior)
        # Simulate an old external enrollment of a real prompt-only profile.
        # Its provenance is valid; it still does not supply Core mutation guards.
        bound = json.loads(case.run_cmd(['git', 'config', '--get', 'scaffold.registration'], cwd=case.consumer).stdout)
        b.publish(home, (ROOT / 'bin/project-settings-bootstrap.py').read_bytes())
        b.publish_anchor(home, bound)
        env = {k: v for k, v in os.environ.items() if not k.startswith(('CRAFT_', 'CLAUDE_', 'CCP_', 'GIT_'))}
        env['HOME'] = str(home)
        raw = json.dumps({'hook_event_name': 'PreToolUse', 'tool_name': 'Edit', 'cwd': str(case.consumer),
                          'tool_input': {'file_path': str(case.consumer / 'source.py')}})
        result = subprocess.run(b.command_for('PreToolUse'), shell=True, input=raw, text=True, capture_output=True,
                                cwd=case.consumer, env=env, timeout=40)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('enforcement profile', result.stderr)
        independent = next(hook['command'] for group in json.loads(case.settings.read_text())['hooks']['UserPromptSubmit'] for hook in group['hooks'] if 'native_git.py' in hook['command'])
        result = subprocess.run(independent, shell=True, input='{"prompt":"inspect changes"}', text=True,
                                capture_output=True, cwd=case.consumer, env=env, timeout=40)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)




class CompatibleCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='core1286-cli-', dir=str(Path(tempfile.gettempdir()).resolve()))
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.base = Path(cls.temporary.name)
        cls.output = cls.base / 'selected'
        spec = importlib.util.spec_from_file_location('bootstrap_selected_build', ROOT / 'examples/selected-build/run.py')
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        spec = importlib.util.spec_from_file_location('bootstrap_registration_example', ROOT / 'examples/selected-registration/run.py')
        cls.example = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.example)
        original = build.selected.module
        def module(name, root, filename):
            return cls.example if name == 'registration_example' else original(name, root, filename)
        def capture(output, selection, policy_source, policy_pin, registration_source, registration_pin, case):
            cls.selection, cls.policy_source, cls.policy_pin = selection, policy_source, policy_pin
            cls.registration_source, cls.registration_pin = registration_source, registration_pin
            return {'fixture': 'build-only; normal installer is exercised by this suite'}
        original_commit = build.commit
        def current_runtime(source):
            for name in ('hooks/lib/log-block.sh', 'hooks/resolver/block-classifier-guard.sh'):
                shutil.copy2(ROOT / name, source / name)
            return original_commit(source)
        with patch.object(build.selected, 'module', side_effect=module), patch.object(cls.example, 'exercise', side_effect=capture), \
             patch.object(build, 'commit', side_effect=current_runtime):
            build.run('siege', cls.output, register=True)
        cls.source, cls.package = cls.output / 'source', cls.output / 'package/flat'
        def source_git(*args):
            return subprocess.run(['/usr/bin/git', '-C', str(cls.source), *args], check=True,
                                  capture_output=True, text=True, timeout=40)
        source_git('add', 'selected-registration-inputs.json')
        source_git('commit', '-qm', 'Synthetic reviewed main source for installer authority')
        canonical = cls.base / 'canonical-source.git'
        subprocess.run(['/usr/bin/git', 'init', '-q', '--bare', str(canonical)], check=True, timeout=20)
        source_git('remote', 'set-url', 'origin', str(canonical))
        source_git('checkout', '-q', '-B', 'main')
        source_git('push', '-q', 'origin', 'HEAD:main')


    def setUp(self):
        self.repo, self.remote = self.example.make_consumer(self.output, self._testMethodName)
        self.home = self.base / (self._testMethodName + '-home')
        self.home.mkdir()
        (self.home / '.claude').mkdir()
        self.global_settings = self.home / '.claude/settings.json'
        self.global_settings.write_text('{"operator":"preserve","hooks":{}}')
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(('CRAFT_', 'CLAUDE_', 'CCP_', 'GIT_'))}
        self.env.update(HOME=str(self.home), PYTHONDONTWRITEBYTECODE='1')
        self.settings = self.repo / '.claude/settings.json'
        value = b.profile()
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
        return ['--selected', '--source', str(self.source), '--selection', str(self.output / 'selection.json'),
                '--policy-root', str(self.source), '--policy-inputs', str(self.policy_source),
                '--policy-inputs-sha256', self.policy_pin, '--registration-inputs', str(self.registration_source),
                '--registration-inputs-sha256', self.registration_pin, '--identity', self.selection['identity'],
                '--backend', 'claude-code-local', '--hooks-root', str(self.package), '--workspace', str(repo),
                '--git-repo', str(repo), '--bootstrap-home', str(self.home)]

    def install(self, repo=None, ok=True):
        result = subprocess.run(['bash', str(self.source / 'bin/install-hooks.sh'), *self.arguments(repo or self.repo)],
                                capture_output=True, text=True, env=self.env, timeout=90)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

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
        args[args.index('--workspace') + 1] = str(workspace)
        enrolled = subprocess.run(['bash', str(self.source / 'bin/install-hooks.sh'), *args],
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
        module = self.package / 'bin/selected_registration.py'
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
