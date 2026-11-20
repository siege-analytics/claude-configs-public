#!/usr/bin/env python3
"""Wrapped project execution is a scoped mutation, never candidate execution."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('task_fixture', ROOT / 'hooks/_test/task_keyed_gates.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


class EnvProjectExecution(unittest.TestCase):
    def setUp(self):
        self.f = f.Gates(); self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.repo = self.f.repo
        self.gate = self.f.task('example/app#1328', self.repo)

    def shape(self, command):
        return f.r.action(command, str(self.repo))

    def test_exact_refused_bun_shape_is_mutation_with_literal_targets(self):
        # Refusal logs normalize paths; exercise literal relative resolution after cd.
        execution = self.repo / 'api.elect.info'; execution.mkdir()
        command = ('cd ./api.elect.info && env -i PATH=/app/vendor/bun:/usr/bin:/bin HOME=./sessions/one/data/home '
                   'XDG_CONFIG_HOME=./sessions/one/data/xdg XDG_CACHE_HOME=./sessions/one/data/cache '
                   'TMPDIR=./sessions/one/data/tmp NODE_ENV=test BUN_RUNTIME_TRANSPILER_CACHE_PATH=0 '
                   'DO_NOT_TRACK=1 /app/vendor/bun/bun --config=./sessions/one/data/bunfig.toml '
                   '--no-env-file --no-install test ./test/red.test.ts')
        shape = self.shape(command)
        self.assertFalse(shape.get('error'), shape)
        self.assertFalse(shape['read_only']); self.assertFalse(shape['investigation'])
        self.assertIn(str(execution), shape['fallback_paths'])
        for name in ('home', 'xdg', 'cache', 'tmp', 'bunfig.toml'):
            self.assertIn(str(execution / 'sessions/one/data' / name), shape['paths'])
        self.assertNotIn('/app/vendor/bun:/usr/bin:/bin', shape['paths'])
        self.f.assertGate(0, command)

    def test_known_executables_keep_unknown_write_floor(self):
        for command in ('command -- bun test ./test.ts', 'env -i NODE_ENV=test node ./app.js',
                        'env CI=1 PYTHONPATH=./src python3 -m pytest ./test_app.py', 'command make test', 'env -i npm test', 'env -i bun --version'):
            with self.subTest(command=command):
                shape = self.shape(command)
                self.assertFalse(shape.get('error'), shape)
                self.assertFalse(shape['read_only'])
                self.assertIn(str(self.repo), shape['fallback_paths'])
                data = json.loads((self.gate / 'think-gate.json').read_text())
                self.assertNotEqual(f.r.task_tier(data, shape['paths'], command, str(self.repo)), 'A')
                self.f.assertGate(0, command)

    def test_foreign_explicit_environment_and_program_outputs_stay_targets(self):
        foreign = str(self.f.b / 'out.xml')
        for command in ('env HOME=' + foreign + ' bun test',
                        'env PYTHONPATH=' + foreign + ':./src python3 -m pytest',
                        'env -i bun test --junitxml=' + foreign,
                        'command pytest --junitxml ' + foreign,
                        'env -i bun test > ' + foreign):
            with self.subTest(command=command):
                self.assertIn(foreign, self.shape(command)['paths'])
                # Narrow the Task so the sibling remains foreign.
                data = json.loads((self.gate / 'think-gate.json').read_text())
                data['scope_paths'] = [str(self.f.a)]
                f.write(self.gate / 'think-gate.json', data)
                self.f.assertGate(2, command, cwd=self.f.a)

    def test_unknown_wrappers_inline_ssh_and_git_stay_denied(self):
        commands = ('env --chdir=/tmp bun test', 'command -p bun test', 'env -S "bun test"',
                    'env -i unknown-runner ./test.ts', 'env -i command bun test',
                    'env LD_PRELOAD=/foreign/hook.so bun test', 'env NODE_OPTIONS=--eval=evil node app.js',
                    'env -i bun --eval "touch /foreign/out"', 'command node -p1',
                    'command /usr/bin/python3 -c "print(1)"', 'env -i python3 -Icprint(1)', 'env -i sh -c "touch out"',
                    'env -i ssh example.invalid true', 'command ssh example.invalid true',
                    'env git --unsupported-global add app.py', 'command git --unsupported-global add app.py',
                    'env -i git add app.py', 'env GIT_DIR=/foreign git add app.py')
        for command in commands:
            with self.subTest(command=command):
                self.assertTrue(self.shape(command).get('error'), self.shape(command))
                self.f.assertGate(2, command)

    def test_supported_git_wrappers_still_use_git_effects(self):
        for command in ('command git add app.py', 'env LANG=C git add app.py',
                        'env GIT_OPTIONAL_LOCKS=0 git add app.py',
                        'env GIT_TERMINAL_PROMPT=0 git add app.py', 'env PAGER=cat git add app.py'):
            with self.subTest(command=command):
                shape = self.shape(command)
                self.assertFalse(shape.get('error'), shape)
                self.assertFalse(shape['read_only'])
                self.assertIn(str(self.repo), shape['paths'])
                self.f.assertGate(0, command)

    def test_missing_designing_and_narrow_task_cannot_borrow_wrapper_permission(self):
        command = 'env -i bun test ./test.ts'
        data = json.loads((self.gate / 'think-gate.json').read_text())
        data['status'] = 'designing'; f.write(self.gate / 'think-gate.json', data)
        self.f.assertGate(2, command)
        data['status'] = 'implementing'; data['scope_paths'] = [str(self.f.a)]
        f.write(self.gate / 'think-gate.json', data); self.f.assertGate(2, command)
        (self.gate / 'think-gate.json').unlink(); self.f.assertGate(2, command)


if __name__ == '__main__':
    unittest.main()
