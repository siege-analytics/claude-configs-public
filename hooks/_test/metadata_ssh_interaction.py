"""Typed metadata posts retain their own authority beside allowlisted SSH."""
import subprocess
import unittest

import task_keyed_gates as fixture


class Interaction(unittest.TestCase):
    def setUp(self):
        self.f = fixture.Gates()
        self.f.setUp()
        self.addCleanup(self.f.tearDown)
        subprocess.run(['git', '-C', str(self.f.repo), 'remote', 'add', 'origin',
                        'https://github.com/example/target.git'], check=True)
        self.f.task('example/target#31', self.f.b, status='designing', artifacts=False)

    def test_foreign_post_cannot_hide_behind_allowed_ssh(self):
        foreign = "gh issue comment 31 --repo other/repo --body 'Done; blocked; will inspect gate.'"
        for command in ['ssh cyberpower uptime && ' + foreign, foreign + ' && ssh cyberpower uptime']:
            with self.subTest(command=command):
                shape = fixture.r.action(command, str(self.f.repo))
                self.assertEqual(len(shape.get('metadata_posts', [])), 1)
                self.assertFalse(shape.get('metadata_only'))
                self.assertFalse(shape.get('remote_contact_only'))
                result = self.f.hook(command)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_own_reports_and_ssh_remain_valid_without_wording_or_fresh_go(self):
        own = "gh issue comment 31 --repo example/target --body 'Done; blocked; will inspect gate.'"
        for command in ['ssh cyberpower uptime', own, 'ssh cyberpower uptime && ' + own,
                        own + ' && ssh cyberpower uptime']:
            with self.subTest(command=command):
                result = self.f.hook(command)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
