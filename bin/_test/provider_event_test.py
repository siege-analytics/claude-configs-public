#!/usr/bin/env python3
"""Synthetic registered events over real Git consumers and one pinned parent.

Local Git transport and host facts are fixtures, not live provider authorization.
"""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('provider_fixtures', ROOT / 'bin/_test/protected_policy_test.py')
f = importlib.util.module_from_spec(spec); spec.loader.exec_module(f)

class ProviderEventTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = tempfile.TemporaryDirectory(prefix='provider-event-python-')
        (Path(cls.runtime.name) / 'python3').symlink_to(sys.executable)
        cls.old_path = os.environ['PATH']
        os.environ['PATH'] = cls.runtime.name + os.pathsep + cls.old_path
        cls.fixture = f.ProtectedPolicyPilotTest
        cls.fixture.setUpClass()
        cls.case = cls.fixture()

    @classmethod
    def tearDownClass(cls):
        cls.fixture.tearDownClass()
        os.environ['PATH'] = cls.old_path
        cls.runtime.cleanup()

    def consumer(self, project='strict-release'):
        repo, _ = self.case.make_repo(project, configure_hook=False)
        workflow = repo / '.github/workflows/pr-base-guard.yml'
        template = (ROOT / 'examples/provider/shared-parent-workflow.yml').read_text()
        workflow.write_text(template.replace('PARENT_SOURCE_REVISION', self.fixture.trusted_revision))
        f.git(repo, 'add', str(workflow))
        f.git(repo, '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'install reviewed host fixture #1002')
        base = f.git(repo, 'rev-parse', 'HEAD').stdout.strip()
        remote = Path(tempfile.mkdtemp(prefix='consumer-canonical-', dir=self.fixture.temp))
        f.run('git', 'init', '--bare', '-q', '--initial-branch=main', str(remote), cwd=self.fixture.temp)
        f.git(repo, 'push', '-q', '--no-verify', str(remote), base + ':refs/heads/main', base + ':refs/heads/develop')
        canonical = 'synthetic-org/' + project
        f.git(repo, 'config', 'url.' + remote.as_uri() + '.insteadOf', 'https://github.example.invalid/' + canonical + '.git')
        f.git(repo, 'checkout', '-q', '-b', 'feature/pilot')
        self.case.change(repo, 'operation', self.case.message('consumer operation'), no_verify=True)
        event = repo.parent / (repo.name + '-event.json')
        value = dict(repo=repo, base=base, remote=remote, canonical=canonical, event=event,
                     target='main' if project == 'synthetic-trunk' else 'develop')
        self.publish_event(value)
        workflow_root = Path(tempfile.mkdtemp(prefix='canonical-workflow-', dir=self.fixture.temp))
        f.run('git', 'clone', '-q', '--no-hardlinks', str(remote), str(workflow_root), cwd=self.fixture.temp)
        f.git(workflow_root, 'remote', 'set-url', 'origin', 'https://github.example.invalid/' + canonical + '.git')
        value['workflow_root'] = workflow_root
        return value

    def publish_event(self, value):
        repo = value['repo']; head = f.git(repo, 'rev-parse', 'HEAD').stdout.strip()
        # Publish only the disposable candidate branch, leaving protected refs
        # unchanged. The adapter evaluates its exact Git facts without executing it.
        f.git(repo, 'push', '-q', '--no-verify', '--force', str(value['remote']), 'HEAD:refs/heads/feature/pilot')
        # Simulate the host's authenticated fetch-depth:0 checkout. The adapter
        # then reads these objects without requiring retained fetch credentials.
        f.git(repo, 'fetch', '--quiet', 'origin', '+refs/heads/*:refs/remotes/origin/*')
        identity = {'full_name': value['canonical']}
        value['event'].write_text(json.dumps({'repository': identity, 'pull_request': {
            'base': {'sha': value['base'], 'ref': value['target'], 'repo': identity},
            'head': {'sha': head, 'ref': 'feature/pilot', 'repo': identity},
        }}))

    def probe(self, value, *, environment=None, parent=None, trusted=None, extra=()):
        identity = value['canonical']
        env = dict(os.environ, GITHUB_EVENT_NAME='pull_request_target', GITHUB_EVENT_PATH=str(value['event']),
                   GITHUB_REPOSITORY=identity, GITHUB_SERVER_URL='https://github.example.invalid',
                   GITHUB_WORKFLOW_REF=identity + '/.github/workflows/pr-base-guard.yml@refs/heads/main',
                   GITHUB_WORKFLOW_SHA=value['base'])
        for key in ['BASE_BRANCH', 'HEAD_BRANCH', 'HEAD_REPO', 'CANONICAL_REPO']:
            env.pop(key, None)
        env.update(environment or {})
        trusted = trusted or self.fixture.trusted
        result = f.run(sys.executable, str(trusted / f.SCRIPT), '--host-event',
                       '--trusted-root', str(trusted),
                       '--trusted-revision', parent or self.fixture.trusted_revision,
                       '--trusted-repository', 'github.com/siege-analytics/claude-configs-public',
                       '--executed-workflow-root', str(value['workflow_root']),
                       '--candidate-repo', str(value['repo']), '--installed-pilot-receipt', '.pilot/composition.json',
                       *extra, cwd=value['repo'], check=False, env=env)
        self.assertTrue(result.stdout, result.stderr)
        return result.returncode, json.loads(result.stdout)

    def test_both_profiles_use_one_parent_and_distinct_consumer_workflow(self):
        revisions = []
        for project in ['strict-release', 'synthetic-trunk']:
            value = self.consumer(project)
            code, result = self.probe(value)
            direct_code, direct = self.case.evaluate(value['repo'], value['base'], value['target'])
            self.assertEqual((code, result['state']), (direct_code, direct['state']))
            self.assertEqual((code, result['state']), (0, 'eligible'), result)
            self.assertEqual(result['resident_workflow'], direct['resident_workflow'])
            revisions.append(result['trusted']['revision'])
            self.assertNotEqual(value['base'], self.fixture.trusted_revision)
            self.assertEqual(result['trusted']['executed_workflow']['revision'], value['base'])
            self.assertEqual(result['host_event_binding']['mode'], 'shared-parent')
            self.assertEqual(result['host_event_binding']['consumer_base'], value['base'])
            self.assertEqual(result['authorization'], 'protected-host-check-required')
            value['target'] = 'develop' if project == 'synthetic-trunk' else 'main'
            self.publish_event(value)
            code, rejected = self.probe(value)
            self.assertEqual((code, rejected['state']), (1, 'denied'), rejected)
        self.assertEqual(revisions, [self.fixture.trusted_revision] * 2)

    def test_missing_ticket_denies_then_new_exact_head_repairs_for_both(self):
        for project in ['strict-release', 'synthetic-trunk']:
            value = self.consumer(project)
            f.git(value['repo'], '-c', 'core.hooksPath=/dev/null', 'commit', '--amend', '-qm', 'missing ticket')
            self.publish_event(value)
            code, result = self.probe(value)
            self.assertEqual((code, result['state']), (1, 'denied'), result)
            f.git(value['repo'], '-c', 'core.hooksPath=/dev/null', 'commit', '--amend', '-qm', self.case.message('repair'))
            self.publish_event(value)
            code, result = self.probe(value)
            self.assertEqual((code, result['state']), (0, 'eligible'), result)
            main = f.run('git', '--git-dir=' + str(value['remote']), 'rev-parse', 'refs/heads/main', cwd=value['repo']).stdout.strip()
            self.assertEqual(main, value['base'])

    def test_parent_pin_event_and_workflow_mismatches_fail_closed(self):
        value = self.consumer()
        code, result = self.probe(value, parent=value['base'])
        self.assertEqual((code, result['state']), (2, 'error'), result)
        for changes in [
            {'GITHUB_WORKFLOW_SHA': self.fixture.trusted_revision},
            {'GITHUB_WORKFLOW_REF': value['canonical'] + '/.github/workflows/pr-base-guard.yml@refs/heads/develop'},
            {'GITHUB_REPOSITORY': 'foreign/repository'}, {'GITHUB_EVENT_PATH': str(value['event']) + '.missing'},
            {'GITHUB_EVENT_NAME': 'pull_request'}, {'HEAD_BRANCH': 'different'},
        ]:
            code, result = self.probe(value, environment=changes)
            self.assertEqual((code, result['state']), (2, 'error'), result)
        code, result = self.probe(value, extra=('--head', '0' * 40))
        self.assertEqual((code, result['state']), (2, 'error'), result)
        f.git(value['workflow_root'], 'update-ref', '-d', 'refs/remotes/origin/main')
        self.assertEqual(self.probe(value)[0], 2)

    def test_stale_candidate_fork_and_missing_install_fail_closed(self):
        value = self.consumer()
        data = json.loads(value['event'].read_text()); data['pull_request']['head']['sha'] = value['base']
        value['event'].write_text(json.dumps(data))
        self.assertEqual(self.probe(value)[0], 2)
        self.publish_event(value)
        data = json.loads(value['event'].read_text()); data['pull_request']['head']['repo']['full_name'] = 'foreign/fork'
        value['event'].write_text(json.dumps(data))
        code, result = self.probe(value)
        self.assertEqual((code, result['state']), (1, 'denied'), result)
        (value['repo'] / '.pilot/composition.json').unlink()
        f.git(value['repo'], 'add', '-u')
        f.git(value['repo'], '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', self.case.message('missing install'))
        self.publish_event(value)
        code, result = self.probe(value)
        self.assertEqual((code, result['state']), (1, 'denied'), result)

    def test_wrong_parent_repository_and_candidate_workflow_store_reject(self):
        value = self.consumer()
        for extra in [('--trusted-repository', 'github.example.invalid/foreign/parent'),
                      ('--executed-workflow-root', str(value['repo']))]:
            code, result = self.probe(value, extra=extra)
            self.assertEqual((code, result['state']), (2, 'error'), result)
        f.git(value['workflow_root'], 'remote', 'set-url', 'origin', 'https://github.example.invalid/foreign/workflow.git')
        self.assertEqual(self.probe(value)[0], 2)

    def test_candidate_validator_and_workflow_edits_are_data_only(self):
        value = self.consumer(); repo = value['repo']
        code, before = self.probe(value); self.assertEqual(code, 0)
        (repo / f.SCRIPT).write_text('raise SystemExit("CANDIDATE CODE MUST NOT EXECUTE")\n')
        (repo / '.github/workflows/pr-base-guard.yml').write_text('jobs: {bypass: {steps: [{run: "true"}]}}\n')
        f.git(repo, 'add', str(f.SCRIPT), '.github/workflows/pr-base-guard.yml')
        f.git(repo, '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', self.case.message('candidate proposal'))
        self.publish_event(value)
        code, result = self.probe(value)
        self.assertEqual((code, result['state']), (0, 'eligible'), result)
        self.assertEqual(result['trusted']['executed_workflow'], before['trusted']['executed_workflow'])
        self.assertEqual(result['trusted']['validator'], before['trusted']['validator'])
        self.assertIn(str(f.SCRIPT), result['candidate']['policy_sensitive_paths'])

    def test_invalid_interior_is_not_hidden_by_valid_head(self):
        for project in ['strict-release', 'synthetic-trunk']:
            value = self.consumer(project)
            bad = self.case.change(value['repo'], 'bad-interior', self.case.message('bad', ticket=False), no_verify=True)
            self.case.change(value['repo'], 'valid-head', self.case.message('valid'), no_verify=True)
            self.publish_event(value)
            code, result = self.probe(value)
            self.assertEqual((code, result['state']), (1, 'denied'), result)
            self.assertIn(bad, result['diagnostic'])

    def test_shallow_parent_recovers_only_from_its_pinned_repository(self):
        value = self.consumer()
        for available in [True, False]:
            parent = Path(tempfile.mkdtemp(prefix='shallow-parent-', dir=self.fixture.temp))
            f.run('git', 'clone', '-q', '--depth', '1', self.fixture.trusted.as_uri(), str(parent), cwd=self.fixture.temp)
            self.assertEqual(f.git(parent, 'rev-parse', '--is-shallow-repository').stdout.strip(), 'true')
            canonical = 'https://github.com/siege-analytics/claude-configs-public.git'
            f.git(parent, 'remote', 'set-url', 'origin', canonical)
            transport = self.fixture.trusted if available else parent / 'absent-origin'
            f.git(parent, 'config', 'url.' + transport.as_uri() + '.insteadOf', canonical)
            code, result = self.probe(value, trusted=parent)
            if available:
                self.assertEqual((code, result['state']), (0, 'eligible'), result)
                self.assertEqual(f.git(parent, 'rev-parse', '--is-shallow-repository').stdout.strip(), 'false')
            else:
                self.assertEqual((code, result['state']), (2, 'error'), result)

    def test_candidate_policy_cannot_select_a_new_parent_or_authorize_wrong_branch(self):
        value = self.consumer(); repo = value['repo']
        path = repo / 'catalog/effective-policy.json'; data = json.loads(path.read_text())
        data['organization_profiles'][0]['values'] = {'branch-policy': {'integration_branch': 'main'}}
        path.write_text(json.dumps(data))
        f.git(repo, 'add', str(path)); f.git(repo, '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', self.case.message('policy proposal'))
        value['target'] = 'main'; self.publish_event(value)
        code, result = self.probe(value)
        self.assertEqual((code, result['state']), (1, 'denied'), result)
        value['target'] = 'develop'; self.publish_event(value)
        code, result = self.probe(value)
        self.assertEqual((code, result['state']), (0, 'eligible'), result)
        self.assertEqual(result['candidate_policy']['authorization_effect'], 'none')
        self.assertEqual(result['trusted']['revision'], self.fixture.trusted_revision)

if __name__ == '__main__':
    unittest.main(verbosity=2)
