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
import shlex
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
    'taskset': 'taskset 1', 'chrt': 'chrt 5', 'arch': 'arch -arm64',
    # Top-level env/command keep the stricter project execution model
    # (env_project_execution.py); behind another wrapper they reach this one.
    'env': 'nohup env -i', 'command': 'nohup command -p', 'exec': 'exec -a name',
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
                                 "python3 -I -c 'open(\"x\", \"w\")'", 'nohup ./sh -c true',
                                 '/opt/venv/bin/python -Ic 1', "nohup /usr/bin/python3 -W error -c 'print(1)'",
                                 # ABI-flagged names: free-threaded, pymalloc, debug, wide unicode.
                                 "python3.13t -c 'print(1)'", "python3t -c 'print(1)'", "python3.7m -c 'print(1)'",
                                 '/usr/local/bin/python3.13d -Ic 1', "python3.2mu -c 'print(1)'",
                                 "nohup python3.13t -c 'print(1)'", "timeout 5 /opt/py/bin/python3.7dm -c 1"):
            with self.subTest(runner=runner):
                self.assertRefused(runner, OPAQUE)

    def test_python_refusal_keeps_develop_as_a_floor(self):
        # Develop refused python/python3 when any word started with -c. That
        # stays refused; -c in an option cluster is added. Words after the
        # script or module are script arguments and keep develop's outcome.
        def develop_refused(argv):
            return argv[0] in {'python', 'python3'} and any(x == '-c' or x.startswith('-c') for x in argv[1:])
        rows = ("python3 -c 'print(1)'", "python -c 'print(1)'", 'python3 ./tool.py -c x', 'python3 ./tool.py -config x',
                'python3 -m pytest -c ./pytest.ini', "python3 -I -c 'open(\"x\", \"w\")'", "python3 -Ic 'print(1)'",
                'python3 -W error -c 1', 'python3 -Wc ./x.py', 'python3 -X dev ./x.py', 'python3 ./tool.py -vc',
                'python3 ./tool.py -xc', 'python3 -m pytest -x', 'python3 -mc ./x.py', 'python3 -- ./x.py -vc',
                'python3 --check-hash-based-pycs always ./x.py', 'python3 ./x.py')
        newly_refused = {"python3 -Ic 'print(1)'"}
        for command in rows:
            with self.subTest(command=command):
                refused = bool(self.shape(command).get('error'))
                expected = develop_refused(shlex.split(command)) or command in newly_refused
                self.assertEqual(refused, expected, command)

    def test_runners_in_pipelines_and_lists_are_refused(self):
        for command in ('echo x | timeout 5 sh', 'echo x | nohup bash -s', 'cd ./a && nohup sh -c true',
                        "true && timeout 5 python3 -c 'print(1)'", 'FOO=1 timeout 5 sh -c true',
                        'timeout 5 FOO=1 sh -c true'):
            with self.subTest(command=command):
                self.assertRefused(command, OPAQUE)

    def test_xargs_supplied_python_arguments_are_refused(self):
        # xargs appends arguments the model cannot see, so -c (or the module)
        # may arrive from its input until a script or module is named.
        for command in ('xargs python3', 'xargs python3 -I', 'xargs -n 1 python3 -W error', 'nohup xargs python3 -m',
                        'xargs python3 --'):
            with self.subTest(command=command):
                self.assertRefused(command, OPAQUE)
        # A replacement string up to and including the script or module word
        # is chosen by the input (it can become -cCODE).
        for command in ('xargs -I X python3 X', 'xargs -J % python3 %', 'xargs -J % python3 -I %',
                        'xargs -I X nohup python3 X', 'xargs --replace=X python3 X', 'xargs -I X python3 -m X',
                        'xargs -I X python3 -- X'):
            with self.subTest(command=command):
                self.assertRefused(command, OPAQUE)
        # Python stops reading options at the script or module, so appended
        # words, and a replacement after the script, are its arguments
        # (develop outcome kept).
        for command in ('xargs -n 1 python3 ./x.py', 'nohup xargs python3 -m pytest', 'xargs python3 -- ./x.py',
                        'xargs -I X python3 ./tool.py X', 'xargs -I Y python3 -m mod Y', 'xargs -J % python3 ./tool.py %'):
            with self.subTest(command=command):
                self.assertOutcome(command, 'mutation')

    def test_run_time_words_in_a_wrapper_head_are_refused(self):
        # Re-review N1: an xargs replacement string or env -S ${VAR} in a word
        # the wrapper consumes itself can move where the command starts.
        for command in ("echo -- | xargs -I X timeout X 5 sh -c 'touch /tmp/1376'",
                        "echo -v | xargs -I X timeout X 1 sh -c 'touch /tmp/1376'",
                        "xargs -iX timeout X 1 sh -c 'touch /tmp/1376'",
                        "xargs --replace=X timeout X 1 sh -c 'touch /tmp/1376'",
                        "echo '5 sh' | xargs -J % timeout % -c 'touch /tmp/1376'",
                        'xargs -J % nice -n % ls', 'xargs -J % sudo -u % ls', 'xargs -I X flock X ls',
                        'xargs -I X taskset X ls', "nohup env -S 'timeout ${X} 5 sh -c true'"):
            with self.subTest(command=command):
                self.assertRefused(command, OPAQUE)

    def test_util_linux_script_command_after_file_is_refused(self):
        # util-linux script permutes options, so -c/--command after FILE runs a shell string.
        for command in ("script ./out -qc 'touch /tmp/1376'", "script ./out -q -c 'touch /tmp/1376'",
                        "script ./out --comm='touch /tmp/1376'", "nohup script -q ./out --command 'touch /tmp/1376'"):
            with self.subTest(command=command):
                self.assertRefused(command, OPAQUE)
        # Only option words directly after FILE are script options; the
        # command's own arguments keep develop's outcome.
        for command in ('script -q ./out ls --color', 'script -q ./out cc -c foo.c'):
            with self.subTest(command=command):
                self.assertOutcome(command, 'mutation')

    def test_each_wrapper_in_front_of_each_runner_is_refused(self):
        for name, prefix in WRAPPERS.items():
            for runner in RUNNERS:
                command = prefix + ' ' + runner
                with self.subTest(command=command):
                    self.assertRefused(command, OPAQUE)

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
                        # watch without -x runs its words as one sh -c string, so
                        # `watch ls` is refused too (a deliberate outcome change).
                        "watch 'touch /tmp/1376'", 'nohup watch -n 1 ls', 'watch ls', 'watch -n 1 git status'):
            with self.subTest(command=command):
                self.assertRefused(command, OPAQUE)

    def test_xargs_supplied_commands_and_executables_are_refused(self):
        # xargs appends its input to the command, so a wrapper with no command
        # of its own runs whatever the input names; a replacement string in the
        # executable position is chosen by the input.
        for command in ("echo 'bash -c true' | xargs env", 'xargs nohup', "printf 'sh -c true' | xargs timeout 5",
                        'xargs sudo', 'xargs command', 'nohup xargs env -i', "xargs -I X X -c 'touch /tmp/1376'",
                        "echo sh | xargs -J % % -c true", 'xargs -I X nohup X', 'xargs -iX timeout 5 X'):
            with self.subTest(command=command):
                self.assertRefused(command, OPAQUE)

    def test_abbreviated_and_unknown_wrapper_options_are_refused(self):
        # GNU accepts a unique long-option prefix; the model matches exactly,
        # so a prefix (or any option no table lists) is not modelled.
        for command in ("timeout --sig KILL 5 bash -c 'touch /tmp/1376'", 'timeout --k 1 5 sh',
                        "nice --adj 5 bash -c 'touch /tmp/1376'", "xargs --max-a 1 bash -c 'touch /tmp/1376'",
                        'stdbuf --out L sh', "nohup env --split='bash -c true'", "nohup env --split-str='sh -c true'",
                        "flock --comm='touch /tmp/1376' /tmp/1376.lock", 'sudo --sh ls', 'sudo --log', 'sudo --shel',
                        "nohup env -L root bash -c 'touch /tmp/1376'", 'timeout --foreground=x 5 ls'):
            with self.subTest(command=command):
                self.assertRefused(command)

    def test_value_options_are_modelled_on_both_platforms(self):
        # BSD env -P, xargs -J/-R/-S and doas -a take a value; GNU xargs
        # --replace/--eof/--max-lines take one only as =VALUE.
        for command in ("nohup env -P /usr/bin bash -c 'touch /tmp/1376'", "timeout 5 env -S '-P /usr/bin bash -c true'",
                        "xargs -J % bash -c 'touch /tmp/1376'", "xargs -R 1 bash -c 'touch /tmp/1376'",
                        "xargs -S 255 bash -c 'touch /tmp/1376'", "doas -a style bash -c 'touch /tmp/1376'",
                        "xargs --replace bash -c 'touch /tmp/1376'", "xargs --eof bash -c 'touch /tmp/1376'",
                        "xargs --max-lines bash -c 'touch /tmp/1376'", 'nohup env -P/usr/bin sh'):
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
            'nice make': 'mutation', 'nice -n 5 make test': 'mutation', 'nohup pytest ./test_app.py': 'mutation',
            'timeout 30 git status': 'read_only', 'timeout 30 git log --oneline -1': 'read_only',
            # The modelled read-only Python reader (an AST-checked -I -c program) is unchanged.
            "python3 -I -c 'print(1)'": 'read_only', "timeout 5 python3 -I -c 'print(1)'": 'mutation',
            # A path-spelled interpreter: only Python's own option region is
            # scanned, so a module's -c (pytest -c FILE) keeps develop's outcome.
            '/absolute/venv/bin/python -m pytest -c pyproject.toml ./test_app.py': 'mutation',
            'nohup /usr/bin/python3 -m pytest -c pytest.ini': 'mutation',
            '/opt/venv/bin/python ./tool.py -c x': 'mutation',
            # Behind a wrapper, python/python3 also use the option-region scan
            # (develop never refused wrapped forms); wrapped inline code is refused.
            'nohup python3 -m pytest -c x': 'mutation', 'timeout 5 python3 ./tool.py -c x': 'mutation',
            "nohup python3 -c 'print(1)'": 'refused', "timeout 5 python -Ic 1": 'refused',
            # ABI-flagged names that run a script or module keep develop's outcome.
            'python3.13t ./x.py': 'mutation', 'python3.13t -m pytest -c pytest.ini': 'mutation',
            # Review findings 4/5: script arguments and sudo value clusters.
            'python3 ./tool.py -vc': 'mutation', 'nohup python3 ./tool.py -xc': 'mutation',
            'nohup python3 ./tool.py --check': 'mutation', 'sudo -usroot ls': 'mutation', 'sudo -Dsrc ls': 'mutation',
            'sudo -E ls': 'mutation', 'sudo -nk ls': 'mutation', 'timeout 5 env -uS ls': 'mutation',
            'xargs': 'mutation', 'nohup ls': 'mutation', 'xargs -0 -n 1 rm': 'mutation',
            'timeout --foreground 5 make': 'mutation', 'timeout --signal=KILL 5 make': 'mutation',
            'nice -10 make': 'mutation', 'xargs -I X touch ./a/X': 'mutation',
            'xargs --replace=@ cp @ ./a': 'mutation', 'script -q /dev/null ls -l': 'mutation',
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
