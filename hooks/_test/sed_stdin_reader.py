#!/usr/bin/env python3
"""Bounded stdin substitutions through classifier, hook and actual sed."""
import importlib.util
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import unittest

import task_keyed_gates as fixture

ROOT = Path(__file__).resolve().parents[2]
READER = ROOT / 'hooks/lib/read-only-command.py'
spec = importlib.util.spec_from_file_location('sed_reader', READER)
reader = importlib.util.module_from_spec(spec); spec.loader.exec_module(reader)
PIPELINE = '''gh run view 41975682106 --repo siege-analytics/siege_utilities --job 127073848171 --log-failed | grep -E "FAILED " | sed -E 's/^.*Z FAILED //' | cut -c1-150 | sort | head -50'''


class SedReader(unittest.TestCase):
    def setUp(self):
        self.f = fixture.Gates(); self.f.setUp(); self.addCleanup(self.f.tearDown)

    def verdict(self, command, allowed):
        result = subprocess.run([sys.executable, str(READER), command], cwd=self.f.repo,
                                env=self.f.env, text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode == 0, allowed, (command,result.stdout,result.stderr))
        actual = self.f.hook(command)
        self.assertEqual(actual.returncode, 0 if allowed else 2, actual.stdout+actual.stderr)

    def test_original_pipeline_and_literal_stdin_transforms_need_no_gate(self):
        for command in [PIPELINE,"sed 's/a/b/'", "sed -E -n 's/a/b/gp'", "sed -r 's/a/b/g'",
                        "sed " + shlex.quote(r's/a\/b/x/'), "sed " + shlex.quote(r's/a/\\/')]:
            with self.subTest(command=command):self.verdict(command,True)

    def test_execution_write_extra_expressions_and_files_still_deny(self):
        for args in [['-i','s/a/b/'],['-E','s/a/b/','-i'],['-f','script.sed'],
                     ['-e','s/a/b/'],['-e','s/a/b/','-e','e touch marker'],
                     ['s/a/b/','input'],['s/a/b/','-n'],['--expression=s/a/b/'],
                     ['s/a/b/e'],['s/a/b/w marker'],['s/a/b/;e touch marker'],
                     ['s/a/b/\ne touch marker'],['s/a/b/\r'],['s/a/b/g;w marker'],
                     [r's/a/\\/e'],[r's/a/\/'],['s#a#b#'],['-E','-E','s/a/b/']]:
            with self.subTest(args=args):self.verdict(shlex.join(['sed',*args]),False)
        self.assertFalse(reader.sed_ok(['s/a/b/\0']))

    def test_shell_companions_cannot_borrow_substitution_read_authority(self):
        target = self.f.b / 'marker'
        for command in ["sed 's/a/b/' > " + str(target), "sed 's/a/b/' | tee " + str(target),
                        "sed 's/a/b/'; touch " + str(target),
                        'sed "s/a/$(touch ' + str(target) + ')/"',
                        'sed "s/a/`touch ' + str(target) + '`/"']:
            with self.subTest(command=command):self.verdict(command,False)
        self.assertFalse(target.exists())

    def test_existing_numeric_print_grammar_unchanged(self):
        for args in [['-n','1p'],['-n','1,20p','input'],['-n','1,$p','input']]:
            self.assertTrue(reader.sed_ok(args),args)
        for args in [['-n','1p','-i'],['-n','1p','input','other'],['-n','1p','--follow-symlinks']]:
            self.assertFalse(reader.sed_ok(args),args)

    def test_actual_available_sed_transforms_and_write_flag_control(self):
        binaries = {p for p in ['/usr/bin/sed',shutil.which('sed'),shutil.which('gsed')] if p and Path(p).is_file()}
        self.assertTrue(binaries)
        for index, binary in enumerate(sorted(binaries)):
            with self.subTest(binary=binary):
                version = subprocess.run([binary,'--version'],text=True,capture_output=True,timeout=5)
                is_gnu = '(GNU sed)' in version.stdout
                print('actual sed fixture:',binary,'GNU' if is_gnu else 'system/non-GNU',flush=True)
                if is_gnu:
                    marker_e = self.f.ws / ('sed-execute-marker-' + str(index))
                    self.assertFalse(reader.sed_ok(['s/^//e']))
                    subprocess.run([binary,'s/^//e'],input='touch '+shlex.quote(str(marker_e))+'\n',text=True,capture_output=True,check=True,timeout=5)
                    self.assertTrue(marker_e.is_file())
                result = subprocess.run([binary,'-E','s/^.*Z FAILED //'],input='2026Z FAILED test_case\n',text=True,capture_output=True,timeout=5)
                self.assertEqual((result.returncode,result.stdout),(0,'test_case\n'))
                for expression,source,want in [(r's/a\/b/x/','a/b\n','x\n'),(r's/a/\\/','a\n','\\\n')]:
                    result = subprocess.run([binary,expression],input=source,text=True,capture_output=True,timeout=5)
                    self.assertEqual((result.returncode,result.stdout),(0,want))
                marker = self.f.ws / ('sed-write-' + str(index))
                expression = 's/a/b/w ' + str(marker)
                self.assertFalse(reader.sed_ok([expression]))
                subprocess.run([binary,expression],input='a\n',text=True,capture_output=True,check=True,timeout=5)
                self.assertEqual(marker.read_text(),'b\n')


if __name__=='__main__':unittest.main()
