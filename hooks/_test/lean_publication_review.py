#!/usr/bin/env python3
"""Actual publication hook checks with compact and historical review records."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

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
        self.env = {k:v for k,v in os.environ.items() if not k.startswith(('CRAFT_', 'CLAUDE_', 'CCP_'))}
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

    def commit(self,artifact=COMPACT,review=True):
        (self.repo/'plans/review.md').write_text(artifact)
        self.git('add','.')
        message='fix: assigned fixture #1\n\nReview-Tier: C\nSelf-Review: actual focused checks\nSelf-Review-Source: plans/review.md\n'
        if review: message+='Hostile-Review: plans/independent.md\n'
        self.git('commit','-q','-m',message)

    def hook(self):
        return subprocess.run(['bash',str(ROOT/'hooks/git/self-review.sh')],input=json.dumps({'cwd':str(self.repo),'tool_input':{'command':'git push'}}),
            env=self.env,text=True,capture_output=True,timeout=20)

    def test_compact_high_risk_review_needs_no_rank_premortem_or_runtime_deploy_stamp(self):
        self.commit()
        result=self.hook()
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
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

    def test_historical_valid_record_remains_publishable(self):
        self.commit(HISTORICAL)
        result=self.hook();self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_historical_minimal_tier_b_record_needs_no_new_field(self):
        source = self.repo/'src'; source.mkdir()
        (self.repo/'hooks/bash/example.sh').rename(source/'example.py')
        (self.repo/'plans/review.md').write_text('## Assumptions\nExisting assigned Task scope.\n## Test plan\nActual fixture checks.\n')
        self.git('add','.')
        self.git('commit','-q','-m','fix: assigned fixture #1\n\nReview-Tier: B\nSelf-Review: focused checks\nSelf-Review-Source: plans/review.md')
        result=self.hook();self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__':
    unittest.main()
