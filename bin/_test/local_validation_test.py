#!/usr/bin/env python3
"""Exercise actual child dispatch, failure propagation and local isolation."""
import json
import importlib.util
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[2]


class LocalValidation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / 'bin').mkdir()
        (self.root / '.github/workflows').mkdir(parents=True)
        for name in ('validate-local.py', 'frontmatter_validation.py'):
            shutil.copy2(ROOT / 'bin' / name, self.root / 'bin' / name)

    def workflow(self, steps):
        (self.root / '.github/workflows/build-and-publish.yml').write_text(
            yaml.safe_dump({'jobs': {'validate': {'steps': steps}}}))

    def run_adapter(self, *args, env=None, interpreter=None):
        return subprocess.run([interpreter or sys.executable, str(self.root / 'bin/validate-local.py'),
                               '--mode', 'full', *args], cwd=self.root,
                              env=env, text=True, capture_output=True, timeout=30)

    def runtime(self):
        binary = self.root / 'runtime'
        binary.mkdir()
        python = binary / 'python3'
        python.symlink_to(sys.executable)
        # Moving an interpreter symlink outside its venv changes site discovery.
        # Keep the test's already-imported pinned YAML available to these aliases.
        pythonpath = str(Path(yaml.__file__).parent.parent)
        if os.environ.get('PYTHONPATH'):
            pythonpath += os.pathsep + os.environ['PYTHONPATH']
        return binary, str(python), {**os.environ,
                                    'PYTHONPATH': pythonpath,
                                    'PATH': str(binary) + os.pathsep + os.environ['PATH']}

    def shim(self, binary, name, body):
        path = binary / name
        path.write_text('#!/bin/sh\n' + body + '\n')
        path.chmod(0o755)
        return path

    def load_adapter(self):
        spec = importlib.util.spec_from_file_location('local_adapter', self.root / 'bin/validate-local.py')
        module = importlib.util.module_from_spec(spec)
        with mock.patch.object(sys, 'path', [str(self.root / 'bin'), *sys.path]):
            spec.loader.exec_module(module)
        return module

    def test_data_inside_complex_shell_shapes_has_no_prerequisites(self):
        module = self.load_adapter()
        cases = ["cat <<'EOF'\npython3 bin/build.py\nEOF",
                 'echo "start\npython3 bin/_test/selected_registration_test.py\nend"',
                 'echo "start\nfiles=(hooks/_test/*.test.sh)\nend"',
                 'echo "<<EOF"\npython3 bin/build.py',
                 'echo "unfinished']
        for command in cases:
            with self.subTest(command=command):
                self.assertEqual(module.full_prerequisites(command), (False, False, False, False))

    def test_complex_synthetic_workflows_execute_without_unused_tools(self):
        binary, python, env = self.runtime()
        sentinel = self.root / 'unused-tool-called'
        for tool in ('git', 'base64'):
            self.shim(binary, tool, 'touch ' + shlex.quote(str(sentinel)) + '; exit 99')
        # Adapter still uses its own known interpreter; bare python3 would fail
        # if the quoted/heredoc data were incorrectly treated as executable.
        Path(python).unlink()
        self.shim(binary, 'python3', 'touch ' + shlex.quote(str(sentinel)) + '; exit 99')
        cases = ["cat <<'EOF'\npython3 bin/build.py\nEOF",
                 'echo "start\npython3 bin/_test/selected_registration_test.py\nend"',
                 'echo "start\nfiles=(hooks/_test/*.test.sh)\nend"']
        for command in cases:
            with self.subTest(command=command):
                self.workflow([{'name': 'synthetic data', 'run': command + '\ntouch synthetic-ran'}])
                result = self.run_adapter(env=env)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertTrue((self.root / 'synthetic-ran').exists())
                self.assertFalse(sentinel.exists())
                (self.root / 'synthetic-ran').unlink()

    def test_actual_ci_prerequisite_selection_survives_conservative_filter(self):
        module = self.load_adapter()
        module.ROOT = ROOT
        selected = [(name, module.full_prerequisites(command))
                    for name, command, _ in module.full_steps(module.workflow_steps())
                    if any(module.full_prerequisites(command))]
        self.assertEqual(selected, [
            ('Validate token resolution (build --check)', (True, False, False, False)),
            ('Full build for hook validation', (True, False, False, False)),
            ('Project procedure and resident composition', (True, True, False, False)),
            ('Hook scenario tests', (False, False, True, True)),
        ])

    def selected_hooks(self):
        self.workflow([{'name': 'early marker', 'run': 'touch workflow-started'},
                       {'name': 'hook fixtures', 'run': 'bash hooks/_test/ticket_required.test.sh'}])

    def test_full_git_feature_failure_precedes_all_steps(self):
        self.workflow([{'name': 'early marker', 'run': 'touch workflow-started'},
                       {'name': 'hook fixtures', 'run': 'files=(hooks/_test/*.test.sh)\nfor f in "${files[@]}"; do bash "$f"; done'}])
        binary, python, env = self.runtime()
        self.shim(binary, 'git', 'cat')  # Accepts config syntax but does not strip comments.
        result = self.run_adapter(env=env, interpreter=python)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('core.commentString', result.stderr)
        self.assertIn('hook fixtures', result.stderr)
        self.assertIn(str(binary / 'git'), result.stderr)
        self.assertFalse((self.root / 'workflow-started').exists())

    def test_unused_full_tools_and_preview_are_not_required(self):
        binary, python, env = self.runtime()
        sentinel = self.root / 'unused-tool-called'
        for tool in ('git', 'base64', 'python3'):
            if tool == 'python3':
                continue
            self.shim(binary, tool, 'touch ' + shlex.quote(str(sentinel)) + '; exit 99')
        self.workflow([{'name': 'synthetic', 'run': 'touch synthetic-ran\npython3 -c "pass"\nprintf "%s\\n" "bin/build.py" "hooks/_test/ticket_required.test.sh"'}])
        result = self.run_adapter(env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / 'synthetic-ran').exists())
        self.selected_hooks()
        result = self.run_adapter('--list', env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(sentinel.exists())
        self.assertFalse((self.root / 'workflow-started').exists())

    def test_check_and_refresh_do_not_run_full_preflight(self):
        binary, python, env = self.runtime()
        bash = shutil.which('bash')
        self.shim(binary, 'bash', 'case "$*" in *"if (false | true)"*) echo "full probe invoked" >&2; exit 91;; esac\nexec ' + shlex.quote(bash) + ' "$@"')
        names = ['build.py', 'skill-inventory.py', 'generated-source-authority.py',
                 'kernel-budget.py', 'progressive-loading-metrics.py',
                 'review-risk-metrics.py', 'language-scope.py', 'data-scope.py',
                 'extra-one.py', 'extra-two.py']
        for name in names:
            (self.root / 'bin' / name).write_text('pass\n')
        self.workflow([{'name': name, 'run': 'python3 bin/' + name + ' --check'} for name in names])
        for mode in ('check', 'refresh'):
            with self.subTest(mode=mode):
                result = self.run_adapter('--mode', mode, env=env, interpreter=python)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_python_symlink_spelling_mismatch_is_not_realpathed_away(self):
        binary, python, env = self.runtime()
        self.assertEqual(Path(python).resolve(), Path(sys.executable).resolve())
        (self.root / 'bin/_test').mkdir()
        (self.root / 'bin/_test/selected_registration_test.py').write_text('pass\n')
        self.workflow([{'name': 'early marker', 'run': 'touch workflow-started'},
                       {'name': 'registration fixture', 'run': 'python3 bin/_test/selected_registration_test.py'}])
        result = self.run_adapter(env=env)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('symlink spellings are significant', result.stderr)
        self.assertIn(python, result.stderr)
        self.assertFalse((self.root / 'workflow-started').exists())
        result = self.run_adapter(env=env, interpreter=python)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / 'workflow-started').exists())

    def test_child_dependency_is_checked_in_step_environment(self):
        binary, python, env = self.runtime()
        other = self.root / 'other-runtime'
        other.mkdir()
        self.shim(other, 'python3', 'echo "pinned validation dependency unavailable" >&2; exit 7')
        self.workflow([{'name': 'early marker', 'run': 'touch workflow-started'},
                       {'name': 'build fixture', 'run': 'python3 bin/build.py',
                        'env': {'PATH': str(other) + os.pathsep + env['PATH']}}])
        result = self.run_adapter(env=env, interpreter=python)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('pinned validation dependency unavailable', result.stderr)
        self.assertIn(str(other / 'python3'), result.stderr)
        self.assertFalse((self.root / 'workflow-started').exists())

    def test_bash_feature_failure_is_not_a_version_guess(self):
        self.selected_hooks()
        binary, python, env = self.runtime()
        bash = shutil.which('bash')
        self.shim(binary, 'bash', 'case "$*" in *"a=(ok)"*) echo "array feature unavailable" >&2; exit 9;; esac\nexec ' + shlex.quote(bash) + ' "$@"')
        result = self.run_adapter(env=env, interpreter=python)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('Bash shell features', result.stderr)
        self.assertIn('array feature unavailable', result.stderr)
        self.assertFalse((self.root / 'workflow-started').exists())

    def test_full_children_use_physical_temporary_directory(self):
        physical = self.root / 'physical-temp'
        physical.mkdir()
        alias = self.root / 'temp-alias'
        alias.symlink_to(physical, target_is_directory=True)
        code = "import json,os,tempfile;from pathlib import Path;Path('temp.json').write_text(json.dumps([os.environ['TMPDIR'],os.environ['RUNNER_TEMP'],tempfile.mkdtemp()]))"
        self.workflow([{'name': 'temporary paths', 'run': shlex.join([sys.executable, '-c', code])}])
        result = self.run_adapter(env={**os.environ, 'TMPDIR': str(alias)})
        self.assertEqual(result.returncode, 0, result.stderr)
        tmpdir, runner, created = json.loads((self.root / 'temp.json').read_text())
        self.assertEqual(tmpdir, runner)
        self.assertEqual(str(Path(runner).parent), str(physical))
        self.assertEqual(str(Path(created).parent), runner)

    def test_darwin_base64_probe_is_platform_and_selection_bound(self):
        # Execute real child shims while selecting Darwin behavior independently
        # of the test host. No mutation of the process-wide sys.platform.
        module = self.load_adapter()
        binary, python, env = self.runtime()
        called = self.root / 'base64-called'
        self.shim(binary, 'base64', 'touch ' + shlex.quote(str(called)) + '; echo "invalid option -- D" >&2; exit 1')
        environment = {**env, 'RUNNER_TEMP': str(self.root)}
        with mock.patch.object(module, 'sys') as runtime:
            runtime.executable = python
            runtime.platform = 'linux'
            module.preflight_full([('reader', 'bash hooks/_test/reader_git_safety.test.sh', {})], environment)
            self.assertFalse(called.exists())
            runtime.platform = 'darwin'
            module.preflight_full([('synthetic', 'true', {})], environment)
            self.assertFalse(called.exists())
            with self.assertRaisesRegex(ValueError, 'Darwin base64 -D -i/-o'):
                module.preflight_full([('reader', 'bash hooks/_test/reader_git_safety.test.sh', {})], environment)
            self.assertTrue(called.exists())

    def test_preview_does_not_execute(self):
        self.workflow([{'name': 'marker', 'run': 'touch should-not-exist'}])
        result = self.run_adapter('--list')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / 'should-not-exist').exists())

    def test_first_failure_stops_command_and_later_steps(self):
        self.workflow([{'name': 'first', 'run': 'false\ntouch after-failure'},
                       {'name': 'later', 'run': 'touch later-step'}])
        result = self.run_adapter()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('FAILED: first', result.stderr)
        self.assertFalse((self.root / 'after-failure').exists())
        self.assertFalse((self.root / 'later-step').exists())

    def test_runtime_git_and_shell_startup_are_isolated(self):
        code = "import json,os;from pathlib import Path;Path('environment.json').write_text(json.dumps({k:os.environ.get(k) for k in ['GIT_DIR','GIT_CONFIG_GLOBAL','GIT_CONFIG_SYSTEM','CRAFT_SESSION_DIR','BASH_ENV','RUNNER_TEMP']}))"
        self.workflow([{'name': 'environment', 'run': shlex.join([sys.executable, '-c', code])}])
        startup = self.root / 'startup.sh'
        startup.write_text('touch startup-was-executed\n')
        env = {**os.environ, 'GIT_DIR': '/not-a-repository',
               'GIT_CONFIG_GLOBAL': str(self.root / 'operator.gitconfig'),
               'CRAFT_SESSION_DIR': '/not-the-current-session', 'BASH_ENV': str(startup)}
        result = self.run_adapter(env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        observed = json.loads((self.root / 'environment.json').read_text())
        for key in ('GIT_DIR', 'CRAFT_SESSION_DIR', 'BASH_ENV'):
            self.assertIsNone(observed[key])
        self.assertEqual(observed['GIT_CONFIG_GLOBAL'], os.devnull)
        self.assertEqual(observed['GIT_CONFIG_SYSTEM'], os.devnull)
        self.assertTrue(observed['RUNNER_TEMP'])
        self.assertFalse((self.root / 'startup-was-executed').exists())

    def test_ambiguous_and_empty_workflows_fail(self):
        cases = [[], [{'name': 'empty', 'run': ''}],
                 [{'name': 'conditional', 'run': 'true', 'if': 'unknown'}],
                 [{'name': 'expression', 'run': 'echo ${{ unknown }}'}],
                 [{'name': 'environment', 'run': 'true', 'env': {'UNKNOWN': '${{ unknown }}'}}]]
        for steps in cases:
            with self.subTest(steps=steps):
                self.workflow(steps)
                result = self.run_adapter('--list')
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_unreadable_malformed_and_wrong_dependency_fail(self):
        workflow = self.root / '.github/workflows/build-and-publish.yml'
        result = self.run_adapter('--list')
        self.assertEqual(result.returncode, 2)
        for content in ('[invalid', '[]', '{}', 'jobs: {validate: {steps: wrong}}',
                        'jobs: {validate: {steps: [false]}}',
                        'jobs: {validate: {steps: [{name: bad, run: false}]}}',
                        'jobs: {validate: {steps: [{name: bad, run: "true", env: []}]}}'):
            with self.subTest(content=content):
                workflow.write_text(content)
                result = self.run_adapter('--list')
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.workflow([{'name': 'valid', 'run': 'true'}])
        dependency = self.root / 'bin/frontmatter_validation.py'
        dependency.write_text(dependency.read_text().replace('PyYAML==6.0.3', 'PyYAML==0.0.0'))
        result = self.run_adapter('--list')
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('pinned validation dependency', result.stderr)

    def test_step_budget_expires_without_reporting_success(self):
        self.workflow([{'name': 'slow', 'run': shlex.join([sys.executable, '-c', 'import time; time.sleep(5)'])}])
        result = self.run_adapter('--step-timeout', '1')
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('timed out', result.stderr)
        self.assertNotIn('Local validation passed', result.stdout)
        for value in ('0', '3601'):
            result = self.run_adapter('--step-timeout', value)
            self.assertEqual(result.returncode, 2)

    def test_step_timeout_cancels_background_descendants(self):
        child = "import time;from pathlib import Path;time.sleep(2);Path('late-mutation').write_text('survived')"
        command = shlex.join([sys.executable, '-c', child]) + ' >/dev/null 2>&1 & wait'
        self.workflow([{'name': 'background child', 'run': command}])
        result = self.run_adapter('--step-timeout', '1')
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('timed out', result.stderr)
        time.sleep(2)
        self.assertFalse((self.root / 'late-mutation').exists(), 'timed-out descendant kept modifying the repository')



if __name__ == '__main__':
    unittest.main()
