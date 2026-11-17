#!/usr/bin/env python3
"""Exercise publisher eligibility with private Git histories and a fixture host API."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = 'siege-analytics/claude-configs-public'


def fixture_environment(base):
    home = base / 'home'
    home.mkdir()
    xdg = home / 'xdg'
    xdg.mkdir()
    global_config, system_config = home / 'gitconfig', home / 'system-gitconfig'
    global_config.write_text('')
    system_config.write_text('')
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(('GIT_', 'GH_')) and key != 'GITHUB_TOKEN'}
    environment.update(HOME=str(home), XDG_CONFIG_HOME=str(xdg),
                       GH_CONFIG_DIR=str(home / 'gh'), GIT_CONFIG_GLOBAL=str(global_config),
                       GIT_CONFIG_SYSTEM=str(system_config), GIT_CONFIG_NOSYSTEM='1')
    return environment


class Publication(unittest.TestCase):
    def git(self, root, *arguments):
        return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null',
                                        '-c', 'commit.gpgsign=false', '-C', str(root), *arguments],
                                       stderr=subprocess.PIPE, text=True, timeout=20,
                                       env=self.environment).strip()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.environment = fixture_environment(self.base)
        self.remote, self.source, self.publisher = [self.base / n for n in ('remote.git', 'source', 'publisher')]
        self.remote.mkdir(); self.source.mkdir()
        self.git(self.remote, 'init', '--bare')
        self.git(self.source, 'init', '-b', 'main')
        self.git(self.source, 'config', 'user.name', 'Fixture')
        self.git(self.source, 'config', 'user.email', 'fixture@example.invalid')
        (self.source / 'VERSION').write_text('1.0.0\n')
        self.git(self.source, 'add', 'VERSION')
        self.git(self.source, 'commit', '-m', 'Initial private fixture')
        self.old = self.git(self.source, 'rev-parse', 'HEAD')
        self.git(self.source, 'remote', 'add', 'origin', str(self.remote))
        self.git(self.source, 'push', 'origin', 'main')
        self.git(self.base, 'clone', '--branch', 'main', str(self.remote), str(self.publisher))
        self.git(self.publisher, 'config', 'url.' + self.remote.as_uri() + '.insteadOf',
                 'https://github.com/' + REPOSITORY + '.git')
        directory = self.publisher / 'scripts/ci'
        directory.mkdir(parents=True)
        shutil.copyfile(ROOT / 'scripts/ci/main-publication.py', directory / 'main-publication.py')
        self.bin = self.base / 'bin'; self.bin.mkdir()
        fixture = self.bin / 'gh'
        fixture.write_text('#!' + sys.executable + '\n' +
            'import json,subprocess,sys\nfrom pathlib import Path\n' +
            'base=Path(' + repr(str(self.base)) + ')\n' +
            "assert sys.argv[1:7]==['api','--hostname','github.com','--method','GET','-H']\n" +
            "if (base/'api-fail').exists():\n print('PRIVATE_FAULT',file=sys.stderr);sys.exit(17)\n" +
            "if (base/'api-malformed').exists():\n print('{}');sys.exit(0)\n" +
            "sha=subprocess.check_output(['git','-C',str(base/'remote.git'),'rev-parse','refs/heads/main'],text=True,timeout=10).strip()\n" +
            "print(json.dumps({'ref':'refs/heads/main','object':{'type':'commit','sha':sha}}))\n")
        fixture.chmod(0o700)
        self.output, self.summary = self.base / 'output', self.base / 'summary'

    def advance(self):
        (self.source / 'second').write_text('Newer private source\n')
        self.git(self.source, 'add', 'second')
        self.git(self.source, 'commit', '-m', 'Advance private Main')
        self.git(self.source, 'push', 'origin', 'main')
        return self.git(self.source, 'rev-parse', 'HEAD')

    def run_guard(self, source=None):
        environment = dict(self.environment, GITHUB_SHA=source or self.old, GITHUB_REPOSITORY=REPOSITORY,
                           GITHUB_OUTPUT=str(self.output), GITHUB_STEP_SUMMARY=str(self.summary),
                           PATH=str(self.bin) + os.pathsep + self.environment.get('PATH', ''))
        return subprocess.run([sys.executable, str(self.publisher / 'scripts/ci/main-publication.py')],
                              cwd=self.publisher, env=environment, capture_output=True, text=True, timeout=30)

    def test_current_source_remains_eligible(self):
        result = self.run_guard()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('status=current\n', self.output.read_text())
        self.assertIn('CURRENT', self.summary.read_text())

    def test_older_validation_finishing_late_uses_fresh_host_head(self):
        new = self.advance()
        self.assertEqual(self.git(self.publisher, 'rev-parse', 'origin/main'), self.old)
        result = self.run_guard()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('status=superseded\n', self.output.read_text())
        self.assertIn('current_main=' + new, self.output.read_text())
        self.assertEqual((self.publisher / 'VERSION').read_text(), '1.0.0\n')

    def test_newer_first_output_refs_are_not_replaced(self):
        new = self.advance()
        self.git(self.remote, 'update-ref', 'refs/heads/release/flat', new)
        self.git(self.remote, 'update-ref', 'refs/tags/fixture-release', new)
        before = self.git(self.remote, 'show-ref')
        result = self.run_guard()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('status=superseded\n', self.output.read_text())
        self.assertEqual(self.git(self.remote, 'show-ref'), before)
        self.assertIn('not an immutable artifact handoff', self.summary.read_text())

    def test_unverifiable_host_fails_before_outputs_or_version_changes(self):
        (self.base / 'api-fail').touch()
        result = self.run_guard()
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('PRIVATE_FAULT', result.stdout + result.stderr)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.summary.exists())
        self.assertEqual((self.publisher / 'VERSION').read_text(), '1.0.0\n')

    def test_malformed_host_ref_and_checkout_mismatch_fail_closed(self):
        (self.base / 'api-malformed').touch()
        self.assertEqual(self.run_guard().returncode, 2)
        (self.base / 'api-malformed').unlink()
        self.assertEqual(self.run_guard('0' * 40).returncode, 2)
        self.assertFalse(self.output.exists())

    def test_divergent_canonical_history_is_not_treated_as_superseded(self):
        self.git(self.source, 'checkout', '--orphan', 'unrelated')
        self.git(self.source, 'commit', '-m', 'Unrelated private history')
        unrelated = self.git(self.source, 'rev-parse', 'HEAD')
        self.git(self.source, 'push', 'origin', 'HEAD:refs/heads/unrelated')
        self.git(self.remote, 'update-ref', 'refs/heads/main', unrelated)
        result = self.run_guard()
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.output.exists())


class FixtureIsolation(unittest.TestCase):
    def test_hostile_caller_git_routing_and_config_remain_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            environment = fixture_environment(base)
            caller = base / 'caller'
            caller.mkdir()
            def git(*arguments):
                return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null',
                                                '-C', str(caller), *arguments],
                                               env=environment, stderr=subprocess.PIPE,
                                               text=True, timeout=20)
            git('init')
            git('config', 'user.name', 'Original caller')
            git('config', 'user.email', 'caller@example.invalid')
            snapshot = {str(p.relative_to(caller)): p.read_bytes()
                        for p in caller.rglob('*') if p.is_file()}
            foreign_index = base / 'foreign-index'
            for routing in ({'GIT_DIR': str(caller / '.git')},
                            {'GIT_INDEX_FILE': str(foreign_index)}):
                with self.subTest(routing=list(routing)):
                    hostile = dict(environment, **routing, GIT_CONFIG_COUNT='1',
                                   GIT_CONFIG_KEY_0='user.name', GIT_CONFIG_VALUE_0='Injected caller')
                    result = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                                             'Publication.test_current_source_remains_eligible'],
                                            env=hostile, capture_output=True, text=True, timeout=40)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual({str(p.relative_to(caller)): p.read_bytes()
                                      for p in caller.rglob('*') if p.is_file()}, snapshot)
                    self.assertFalse(foreign_index.exists())


class Workflow(unittest.TestCase):
    def test_guard_is_inside_mutex_before_every_version_and_output_step(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/build-and-publish.yml').read_text())
        job = workflow['jobs']['publish']
        self.assertEqual(job['concurrency'], {'group': 'publish-release-branches', 'cancel-in-progress': False})
        self.assertEqual(job['needs'], 'validation-complete')
        steps = job['steps']
        guards = [i for i, step in enumerate(steps) if step.get('id') == 'publication']
        self.assertEqual(len(guards), 1, 'publisher needs one current-Main eligibility guard')
        index = guards[0]
        self.assertEqual(steps[index]['run'], 'python3 scripts/ci/main-publication.py')
        self.assertLess(index, next(i for i, step in enumerate(steps) if step.get('id') == 'resolve-version'))
        self.assertGreater(len(steps[index + 1:]), 5)
        for step in steps[index + 1:]:
            self.assertEqual(step.get('if'), "steps.publication.outputs.status == 'current'", step)
        self.assertEqual(job['outputs'], {'publication_status': '${{ steps.publication.outputs.status }}'})


if __name__ == '__main__':
    unittest.main()
