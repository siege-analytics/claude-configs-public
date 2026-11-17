#!/usr/bin/env python3
"""Own scratch and Git input operands, using real hooks and disposable files."""
import importlib.util
import os
from pathlib import Path
import shlex
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('task_fixture', ROOT / 'hooks/_test/task_keyed_gates.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class OwnOperands(unittest.TestCase):
    def setUp(self):
        self.f = fixture.Gates()
        self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.own = Path(self.f.env['CRAFT_SESSION_DIR'])
        self.data = self.own / 'data'; self.data.mkdir()
        self.plans = self.own / 'plans'; self.plans.mkdir()
        self.foreign = self.f.ws / 'sessions/two/data'; self.foreign.mkdir(parents=True)
        self.source = self.foreign / 'notes.txt'; self.source.write_text('read-only predecessor notes\n')

    def command(self, *words):
        return shlex.join([str(word) for word in words])

    def test_copy_to_own_data_directory_matches_write_and_real_effect(self):
        self.f.assertGate(0, tool='Write', path=self.data / self.source.name)
        command = self.command('cp', '-p', self.source, self.data)
        self.f.assertGate(0, command)
        subprocess.run(['cp', '-p', str(self.source), str(self.data)], check=True, timeout=10)
        self.assertEqual((self.data / self.source.name).read_text(), self.source.read_text())
        self.assertNotEqual((self.data / self.source.name).stat().st_ino, self.source.stat().st_ino)

    def test_recursive_predecessor_copy_into_own_data(self):
        folder = self.foreign / 'handoff'; folder.mkdir()
        (folder / 'next.txt').write_text('next work\n')
        self.f.assertGate(0, self.command('cp', '-pR', folder, self.data))
        subprocess.run(['cp', '-pR', str(folder), str(self.data)], check=True, timeout=10)
        self.assertEqual((self.data / 'handoff/next.txt').read_text(), 'next work\n')

    def test_mkdir_modes_and_own_mv_keep_lifecycle_semantics(self):
        self.f.assertGate(0, self.command('mkdir', '-p', '-m', '750', self.data / 'nested'))
        local = self.data / 'local'; local.write_text('own\n')
        self.f.assertGate(0, self.command('mv', local, self.plans))
        self.f.assertGate(2, self.command('mv', self.source, self.data))
        self.assertTrue(self.source.exists())

    def test_cross_session_destination_and_aliases_stay_denied(self):
        own_source = self.data / 'out'; own_source.write_text('own\n')
        self.f.assertGate(2, self.command('cp', own_source, self.foreign))
        alias = self.data / 'alias'; alias.symlink_to(self.foreign, target_is_directory=True)
        self.f.assertGate(2, self.command('cp', self.source, alias))
        dest = self.data / self.source.name; dest.symlink_to(self.source)
        self.f.assertGate(2, self.command('cp', self.source, self.data))
        dest.unlink(); os.link(self.source, dest)
        self.f.assertGate(2, self.command('cp', self.source, self.data))
        self.assertEqual(self.source.read_text(), 'read-only predecessor notes\n')

    def test_recursive_destination_links_are_not_hidden_by_directory_operand(self):
        folder = self.foreign / 'folder'; folder.mkdir(); (folder / 'leaf').write_text('new\n')
        dest = self.data / 'folder'; dest.mkdir()
        (dest / 'leaf').symlink_to(self.source)
        self.f.assertGate(2, self.command('cp', '-pR', folder, self.data))
        (dest / 'leaf').unlink(); os.link(self.source, dest / 'leaf')
        self.f.assertGate(2, self.command('cp', '-pR', folder, self.data))

    def test_link_copy_and_preserved_symlink_source_keep_source_authority(self):
        self.f.assertGate(2, self.command('cp', '-l', self.source, self.data / 'linked'))
        link = self.foreign / 'alias'; link.symlink_to(self.source)
        self.f.assertGate(2, self.command('cp', '-P', link, self.data))
        self.f.assertGate(0, self.command('cp', '--reflink=auto', self.source, self.data / 'copy'))

    def test_no_target_directory_short_cluster_cannot_hide_merge_alias(self):
        folder = self.foreign / 'folder'; folder.mkdir(); (folder / 'leaf').write_text('new\n')
        (self.data / 'leaf').symlink_to(self.source)
        self.f.assertGate(2, self.command('cp', '-pRT', folder, self.data))

    def test_commit_message_file_is_read_but_git_still_needs_its_owner(self):
        message = self.data / 'msg.txt'; message.write_text('fix: scratch input\n\nRefs #1166\n')
        command = self.command('git', '-C', self.f.repo, 'commit', '-F', message)
        self.f.assertGate(2, command)
        self.f.task('o/r#1166', self.f.repo, artifacts=True)
        self.f.assertGate(0, command)
        self.f.assertGate(0, self.command('git', '-C', self.f.repo, 'commit', '--file=' + str(message)))
        shape = fixture.r.action(command, str(self.f.ws))
        self.assertNotIn(str(message), shape['paths'])
        self.assertIn(str(self.f.repo), shape['paths'])

    def test_commit_cleanup_names_supported_split_without_weakening_message_guard(self):
        message = self.data / 'msg.txt'; message.write_text('fix: input\n\nRefs #1166\n')
        self.f.task('o/r#1166', self.f.repo, artifacts=True)
        commit = self.command('git', '-C', self.f.repo, 'commit', '--amend', '-F', message)
        result = self.f.assertGate(2, commit + ' && ' + self.command('rm', message))
        self.assertIn('separate', result.stderr)
        self.assertIn('commit', result.stderr)
        self.f.assertGate(0, commit)
        self.f.assertGate(0, self.command('rm', message))
        self.f.assertGate(2, self.command('rm', self.source))


if __name__ == '__main__':
    unittest.main()
