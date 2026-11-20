#!/usr/bin/env python3
"""Long literal operand lists resolve within the hook budget.

Target resolution must not spend git subprocesses per operand: per target,
a `git rev-parse` plus origin reads for every foreign-repository own-session
gate made a 50-operand `cp -p` with three foreign gates exceed the 10 s hook
timeout. These cases run the real hook in a private fixture, count git
subprocesses through a PATH shim, and keep every scope denial intact.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / 'hooks/bash/universal-mutation-gate.sh'
SID = '261110-r1167-fixture'
HOOK_TIMEOUT = 10  # hooks/settings-snippet.json universal-mutation-gate timeout
BUDGET = HOOK_TIMEOUT / 2  # AC1: at most half the hook timeout

spec = importlib.util.spec_from_file_location('resolver_1167', ROOT / 'hooks/lib/resolve-think-gate.py')
resolver = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(ROOT / 'hooks/lib'))
spec.loader.exec_module(resolver)


class LongOperandResolution(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='r1167-')
        base = Path(self.tmp.name).resolve()
        self.ws, self.repo, self.home, self.shim = (base / x for x in ('ws', 'repo', 'home', 'shim'))
        self.plans = self.ws / 'sessions' / SID / 'plans'
        for directory in (self.plans, self.repo, self.home, self.shim):
            directory.mkdir(parents=True)
        self.git = shutil.which('git')
        self.git_init(self.repo)
        self.other = base / 'other'
        self.other.mkdir()
        self.git_init(self.other)
        self.outside = base / 'outside'
        self.outside.mkdir()
        self.log = base / 'git-calls.log'
        shim = self.shim / 'git'
        shim.write_text(f"#!/bin/sh\necho x >> '{self.log}'\nexec '{self.git}' \"$@\"\n")
        shim.chmod(0o755)
        self.gate('cover', 'TEST-1167-cover', self.repo)
        for index in range(3):  # unrelated own tasks in another repository
            self.gate(f'other{index}', f'TEST-1167-other{index}', self.other)
        self.src = self.repo / 'src'
        self.src.mkdir()
        self.dest = self.repo / 'dest'
        self.dest.mkdir()
        self.names = [self.src / f'file_{index:03d}.txt' for index in range(100)]
        for name in self.names:
            name.touch()

    def tearDown(self):
        self.tmp.cleanup()

    def git_init(self, path):
        subprocess.run([self.git, 'init', '-q', str(path)], check=True, timeout=60)

    def gate(self, slug, task, root):
        directory = self.ws / 'sessions' / SID / 'tasks' / slug
        directory.mkdir(parents=True)
        common = {'task_id': task, 'sessionId': SID}
        files = {
            'think-gate.json': {**common, 'status': 'implementing', 'repo_root': str(root),
                                'scope_paths': [str(root)], 'tier': 'C'},
            'investigate-gate.json': {**common, 'findings': ['fixture']},
            'junior-senior-gate.json': {**common, 'junior_found': True, 'senior_found': True},
            'artifacts-posted-gate.json': {**common, 'investigate_posted': True, 'premortem_posted': True},
        }
        for name, data in files.items():
            (directory / name).write_text(json.dumps(data))
        (self.plans / f'pre-mortem-{slug}.md').write_text(
            f'---\nticket_refs:\n  - {task}: fixture\n---\n# Pre-mortem {task}\n\n### Tiger 1\nSeverity: LOW\n')

    def run_gate(self, command, shim=None):
        payload = json.dumps({'tool_name': 'Bash', 'hook_event_name': 'PreToolUse', 'session_id': SID,
                              'tool_input': {'command': command}, 'cwd': str(self.repo)})
        env = {'PATH': f'{shim or self.shim}:{os.path.dirname(sys.executable)}:/usr/bin:/bin', 'HOME': str(self.home),
               'CRAFT_AGENT_WORKSPACE': str(self.ws), 'CRAFT_SESSION_ID': SID}
        self.log.unlink(missing_ok=True)
        start = time.monotonic()
        result = subprocess.run(['bash', str(GATE)], input=payload, capture_output=True, text=True,
                                cwd=str(self.repo), env=env, timeout=120)
        elapsed = time.monotonic() - start
        calls = len(self.log.read_text().splitlines()) if self.log.exists() else 0
        return result.returncode, elapsed, calls, result.stdout + result.stderr

    def copy_command(self, count, destination=None):
        return 'cp -p ' + ' '.join(map(str, self.names[:count])) + ' ' + str(destination or self.dest) + '/'

    # AC1 -----------------------------------------------------------------
    def test_fifty_operand_copy_is_allowed_within_half_the_hook_timeout(self):
        code, elapsed, calls, output = self.run_gate(self.copy_command(50))
        self.assertEqual(code, 0, output)
        self.assertLess(elapsed, BUDGET, f'{elapsed:.2f}s with {calls} git calls')

    def test_git_subprocesses_do_not_grow_with_operand_count(self):
        counts = {}
        for count in (14, 42, 100):
            code, _, calls, output = self.run_gate(self.copy_command(count))
            self.assertEqual(code, 0, output)
            counts[count] = calls
        self.assertEqual(counts[14], counts[100], counts)
        self.assertGreater(counts[100], 0, counts)  # the shim observed real resolution
        self.assertLess(counts[100], 14, counts)  # fewer git calls than even the smallest operand list

    def test_same_origin_checkouts_do_not_scale_with_operand_count(self):
        # Other tasks in separate checkouts of the same origin pass the
        # identity check by origin, which costs origin reads rather than a
        # rejection; those verdicts are reused too.
        for checkout in (self.repo, self.other):
            subprocess.run([self.git, '-C', str(checkout), 'remote', 'add', 'origin',
                            'https://github.com/example/shared.git'], check=True, timeout=60)
        counts = {}
        for count in (14, 100):
            code, _, calls, output = self.run_gate(self.copy_command(count))
            self.assertEqual(code, 0, output)
            counts[count] = calls
        self.assertEqual(counts[14], counts[100], counts)
        self.assertLess(counts[100], 14, counts)

    # AC2 and scope negatives ---------------------------------------------
    def test_one_out_of_scope_operand_denies_the_whole_command(self):
        operands = ' '.join(str(self.dest / f'new_{index:03d}.txt') for index in range(49))
        code, _, _, output = self.run_gate(f'touch {operands} {self.outside / "x.txt"}')
        self.assertEqual(code, 2, output)
        self.assertIn('Unscoped mutation', output)

    def test_out_of_scope_copy_destination_is_denied(self):
        code, _, _, output = self.run_gate(self.copy_command(50, self.outside))
        self.assertEqual(code, 2, output)
        self.assertIn('Unscoped mutation', output)

    def test_destination_symlink_escaping_scope_is_denied(self):
        (self.dest / 'file_049.txt').symlink_to(self.outside / 'escape.txt')
        code, _, _, output = self.run_gate(self.copy_command(50))
        self.assertEqual(code, 2, output)
        self.assertIn('Unscoped mutation', output)

    def test_operand_in_nested_foreign_repository_is_denied(self):
        nested = self.repo / 'nested'
        nested.mkdir()
        self.git_init(nested)
        operands = ' '.join(str(self.dest / f'new_{index:03d}.txt') for index in range(49))
        code, _, _, output = self.run_gate(f'touch {operands} {nested / "x.txt"}')
        self.assertEqual(code, 2, output)
        self.assertIn('Task gate scope rejected', output)
        self.assertIn(f'expected target repo={nested}', output)

    def test_operands_spanning_two_owned_repositories_through_a_symlink_are_split(self):
        # dest/elsewhere resolves into the other task's repository; the cache
        # must key on the resolved directory, not the operand's spelling.
        (self.other / 'inbox').mkdir()
        (self.dest / 'elsewhere').symlink_to(self.other / 'inbox', target_is_directory=True)
        operands = ' '.join(str(self.dest / f'new_{index:03d}.txt') for index in range(49))
        code, _, _, output = self.run_gate(f'touch {operands} {self.dest / "elsewhere" / "x.txt"}')
        self.assertEqual(code, 2, output)
        self.assertRegex(output, 'Mutation spans multiple tasks|Ambiguous task ownership')

    def test_genuine_non_git_own_task_is_allowed_and_unowned_is_denied(self):
        # Outside Git every toplevel lookup fails; that must neither authorize
        # an unowned directory nor deny an explicit own Task for that directory.
        base = Path(self.tmp.name).resolve()
        maintenance, unowned = base / 'maintenance', base / 'unowned'
        maintenance.mkdir()
        unowned.mkdir()
        self.gate('maintenance', 'TEST-1167-maintenance', maintenance)
        code, _, _, output = self.run_gate(f'touch {maintenance / "a.txt"} {maintenance / "b.txt"}')
        self.assertEqual(code, 0, output)
        code, _, _, output = self.run_gate(f'touch {unowned / "a.txt"} {unowned / "b.txt"}')
        self.assertEqual(code, 2, output)

    def test_transient_toplevel_failure_cannot_authorize_nested_siblings(self):
        # Real git behind a shim whose first --show-toplevel exits 128. A
        # failed lookup must never authorize the foreign nested repository.
        nested = self.repo / 'nested'
        nested.mkdir()
        self.git_init(nested)
        flaky = Path(self.tmp.name).resolve() / 'flaky-shim'
        flaky.mkdir()
        marker = flaky / 'failed-once'
        (flaky / 'git').write_text(
            '#!/bin/sh\n'
            f'case " $* " in *" --show-toplevel "*) [ -e \'{marker}\' ] || {{ : > \'{marker}\'; exit 128; }} ;; esac\n'
            f"exec '{self.git}' \"$@\"\n")
        (flaky / 'git').chmod(0o755)
        code, _, _, output = self.run_gate(f'touch {nested / "a.txt"} {nested / "b.txt"}', shim=flaky)
        self.assertTrue(marker.exists(), 'the shim never failed a toplevel lookup')
        self.assertEqual(code, 2, output)

    def test_unowned_repository_lists_every_rejected_gate(self):
        stranger = self.outside / 'stranger'
        stranger.mkdir()
        self.git_init(stranger)
        code, _, _, output = self.run_gate(f'touch {stranger / "a.txt"} {stranger / "b.txt"}')
        self.assertEqual(code, 2, output)
        self.assertEqual(output.count('Task gate scope rejected'), 4, output)


class ResolutionCache(unittest.TestCase):
    """Only definitive git answers are reused across targets in one resolution."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='r1167-unit-')
        base = Path(self.tmp.name).resolve()
        self.ws, self.repo = base / 'ws', base / 'repo'
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True, timeout=60)
        directory = self.ws / 'sessions' / SID / 'tasks' / 'cover'
        directory.mkdir(parents=True)
        (directory / 'think-gate.json').write_text(json.dumps({
            'task_id': 'TEST-1167-cover', 'sessionId': SID, 'status': 'implementing',
            'repo_root': str(self.repo), 'scope_paths': [str(self.repo)]}))
        # Isolate from the invoking runtime's session/task bindings.
        isolated = {k: v for k, v in os.environ.items()
                    if not k.startswith(('CRAFT_', 'CLAUDE_', 'CCP_', 'SESSION_', 'HUB_'))}
        self.env = mock.patch.dict(os.environ, {**isolated, 'CRAFT_SESSION_ID': SID}, clear=True)
        self.env.start()
        self.paths = [str(self.repo / f'f{index}.txt') for index in range(5)]

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def toplevel_calls(self, side_effect):
        real = subprocess.check_output
        calls = []

        def check_output(arguments, *args, **kwargs):
            if 'rev-parse' in arguments and '--show-toplevel' in arguments:
                calls.append(arguments)
                outcome = side_effect(len(calls))
                if isinstance(outcome, BaseException):
                    raise outcome
            return real(arguments, *args, **kwargs)
        with mock.patch.object(resolver.subprocess, 'check_output', check_output):
            selected = resolver.select_task(str(self.ws), self.paths, session_id=SID)
        return selected, calls

    def test_one_toplevel_lookup_serves_targets_in_the_same_directory(self):
        selected, calls = self.toplevel_calls(lambda n: None)
        self.assertTrue(selected['gate'], selected)
        self.assertEqual(len(calls), 1)

    # A git exit status, timeout, launch failure or signal is never proof of
    # stable repository absence, so a failure is never reused as an identity.
    FAILURES = (subprocess.TimeoutExpired(['git'], 3), OSError('exec failed'),
                subprocess.CalledProcessError(128, ['git']),  # positive fatal status
                subprocess.CalledProcessError(-9, ['git']))   # signal-killed git

    def test_failed_lookup_never_authorizes_foreign_siblings(self):
        # A failed identity lookup must not be cached as an identity: the
        # foreign nested siblings stay unowned whatever the failure was.
        nested = self.repo / 'nested'
        nested.mkdir()
        subprocess.run(['git', 'init', '-q', str(nested)], check=True, timeout=60)
        self.paths = [str(nested / 'a.txt'), str(nested / 'b.txt')]
        for failure in self.FAILURES:
            with self.subTest(failure=repr(failure)):
                selected, _ = self.toplevel_calls(lambda n: failure if n == 1 else None)
                self.assertIsNone(selected['gate'], selected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
