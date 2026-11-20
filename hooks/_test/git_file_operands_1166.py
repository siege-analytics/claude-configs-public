#!/usr/bin/env python3
"""Git archive direct output and apply inspection semantics (#1166)."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import task_keyed_gates as fixture
ROOT = Path(__file__).resolve().parents[2]
q = shlex.quote


class GitFileOperands(unittest.TestCase):
    def setUp(self):
        self.f = fixture.Gates(); self.f.setUp(); self.addCleanup(self.f.tearDown)
        self.f.env.update(GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_SYSTEM='/dev/null', GIT_CONFIG_NOSYSTEM='1')
        os.environ.update({k: self.f.env[k] for k in ('GIT_CONFIG_GLOBAL', 'GIT_CONFIG_SYSTEM', 'GIT_CONFIG_NOSYSTEM')})
        self.source = self.f.a / 'tracked.txt'; self.source.write_text('one\n')
        self.git('add', 'a/tracked.txt')
        self.git('-c', 'user.name=fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture')
        self.patch = self.f.ws / 'change.patch'
        self.patch.write_text('diff --git a/a/tracked.txt b/a/tracked.txt\n--- a/a/tracked.txt\n+++ b/a/tracked.txt\n@@ -1 +1 @@\n-one\n+two\n')

    def git(self, *args):
        return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(self.f.repo), *args],
                              env=self.f.env, capture_output=True, text=True, check=True, timeout=15)

    def tasks(self):
        self.f.task('source1166', self.f.a)
        return self.f.task('output1166', self.f.b)

    def archive(self, options):
        return 'CCP_TASK_ID=output1166 git -C ' + q(str(self.f.repo)) + ' archive ' + options + ' HEAD'

    def shape(self, command):
        return fixture.r.action(command, str(self.f.repo))

    def test_archive_output_is_only_mutation_not_source_repository(self):
        self.tasks()
        for option in ['-o '+q(str(self.f.b/'one.tar')), '-o'+q(str(self.f.b/'two.tar')),
                       '--output='+q(str(self.f.b/'three.tar')), '--output '+q(str(self.f.b/'four.tar')),
                       '--format=tar -o '+q(str(self.f.b/'explicit.anything'))]:
            with self.subTest(option=option):
                command = self.archive(option); shape = self.shape(command)
                self.assertFalse(shape.get('error'), shape)
                self.assertFalse(shape['read_only']); self.assertEqual(len(shape['paths']), 1)
                self.assertTrue(shape['paths'][0].startswith(str(self.f.b)+'/'), shape)
                self.f.assertGate(0, command)

    def test_relative_output_uses_effective_git_directory(self):
        self.tasks()
        command = self.archive('--output=b/relative.tar')
        self.assertEqual(self.shape(command)['paths'], [str(self.f.b/'relative.tar')])
        self.f.assertGate(0, command)

    def test_stdout_archive_and_apply_inspection_need_no_mutation_task(self):
        for command in ['git -C '+q(str(self.f.repo))+' archive HEAD',
                        'git -C'+q(str(self.f.repo))+' --no-pager archive --format=tar HEAD',
                        'git -C '+q(str(self.f.repo))+' archive --list',
                        *['git -C '+q(str(self.f.repo))+' apply '+mode+' '+q(str(self.patch))
                          for mode in ['--check', '--stat', '--numstat', '--summary', '--check -p1', '--check --reverse']]]:
            with self.subTest(command=command):
                shape = self.shape(command); self.assertTrue(shape['read_only'], shape)
                self.assertEqual(shape['paths'], []); self.f.assertGate(0, command)

    def test_actual_apply_and_write_overrides_keep_repository_mutation(self):
        self.tasks()
        for flags in ['', '--apply', '--stat --apply', '--check --apply', '--apply --check',
                      '--check --build-fake-ancestor='+str(self.f.b/'fake-index')]:
            command = 'CCP_TASK_ID=output1166 git -C '+q(str(self.f.repo))+' apply '+flags+' '+q(str(self.patch))
            with self.subTest(flags=flags):
                shape = self.shape(command)
                self.assertFalse(shape['read_only'], shape)
                self.assertIn(str(self.f.repo), shape['paths'])
                self.f.assertGate(2, command)

    def test_unknown_external_archive_selections_stay_guarded(self):
        self.tasks()
        for options in ['--format=zip -o '+str(self.f.b/'x.tar'),
                        '--format=tar.gz -o '+str(self.f.b/'x.tar'),
                        '--format=custom -o '+str(self.f.b/'x.tar'),
                        '--remote=foreign.example/repo -o '+str(self.f.b/'x.tar'),
                        '--exec=program -o '+str(self.f.b/'x.tar'),
                        '--future-option -o '+str(self.f.b/'x.tar'),
                        '-o '+str(self.f.b/'ambiguous.name.tar'),
                        '-o '+str(self.f.b/'x.zip'),
                        '-o '+str(self.f.b/'a.tar')+' -o '+str(self.f.b/'b.tar')]:
            with self.subTest(options=options):
                shape = self.shape(self.archive(options)); self.assertFalse(shape['read_only'], shape)
                self.f.assertGate(2, self.archive(options))

    def test_foreign_outputs_symlinks_and_hardlinks_do_not_borrow_scope(self):
        self.tasks(); foreign = self.f.a/'foreign.txt'; foreign.write_text('preserved\n')
        symlink = self.f.b/'symlink.tar'; symlink.symlink_to(foreign)
        hardlink = self.f.b/'hardlink.tar'; os.link(foreign, hardlink)
        loop = self.f.b/'loop.tar'; loop.symlink_to(loop.name)
        for output in [self.f.a/'foreign.tar', symlink, hardlink, loop]:
            with self.subTest(output=output):
                result = self.f.assertGate(2, self.archive('-o '+q(str(output))))
                if output == loop:
                    self.assertIn('cannot inspect archive output', result.stdout + result.stderr)
        self.assertEqual(foreign.read_text(), 'preserved\n')

    def test_compounds_and_stdout_redirection_keep_their_write_targets(self):
        self.tasks()
        plain = 'git -C '+q(str(self.f.repo))+' archive --format=tar HEAD'
        command = plain+' > '+q(str(self.f.b/'redirect.tar'))
        self.assertEqual(self.shape(command)['paths'], [str(self.f.b/'redirect.tar')])
        self.f.assertGate(0, 'CCP_TASK_ID=output1166 '+command)
        self.f.assertGate(2, 'CCP_TASK_ID=output1166 '+plain+' > '+q(str(self.f.a/'foreign.tar')))
        self.f.assertGate(2, self.archive('-o '+q(str(self.f.b/'own.tar')))+' && touch '+q(str(self.f.a/'foreign.txt')))

    def test_actual_git_effects_match_the_direct_operand_model(self):
        self.tasks(); output = self.f.b/'actual.tar'; before = self.source.read_bytes()
        self.f.assertGate(0, self.archive('-o '+q(str(output))))
        self.git('archive', '-o', str(output), 'HEAD')
        with tarfile.open(output) as archive:
            self.assertEqual(archive.extractfile('a/tracked.txt').read(), before)
        self.assertEqual(self.source.read_bytes(), before)
        for mode in ['--check', '--stat', '--numstat', '--summary']:
            self.git('apply', mode, str(self.patch)); self.assertEqual(self.source.read_bytes(), before)
        self.git('apply', str(self.patch)); self.assertEqual(self.source.read_text(), 'two\n')

    def test_full_configured_chain_accepts_output_only_and_denies_foreign(self):
        self.tasks()
        hooks = [ROOT/h['command'].split('/claude-configs-public/',1)[1]
                 for group in json.loads((ROOT/'hooks/settings-snippet.json').read_text())['hooks']['PreToolUse']
                 if group.get('matcher')=='Bash' for h in group['hooks']]
        self.assertEqual(len(hooks), 16)
        for output, allowed in [(self.f.b/'chain.tar', True), (self.f.a/'foreign.tar', False)]:
            command = self.archive('-o '+q(str(output)))
            payload = fixture.craft_payload(tool_name='Bash', cwd=str(self.f.repo), tool_input={'command':command})
            results = {h.name:subprocess.run(['bash',str(h)],input=json.dumps(payload),env=self.f.env,
                       cwd=self.f.repo,text=True,capture_output=True,timeout=15) for h in hooks}
            if allowed:
                self.assertEqual({name:r.returncode for name,r in results.items()}, {h.name:0 for h in hooks},
                                 {name:r.stdout+r.stderr for name,r in results.items()if r.returncode})
            else:
                self.assertEqual(results['universal-mutation-gate.sh'].returncode,2)


if __name__ == '__main__':
    unittest.main()
