#!/usr/bin/env python3
"""Real repositories exercise source provenance and safe bootstrap boundaries."""
import importlib.util
import os
import json
import re
import shlex
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'hooks/lib'))
from branch_source import check
from git_command import inspect_git
from task_actions import UnknownShape
spec = importlib.util.spec_from_file_location('prepare_task', ROOT / 'bin/prepare-task-branch.py')
prepare_task = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare_task)


class BranchSources(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.remote, self.repo = self.base / 'origin.git', self.base / 'repo'
        self.run_git(self.base, 'init', '--bare', str(self.remote))
        self.run_git(self.base, 'clone', str(self.remote), str(self.repo))
        self.run_git(self.repo, 'config', 'user.email', 'test@example.invalid')
        self.run_git(self.repo, 'config', 'user.name', 'Fixture')
        self.run_git(self.repo, 'checkout', '-b', 'main')
        (self.repo / 'tracked').write_text('base\n')
        self.run_git(self.repo, 'add', 'tracked')
        self.run_git(self.repo, 'commit', '-m', 'initial')
        self.run_git(self.repo, 'push', 'origin', 'main')
        self.main = self.run_git(self.repo, 'rev-parse', 'HEAD')

    def run_git(self, repo, *args):
        p = subprocess.run(['git', '-C', str(repo), *args], text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout.strip()

    def develop(self):
        self.run_git(self.repo, 'branch', 'develop')
        self.run_git(self.repo, 'push', 'origin', 'develop')
        self.run_git(self.repo, 'fetch', 'origin')

    def inspect(self, *args):
        return self.run_git(self.repo, *args)

    def test_existing_develop_preserves_active_work(self):
        self.develop()
        (self.repo / 'tracked').write_text('uncommitted\n')
        (self.repo / 'untracked').write_text('keep\n')
        before = self.inspect('status', '--porcelain')
        tip = prepare_task.prepare(self.repo, 'feature/proper', self.base / 'task')
        self.assertEqual(tip, self.main)
        self.assertEqual(self.inspect('status', '--porcelain'), before)
        self.assertEqual(self.inspect('branch', '--show-current'), 'main')
        self.assertEqual(self.run_git(self.base / 'task', 'rev-parse', 'HEAD'), tip)
        self.assertEqual(self.run_git(self.remote, 'rev-parse', 'refs/heads/main'), self.main)

    def test_missing_develop_bootstraps_then_branches(self):
        tip = prepare_task.prepare(self.repo, 'feature/bootstrap', self.base / 'task')
        self.assertEqual(self.run_git(self.remote, 'rev-parse', 'refs/heads/develop'), self.main)
        self.assertEqual(tip, self.main)
        self.assertEqual(self.inspect('branch', '--show-current'), 'main')

    def test_network_failure_is_not_absence(self):
        self.run_git(self.repo, 'remote', 'set-url', 'origin', str(self.base / 'unavailable.git'))
        with self.assertRaises(prepare_task.PreparationError):
            prepare_task.prepare(self.repo, 'feature/network', self.base / 'task')
        self.assertFalse((self.base / 'task').exists())
        self.assertEqual(self.run_git(self.remote, 'for-each-ref', '--format=%(refname)'), 'refs/heads/main')

    def test_helper_uses_known_cached_develop_offline_without_bootstrap(self):
        self.develop()
        self.run_git(self.repo, 'remote', 'set-url', 'origin', str(self.base / 'unavailable.git'))
        tip = prepare_task.prepare(self.repo, 'feature/offline', self.base / 'task')
        self.assertEqual(tip, self.main)
        self.assertEqual(self.run_git(self.base / 'task', 'rev-parse', 'HEAD'), self.main)
        self.assertEqual(self.run_git(self.remote, 'rev-parse', 'refs/heads/develop'), self.main)
        # The same structural rule accepts a local-only develop if tracking refs
        # are absent; it still never substitutes local main.
        self.run_git(self.repo, 'update-ref', '-d', 'refs/remotes/origin/develop')
        check({'args': ['switch', '-c', 'feature/local-only', 'develop'], 'cwd': str(self.repo)}, inspect_git)

    def test_successful_fetch_but_failed_remote_query_does_not_bootstrap(self):
        real_run = subprocess.run
        def unavailable(argv, **kwargs):
            if 'ls-remote' in argv:
                return subprocess.CompletedProcess(argv, 128, '', 'remote query unavailable')
            return real_run(argv, **kwargs)
        with patch.object(prepare_task.subprocess, 'run', side_effect=unavailable):
            with self.assertRaises(prepare_task.PreparationError):
                prepare_task.prepare(self.repo, 'feature/no-query', self.base / 'task')
        self.assertEqual(self.run_git(self.remote, 'for-each-ref', '--format=%(refname)'), 'refs/heads/main')

    def test_known_develop_source_works_offline_without_main_fallback(self):
        self.develop()
        self.run_git(self.repo, 'remote', 'set-url', 'origin', str(self.base / 'unavailable.git'))
        check({'args': ['switch', '-c', 'feature/offline', 'origin/develop'], 'cwd': str(self.repo)}, inspect_git)
        with self.assertRaises(UnknownShape):
            check({'args': ['switch', '-c', 'feature/wrong', 'origin/main'], 'cwd': str(self.repo)}, inspect_git)

    def test_default_tip_is_only_used_to_bootstrap_develop(self):
        self.run_git(self.remote, 'update-ref', 'refs/heads/master', self.main)
        self.run_git(self.remote, 'update-ref', '-d', 'refs/heads/main')
        self.run_git(self.remote, 'symbolic-ref', 'HEAD', 'refs/heads/master')
        tip = prepare_task.prepare(self.repo, 'feature/from-bootstrap', self.base / 'task')
        self.assertEqual(tip, self.run_git(self.remote, 'rev-parse', 'refs/heads/develop'))
        self.assertEqual(self.run_git(self.remote, 'symbolic-ref', 'HEAD'), 'refs/heads/master')

    def test_racing_develop_creation_is_not_overwritten(self):
        # Simulate another actor creating a distinct develop after our absence
        # query, immediately before the create-only push.
        self.run_git(self.repo, 'checkout', '-b', 'other')
        (self.repo / 'tracked').write_text('racing develop\n')
        self.run_git(self.repo, 'commit', '-am', 'racer')
        raced = self.inspect('rev-parse', 'HEAD')
        self.run_git(self.repo, 'push', 'origin', 'other')
        real_run = subprocess.run
        def race(argv, **kwargs):
            if 'push' in argv and '--force-with-lease=refs/heads/develop:' in argv:
                self.run_git(self.remote, 'update-ref', 'refs/heads/develop', raced)
            return real_run(argv, **kwargs)
        with patch.object(prepare_task.subprocess, 'run', side_effect=race):
            tip = prepare_task.prepare(self.repo, 'feature/race', self.base / 'task')
        self.assertEqual(tip, raced)
        self.assertEqual(self.run_git(self.remote, 'rev-parse', 'refs/heads/develop'), raced)

    def test_existing_branch_and_path_are_preserved(self):
        self.run_git(self.repo, 'branch', 'feature/existing')
        with self.assertRaises(prepare_task.PreparationError):
            prepare_task.prepare(self.repo, 'feature/existing', self.base / 'task')
        target = self.base / 'existing'
        target.mkdir()
        with self.assertRaises(prepare_task.PreparationError):
            prepare_task.prepare(self.repo, 'feature/new', target)
        self.assertTrue(target.is_dir())

    def test_creation_routes_reject_main_even_when_trees_and_commits_equal(self):
        self.develop()
        routes = [
            ['checkout', '-b', 'feature/x', 'origin/main'],
            ['switch', '-c', 'feature/x', 'origin/main'],
            ['branch', 'feature/x', 'origin/main'],
            ['worktree', 'add', '-b', 'feature/x', '/unused', 'origin/main'],
            ['checkout', '-b', 'feature/x'], ['switch', '-c', 'feature/x'],
            ['branch', 'feature/x'], ['worktree', 'add', '/unused'],
            ['switch', '-c', 'feature/x', 'origin/main^0'],
            ['switch', '-c', 'feature/x', 'main^{commit}'],
            ['switch', '-c', 'feature/x', 'HEAD^0'],
            ['switch', '-c', 'feature/x', '@'],
        ]
        for args in routes:
            with self.subTest(args=args), self.assertRaises(UnknownShape):
                check({'args': args, 'cwd': str(self.repo)}, inspect_git)
        for args in routes[:4]:
            args[-1] = 'origin/develop'
            check({'args': args, 'cwd': str(self.repo)}, inspect_git)

    def test_release_name_does_not_grant_exception_but_trusted_exact_source_can(self):
        self.develop()
        self.run_git(self.repo, 'checkout', 'develop')
        (self.repo / 'tracked').write_text('new develop\n')
        self.run_git(self.repo, 'commit', '-am', 'advance develop')
        self.run_git(self.repo, 'push', 'origin', 'develop')
        item = {'args': ['switch', '-c', 'release/backport', self.main], 'cwd': str(self.repo)}
        with self.assertRaises(UnknownShape):
            check(item, inspect_git)
        check(item, inspect_git, release_source=self.main)
        with self.assertRaises(UnknownShape):
            check(item, inspect_git, release_source='f' * 40)
        check({'args': ['worktree', 'add', '--detach', '/review', self.main], 'cwd': str(self.repo)}, inspect_git)

    def test_short_option_clusters_keep_creation_source_checks(self):
        self.develop()
        env = dict(os.environ, CLAUDE_SCOPED_OWNERS=self.base.name)
        for sub, flags in [('checkout', '-qb'), ('switch', '-qc')]:
            with self.subTest(sub=sub):
                args = [sub, flags, 'feature/cluster-' + sub, 'origin/main']
                command = shlex.join(['git', *args])
                result = subprocess.run([sys.executable, str(ROOT / 'hooks/lib/git_command.py'),
                    '--cwd', str(self.repo), '--policy', 'branch'], input=command,
                    text=True, capture_output=True, env=env)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                # Git really interprets these as creation, including attached names.
                for option in [flags, flags + 'feature/attached-' + sub]:
                    candidate = [sub, option, *([] if option != flags else ['feature/cluster-' + sub]), 'origin/main']
                    with self.assertRaises(UnknownShape):
                        check({'args': candidate, 'cwd': str(self.repo)}, inspect_git)
                    candidate[-1] = 'origin/develop'
                    check({'args': candidate, 'cwd': str(self.repo)}, inspect_git)
                args[-1] = 'origin/develop'
                self.run_git(self.repo, *args)
                self.assertEqual(self.inspect('branch', '--show-current'), 'feature/cluster-' + sub)

    def test_main_ref_aliases_do_not_become_develop_sources_at_equal_commit(self):
        self.develop()
        self.run_git(self.repo, 'symbolic-ref', 'refs/remotes/origin/HEAD', 'refs/remotes/origin/main')
        # All aliases resolve successfully, so rejection cannot rely on SHA inequality.
        sources = ['heads/main', 'remotes/origin/main', 'origin/HEAD', 'refs/remotes/origin/HEAD']
        for source in sources:
            for suffix in ['', '^0']:
                with self.subTest(source=source + suffix):
                    self.assertEqual(self.inspect('rev-parse', '--verify', source + suffix + '^{commit}'), self.main)
                    item = {'args': ['switch', '-c', 'feature/alias', source + suffix], 'cwd': str(self.repo)}
                    with self.assertRaises(UnknownShape):
                        check(item, inspect_git)
                    check(item, inspect_git, release_source=self.main)
        self.run_git(self.repo, 'symbolic-ref', 'refs/remotes/origin/HEAD', 'refs/remotes/origin/develop')
        self.run_git(self.repo, 'tag', 'known@develop', self.main)
        self.run_git(self.repo, 'remote', 'set-url', 'origin', str(self.base / 'offline.git'))
        for source in ['heads/develop', 'remotes/origin/develop', 'origin/HEAD', 'known@develop']:
            check({'args': ['switch', '-c', 'feature/develop', source], 'cwd': str(self.repo)}, inspect_git)

    def test_attached_orphan_option_keeps_existing_orphan_rejection(self):
        self.develop()
        for args in [['checkout', '--orphan=feature/orphan', 'origin/main'],
                     ['switch', '--orphan=feature/orphan'],
                     ['checkout', '--orphan', 'feature/orphan', 'origin/develop']]:
            with self.subTest(args=args), self.assertRaises(UnknownShape):
                check({'args': args, 'cwd': str(self.repo)}, inspect_git)
        # This is real creation syntax, not an unknown option that Git rejects.
        self.run_git(self.repo, 'checkout', '--orphan=feature/orphan', 'origin/main')
        self.assertEqual(self.inspect('symbolic-ref', '--short', 'HEAD'), 'feature/orphan')
        # Explicit path restoration still does not create a branch.
        check({'args': ['checkout', '--', '--orphan=literal-path'], 'cwd': str(self.repo)}, inspect_git)

    def test_cli_guard_enforces_all_creation_routes_and_leaves_switches_alone(self):
        self.develop()
        env = dict(os.environ, CLAUDE_SCOPED_OWNERS=self.base.name)
        commands = [
            'git checkout -b feature/x origin/main',
            'git switch -c feature/x origin/main',
            'git branch feature/x origin/main',
            'git worktree add -b feature/x /unused origin/main',
            'git worktree add /unused',
            'git branch --copy main feature/copied',
            'git checkout --track origin/main',
        ]
        for command in commands:
            with self.subTest(command=command):
                result = subprocess.run([sys.executable, str(ROOT / 'hooks/lib/git_command.py'),
                    '--cwd', str(self.repo), '--policy', 'branch'], input=command,
                    text=True, capture_output=True, env=env)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        for command in ['git switch -c feature/x origin/develop', 'git switch main',
                        'git checkout -- tracked', 'git checkout tracked',
                        'git worktree add --detach /unused origin/main']:
            result = subprocess.run([sys.executable, str(ROOT / 'hooks/lib/git_command.py'),
                '--cwd', str(self.repo), '--policy', 'branch'], input=command,
                text=True, capture_output=True, env=env)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_python_branch_policy_honors_installed_client_scope_overlay(self):
        self.develop()
        self.run_git(self.repo, 'remote', 'set-url', 'origin', 'https://github.com/electinfo/synthetic.git')
        library = self.base / 'consumer-lib'
        shutil.copytree(ROOT / 'hooks/lib', library)
        scope = library / 'scope-check.sh'
        scope.write_text(scope.read_text().replace('CLAUDE_SCOPED_OWNERS:-siege-analytics}',
                                                   'CLAUDE_SCOPED_OWNERS:-siege-analytics:electinfo}'))
        env = dict(os.environ)
        env.pop('CLAUDE_SCOPED_OWNERS', None)
        def run(environment):
            return subprocess.run([sys.executable, str(library / 'git_command.py'), '--cwd', str(self.repo),
                '--policy', 'branch'], input='git switch -c feature/client origin/main',
                text=True, capture_output=True, env=environment)
        self.assertEqual(run(env).returncode, 2)  # Client literal includes electinfo.
        scope.write_text(scope.read_text().replace('siege-analytics:electinfo}', 'siege-analytics}'))
        self.assertEqual(run(env).returncode, 0)  # Core default deliberately scopes elsewhere.
        self.assertEqual(run(dict(env, CLAUDE_SCOPED_OWNERS='siege-analytics:electinfo')).returncode, 2)
        scope.write_text(scope.read_text() + '\nSCOPED_OWNERS="${CLAUDE_SCOPED_OWNERS:-siege-analytics:electinfo}"\n')
        result = run(env)
        self.assertEqual(result.returncode, 2)
        self.assertIn('ambiguous', result.stdout)

    def test_registered_bash_hooks_allow_helper_from_main_with_owning_task(self):
        import task_keyed_gates as fixture
        gates = fixture.Gates(methodName='runTest')
        gates.setUp()
        try:
            gates.repo = self.repo
            gate = gates.task('normal-branch-task', self.repo)
            destination = self.base / 'assigned-worktree'
            data = json.loads((gate / 'think-gate.json').read_text())
            data['scope_paths'].append(str(destination))
            (gate / 'think-gate.json').write_text(json.dumps(data))
            command = shlex.join([sys.executable, str(ROOT / 'bin/prepare-task-branch.py'),
                '--repo', str(self.repo), '--branch', 'feature/registered', '--worktree', str(destination)])
            payload = fixture.craft_payload(tool_name='Bash', cwd=str(self.repo), tool_input={'command': command})
            groups = json.loads((ROOT / 'hooks/settings-snippet.json').read_text())['hooks']['PreToolUse']
            hooks = [hook for group in groups if re.fullmatch(group.get('matcher', '.*'), 'Bash')
                     for hook in group['hooks']]
            self.assertGreaterEqual(len(hooks), 16)
            for hook in hooks:
                script = hook['command'].replace('/path/to/claude-configs-public/', str(ROOT) + '/')
                result = subprocess.run(shlex.split(script), input=json.dumps(payload),
                    text=True, capture_output=True, env=gates.env)
                self.assertEqual(result.returncode, 0, script + result.stdout + result.stderr)
            # Execute only after all configured hooks permit the task action.
            result = subprocess.run(shlex.split(command), text=True, capture_output=True, env=gates.env)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(self.inspect('branch', '--show-current'), 'main')
            self.assertEqual(self.run_git(destination, 'branch', '--show-current'), 'feature/registered')
            # The bounded lane remains mutation-gated; wrong and absent task
            # authority do not acquire an execution exemption.
            data['scope_paths'] = [str(self.repo / 'unrelated')]
            (gate / 'think-gate.json').write_text(json.dumps(data))
            self.assertEqual(gates.hook(command, cwd=self.repo).returncode, 2)
            (gate / 'think-gate.json').unlink()
            self.assertEqual(gates.hook(command, cwd=self.repo).returncode, 2)
        finally:
            gates.tearDown()

    def test_native_registration_covers_both_observed_schemas(self):
        groups = json.loads((ROOT / 'hooks/settings-snippet.json').read_text())['hooks']['PreToolUse']
        for tool in ['mcp__codex_apps__github_create_branch', 'mcp__github-dheeraj__create_branch']:
            hooks = [hook for group in groups if re.fullmatch(group.get('matcher', '.*'), tool)
                     for hook in group['hooks']]
            self.assertTrue(any(h['command'].endswith('/hooks/git/native-branch-source.py') for h in hooks))
            for hook in hooks:
                script = hook['command'].replace('/path/to/claude-configs-public/', str(ROOT) + '/')
                for source, expected in [('develop', 0), ('main', 2), (None, 2)]:
                    args = ({'repository_full_name': 'electinfo/test', 'branch_name': 'feature/a', 'base_ref': source}
                            if 'codex_apps' in tool else {'owner': 'electinfo', 'repo': 'test', 'branch': 'feature/a', 'from_branch': source})
                    result = subprocess.run(shlex.split(script), input=json.dumps({'tool_name': tool, 'tool_input': args}),
                        text=True, capture_output=True)
                    self.assertEqual(result.returncode, expected, result.stderr)

    def test_plain_checkout_remote_tag_and_sha_detach_without_branch_creation(self):
        self.develop()
        self.run_git(self.repo, 'tag', 'v1', self.main)
        before = self.inspect('for-each-ref', '--format=%(refname)', 'refs/heads')
        for source in ['origin/main', 'v1', self.main]:
            item = {'args': ['checkout', source], 'cwd': str(self.repo)}
            check(item, inspect_git)
            self.run_git(self.repo, 'checkout', source)
            self.assertEqual(self.inspect('rev-parse', '--abbrev-ref', 'HEAD'), 'HEAD')
            self.assertEqual(self.inspect('for-each-ref', '--format=%(refname)', 'refs/heads'), before)
        # With no local main, bare checkout main guesses origin/main and creates
        # a branch. That different operation must retain main-source rejection.
        self.run_git(self.repo, 'branch', '-D', 'main')
        with self.assertRaises(UnknownShape):
            check({'args': ['checkout', 'main'], 'cwd': str(self.repo)}, inspect_git)

    def test_existing_own_task_exact_release_grant_is_runtime_wired(self):
        import task_keyed_gates as fixture
        self.develop()
        self.run_git(self.repo, 'tag', 'v0.15.6', self.main)
        self.run_git(self.repo, 'checkout', 'develop')
        (self.repo / 'tracked').write_text('normal develop advances\n')
        self.run_git(self.repo, 'commit', '-am', 'develop advances')
        self.run_git(self.repo, 'push', 'origin', 'develop')
        gates = fixture.Gates(methodName='runTest')
        gates.setUp()
        try:
            gates.repo = self.repo
            gate = gates.task('authorized-version-backport', self.repo)
            file = gate / 'think-gate.json'
            data = json.loads(file.read_text())
            grant = {'kind': 'release-backport', 'source_ref': 'v0.15.6', 'source_commit': self.main,
                     'destination_branch': 'backport/approved', 'user_grant_reference': 'user-message: explicit v0.15.6 backport instruction'}
            command = 'git switch -c backport/approved v0.15.6'
            payload = fixture.craft_payload(tool_name='Bash', cwd=str(self.repo), tool_input={'command': command})
            env = dict(gates.env, CLAUDE_SCOPED_OWNERS=self.base.name)
            def branch_check(request=payload):
                return subprocess.run(['bash', str(ROOT / 'hooks/git/branch-guard.sh')],
                    input=json.dumps(request), text=True, capture_output=True, env=env)
            self.assertEqual(branch_check().returncode, 2)  # Name alone grants nothing.
            data['branch_source_authorization'] = grant
            file.write_text(json.dumps(data))
            result = branch_check()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            # Match UMG's existing same-package workspace fallback outside Craft.
            shutil.copytree(ROOT / 'hooks', gates.ws / 'hooks')
            no_workspace = dict(env)
            no_workspace.pop('CRAFT_AGENT_WORKSPACE', None)
            fallback = subprocess.run(['bash', str(gates.ws / 'hooks/git/branch-guard.sh')],
                input=json.dumps(payload), text=True, capture_output=True, env=no_workspace)
            self.assertEqual(fallback.returncode, 0, fallback.stdout + fallback.stderr)
            # Ordinary task/lifecycle hooks also accept this already-granted work.
            self.assertEqual(gates.hook(command, cwd=self.repo, env=env).returncode, 0)
            self.run_git(self.repo, 'switch', '-c', 'backport/approved', 'v0.15.6')
            self.assertEqual(self.inspect('rev-parse', 'HEAD'), self.main)
            for key, value in [('status', 'planned'), ('status', 'designing'), ('status', 'reviewing'), ('status', 'complete'), ('sessionId', 'foreign'), ('role', 'reviewer'), ('role', 'read-only'), ('role', 'comment-only')]:
                changed = dict(data, **{key: value})
                file.write_text(json.dumps(changed))
                self.assertEqual(branch_check().returncode, 2, (key, value))
            for key, value in [('destination_branch', 'other/branch'), ('source_commit', 'f' * 40),
                               ('source_ref', 'other-tag'), ('user_grant_reference', '')]:
                changed = dict(data, branch_source_authorization=dict(grant, **{key: value}))
                file.write_text(json.dumps(changed))
                self.assertEqual(branch_check().returncode, 2, key)
            file.write_text(json.dumps(data))
            other = dict(payload, tool_input={'command': 'git switch -c other/branch v0.15.6'})
            self.assertEqual(branch_check(other).returncode, 2)
            changed = dict(data, scope_paths=[str(self.repo / 'unrelated')])
            file.write_text(json.dumps(changed))
            self.assertEqual(branch_check().returncode, 2)
            file.write_text(json.dumps(data))
            self.run_git(self.repo, 'commit', '--allow-empty', '-m', 'distinct backport source')
            self.run_git(self.repo, 'tag', '-f', 'v0.15.6', 'HEAD')
            self.assertEqual(branch_check().returncode, 2)  # Approved tag moved.
        finally:
            gates.tearDown()

    def test_native_github_sources_and_create_only_bootstrap(self):
        spec = importlib.util.spec_from_file_location('native_branch', ROOT / 'hooks/git/native-branch-source.py')
        native = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(native)
        for modern in (False, True):
            tool = 'mcp__codex_apps__github_create_branch' if modern else 'mcp__github-dheeraj__create_branch'
            def payload(branch, source):
                args = ({'repository_full_name': 'electinfo/example', 'branch_name': branch, 'base_ref': source}
                        if modern else {'owner': 'electinfo', 'repo': 'example', 'branch': branch, 'from_branch': source})
                return {'tool_name': tool, 'tool_input': args}
            native.check(payload('feature/correct', 'develop'))
            native.check(payload('develop', 'main'))
            native.check(payload('develop', 'refs/heads/main'))
            for branch, source in [('feature/wrong', 'main'), ('feature/omitted', None),
                                   ('release/fake', 'main'), ('develop', None), ('main', 'develop')]:
                with self.subTest(modern=modern, branch=branch, source=source), self.assertRaises(ValueError):
                    native.check(payload(branch, source))
            request = payload('develop', 'main')
            request['tool_input']['force'] = True
            with self.assertRaises(ValueError):
                native.check(request)
            request = payload('feature/wrong', None)
            request['tool_input']['sha'] = self.main
            with self.assertRaises(ValueError):
                native.check(request)


if __name__ == '__main__':
    unittest.main()
