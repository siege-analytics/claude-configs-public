#!/usr/bin/env python3
"""#1327: bounded native cleanliness reads and composed task ownership."""
import importlib.util
from pathlib import Path
import shlex
import subprocess
import sys
import unittest

import task_keyed_gates as fixture

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('diff_files_reader', ROOT / 'hooks/lib/read-only-command.py')
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
sys.path.insert(0, str(ROOT / 'hooks/lib'))
import task_actions


class DiffFilesReader(unittest.TestCase):
    def setUp(self):
        self.f = fixture.Gates()
        self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.probe = shlex.join(['git', '-C', str(self.f.repo), 'diff-files', '--quiet'])

    def test_exact_probe_without_task_and_in_nonimplementing_phases(self):
        for phase in ('absent', 'designing', 'reviewing'):
            if phase != 'absent':
                self.f.task('design', self.f.repo, status=phase, artifacts=False)
            for command in ('git diff-files --quiet', self.probe, self.probe + ' && git status'):
                with self.subTest(phase=phase, command=command):
                    self.assertEqual(reader.main(command), 0)
                    self.assertTrue(task_actions.action(command, str(self.f.repo))['read_only'])
                    self.f.assertGate(0, command)

    def test_options_config_expansions_and_shell_companions_are_not_readers(self):
        for tail in ('', '-q', '--quiet --unknown', '--quiet --output=outside',
                     '--quiet -ooutside', '--quiet --ext-diff', '--quiet --textconv',
                     '--quiet --help', '--quiet --exit-code', '--quiet -- file'):
            command = 'git diff-files ' + tail
            with self.subTest(command=command):
                self.assertNotEqual(reader.main(command), 0)
                self.f.assertGate(2, command)
        for command in ('git -c diff.external=evil diff-files --quiet',
                        'git --config-env=diff.external=EVIL diff-files --quiet',
                        'git diff-files $OPTIONS', 'git diff-files "${OPTIONS}"',
                        self.probe + ' > outside', self.probe + ' | tee outside',
                        self.probe + '; touch outside', self.probe + ' && bash evil.sh'):
            with self.subTest(command=command):
                self.assertNotEqual(reader.main(command), 0)
                self.f.assertGate(2, command)
        self.assertEqual(reader.main('git diff-files --quiet --ext-diff'), 3)
        self.assertEqual(reader.main('git diff-files --quiet --textconv'), 3)
        self.assertEqual(reader.main('git diff-files --quiet --output=outside'), 3)

    def test_companion_mutations_keep_exact_task_and_file_scope(self):
        self.f.task('active', self.f.a)
        self.f.task('design', self.f.b, status='designing', artifacts=False)
        allowed = self.probe + ' && touch ' + shlex.quote(str(self.f.a / 'owned'))
        result = task_actions.action(allowed, str(self.f.repo))
        self.assertFalse(result['read_only'])
        self.assertEqual(result['paths'], [str(self.f.a / 'owned')])
        self.f.assertGate(0, allowed)
        for target in (self.f.b / 'unowned', self.f.repo / 'outside'):
            self.f.assertGate(2, self.probe + ' && touch ' + shlex.quote(str(target)))
        self.assertFalse((self.f.a / 'owned').exists())

    def test_actual_plumbing_defaults_do_not_run_diff_helpers_or_write_index(self):
        env = {k: v for k, v in self.f.env.items() if not k.startswith('GIT_')}
        env.update(GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1')
        def git(*args):
            return subprocess.run(['git', '-C', str(self.f.repo), *args], env=env,
                                  capture_output=True, text=True, timeout=15)
        tracked = self.f.repo / 'tracked'
        tracked.write_text('before\n')
        self.assertEqual(git('add', 'tracked').returncode, 0)
        marker = self.f.ws / 'helper-ran'
        helper = self.f.ws / 'helper.sh'
        helper.write_text('#!/bin/sh\ntouch ' + shlex.quote(str(marker)) + '\nexit 1\n')
        helper.chmod(0o755)
        env.update(GIT_EXTERNAL_DIFF=str(helper), GIT_EXTERNAL_DIFF_TRUST_EXIT_CODE='1')
        for key, value in [('diff.external', str(helper)), ('diff.trustExitCode', 'true'),
                           ('diff.fixture.command', str(helper)), ('diff.fixture.trustExitCode', 'true'),
                           ('diff.fixture.textconv', str(helper))]:
            self.assertEqual(git('config', key, value).returncode, 0)
        (self.f.repo / '.gitattributes').write_text('tracked diff=fixture\n')
        for changed in (False, True):
            if changed:
                tracked.write_text('different contents\n')
            before = {p.relative_to(self.f.repo): p.read_bytes() for p in self.f.repo.rglob('*') if p.is_file()}
            result = git('diff-files', '--quiet')
            self.assertEqual((result.returncode, result.stdout), (int(changed), ''))
            self.assertFalse(marker.exists())
            self.assertEqual({p.relative_to(self.f.repo): p.read_bytes() for p in self.f.repo.rglob('*') if p.is_file()}, before)
        # A pre-existing private index is selected by Git's environment, not -C.
        # Prove both comparisons without changing the fixture's default index.
        private = self.f.ws / 'private-index'
        private_env = dict(env, GIT_INDEX_FILE=str(private))
        subprocess.run(['git', '-C', str(self.f.repo), 'read-tree', '--empty'],
                       env=private_env, check=True, capture_output=True, timeout=15)
        before_private = private.read_bytes()
        result = subprocess.run(['git', '-C', str(self.f.repo), 'diff-files', '--quiet'],
                                env=private_env, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(private.read_bytes(), before_private)
        self.assertEqual(git('diff-files', '--quiet').returncode, 1)
        # Negative real-effects control: quiet does not suppress a trusted helper
        # enabled by --ext-diff. This shape remains vetoed above.
        self.assertEqual(git('diff-files', '--quiet', '--ext-diff').returncode, 1)
        self.assertTrue(marker.exists())


if __name__ == '__main__':
    unittest.main()
