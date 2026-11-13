"""Real Task/hook decisions for unchanged worktree materialization (#1171)."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import task_keyed_gates as fixture


class Materialization(unittest.TestCase):
    def setUp(self):
        inherited_git = {'GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_INDEX_FILE',
                         'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES',
                         'GIT_PREFIX', 'GIT_CONFIG', 'GIT_CONFIG_PARAMETERS',
                         'GIT_CONFIG_COUNT', 'GIT_TEMPLATE_DIR', 'GIT_SSH',
                         'GIT_SSH_COMMAND', 'GIT_EXEC_PATH'}
        isolated = patch.dict(os.environ, {k: v for k, v in os.environ.items()
                                          if k not in inherited_git}, clear=True)
        isolated.start()
        self.addCleanup(isolated.stop)
        self.f = fixture.Gates()
        original = tempfile.TemporaryDirectory
        with patch.object(fixture.tempfile, 'TemporaryDirectory', side_effect=lambda **kw:
                          original(prefix=kw['prefix'], dir=os.path.realpath(tempfile.gettempdir()))):
            self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.repo = self.f.repo
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        (self.repo / '.github/workflows').mkdir(parents=True)
        (self.repo / '.github/workflows/ci.yml').write_text('name: unchanged\n')
        (self.repo / '.review').mkdir()
        (self.repo / '.review/release-1.0.md').write_text('unchanged release evidence\n')
        (self.repo / 'app.py').write_text('value = 1\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture baseline')
        self.base = self.git('rev-parse', 'HEAD').stdout.strip()
        self.git('update-ref', 'refs/remotes/origin/develop', self.base)
        self.git('update-ref', 'refs/remotes/origin/main', self.base)
        self.git('remote', 'add', 'origin', 'https://github.com/siege-analytics/materialization-fixture.git')
        self.destination = self.repo / 'task-checkout'
        self.gate = self.f.task('example/project#1171', self.repo)
        for name in ('junior-senior-gate.json', 'artifacts-posted-gate.json'):
            (self.gate / name).unlink()
        self.data = json.loads((self.gate / 'think-gate.json').read_text())
        self.data['tier'] = 'B'
        self.save_gate()

    def save_gate(self):
        fixture.write(self.gate / 'think-gate.json', self.data)

    def git(self, *args):
        return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(self.repo), *args],
                              text=True, capture_output=True, check=True, timeout=15)

    def command(self, *, source='origin/develop', destination=None, branch='feature/task'):
        return shlex.join(['git', 'worktree', 'add', '-b', branch,
                           str(destination or self.destination), source])

    def hook(self, command=None, expected=0):
        result = self.f.hook(command or self.command())
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def tier_c(self, command=None):
        verdict = fixture.r.task_tier(self.data, [str(self.repo), str(self.destination)], command or self.command(), str(self.repo))
        self.assertEqual(verdict['effective'], 'C', verdict)
        return verdict

    def test_unchanged_workflow_materialization_is_not_authored_change(self):
        self.hook()

    def test_owned_sibling_materializes_and_preserves_active_work(self):
        destination = self.f.ws / 'assigned-sibling'
        self.data['scope_paths'] = [str(self.repo), str(destination)]
        self.save_gate()
        (self.repo / 'app.py').write_text('value = 2\n')
        before = self.git('status', '--porcelain').stdout
        command = self.command(destination=destination)
        self.hook(command)
        self.branch_guard(command, 0)
        self.configured_chain(command)
        subprocess.run(shlex.split(command), cwd=self.repo, env=self.f.env,
                       text=True, capture_output=True, check=True, timeout=15)
        self.assertEqual((destination / '.github/workflows/ci.yml').read_text(), 'name: unchanged\n')
        self.assertEqual((destination / 'app.py').read_text(), 'value = 1\n')
        self.assertEqual(self.git('status', '--porcelain').stdout, before)

    def branch_guard(self, command, expected):
        payload = fixture.craft_payload(tool_name='Bash', cwd=str(self.repo), tool_input={'command': command})
        root = Path(__file__).resolve().parents[2]
        result = subprocess.run(['bash', str(root / 'hooks/git/branch-guard.sh')],
                                input=json.dumps(payload), text=True, capture_output=True,
                                cwd=self.repo, env=self.f.env, timeout=20)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)

    def configured_chain(self, command):
        root = Path(__file__).resolve().parents[2]
        settings = json.loads((root / 'hooks/settings-snippet.json').read_text())
        payload = fixture.craft_payload(tool_name='Bash', cwd=str(self.repo), tool_input={'command': command})
        for group in settings['hooks']['PreToolUse']:
            if group.get('matcher') != 'Bash':
                continue
            for hook in group['hooks']:
                path = root / hook['command'].split('/claude-configs-public/', 1)[1]
                result = subprocess.run(['bash', str(path)], input=json.dumps(payload),
                                        text=True, capture_output=True, env=self.f.env,
                                        cwd=self.repo, timeout=20)
                self.assertEqual(result.returncode, 0, str(path) + ': ' + result.stdout + result.stderr)

    def test_main_source_does_not_gain_branch_authority(self):
        # Tier assessment is not source authorization, even for equal commits.
        self.hook(self.command(source='origin/main'))
        self.branch_guard(self.command(source='origin/main'), 2)
        self.branch_guard(self.command(), 0)

    def test_existing_branch_and_detached_review_remain_supported(self):
        self.git('branch', 'existing-review', self.base)
        for command in [shlex.join(['git', 'worktree', 'add', str(self.destination), 'existing-review']),
                        shlex.join(['git', 'worktree', 'add', '--detach', str(self.destination), 'origin/main'])]:
            with self.subTest(command=command):
                self.hook(command)
                self.branch_guard(command, 0)

    def test_known_local_develop_remains_valid_without_remote_tracking(self):
        self.git('branch', 'develop', self.base)
        self.git('update-ref', '-d', 'refs/remotes/origin/develop')
        self.hook(self.command(source='develop'))
        self.branch_guard(self.command(source='develop'), 0)

    def test_risky_working_staged_committed_and_untracked_paths_stay_c(self):
        workflow = self.repo / '.github/workflows/ci.yml'
        workflow.write_text('name: authored change\n')
        self.tier_c()
        self.git('add', '.github/workflows/ci.yml')
        self.tier_c()
        self.git('commit', '-qm', 'fixture actual risky commit')
        self.tier_c()
        self.git('reset', '--hard', self.base)
        (self.repo / '.github/workflows/new.yml').write_text('name: new\n')
        self.tier_c()

    def test_materialized_revision_delta_stays_c(self):
        (self.repo / '.github/workflows/ci.yml').write_text('name: changed source\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture risky source')
        self.git('update-ref', 'refs/heads/reviewed-source', self.git('rev-parse', 'HEAD').stdout.strip())
        self.git('reset', '--hard', self.base)
        self.tier_c(self.command(source='reviewed-source'))

    def test_scope_lifecycle_and_declared_c_are_not_relaxed(self):
        self.hook(self.command(destination=self.f.ws / 'unassigned'), expected=2)
        self.data['status'] = 'designing'
        self.save_gate()
        self.hook(expected=2)
        self.data['status'] = 'implementing'
        self.data['tier'] = 'C'
        self.save_gate()
        self.tier_c()

    def test_foreign_session_and_foreign_existing_repository_remain_denied(self):
        self.data['sessionId'] = 'another-session'
        self.save_gate()
        self.hook(expected=2)
        self.data['sessionId'] = 'one'
        foreign = self.f.ws / 'foreign'
        subprocess.run(['git', 'init', '-q', str(foreign)], check=True, capture_output=True, env=self.f.env, timeout=20)
        self.data['scope_paths'] = [str(self.repo), str(foreign)]
        self.save_gate()
        self.hook(self.command(destination=foreign / 'assigned-but-foreign-repo'), expected=2)

    def test_risky_destination_and_existing_destination_stay_c(self):
        self.tier_c(self.command(destination=self.repo / '.github/workflows/checkout'))
        self.destination.mkdir()
        self.tier_c()

    def test_missing_baseline_revision_and_listing_failure_stay_c(self):
        self.tier_c(self.command(source='missing-source'))
        original = fixture.r._git_lines
        for failed_prefix in [('ls-files', '--others'), ('diff', '--no-ext-diff'),
                              ('rev-parse', '--show-toplevel'), ('merge-base',)]:
            def unavailable(repo, *args):
                return None if args[:len(failed_prefix)] == failed_prefix else original(repo, *args)
            with self.subTest(failed_prefix=failed_prefix), patch.object(fixture.r, '_git_lines', side_effect=unavailable):
                verdict = fixture.r.task_tier(self.data, [str(self.repo), str(self.destination)], self.command(), str(self.repo))
                self.assertEqual(verdict['floor'], 'C')
        self.git('update-ref', '-d', 'refs/remotes/origin/develop')
        self.tier_c()

    def test_unsupported_forms_do_not_acquire_narrowed_risk(self):
        for command in [self.command().replace('worktree add', 'worktree add --force'),
                        self.command().replace(' -b ', ' -B '),
                        self.command() + ' && touch app.py',
                        'env ' + self.command(),
                        self.command().rsplit(' ', 1)[0]]:
            with self.subTest(command=command):
                self.tier_c(command)
                self.hook(command)


if __name__ == '__main__':
    unittest.main()
