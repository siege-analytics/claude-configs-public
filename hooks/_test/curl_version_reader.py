"""Transfer-free curl diagnostics through the shared parser and actual guard."""
import shlex
import unittest

import task_keyed_gates as fixture


class CurlVersion(unittest.TestCase):
    def setUp(self):
        self.f = fixture.Gates(); self.f.setUp(); self.addCleanup(self.f.tearDown)
        self.private = self.f.ws / 'sessions/one/data/capture'
        self.private.mkdir(parents=True)

    def test_exact_version_needs_no_task_even_after_private_cd(self):
        for command in ['curl -q --version',
                        'cd ' + shlex.quote(str(self.private)) + ' && curl -q --version']:
            with self.subTest(command=command):
                result = self.f.hook(command, cwd=self.private)
                self.assertEqual(result.returncode, 0, result.stderr)
                shape = fixture.r.action(command, str(self.private))
                self.assertTrue(shape['read_only'], shape)
                self.assertFalse(shape['investigation'], shape)
                self.assertEqual(shape['paths'], [])

    def test_transfer_config_output_and_dynamic_forms_are_not_readers(self):
        for command in ['curl --version', 'curl --version -q', 'curl -q',
                        'curl -q --version https://example.invalid',
                        'curl -q --version --url https://example.invalid',
                        'curl -q --version --config settings', 'curl -q -K settings --version',
                        'curl -q --version --output output', 'curl -q --version -O',
                        'curl -q --version --next https://example.invalid',
                        'curl -q --version "$OPTIONS"', 'curl -q $VERSION',
                        'curl -q $(echo --version)', 'curl -q --version *']:
            with self.subTest(command=command):
                self.assertFalse(fixture.r.action(command, str(self.f.a))['read_only'])
                self.assertEqual(self.f.hook(command, cwd=self.f.a).returncode, 2)

    def test_secondary_writes_keep_scope_and_real_task_checks(self):
        output = self.f.a / 'version.txt'
        commands = ['curl -q --version > ' + str(output),
                    'curl -q --version && touch ' + str(output),
                    'curl -q --version | tee ' + str(output)]
        for command in commands:
            with self.subTest(no_task=command):
                self.assertFalse(fixture.r.action(command, str(self.f.a))['read_only'])
                self.assertEqual(self.f.hook(command, cwd=self.f.a).returncode, 2)
        self.f.task('o/r#1321', self.f.a)
        for command in commands:
            with self.subTest(own_task=command):
                result = self.f.hook(command, cwd=self.f.a)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.f.hook(command.replace(str(output), str(self.f.b / 'foreign')),
                                             cwd=self.f.a).returncode, 2)

    def test_owned_output_from_unrelated_cwd_does_not_need_cwd_authority(self):
        self.f.task('o/r#1321', self.f.a)
        command = 'curl -q --version > ' + str(self.f.a / 'version.txt')
        result = self.f.hook(command, cwd=self.f.b)
        self.assertEqual(result.returncode, 0, result.stderr)
        shape = fixture.r.action(command, str(self.f.b))
        self.assertFalse(shape['investigation'], shape)
        self.assertEqual(shape['paths'], [str((self.f.a / 'version.txt').resolve())])
        self.assertEqual(self.f.hook(command.replace('/a/version.txt', '/b/version.txt'),
                                     cwd=self.f.a).returncode, 2)


if __name__ == '__main__':
    unittest.main()
