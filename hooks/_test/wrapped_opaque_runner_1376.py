#!/usr/bin/env python3
"""Opaque program-runner refusal looks through supported command wrappers (#1376).

A shell runner, eval/exec or interpreter inline code run through a supported
process wrapper (timeout, nohup, nice, setsid, sudo, ...) must be refused like
the bare runner, repeating through nested wrappers. A wrapper whose behaviour
cannot be modelled is refused. Wrappers in front of ordinary, modelled
commands keep their current outcome.
"""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('task_fixture', ROOT / 'hooks/_test/task_keyed_gates.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
task_actions = f.sys.modules['task_actions']

OPAQUE = 'opaque inline execution has unbounded mutation targets'

# One literal spelling of each supported wrapper in front of the command it runs.
WRAPPERS = {
    'timeout': 'timeout 5', 'gtimeout': 'gtimeout -k 2 5', 'nohup': 'nohup', 'setsid': 'setsid',
    'unbuffer': 'unbuffer', 'builtin': 'builtin', 'nocorrect': 'nocorrect', 'noglob': 'noglob',
    'nice': 'nice -n 5', 'time': 'time -p', 'xargs': 'xargs -n 1', 'sudo': 'sudo -u root',
    'doas': 'doas -u root', 'stdbuf': 'stdbuf -oL', 'caffeinate': 'caffeinate -t 5', 'watch': 'watch -x',
    'flock': 'flock /tmp/1376.lock', 'script': 'script -q /dev/null', 'ionice': 'ionice -c 3',
    'taskset': 'taskset 1', 'chrt': 'chrt 5', 'arch': 'arch -arm64', 'env': 'env', 'command': 'command',
    'exec': 'exec -a name',
}

# One member of each refused runner class.
RUNNERS = (
    "sh -c 'touch /tmp/1376'", "bash -c 'touch /tmp/1376'", "zsh -c 'touch /tmp/1376'",
    "dash -c 'touch /tmp/1376'", "ksh -c 'touch /tmp/1376'", "bash ./script.sh",
    "eval 'touch /tmp/1376'", 'exec sh', "python3 -c 'print(1)'", "python -c 'print(1)'",
    "/bin/sh -c 'touch /tmp/1376'", "/usr/bin/python3 -c 'print(1)'",
)


class WrappedOpaqueRunner(unittest.TestCase):
    def setUp(self):
        self.f = f.Gates(); self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.repo = self.f.repo
        self.f.task('fix-1376-fixture', self.repo)

    def shape(self, command):
        return task_actions.action(command, str(self.repo))

    def assertRefused(self, command, message=None):
        shape = self.shape(command)
        self.assertTrue(shape.get('error'), (command, shape))
        if message:
            self.assertIn(message, shape['error'], command)
        self.assertFalse(shape['read_only'], command)

    def assertOutcome(self, command, expected):
        shape = self.shape(command)
        actual = 'refused' if shape.get('error') else 'read_only' if shape['read_only'] else 'mutation'
        self.assertEqual(actual, expected, (command, shape))

    def test_every_supported_wrapper_has_a_row(self):
        self.assertEqual(set(WRAPPERS), set(task_actions._WRAPPER_VALUES))

    def test_bare_runner_spellings_are_refused(self):
        # The first word is matched by basename and case-insensitively, after
        # leading assignments, and Python inline code also in a short cluster.
        for runner in RUNNERS + ("SH -c 'touch /tmp/1376'", "Python3 -c 'print(1)'", 'FOO=1 sh -c true',
                                 "python3 -Ic 'print(1)'", "python3 -IScprint", "python3.12 -c 'print(1)'",
                                 "python3 -I -c 'open(\"x\", \"w\")'", 'nohup ./sh -c true'):
            with self.subTest(runner=runner):
                self.assertRefused(runner, OPAQUE)

    def test_runners_in_pipelines_and_lists_are_refused(self):
        for command in ('echo x | timeout 5 sh', 'echo x | nohup bash -s', 'cd ./a && nohup sh -c true',
                        "true && timeout 5 python3 -c 'print(1)'", 'FOO=1 timeout 5 sh -c true',
                        'timeout 5 FOO=1 sh -c true'):
            with self.subTest(command=command):
                self.assertRefused(command, OPAQUE)

    def test_xargs_supplied_python_arguments_are_refused(self):
        # xargs appends arguments the model cannot see, so -c may arrive from stdin.
        for command in ('xargs python3', 'xargs -n 1 python3 ./x.py', 'nohup xargs python3 -m pytest'):
            with self.subTest(command=command):
                self.assertRefused(command, OPAQUE)

    def test_each_wrapper_in_front_of_each_runner_is_refused(self):
        for name, prefix in WRAPPERS.items():
            for runner in RUNNERS:
                command = prefix + ' ' + runner
                with self.subTest(command=command):
                    # env/command at the top level keep their stricter project
                    # execution model and its own refusal text.
                    self.assertRefused(command, None if name in {'env', 'command'} else OPAQUE)

    def test_nested_wrappers_are_unwrapped_repeatedly(self):
        for command in ("timeout 5 nice -n 5 nohup sh -c 'touch /tmp/1376'",
                        "sudo -u root timeout 5 setsid bash -c 'touch /tmp/1376'",
                        "timeout 5 env sh -c 'touch /tmp/1376'",
                        "timeout 5 env -i FOO=1 python3 -c 'print(1)'",
                        "nohup command eval 'touch /tmp/1376'",
                        "timeout 5 env -S 'sh -c true'",
                        "nohup env --split-string='timeout 5 bash -c true'",
                        '/usr/bin/timeout 5 /bin/bash -c true',
                        "TIMEOUT 5 sh -c 'touch /tmp/1376'",
                        "timeout 5 exec -a name zsh -c true"):
            with self.subTest(command=command):
                self.assertRefused(command, OPAQUE)

    def test_wrappers_that_run_their_operand_through_a_shell_are_refused(self):
        for command in ("timeout 5 flock /tmp/1376.lock -c 'touch /tmp/1376'",
                        "flock /tmp/1376.lock -c 'touch /tmp/1376'",
                        "script -q -c 'touch /tmp/1376' /dev/null",
                        "watch 'touch /tmp/1376'", 'nohup watch -n 1 ls'):
            with self.subTest(command=command):
                self.assertRefused(command, OPAQUE)

    def test_unmodelled_wrapper_behaviour_is_refused(self):
        for command in ("timeout 5 env -S '${RUNNER} -c true'",   # executable chosen by the environment
                        "timeout 5 env -S 'python3 ${OPTION} true'",  # inline-code option chosen by the environment
                        "timeout 5 env -S 'sh -c \\q'",            # split string with no modelled argv
                        'script -q /dev/null',                    # runs an interactive shell
                        'nohup script', 'sudo -s', 'sudo -i ls', 'sudo --login', 'sudo -u root -s ls',
                        'doas -s', 'timeout 5 sudo -s',
                        'nohup ' * 17 + 'ls'):                   # nesting beyond the modelled depth
            with self.subTest(command=command):
                self.assertRefused(command)

    def test_wrappers_in_front_of_ordinary_commands_keep_their_outcome(self):
        # Outcomes observed on develop 1206bf61 before #1376.
        expected = {
            'timeout 5 touch ./a/x': 'mutation', 'nohup touch ./a/x': 'mutation', 'nice -n 5 ls': 'mutation',
            'timeout 5 ls': 'read_only', 'time ls': 'read_only', 'timeout 5 git status': 'read_only',
            'command -v sh': 'read_only', 'timeout 5 rm ./a/x': 'mutation', 'xargs touch': 'mutation',
            'sudo -l': 'mutation', 'timeout 5 python3 ./script.py': 'mutation',
            'nohup python3 -m pytest ./test_app.py': 'mutation', 'watch -x ls': 'mutation',
            'flock /tmp/1376.lock ls': 'mutation', 'timeout 5 env -i bun test': 'mutation',
            "timeout 5 env -S 'ls -l'": 'mutation', 'setsid -w make test': 'mutation',
            'stdbuf -oL ./a/run.sh': 'mutation', 'taskset 1 make': 'mutation', 'nohup': 'mutation',
            'sudo -e ./a/x': 'mutation', 'nohup command -v sh': 'mutation',
            'timeout 5 shasum ./a/x': 'read_only',
            'env -i bun test': 'mutation', 'env -i sh -c true': 'refused', 'command make test': 'mutation',
            'timeout 5 xargs ls': 'mutation', 'sudo -u root ls': 'mutation', 'sudo -H ls': 'mutation',
            'doas -u root ls': 'mutation', 'nohup env -u FOO ls': 'mutation', 'script -q /dev/null ls': 'mutation',
            'python3 -W error::DeprecationWarning ./x.py': 'mutation', 'python3 -Werror::DeprecationWarning ./x.py': 'mutation',
            'python3 -m pytest ./test_app.py': 'mutation', 'timeout 5 python3 -X dev ./x.py': 'mutation',
            # The modelled read-only Python reader (an AST-checked -I -c program) is unchanged.
            "python3 -I -c 'print(1)'": 'read_only', "timeout 5 python3 -I -c 'print(1)'": 'mutation',
        }
        for command, outcome in expected.items():
            with self.subTest(command=command):
                self.assertOutcome(command, outcome)

    def test_mutation_gate_refuses_a_wrapped_runner_in_scope(self):
        self.f.assertGate(2, "timeout 5 sh -c 'touch ./a/out'")
        self.f.assertGate(2, "nohup python3 -c 'print(1)'")
        self.f.assertGate(0, 'timeout 5 touch ./a/out')


if __name__ == '__main__':
    unittest.main()
