"""PR descriptions bypass status vocabulary, never operation authorization."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import task_keyed_gates as fixture

ROOT = Path(__file__).resolve().parents[2]
BODY = 'Nothing is tagged, released, uploaded or merged to main. Read-only verification reports docs/conf.py missing, as already on develop.'
MARKER = '[destructive-ok: Reason: approved fixture PR; Evidence: explicit existing test grant; Falsification: wrong scope or failed checks]'


class PRDescription(unittest.TestCase):
    def setUp(self):
        self.f = fixture.Gates()
        original = tempfile.TemporaryDirectory
        with patch.object(fixture.tempfile, 'TemporaryDirectory', side_effect=lambda **kw:
                          original(prefix=kw['prefix'], dir=os.path.realpath(tempfile.gettempdir()))):
            self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('remote', 'add', 'origin', 'https://github.com/siege-analytics/pr-body-fixture.git')
        readme = self.f.repo / 'README.md'
        readme.write_text('baseline\n')
        self.git('add', 'README.md')
        self.git('commit', '-qm', 'baseline')
        self.git('update-ref', 'refs/remotes/origin/develop', self.git('rev-parse', 'HEAD'))
        self.git('checkout', '-qb', 'fix/fixture', 'origin/develop')
        readme.write_text('baseline\nmechanical change\n')
        self.git('add', 'README.md')
        self.git('commit', '-qm', 'docs: fixture\n\nRefs #1885\n\nReview-Tier: A\nSelf-Review: Read the fixture documentation change.')
        self.gate = self.f.task('siege-analytics/pr-body-fixture#1885', self.f.repo)

    def git(self, *args):
        return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(self.f.repo), *args],
                                       text=True, stderr=subprocess.PIPE).strip()

    def command(self, body=BODY, marker=True):
        result = shlex.join(['gh', 'pr', 'create', '--base', 'develop', '--body', body, '--title', 'Mechanical release bucket'])
        return result + (' # ' + MARKER if marker else '')

    def hook(self, path, command):
        payload = fixture.craft_payload(tool_name='Bash', cwd=str(self.f.repo), tool_input={'command': command})
        return subprocess.run(['bash', str(ROOT / path)], input=json.dumps(payload),
                              text=True, capture_output=True, cwd=self.f.repo, env=self.f.env, timeout=30)

    def chain(self, command):
        settings = json.loads((ROOT / 'hooks/settings-snippet.json').read_text())
        return {Path(h['command']).name: self.hook(h['command'].split('/claude-configs-public/', 1)[1], command)
                for group in settings['hooks']['PreToolUse'] if group.get('matcher') == 'Bash'
                for h in group['hooks']}

    def test_descriptive_create_passes_full_configured_chain_with_existing_authority(self):
        body_file = self.f.repo / 'pr-description.md'
        body_file.write_text(BODY)
        file_command = shlex.join(['gh', 'pr', 'create', '--base', 'develop',
                                  '--title', 'Mechanical release bucket', '--body-file', str(body_file)]) + ' # ' + MARKER
        for command in [self.command(), file_command]:
            with self.subTest(command=command):
                outcomes = self.chain(command)
                self.assertEqual(len(outcomes), 16)
                self.assertTrue(all(r.returncode == 0 for r in outcomes.values()),
                                {name: (r.returncode, r.stderr) for name, r in outcomes.items() if r.returncode})

    def test_create_does_not_enter_task_free_metadata_lane(self):
        from github_metadata_comment import metadata_comment
        self.assertIsNone(metadata_comment(self.command(), str(self.f.repo)))
        self.assertFalse(fixture.r.action(self.command(), str(self.f.repo)).get('metadata_only'))
        shutil.rmtree(self.f.ws / 'sessions/one/tasks')
        self.assertEqual(self.chain(self.command())['universal-mutation-gate.sh'].returncode, 2)

    def test_wrong_scope_and_missing_marker_still_fail_proper_guards(self):
        data = json.loads((self.gate / 'think-gate.json').read_text())
        data['scope_paths'] = [str(self.f.a)]
        fixture.write(self.gate / 'think-gate.json', data)
        self.assertEqual(self.chain(self.command())['universal-mutation-gate.sh'].returncode, 2)
        self.assertEqual(self.chain(self.command(marker=False))['destructive-guard.sh'].returncode, 2)

    def test_state_actions_and_composition_do_not_borrow_description_exemption(self):
        for command in ['gh pr close 1 --comment ' + shlex.quote(BODY),
                        'gh pr review 1 --approve --body ' + shlex.quote(BODY),
                        self.command() + '\ngh pr close 1',
                        self.command(marker=False) + ' && gh pr close 1']:
            with self.subTest(command=command):
                self.assertEqual(self.hook('hooks/bash/coordinator-status-guard.sh', command).returncode, 2)


if __name__ == '__main__':
    unittest.main()
