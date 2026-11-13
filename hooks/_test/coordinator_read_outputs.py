#!/usr/bin/env python3
"""Admission-only GET/read chains cannot become coordinator status claims."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT/'hooks/bash/coordinator-status-guard.sh'
GET = "gh api 'repos/example/target/issues/651/comments?since=2026-11-13T05:03:41Z&per_page=100'"


class ReadOutputs(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='coordinator-read-output-')
        self.addCleanup(temporary.cleanup)
        self.cwd = Path(temporary.name)
        binaries = self.cwd/'bin'
        binaries.mkdir()
        self.marker = self.cwd/'unexpected-gh'
        gh = binaries/'gh'
        gh.write_text('#!/bin/sh\nprintf called >> ' + shlex.quote(str(self.marker)) + '\nexit 97\n')
        gh.chmod(0o755)
        (binaries/'python3').symlink_to(sys.executable)
        self.env = {key:value for key,value in os.environ.items()
                    if not key.startswith(('CRAFT_', 'CLAUDE_', 'CCP_', 'GIT_'))}
        self.env['PATH'] = str(binaries)+os.pathsep+os.environ['PATH']

    def guard(self, command, expected):
        payload = {'hook_event_name':'PreToolUse', 'tool_name':'Bash', 'cwd':str(self.cwd),
                   'tool_input':{'command':command}}
        result = subprocess.run(['bash',str(HOOK)],input=json.dumps(payload),cwd=self.cwd,
                                env=self.env,text=True,capture_output=True,timeout=30)
        self.assertEqual(result.returncode,expected,result.stdout+result.stderr)
        self.assertFalse(self.marker.exists(), 'No user command or network transport may run')
        return result

    def test_get_chain_receipt_paths_and_status_fields_are_data(self):
        receipts = ' '.join('blocked-receipt-'+str(n)+'.md' for n in range(8))
        for method in ('', '--method GET ', '-XGET '):
            with self.subTest(method=method):
                request = GET.replace('gh api ', 'gh api '+method, 1)
                command = request+" > MISSING-status.json && jq '{count:length}' MISSING-status.json"
                command += '; sha256sum '+receipts+"; jq '{task_id,status}' own-think-gate.json"
                self.guard(command,0)
        self.assertFalse((self.cwd/'MISSING-status.json').exists())

    def test_quoted_operation_text_and_fd_duplication_stay_data(self):
        self.guard(GET+" > blocked.json 2>&1 && jq '{text:\"gh issue close 651 | blocked\"}' blocked.json",0)
        self.guard("echo 'gh issue close missing' >> status.txt",0)

    def test_later_transitions_and_api_writes_cannot_borrow_first_get(self):
        writes = [
            "gh issue close 651 -R example/target --reason 'not planned'",
            'gh issue reopen 651 -R example/target',
            "gh api repos/example/target/issues/651/comments --method POST -f 'body=Status: blocked.'",
            "gh api --method=POST repos/example/target/issues/651/comments --raw-field 'body=Status: blocked.'",
            'gh api repos/example/target/issues/651 -XPATCH -f state=closed',
            'gh api -iXPATCH repos/example/target/issues/651 -F state=closed',
        ]
        for operation in writes:
            with self.subTest(operation=operation):
                self.guard(GET+' && '+operation,2)

    def test_supported_wrappers_do_not_hide_later_transitions(self):
        close = "gh issue close 651 -R example/target --reason 'not planned'"
        for command in (GET+' && timeout 5 '+close, 'timeout 5 '+GET+' && '+close,
                        GET+' && nice '+close, 'time '+GET+' && '+close,
                        GET+' && command env -i '+close,
                        GET+' && '+'timeout 5 '*33+close):
            with self.subTest(command=command):
                self.guard(command,2)
        self.guard('timeout 5 '+GET+' > blocked.json',0)
        self.guard(GET+" && timeout 5 echo 'gh issue close blocked'",0)

    def test_unknown_output_shapes_are_not_normalized_into_proof(self):
        for output in ('blocked*.json', '~/blocked.json', '"$blocked"', '$(printf blocked)'):
            with self.subTest(output=output):
                self.guard(GET+' > '+output,2)

    def test_globs_cannot_discard_detected_remote_transitions(self):
        read = 'gh pr view 651 -R example/target'
        close = 'gh issue close 651 -R example/target'
        for suffix in ('cat *.json', 'cat > blocked*.json', 'cat < blocked*.json'):
            with self.subTest(suffix=suffix):
                self.guard(read+' && '+close+' && '+suffix,2)
                self.guard(suffix+'; '+read+' && '+close,2)

    def test_existing_bare_reader_and_descriptive_metadata_are_unchanged(self):
        self.guard(GET,0)
        self.guard("gh issue comment 651 -R example/target --body 'Status: blocked.'",0)


if __name__ == '__main__':
    unittest.main()
