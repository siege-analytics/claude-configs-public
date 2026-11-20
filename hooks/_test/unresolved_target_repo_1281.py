#!/usr/bin/env python3
"""An unresolved target repository denies task ownership (#1281).

`select_task` compares a gate's declared repo_root with the target's
`git rev-parse --show-toplevel`. When that lookup fails (non-zero exit,
signal, timeout, exec error) for a target inside a Git checkout, the
comparison must not be skipped: a gate whose repo_root names a different
repository could otherwise own the target through its scope_paths. These
cases run the real hook with a PATH git shim that fails the lookup for one
directory only, plus unit cases for the resolver and its filesystem probe.
"""
import errno
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / 'hooks/bash/universal-mutation-gate.sh'
SID = '261110-r1281-fixture'

spec = importlib.util.spec_from_file_location('resolver_1281', ROOT / 'hooks/lib/resolve-think-gate.py')
resolver = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(ROOT / 'hooks/lib'))
spec.loader.exec_module(resolver)

# R1281_FAIL_DIR is one `git -C` directory, or `*` for every --show-toplevel lookup.
SHIM = """#!/bin/sh
toplevel=0
case " $* " in *" rev-parse "*"--show-toplevel "*) toplevel=1 ;; esac
match=0
if [ "$R1281_FAIL_DIR" = "*" ]; then match=1; fi
if [ "$1" = "-C" ] && [ "$2" = "$R1281_FAIL_DIR" ]; then match=1; fi
if [ "$toplevel" = 1 ] && [ "$match" = 1 ]; then
  case "$R1281_FAIL_MODE" in
    signal) kill -9 $$ ;;
    refusal) echo "fatal: injected refusal" >&2; exit 128 ;;
    *) exit 1 ;;
  esac
fi
exec '{git}' "$@"
"""


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='r1281-')
        base = Path(self.tmp.name).resolve()
        self.ws, self.home, self.shim = base / 'ws', base / 'home', base / 'shim'
        self.own, self.foreign, self.plain = base / 'own', base / 'foreign', base / 'plain'
        self.plans = self.ws / 'sessions' / SID / 'plans'
        for directory in (self.plans, self.home, self.shim, self.own, self.foreign, self.plain):
            directory.mkdir(parents=True)
        self.git = shutil.which('git')
        for repo in (self.own, self.foreign):
            subprocess.run([self.git, 'init', '-q', str(repo)], check=True, timeout=60)
        self.shared = self.foreign / 'shared'
        self.shared.mkdir()
        (self.shim / 'git').write_text(SHIM.format(git=self.git))
        (self.shim / 'git').chmod(0o755)
        # The own-repo gate's scope_paths also cover a directory of the foreign
        # repository and a plain non-Git directory.
        self.gate('own', 'TEST-1281-own', self.own, [self.own, self.shared, self.plain])

    def tearDown(self):
        self.tmp.cleanup()

    def gate(self, slug, task, root, scopes):
        directory = self.ws / 'sessions' / SID / 'tasks' / slug
        directory.mkdir(parents=True)
        common = {'task_id': task, 'sessionId': SID}
        files = {
            'think-gate.json': {**common, 'status': 'implementing', 'repo_root': str(root),
                                'scope_paths': [str(s) for s in scopes], 'tier': 'C'},
            'investigate-gate.json': {**common, 'findings': ['fixture']},
            'junior-senior-gate.json': {**common, 'junior_found': True, 'senior_found': True},
            'artifacts-posted-gate.json': {**common, 'investigate_posted': True, 'premortem_posted': True},
        }
        for name, data in files.items():
            (directory / name).write_text(json.dumps(data))
        (self.plans / f'pre-mortem-{slug}.md').write_text(
            f'---\nticket_refs:\n  - {task}: fixture\n---\n# Pre-mortem {task}\n\n### Tiger 1\nSeverity: LOW\n')


class UnresolvedTargetThroughHook(Fixture):
    def run_gate(self, target, fail_dir=None, mode='exit'):
        payload = json.dumps({'tool_name': 'Bash', 'hook_event_name': 'PreToolUse', 'session_id': SID,
                              'tool_input': {'command': f'touch {target}'}, 'cwd': str(self.own)})
        env = {'PATH': f'{self.shim}:{os.path.dirname(sys.executable)}:/usr/bin:/bin', 'HOME': str(self.home),
               'CRAFT_AGENT_WORKSPACE': str(self.ws), 'CRAFT_SESSION_ID': SID,
               'R1281_FAIL_DIR': str(fail_dir or ''), 'R1281_FAIL_MODE': mode}
        result = subprocess.run(['bash', str(GATE)], input=payload, capture_output=True, text=True,
                                cwd=str(self.own), env=env, timeout=120)
        return result.returncode, result.stdout + result.stderr

    def test_control_resolved_foreign_target_is_denied(self):
        code, output = self.run_gate(self.shared / 'x.txt')
        self.assertEqual(code, 2, output)
        self.assertIn('Task gate scope rejected', output)

    def test_failed_lookup_in_foreign_repository_denies(self):
        for mode in ('exit', 'signal', 'refusal'):
            with self.subTest(mode=mode):
                code, output = self.run_gate(self.shared / 'x.txt', fail_dir=self.shared, mode=mode)
                self.assertEqual(code, 2, output)
                self.assertIn('target repository is unresolved', output)

    def test_same_repo_target_still_allowed(self):
        code, output = self.run_gate(self.own / 'x.txt')
        self.assertEqual(code, 0, output)
        # A failure injected for another directory does not affect this target.
        code, output = self.run_gate(self.own / 'x.txt', fail_dir=self.shared, mode='signal')
        self.assertEqual(code, 0, output)

    def test_bare_repository_inside_scope_denies(self):
        # rev-parse refuses inside a bare repository, which has no .git entry.
        bare = self.plain / 'bare.git'
        subprocess.run([self.git, 'init', '-q', '--bare', str(bare)], check=True, timeout=60)
        code, output = self.run_gate(bare / 'hooks' / 'x')
        self.assertEqual(code, 2, output)
        self.assertIn('target repository is unresolved', output)

    def test_own_git_directory_internals_deny(self):
        # rev-parse refuses inside .git; a scope covering the checkout does not
        # extend ownership to its hooks.
        code, output = self.run_gate(self.own / '.git' / 'hooks' / 'pre-commit')
        self.assertEqual(code, 2, output)
        self.assertIn('target repository is unresolved', output)

    # Hub acceptance controls (issuecomment-6784870434): a genuine non-Git own
    # Task allows, an unowned non-Git directory denies, and a nested real
    # repository whose every toplevel lookup fails with 128 denies.
    def test_control_non_git_own_task_allows(self):
        maintenance = self.foreign.parent / 'maintenance'
        maintenance.mkdir()
        self.gate('maintenance', 'TEST-1281-maintenance', maintenance, [maintenance])
        for fail_dir in (None, '*'):
            with self.subTest(fail_dir=fail_dir):
                code, output = self.run_gate(maintenance / 'x.txt', fail_dir=fail_dir, mode='refusal')
                self.assertEqual(code, 0, output)

    def test_control_unowned_non_git_directory_denies(self):
        stranger = self.foreign.parent / 'stranger'
        stranger.mkdir()
        for fail_dir in (None, '*'):
            with self.subTest(fail_dir=fail_dir):
                code, output = self.run_gate(stranger / 'x.txt', fail_dir=fail_dir, mode='refusal')
                self.assertEqual(code, 2, output)
                self.assertIn('Unscoped mutation', output)

    def test_control_nested_repository_with_every_lookup_failing_denies(self):
        nested = self.own / 'nested'
        subprocess.run([self.git, 'init', '-q', str(nested)], check=True, timeout=60)
        code, output = self.run_gate(nested / 'x.txt')
        self.assertEqual(code, 2, output)  # resolved: nested repo is foreign to the own gate
        code, output = self.run_gate(nested / 'x.txt', fail_dir='*', mode='refusal')
        self.assertEqual(code, 2, output)
        self.assertIn('target repository is unresolved', output)

    def test_non_git_scope_path_still_allowed(self):
        code, output = self.run_gate(self.plain / 'x.txt')
        self.assertEqual(code, 0, output)
        code, output = self.run_gate(self.plain / 'x.txt', fail_dir=self.plain, mode='signal')
        self.assertEqual(code, 0, output)


class UnresolvedTargetResolver(Fixture):
    def setUp(self):
        super().setUp()
        isolated = {k: v for k, v in os.environ.items()
                    if not k.startswith(('CRAFT_', 'CLAUDE_', 'CCP_', 'SESSION_', 'HUB_'))}
        self.env = mock.patch.dict(os.environ, {**isolated, 'CRAFT_SESSION_ID': SID}, clear=True)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        super().tearDown()

    def select(self, paths, failure, failing=None, times=None):
        """Fail the toplevel lookup for one directory (the first `times` calls, or all)."""
        real = subprocess.check_output
        failing = str(failing or self.shared)
        calls = []

        def check_output(arguments, *args, **kwargs):
            if arguments[:3] == ['git', '-C', failing] and arguments[3:5] == ['rev-parse', '--show-toplevel']:
                calls.append(arguments)
                if times is None or len(calls) <= times:
                    raise failure
            return real(arguments, *args, **kwargs)
        with mock.patch.object(resolver.subprocess, 'check_output', check_output):
            return resolver.select_task(str(self.ws), [str(p) for p in paths], session_id=SID)

    def test_every_lookup_failure_denies_the_foreign_target(self):
        for failure in (subprocess.CalledProcessError(1, ['git']), subprocess.CalledProcessError(-9, ['git']),
                        subprocess.CalledProcessError(128, ['git']), subprocess.TimeoutExpired(['git'], 3),
                        OSError('exec failed')):
            with self.subTest(failure=repr(failure)):
                selected = self.select([self.shared / 'x.txt'], failure)
                self.assertIsNone(selected['gate'], selected)
                self.assertIn('target repository is unresolved', selected['error'])
                self.assertIn(str(self.shared / 'x.txt'), selected['error'])

    def test_unresolved_target_denies_a_mixed_operand_list(self):
        selected = self.select([self.own / 'a.txt', self.shared / 'x.txt'], subprocess.CalledProcessError(-9, ['git']))
        self.assertIsNone(selected['gate'], selected)
        self.assertIn('target repository is unresolved', selected['error'])

    def test_resolved_own_targets_still_select_the_gate(self):
        selected = self.select([self.own / 'a.txt', self.plain / 'b.txt'], subprocess.CalledProcessError(-9, ['git']))
        self.assertTrue(selected['gate'], selected)

    # Explicit split for reconciling with per-call lookup caching (PR #1278):
    # a target whose own lookup failed is denied, and that deny ends the
    # resolution even when other targets in the same directory follow; a
    # separate later resolution whose lookup succeeds selects the gate.
    def test_failed_lookup_for_own_repo_target_denies(self):
        for failure in (subprocess.CalledProcessError(-9, ['git']), subprocess.TimeoutExpired(['git'], 3),
                        OSError('exec failed')):
            with self.subTest(failure=repr(failure)):
                selected = self.select([self.own / 'a.txt'], failure, failing=self.own)
                self.assertIsNone(selected['gate'], selected)
                self.assertIn('target repository is unresolved', selected['error'])

    def test_one_failed_lookup_denies_within_a_single_resolution(self):
        for failure in (subprocess.CalledProcessError(-9, ['git']), subprocess.TimeoutExpired(['git'], 3),
                        OSError('exec failed')):
            with self.subTest(failure=repr(failure)):
                selected = self.select([self.own / 'a.txt', self.own / 'b.txt'], failure, failing=self.own, times=1)
                self.assertIsNone(selected['gate'], selected)
                self.assertIn('target repository is unresolved', selected['error'])
                self.assertIn(str(self.own / 'a.txt'), selected['error'])

    def test_successful_lookup_after_a_failure_selects_the_gate(self):
        denied = self.select([self.own / 'a.txt'], subprocess.CalledProcessError(-9, ['git']), failing=self.own)
        self.assertIsNone(denied['gate'], denied)
        selected = resolver.select_task(str(self.ws), [str(self.own / 'a.txt')], session_id=SID)
        self.assertTrue(selected['gate'], selected)

    def test_git_entry_probe(self):
        self.assertTrue(resolver._git_entry_above(str(self.shared / 'missing' / 'x.txt')))
        self.assertFalse(resolver._git_entry_above(str(self.plain / 'x.txt')))
        denied = OSError(errno.EACCES, 'denied')
        with mock.patch.object(resolver.os, 'lstat', side_effect=denied):
            self.assertTrue(resolver._git_entry_above(str(self.plain / 'x.txt')))


if __name__ == '__main__':
    unittest.main(verbosity=2)
