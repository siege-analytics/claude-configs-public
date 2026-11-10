"""Typed metadata posts retain their own authority beside allowlisted SSH."""
import subprocess
import json
from pathlib import Path
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

    def test_umg_proof_for_own_reports_and_ssh_needs_no_wording_or_fresh_go(self):
        own = "gh issue comment 31 --repo example/target --body 'Done; blocked; will inspect gate.'"
        for command in ['ssh cyberpower uptime', own, 'ssh cyberpower uptime && ' + own,
                        own + ' && ssh cyberpower uptime']:
            with self.subTest(command=command):
                result = self.f.hook(command)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_configured_standalone_contract_is_preserved(self):
        root = Path(__file__).resolve().parents[2]
        settings = json.loads((root / 'hooks/settings-snippet.json').read_text())
        hooks = [root / h['command'].split('/claude-configs-public/', 1)[1]
                 for group in settings['hooks']['PreToolUse'] if group.get('matcher') == 'Bash'
                 for h in group['hooks']]
        own = "gh issue comment 31 --repo example/target --body 'Done; blocked; will inspect gate.'"
        def chain(command):
            payload = fixture.craft_payload(tool_name='Bash', cwd=str(self.f.repo), tool_input={'command': command})
            return {hook.name: subprocess.run(['bash', str(hook)], input=json.dumps(payload),
                    text=True, capture_output=True, env=self.f.env, cwd=self.f.repo, timeout=20)
                    for hook in hooks}
        for command in ['ssh cyberpower uptime', own]:
            outcomes = chain(command)
            self.assertTrue(all(r.returncode == 0 for r in outcomes.values()),
                            {name: (r.returncode, r.stderr) for name, r in outcomes.items()})
        # UMG Task proof does not grant a new composed reporting format.
        self.assertEqual(chain(own + ' && ssh cyberpower uptime')['coordinator-status-guard.sh'].returncode, 2)


if __name__ == '__main__':
    unittest.main()
