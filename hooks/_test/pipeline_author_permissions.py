"""Exact repository/author permission attestation when gh /user is unavailable.

Runs the real comment writer and unchanged Tier C guard through the existing
#1164 fixture, with a fake gh boundary that returns installation-token /user
failure and an exact repository collaborator permission response.
"""
import ast
import json
import os
import sys
import time
import unittest
from types import SimpleNamespace
from unittest import mock

import gate_bypass_1164 as fixture

PERMISSION_GH = '''
if args[:2] == ['api', 'graphql']:
    body = 'Refs #1164' if __import__('os').environ.get('TEST_PERMISSION_PR') == 'own' else 'Refs #99999'
    print(json.dumps({{'data': {{'repository': {{'pullRequest': {{'number':1748, 'repository':{{'nameWithOwner':'o/r'}}, 'body':body, 'closingIssuesReferences':{{'nodes':[]}}}}}}}}}})); sys.exit(0)
if len(args) > 1 and '/collaborators/' in args[1]:
    with open(here / 'permission-calls.jsonl', 'a') as f:
        f.write(json.dumps(args) + '\\n')
    response = json.loads(__import__('os').environ.get('TEST_PERMISSION', 'null'))
    if response == 'timeout':
        __import__('time').sleep(30)
    if response == 'error' or args[1].lower() != 'repos/o/r/collaborators/maintainer/permission':
        sys.exit(1)
    if response == 'malformed':
        print('{{bad'); sys.exit(0)
    print(json.dumps(response)); sys.exit(0)
'''


def permission(value='admin', author='maintainer', **extra):
    return dict(permission=value, user={'login': author}, **extra)


class AuthorPermissions(unittest.TestCase):
    def run_chain(self, response, records=None, actor=None, extra_env=None, local_review=False):
        case = fixture.WriterGateChain(methodName='runTest')
        case.setUp()
        self.addCleanup(case.doCleanups)
        fake = fixture.FAKE_GH.replace("assert args[:2] == ['api', 'repos/o/r/issues/1164/comments'], args", PERMISSION_GH + "\nassert args[:2] == ['api', 'repos/o/r/issues/1164/comments'], args")
        env = dict(fixture.ENV, TEST_PERMISSION=json.dumps(response), **(extra_env or {}))
        comments = records or [fixture.comment('Ticket: o/r#1164\n' + fixture.H, 'maintainer', 'CONTRIBUTOR')]
        original_run = fixture.subprocess.run
        def run(command, **kwargs):
            if local_review and len(command) > 1 and command[1] == str(fixture.LIB / 'pipeline_state.py'):
                workspace = __import__('pathlib').Path(command[3])
                original_run(['git', 'init', '-q', str(workspace)], check=True)
                changed = workspace / 'changed.py'
                changed.write_text('before')
                original_run(['git', '-C', str(workspace), 'add', 'changed.py'], check=True)
                (__import__('pathlib').Path(kwargs['cwd']) / 'plans/self-review-local.md').write_text('o/r#1164\nPeer review complete.')
            return original_run(command, **kwargs)
        with mock.patch.object(fixture, 'FAKE_GH', fake), mock.patch.object(fixture, 'ENV', env), mock.patch.object(fixture.subprocess, 'run', side_effect=run):
            start = time.monotonic()
            flags, exits = case.chain('permission', comments, actor)
            elapsed = time.monotonic() - start
        task = __import__('pathlib').Path(case.tmp.name) / 'permission/workspace/sessions/fixture-session/tasks/t'
        self.selfreview_posted = json.loads((task / 'artifacts-posted-gate.json').read_text())['selfreview_posted']
        log = __import__('pathlib').Path(case.tmp.name) / 'permission/permission-calls.jsonl'
        calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        return flags, exits, calls, elapsed

    def assert_chain(self, response, allowed, **kwargs):
        flags, exits, calls, elapsed = self.run_chain(response, **kwargs)
        self.assertEqual(flags, [allowed] * 4)
        for code, output in exits:
            self.assertEqual(code, 0 if allowed else 2, output)
        return calls, elapsed

    def test_installation_user_failure_exact_admin_author_counts(self):
        calls, _ = self.assert_chain(permission(), True)
        self.assertEqual(calls[0][:2], ['api', 'repos/o/r/collaborators/maintainer/permission'])
        self.assertEqual(len(calls), 1)

    def test_separate_selfreview_author_gets_exact_permission_attestation(self):
        records = [fixture.comment('Ticket: o/r#1164\n' + fixture.H, 'trusted', 'MEMBER'),
                   fixture.comment('Ticket: o/r#1164\nPeer review; lead review; syntax check.', 'maintainer', 'CONTRIBUTOR')]
        calls, _ = self.assert_chain(permission(), True, records=records, local_review=True)
        self.assertTrue(self.selfreview_posted)
        self.assertEqual(len(calls), 1)

    def test_write_and_maintain_count_without_role_name_upgrade(self):
        for value in ['write', 'maintain']:
            with self.subTest(value):
                self.assert_chain(permission(value), True)

    def test_read_triage_none_unknown_and_role_name_only_do_not_count(self):
        for value in ['read', 'triage', 'none', 'unknown', '', None]:
            with self.subTest(value):
                self.assert_chain(permission(value, role_name='admin'), False)

    def test_wrong_author_malformed_or_unreachable_response_does_not_count(self):
        for response in [permission(author='someone-else'), {'permission': 'admin'}, None, 'malformed', 'error']:
            with self.subTest(response):
                self.assert_chain(response, False)

    def test_another_repository_artifact_still_does_not_count_or_spend_lookup(self):
        calls, _ = self.assert_chain(permission(), False, records=[fixture.comment('Ticket: other/repo#1164\n' + fixture.H, 'maintainer', 'CONTRIBUTOR')])
        self.assertEqual(calls, [])

    def test_foreign_host_and_path_shaped_author_never_get_permission_lookup(self):
        calls, _ = self.assert_chain(permission(), False, extra_env={'GH_HOST': 'github.example.com'})
        self.assertEqual(calls, [])
        calls, _ = self.assert_chain(permission(), False, records=[fixture.comment('Ticket: o/r#1164\n' + fixture.H, '../maintainer', 'CONTRIBUTOR')])
        self.assertEqual(calls, [])

    def test_quotes_examples_and_non_artifacts_do_not_spend_lookup(self):
        selfreview = 'Peer review; lead review; syntax check.'
        for body in ['> ' + fixture.H.replace('\n', '\n> '), '```\n' + fixture.H + '\n```', 'ordinary discussion only',
                     '> ' + selfreview, '```\n' + selfreview + '\n```', 'peer review; lead review only']:
            with self.subTest(body):
                calls, _ = self.assert_chain(permission(), False, records=[fixture.comment(body, 'maintainer', 'CONTRIBUTOR')])
                self.assertEqual(calls, [])

    def test_casefolded_author_and_cached_repeat(self):
        comments = [fixture.comment('Ticket: o/r#1164\n' + fixture.H, author, 'CONTRIBUTOR') for author in ['maintainer', 'Maintainer']]
        calls, _ = self.assert_chain(permission(author='MAINTAINER'), True, records=comments)
        self.assertEqual(len(calls), 1)

    def test_attested_author_still_requires_own_pr_ticket_relationship(self):
        body = ('Ticket: o/r#1164\n' + fixture.H).replace('## Investigation', '## Investigation for PR #1748')
        records = [fixture.comment(body, 'maintainer', 'CONTRIBUTOR')]
        self.assert_chain(permission(), True, records=records, extra_env={'TEST_PERMISSION_PR': 'own'})
        self.assert_chain(permission(), False, records=records, extra_env={'TEST_PERMISSION_PR': 'foreign'})

    def test_exhausted_fallback_cap_does_not_skip_trusted_artifact(self):
        records = [fixture.comment('Ticket: o/r#1164\n' + fixture.H, 'trusted', 'MEMBER')]
        records += [fixture.comment('Ticket: o/r#1164\n' + fixture.H, name, 'CONTRIBUTOR') for name in ['one', 'two', 'three', 'four', 'five']]
        calls, _ = self.assert_chain('error', True, records=records)
        self.assertEqual(len(calls), 4)

    def test_fast_paths_do_not_need_permission_api(self):
        for actor, association in [('maintainer', 'CONTRIBUTOR'), (None, 'OWNER'), (None, 'MEMBER'), (None, 'COLLABORATOR')]:
            with self.subTest(association):
                calls, _ = self.assert_chain('error', True, actor=actor, records=[fixture.comment('Ticket: o/r#1164\n' + fixture.H, 'maintainer', association)])
                self.assertEqual(calls, [])

    def test_timeout_is_bounded_and_does_not_hide_later_trusted_comment(self):
        comments = [fixture.comment('Ticket: o/r#1164\n' + fixture.H, 'trusted', 'MEMBER'), fixture.comment('Ticket: o/r#1164\n' + fixture.H, 'maintainer', 'CONTRIBUTOR')]
        calls, elapsed = self.assert_chain('timeout', True, records=comments)
        self.assertEqual(len(calls), 1)
        self.assertLess(elapsed, 4.0)


class PermissionReadBounds(unittest.TestCase):
    def make_reader(self, now=0.0):
        source = ast.parse((fixture.LIB / 'pipeline_state.py').read_text())
        names = {'AUTHOR_PERMISSION_LOOKUPS', 'AUTHOR_PERMISSION_READ_SECONDS', 'AUTHOR_PERMISSION_BUDGET_SECONDS',
                 'AUTHOR_PERMISSION_REPLY_BYTES', 'GITHUB_LOGIN', 'REPO_NAME', 'OWN_PR_WRITER_CEILING_SECONDS'}
        nodes = [node for node in source.body if (isinstance(node, ast.ClassDef) and node.name == 'RepositoryAuthorPermissions')
                 or (isinstance(node, ast.Assign) and any(isinstance(n, ast.Name) and n.id in names for n in node.targets))]
        clock = SimpleNamespace(now=now)
        namespace = {'json': json, 'os': os, 're': __import__('re'), 'time': SimpleNamespace(monotonic=lambda: clock.now), 'WRITER_STARTED': 0.0}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), '<actual permission reader>', 'exec'), namespace)
        return namespace['RepositoryAuthorPermissions'], clock

    def test_four_unique_reads_cap_and_negative_cache(self):
        Reader, _ = self.make_reader()
        reader = Reader('o/r')
        with mock.patch('subprocess.run', return_value=SimpleNamespace(returncode=1, stdout='')) as run:
            for author in ['one', 'two', 'three', 'four', 'five', 'ONE']:
                self.assertFalse(reader(author))
        self.assertEqual(run.call_count, 4)
        self.assertIn('budget exhausted', reader.reasons['five'])

    def test_aggregate_timeout_budget_and_diagnostic(self):
        Reader, clock = self.make_reader()
        reader = Reader('o/r')
        def timeout(command, **kwargs):
            clock.now += kwargs['timeout']
            raise fixture.subprocess.TimeoutExpired(command, kwargs['timeout'])
        with mock.patch('subprocess.run', side_effect=timeout) as run:
            for author in ['one', 'two', 'three']:
                self.assertFalse(reader(author))
        self.assertEqual(run.call_count, 2)
        self.assertEqual(clock.now, 2.0)
        self.assertEqual(reader.reasons['one'], 'permission lookup timed out')
        self.assertEqual(reader.reasons['three'], 'permission lookup budget exhausted')

    def test_writer_ceiling_shared_with_existing_own_pr_reads(self):
        Reader, clock = self.make_reader(6.8)
        reader = Reader('o/r')
        def timeout(command, **kwargs):
            self.assertAlmostEqual(kwargs['timeout'], 0.2)
            clock.now += kwargs['timeout']
            raise fixture.subprocess.TimeoutExpired(command, kwargs['timeout'])
        with mock.patch('subprocess.run', side_effect=timeout) as run:
            self.assertFalse(reader('one'))
            self.assertFalse(reader('two'))
        self.assertEqual(run.call_count, 1)

    def test_exact_repository_path_not_other_repository_permission(self):
        Reader, _ = self.make_reader()
        reader = Reader('o/r')
        def scoped_response(command, **kwargs):
            # The author is admin elsewhere. Only the current ticket repository
            # may supply the attestation, so another repository cannot grant it.
            response = permission() if command[2] == 'repos/other/repo/collaborators/maintainer/permission' else permission('read')
            return SimpleNamespace(returncode=0, stdout=json.dumps(response))
        with mock.patch('subprocess.run', side_effect=scoped_response) as run:
            self.assertFalse(reader('maintainer'))
        self.assertEqual(run.call_args.args[0][2], 'repos/o/r/collaborators/maintainer/permission')

    def test_invalid_repository_and_oversized_response_are_not_trusted(self):
        Reader, _ = self.make_reader()
        with mock.patch('subprocess.run') as run:
            self.assertFalse(Reader('o/r/../../other')('maintainer'))
            run.assert_not_called()
        with mock.patch('subprocess.run', return_value=SimpleNamespace(returncode=0, stdout=' ' * 65537 + json.dumps(permission()))):
            self.assertFalse(Reader('o/r')('maintainer'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
