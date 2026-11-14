#!/usr/bin/env python3
"""Publication distinguishes test fixture SQL from production transformation work."""
import os
import subprocess
import unittest

import lean_publication_review as reviews


class TransformationScope(unittest.TestCase):
    def fixture(self):
        fixture = reviews.PublicationReview('runTest')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
        return fixture

    def source(self, fixture, name, text):
        path = fixture.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def callbacks(self, fixture):
        yield fixture.hook()
        yield subprocess.run(['bash', str(reviews.ROOT / 'hooks/git/self-review.sh')],
                             input='refs/heads/feature\n', cwd=fixture.repo, env=fixture.env,
                             capture_output=True, text=True, timeout=20)

    def test_inherited_sql_test_fixture_does_not_require_production_probe(self):
        fixture = self.fixture()
        name = 'fec/tests/test_money_attestation_provider.py'
        self.source(fixture, name, 'SQL = "CREATE TABLE fixture (value INTEGER)"\nVALUE = 1\n')
        fixture.commit()
        self.source(fixture, name, 'SQL = "CREATE TABLE fixture (value INTEGER)"\nVALUE = 2\n')
        fixture.commit()
        for result in self.callbacks(fixture):
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_test_paths_do_not_require_production_transformation_evidence(self):
        for name in ('tests/seed.sql', 'package/__tests__/seed.sql', 'hooks/_test/seed.py',
                     'package/test_seed.py', 'test_seed.py', 'package/seed.test.ts', 'package/seed.spec.js'):
            with self.subTest(path=name):
                fixture = self.fixture()
                fixture.commit()
                self.source(fixture, name, 'CREATE TABLE fixture (value INTEGER);\n')
                fixture.commit()
                for result in self.callbacks(fixture):
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_production_and_mixed_changes_still_require_real_probe_evidence(self):
        for name, text in (('pipelines/schema.sql', 'SELECT 1;\n'),
                           ('pipelines/model.sql.j2', 'SELECT 1;\n'),
                           ('pipelines/load step.py', 'SQL = "CREATE TABLE results (n INTEGER)"\n'),
                           ('testsuite/load.py', 'SQL = "CREATE TABLE results (n INTEGER)"\n'),
                           ('pipelines/runtime.test.assets/model.sql', 'SELECT 1;\n'),
                           ('pipelines/runtime.spec.assets/load.py', 'SQL = "INSERT INTO results VALUES (1)"\n'),
                           ('pipelines/test_fixture.py.assets/load.py', 'SQL = "CREATE TABLE results (n INTEGER)"\n'),
                           ('pipelines/load.py', 'SQL = "INSERT INTO results VALUES (1)"\n')):
            with self.subTest(path=name):
                fixture = self.fixture()
                fixture.commit()
                self.source(fixture, 'fec/tests/test_seed.py', 'SQL = "CREATE TABLE fixture (n INTEGER)"\n')
                self.source(fixture, name, text)
                fixture.commit()
                for result in self.callbacks(fixture):
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('missing both', result.stderr)


if __name__ == '__main__':
    unittest.main()
