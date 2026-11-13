#!/usr/bin/env python3
"""One enrolled scanner source is selected by both actual hook stacks."""
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import unittest
import registered_receipt_provider_test as fixture

ROOT=Path(__file__).resolve().parents[2]

class RegisteredScanner(unittest.TestCase):
    def setUp(self):
        self.f=fixture.ReceiptProviders();self.f.setUp();self.addCleanup(self.f.doCleanups)
        for relative in ['scan.sh','scan_ast.py','scan_snapshot.py']:
            target=self.f.workspace/'skills/detect-ai-fingerprints'/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/'skills/detect-ai-fingerprints'/relative,target)
        self.tmp=self.f.host.session/'data/scanner';self.tmp.mkdir(parents=True,mode=0o700)
        gate=self.f.task/'think-gate.json';data=json.loads(gate.read_text());data['status']='reviewing';data['scope_paths'].append(str(self.tmp));gate.write_text(json.dumps(data))

    def command(self,producer=None):
        return shlex.join(['python3','-I','-B',str(producer or self.f.workspace/'hooks/lib/scanner-exec.py'),'--repo',str(self.f.project),'--think-gate',str(self.f.task/'think-gate.json'),'--tmp-root',str(self.tmp),'--staged'])

    def test_both_registered_stacks_select_host_and_reject_clone_or_corrupt_closure(self):
        self.f.both(self.command())
        self.f.both(self.command(self.f.project/'hooks/lib/scanner-exec.py'),code=2)
        helper=self.f.workspace/'skills/detect-ai-fingerprints/scan_ast.py'
        helper.write_bytes(helper.read_bytes()+b'\n# drift\n')
        self.f.both(self.command(),code=2)

    def test_mutable_capability_is_rejected_before_its_code_executes(self):
        helper=self.f.workspace/'hooks/lib/scanner_capability.py'
        marker=self.f.host.session/'data/must-not-execute'
        helper.write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("wrong")\n')
        self.f.both(self.command(),code=2)
        result=subprocess.run(shlex.split(self.command()),env=self.f.env,capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        self.assertFalse(marker.exists())

    def test_missing_capability_is_incomplete_without_executing_other_code(self):
        helper=self.f.workspace/'hooks/lib/scanner_capability.py';helper.unlink()
        self.f.both(self.command(),code=2)
        result=subprocess.run(shlex.split(self.command()),env=self.f.env,capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        self.assertIn('incomplete',result.stderr)

    def test_broken_binding_and_registration_do_not_choose_another_producer(self):
        self.f.both(self.command(),code=2,payload_change={'session_id':'ffe0010a-0000-4000-8000-000000000099'})
        self.f.host.receipt_path.unlink()
        self.f.both(self.command(),code=2)

if __name__=='__main__':unittest.main()
