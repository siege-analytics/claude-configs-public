"""Own-Task source proposals through actual UMG/destructive hooks; no gh executes."""
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import unittest
import task_keyed_gates as fixture

class Proposals(unittest.TestCase):
    task = fixture.Gates.task
    hook = fixture.Gates.hook
    tearDown = fixture.Gates.tearDown
    def setUp(self):
        fixture.Gates.setUp(self)
        for args in [('remote', 'add', 'origin', 'https://github.com/electinfo/fec-api.git'), ('checkout', '-q', '-b', 'feat/3133-source')]:
            fixture.fixture_git('-C', self.repo, *args, check=True, timeout=20)
        fixture.fixture_git('-C', self.repo, '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-q', '--allow-empty', '-m', 'Fixture #3133', check=True, timeout=20)
        self.gate = self.task('electinfo/enterprise#3133', self.repo, artifacts=False)
        self.body = self.ws / 'sessions/one/data/source-pr.md'
        self.body.parent.mkdir(parents=True)
        self.body.write_bytes((fixture.ROOT / 'hooks/_test/fixtures/source-pr-proposal-body.md').read_bytes())
        self.command = 'gh pr create --repo electinfo/fec-api --base develop --head feat/3133-source --draft --title repair --body-file ' + shlex.quote(str(self.body))

    def test_owned_source_proposal_is_not_local_operand_write(self):
        for command in [self.command, self.command.replace(' --draft', ''), 'cd ' + shlex.quote(str(self.repo)) + ' && ' + self.command]:
            result = self.hook(command, cwd=self.ws)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = fixture.craft_payload(tool_name='Bash', cwd=str(self.ws), tool_input={'command': command})
            result = subprocess.run(['bash', str(fixture.ROOT / 'hooks/bash/destructive-guard.sh')], input=json.dumps(payload), env=self.env, text=True, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_bare_legacy_create_still_requires_destructive_waiver(self):
        command = 'gh pr create'
        payload = fixture.craft_payload(tool_name='Bash', cwd=str(self.repo), tool_input={'command': command})
        result = subprocess.run(['bash', str(fixture.ROOT / 'hooks/bash/destructive-guard.sh')],
                                input=json.dumps(payload), env=self.env, text=True,
                                capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('github pull request write', result.stderr)
        for suffix in [' --repo electinfo/fec-api', ' --unknown-option', ' --draft']:
            self.assertEqual(self.hook(command + suffix, cwd=self.repo).returncode, 2)

    def test_allowlisted_ssh_cannot_borrow_proposal_exemption(self):
        # A private policy package admits one fixture host, never a network call.
        package = self.ws / 'policy'
        shutil.copytree(fixture.ROOT / 'hooks/lib', package / 'hooks/lib',
                        ignore=shutil.ignore_patterns('__pycache__'))
        (package / 'hooks/bash').mkdir(parents=True)
        hook = package / 'hooks/bash/destructive-guard.sh'
        shutil.copyfile(fixture.ROOT / 'hooks/bash/destructive-guard.sh', hook)
        (package / 'hooks/lib/ssh-host-allowlist.json').write_text(' {"hosts": ["fixture-host"]} ')
        command = self.command + " && ssh fixture-host 'aws s3 rm s3://fixture-bucket/item'"
        # Confirm the causal shape really reaches the formerly unguarded hosts field.
        probe = subprocess.run(['python3', '-B', '-c',
            'import sys,json;sys.path.insert(0,sys.argv[1]);import task_actions;print(json.dumps(task_actions.action(sys.argv[2],sys.argv[3])))',
            str(package / 'hooks/lib'), command, str(self.ws)], env=self.env,
            text=True, capture_output=True, timeout=20, check=True)
        shape = json.loads(probe.stdout)
        self.assertEqual(shape['remote_hosts'], ['fixture-host'])
        self.assertEqual(len(shape['metadata_posts']), 1)
        self.assertEqual(shape['paths'], [])
        payload = fixture.craft_payload(tool_name='Bash', cwd=str(self.ws), tool_input={'command': command})
        result = subprocess.run(['bash', str(hook)], input=json.dumps(payload), env=self.env,
                                text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('github pull request write', result.stderr)

    def test_exact_source_target_and_lifecycle_remain_required(self):
        foreign = self.ws / 'foreign.md'; foreign.write_text('foreign body')
        for command in [self.command.replace('electinfo/fec-api', 'foreign/repo'), self.command.replace('feat/3133-source', 'feat/foreign'), self.command.replace('--base develop', '--base main'), self.command.replace(str(self.body), str(foreign)), self.command + ' && gh pr close 31', self.command.replace('pr create', 'pr merge'), self.command + ' --repo electinfo/fec-api', self.command.replace(str(self.body), str(self.body) + '.missing'), self.command.replace('--body-file ' + str(self.body), '--body-file -')]:
            with self.subTest(command=command):
                self.assertEqual(self.hook(command, cwd=self.ws).returncode, 2)
        linked = self.body.parent / 'linked.md'; linked.symlink_to(self.body)
        secret = self.body.parent / 'credentials.json'; secret.write_text('{}')
        for operand in [linked, secret]:
            self.assertEqual(self.hook(self.command.replace(str(self.body), str(operand)), cwd=self.ws).returncode, 2)
        data = json.loads((self.gate / 'think-gate.json').read_text())
        for change in [{'status': 'reviewing'}, {'sessionId': 'foreign'}]:
            fixture.write(self.gate / 'think-gate.json', {**data, **change})
            self.assertEqual(self.hook(self.command, cwd=self.ws).returncode, 2)
        fixture.write(self.gate / 'think-gate.json', data)
        # File-scoped implementation remains a source-review proposal, not a
        # grant to write any additional repository files.
        fixture.write(self.gate / 'think-gate.json', {**data, 'scope_paths': [str(self.a)]})
        self.assertEqual(self.hook(self.command, cwd=self.ws).returncode, 0)

if __name__ == '__main__':
    unittest.main()
