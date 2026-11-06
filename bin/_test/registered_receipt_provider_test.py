#!/usr/bin/env python3
"""Two actual hook roots share a registered provider; no live host writes."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

import craft_hook_router_test as router_fixture

ROOT = Path(__file__).resolve().parents[2]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


class ReceiptProviders(unittest.TestCase):
    def setUp(self):
        self.host = router_fixture.Router()
        self.host.setUp()
        self.addCleanup(self.host.doCleanups)
        self.host.activate()
        self.workspace = self.host.workspace
        self.project = self.host.fixture.base / 'project'
        self.project.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.project)], check=True, timeout=10)
        shutil.copytree(ROOT / 'hooks', self.project / 'hooks')
        (self.project / 'bin').mkdir()
        shutil.copy2(ROOT / 'bin/review-risk.py', self.project / 'bin/review-risk.py')
        (self.project / 'catalog').mkdir()
        shutil.copy2(ROOT / 'catalog/review-risk-policy.json', self.project / 'catalog/review-risk-policy.json')
        (self.project / 'source.py').write_text('VALUE = 7\n')
        # Disposable source revision for the real receipt producer, not a claim
        # about publication or operator Git registration.
        subprocess.run(['git', '-C', str(self.project), 'add', 'source.py'], check=True, timeout=10)
        subprocess.run(['git', '-C', str(self.project), '-c', 'user.name=Fixture',
                        '-c', 'user.email=fixture@example.invalid', '-c', 'commit.gpgsign=false',
                        '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'fixture source'], check=True, timeout=10)
        self.task = self.host.session / 'tasks/receipt'
        identity = dict(ticket='example/project#1180', sessionId='one', repo_root=str(self.project),
                        scope_paths=[str(self.project)], status='implementing', tier='C')
        write(self.task / 'think-gate.json', identity)
        for name, fields in [('investigate', {'findings':[{'claim':'fixture source checked'}]}),
                             ('junior-senior', {'junior_found':True,'senior_found':True}),
                             ('artifacts-posted', {'investigate_posted':True,'premortem_posted':True})]:
            write(self.task / (name + '-gate.json'), {**identity, **fields})
        plan = self.project / 'plans/pre-mortem-fixture.md'; plan.parent.mkdir()
        plan.write_text('Ticket: example/project#1180\nSeverity: 50\nImplementation may proceed: YES\n')
        self.provider = self.workspace / 'hooks/lib/test-evidence.py'
        self.hooks = [self.workspace / 'hooks/bash/universal-mutation-gate.sh',
                      self.project / 'hooks/bash/universal-mutation-gate.sh']
        self.env = {k:v for k,v in self.host.env.items() if not k.startswith(('CCP_', 'CLAUDE_', 'HUB_'))}
        self.env.update(CRAFT_AGENT_WORKSPACE=str(self.workspace), PYTHONDONTWRITEBYTECODE='1')

    def command(self, provider=None, output=None):
        return shlex.join(['python3', str(provider or self.provider), 'record', '--repo', str(self.project),
                           '--source', 'source.py', '--think-gate', str(self.task / 'think-gate.json'),
                           '--output', str(output or self.task / 'test-gate.json'), '--framework', 'unittest',
                           '--', 'python3', '-c', "import source; assert source.VALUE == 7"])

    def both(self, command=None, code=0, payload_change=None):
        for hook in self.hooks:
            with self.subTest(hook=hook):
                value = json.loads(self.host.payload(command=command or self.command()))
                value['cwd'] = str(self.project)
                if payload_change:
                    value.update(payload_change)
                result = subprocess.run(['bash', str(hook)], input=json.dumps(value), cwd=self.project,
                                        env=self.env, text=True, capture_output=True, timeout=25)
                self.assertEqual(result.returncode, code, result.stdout + result.stderr)

    def test_one_registered_provider_passes_both_hook_locations_and_records_real_tests(self):
        self.both()
        subprocess.run(shlex.split(self.command()), cwd=self.project, env=self.env, check=True, timeout=20)
        receipt = json.loads((self.task / 'test-gate.json').read_text())
        self.assertEqual(receipt['exit_code'], 0)
        self.assertEqual(receipt['evidence'][0]['source'], 'source.py')
        registration = json.loads(self.host.receipt_path.read_text())
        self.assertEqual(registration['test_evidence_sha256'], hashlib.sha256(self.provider.read_bytes()).hexdigest())

    def test_clone_local_unrelated_and_symlink_provider_do_not_get_workspace_authority(self):
        self.both(self.command(self.project / 'hooks/lib/test-evidence.py'), code=2)
        foreign = self.host.fixture.base / 'foreign/test-evidence.py'
        foreign.parent.mkdir(); foreign.write_bytes(self.provider.read_bytes())
        self.both(self.command(foreign), code=2)
        alias = foreign.parent / 'alias/test-evidence.py'; alias.parent.mkdir(); alias.symlink_to(self.provider)
        self.both(self.command(alias), code=2)

    def test_changed_hardlinked_and_missing_pin_fail_closed(self):
        self.provider.write_bytes(self.provider.read_bytes() + b'\n# changed\n')
        self.both(code=2)
        shutil.copy2(ROOT / 'hooks/lib/test-evidence.py', self.provider)
        alias = self.host.fixture.base / 'hardlink'; os.link(self.provider, alias)
        self.both(code=2)
        alias.unlink()
        record = json.loads(self.host.receipt_path.read_text()); record.pop('test_evidence_sha256', None)
        write(self.host.receipt_path, record)
        self.both(code=2)

    def test_forged_session_and_foreign_or_nonadjacent_output_fail(self):
        self.both(code=2, payload_change={'session_id':'ffe0010a-0000-4000-8000-000000000099'})
        self.both(self.command(output=self.host.session / 'data/test-gate.json'), code=2)
        self.both(self.command(output=self.workspace / 'sessions/other/tasks/x/test-gate.json'), code=2)

    def test_broken_registration_never_falls_back_to_project_provider(self):
        self.host.receipt_path.unlink()
        self.both(self.command(self.project / 'hooks/lib/test-evidence.py'), code=2)

    def test_real_v3584_receipt_upgrades_without_requiring_its_future_pin(self):
        revision = 'f004df3c66cf6374548cfc49d0e49c375aa4376c'
        registered = json.loads(self.host.receipt_path.read_text())
        fields = [('session_anchor_sha256','hooks/lib/session_anchor.py'),
                  ('read_classifier_sha256','hooks/lib/read-only-command.py'),
                  ('task_resolver_sha256','hooks/lib/resolve-think-gate.py'),
                  ('hook_payload_sha256','hooks/lib/hook_payload.py'),
                  ('task_actions_sha256','hooks/lib/task_actions.py')]
        for key, relative in fields:
            old = subprocess.check_output(['git','-C',str(ROOT),'show',revision + ':' + relative], timeout=10)
            (self.workspace / relative).write_bytes(old)
            registered[key] = hashlib.sha256(old).hexdigest()
        old_router = subprocess.check_output(['git','-C',str(ROOT),'show',revision + ':hooks/lib/craft-settings-router.py'], timeout=10)
        self.host.target.write_bytes(old_router)
        registered.update(source_revision=revision, router_sha256=hashlib.sha256(old_router).hexdigest())
        registered.pop('test_evidence_sha256')
        write(self.host.receipt_path, registered)
        # Existing routing validation accepts the actual legacy generation.
        receipt, _ = router_fixture.r.registration(self.workspace, router_path_override=self.host.target)
        self.assertNotIn('test_evidence_sha256', receipt)
        with patch.dict(os.environ, self.env, clear=True):
            with self.assertRaisesRegex(router_fixture.r.RoutingError, 'not pinned'):
                router_fixture.r.registered_test_provider(self.env, json.loads(self.host.payload()))
        # Normal source delivery precedes the normal installer; no receipt is
        # hand-upgraded and no old-generation check demands the future pin.
        for _key, relative in fields:
            shutil.copy2(ROOT / relative, self.workspace / relative)
        before = json.loads(self.host.fixture.user_settings.read_text())
        self.host.activate()
        after = json.loads(self.host.fixture.user_settings.read_text())
        self.assertEqual(before['permissions'], after['permissions'])
        self.assertEqual(before['operatorSecret'], after['operatorSecret'])
        self.assertTrue(any(self.host.foreign in group['hooks'] for group in after['hooks']['PreToolUse']))
        self.both()

    def test_unenrolled_direct_craft_stack_keeps_its_exact_local_provider(self):
        self.host.receipt_path.unlink()
        self.host.target.unlink()
        # This policy file exists on legitimate direct-hook/headless installs;
        # it is not evidence of external router enrollment.
        self.assertTrue(self.host.policy_path.exists())
        self.hooks = [self.workspace / 'hooks/bash/universal-mutation-gate.sh']
        self.both()

    def test_unregistered_native_classifier_keeps_local_generation(self):
        import importlib.util
        from unittest.mock import patch
        sys.path.insert(0, str(ROOT / 'hooks/lib'))
        spec = importlib.util.spec_from_file_location('native_receipt_actions', ROOT / 'hooks/lib/task_actions.py')
        actions = importlib.util.module_from_spec(spec); spec.loader.exec_module(actions)
        env = {key:value for key,value in os.environ.items() if not key.startswith(('CRAFT_', 'CLAUDE_', 'CCP_'))}
        for native_directory in (None, str(self.host.fixture.base / 'native-history' / 'one')):
            native_env = dict(env)
            if native_directory:
                Path(native_directory).mkdir(parents=True)
                native_env['CLAUDE_SESSION_DIR'] = native_directory
            with self.subTest(native_directory=native_directory), patch.dict(os.environ, native_env, clear=True):
                shape = actions.action(self.command(ROOT / 'hooks/lib/test-evidence.py'), str(self.project))
                self.assertFalse(shape.get('error'), shape)
                self.assertEqual(shape['test_receipt_repo'], str(self.project))

    def test_unenrolled_native_session_directory_does_not_require_craft_layout(self):
        native = self.host.fixture.base / 'native-history' / 'one'
        native.mkdir(parents=True)
        environment = {'CLAUDE_SESSION_DIR': str(native)}
        with patch.dict(os.environ, environment, clear=True):
            self.assertIsNone(router_fixture.r.registered_test_provider(environment, {}))

    def test_registered_marker_cannot_hide_invalid_session_layout(self):
        native = self.host.fixture.base / 'native-history' / 'one'
        native.mkdir(parents=True)
        environment = {'CLAUDE_SESSION_DIR': str(native),
                       'CRAFT_AGENT_WORKSPACE': str(self.workspace)}
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(router_fixture.r.RoutingError, 'physical host session'):
                router_fixture.r.registered_test_provider(environment, {})


if __name__ == '__main__':
    unittest.main()
