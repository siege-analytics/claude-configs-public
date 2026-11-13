"""Literal body-file report prose and actual empty trailer diagnostics."""
import json
from pathlib import Path
import shutil
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / 'hooks/bash/coordinator-status-guard.sh'


class ArtifactResults(unittest.TestCase):
    # This component recognizes report shape, not authority from prose.
    # metadata_comment_reporting.py exercises own-Task/repository proof through
    # all sixteen hooks, including missing-Task, foreign and mixed-write denial.
    def hook(self, body, expected, action='comment'):
        with tempfile.TemporaryDirectory(prefix="artifact review ") as folder:
            path = Path(folder) / 'body.md'
            path.write_text(body)
            payload = {'cwd': str(ROOT), 'tool_input': {'command': f'gh issue {action} 1164 --body-file {shlex.quote(str(path))}'}}
            result = subprocess.run(['bash', str(HOOK)], input=json.dumps(payload), text=True,
                                    capture_output=True, timeout=20)
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
            return result

    def test_wrapped_hypothetical_field_is_not_project_completion(self):
        self.hook('## Pre-Mortem\nTicket: o/r#1164\nScenario:\n  The deployment could be complete without a verified owner.\n\nMitigation: retain the actual review.\n', 0)
        # Preserve historical B1 texts as metadata-operation controls, not word gates.
        self.hook('## Pre-Mortem\nTicket: o/r#1164\nScenario:\n  The deployment is complete without a verified owner.\n\nMitigation: retain the actual review.\n', 0)

    def test_unindented_completion_prose_is_plain_comment_data(self):
        self.hook('## Pre-Mortem\nTicket: o/r#1164\nScenario: tests may fail.\nDeployment complete.\n', 0)

    def test_conditional_and_factual_prose_needs_no_word_signoff(self):
        self.hook('## Pre-Mortem\nTicket: o/r#1164\nIf tests fail, stop rollout; the deployment is complete.\n', 0)

    def test_hypothetical_and_actual_status_prose_needs_no_word_evidence(self):
        self.hook('## Pre-Mortem\nTicket: o/r#1164\nScenario: owner approved main deployment.\nStatus: complete.\n', 0)
        self.hook('## Pre-Mortem\nTicket: o/r#1164\nScenario:\n  owner approved main deployment.\n\nStatus: complete.\n', 0)

    def test_actual_junior_senior_review_result_needs_no_deployment(self):
        self.hook('# Junior/Senior Review\nTicket: siege-analytics/claude-configs-public#1164\nReview completed: no blocking findings.\n', 0)

    def test_canonical_senior_checklist_result_needs_no_deployment(self):
        self.hook('## Senior adversarial checklist\nTicket: siege-analytics/claude-configs-public#1164\nThe named checks are complete. No blocking findings.\n', 0)

    def test_other_explicit_artifact_subject_results(self):
        for result in ['Investigation is complete.', 'The fact sheet is completed.', 'Audit done.',
                       'Checklist was complete.', 'Named checks were completed.',
                       'Checks completed: no findings.', 'Review has been completed.',
                       'Listed checks have been completed.', 'Adversarial checks are complete.']:
            with self.subTest(result=result):
                self.hook('## Investigation Fact Sheet\nTicket: o/r#1164\n' + result, 0)

    def test_project_and_deployment_words_do_not_change_comment_authority(self):
        for result in ['Review complete; deployment complete.', 'Named checks done; project ready.',
                       'Review has been completed; deployment complete.',
                       'Checks completed; project ready.',
                       'Investigation completed. Release shipped to production.',
                       'Deployment completed.', 'Release shipped to production.',
                       'Review complete, but the project is complete.',
                       'Review of the project is complete.']:
            with self.subTest(result=result):
                self.hook('## Junior/Senior Review\nTicket: o/r#1164\n' + result, 0)

    def test_unmarked_completion_is_plain_comment_data(self):
        self.hook('Review completed.\n', 0)

    def test_existing_hypothetical_fields_still_work(self):
        self.hook('## Pre-Mortem\nTicket: o/r#1164\nScenario: deployment could be complete with stale data.\nMitigation: if checks complete, compare actual state.\n', 0)
        self.hook('## Pre-Mortem\nTicket: o/r#1164\nScenario: deployment complete with stale data.\nMitigation: if checks complete, compare actual state.\n', 0)


class EmptyTrailers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        for relative in ['.githooks/commit-msg', 'bin/review-risk.py', 'catalog/review-risk-policy.json']:
            p = self.repo / relative
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, p)
        shutil.copytree(ROOT/'hooks/lib', self.repo/'hooks/lib')
        self.git('init', '-q')
        source = self.repo / 'hooks/git/x.sh'
        source.parent.mkdir(parents=True)
        source.write_text('#!/bin/sh\n')
        self.git('add', '.')

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.repo, capture_output=True,
                              text=True, check=True, timeout=10)

    def message(self, body):
        path = self.repo / 'message.txt'
        path.write_text(body)
        return subprocess.run(['bash', str(self.repo / '.githooks/commit-msg'), str(path)],
                              cwd=self.repo, text=True, capture_output=True, timeout=20)

    def full(self, self_review='fixture', source='https://example.com/review', negative='fixture', hostile='https://example.com/hostile'):
        return f'fix(#1168): fixture\n\nReview-Tier: C\nSelf-Review: {self_review}\nSelf-Review-Source: {source}\nHostile-Review: {hostile}\nNegative-Tests: {negative}\nFull-Suite: fixture\nCanary-Rollback: fixture\n'

    def test_three_empty_values_are_reported_in_one_rejection(self):
        result = self.message(self.full('', '', hostile=''))
        self.assertEqual(result.returncode, 1)
        for name in ['Self-Review', 'Self-Review-Source', 'Hostile-Review']:
            self.assertRegex(result.stdout + result.stderr, r'(?m)^\s+- ' + name + ':')
        self.assertEqual((result.stdout + result.stderr).count('BLOCKED:'), 1)

    def test_empty_review_and_source_cannot_pass_commit_then_fail_push(self):
        self.assertEqual(self.message(self.full('', '')).returncode, 1)

    def test_valid_fields_are_not_reported_missing(self):
        result = self.message(self.full(hostile=''))
        self.assertEqual(result.returncode, 1)
        self.assertNotRegex(result.stdout + result.stderr, r'(?m)^\s+- Self-Review(?:-Source)?:')
        self.assertEqual(self.message(self.full()).returncode, 0)
        self.assertEqual(self.message(self.full(negative='')).returncode, 0)

    def test_tier_A_no_review_exemption_is_unchanged(self):
        self.git('reset', '-q')
        p = self.repo / 'README.md'
        p.write_text('fixture\n')
        self.git('add', 'README.md')
        self.assertEqual(self.message('docs [task: authorized fixture] [no-review]\n\nReview-Tier: A\n').returncode, 0)
        self.assertEqual(self.message('docs [task: authorized fixture]\n\nReview-Tier: A\nSelf-Review:\n').returncode, 1)


if __name__ == '__main__':
    unittest.main()
