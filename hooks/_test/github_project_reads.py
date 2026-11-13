#!/usr/bin/env python3
"""Project prerequisites are reads; no gh command or network is executed."""
from pathlib import Path
import subprocess
import sys
import unittest

import task_keyed_gates as fixture

ROOT = Path(__file__).resolve().parents[2]


class ProjectReads(unittest.TestCase):
    def setUp(self):
        self.f = fixture.Gates(); self.f.setUp(); self.addCleanup(self.f.tearDown)

    def check(self, command, allowed):
        classifier = subprocess.run([sys.executable,str(ROOT/'hooks/lib/read-only-command.py'),command],
                                    cwd=self.f.repo,env=self.f.env,text=True,capture_output=True,timeout=10)
        gate=self.f.hook(command)
        self.assertEqual((classifier.returncode==0,gate.returncode),
                         (allowed,0 if allowed else 2),(command,classifier.stderr,gate.stdout+gate.stderr))

    def test_project_field_and_item_reads_need_no_task_gate(self):
        for verb in ('field-list','item-list'):
            with self.subTest(verb=verb):
                self.check('gh project '+verb+' 1 --owner electinfo --format json',True)
                self.check('gh project '+verb+' 1 --owner electinfo --format json | jq .',True)
        self.check('gh project list --owner electinfo',True)
        self.check('gh project view 1 --owner electinfo',True)

    def test_mutations_browser_host_switches_and_execution_remain_denied(self):
        for command in ['gh project item-edit --project-id PVT_x --id PVTI_x --field-id PVTSSF_x --single-select-option-id option',
                        'gh project item-delete 1 --owner electinfo --id PVTI_x','gh project delete 1 --owner electinfo',
                        'gh project field-delete --id PVTF_x', 'gh extension exec helper',
                        "gh api graphql -f 'query=mutation { x }'",'gh api /graphql --input mutation.json']:
            with self.subTest(command=command):self.check(command,False)
        for verb in ('field-list','item-list'):
            command='gh project '+verb+' 1 --owner electinfo'
            for unsafe in [command+' --web',command+' -w',command+' --hostname other.invalid',
                           command+' --hostname=other.invalid','gh --hostname other.invalid '+command[3:],
                           'GH_HOST=other.invalid '+command]:
                with self.subTest(command=unsafe):self.check(unsafe,False)

    def test_redirect_substitution_and_secondary_mutations_remain_denied(self):
        read='gh project item-list 1 --owner electinfo --format json'
        target=str(self.f.b/'marker')
        for command in [read+' > '+target,read+' | tee '+target,read+'; touch '+target,
                        read+'; gh project delete 1 --owner electinfo',
                        'gh project item-list $(touch '+target+') --owner electinfo']:
            with self.subTest(command=command):self.check(command,False)
        self.assertFalse(Path(target).exists())


if __name__=='__main__':unittest.main()
