#!/usr/bin/env python3
"""Literal shell operands still require their actual owning task."""
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('task_fixture', ROOT / 'hooks/_test/task_keyed_gates.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
from task_actions import shell_tokens


class QuotedOperands(unittest.TestCase):
    def setUp(self):
        self.f = f.Gates(); self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.repo = self.f.repo
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.test')
        (self.repo / '.github/workflows').mkdir(parents=True)
        (self.repo / '.github/workflows/ci.yml').write_text('name: baseline\n')
        (self.repo / 'tests').mkdir()
        (self.repo / 'tests/test_demo.py').write_text('def test_case(): pass\n')
        self.git('add', '-f', '.')
        self.git('commit', '-qm', 'fixture baseline')
        self.git('update-ref', 'refs/remotes/origin/main', self.git('rev-parse', 'HEAD').stdout.strip())
        self.command = "python3 -m pytest 'tests/test_demo.py::test_case[param]'"

    def git(self, *args):
        return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(self.repo), *args], check=True, capture_output=True, text=True, timeout=10)

    def task(self, scope=None, full=False, status='implementing'):
        gate = self.f.task('example/app#1194', scope or self.repo, status=status)
        if not full:
            for name in ['junior-senior-gate.json', 'artifacts-posted-gate.json']:
                (gate / name).unlink()
            data = json.loads((gate / 'think-gate.json').read_text())
            data['tier'] = 'B'; f.write(gate / 'think-gate.json', data)
        return gate

    def test_original_literal_node_is_not_a_shell_expansion(self):
        shape = f.r.action(self.command, str(self.repo))
        self.assertFalse(any(globs for _, _, globs in shell_tokens(self.command)))
        self.assertFalse(shape.get('error'), shape)
        self.assertFalse(shape['read_only'])
        self.assertFalse(shape.get('investigation'))
        self.task()
        self.f.assertGate(0, self.command)
        self.f.assertGate(0, 'pytest "tests/test_demo.py::test_case[param]"')
        self.f.assertGate(0, r'python3 -m pytest tests/test_demo.py::test_case\[param\]')

    def test_no_gate_designing_and_narrow_scope_still_deny(self):
        self.f.assertGate(2, self.command)
        gate = self.task(status='designing')
        self.f.assertGate(2, self.command)
        data = json.loads((gate / 'think-gate.json').read_text())
        data.update(status='implementing', scope_paths=[str(self.repo / 'tests')])
        f.write(gate / 'think-gate.json', data)
        self.f.assertGate(2, self.command)

    def test_absolute_venv_and_real_reporter_options_keep_unknown_tier(self):
        self.task()
        command = "/absolute/venv/bin/python -m pytest -o addopts= --rootdir=. -c pyproject.toml -p no:cacheprovider 'tests/test_demo.py::test_case[param]' 2>&1 | tail -n 20"
        shape = f.r.action(command, str(self.repo))
        self.assertFalse(shape.get('error'), shape)
        self.assertFalse(shape['read_only'])
        self.assertFalse(shape.get('investigation'))
        self.f.assertGate(2, command)
        self.task(full=True)
        self.f.assertGate(0, command)

    def test_actual_unquoted_globs_and_shell_expansion_stay_denied(self):
        self.task(full=True)
        for command in [self.command.replace("'tests/test_demo.py::test_case[param]'", 'tests/test_demo.py::test_case[param]'), 'pytest tests/*.py', 'pytest "$(printf tests/test_demo.py)"']:
            with self.subTest(command=command): self.f.assertGate(2, command)

    def test_unknown_plugins_and_inline_programs_keep_their_guards(self):
        self.task()
        for command in ['pytest -p arbitrary ' + shlex.quote('tests/test_demo.py::test_case[param]'), 'pytest -c pytest.ini ' + shlex.quote('tests/test_demo.py::test_case[param]')]:
            with self.subTest(command=command): self.f.assertGate(2, command)
        self.task(full=True)
        for command in ["python3 -c 'print([1])'", "./unknown '[literal]'", "/absolute/venv/bin/python -c 'print([1])'", "env pytest 'tests/test_demo.py::test_case[param]'", "git add '[literal]'", "touch '~literal' "]:
            with self.subTest(command=command): self.f.assertGate(2, command)

    def test_mixed_or_foreign_targets_cannot_borrow_pytest_authority(self):
        self.task(full=True)
        foreign = self.f.ws / 'foreign.py'
        for command in [self.command + '; touch ' + str(foreign), self.command + ' > ' + str(foreign), self.command + ' --junitxml=' + str(foreign), 'pytest ' + shlex.quote(str(foreign) + '::test_case[param]')]:
            with self.subTest(command=command): self.f.assertGate(2, command)

    def test_literal_filesystem_operand_scope_and_real_effect(self):
        target = self.f.a / '[literal].txt'
        command = 'touch ' + shlex.quote(str(target))
        self.f.assertGate(2, command)
        self.f.task('file-literal', self.f.a)
        self.f.assertGate(0, command)
        subprocess.run(['touch', str(target)], check=True, timeout=10)
        self.assertTrue(target.is_file())
        self.f.assertGate(2, 'touch ' + shlex.quote(str(self.f.b / '[literal].txt')))
        self.f.assertGate(2, 'touch ' + str(self.f.a / '[literal].txt'))
        destination = self.f.a / 'copy[one].txt'
        self.f.assertGate(0, 'cp ' + shlex.quote(str(target)) + ' ' + shlex.quote(str(destination)))


if __name__ == '__main__': unittest.main()
