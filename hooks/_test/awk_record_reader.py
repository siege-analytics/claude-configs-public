#!/usr/bin/env python3
"""Complete inline awk record-copy grammar and real guard effect boundaries."""
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess
import sys
import unittest

import task_keyed_gates as fixtures
from task_keyed_gates import ROOT, craft_payload

spec = importlib.util.spec_from_file_location('awk_reader', ROOT / 'hooks/lib/read-only-command.py')
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
PROGRAM = '/^## / {release=$0} /^### / {category=$0} /target phrase/ {print NR, release, category}'

class RecordReader(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.Gates(); self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.source = self.f.repo / 'records.txt'
        self.source.write_text('## Release\n### Fixes\ntarget phrase\n')

    def classify(self, command):
        return subprocess.run([sys.executable, str(ROOT / 'hooks/lib/read-only-command.py'), command],
                              text=True, capture_output=True, env=self.f.env, timeout=10)

    def test_actual_output_and_complete_guard_chain(self):
        command = '/usr/bin/awk ' + shlex.quote(PROGRAM) + ' ' + shlex.quote(str(self.source))
        result = subprocess.run(['/usr/bin/awk', PROGRAM, str(self.source)], text=True,
                                capture_output=True, env=self.f.env, timeout=10)
        self.assertEqual((result.returncode, result.stdout), (0, '3 ## Release ### Fixes\n'))
        self.assertEqual(self.classify(command).returncode, 0)
        template = json.loads((ROOT / 'hooks/settings-snippet.json').read_text())
        hooks = [hook for group in template['hooks']['PreToolUse'] if group['matcher'] == 'Bash'
                 for hook in group['hooks']]
        self.assertEqual(len(hooks), 16)
        payload = json.dumps(craft_payload(tool_name='Bash', cwd=str(self.f.repo), tool_input={'command':command}))
        for hook in hooks:
            path = hook['command'].replace('/path/to/claude-configs-public', str(ROOT))
            with self.subTest(hook=path):
                checked = subprocess.run(['bash', path], input=payload, text=True, capture_output=True,
                                         env=self.f.env, timeout=30)
                self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def test_program_and_argument_negatives_never_execute(self):
        for args in [[], ['-f', str(self.source)], ['-v', 'x=1', PROGRAM],
                     [PROGRAM, 'var=value'], [PROGRAM, '-option'],
                     [PROGRAM, '/inet/tcp/0/host/80']]:
            with self.subTest(args=args): self.assertFalse(reader.awk_ok(args))
        programs = ['{system("touch marker")}', '{print NR > "out"}', '{print NR | "cat"}',
                    '{getline x}', '{x=$0; print length(x)}', '{ENVIRON=$0; print NR}',
                    '{x=$0} END {print x}', '{x=$0; print x} trailing',
                    '/x/ {x=$0; print x}; function f() {}', '{print NR} @include "x"',
                    '{x=$0; print x} {print NR; exit}', '{print NR}\n{print NR}',
                    '{x=$0; print x; x++}', '{print NR;}', '{x=$0; print x} >out']
        # A trailing statement separator is harmless and parsed.
        programs.remove('{print NR;}')
        for program in programs:
            with self.subTest(program=program): self.assertFalse(reader.awk_ok([program]))
        for suffix in ['*.txt', '$(touch marker)', '`touch marker`']:
            with self.subTest(suffix=suffix):
                self.assertNotEqual(self.classify('awk ' + shlex.quote(PROGRAM) + ' ' + suffix).returncode, 0)
        self.assertFalse((self.f.repo/'marker').exists())

    def test_literal_filename_and_symlink_boundaries(self):
        link = self.f.repo / 'records-link'
        link.symlink_to(self.source)
        odd = self.f.repo / 'records;*.txt'
        odd.write_text(self.source.read_text())
        for path in (link, odd):
            command = 'awk ' + shlex.quote(PROGRAM) + ' ' + shlex.quote(str(path))
            with self.subTest(path=path):
                self.assertEqual(self.classify(command).returncode, 0)
                result = subprocess.run(['/usr/bin/awk', PROGRAM, str(path)], text=True,
                                        capture_output=True, env=self.f.env, timeout=10)
                self.assertEqual((result.returncode, result.stdout), (0, '3 ## Release ### Fixes\n'))
        mutation = 'awk ' + shlex.quote('{system("touch marker")}') + ' ' + shlex.quote(str(self.source))
        self.assertNotEqual(self.classify(mutation).returncode, 0)
        self.assertEqual(self.f.hook(mutation).returncode, 2)
        target = self.f.b / 'external'
        target.write_text('unchanged')
        output = self.f.a / 'linked-output'
        output.symlink_to(target)
        self.f.task('awk-record', self.f.a)
        command = 'awk ' + shlex.quote(PROGRAM) + ' ' + shlex.quote(str(self.source)) + ' > ' + shlex.quote(str(output))
        self.assertEqual(self.f.hook(command).returncode, 2)
        self.assertEqual(target.read_text(), 'unchanged')
        self.assertFalse((self.f.repo/'marker').exists())

    def test_owned_stdout_effect_and_foreign_output(self):
        command = 'awk ' + shlex.quote(PROGRAM) + ' ' + shlex.quote(str(self.source))
        self.assertEqual(self.f.hook(command).returncode, 0)
        self.f.task('awk-record', self.f.a)
        own = command + ' > ' + shlex.quote(str(self.f.a/'out'))
        foreign = command + ' > ' + shlex.quote(str(self.f.b/'out'))
        self.assertEqual(self.f.hook(own).returncode, 0)
        self.assertEqual(self.f.hook(foreign).returncode, 2)
        self.assertFalse((self.f.a/'out').exists())
        self.assertFalse((self.f.b/'out').exists())

if __name__ == '__main__': unittest.main()
