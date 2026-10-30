#!/usr/bin/env python3
"""Real Git snapshots, producer subprocesses and strict receipt rejection."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import time
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / 'hooks/lib/test-evidence.py'
spec = importlib.util.spec_from_file_location('test_evidence_contract', TOOL)
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)


class Evidence(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name).resolve()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        (self.repo / 'PROJECT.md').write_text('testing:\n  command: unittest\n')
        (self.repo / 'app.py').write_text('x = 1\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'base')
        self.base = self.git('rev-parse', 'HEAD').strip()
        (self.repo / 'app.py').write_text('x = 2\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'change')
        self.receipt = self.repo / 'receipt.json'
        self.produce()
        self.valid = json.loads(self.receipt.read_text())

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True, timeout=120).strip()

    def produce(self, source='app.py', command=None):
        return subprocess.run([sys.executable, str(TOOL), 'record', '--repo', str(self.repo),
                               '--output', str(self.receipt), '--source', source,
                               '--framework', 'unittest', '--', *(command or [sys.executable, '-c', 'assert 1 + 1 == 2'])],
                              text=True, capture_output=True, timeout=120)

    def check(self, document=None):
        if document is not None:
            self.receipt.write_text(json.dumps(document))
        return e.check(self.repo, self.receipt, e.source_paths(self.repo, self.base))

    def test_timeout_cancels_descendants_and_invalidates_old_pass(self):
        marker = self.repo / 'late-mutation'
        child = "import time; from pathlib import Path; time.sleep(0.8); Path(" + repr(str(marker)) + ").write_text('unexpected')"
        parent = "import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', " + repr(child) + "]); time.sleep(5)"
        args = SimpleNamespace(repo=str(self.repo), source=['app.py'], output=str(self.receipt),
                               think_gate=None, framework='unittest', command=[sys.executable, '-c', parent])
        with patch.object(e, 'TEST_TIMEOUT_SECONDS', 0.3):
            with self.assertRaises(subprocess.TimeoutExpired):
                e.record(args)
        pending = json.loads(self.receipt.read_text())
        self.assertIsNone(pending['exit_code'])
        self.assertEqual(pending['evidence'][0]['result'], 'pending')
        self.assertTrue(self.check())
        time.sleep(1)
        self.assertFalse(marker.exists(), 'timed-out test descendant survived cancellation')

    def test_success_and_exact_content(self):
        self.assertEqual(self.check(), [])
        self.assertEqual(e.source_paths(self.repo, self.base), ['app.py'])

    def test_empty_suffix_absolute_and_traversal_do_not_cover(self):
        for source in ('', 'pp.py', 'nested/app.py', '/app.py', '../app.py', './app.py'):
            with self.subTest(source=source):
                d = copy.deepcopy(self.valid); d['evidence'][0]['source'] = source
                self.assertTrue(self.check(d))

    def test_failed_missing_and_malformed_results(self):
        for result in ('fail', 'failed', 'skipped', '', None, {}, True):
            with self.subTest(result=result):
                d = copy.deepcopy(self.valid); d['evidence'][0]['result'] = result
                try:
                    problems = self.check(d)
                except TypeError:
                    # CLI must also fail closed for malformed JSON field types.
                    p = subprocess.run([sys.executable, str(TOOL), 'check', '--repo', str(self.repo),
                                        '--receipt', str(self.receipt), '--base', self.base], capture_output=True, timeout=120)
                    self.assertEqual(p.returncode, 2)
                else:
                    self.assertTrue(problems)
        d = copy.deepcopy(self.valid); d['exit_code'] = True
        self.assertTrue(self.check(d))

    def test_stale_committed_and_working_source(self):
        (self.repo / 'app.py').write_text('x = 3\n')
        self.assertTrue(self.check())
        self.git('add', 'app.py'); self.git('commit', '-qm', 'new change')
        self.assertTrue(self.check())

    def test_nonancestor_and_missing_revision(self):
        for value in (None, '', 'HEAD', '0' * 40):
            d = copy.deepcopy(self.valid); d['tested_revision'] = value
            self.assertTrue(self.check(d))

    def test_precommit_receipt_survives_commit_and_unrelated_change(self):
        (self.repo / 'app.py').write_text('x = 4\n')
        self.assertEqual(self.produce().returncode, 0)
        self.assertTrue(self.check(), 'uncommitted source is not yet the pushed snapshot')
        self.git('add', 'app.py'); self.git('commit', '-qm', 'commit tested content')
        self.assertEqual(self.check(), [])
        (self.repo / 'note.md').write_text('unrelated\n')
        self.git('add', 'note.md'); self.git('commit', '-qm', 'docs')
        self.assertEqual(self.check(), [])

    def test_failed_or_mutating_test_run_invalidates_prior_success(self):
        self.assertNotEqual(self.produce(command=[sys.executable, '-c', 'raise SystemExit(1)']).returncode, 0)
        self.assertTrue(self.check())
        self.assertNotEqual(self.produce(command=[sys.executable, '-c', "from pathlib import Path; Path('app.py').write_text('mutated')"]).returncode, 0)
        self.assertTrue(self.check())

    def test_legacy_report_only_does_not_pass_strict(self):
        self.receipt.write_text(json.dumps({'evidence': [{'source': '', 'result': 'pass'}]}))
        command = [sys.executable, str(TOOL), 'check', '--repo', str(self.repo),
                   '--receipt', str(self.receipt), '--base', self.base]
        self.assertEqual(subprocess.run(command, capture_output=True, timeout=120).returncode, 2)
        self.assertEqual(subprocess.run([*command, '--report-only'], capture_output=True, timeout=120).returncode, 0)

    def test_quotes_unicode_newlines_and_suffix_duplicates(self):
        names = ["quote'file.py", 'line\nfile.py', 'unicode-λ.py', 'nested/app.py']
        for name in names:
            (self.repo / name).parent.mkdir(exist_ok=True)
            (self.repo / name).write_text('x = 1\n')
        self.git('add', '.'); self.git('commit', '-qm', 'hostile paths')
        command = [sys.executable, str(TOOL), 'record', '--repo', str(self.repo), '--output', str(self.receipt)]
        for name in ['app.py', *names]:
            command += ['--source', name]
        p = subprocess.run([*command, '--framework', 'unittest', '--', sys.executable, '-c', 'assert True'], capture_output=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.check(), [])
        d = json.loads(self.receipt.read_text()); d['evidence'] = d['evidence'][:1]
        self.assertTrue(self.check(d))

    def test_actual_guard_handles_hostile_paths_and_strict_failures(self):
        self.git('update-ref', 'refs/remotes/origin/main', self.base)
        names = ["quote'file.py", 'line\nfile.py', 'evil$(touch INJECTED).py', 'unicode-λ.py']
        for name in names:
            (self.repo / name).write_text('x = 1\n')
        self.git('add', '.'); self.git('commit', '-qm', 'hostile source paths')
        session = self.repo / 'session-one'
        task = session / 'tasks/current'; task.mkdir(parents=True)
        think = task / 'think-gate.json'
        think.write_text(json.dumps(dict(task_id='strict-evidence', sessionId=session.name,
                                        repo_root=str(self.repo), scope_paths=[str(self.repo)], status='implementing')))
        receipt = task / 'test-gate.json'
        cmd = [sys.executable, str(TOOL), 'record', '--repo', str(self.repo),
               '--think-gate', str(think), '--output', str(receipt), '--framework', 'unittest']
        for name in ['app.py', *names]:
            cmd += ['--source', name]
        self.assertEqual(subprocess.run([*cmd, '--', sys.executable, '-c', 'assert True'], capture_output=True, timeout=120).returncode, 0)
        env = {k:v for k,v in os.environ.items() if not k.startswith(('CRAFT_', 'CLAUDE_', 'CCP_', 'SESSION_'))}
        env.update(CRAFT_SESSION_DIR=str(session), CRAFT_AGENT_WORKSPACE=str(self.repo))
        payload = json.dumps(dict(cwd=str(self.repo), tool_input={'command': 'git push'}))
        def guard():
            return subprocess.run(['bash', str(ROOT / 'hooks/git/test-guard.sh')], input=payload,
                                  env=env, text=True, capture_output=True, timeout=120)
        result = guard()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.repo / 'INJECTED').exists())
        valid = json.loads(receipt.read_text())
        for change in ('empty', 'failed', 'stale', 'legacy'):
            document = copy.deepcopy(valid)
            if change == 'empty': document['evidence'][0]['source'] = ''
            elif change == 'failed': document['evidence'][0]['result'] = 'failed'
            elif change == 'stale': document['evidence'][0]['source_blob'] = '0' * 40
            else: document.pop('schema_version')
            receipt.write_text(json.dumps(document))
            self.assertEqual(guard().returncode, 2, change)

    def test_deleted_source_requires_deleted_receipt(self):
        (self.repo / 'app.py').unlink(); self.git('add', '-u'); self.git('commit', '-qm', 'delete')
        self.assertTrue(self.check())
        self.assertEqual(self.produce().returncode, 0)
        self.assertEqual(self.check(), [])

    def test_symlink_and_hardlink_receipts_rejected(self):
        other = self.repo / 'other.json'; other.write_bytes(self.receipt.read_bytes())
        self.receipt.unlink(); self.receipt.symlink_to(other)
        with self.assertRaises(OSError): self.check()
        self.receipt.unlink(); os.link(other, self.receipt)
        with self.assertRaises(ValueError): self.check()

    def test_unrequested_entries_must_be_well_formed_and_successful(self):
        for extra in ({'source': 'other.py', 'source_blob': '0' * 40},
                      {'source': 'other.py', 'result': 'failed', 'source_blob': '0' * 40},
                      {'source': 'other.py', 'result': 'pass'},
                      {'source': 'other.py', 'result': 'pass', 'source_blob': '$BAD'}):
            document = copy.deepcopy(self.valid); document['evidence'].append(extra)
            self.assertTrue(self.check(document))

    def test_fifo_replacement_fails_without_blocking(self):
        (self.repo / 'app.py').unlink(); os.mkfifo(self.repo / 'app.py')
        result = subprocess.run([sys.executable, str(TOOL), 'check', '--repo', str(self.repo),
                                 '--receipt', str(self.receipt), '--base', self.base],
                                capture_output=True, timeout=3)
        self.assertEqual(result.returncode, 2)
        self.assertIn(b'regular file', result.stderr)

    def test_source_hashing_does_not_execute_clean_filters(self):
        (self.repo / '.gitattributes').write_text('app.py filter=sentinel\n')
        self.git('config', 'filter.sentinel.clean', 'touch FILTER_EXECUTED; cat')
        self.assertEqual(e.working_blob(self.repo, 'app.py'), self.valid['evidence'][0]['source_blob'])
        self.assertFalse((self.repo / 'FILTER_EXECUTED').exists())

    def test_duplicate_source_evidence_rejected(self):
        d = copy.deepcopy(self.valid); d['evidence'].append(d['evidence'][0])
        self.assertTrue(self.check(d))


if __name__ == '__main__':
    unittest.main(verbosity=2)
