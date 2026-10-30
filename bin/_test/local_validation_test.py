#!/usr/bin/env python3
"""Exercise actual child dispatch, failure propagation and local isolation."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

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

    def run_adapter(self, *args, env=None):
        return subprocess.run([sys.executable, str(self.root / 'bin/validate-local.py'),
                               '--mode', 'full', *args], cwd=self.root,
                              env=env, text=True, capture_output=True, timeout=30)

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
