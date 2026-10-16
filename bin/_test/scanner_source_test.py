#!/usr/bin/env python3
"""Real index/PR object truth and incomplete-result regressions for the scanner."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import shlex
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / 'skills/detect-ai-fingerprints'
spec = importlib.util.spec_from_file_location('scanner_ast', SKILL / 'scan_ast.py')
ast_scanner = importlib.util.module_from_spec(spec); spec.loader.exec_module(ast_scanner)
VIOLATION = 'import requests\nrequests.get("https://example.invalid")\n'
CLEAN = 'answer = 1\n'


class ScannerSourceTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='scanner-source-')
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name); self.root = self.base / 'repo'; self.root.mkdir()
        commands = self.base / 'commands'; commands.mkdir()
        python = commands / 'python3'
        python.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' "$@"\n'); python.chmod(0o755)
        self.env = {**os.environ, 'PATH': str(commands) + ':' + os.environ['PATH'], 'PYTHONDONTWRITEBYTECODE': '1'}
        self.git('init', '-q'); self.git('config', 'user.name', 'Fixture'); self.git('config', 'user.email', 'fixture@example.invalid')
        self.write('client.py', CLEAN); self.git('add', 'client.py'); self.git('commit', '-qm', 'seed')

    def git(self, *args):
        if args[0] == 'add': args = ('add', '--force', *args[1:])
        return subprocess.check_output(['git', *args], cwd=self.root, stderr=subprocess.PIPE).decode().strip()

    def write(self, name, content):
        p = self.root / name; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content if isinstance(content, bytes) else content.encode())
        return p

    def scan(self, *args, cwd=None):
        return subprocess.run(['bash', str(SKILL / 'scan.sh'), *args], cwd=cwd or self.root, env=self.env, text=True, capture_output=True, timeout=60)

    def expect(self, result, code, diagnostic=None):
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, code, output)
        if code == 2: self.assertNotIn('clean. scanned:', output)
        if diagnostic: self.assertIn(diagnostic, output)
        return output

    def gh(self, metadata=None, fail=False):
        folder = self.base / 'commands'; folder.mkdir(exist_ok=True)
        script = folder / 'gh'
        script.write_text('#!' + sys.executable + '\nimport json,sys\n'
                          + 'assert sys.argv[1:] == ["pr","view","17","--json","baseRefOid,headRefOid"]\n'
                          + ('raise SystemExit(31)\n' if fail else 'print(' + repr(json.dumps(metadata)) + ')\n'))
        script.chmod(0o755)
        self.env['PATH'] = str(folder) + ':' + self.env['PATH']

    def test_staged_violation_uses_index_despite_clean_working_file(self):
        self.write('client.py', VIOLATION); self.git('add', 'client.py'); self.write('client.py', CLEAN)
        before = self.git('write-tree')
        self.expect(self.scan(), 1, 'writing-code-15')
        self.assertEqual(self.git('write-tree'), before)
        self.assertEqual((self.root / 'client.py').read_text(), CLEAN)

    def test_staged_clean_ignores_unstaged_violation(self):
        self.write('client.py', 'answer = 2\n'); self.git('add', 'client.py'); self.write('client.py', VIOLATION)
        self.expect(self.scan(), 0, 'clean. scanned:')
        self.expect(self.scan('--working'), 1, 'writing-code-15')

    def test_exact_pr_head_differs_from_checkout_in_both_directions(self):
        base = self.git('rev-parse', 'HEAD')
        self.write('client.py', VIOLATION); self.git('add', 'client.py'); self.git('commit', '-qm', 'violating head')
        head = self.git('rev-parse', 'HEAD')
        self.write('client.py', 'answer = 2\n'); self.git('add', 'client.py'); self.git('commit', '-qm', 'clean changed head')
        clean_head = self.git('rev-parse', 'HEAD'); self.git('checkout', '-q', base)
        self.gh({'baseRefOid': base, 'headRefOid': head})
        self.expect(self.scan('--pr', '17'), 1, 'writing-code-15')
        self.git('checkout', '-q', head)
        self.gh({'baseRefOid': base, 'headRefOid': clean_head})
        self.expect(self.scan('--pr', '17'), 0, 'clean. scanned:')

    def test_pr_metadata_failure_and_missing_objects_are_incomplete(self):
        for metadata in ({}, {'baseRefOid': '0' * 40, 'headRefOid': self.git('rev-parse', 'HEAD')}):
            self.gh(metadata)
            self.expect(self.scan('--pr', '17'), 2, 'scan-source-error')
        self.gh(fail=True)
        self.expect(self.scan('--pr', '17'), 2, 'scan-source-error')

    def test_cross_file_evidence_is_selected_from_same_index(self):
        source = 'def recover():\n    try:\n        int("bad")\n    except ValueError:\n        raise\n'
        test = 'import unittest\nclass Coverage(unittest.TestCase):\n    def test_error(self):\n        with self.assertRaises(ValueError):\n            int("bad")\n'
        self.write('client.py', source); self.git('add', 'client.py')
        path = self.write('tests/test_client.py', test)
        self.expect(self.scan(), 1, 'writing-tests-5')
        self.git('add', 'tests/test_client.py'); path.unlink()
        self.expect(self.scan(), 0, 'clean. scanned:')

    def test_scanner_config_comes_from_index_and_errors_do_not_become_clean(self):
        self.write('client.py', '@project_marker\ndef callback(unused=1):\n    return 1\n'); self.git('add', 'client.py')
        path = self.write('.claude/scanner-config.toml', '[scanner]\nallow_decorators = ["project_marker"]\n')
        self.expect(self.scan(), 1, 'writing-code-9')
        self.git('add', '.claude/scanner-config.toml'); path.write_text('malformed [')
        self.expect(self.scan(), 0)
        self.git('add', '.claude/scanner-config.toml'); path.write_text('[scanner]\nallow_decorators = ["project_marker"]\n')
        self.expect(self.scan(), 2, 'scan-ast-config-error')

    def test_syntax_encoding_and_related_test_errors_are_incomplete(self):
        for content in ('def broken(:\n', b'\xff\xfe\n'):
            self.write('client.py', content); self.git('add', 'client.py')
            self.expect(self.scan(), 2, 'scan-ast-')
        self.write('client.py', 'def recover():\n    try:\n        int("bad")\n    except ValueError:\n        raise\n')
        self.write('tests/test_client.py', 'def broken(:\n'); self.git('add', 'client.py', 'tests/test_client.py')
        self.expect(self.scan(), 2, 'scan-ast-syntax-error')

    def test_symlink_input_and_non_repository_fail_without_reading_target(self):
        target = self.base / 'outside.py'; target.write_text(VIOLATION)
        link = self.root / 'link.py'; link.symlink_to(target); self.git('add', 'link.py')
        result = self.scan()
        self.expect(result, 2, 'unsupported symlink')
        self.assertNotIn('writing-code-15', result.stdout)
        self.expect(self.scan(cwd=self.base), 2, 'scan-source-error')

    def test_spaces_and_subdirectory_invocation_preserve_logical_paths(self):
        self.write('folder with space/client.py', VIOLATION); self.git('add', 'folder with space/client.py')
        self.expect(self.scan(cwd=self.root / 'folder with space'), 1, 'folder with space/client.py:')

    def test_unborn_index_is_supported(self):
        root = self.base / 'unborn'; root.mkdir()
        subprocess.run(['git', 'init', '-q', str(root)], check=True)
        (root / 'client.py').write_text(VIOLATION)
        subprocess.run(['git', 'add', 'client.py'], cwd=root, check=True)
        self.expect(self.scan(cwd=root), 1, 'writing-code-15')

    def test_ast_cli_missing_config_file_list_and_bad_config_types_fail(self):
        self.write('invalid.toml', '[scanner]\nallow_decorators = "not-an-array"\n')
        self.write('invalid-list', b'\xff')
        for args in (['missing.py'], ['--config', 'missing.toml', 'client.py'], ['--config', 'invalid.toml', 'client.py'], ['--files-from', 'missing-list'], ['--files-from', 'invalid-list'], ['--config'], ['--files-from']):
            result = subprocess.run([sys.executable, str(SKILL / 'scan_ast.py'), *args], cwd=self.root, capture_output=True, text=True)
            self.expect(result, 2, 'scan-ast-')

    def test_ast_input_error_api_preserves_failure_cause(self):
        for name, content, exception in (('bad.py', 'def broken(:\n', SyntaxError), ('binary.py', b'\xff', UnicodeDecodeError)):
            path = self.write(name, content)
            with self.assertRaises(ast_scanner.ScanInputError) as caught:
                ast_scanner.scan_file(str(path), set())
            self.assertIsInstance(caught.exception.__cause__, exception)
        with self.assertRaises(ast_scanner.ScanInputError) as caught:
            ast_scanner.scan_file(str(self.root / 'missing.py'), set())
        self.assertIsInstance(caught.exception.__cause__, OSError)
        for path in (self.root / 'missing.py', self.root / 'bad.py', self.root / 'binary.py'):
            with self.assertRaises(ast_scanner.ScanInputError):
                ast_scanner._test_ast_covers_exception(path, 'ValueError')

    def test_missing_toml_dependency_does_not_silently_use_defaults(self):
        config = self.write('scanner.toml', '[scanner]\n')
        original = __import__
        import tomllib
        def fallback(name, *args, **kwargs):
            if name == 'tomllib': raise ImportError('fixture stdlib unavailable')
            if name == 'tomli': return tomllib
            return original(name, *args, **kwargs)
        with mock.patch('builtins.__import__', side_effect=fallback):
            self.assertEqual(ast_scanner.load_decorator_allowlist(config), ast_scanner.DEFAULT_ALLOW_DECORATORS)
        def unavailable(name, *args, **kwargs):
            if name in ('tomllib', 'tomli'): raise ImportError('fixture missing dependency')
            return original(name, *args, **kwargs)
        with mock.patch('builtins.__import__', side_effect=unavailable), self.assertRaisesRegex(ValueError, 'requires tomllib or tomli'):
            ast_scanner.load_decorator_allowlist(config)

    def test_child_process_failure_cannot_report_clean(self):
        python = self.base / 'commands/python3'
        python.write_text('#!/bin/sh\ncase "$1" in */scan_ast.py) exit 23;; esac\nexec ' + shlex.quote(sys.executable) + ' "$@"\n')
        self.write('client.py', 'answer = 2\n'); self.git('add', 'client.py')
        self.expect(self.scan(), 2, 'AST scanner failed (exit 23)')

    def test_snapshot_missing_git_is_an_explicit_source_error(self):
        env = {**self.env, 'PATH': str(self.base / 'empty-path')}
        result = subprocess.run([sys.executable, str(SKILL / 'scan_snapshot.py'), '--mode', 'staged', '--output', str(self.base / 'snapshot')], cwd=self.root, env=env, text=True, capture_output=True)
        self.expect(result, 2, 'scan-source-error')

    def test_missing_exact_pr_object_is_fetched_without_using_checkout_bytes(self):
        base = self.git('rev-parse', 'HEAD')
        self.write('client.py', VIOLATION); self.git('add', 'client.py'); self.git('commit', '-qm', 'PR object')
        head = self.git('rev-parse', 'HEAD')
        remote = self.base / 'remote.git'
        subprocess.run(['git', 'init', '-q', '--bare', str(remote)], check=True)
        self.git('remote', 'add', 'origin', str(remote))
        self.git('push', '-q', 'origin', base + ':refs/heads/main', head + ':refs/heads/pr-head')
        clone = self.base / 'source-only'
        subprocess.run(['git', 'clone', '-q', '--single-branch', '--branch', 'main', '--no-tags', 'file://' + str(remote), str(clone)], check=True)
        self.root = clone
        with self.assertRaises(subprocess.CalledProcessError): self.git('cat-file', '-e', head)
        self.gh({'baseRefOid': base, 'headRefOid': head})
        self.expect(self.scan('--pr', '17'), 1, 'writing-code-15')
        self.assertEqual((clone / 'client.py').read_text(), CLEAN)

    def test_unmerged_index_is_incomplete(self):
        original = self.git('rev-parse', 'HEAD')
        self.write('client.py', 'answer = 2\n'); self.git('add', 'client.py'); self.git('commit', '-qm', 'left')
        left = self.git('rev-parse', 'HEAD'); self.git('checkout', '-qb', 'other', original)
        self.write('client.py', 'answer = 3\n'); self.git('add', 'client.py'); self.git('commit', '-qm', 'right')
        with self.assertRaises(subprocess.CalledProcessError): self.git('merge', '--no-edit', left)
        self.expect(self.scan(), 2, 'scan-source-error')

    def test_missing_message_input_is_incomplete(self):
        for mode in ('--message-file', '--commit-message-file'):
            self.expect(self.scan(mode, str(self.base / 'missing-message')), 2, 'scan-input-error')


if __name__ == '__main__': unittest.main(verbosity=2)
