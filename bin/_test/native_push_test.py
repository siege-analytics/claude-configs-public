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

    def test_option_like_native_names_and_message_paths_remain_data(self):
        aliases = ('--help', '--selected', '--binding', '--command', '-h', '--', '\u540d\u524d')
        for index, alias in enumerate(aliases):
            self.git('remote', 'add', '--', alias, str(self.remote))
            head = self.commit(f'alias-{index}.md')
            self.run_cmd(['git', 'push', '--', alias, 'HEAD:feature'])
            self.assertIn(head + '\trefs/heads/feature', self.refs())
        for name in (*aliases, 'space name'):
            path = self.repo / name
            path.write_text(VALID)
            hook = str(self.package / '.githooks/commit-msg')
            self.run_cmd([hook, name])
            path.write_text('Missing ticket and review')
            self.assertNotEqual(self.run_cmd([hook, name], ok=False).returncode, 0)
        self.bad_interior()
        for alias in (*aliases, 'origin'):
            before = self.refs()
            result = self.run_cmd(['git', 'push', '--', alias, 'HEAD:release'], ok=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(self.refs(), before)

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
        alias = self.base / 'native-hook-alias'
        alias.symlink_to(self.package / 'hooks/git/pre-push-self-review.sh')
        original = {'model': 'project-choice', 'permissions': {'deny': ['example']},
                    'hooks': {
                        'UserPromptSubmit': [{'hooks': [
                            {'type': 'command', 'command': 'project-helper'},
                            {'type': 'prompt', 'prompt': 'operator prompt hook'},
                        ]}],
                        'PreToolUse': [{'matcher': 'Bash', 'hooks': [
                            {'type': 'command', 'command': '/old/package/hooks/git/pre-push-self-review.sh'},
                            {'type': 'command', 'command': 'hooks/git/pre-push-self-review.sh'},
                            {'type': 'command', 'command': str(alias)},
                            {'type': 'command', 'command': 'operator-bash-helper'},
                            {'type': 'command', 'command': '/operator/pre-push-self-review.sh'},
                        ]}],
                    }}
        settings.write_text(json.dumps(original))
        result = self.install()
        self.assertEqual(result.stdout.count('Retired native Git hook from Claude PreToolUse:'), 2)
        first = settings.read_bytes(); merged = json.loads(first)
        self.assertEqual(merged['permissions'], original['permissions'])
        self.assertEqual(merged['model'], 'project-choice')
        commands = [hook['command'] for groups in merged['hooks'].values()
                    for group in groups for hook in group['hooks'] if hook.get('type') == 'command']
        self.assertIn('project-helper', commands)
        prompt_hooks = [hook for groups in merged['hooks'].values() for group in groups
                        for hook in group['hooks'] if hook.get('type') == 'prompt']
        self.assertEqual(prompt_hooks, [{'type': 'prompt', 'prompt': 'operator prompt hook'}])
        self.assertIn('operator-bash-helper', commands)
        self.assertIn('/operator/pre-push-self-review.sh', commands)
        self.assertTrue(any(Path(shlex.split(command)[0]).as_posix().endswith('/hooks/git/branch-guard.sh')
                            for command in commands))
        self.assertIn('/old/package/hooks/git/pre-push-self-review.sh', commands)
        self.assertNotIn('hooks/git/pre-push-self-review.sh', commands)
        self.assertNotIn(str(alias), commands)
        self.assertEqual(self.run_cmd(['git', 'config', '--get', 'core.hooksPath'], ok=False).returncode, 1)
        for command in commands:
            if command not in ('project-helper', 'operator-bash-helper', '/operator/pre-push-self-review.sh',
                               '/old/package/hooks/git/pre-push-self-review.sh'):
                self.assertEqual(len(shlex.split(command)), 1)
        self.install(); self.assertEqual(first, settings.read_bytes())

    def test_foreign_native_shaped_command_and_alias_keep_operator_metadata(self):
        settings = self.repo / '.claude/settings.json'; settings.parent.mkdir()
        foreign = self.base / 'operator/hooks/git/pre-push-self-review.sh'
        foreign.parent.mkdir(parents=True)
        foreign.write_text('#!/bin/sh\nexit 0\n'); foreign.chmod(0o755)
        alias = self.base / 'foreign-alias'; alias.symlink_to(foreign)
        commands = [str(foreign), str(alias), 'other/hooks/git/pre-push-self-review.sh']
        original = {'matcher': 'Bash', 'operator_metadata': 'retain',
                    'hooks': [{'type': 'command', 'command': command, 'timeout': 17}
                              for command in commands]}
        settings.write_text(json.dumps({'hooks': {'PreToolUse': [original]}}))
        self.install()
        groups = json.loads(settings.read_text())['hooks']['PreToolUse']
        self.assertIn(original, groups)
        first = settings.read_bytes()
        self.install()
        self.assertEqual(settings.read_bytes(), first)

    def test_malformed_existing_command_fails_without_settings_mutation(self):
        self.git('config', '--unset', 'core.hooksPath')
        settings = self.repo / '.claude/settings.json'; settings.parent.mkdir()
        settings.write_text(json.dumps({'hooks': {'PreToolUse': [{'matcher': 'Bash', 'hooks': [
            {'type': 'command', 'command': "'unterminated"},
        ]}]}}))
        before = settings.read_bytes()
        result = self.install(ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('invalid existing hook command', result.stderr)
        self.assertEqual(settings.read_bytes(), before)

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
