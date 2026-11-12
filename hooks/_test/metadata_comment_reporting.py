"""Actual coordinator hook decisions; candidate gh commands never execute."""
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / 'hooks/bash/coordinator-status-guard.sh'

class Reporting(unittest.TestCase):
    def test_private_report_task_posts_only_its_exact_canonical_issue(self):
        import shlex
        import shutil
        import tempfile
        from unittest.mock import patch
        import task_keyed_gates as fixture
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        f = fixture.Gates()
        # The default fixture is nested below this source Git checkout. A real
        # private report workspace must not inherit its repository as a witness.
        with patch.object(fixture, 'ROOT', Path(temporary.name)):
            f.setUp()
        self.addCleanup(f.tearDown)
        private = f.ws / 'sessions/one/data'; private.mkdir()
        body = private / 'senior.md'; body.write_text('Senior review complete; owner hold remains.\n')
        gate = f.task('example/target#803', private, status='reviewing', artifacts=False)
        data = json.loads((gate / 'think-gate.json').read_text())
        data['repo_root'] = str(private)
        fixture.write(gate / 'think-gate.json', data)
        command = 'gh issue comment 803 --repo example/target --body-file ' + shlex.quote(str(body))
        result = f.hook(command, cwd=private)
        self.assertEqual(result.returncode, 0, result.stderr)
        foreign = f.ws / 'sessions/two/data/report.md'; foreign.parent.mkdir(parents=True)
        foreign.write_text('foreign report\n')
        child = foreign.parent / 'child'; child.mkdir()
        (foreign.parent / body.name).write_text('foreign senior evidence\n')
        foreign_alias = private / 'foreign-alias'; foreign_alias.symlink_to(child, target_is_directory=True)
        own_alias = private / 'own-alias'; own_alias.symlink_to(private, target_is_directory=True)
        for operand in [str(foreign_alias / '..' / body.name), str(own_alias / body.name),
                        str(foreign_alias / '..' / foreign.name)]:
            with self.subTest(parent_alias=operand):
                self.assertEqual(f.hook(command.replace(str(body), operand), cwd=private).returncode, 2)
        unclaimed = private / 'unclaimed'; unclaimed.mkdir()
        unclaimed_body = unclaimed / 'report.md'; unclaimed_body.write_text('unclaimed\n')
        secret = private / '.env'; secret.write_text('PRIVATE_FIXTURE=value\n')
        hidden = private / '.secrets/report.md'; hidden.parent.mkdir(); hidden.write_text('private\n')
        key = private / 'key.pem'; key.write_text('fixture key\n')
        link = private / 'linked.md'; link.symlink_to(body)
        hardlink = private / 'hardlink.md'; os.link(body, hardlink)
        for operand in [foreign, secret, hidden, key, link, hardlink]:
            with self.subTest(operand=operand):
                self.assertEqual(f.hook(command.replace(str(body), str(operand)), cwd=private).returncode, 2)
        hardlink.unlink()
        # A legitimate report outside this Task's claimed scope also denies.
        fixture.write(gate / 'think-gate.json', {**data, 'scope_paths': [str(body)]})
        self.assertEqual(f.hook(command.replace(str(body), str(unclaimed_body)), cwd=private).returncode, 2)
        fixture.write(gate / 'think-gate.json', data)
        self.assertEqual(f.hook(command.replace('--body-file ' + str(body), '--body report'), cwd=private).returncode, 0)
        for name in ['report.txt', 'report.json', '.review-report']:
            report = private / name; report.write_text('Descriptive report evidence.\n')
            self.assertEqual(f.hook(command.replace(str(body), str(report)), cwd=private).returncode, 0)
        for name, content in [('credentials.json', b'{}'), ('invalid.txt', b'\xff'),
                              ('binary.txt', b'hello\0world'), ('oversize.txt', b'x' * (1024 * 1024 + 1))]:
            report = private / name; report.write_bytes(content)
            self.assertEqual(f.hook(command.replace(str(body), str(report)), cwd=private).returncode, 2)
        for denied in [command.replace('comment 803', 'comment 804'),
                       command.replace('example/target', 'foreign/repo'),
                       command.replace('issue comment', 'pr comment'),
                       command.replace(' --repo example/target', ''),
                       'GH_HOST=foreign.example ' + command,
                       'CCP_TASK_ID=foreign/repo#803 ' + command,
                       command + ' && touch ' + str(f.b / 'code'),
                       command + ' && gh issue close 803 --repo example/target',
                       'gh pr review 803 --repo example/target --approve --body report',
                       'gh api graphql -f query=mutation']:
            with self.subTest(command=denied):
                self.assertEqual(f.hook(denied, cwd=private).returncode, 2)
        url = command.replace('803 --repo example/target', 'https://github.com/example/target/issues/803')
        self.assertEqual(f.hook(url, cwd=private).returncode, 0)
        settings = json.loads((ROOT / 'hooks/settings-snippet.json').read_text())
        hooks = [ROOT / h['command'].split('/claude-configs-public/', 1)[1]
                 for group in settings['hooks']['PreToolUse'] if group.get('matcher') == 'Bash'
                 for h in group['hooks']]
        for hook in hooks:
            result = subprocess.run(['bash', str(hook)], input=json.dumps(fixture.craft_payload(
                tool_name='Bash', cwd=str(private), tool_input={'command': command})),
                env=f.env, text=True, capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0, (hook.name, result.stderr))
        fixture.write(gate / 'think-gate.json', {**data, 'sessionId': 'foreign'})
        self.assertEqual(f.hook(command, cwd=private).returncode, 2)
        fixture.write(gate / 'think-gate.json', data)
        duplicate = f.task('example/target#803', private, slug='duplicate', artifacts=False)
        self.assertEqual(f.hook(command, cwd=private).returncode, 2)
        shutil.rmtree(duplicate)
        shutil.rmtree(gate)
        self.assertEqual(f.hook(command, cwd=private).returncode, 2)

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

    def test_numeric_aliases_keep_task_and_repository_proof_in_full_chain(self):
        import task_keyed_gates as fixture
        f = fixture.Gates(); f.setUp(); self.addCleanup(f.tearDown)
        subprocess.run(['git', '-C', str(f.repo), 'remote', 'add', 'origin',
                        'https://github.com/example/target.git'], check=True)
        hooks = [ROOT / h['command'].split('/claude-configs-public/', 1)[1]
                 for g in json.loads((ROOT / 'hooks/settings-snippet.json').read_text())['hooks']['PreToolUse']
                 if g.get('matcher') == 'Bash' for h in g['hooks']]
        self.assertEqual(len(hooks), 16)
        def chain(command):
            payload = fixture.craft_payload(tool_name='Bash', cwd=str(f.repo), tool_input={'command': command})
            return {h.name: subprocess.run(['bash', str(h)], input=json.dumps(payload),
                    env=f.env, cwd=f.repo, text=True, capture_output=True, timeout=15).returncode for h in hooks}
        aliases = ['05', "'#5'", '+005', "'#+5'"]
        for selector in aliases:
            with self.subTest(no_task=selector):
                self.assertEqual(chain('gh issue comment ' + selector + ' --repo other/repo --body x')['universal-mutation-gate.sh'], 2)
        f.task('own-task', f.repo)
        for selector in aliases:
            with self.subTest(own_task=selector):
                result = chain('gh issue comment ' + selector + ' --repo example/target --body x')
                self.assertTrue(all(code == 0 for code in result.values()), result)
                self.assertEqual(chain('gh issue comment ' + selector + ' --repo other/repo --body x')['universal-mutation-gate.sh'], 2)
        for command in ['gh issue comment 05 --repo github.com/example/target --body x',
                        'gh issue comment https://github.com/example/target/issues/005 --body x']:
            result = chain(command); self.assertTrue(all(code == 0 for code in result.values()), result)

    def test_implicit_repo_defaults_and_rewrites_cannot_borrow_origin(self):
        import task_keyed_gates as fixture
        f = fixture.Gates(); f.setUp(); self.addCleanup(f.tearDown)
        def git(*args):
            return subprocess.run(['git', '-C', str(f.repo), *args], check=True, capture_output=True, text=True)
        git('remote', 'add', 'origin', 'https://github.com/example/target.git')
        f.task('own-task', f.repo)
        command = 'gh issue create --title report --body x'
        self.assertEqual(f.hook(command, cwd=f.repo).returncode, 0)
        # A transport-only rewrite with the same GitHub identity remains usable.
        same = 'url.ssh://git@github.com/example/target.git.insteadOf'
        git('config', same, 'https://github.com/example/target.git')
        self.assertEqual(f.hook(command, cwd=f.repo).returncode, 0)
        git('config', '--unset-all', same)
        foreign = 'url.https://github.com/other/repo.git.insteadOf'
        git('config', foreign, 'https://github.com/example/target.git')
        denied = f.hook(command, cwd=f.repo)
        self.assertEqual(denied.returncode, 2); self.assertIn('literal --repo', denied.stderr)
        self.assertEqual(f.hook(command + ' --repo example/target', cwd=f.repo).returncode, 0)
        self.assertEqual(f.hook(command + ' --repo other/repo', cwd=f.repo).returncode, 2)
        git('config', '--unset-all', foreign)
        git('remote', 'add', 'upstream', 'https://github.com/other/repo.git')
        self.assertEqual(f.hook(command, cwd=f.repo).returncode, 2)
        self.assertEqual(f.hook(command + ' --repo example/target', cwd=f.repo).returncode, 0)
        git('remote', 'remove', 'upstream')
        git('config', 'remote.origin.gh-resolved', 'base')
        self.assertEqual(f.hook(command, cwd=f.repo).returncode, 2)
        self.assertEqual(f.hook(command + ' --repo example/target', cwd=f.repo).returncode, 0)

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

    def git_scope_fixture(self):
        from unittest.mock import patch
        import task_keyed_gates as fixture
        # Isolate fixture construction before deliberately supplying hostile
        # Git variables to candidate inspection. Never redirect the caller repo.
        clean = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        clean.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
        context = patch.dict(os.environ, clean, clear=True)
        context.start(); self.addCleanup(context.stop)
        f = fixture.Gates(); f.setUp(); self.addCleanup(f.tearDown)
        foreign = f.ws / 'foreign'; foreign.mkdir()
        for repo, origin in [(f.repo, 'https://github.com/example/target.git'),
                             (foreign, 'https://github.com/other/foreign.git')]:
            if repo == foreign:
                subprocess.run(['git', 'init', '-q', str(repo)], env=f.env, check=True)
            subprocess.run(['git', '-C', str(repo), 'remote', 'add', 'origin', origin],
                           env=f.env, check=True)
        gate = f.task('metadata-own-scope', f.repo)
        redirected = dict(f.env, GIT_DIR=str(foreign / '.git'),
                          GIT_WORK_TREE=str(foreign), GIT_INDEX_FILE=str(foreign / '.git/index'))
        return fixture, f, foreign, gate, redirected

    def test_ambient_git_cannot_borrow_metadata_scope_in_full_chain(self):
        fixture, f, foreign, gate, redirected = self.git_scope_fixture()
        hooks = [ROOT / h['command'].split('/claude-configs-public/', 1)[1]
                 for group in json.loads((ROOT / 'hooks/settings-snippet.json').read_text())['hooks']['PreToolUse']
                 if group.get('matcher') == 'Bash' for h in group['hooks']]
        self.assertEqual(len(hooks), 16)
        def chain(command, environment):
            payload = fixture.craft_payload(tool_name='Bash', cwd=str(f.repo), tool_input={'command': command})
            return {hook.name: subprocess.run(['bash', str(hook)], input=json.dumps(payload),
                    env=environment, cwd=f.repo, capture_output=True, text=True, timeout=15)
                    for hook in hooks}
        own = 'gh issue comment 50 --repo example/target --body report'
        other = 'gh issue comment 50 --repo other/foreign --body report'
        implicit = 'gh issue comment 50 --body report'
        # The ambient environment really targets B; candidate posts never run.
        observed = subprocess.check_output(['git', '-C', str(f.repo), 'config', '--get',
                   'remote.origin.url'], env=redirected, text=True).strip()
        self.assertEqual(observed, 'https://github.com/other/foreign.git')
        for environment in [f.env, redirected]:
            with self.subTest(redirected=environment is redirected):
                own_results = chain(own, environment)
                self.assertTrue(all(p.returncode == 0 for p in own_results.values()),
                                {n: p.stderr for n, p in own_results.items()})
                self.assertEqual(chain(other, environment)['universal-mutation-gate.sh'].returncode, 2)
        self.assertTrue(all(p.returncode == 0 for p in chain(implicit, f.env).values()))
        denied = chain(implicit, redirected)['universal-mutation-gate.sh']
        self.assertEqual(denied.returncode, 2); self.assertIn('literal --repo', denied.stderr)

    def test_metadata_git_config_injection_keeps_explicit_continuation(self):
        fixture, f, foreign, gate, redirected = self.git_scope_fixture()
        for injected in [dict(GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='remote.origin.url',
                              GIT_CONFIG_VALUE_0='https://github.com/other/foreign.git'),
                         dict(GIT_CONFIG_PARAMETERS="'remote.origin.url=https://github.com/other/foreign.git'")]:
            environment = dict(f.env, **injected)
            observed = subprocess.check_output(['git', '-C', str(f.repo), 'config', '--get',
                       'remote.origin.url'], env=environment, text=True).strip()
            self.assertEqual(observed, 'https://github.com/other/foreign.git')
            for target, expected in [('example/target', 0), ('other/foreign', 2)]:
                self.assertEqual(f.hook('gh issue comment 50 --repo ' + target + ' --body report',
                                 cwd=f.repo, env=environment).returncode, expected)
            # --get sees the appended B value, but actual primary fetch/gh
            # remains local A (independently verified by safe gh issue-list).
            primary = subprocess.check_output(['git', '-C', str(f.repo), 'remote',
                      'get-url', 'origin'], env=environment, text=True).strip()
            self.assertEqual(primary, 'https://github.com/example/target.git')
            self.assertEqual(f.hook('gh issue comment 50 --body report', cwd=f.repo,
                                   env=environment).returncode, 0)

    def test_metadata_nested_owner_proof_uses_physical_repository(self):
        fixture, f, foreign, gate, redirected = self.git_scope_fixture()
        data = json.loads((gate / 'think-gate.json').read_text())
        data['repo_root'] = str(foreign)  # Contradicts its physical A scope.
        (gate / 'think-gate.json').write_text(json.dumps(data))
        for environment in [f.env, redirected]:
            for target in ['example/target', 'other/foreign']:
                result = f.hook('gh issue comment 50 --repo ' + target + ' --body report',
                                cwd=f.repo, env=environment)
                self.assertEqual(result.returncode, 2, result.stderr)

    def test_metadata_inspection_does_not_scrub_ordinary_git_targets_or_mutate_environment(self):
        from unittest.mock import patch
        fixture, f, foreign, gate, redirected = self.git_scope_fixture()
        with patch.dict(os.environ, redirected, clear=True):
            before = dict(os.environ)
            post = fixture.r.resolve_action(str(f.ws), fixture.craft_payload(tool_name='Bash',
                cwd=str(f.repo), tool_input={'command': 'gh issue comment 50 --repo example/target --body report'}))
            self.assertTrue(post.get('gate'), post)
            self.assertEqual(dict(os.environ), before)
            self.assertEqual(fixture.r._target_repo(str(f.repo)), str(foreign.resolve()))
            shape = fixture.r.action('git add note.txt', str(f.repo))
            self.assertTrue(shape['paths'], shape)
            self.assertTrue(all(str(foreign.resolve()) == p or str(foreign.resolve()) + os.sep in p
                                for p in shape['paths']), shape)
            ordinary = fixture.r.resolve_action(str(f.ws), fixture.craft_payload(tool_name='Bash',
                cwd=str(f.repo), tool_input={'command': 'git add note.txt'}))
            self.assertIsNone(ordinary.get('gate'), ordinary)
            self.assertEqual(dict(os.environ), before)

    def origin_scope_fixture(self):
        import shutil
        fixture, f, foreign, gate, redirected = self.git_scope_fixture()
        shutil.rmtree(f.ws / 'sessions/one/tasks')
        gate = f.task('example/target#31', f.a)
        return fixture, f, foreign, gate

    def test_nonrepository_origin_cannot_donate_scope_but_own_ticket_remains(self):
        fixture, f, foreign, gate = self.origin_scope_fixture()
        subprocess.run(['git', '-C', str(f.repo), 'remote', 'remove', 'origin'], env=f.env, check=True)
        config = f.ws / 'ambient.cfg'
        config.write_text('[remote "origin"]\n url = https://github.com/other/foreign.git\n')
        environments = [dict(f.env, GIT_CONFIG_GLOBAL=str(config)),
                        dict(f.env, GIT_CONFIG_SYSTEM=str(config))]
        environments[1].pop('GIT_CONFIG_NOSYSTEM', None)
        hooks = [ROOT / h['command'].split('/claude-configs-public/', 1)[1]
                 for group in json.loads((ROOT / 'hooks/settings-snippet.json').read_text())['hooks']['PreToolUse']
                 if group.get('matcher') == 'Bash' for h in group['hooks']]
        self.assertEqual(len(hooks), 16)
        own = 'gh issue comment 31 --repo example/target --body report'
        for command in [own, 'gh issue comment 50 --repo other/foreign --body report',
                        'gh issue comment 50 --repo example/target --body report']:
            payload = fixture.craft_payload(tool_name='Bash', cwd=str(f.repo), tool_input={'command': command})
            outcomes = {h.name: subprocess.run(['bash', str(h)], input=json.dumps(payload),
                        env=environments[0], cwd=f.repo, capture_output=True, text=True, timeout=15)
                        for h in hooks}
            if command == own:
                self.assertTrue(all(p.returncode == 0 for p in outcomes.values()),
                                {n: p.stderr for n, p in outcomes.items()})
            else:
                self.assertEqual(outcomes['universal-mutation-gate.sh'].returncode, 2)
        for environment in [f.env, *environments]:
            self.assertEqual(f.hook(own, cwd=f.repo, env=environment).returncode, 0)
            for command in ['gh issue comment 50 --repo other/foreign --body report',
                            'gh issue comment 50 --repo example/target --body report',
                            'gh issue create --repo example/target --title report --body report',
                            'gh pr comment 31 --repo example/target --body report']:
                self.assertEqual(f.hook(command, cwd=f.repo, env=environment).returncode, 2)
        # The canonical ticket is not an escape around physical ownership proof.
        data = json.loads((gate / 'think-gate.json').read_text());data['repo_root'] = str(foreign)
        (gate / 'think-gate.json').write_text(json.dumps(data))
        self.assertEqual(f.hook(own, cwd=f.repo, env=environments[0]).returncode, 2)

    def test_origin_authority_uses_first_repository_value_and_local_includes(self):
        fixture, f, foreign, gate, redirected = self.git_scope_fixture()
        def git(*args):
            return subprocess.check_output(['git', '-C', str(f.repo), *args], env=f.env, text=True).strip()
        git('config', '--add', 'remote.origin.url', 'https://github.com/other/foreign.git')
        self.assertEqual(git('config', '--get', 'remote.origin.url'), 'https://github.com/other/foreign.git')
        self.assertEqual(git('remote', 'get-url', 'origin'), 'https://github.com/example/target.git')
        for target, expected in [('example/target', 0), ('other/foreign', 2)]:
            self.assertEqual(f.hook('gh issue comment 50 --repo ' + target + ' --body report', cwd=f.repo).returncode, expected)
        self.assertEqual(f.hook('gh issue comment 50 --body report', cwd=f.repo).returncode, 0)
        git('config', '--unset-all', 'remote.origin.url')
        included = f.ws / 'owned-include.cfg'
        included.write_text('[remote "origin"]\n url = https://github.com/example/target.git\n')
        git('config', 'include.path', str(included))
        self.assertEqual(f.hook('gh issue comment 50 --repo example/target --body report', cwd=f.repo).returncode, 0)
        self.assertEqual(f.hook('gh issue comment 50 --repo other/foreign --body report', cwd=f.repo).returncode, 2)

    def test_origin_authority_supports_worktree_order_and_worktree_only_config(self):
        import shutil
        fixture, f, foreign, gate, redirected = self.git_scope_fixture()
        def git(*args):
            return subprocess.check_output(['git', '-C', str(f.repo), *args], env=f.env, text=True).strip()
        (f.repo / 'note').write_text('fixture')
        git('add', 'note')
        git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
            '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture')
        git('config', 'extensions.worktreeConfig', 'true')
        worktree = f.ws / 'sibling'
        git('-c', 'core.hooksPath=/dev/null', 'worktree', 'add', '-q', '-b', 'fixture-sibling', str(worktree))
        subprocess.run(['git', '-C', str(worktree), 'config', '--worktree', 'remote.origin.url',
                        'https://github.com/other/foreign.git'], env=f.env, check=True)
        shutil.rmtree(f.ws / 'sessions/one/tasks')
        gate = f.task('metadata-worktree-scope', worktree)
        # Declared main and actual worktree share the owned primary A URL,
        # despite the worktree's later B value. Nested comparison must agree.
        self.assertEqual(f.hook('gh issue comment 50 --repo example/target --body report', cwd=worktree).returncode, 0)
        self.assertEqual(f.hook('gh issue comment 50 --repo other/foreign --body report', cwd=worktree).returncode, 2)
        self.assertEqual(f.hook('gh issue comment 50 --body report', cwd=worktree).returncode, 0)
        git('config', '--unset-all', 'remote.origin.url')
        data = json.loads((gate / 'think-gate.json').read_text()); data['repo_root'] = str(worktree)
        (gate / 'think-gate.json').write_text(json.dumps(data))
        self.assertEqual(f.hook('gh issue comment 50 --repo other/foreign --body report', cwd=worktree).returncode, 0)
        self.assertEqual(f.hook('gh issue comment 50 --body report', cwd=worktree).returncode, 0)

    def test_global_trust_auth_and_actual_command_cwd_remain_usable(self):
        fixture, f, foreign, gate, redirected = self.git_scope_fixture()
        config = f.ws / 'trusted-global.cfg'
        config.write_text('[safe]\n directory = ' + str(f.repo) + '\n[credential]\n helper = cache\n[core]\n worktree = ' + str(foreign) + '\n')
        environment = dict(f.env, GIT_CONFIG_GLOBAL=str(config), GIT_TEST_ASSUME_DIFFERENT_OWNER='1')
        observed = subprocess.run(['git', '-C', str(f.repo), 'rev-parse', '--show-toplevel'],
                                 env=environment, text=True, capture_output=True)
        self.assertEqual(observed.returncode, 0, observed.stderr)
        self.assertEqual(observed.stdout.strip(), str(f.repo.resolve()))
        for command in ['gh issue comment 50 --repo example/target --body report',
                        'gh issue comment 50 --body report']:
            result = f.hook(command, cwd=f.repo, env=environment)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(f.hook('gh issue comment 50 --repo other/foreign --body report', cwd=f.repo, env=environment).returncode, 2)

    def test_first_owned_origin_is_exact_and_invalid_values_do_not_fall_through(self):
        fixture, f, foreign, gate, redirected = self.git_scope_fixture()
        for first in ['', ' https://github.com/example/target.git',
                      'https://github.com/example/target.git ',
                      'https://github.com/example/target.git\n',
                      'https://github.com/example/target.git\t']:
            subprocess.run(['git', '-C', str(f.repo), 'config', '--replace-all', 'remote.origin.url', first], env=f.env, check=True)
            subprocess.run(['git', '-C', str(f.repo), 'config', '--add', 'remote.origin.url',
                            'https://github.com/example/target.git'], env=f.env, check=True)
            self.assertEqual(f.hook('gh issue comment 50 --repo example/target --body report', cwd=f.repo).returncode, 2, repr(first))

    def test_local_origin_and_canonical_ticket_do_not_require_worktree_git_option(self):
        from unittest.mock import patch
        fixture, f, foreign, gate = self.origin_scope_fixture()
        actual_run = subprocess.run
        calls = []
        def older_git(args, *positional, **keywords):
            calls.append(args)
            if '--worktree' in args:
                return subprocess.CompletedProcess(args, 129, stdout='', stderr='unknown option: worktree')
            return actual_run(args, *positional, **keywords)
        with patch('subprocess.run', side_effect=older_git):
            observed = fixture.r._git_origin(str(f.repo), git_environment=fixture.r._metadata_git_environment())
            self.assertEqual(observed, 'https://github.com/example/target.git')
            self.assertFalse(any('--worktree' in args for args in calls))
            subprocess.run(['git', '-C', str(f.repo), 'remote', 'remove', 'origin'], env=f.env, check=True)
            self.assertEqual(fixture.r._git_origin(str(f.repo), git_environment=fixture.r._metadata_git_environment()), '')
            own = fixture.r.resolve_action(str(f.ws), fixture.craft_payload(tool_name='Bash',
                cwd=str(f.repo), tool_input={'command': 'gh issue comment 31 --repo example/target --body report'}))
            self.assertTrue(own.get('gate'), own)

    def test_preparation_reports_do_not_require_implementation_artifacts(self):
        import task_keyed_gates as fixture
        f = fixture.Gates(); f.setUp(); self.addCleanup(f.tearDown)
        subprocess.run(['git', '-C', str(f.repo), 'remote', 'add', 'origin',
                        'https://github.com/example/target.git'], check=True, timeout=15)
        gate = f.task('example/target#31', f.b, status='designing', artifacts=False)
        data = json.loads((gate / 'think-gate.json').read_text()); data['tier'] = 'C'
        commands = [
            "CCP_TASK_ID='example/target#31' gh issue comment 31 --repo example/target --body 'Investigation evidence; missing implementation checks.'",
            "gh issue create --repo example/target --title 'Followup' --body 'Missing evidence; pending review.'",
            "gh pr review 50 --repo example/target --comment --body 'Review complete; code work pending.'",
        ]
        for status in ['designing', 'reviewing', 'implementing']:
            fixture.write(gate / 'think-gate.json', {**data, 'status': status})
            for command in commands:
                with self.subTest(status=status, command=command):
                    self.assertEqual(f.hook(command).returncode, 0)
            mixed = commands[0] + ' && touch ' + str(f.b / 'code.txt')
            self.assertEqual(f.hook(mixed).returncode, 2)
            self.assertEqual(f.hook('touch ' + str(f.b / 'code.txt')).returncode, 2)
            self.assertEqual(f.hook(commands[0].replace('--repo example/target', '--repo other/repo')).returncode, 2)
        fixture.write(gate / 'think-gate.json', {**data, 'status': 'designing'})
        settings = json.loads((ROOT / 'hooks/settings-snippet.json').read_text())
        hooks = [ROOT / h['command'].split('/claude-configs-public/', 1)[1]
                 for group in settings['hooks']['PreToolUse'] if group.get('matcher') == 'Bash'
                 for h in group['hooks']]
        self.assertEqual(len(hooks), 16)
        for command in commands:
            payload = fixture.craft_payload(tool_name='Bash', cwd=str(f.repo), tool_input={'command': command})
            for hook in hooks:
                result = subprocess.run(['bash', str(hook)], input=json.dumps(payload), env=f.env,
                                        text=True, capture_output=True, cwd=f.repo, timeout=15)
                self.assertEqual(result.returncode, 0, (hook.name, command, result.stderr))

    def test_labeled_issue_creation_retains_task_and_repository_proof(self):
        import shutil
        import task_keyed_gates as fixture
        f = fixture.Gates(); f.setUp(); self.addCleanup(f.tearDown)
        subprocess.run(['git', '-C', str(f.repo), 'remote', 'add', 'origin',
                        'https://github.com/example/target.git'], check=True, timeout=15)
        f.task('example/target#31', f.b, status='designing', artifacts=False)
        settings = json.loads((ROOT / 'hooks/settings-snippet.json').read_text())
        hooks = [ROOT / h['command'].split('/claude-configs-public/', 1)[1]
                 for group in settings['hooks']['PreToolUse'] if group.get('matcher') == 'Bash'
                 for h in group['hooks']]
        self.assertEqual(len(hooks), 16)
        commands = ["gh issue create --repo example/target --title Report --body 'Missing evidence; review pending.' " + flags
                    for flags in ['--label tooling', '-l bug --label=tooling', "--label 'bug,tooling'"]]
        for command in commands:
            payload = fixture.craft_payload(tool_name='Bash', cwd=str(f.repo), tool_input={'command': command})
            for hook in hooks:
                result = subprocess.run(['bash', str(hook)], input=json.dumps(payload), env=f.env,
                                        text=True, capture_output=True, cwd=f.repo, timeout=15)
                self.assertEqual(result.returncode, 0, (hook.name, command, result.stderr))
            self.assertEqual(f.hook(command.replace('--repo example/target', '--repo foreign/repo')).returncode, 2)
            self.assertEqual(f.hook(command + ' && touch ' + str(f.b / 'code.txt')).returncode, 2)
        self.assertEqual(f.hook(commands[0].replace('--label tooling', "--label ''")).returncode, 2)
        shutil.rmtree(f.ws / 'sessions/one/tasks')
        for command in commands:
            self.assertEqual(f.hook(command).returncode, 2)

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
