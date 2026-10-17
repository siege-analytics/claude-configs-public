#!/usr/bin/env python3
"""Actual destination ref effects, consumer registration and failed-probe tests."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
ZERO = '0' * 40
VALID = 'docs: fixture #845\n\nReview-Tier: A\nSelf-Review: fixture checked'

class NativePush(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='native-push-845-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.env = dict(os.environ, HOME=str(self.base / 'home'), GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_CONFIG_NOSYSTEM='1', PYTHONDONTWRITEBYTECODE='1')
        self.env.pop('GIT_DIR', None)
        self.env.pop('GIT_WORK_TREE', None)
        binary = self.base / 'bin'; binary.mkdir()
        (binary / 'python3').symlink_to(sys.executable)
        self.env['PATH'] = str(binary) + os.pathsep + self.env['PATH']
        # Copy generated package outside the source repository, including odd paths.
        self.package = self.base / "package with 'quotes' & spaces"
        shutil.copytree(ROOT / 'dist/craft-agent', self.package)
        self.repo = self.base / 'consumer'; self.repo.mkdir()
        self.run_cmd(['git', 'init', '-q', '-b', 'main'])
        self.run_cmd(['git', 'config', 'user.name', 'Fixture'])
        self.run_cmd(['git', 'config', 'user.email', 'fixture@example.invalid'])
        self.remote = self.base / 'destination.git'
        self.run_cmd(['git', 'init', '-q', '--bare', str(self.remote)])
        self.run_cmd(['git', 'remote', 'add', 'origin', str(self.remote)])
        self.commit('historical.md', 'pre-enforcement baseline')
        self.run_cmd(['git', 'push', '-q', '--no-verify', 'origin', 'HEAD:main'])
        self.baseline = self.git('rev-parse', 'HEAD')
        self.run_cmd(['git', 'checkout', '-q', '-b', 'feature'])
        self.run_cmd(['git', 'config', 'core.hooksPath', str(self.package / '.githooks')])

    def run_cmd(self, argv, *, ok=True, input=None, cwd=None):
        result = subprocess.run(argv, cwd=cwd or self.repo, env=self.env, input=input,
                                capture_output=True, text=True, timeout=90)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def git(self, *argv):
        return self.run_cmd(['git', *argv]).stdout.strip()

    def commit(self, file='next.md', message=VALID):
        (self.repo / file).write_text(message + '\n')
        self.git('add', '--force', file)
        self.git('-c', 'core.hooksPath=/dev/null', 'commit', '-q', '-m', message)
        return self.git('rev-parse', 'HEAD')

    def refs(self):
        return self.git('ls-remote', '--heads', str(self.remote))

    def push(self, *args, deny=False):
        before = self.refs()
        result = self.run_cmd(['git', 'push', 'origin', *(args or ('HEAD:feature',))], ok=not deny)
        if deny:
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(self.refs(), before, result.stderr)
            self.assertIn('pre-push', result.stderr)
        return result

    def install(self, *args, ok=True):
        return self.run_cmd(['bash', str(ROOT / 'bin/install-hooks.sh'), '--workspace', str(self.repo),
                             '--hooks-root', str(self.package), *map(str, args)], ok=ok)

    def bad_interior(self):
        self.commit('probe.py', 'feat: invalid interior #845\n\nReview-Tier: B\nSelf-Review: missing source')
        self.commit('valid-head.md')

    def test_valid_range_then_promotion_preserves_published_history(self):
        head = self.commit(); self.push()
        self.push('HEAD:second')
        self.assertIn(head + '\trefs/heads/second', self.refs())

    def test_remote_named_selected_is_not_a_dispatch_option(self):
        self.git('remote', 'add', '--', '--selected', str(self.remote))
        head = self.commit()
        self.run_cmd(['git', 'push', '--', '--selected', 'HEAD:feature'])
        self.assertIn(head + '\trefs/heads/feature', self.refs())

    def test_bad_interior_and_repaired_push(self):
        self.bad_interior(); result = self.push(deny=True)
        self.assertIn('Self-Review-Source', result.stderr)
        self.git('checkout', '-q', '-B', 'repaired', self.baseline)
        self.commit('repaired.md'); self.push()

    def test_other_remote_and_fabricated_tracking_do_not_hide_bad_commit(self):
        self.bad_interior()
        other = self.base / 'other.git'
        self.git('init', '-q', '--bare', str(other))
        self.git('remote', 'add', 'other', str(other))
        self.git('push', '-q', '--no-verify', 'other', 'HEAD:feature')
        self.git('update-ref', 'refs/remotes/origin/fabricated', self.git('rev-parse', 'HEAD'))
        self.push(deny=True)

    def test_multi_ref_push_is_rejected_without_partial_remote_effect(self):
        good = self.commit(); self.git('branch', 'good', good)
        self.bad_interior(); self.push('good:good', 'HEAD:bad', deny=True)

    def test_force_update_checks_new_history(self):
        self.commit(); self.push()
        self.git('checkout', '-q', '-B', 'replacement', self.baseline)
        self.bad_interior(); self.push('--force', 'HEAD:feature', deny=True)

    def test_deletion_is_allowed(self):
        self.commit(); self.push(); self.push(':feature')
        self.assertNotIn('refs/heads/feature', self.refs())

    def test_missing_remote_object_fails_closed(self):
        other = self.base / 'other'; self.git('clone', '-q', str(self.remote), str(other))
        for key, value in [('user.name', 'Fixture'), ('user.email', 'fixture@example.invalid')]:
            self.run_cmd(['git', 'config', key, value], cwd=other)
        self.run_cmd(['git', 'checkout', '-q', '-b', 'unknown', 'origin/main'], cwd=other)
        self.run_cmd(['git', '-c', 'core.hooksPath=/dev/null', 'commit', '--allow-empty', '-qm', VALID], cwd=other)
        self.run_cmd(['git', 'push', '-q', '--no-verify', 'origin', 'HEAD:unknown'], cwd=other)
        self.commit(); result = self.push(deny=True)
        self.assertIn('fetch this destination and retry', result.stderr)

    def test_invalid_update_protocol_and_missing_object_return_incomplete(self):
        hook = str(self.package / 'hooks/git/pre-push-self-review.sh')
        head = self.git('rev-parse', 'HEAD')
        for line in ['invalid', '{"tool_input":{}}\n', f'refs/heads/f {head} refs/heads/f garbage\n',
                     f'refs/heads/f {"1"*40} refs/heads/f {ZERO}\n']:
            result = self.run_cmd(['bash', hook], ok=False, input=line)
            self.assertEqual(result.returncode, 2, result.stderr)

    def test_missing_dependencies_and_nonexecutable_range_deny(self):
        self.commit()
        for relative in ['bin/review-risk.py', 'catalog/review-risk-policy.json', 'hooks/git/pre-push-self-review.sh']:
            path = self.package / relative; saved = path.with_name(path.name + '.saved')
            path.rename(saved)
            try: self.push(deny=True)
            finally: saved.rename(path)
        hook = self.package / 'hooks/git/pre-push-self-review.sh'; hook.chmod(0o644)
        self.push(deny=True)

    def test_settings_only_does_not_register_git_and_preserves_project_settings(self):
        self.git('config', '--unset', 'core.hooksPath')
        settings = self.repo / '.claude/settings.json'; settings.parent.mkdir()
        original = {'model': 'project-choice', 'permissions': {'deny': ['example']},
                    'hooks': {'UserPromptSubmit': [{'hooks': [{'type': 'command', 'command': 'project-helper'}]}]}}
        settings.write_text(json.dumps(original))
        self.install()
        first = settings.read_bytes(); merged = json.loads(first)
        self.assertEqual(merged['permissions'], original['permissions'])
        self.assertEqual(merged['model'], 'project-choice')
        self.assertEqual(merged['hooks']['UserPromptSubmit'][0]['hooks'][0]['command'], 'project-helper')
        self.assertEqual(self.run_cmd(['git', 'config', '--get', 'core.hooksPath'], ok=False).returncode, 1)
        for groups in merged['hooks'].values():
            for group in groups:
                for hook in group['hooks']:
                    if hook['command'] != 'project-helper':
                        self.assertEqual(len(shlex.split(hook['command'])), 1)
        self.install(); self.assertEqual(first, settings.read_bytes())

    def test_explicit_consumer_registration_permits_real_push(self):
        self.git('config', '--unset', 'core.hooksPath')
        self.install('--git-repo', self.repo)
        self.assertEqual(Path(self.git('config', '--get', 'core.hooksPath')), (self.package / '.githooks').resolve())
        self.commit(); self.push()

    def test_invalid_registration_is_preflight_without_settings_mutation(self):
        settings = self.repo / '.claude/settings.json'; settings.parent.mkdir()
        settings.write_text('{"model":"keep me"}\n'); before = settings.read_bytes()
        sub = self.repo / 'sub'; sub.mkdir()
        for target in [sub, self.base / 'missing']:
            result = self.install('--git-repo', target, ok=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(before, settings.read_bytes())
        self.git('config', 'core.hooksPath', 'project-hooks')
        self.assertNotEqual(self.install('--git-repo', self.repo, ok=False).returncode, 0)
        self.assertEqual(self.git('config', '--get', 'core.hooksPath'), 'project-hooks')
        self.assertEqual(before, settings.read_bytes())

    def test_existing_hook_and_settings_conflicts_are_not_overwritten(self):
        self.git('config', '--unset', 'core.hooksPath')
        prior = self.repo / '.git/hooks/pre-push'; prior.write_text('#!/bin/sh\nexit 0\n'); prior.chmod(0o755)
        self.assertNotEqual(self.install('--git-repo', self.repo, ok=False).returncode, 0)
        self.assertFalse((self.repo / '.claude/settings.json').exists())
        settings = self.repo / '.claude/settings.json'; settings.parent.mkdir()
        settings.write_text(json.dumps({'hooks': {'UserPromptSubmit': [{'hooks': [{'type': 'command', 'command': '/operator/inject-resolver.sh'}]}]}}))
        before = settings.read_bytes()
        self.assertNotEqual(self.install(ok=False).returncode, 0)
        self.assertEqual(before, settings.read_bytes())

    def test_verifier_rejects_noop_missing_and_foreign_native_registration(self):
        settings = self.package / '.claude/settings.json'; settings.parent.mkdir(exist_ok=True)
        command = shlex.quote(str(self.package / 'hooks/resolver/ca-enforcement-gate.sh'))
        settings.write_text(json.dumps({'hooks': {'UserPromptSubmit': [{'hooks': [{'type': 'command', 'command': command}]}]}}))
        # The verifier targets an installed workspace: materialize its root mounts.
        shutil.copy2(self.package / 'skills/KERNEL.md', self.package / 'KERNEL.md')
        shutil.copy2(ROOT / 'dist/RULES_BUNDLE.md', self.package / 'RULES_BUNDLE.md')
        shutil.copy2(ROOT / 'RESOLVER.md', self.package / 'RESOLVER.md')
        (self.package / 'CLAUDE.md').symlink_to('KERNEL.md')
        argv = ['bash', str(ROOT / 'bin/verify-enforcement.sh'), '--target', str(self.package), '--git-repo', str(self.repo)]
        self.run_cmd(argv)
        for relative in ['.githooks/pre-push', 'hooks/git/pre-push-self-review.sh']:
            path = self.package / relative; original = path.read_bytes()
            try:
                path.write_text('#!/bin/sh\nexit 0\n')
                result = self.run_cmd(argv, ok=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('accepted an invalid interior commit', result.stderr)
            finally:
                path.write_bytes(original)
        wrapper = self.package / '.githooks/pre-push'
        wrapper.chmod(0o644)
        self.assertNotEqual(self.run_cmd(argv, ok=False).returncode, 0)
        wrapper.chmod(0o755)
        self.git('config', 'core.hooksPath', 'foreign-hooks')
        result = self.run_cmd(argv, ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('outside installed native hooks', result.stderr)

    def test_direct_clone_default_and_target_file_only_are_distinct(self):
        # Exercise the installer's own root using only a disposable copied tree.
        script = self.package / 'bin/install-hooks.sh'
        shutil.copy2(ROOT / 'bin/install-hooks.sh', script)
        self.run_cmd(['git', 'init', '-q', str(self.package)])
        target = self.base / 'external-settings.json'
        self.run_cmd(['bash', str(script), '--target-file', str(target)])
        result = self.run_cmd(['git', '-C', str(self.package), 'config', '--local', '--get', 'core.hooksPath'], ok=False)
        self.assertEqual(result.returncode, 1)
        self.run_cmd(['bash', str(script)])
        self.assertEqual(self.run_cmd(['git', '-C', str(self.package), 'config', '--local', '--get', 'core.hooksPath']).stdout.strip(), '.githooks')

    def test_native_hook_is_absent_from_tool_json_registration(self):
        for source in [ROOT / '.claude/settings.json', ROOT / 'hooks/settings-snippet.json']:
            self.assertNotIn('pre-push-self-review.sh', source.read_text())
        self.assertEqual((ROOT / '.githooks/pre-push').read_bytes(), (self.package / '.githooks/pre-push').read_bytes())

if __name__ == '__main__':
    unittest.main()
