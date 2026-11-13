#!/usr/bin/env python3
"""Actual publication hook checks with compact and historical review records."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
COMPACT = '''## Assumptions
Goal source: assigned fixture behavior
Read hooks/git/self-review.sh and the affected guard; scope is the isolated fixture.
## Test plan
Focused positive and negative hook fixtures passed.
## Findings
None.
## Independent review
Separate reviewer result: plans/independent.md
'''
HISTORICAL = '''## Assumptions
Goal source: assigned fixture behavior
## Peer review
Actual local checks.
## Lead review
Independent findings assessed.
## Quantified claims
See test results.
'''

class PublicationReview(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='compact-publication-')
        self.addCleanup(self.directory.cleanup)
        self.repo = Path(self.directory.name)
        self.env = {k:v for k,v in os.environ.items() if not k.startswith(('CRAFT_', 'CLAUDE_', 'CCP_', 'GIT_'))}
        self.env.update(GIT_AUTHOR_NAME='Fixture',GIT_AUTHOR_EMAIL='fixture@example.invalid',
                        GIT_COMMITTER_NAME='Fixture',GIT_COMMITTER_EMAIL='fixture@example.invalid')
        self.git('init','-q')
        self.git('remote','add','origin','https://github.com/siege-analytics/fixture.git')
        (self.repo/'hooks/bash').mkdir(parents=True)
        (self.repo/'hooks/bash/example.sh').write_text('#!/bin/sh\nexit 0\n')
        (self.repo/'plans').mkdir()
        (self.repo/'plans/independent.md').write_text('Separate fixture reviewer: scoped behavior and negative cases inspected.\n')

    def git(self,*args):
        return subprocess.run(['git','-C',str(self.repo),*args],env=self.env,text=True,capture_output=True,check=True,timeout=20)

    def commit(self,artifact=COMPACT,review=True,review_path='plans/independent.md'):
        (self.repo/'plans/review.md').write_text(artifact)
        self.git('add','.')
        message='fix: assigned fixture #1\n\nReview-Tier: C\nSelf-Review: actual focused checks\nSelf-Review-Source: plans/review.md\n'
        if review: message+='Hostile-Review: '+review_path+'\n'
        self.git('commit','-q','-m',message)

    def hook(self):
        return subprocess.run(['bash',str(ROOT/'hooks/git/self-review.sh')],input=json.dumps({'cwd':str(self.repo),'tool_input':{'command':'git push'}}),
            env=self.env,text=True,capture_output=True,timeout=20)

    def native_hook(self):
        commit = self.git('rev-parse', 'HEAD').stdout.strip()
        return subprocess.run(['bash',str(ROOT/'hooks/git/pre-push-self-review.sh')],
            input=f'refs/heads/feature {commit} refs/heads/feature {"0" * 40}\n',
            cwd=self.repo,env=self.env,text=True,capture_output=True,timeout=20)

    def assert_publication(self, expected):
        for invoke in (self.hook, self.native_hook):
            result = invoke()
            code = 1 if invoke.__name__ == 'native_hook' and expected else expected
            self.assertEqual(result.returncode, code, invoke.__name__ + result.stdout + result.stderr)

    def test_fixture_git_locations_cannot_stage_or_commit_in_the_caller(self):
        before = self.git('status','--porcelain').stdout
        index = self.repo/'.git/index'
        self.assertFalse(index.exists())
        other = PublicationReview()
        self.addCleanup(other.doCleanups)
        with patch.dict(os.environ, {
            'GIT_DIR':str(self.repo/'.git'), 'GIT_WORK_TREE':str(self.repo),
            'GIT_INDEX_FILE':str(index), 'GIT_COMMON_DIR':str(self.repo/'.git'),
            'GIT_OBJECT_DIRECTORY':str(self.repo/'.git/objects')}):
            other.setUp()
            other.commit()
        self.assertEqual(Path(other.git('rev-parse','--show-toplevel').stdout.strip()).resolve(), other.repo.resolve())
        self.assertFalse(index.exists())
        self.assertEqual(self.git('status','--porcelain').stdout, before)

    def test_historical_trailing_whitespace_and_crlf_remain_publishable(self):
        artifact = HISTORICAL.replace('## Peer review','## Peer review \t').replace('\n','\r\n')
        self.commit(artifact)
        self.assert_publication(0)

    def test_compact_prose_unresolved_p1_blocks_both_publishers(self):
        self.commit(COMPACT.replace('None.', 'P1: incorrect behavior; resolution: unresolved'))
        self.assert_publication(2)

    def test_compact_p1_without_resolution_blocks_both_publishers(self):
        self.commit(COMPACT.replace('None.', '- P1: incorrect behavior'))
        self.assert_publication(2)

    def test_compact_fixed_p1_with_prose_context_is_publishable(self):
        self.commit(COMPACT.replace('None.', 'P1: incorrect behavior; Resolution: fixed\nVerified the boundary and retained the actual regression evidence.'))
        self.assert_publication(0)

    def test_table_finding_text_cannot_resolve_a_p1(self):
        self.commit(COMPACT.replace('None.', '| 1 | P1 | fixed-width parsing crashes | unresolved |'))
        self.assert_publication(2)

    def test_table_resolution_must_be_the_complete_cell(self):
        self.commit(COMPACT.replace('None.', '| 1 | P1 | Incorrect behavior | fixed later |'))
        self.assert_publication(2)

    def test_table_fixed_resolution_is_publishable(self):
        self.commit(COMPACT.replace('None.', '| 1 | P1 | fixed-width parsing crashes | FIXED |'))
        self.assert_publication(0)

    def test_escaped_finding_pipe_preserves_four_columns(self):
        self.commit(COMPACT.replace('None.', r'| 1 | P1 | Correct `a \| b` parsing | fixed |'))
        self.assert_publication(0)

    def test_escaped_pipe_cannot_hide_an_unresolved_resolution(self):
        self.commit(COMPACT.replace('None.', r'| 1 | P1 | Correct `a \| b` parsing | unresolved |'))
        self.assert_publication(2)

    def test_escaped_resolution_pipe_is_not_fixed(self):
        self.commit(COMPACT.replace('None.', r'| 1 | P1 | Incorrect parsing | fixed \| unresolved |'))
        self.assert_publication(2)

    def test_unescaped_extra_column_is_not_a_four_column_finding(self):
        self.commit(COMPACT.replace('None.', '| 1 | P1 | Incorrect parsing | fixed | unresolved |'))
        self.assert_publication(2)

    def test_fixed_table_row_without_trailing_separator_is_publishable(self):
        self.commit(COMPACT.replace('None.', '| 1 | P1 | Correct parsing | fixed'))
        self.assert_publication(0)

    def test_unresolved_table_row_without_trailing_separator_blocks(self):
        self.commit(COMPACT.replace('None.', '| 1 | P1 | Incorrect parsing | unresolved'))
        self.assert_publication(2)

    def test_documented_compact_resolution_is_publishable(self):
        contract = (ROOT/'skills/self-review/artifact-contract.md').read_text()
        example = next(line.split('one line: ', 1)[1] for line in contract.splitlines()
                       if 'For an actual P1 finding use one line: ' in line)
        self.commit(COMPACT.replace('None.', example.replace('<finding>', 'Incorrect behavior').replace('fixed|unresolved', 'fixed')))
        self.assert_publication(0)

    def test_hostile_review_directory_is_not_review_evidence(self):
        self.commit(review_path='plans')
        self.assert_publication(2)

    def test_tracked_review_symlinks_do_not_count_as_independent_evidence(self):
        for target in ('.', 'missing.md', 'independent.md'):
            with self.subTest(target=target):
                f = PublicationReview()
                f.setUp()
                try:
                    (f.repo/'plans/linked-review').symlink_to(target)
                    f.commit(review_path='plans/linked-review')
                    f.assert_publication(2)
                finally:
                    f.doCleanups()

    def test_compact_high_risk_review_needs_no_rank_premortem_or_runtime_deploy_stamp(self):
        self.commit()
        self.assert_publication(0)
        self.assertFalse((self.repo/'deploy-stamp.json').exists())

    def test_actual_independent_review_is_still_required(self):
        self.commit(review=False)
        result=self.hook();self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        self.assertIn('Hostile-Review',result.stdout+result.stderr)

    def test_unresolved_real_findings_block_publication(self):
        artifact=COMPACT.replace('## Findings\nNone.','## Findings\n| F1 | P1 | Incorrect normal behavior | unresolved |')
        self.commit(artifact)
        result=self.hook();self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        self.assertIn('unresolved P1',result.stdout+result.stderr)
        self.assertEqual(self.native_hook().returncode,1)

    def test_historical_valid_record_remains_publishable(self):
        self.commit(HISTORICAL)
        self.assert_publication(0)

    def test_historical_minimal_tier_b_record_needs_no_new_field(self):
        source = self.repo/'src'; source.mkdir()
        (self.repo/'hooks/bash/example.sh').rename(source/'example.py')
        (self.repo/'plans/review.md').write_text('## Assumptions\nExisting assigned Task scope.\n## Test plan\nActual fixture checks.\n')
        self.git('add','.')
        self.git('commit','-q','-m','fix: assigned fixture #1\n\nReview-Tier: B\nSelf-Review: focused checks\nSelf-Review-Source: plans/review.md')
        self.assert_publication(0)

if __name__=='__main__':
    unittest.main()
