"""Actual coordinator hook decisions; candidate gh commands never execute."""
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / 'hooks/bash/coordinator-status-guard.sh'

class Reporting(unittest.TestCase):
    def decision(self, command, hook=None):
        result = subprocess.run(['bash', str(hook or HOOK)], input=json.dumps({
            'tool_name': 'Bash', 'cwd': str(ROOT), 'tool_input': {'command': command}}),
            text=True, capture_output=True, timeout=15, env=os.environ.copy())
        return result.returncode, result.stderr

    def test_descriptive_metadata_does_not_require_status_wording(self):
        bodies = ['Done. A dependency remains blocked.', 'Status: blocked.',
                  'I will rerun deployment gates; then decide next steps.',
                  '## Investigation\nTicket: #1245\nReview complete; rollout pending.',
                  'Owner approval missing. I can continue independent work.',
                  'Literal ; && | > $(example) `example` are documentation.']
        for body in bodies:
            quoted = "'" + body.replace("'", "'\\''") + "'"
            for prefix in ['gh issue comment 1245 --body ',
                           'gh pr comment 1245 --body ',
                           'gh issue edit 1245 --body ',
                           'gh pr edit 1245 --body ',
                           'gh pr review 1245 --comment --body ']:
                with self.subTest(prefix=prefix, body=body):
                    self.assertEqual(self.decision(prefix + quoted)[0], 0)

    def test_task_binding_prefix_is_metadata_not_a_new_prose_gate(self):
        binding = 'CCP_TASK_ID=siege-analytics/claude-configs-public#1245 '
        for prefix in [binding, 'env ' + binding, binding + 'command ',
                       'LANG=C ' + binding, 'env LANG=C ' + binding]:
            for post in ["gh issue comment 1245 --body 'Status: done. Blocker: CI pending.'",
                         "gh pr review 1245 --comment --body 'I will rerun deployment gates.'"]:
                with self.subTest(prefix=prefix, post=post):
                    self.assertEqual(self.decision(prefix + post)[0], 0)
        for prefix in ['BASH_ENV=/tmp/unknown ', 'env GIT_DIR=/tmp/unknown ',
                       'env GH_HOST=foreign.example ', 'env -i ' + binding]:
            with self.subTest(prefix=prefix):
                self.assertEqual(self.decision(prefix + "gh issue comment 1245 --body 'Done. Blocked.'")[0], 2)
        self.assertEqual(self.decision(binding + "gh issue comment 1245 --body 'hello' && gh issue close 1245")[0], 2)

    def test_unmodeled_single_edits_keep_existing_checks(self):
        for command in ["gh issue edit 1245 --add-label bug",
                        "gh pr edit 1245 --title 'Fix parser'"]:
            with self.subTest(command=command):
                self.assertEqual(self.decision(command)[0], 0)
        # This was already rejected by the old editor-body inspection route.
        self.assertEqual(self.decision('gh issue comment 1245 --web')[0], 2)

    def test_helper_failures_decline_the_metadata_lane(self):
        import sys
        import tempfile
        from unittest.mock import patch
        sys.path.insert(0, str(ROOT / 'hooks/lib'))
        from github_metadata_comment import metadata_comment
        # Existing literal-prefix parser declines unsupported env options.
        self.assertIsNone(metadata_comment('env -i gh issue comment 31 --body done', str(ROOT)))
        with tempfile.TemporaryDirectory() as directory:
            body = Path(directory) / 'body.md'
            body.write_text('Done; this is descriptive.')
            with patch('github_metadata_comment.Path.open', side_effect=OSError('fixture denied')):
                self.assertIs(metadata_comment('gh issue comment 31 --body-file ' + str(body), directory), False)

    def test_configured_chain_keeps_task_authority(self):
        import shutil
        import task_keyed_gates as fixture
        f = fixture.Gates()
        f.setUp()
        self.addCleanup(f.tearDown)
        subprocess.run(['git', '-C', str(f.repo), 'remote', 'add', 'origin',
                        'https://github.com/example/target.git'], check=True, timeout=15)
        f.task('example/target#31', f.repo)
        # PR creation remains its existing ordinary Task mutation, not this lane.
        self.assertEqual(f.hook("gh pr create --base develop --title 'source change' --body text").returncode, 0)
        settings = json.loads((ROOT / 'hooks/settings-snippet.json').read_text())
        hooks = [ROOT / h['command'].split('/claude-configs-public/', 1)[1]
                 for group in settings['hooks']['PreToolUse'] if group.get('matcher') == 'Bash'
                 for h in group['hooks']]
        self.assertEqual(len(hooks), 16)
        def chain(command):
            payload = fixture.craft_payload(tool_name='Bash', cwd=str(f.repo),
                                             tool_input={'command': command})
            outcomes = {}
            for hook in hooks:
                result = subprocess.run(['bash', str(hook)], input=json.dumps(payload),
                                        env=f.env, text=True, capture_output=True,
                                        cwd=f.repo, timeout=15)
                self.assertIn(result.returncode, [0, 2], (hook.name, result.stderr))
                outcomes[hook.name] = (result.returncode, result.stderr)
            return outcomes
        commands = [
            "CCP_TASK_ID='example/target#31' gh issue comment 31 --repo example/target --body 'Done; CI is blocked. I will rerun gates.'",
            "CCP_TASK_ID='example/target#31' gh pr comment 50 --repo example/target --body 'Review done; literal | & < > $ and `example` are data.'",
        ]
        for command in commands:
            with self.subTest(command=command):
                outcomes = chain(command)
                self.assertTrue(all(code == 0 for code, _ in outcomes.values()), outcomes)
        for command in [
            "CCP_TASK_ID='example/target#31' gh pr comment 50 --repo other/repo --body x",
            "CCP_TASK_ID='example/target#31' gh issue comment https://github.com/other/repo/issues/31 --body x",
        ]:
            with self.subTest(foreign_target=command):
                outcomes = chain(command)
                self.assertEqual(outcomes['universal-mutation-gate.sh'][0], 2, outcomes)
        conflict = "CCP_TASK_ID='example/target#31' gh issue comment https://github.com/example/target/issues/99 --repo other/repo --body x"
        self.assertEqual(chain(conflict)['universal-mutation-gate.sh'][0], 2)
        f.env['GH_REPO'] = 'other/repo'
        self.assertTrue(all(code == 0 for code, _ in chain(commands[0]).values()))
        self.assertEqual(chain('gh issue comment 31 --body x')['universal-mutation-gate.sh'][0], 2)
        del f.env['GH_REPO']
        f.task('example/target#32', f.repo)
        self.assertEqual(chain('gh pr comment 50 --repo example/target --body x')['universal-mutation-gate.sh'][0], 2)
        self.assertTrue(all(code == 0 for code, _ in chain(commands[0]).values()))
        shutil.rmtree(f.ws / 'sessions/one/tasks')
        f.task('governance/tickets#31', f.b)
        cross = "CCP_TASK_ID='governance/tickets#31' gh issue comment 31 --repo governance/tickets --body 'report pending; done with current check'"
        self.assertTrue(all(code == 0 for code, _ in chain(cross).values()))
        shutil.rmtree(f.ws / 'sessions/one/tasks')
        self.assertEqual(chain('gh issue comment 31 --repo example/target --body x')['universal-mutation-gate.sh'][0], 2)
        outcomes = chain(commands[0])
        self.assertEqual(outcomes['universal-mutation-gate.sh'][0], 2, outcomes)
        self.assertEqual(outcomes['destructive-guard.sh'][0], 0, outcomes)
        # Reporting does not require fictional write scope over the whole repo.
        f.task('example/target#31', f.b)
        outcomes = chain(commands[0].replace('comment 31', 'comment 99'))
        self.assertTrue(all(code == 0 for code, _ in outcomes.values()), outcomes)
        # A real other-repository Task does not authorize this remote target.
        shutil.rmtree(f.ws / 'sessions/one/tasks')
        other = f.ws / 'other'; other.mkdir()
        subprocess.run(['git', 'init', '-q', str(other)], check=True, timeout=15)
        subprocess.run(['git', '-C', str(other), 'remote', 'add', 'origin',
                        'https://github.com/other/allowed.git'], check=True, timeout=15)
        f.task('example/target#31', other)
        outcomes = chain(commands[1])  # A PR is not this task's canonical issue.
        self.assertEqual(outcomes['universal-mutation-gate.sh'][0], 2, outcomes)
        self.assertEqual(outcomes['destructive-guard.sh'][0], 0, outcomes)

    def test_issue_create_uses_actual_1251_bodies_without_word_gates(self):
        import shlex
        import task_keyed_gates as fixture
        f = fixture.Gates(); f.setUp(); self.addCleanup(f.tearDown)
        subprocess.run(['git', '-C', str(f.repo), 'remote', 'add', 'origin',
                        'https://github.com/siege-analytics/siege_utilities.git'], check=True, timeout=15)
        f.task('siege-analytics/siege_utilities#1812', f.b)
        entries = json.loads((ROOT / 'hooks/_test/fixtures/metadata-issues-1251.json').read_text())
        settings = json.loads((ROOT / 'hooks/settings-snippet.json').read_text())
        hooks = [ROOT / h['command'].split('/claude-configs-public/', 1)[1]
                 for group in settings['hooks']['PreToolUse'] if group.get('matcher') == 'Bash'
                 for h in group['hooks']]
        self.assertEqual(len(hooks), 16)
        for entry in entries:
            command = shlex.join(['gh', 'issue', 'create', '--repo', 'siege-analytics/siege_utilities',
                                   '--title', entry['title'], '--body', entry['body']])
            payload = fixture.craft_payload(tool_name='Bash', cwd=str(f.repo), tool_input={'command':command})
            for hook in hooks:
                result = subprocess.run(['bash', str(hook)], input=json.dumps(payload), env=f.env,
                                        text=True, capture_output=True, cwd=f.repo, timeout=15)
                self.assertEqual(result.returncode, 0, (entry['url'], hook.name, result.stderr))
            # Creating a ticket does not donate authority to a subsequent close.
            self.assertEqual(self.decision(command + ' && gh issue close 1812')[0], 2)
            self.assertEqual(f.hook(command.replace('siege-analytics/siege_utilities', 'other/repo')).returncode, 2)

    def test_unparsed_single_metadata_keeps_existing_coordinator_checks(self):
        for command in ["gh issue edit 1245 --title x # trailing note",
                        "gh issue edit 1245 \\\n--title x"]:
            with self.subTest(command=command):
                self.assertEqual(self.decision(command)[0], 0)

    def test_existing_typed_metadata_route_is_not_replaced(self):
        import shlex
        commands = [
            'cd ' + shlex.quote(str(ROOT)) + " && gh issue edit 1245 --title 'Clarify scope'",
            'cd ' + shlex.quote(str(ROOT)) + " && gh pr comment 12 --edit-last --body notes",
            "gh issue edit 1245 --title x\n",
            "gh issue edit 1245 --title t --body ''",
        ]
        for hook in [HOOK, ROOT / 'hooks/bash/destructive-guard.sh']:
            for command in commands:
                with self.subTest(hook=hook.name, command=command):
                    self.assertEqual(self.decision(command, hook)[0], 0)

    def test_state_and_compound_commands_never_borrow_comment_lane(self):
        for command in [
            "gh issue close 1245 --reason completed", 'gh issue reopen 1245',
            'gh pr ready 1245', "gh pr review 1245 --approve --body 'done'",
            "gh pr review 1245 --request-changes --body 'done'",
            "gh issue comment 1245 --body 'hello' && gh issue close 1245",
            "printf hello && gh issue comment 1245 --body 'hello'",
            "gh issue comment 1245 --body 'hello'; gh pr ready 1245",
            "gh issue comment 1245 --body 'hello' | gh pr merge 1245",
            "gh issue comment 1245 --body 'hello' > /tmp/other",
            "gh issue comment 1245 --body 'done' --unknown",
            "gh pr edit 1245 --body 'done' --base main",
            'gh issue comment 1245 --body "$BODY"',
            "gh pr review 1245 --comment --approve --body 'done'",
        ]:
            with self.subTest(command=command):
                self.assertEqual(self.decision(command)[0], 2)

if __name__ == '__main__':
    unittest.main()
