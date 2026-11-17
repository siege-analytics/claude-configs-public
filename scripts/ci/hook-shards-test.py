#!/usr/bin/env python3
"""Exercise actual file dispatch and fail-closed aggregate coverage."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('hook_shards', ROOT / 'scripts/ci/hook-shards.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


class HookShards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'hooks/_test').mkdir(parents=True)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        for index in range(9):
            (self.root / f'hooks/_test/{index}.test.sh').write_text('printf "%s\\n" ' + str(index) + ' >> executed\nexit 0\n')
        self.commit()
        self.env = {'GITHUB_SHA': self.git('rev-parse', 'HEAD'), 'GITHUB_RUN_ID': '123', 'GITHUB_RUN_ATTEMPT': '2'}

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, text=True, stderr=subprocess.PIPE, timeout=10).strip()

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')

    def needs(self):
        values = {'validate': h.record(self.root, self.env)}
        for i in range(h.SHARDS):
            r = h.record(self.root, self.env, i)
            r['statuses'] = {p: 0 for p in r['files']}
            values[f'hooks-{i}'] = r
        return {name: {'result': 'success', 'outputs': {'report': json.dumps(r)}} for name, r in values.items()}

    def test_deterministic_exhaustive_disjoint_execution(self):
        observed = []
        for i in range(h.SHARDS):
            report = h.record(self.root, self.env, i)
            observed.extend(report['files'])
            self.assertEqual(h.run(self.root, report), 0)
        self.assertEqual(sorted(observed), list(h.files(self.root)))
        self.assertEqual(len(observed), len(set(observed)))
        self.assertEqual(sorted((self.root / 'executed').read_text().splitlines()), list('012345678'))
        h.aggregate(self.root, self.env, self.needs())

    def test_nonfinal_failure_runs_later_files_and_fails(self):
        (self.root / 'hooks/_test/0.test.sh').write_text('exit 7\n')
        self.commit()
        self.env['GITHUB_SHA'] = self.git('rev-parse', 'HEAD')
        report = h.record(self.root, self.env, 0)
        self.assertEqual(h.run(self.root, report), 1)
        self.assertEqual(list(report['statuses'].values()), [7, 0, 0])
        self.assertEqual((self.root / 'executed').read_text().splitlines(), ['4', '8'])

    def test_empty_dirty_and_untracked_globs_refuse(self):
        with patch.object(Path, 'glob', return_value=[]):
            with self.assertRaisesRegex(ValueError, 'No files'):
                h.files(self.root)
        (self.root / 'hooks/_test/0.test.sh').write_text('exit 0\n')
        with self.assertRaises(subprocess.CalledProcessError):
            h.files(self.root)
        self.git('checkout', '--', 'hooks/_test/0.test.sh')
        (self.root / 'hooks/_test/new.test.sh').write_text('exit 0\n')
        with self.assertRaisesRegex(ValueError, 'tracked source'):
            h.files(self.root)

    def test_missing_skipped_cancelled_failed_dependency_refuses(self):
        for state in ('skipped', 'cancelled', 'failure', ''):
            needs = self.needs()
            needs['hooks-0']['result'] = state
            with self.subTest(state=state), self.assertRaises(ValueError):
                h.aggregate(self.root, self.env, needs)
        needs = self.needs()
        del needs['hooks-0']
        with self.assertRaises(ValueError):
            h.aggregate(self.root, self.env, needs)

    def test_wrong_source_run_coverage_and_status_refuse(self):
        for key, value in [('source', 'a' * 40), ('run', '999'), ('attempt', 3),
                           ('shard', 1), ('shard', False), ('files', {}), ('statuses', {}),
                           ('statuses', {'hooks/_test/0.test.sh': False})]:
            needs = self.needs()
            r = json.loads(needs['hooks-0']['outputs']['report'])
            r[key] = value
            needs['hooks-0']['outputs']['report'] = json.dumps(r)
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                h.aggregate(self.root, self.env, needs)
        needs = self.needs()
        r = json.loads(needs['hooks-0']['outputs']['report'])
        r['statuses'][next(iter(r['statuses']))] = False
        needs['hooks-0']['outputs']['report'] = json.dumps(r)
        with self.assertRaises(ValueError):
            h.aggregate(self.root, self.env, needs)
        needs = self.needs()
        needs['hooks-0']['outputs'] = {}
        with self.assertRaises(ValueError):
            h.aggregate(self.root, self.env, needs)

    def test_rerun_accepts_prior_success_only_same_run_and_source(self):
        needs = self.needs()
        for job in needs.values():
            r = json.loads(job['outputs']['report'])
            r['attempt'] = 1
            job['outputs']['report'] = json.dumps(r)
        h.aggregate(self.root, self.env, needs)
        with self.assertRaises(ValueError):
            h.aggregate(self.root, dict(self.env, GITHUB_SHA='a' * 40), needs)

    def test_cli_failure_exports_complete_report_and_aggregate_refuses(self):
        script = self.root / 'scripts/ci/hook-shards.py'
        script.parent.mkdir(parents=True)
        script.write_bytes((ROOT / 'scripts/ci/hook-shards.py').read_bytes())
        (self.root / 'hooks/_test/0.test.sh').write_text('exit 7\n')
        self.commit()
        self.env['GITHUB_SHA'] = self.git('rev-parse', 'HEAD')
        output = self.root / 'job-output'
        result = subprocess.run([os.sys.executable, str(script), 'run', '--shard', '0'],
                                cwd=self.root, env=dict(os.environ, **self.env, GITHUB_OUTPUT=str(output)),
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = json.loads(output.read_text().removeprefix('report='))
        self.assertEqual(list(report['statuses'].values()), [7, 0, 0])
        needs = self.needs()
        needs['hooks-0']['outputs']['report'] = json.dumps(report)
        with self.assertRaises(ValueError):
            h.aggregate(self.root, self.env, needs)

    def test_runner_launch_failure_is_not_success(self):
        report = h.record(self.root, self.env, 0)
        with patch.object(h.subprocess, 'run', side_effect=OSError('fixture launch failure')):
            self.assertEqual(h.run(self.root, report), 1)
        self.assertTrue(all(code == 1 for code in report['statuses'].values()))


if __name__ == '__main__':
    unittest.main()
