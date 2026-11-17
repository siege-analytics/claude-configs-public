#!/usr/bin/env python3
"""Private Git histories exercise promotion coverage and real missing changes."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('canonical_main', ROOT / 'scripts/ci/canonical_main.py')
POLICY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POLICY)


class MainCoverage(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name).resolve()
        self.environment = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        self.environment.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.initial = self.commit('initial')
        self.git('checkout', '-b', 'develop')
        self.develop = self.commit('develop')
        self.git('checkout', 'main')
        self.git('merge', '--no-ff', '-m', 'Promotion', 'develop')
        self.main = self.git('rev-parse', 'HEAD')
        self.git('checkout', '-b', 'feature/work', self.develop)
        self.head = self.commit('feature')

    def git(self, *arguments):
        return subprocess.check_output(
            ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false',
             '-C', str(self.repo), *arguments], env=self.environment,
            stderr=subprocess.PIPE, text=True, timeout=20,
        ).strip()

    def commit(self, filename):
        (self.repo / filename).write_text(filename + '\n')
        self.git('add', filename)
        self.git('commit', '-m', filename)
        return self.git('rev-parse', 'HEAD')

    def coverage(self, main=None, head=None):
        # The pure implementation inherits only this fixture's Git environment.
        original = POLICY.subprocess
        class PrivateProcess:
            DEVNULL = subprocess.DEVNULL
            @staticmethod
            def check_output(*args, timeout, **kwargs):
                return subprocess.check_output(*args, timeout=timeout, env=self.environment, **kwargs)
            @staticmethod
            def run(*args, timeout, **kwargs):
                return subprocess.run(*args, timeout=timeout, env=self.environment, **kwargs)
        POLICY.subprocess = PrivateProcess
        try:
            return POLICY.covers_main(self.repo, main or self.main, head or self.head)
        finally:
            POLICY.subprocess = original

    def test_feature_and_develop_cover_content_identical_promotion(self):
        self.assertTrue(self.coverage())
        self.assertTrue(self.coverage(head=self.develop))

    def test_ordinary_main_ancestor_still_passes(self):
        self.assertTrue(self.coverage(main=self.initial))
        self.assertTrue(self.coverage(head=self.main))

    def test_consecutive_content_identical_promotions_need_no_backmerge(self):
        self.git('checkout', 'develop')
        second = self.commit('second')
        self.git('checkout', 'main')
        self.git('merge', '--no-ff', '-m', 'Second promotion', 'develop')
        main = self.git('rev-parse', 'HEAD')
        self.git('checkout', '-b', 'feature/second', second)
        head = self.commit('after-second')
        self.assertTrue(self.coverage(main=main, head=head))

    def test_candidate_missing_promoted_content_is_refused(self):
        self.assertFalse(self.coverage(head=self.initial))

    def test_single_parent_hotfix_is_refused(self):
        self.git('checkout', 'main')
        hotfix = self.commit('hotfix')
        self.assertFalse(self.coverage(main=hotfix))

    def test_merge_resolution_change_is_refused(self):
        self.git('checkout', 'main')
        (self.repo / 'extra').write_text('Not in promoted tree\n')
        self.git('add', 'extra')
        self.git('commit', '--amend', '--no-edit')
        self.assertFalse(self.coverage(main=self.git('rev-parse', 'HEAD')))

    def test_identical_tree_does_not_erase_unmerged_main_history(self):
        self.git('checkout', '-b', 'hot-main', self.initial)
        hotfix = self.commit('hotfix')
        tree = self.git('rev-parse', self.develop + '^{tree}')
        forged = self.git('commit-tree', tree, '-p', hotfix, '-p', self.develop, '-m', 'Not a pure promotion')
        self.assertFalse(self.coverage(main=forged))

    def test_unavailable_object_is_an_error(self):
        with self.assertRaises(subprocess.SubprocessError):
            self.coverage(main='0' * 40)

    def test_missing_git_is_an_error(self):
        self.environment['PATH'] = str(self.repo / 'no-bin')
        with self.assertRaises(OSError):
            self.coverage()

    def test_ancestry_command_failure_is_an_error(self):
        real_git = shutil.which('git')
        self.assertIsNotNone(real_git)
        directory = self.repo / 'private-bin'
        directory.mkdir()
        wrapper = directory / 'git'
        wrapper.write_text('#!' + sys.executable + '\nimport os,sys\n'
                           "if 'merge-base' in sys.argv: sys.exit(73)\n"
                           'os.execv(' + repr(real_git) + ', [' + repr(real_git) + '] + sys.argv[1:])\n')
        wrapper.chmod(0o700)
        self.environment['PATH'] = str(directory)
        with self.assertRaises(ValueError):
            self.coverage()

    def test_cli_preserves_positive_negative_and_incomplete_results(self):
        for main, head, expected in [(self.main, self.head, 0),
                                     (self.main, self.initial, 1), ('0' * 40, self.head, 2)]:
            result = subprocess.run(
                [sys.executable, str(ROOT / 'scripts/ci/canonical_main.py'), main, head],
                cwd=self.repo, env=self.environment, capture_output=True, text=True, timeout=20,
            )
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        result = subprocess.run(
            [sys.executable, str(ROOT / 'scripts/ci/canonical_main.py'), self.main, self.head],
            cwd=self.repo, env=dict(self.environment, PATH=str(self.repo / 'no-bin')),
            capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
