"""Named staging risk must not inherit unrelated repository-wide files."""
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import task_keyed_gates as fixture


class GitAddRisk(unittest.TestCase):
    def setUp(self):
        self.f = fixture.Gates()
        self.f.setUp()
        self.repo = self.f.repo
        for name in ['README.md', 'docs/note.md', 'module.py', '.github/workflows/ci.yml',
                     'hooks/bash/guard.sh', 'hooks/github-project-policy.json', '-dash.md']:
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('fixture\n')
        subprocess.run(['git', '-C', str(self.repo), 'add', '--all'], check=True, timeout=10)

    def tearDown(self):
        self.f.tearDown()

    def tier(self, command, declared='A', cwd=None):
        return fixture.r.task_tier({'repo_root': str(self.repo), 'tier': declared},
                                   [str(self.repo)], command, str(cwd or self.repo))

    def task(self, artifacts=False, scope=None, sid='one', status='implementing'):
        directory = self.f.task('example/project#1174', scope or self.repo,
                                artifacts=artifacts, sid=sid, status=status)
        p = directory / 'think-gate.json'
        data = json.loads(p.read_text())
        data['tier'] = 'A'
        fixture.write(p, data)
        return directory

    def test_named_prose_and_basename_ignore_unrelated_workflow(self):
        for command in ['git add README.md', 'git add docs/note.md',
                        'git add -- docs/note.md README.md', 'git add -f -v -- -dash.md',
                        'git add --all -- docs/note.md', 'git add --update docs/note.md']:
            with self.subTest(command=command):
                self.assertEqual(self.tier(command)['floor'], 'A')

    def test_code_policy_and_workflow_floors_remain(self):
        for path, expected in [('module.py', 'B'), ('.github/workflows/ci.yml', 'C'),
                               ('hooks/bash/guard.sh', 'C'), ('hooks/github-project-policy.json', 'C')]:
            with self.subTest(path=path):
                self.assertEqual(self.tier('git add -- ' + path)['floor'], expected)
        self.assertEqual(self.tier('git add README.md module.py')['floor'], 'B')
        self.assertEqual(self.tier('git add README.md .github/workflows/ci.yml')['floor'], 'C')
        self.assertEqual(self.tier('git add README.md', declared='C')['effective'], 'C')

    def test_actual_cwd_and_git_C_are_used(self):
        self.assertEqual(self.tier('git add note.md', cwd=self.repo / 'docs')['floor'], 'A')
        self.assertEqual(self.tier('git -C ' + str(self.repo) + ' add docs/note.md', cwd=self.f.ws)['floor'], 'A')
        self.assertEqual(self.tier('git --no-pager -C docs add note.md')['floor'], 'A')

    def test_unproved_shapes_keep_whole_tree_floor(self):
        for command in ['git add', 'git add --all', 'git add docs', 'git add .',
                        'git add missing.md', 'git add "*.md"', 'git add ":(literal)README.md"',
                        'git add --pathspec-from-file README.md', 'git add --chmod=+x README.md',
                        'git -c core.hooksPath=/tmp/no-hooks add README.md',
                        'git add README.md && touch module.py', 'git add README.md > out.md',
                        'git add README.md; git add .github/workflows/ci.yml',
                        'env git add README.md', "git add 'README.md"]:
            with self.subTest(command=command):
                self.assertEqual(self.tier(command)['floor'], 'C')
        (self.repo / 'link.md').symlink_to('README.md')
        self.assertEqual(self.tier('git add link.md')['floor'], 'C')
        (self.repo / 'README.md').unlink()
        self.assertEqual(self.tier('git add README.md')['floor'], 'C')

    def test_classifier_failure_stays_C(self):
        with patch('builtins.open', side_effect=OSError('unavailable policy')):
            self.assertEqual(self.tier('git add README.md')['floor'], 'C')
        with patch.object(fixture.r.os, 'lstat', side_effect=PermissionError('unreadable target')):
            self.assertEqual(self.tier('git add README.md')['floor'], 'C')

    def test_real_hook_allows_named_prose_without_unrelated_C_artifacts(self):
        self.task()
        self.f.assertGate(0, 'git add README.md')
        self.f.assertGate(0, 'git -C ' + str(self.repo) + ' add -- docs/note.md', cwd=self.f.ws)

    def test_real_hook_retains_B_C_preparation(self):
        self.task()
        self.f.assertGate(2, 'git add module.py')
        self.f.assertGate(2, 'git add .github/workflows/ci.yml')
        self.task(artifacts=True)
        self.f.assertGate(0, 'git add module.py')
        self.f.assertGate(0, 'git add .github/workflows/ci.yml')

    def test_nested_or_other_session_task_cannot_own_git_index(self):
        self.task(scope=self.repo / 'docs')
        self.f.assertGate(2, 'git add docs/note.md')
        self.task(sid='two')
        self.f.assertGate(2, 'git add README.md')

    def test_bound_wrong_task_and_mixed_outside_write_still_deny(self):
        self.task()
        self.f.assertGate(2, "CCP_TASK_ID='example/project#99' git add README.md")
        self.f.assertGate(2, 'git add README.md && touch ' + str(self.f.ws / 'outside.md'))
        self.f.assertGate(2, 'git add .github/workflows/ci.yml README.md')

    def test_designing_status_does_not_authorize_staging(self):
        self.task(status='designing')
        self.f.assertGate(2, 'git add README.md')


if __name__ == '__main__':
    unittest.main()
