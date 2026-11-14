#!/usr/bin/env python3
"""Actual UMG admission and child receipt semantics, without executing receipt argv."""
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import task_keyed_gates as fixtures

ROOT = Path(__file__).resolve().parents[2]
PROVIDER = ROOT / 'hooks/lib/test-evidence.py'

class ReceiptReads(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.Gates(methodName='runTest')
        self.f.setUp()
        fixtures.fixture_git('-C', self.f.repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                             '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', 'commit', '--allow-empty', '-qm', 'fixture', check=True)
        self.base = subprocess.check_output(['/usr/bin/git', '-C', str(self.f.repo), 'rev-parse', 'HEAD'], text=True, timeout=20).strip()
        self.receipt = self.f.ws / 'sessions/one/tasks/read/test-gate.json'
        self.receipt.parent.mkdir(parents=True)
        self.marker = self.f.ws / 'must-not-execute'
        self.receipt.write_text(json.dumps({'schema_version': 2, 'command': ['touch', str(self.marker)]}))

    def tearDown(self):
        self.f.tearDown()

    def argv(self, mode='check'):
        argv = ['python3', '-I', '-B', str(PROVIDER), mode, '--repo', str(self.f.repo), '--base', self.base]
        if mode == 'check':
            argv += ['--receipt', str(self.receipt)]
        return argv

    def test_actual_hook_admits_check_and_sources_but_child_validates_receipt(self):
        for mode in ('check', 'sources'):
            argv = self.argv(mode)
            gate = self.f.hook(shlex.join(argv))
            self.assertEqual(gate.returncode, 0, gate.stdout + gate.stderr)
            child = subprocess.run(argv, cwd=self.f.repo, env=self.f.env, capture_output=True, text=True, timeout=20)
            self.assertEqual(child.returncode, 2 if mode == 'check' else 0, child.stdout + child.stderr)
        reordered = self.argv()
        reordered[1:3] = ['-B', '-I']
        self.assertEqual(self.f.hook(shlex.join(reordered)).returncode, 0)
        absolute = self.argv()
        absolute[0] = sys.executable
        self.assertEqual(self.f.hook(shlex.join(absolute)).returncode, 0)
        before = self.receipt.read_bytes()
        diagnostic = self.argv() + ['--report-only']
        admitted = self.f.hook(shlex.join(diagnostic))
        self.assertEqual(admitted.returncode, 0, admitted.stdout + admitted.stderr)
        child = subprocess.run(diagnostic, env=self.f.env, capture_output=True, text=True, timeout=20)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
        self.assertIn('Test evidence is not current', child.stderr)
        strict = subprocess.run(self.argv(), env=self.f.env, capture_output=True, text=True, timeout=20)
        self.assertEqual(strict.returncode, 2)
        self.assertEqual(self.receipt.read_bytes(), before)
        self.assertFalse(self.marker.exists())
        self.assertEqual(self.f.hook(shlex.join(self.argv('sources') + ['--report-only'])).returncode, 2)

    def test_valid_content_bound_receipt_after_commit_passes_strict_read(self):
        source = self.f.repo / 'behavior.py'
        source.write_text('VALUE = 42\n')
        record = [sys.executable, '-I', '-B', str(PROVIDER), 'record', '--repo', str(self.f.repo),
                  '--output', str(self.receipt), '--source', 'behavior.py', '--framework', 'python-assert',
                  '--', sys.executable, '-I', '-B', '-c',
                  "import runpy; assert runpy.run_path('behavior.py')['VALUE'] == 42"]
        produced = subprocess.run(record, env=self.f.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(produced.returncode, 0, produced.stdout + produced.stderr)
        fixtures.fixture_git('-C', self.f.repo, 'add', 'behavior.py', check=True)
        fixtures.fixture_git('-C', self.f.repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                             '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false',
                             'commit', '-qm', 'tested source', check=True)
        receipt_before = self.receipt.read_bytes()
        admitted = self.f.hook(shlex.join(self.argv()))
        self.assertEqual(admitted.returncode, 0, admitted.stdout + admitted.stderr)
        strict = subprocess.run(self.argv(), env=self.f.env, capture_output=True, text=True, timeout=20)
        self.assertEqual(strict.returncode, 0, strict.stdout + strict.stderr)
        listing = subprocess.run(self.argv('sources'), env=self.f.env, capture_output=True, text=True, timeout=20)
        self.assertEqual(listing.returncode, 0, listing.stdout + listing.stderr)
        self.assertEqual(json.loads(listing.stdout), ['behavior.py'])
        source.write_text('VALUE = 43\n')
        stale = subprocess.run(self.argv(), env=self.f.env, capture_output=True, text=True, timeout=20)
        self.assertEqual(stale.returncode, 2, stale.stdout + stale.stderr)
        self.assertEqual(self.receipt.read_bytes(), receipt_before)

    def test_fixture_seed_preserves_operator_hook_and_signing_context(self):
        with tempfile.TemporaryDirectory(prefix='receipt-operator-control-') as directory:
            home = Path(directory)
            hooks = home / 'operator-hooks'
            hooks.mkdir()
            marker = home / 'operator-executed'
            script = '#!/bin/sh\ntouch ' + shlex.quote(str(marker)) + '\nexit 1\n'
            (hooks / 'pre-commit').write_text(script)
            (hooks / 'pre-commit').chmod(0o700)
            signer = home / 'operator-signer'
            signer.write_text(script)
            signer.chmod(0o700)
            (home / '.gitconfig').write_text('[core]\n hooksPath = ' + str(hooks) +
                                           '\n[commit]\n gpgsign = true\n[gpg]\n program = ' + str(signer) + '\n')
            before = {str(p.relative_to(home)): p.read_bytes() for p in home.rglob('*') if p.is_file()}
            environment = {key: value for key, value in self.f.env.items() if not key.startswith('GIT_')}
            environment.update(HOME=str(home), GIT_CONFIG_NOSYSTEM='1')
            recipe = ("import sys;sys.path.insert(0," + repr(str(ROOT / 'hooks/_test')) + ");"
                      "from test_receipt_reads import ReceiptReads;fixture=ReceiptReads('runTest');"
                      "fixture.setUp();fixture.tearDown()")
            result = subprocess.run([sys.executable, '-I', '-B', '-c', recipe], env=environment,
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(marker.exists())
            self.assertEqual({str(p.relative_to(home)): p.read_bytes() for p in home.rglob('*') if p.is_file()}, before)

    def test_nonread_shapes_do_not_get_the_lane(self):
        argv = self.argv()
        shapes = [argv[:1]+argv[2:], argv[:2]+argv[3:], argv+['--report-only', '--report-only'],
                  argv+['--base', self.base], argv+['--output', str(self.marker)],
                  [x if x != self.base else '--output='+str(self.marker) for x in argv],
                  [x if x != self.base else 'HEAD' for x in argv],
                  [x if x != str(PROVIDER) else str(self.f.ws/'test-evidence.py') for x in argv],
                  [x if x != str(self.f.repo) else str(self.f.ws) for x in argv]]
        for shape in shapes:
            with self.subTest(command=shape):
                result = self.f.hook(shlex.join(shape))
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        result = self.f.hook(shlex.join(argv)+'; touch '+shlex.quote(str(self.marker)))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertFalse(self.marker.exists())

    def test_reader_interpreter_and_registered_provider_integrity(self):
        import task_actions
        with patch('shutil.which', return_value='/untrusted/python3'):
            classified = task_actions.action(shlex.join(self.argv()), str(self.f.repo))
            self.assertFalse(classified['read_only'])
        sys.path.insert(0, str(ROOT / 'bin/_test'))
        import craft_hook_router_test as registered
        fixture = registered.Router(methodName='runTest')
        fixture.setUp()
        try:
            fixture.activate()
            provider = fixture.workspace / 'hooks/lib/test-evidence.py'
            argv = [str(provider) if x == str(PROVIDER) else x for x in self.argv()]
            environment = {**self.f.env, **fixture.env, 'CRAFT_AGENT_WORKSPACE': str(fixture.workspace)}
            good = self.f.hook(shlex.join(argv), env=environment)
            self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
            local = self.f.hook(shlex.join(self.argv()), env=environment)
            self.assertEqual(local.returncode, 2, local.stdout + local.stderr)
            raw = provider.read_bytes()
            provider.write_bytes(raw + b'\n# provider drift\n')
            drift = self.f.hook(shlex.join(argv), env=environment)
            self.assertEqual(drift.returncode, 2, drift.stdout + drift.stderr)
            provider.write_bytes(raw)
            alias = provider.with_name('alias-test-evidence.py')
            alias.symlink_to(provider)
            linked = self.f.hook(shlex.join([str(alias) if x == str(provider) else x for x in argv]), env=environment)
            self.assertEqual(linked.returncode, 2, linked.stdout + linked.stderr)
            alias.unlink()
            os.link(provider, alias)
            hardlink = self.f.hook(shlex.join(argv), env=environment)
            self.assertEqual(hardlink.returncode, 2, hardlink.stdout + hardlink.stderr)
        finally:
            fixture.tearDown()
            fixture.doCleanups()

    def test_child_git_context_ignores_inherited_target_and_helper_configuration(self):
        caller = self.f.ws / 'caller'
        fixtures.fixture_git('init', '-q', str(caller), check=True)
        helper = self.f.ws / 'fsmonitor-helper'
        helper.write_text('#!/bin/sh\ntouch ' + shlex.quote(str(self.marker)) + '\n')
        helper.chmod(0o700)
        fixtures.fixture_git('-C', self.f.repo, 'config', 'core.fsmonitor', str(helper), check=True)
        before = {str(p.relative_to(caller)): p.read_bytes() for p in caller.rglob('*') if p.is_file()}
        parent_environment = dict(os.environ)
        environment = {**self.f.env, 'GIT_DIR': str(caller / '.git'), 'GIT_WORK_TREE': str(caller),
                       'GIT_INDEX_FILE': str(caller / '.git/index'), 'GIT_CONFIG_COUNT': '1',
                       'GIT_CONFIG_KEY_0': 'core.fsmonitor', 'GIT_CONFIG_VALUE_0': str(helper),
                       'GIT_CONFIG_PARAMETERS': "'core.bare=true'"}
        admitted = self.f.hook(shlex.join(self.argv('sources')), env=environment)
        self.assertEqual(admitted.returncode, 0, admitted.stdout + admitted.stderr)
        result = subprocess.run(self.argv('sources'), env=environment, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout), [])
        self.assertFalse(self.marker.exists())
        self.assertEqual({str(p.relative_to(caller)): p.read_bytes() for p in caller.rglob('*') if p.is_file()}, before)
        self.assertEqual(dict(os.environ), parent_environment)

    def test_unregistered_provider_byte_drift_cannot_acquire_read_authority(self):
        import task_actions
        policy = self.f.ws / 'copied-policy/hooks/lib'
        policy.mkdir(parents=True)
        for name in ('task_actions.py', 'craft-settings-router.py', 'test-evidence.py'):
            (policy / name).write_bytes((ROOT / 'hooks/lib' / name).read_bytes())
        provider = policy / 'test-evidence.py'
        provider.write_text('from pathlib import Path\nPath(' + repr(str(self.marker)) + ').touch()\n')
        argv = [str(provider) if x == str(PROVIDER) else x for x in self.argv()]
        with patch.object(task_actions, '__file__', str(policy / 'task_actions.py')):
            with self.assertRaises(task_actions.UnknownShape):
                task_actions._test_receipt_record(task_actions.shell_tokens(shlex.join(argv)), str(self.f.repo))
        self.assertFalse(self.marker.exists())

    def test_cli_named_ref_works_and_option_base_cannot_write(self):
        for base in ('HEAD', self.base, '--output='+str(self.marker)):
            argv = self.argv('sources')
            argv[argv.index('--base')+1] = base
            result = subprocess.run(argv, env=self.f.env, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 2 if base.startswith('-') else 0, result.stdout+result.stderr)
        self.assertFalse(self.marker.exists())
        record = ['python3', '-I', '-B', str(PROVIDER), 'record', '--repo', str(self.f.repo), '--output', str(self.marker)]
        self.assertEqual(self.f.hook(shlex.join(record)).returncode, 2)

if __name__ == '__main__':
    unittest.main()
