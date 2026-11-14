#!/usr/bin/env python3
"""Own-session data/ scratch floor in a truthful non-Git workspace (#1152).

Root reproduced (issuecomment-6785389467): with a non-Git workspace as
repo_root and a narrowly scoped own run-data directory, the same command
classified B before the directory existed and C after it was created, only
because `git ls-files` cannot list a directory outside every repository.

The floor must not depend on directory existence. It stays narrow: only
untracked own-data scratch qualifies; high-risk path patterns, other
directories in the non-Git workspace, another session's data, symlinked or
hardlinked targets, an unbound session and unproven Git state keep their
classification. There is no command-specific (Node) exemption.
"""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import task_keyed_gates as fixture  # noqa: E402

q = shlex.quote


class NonGitOwnDataFloor(unittest.TestCase):
    def setUp(self):
        original = tempfile.TemporaryDirectory
        # The default fixture lives inside this repository's checkout; a truthful
        # non-Git workspace must live outside every repository.
        with patch.object(fixture.tempfile, 'TemporaryDirectory',
                          side_effect=lambda **kw: original(prefix=kw['prefix'], dir=os.path.realpath(tempfile.gettempdir()))):
            self.f = fixture.Gates()
            self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.ws = self.f.ws
        probe = subprocess.run(['git', '-C', str(self.ws), 'rev-parse', '--git-dir'],
                               capture_output=True, text=True, env={**os.environ, 'LC_ALL': 'C'})
        if probe.returncode == 0:
            self.skipTest('system temporary directory is inside a Git repository')
        self.data = self.ws / 'sessions/one/data/run'
        self.helper = self.ws / 'tools/helper.js'
        self.helper.parent.mkdir(parents=True)
        self.helper.write_text('// helper\n')

    def task(self, *scopes, tier='A', identity='health1152'):
        gate = self.f.task(identity, scopes[0], artifacts=False)
        for p in gate.glob('*.json'):
            data = json.loads(p.read_text())
            data.update(repo_root=str(self.ws), scope_paths=[str(s) for s in scopes], tier=tier)
            fixture.write(p, data)
        return gate

    def tier(self, command, cwd):
        payload = fixture.craft_payload(tool_name='Bash', cwd=str(cwd), tool_input={'command': command})
        result = fixture.r.resolve_action(str(self.ws), payload)
        self.assertTrue(result.get('gate'), result)
        return result['tier']

    def both_states(self, command, cwd, directory):
        """Floors before and after the same directory is created."""
        before = self.tier(command, cwd)
        directory.mkdir(parents=True, exist_ok=True)
        after = self.tier(command, cwd)
        return before, after

    # --- positive: existence-independent ---------------------------------

    def test_pure_scratch_floor_is_a_before_and_after_mkdir(self):
        self.task(self.data)
        before, after = self.both_states('tar -xzf src.tar.gz', self.data, self.data)
        self.assertEqual((before['floor'], after['floor']), ('A', 'A'), (before, after))
        self.assertTrue(any('own-session data scratch' in r for r in after['reasons']), after)

    def test_root_helper_shape_is_b_from_the_helper_before_and_after_mkdir(self):
        self.task(self.data, self.helper)
        command = f'node {q(str(self.helper))} decide {q(str(self.data / "facts.json"))} {q(str(self.data / "ledger.json"))}'
        before, after = self.both_states(command, self.data, self.data)
        self.assertEqual((before['floor'], after['floor']), ('B', 'B'), (before, after))
        for verdict in (before, after):
            self.assertTrue(any('tools/helper.js' in r for r in verdict['reasons']), verdict)
            self.assertFalse(any('cannot list files' in r for r in verdict['reasons']), verdict)

    # --- negatives ---------------------------------------------------------

    # Plain own-data writes (printf/tee/touch) are own-session lifecycle writes
    # with no gate at all, so these negatives use an unmodelled command, which
    # is gated and tiered.

    def helper_write(self, name):
        return f'node {q(str(self.helper))} write {q(str(self.data / name))}'

    def test_high_risk_name_under_own_data_keeps_c(self):
        self.task(self.data, self.helper)
        self.data.mkdir(parents=True)
        tier = self.tier(self.helper_write('credentials.json'), self.data)
        self.assertEqual(tier['floor'], 'C', tier)
        self.assertTrue(any('credentials.json' in r for r in tier['reasons']), tier)

    def test_high_risk_name_under_own_data_keeps_c_in_a_git_workspace(self):
        # In a Git workspace `ls-files` succeeds with an empty listing, so the
        # scratch floor must still defer to high-risk path patterns.
        subprocess.run(['git', 'init', '-q', str(self.ws)], check=True)
        self.task(self.data, self.helper)
        self.data.mkdir(parents=True)
        tier = self.tier(self.helper_write('credentials.json'), self.data)
        self.assertEqual(tier['floor'], 'C', tier)
        plain = self.tier(self.helper_write('notes'), self.data)
        self.assertEqual(plain['floor'], 'B', plain)  # from tools/helper.js only

    def test_existing_directory_outside_data_keeps_c(self):
        other = self.ws / 'other'
        self.task(other)
        before, after = self.both_states('tar -xzf src.tar.gz', other, other)
        self.assertEqual(after['floor'], 'C', after)
        self.assertTrue(any('cannot list files' in r for r in after['reasons']), after)

    def test_another_sessions_data_is_not_own_scratch(self):
        foreign = self.ws / 'sessions/two/data/run'
        self.task(foreign)
        before, after = self.both_states('tar -xzf src.tar.gz', foreign, foreign)
        self.assertNotEqual(before['floor'], 'A', before)
        self.assertEqual(after['floor'], 'C', after)

    def test_symlinked_data_directory_is_not_own_scratch(self):
        real = self.ws / 'elsewhere/data'
        (real / 'run').mkdir(parents=True)
        (self.ws / 'sessions/one/data').rmdir() if (self.ws / 'sessions/one/data').is_dir() else None
        os.symlink(real, self.ws / 'sessions/one/data')
        self.task(real / 'run')
        tier = self.tier('tar -xzf src.tar.gz', real / 'run')
        self.assertEqual(tier['floor'], 'C', tier)

    def test_hardlinked_file_under_data_is_not_scratch(self):
        self.task(self.data)
        self.data.mkdir(parents=True)
        outside = self.ws / 'tools/alias-source'
        outside.write_text('x\n')
        os.link(outside, self.data / 'alias')
        tier = self.tier(f'printf x > {q(str(self.data / "alias"))}', self.ws)
        self.assertNotEqual(tier['floor'], 'A', tier)

    def test_nested_clone_under_data_in_a_non_git_workspace_stays_strict(self):
        # A workspace-rooted gate cannot prove that content inside a nested
        # clone is untracked: Git does not report "not a git repository" there.
        clone = self.data / 'c'
        (clone / 'hooks/lib').mkdir(parents=True)
        subprocess.run(['git', 'init', '-q', str(clone)], check=True)
        target = clone / 'hooks/lib/task_actions.py'
        target.write_text('x = 1\n')
        subprocess.run(['git', '-C', str(clone), 'add', 'hooks/lib/task_actions.py'], check=True)
        gate = {'repo_root': str(self.ws), 'tier': 'A'}
        tier = fixture.r.task_tier(gate, [str(target)], f'printf x > {q(str(target))}', str(self.ws),
                                   scratch_root=fixture.r.own_session_data_root(str(self.ws)))
        self.assertEqual(tier['floor'], 'C', tier)
        self.assertFalse(fixture.r._outside_git(str(target)))
        self.assertTrue(fixture.r._outside_git(str(self.ws)))

    def direct_tier(self, target, command):
        gate = {'repo_root': str(self.ws), 'tier': 'A'}
        return fixture.r.task_tier(gate, [str(target)], command, str(self.ws),
                                   scratch_root=fixture.r.own_session_data_root(str(self.ws)))

    def test_dangling_gitdir_file_cannot_spoof_outside_git(self):
        # A `.git` file with a dangling gitdir makes Git print
        # "not a git repository: (null)" for a path inside that repository.
        nested = self.data / 'c'
        (nested / 'hooks/lib').mkdir(parents=True)
        (nested / '.git').write_text('gitdir: /nonexistent/ccp1152\n')
        target = nested / 'hooks/lib/task_actions.py'
        target.write_text('x = 1\n')
        self.assertFalse(fixture.r._outside_git(str(target)))
        self.assertTrue(fixture.r._outside_git(str(self.ws)))
        tier = self.direct_tier(target, f'printf x > {q(str(target))}')
        self.assertEqual(tier['floor'], 'C', tier)

    def test_directory_target_with_nested_repository_gets_no_floor(self):
        subprocess.run(['git', 'init', '-q', str(self.ws)], check=True)
        self.data.mkdir(parents=True)
        command = f'tar -xzf src.tar.gz -C {q(str(self.data))}'
        plain = self.direct_tier(self.data, command)
        self.assertEqual(plain['floor'], 'A', plain)  # control: untracked scratch directory
        subprocess.run(['git', 'init', '-q', str(self.data / 'c')], check=True)
        nested = self.direct_tier(self.data, command)
        self.assertNotEqual(nested['floor'], 'A', nested)
        dangling = self.data / 'd'
        dangling.mkdir()
        (dangling / '.git').write_text('gitdir: /nonexistent/ccp1152\n')
        self.assertNotEqual(self.direct_tier(dangling, f'tar -xzf src.tar.gz -C {q(str(dangling))}')['floor'], 'A')

    def test_inherited_git_dir_cannot_empty_the_scratch_listing(self):
        subprocess.run(['git', 'init', '-q', str(self.ws)], check=True)
        self.data.mkdir(parents=True)
        (self.data / 'tool.py').write_text('x = 1\n')
        subprocess.run(['git', '-C', str(self.ws), 'add', '-f', 'sessions/one/data/run/tool.py'], check=True)
        other = self.ws / 'other-repo'
        subprocess.run(['git', 'init', '-q', str(other)], check=True)
        command = f'tar -xzf src.tar.gz -C {q(str(self.data))}'
        with patch.dict(os.environ, {'GIT_DIR': str(other / '.git')}):
            tier = self.direct_tier(self.data, command)
        self.assertNotEqual(tier['floor'], 'A', tier)

    def test_redirected_git_cannot_hide_a_tracked_own_data_file(self):
        # Codex review issuecomment-6785744722: GIT_DIR and GIT_WORK_TREE pointing
        # at an empty foreign repository must not make a tracked file look untracked.
        subprocess.run(['git', 'init', '-q', str(self.ws)], check=True)
        self.data.mkdir(parents=True)
        tool = self.data / 'tool.py'
        tool.write_text('x = 1\n')
        subprocess.run(['git', '-C', str(self.ws), 'add', '-f', 'sessions/one/data/run/tool.py'], check=True)
        empty = self.ws / 'empty-foreign'
        subprocess.run(['git', 'init', '-q', str(empty)], check=True)
        command = f'printf x > {q(str(tool))}'
        normal = self.direct_tier(tool, command)
        self.assertEqual(normal['floor'], 'B', normal)
        with patch.dict(os.environ, {'GIT_DIR': str(empty / '.git'), 'GIT_WORK_TREE': str(empty)}):
            redirected = self.direct_tier(tool, command)
        self.assertEqual(redirected['floor'], 'B', redirected)
        self.assertFalse(any('own-session data scratch' in r for r in redirected['reasons']), redirected)

    def test_unmodelled_command_cwd_in_own_data_is_b_not_scratch(self):
        # S1-2: the cwd of an unmodelled command is unknown writes, never A,
        # and never C merely because a non-Git directory cannot be listed.
        self.task(self.data)
        before, after = self.both_states('make install', self.data, self.data)
        self.assertEqual((before['floor'], after['floor']), ('B', 'B'), (before, after))
        self.assertFalse(any('own-session data scratch' in r for r in after['reasons']), after)

    def test_unbound_session_identity_gets_no_floor(self):
        self.task(self.data)
        self.data.mkdir(parents=True)
        payload = fixture.craft_payload(tool_name='Bash', cwd=str(self.data), tool_input={'command': 'tar -xzf src.tar.gz'})
        selection = fixture.r.resolve_action(str(self.ws), payload)
        gate = selection['gate']
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(fixture.r.own_session_data_root(str(self.ws)), '')
            tier = fixture.r.task_tier(gate['data'], [str(self.data)], 'tar -xzf src.tar.gz', str(self.data), scratch_root='')
        self.assertEqual(tier['floor'], 'C', tier)

    def test_unproven_git_state_fails_closed(self):
        self.task(self.data)
        self.data.mkdir(parents=True)
        # Without a usable git executable nothing proves the workspace is outside
        # every repository, so classification keeps failing closed.
        with patch.dict(os.environ, {'PATH': str(self.ws / 'no-git-here')}):
            tier = self.tier('tar -xzf src.tar.gz', self.data)
        self.assertEqual(tier['floor'], 'C', tier)


if __name__ == '__main__':
    unittest.main()
