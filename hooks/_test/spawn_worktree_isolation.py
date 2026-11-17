#!/usr/bin/env python3
"""Exercise the native spawn payload against real isolated Git worktrees."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / 'hooks/agent-comms/spawn-guard.sh'


class Isolation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='spawn-isolation-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / 'project'
        self.child = self.base / 'child-slot'
        self.env = dict(os.environ, GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1')
        self.git(self.base, 'init', '-q', '-b', 'develop', str(self.repo))
        self.git(self.repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-q', '--no-gpg-sign', '--allow-empty', '-m', 'seed')
        self.git(self.repo, 'worktree', 'add', '-q', '-b', 'feature/child', str(self.child), 'develop')

    def git(self, cwd, *args):
        result = subprocess.run(['git', '-C', str(cwd), *args], env=self.env,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def payload(self, path=None, *, prompt=None, parent=None):
        inputs = {'name': 'Implementation', 'prompt': prompt or 'Use RESOLVER.md and spawn-protocol. Implement assigned fix and commit changes.',
                  'permissionMode': 'allow-all', 'labels': ['implementation'],
                  'model': 'claude-sonnet-5', 'thinkingLevel': 'medium', 'enabledSourceSlugs': []}
        if path is not None:
            inputs['workingDirectory'] = str(path)
        return {'tool_name': 'mcp__session__spawn_session', 'cwd': str(parent or self.repo), 'tool_input': inputs}

    def guard(self, payload, *, env=None):
        return subprocess.run(['bash', str(HOOK)], input=json.dumps(payload), cwd=self.repo,
                              env=env or self.env, text=True, capture_output=True, timeout=10)

    def test_sibling_registered_worktree_needs_no_magic_words(self):
        result = self.guard(self.payload(self.child))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_canonical_checkout_is_not_isolation_even_with_magic_prompt(self):
        for suffix in ['', ' Create a git worktree first.', ' This is worktree-isolated.']:
            request = self.payload(self.repo)
            request['tool_input']['prompt'] += suffix
            result = self.guard(request)
            self.assertEqual(result.returncode, 2, result.stderr)

    def test_path_named_worktrees_is_not_proof(self):
        misleading = self.base / 'worktrees' / 'not-isolated'
        misleading.mkdir(parents=True)
        self.git(misleading, 'init', '-q', '-b', 'develop')
        self.assertEqual(self.guard(self.payload(misleading)).returncode, 2)

    def test_subdirectory_of_registered_worktree_passes(self):
        target = self.child / 'src'
        target.mkdir()
        self.assertEqual(self.guard(self.payload(target)).returncode, 0)

    def test_same_parent_worktree_and_inherited_directory_block(self):
        self.assertEqual(self.guard(self.payload(self.child, parent=self.child)).returncode, 2)
        self.assertEqual(self.guard(self.payload()).returncode, 2)

    def test_copied_git_pointer_is_not_registered_isolation(self):
        fake = self.base / 'copied-pointer'
        fake.mkdir()
        (fake / '.git').write_bytes((self.child / '.git').read_bytes())
        self.assertEqual(self.guard(self.payload(fake)).returncode, 2)

    def test_absolute_symlink_alias_preserves_actual_ownership(self):
        alias = self.base / 'alias with spaces'
        alias.symlink_to(self.child, target_is_directory=True)
        self.assertEqual(self.guard(self.payload(alias)).returncode, 0)
        self.assertEqual(self.guard(self.payload(alias, parent=self.child)).returncode, 2)

    def test_unresolved_host_directory_defaults_are_not_verification(self):
        for target in [None, '../child-slot', '~/child-slot']:
            result = self.guard(self.payload(target))
            self.assertEqual(result.returncode, 2)
            self.assertIn('explicit absolute workingDirectory', result.stderr)

    def test_host_home_substitutions_are_not_literal_directory_evidence(self):
        for index, segment in enumerate(['${HOME}', '$HOME', '$HOME-literal']):
            target = self.base / segment / 'child'
            target.parent.mkdir()
            self.git(self.repo, 'worktree', 'add', '-q', '-b', 'feature/home-' + str(index), str(target), 'develop')
            result = self.guard(self.payload(target))
            self.assertEqual(result.returncode, 0 if segment == '$HOME-literal' else 2, result.stderr)
            if segment != '$HOME-literal':
                self.assertIn('explicit absolute workingDirectory', result.stderr)

    def test_host_lexical_normalization_precedes_following_symlinks(self):
        deeper = self.base / 'other' / 'deeper'
        deeper.mkdir(parents=True)
        alias = self.base / 'alias'
        alias.symlink_to(deeper, target_is_directory=True)
        alternate = self.base / 'other' / 'project'
        self.git(self.repo, 'worktree', 'add', '-q', '-b', 'feature/alternate', str(alternate), 'develop')
        supplied = str(alias / '..' / 'project')
        self.assertEqual(Path(os.path.realpath(supplied)), alternate.resolve())
        self.assertEqual(Path(os.path.normpath(supplied)), self.repo)
        result = self.guard(self.payload(supplied))
        self.assertEqual(result.returncode, 2)
        self.assertIn('primary Git checkout', result.stderr)

    def test_inherited_git_targeting_cannot_disguise_primary_checkout(self):
        redirected = dict(self.env, GIT_DIR=self.git(self.child, 'rev-parse', '--absolute-git-dir'),
                          GIT_WORK_TREE=str(self.child))
        self.assertEqual(self.guard(self.payload(self.repo), env=redirected).returncode, 2)

    def test_unavailable_git_only_blocks_targets_with_git_ownership(self):
        shim = self.base / 'bin'
        shim.mkdir()
        git = shim / 'git'
        git.write_text('#!/bin/sh\necho unavailable >&2\nexit 128\n')
        git.chmod(0o755)
        unavailable = dict(self.env, PATH=str(shim) + os.pathsep + self.env.get('PATH', ''))
        plain = self.base / 'ordinary-data'
        plain.mkdir()
        self.assertEqual(self.guard(self.payload(plain), env=unavailable).returncode, 0)
        result = self.guard(self.payload(self.child), env=unavailable)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Git workspace metadata could not be read', result.stderr)

    def test_backpointer_fifo_and_oversize_are_bounded_denials(self):
        admin = Path(self.git(self.child, 'rev-parse', '--absolute-git-dir'))
        pointer = admin / 'gitdir'
        original = pointer.read_bytes()
        try:
            pointer.unlink()
            os.mkfifo(pointer)
            result = self.guard(self.payload(self.child))
            self.assertEqual(result.returncode, 2)
            self.assertIn('backpointer must be a small regular file', result.stderr)
            pointer.unlink()
            pointer.write_bytes(b'x' * 4097)
            result = self.guard(self.payload(self.child))
            self.assertEqual(result.returncode, 2)
            self.assertIn('backpointer must be a small regular file', result.stderr)
        finally:
            pointer.unlink(missing_ok=True)
            pointer.write_bytes(original)

    def test_independent_read_only_review_keeps_existing_contract(self):
        request = self.payload(self.repo, prompt='Use RESOLVER.md and spawn-protocol. Review only; do not modify files.')
        request['tool_input'].update(name='Read-only review', labels=['research'], thinkingLevel='high', model='claude-opus-4-8')
        self.assertEqual(self.guard(request).returncode, 0)

    def test_non_git_work_keeps_existing_route_and_missing_target_blocks(self):
        plain = self.base / 'plain'
        plain.mkdir()
        self.assertEqual(self.guard(self.payload(plain)).returncode, 0)
        missing = self.guard(self.payload(self.base / 'missing'))
        self.assertEqual(missing.returncode, 2)
        self.assertIn('workingDirectory does not exist', missing.stderr)
        file = self.base / 'ordinary-file'
        file.write_text('not a directory')
        result = self.guard(self.payload(file))
        self.assertEqual(result.returncode, 2)
        self.assertIn('workingDirectory is not a directory', result.stderr)


if __name__ == '__main__':
    unittest.main()
