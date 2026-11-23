"""Actual draft-body status-domain regression; no candidate command executes."""
import json
from pathlib import Path
import shlex
import subprocess
import unittest
ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / 'hooks/bash/coordinator-status-guard.sh'
BODY = ROOT / 'hooks/_test/fixtures/draft-source-pr-body.md'

class DraftCreation(unittest.TestCase):
    def check(self, command):
        return subprocess.run(['bash', str(HOOK)], input=json.dumps({'cwd': str(ROOT), 'tool_input': {'command': command}}), text=True, capture_output=True, timeout=15)

    def test_original_body_proposal_and_cwd_prefix(self):
        proposal = "gh pr create --repo electinfo/fec-api --base develop --head feat/3133-panel-vintage-bound --draft --title 'bugfix: Bind fetched money panels to row vintage' --body-file " + shlex.quote(str(BODY))
        # This guard inspects status semantics only. Missing directories/files
        # remain actual shell/GitHub errors and UMG retains filesystem scope.
        for command in [proposal, 'cd ./sessions/261010-fleet-carbon/data/wt-fec-api-3133-panel-vintage && ' + proposal, 'cd missing-directory && ' + proposal, 'cd relative-directory && ' + proposal, proposal.replace(shlex.quote(str(BODY)), './sessions/261010-fleet-carbon/data/3133-panel-vintage-source-pr-body-20261114.md')]:
            with self.subTest(command=command):
                result = self.check(command)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_other_members_do_not_borrow_proposal_exemption(self):
        proposal = 'gh pr create --draft --body-file ' + shlex.quote(str(BODY))
        for command in [proposal + ' && gh pr close 31', 'gh pr close 31 && ' + proposal, 'cd x && ' + proposal + ' && gh pr ready 31', 'X=unsafe ' + proposal, 'cd x; ' + proposal, 'cd x || ' + proposal, 'cd x | ' + proposal, 'cd x & ' + proposal, 'cd "$TARGET" && ' + proposal, 'cd * && ' + proposal]:
            with self.subTest(command=command):
                result = self.check(command)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("BLOCKED:", result.stderr)
                if "gh pr close" in command or "gh pr ready" in command:
                    self.assertIn("mixed GitHub operations", result.stderr)

if __name__ == '__main__':
    unittest.main()
