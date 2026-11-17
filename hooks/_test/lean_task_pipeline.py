#!/usr/bin/env python3
"""Task ownership survives removal of universal preparation artifacts."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import task_keyed_gates as fixture

ROOT = Path(__file__).resolve().parents[2]

class LeanTaskPipeline(unittest.TestCase):
    def setUp(self):
        self.f = fixture.Gates()
        self.f.setUp()
        self.addCleanup(self.f.tearDown)

    def test_all_tiers_allow_only_owned_implementing_targets_without_companions(self):
        for tier in ('A', 'B', 'C'):
            directory = self.f.task('own', self.f.a, artifacts=False)
            gate = directory / 'think-gate.json'
            data = json.loads(gate.read_text()); data['tier'] = tier
            gate.write_text(json.dumps(data))
            self.f.assertGate(0, 'touch ' + str(self.f.a / 'owned.py'))
            self.f.assertGate(0, tool='Write', path=self.f.a / 'owned.py')
            self.f.assertGate(2, 'touch ' + str(self.f.b / 'foreign.py'))
            self.assertEqual(sorted(p.name for p in directory.iterdir()), ['think-gate.json'])

    def test_missing_foreign_and_nonimplementing_tasks_still_deny(self):
        self.f.assertGate(2, 'touch ' + str(self.f.a / 'owned'))
        self.f.task('foreign', self.f.a, sid='two', artifacts=False)
        self.f.assertGate(2, 'touch ' + str(self.f.a / 'owned'))
        for status in ('designing', 'reviewing', 'disposed', 'done-awaiting-pr'):
            self.f.task('own', self.f.a, status=status, artifacts=False)
            self.f.assertGate(2, 'touch ' + str(self.f.a / 'owned'))

    def test_prompt_does_not_require_remote_rank_posts_or_derive_authority_companions(self):
        directory = self.f.task('o/r#42', self.f.a, artifacts=False)
        stub = self.f.ws / 'stub'; stub.mkdir()
        marker = self.f.ws / 'unexpected-gh'
        gh = stub / 'gh'; gh.write_text('#!/bin/sh\ntouch "' + str(marker) + '"\nexit 1\n'); gh.chmod(0o755)
        env = {**self.f.env, 'PATH': str(stub) + os.pathsep + self.f.env['PATH'], 'CCP_TASK_ID': 'o/r#42'}
        payload = fixture.craft_payload(hook_event_name='UserPromptSubmit', cwd=str(self.f.repo), prompt='Continue the assigned task.')
        for name in ('pipeline-state-guard.sh', 'investigate-gate-guard.sh'):
            result = subprocess.run(['bash', str(ROOT / 'hooks/resolver' / name)], input=json.dumps(payload), env=env,
                                    capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('Before writing code', result.stdout)
            self.assertNotIn('BLOCKED', result.stdout)
        self.assertFalse(marker.exists(), 'planning must not depend on GitHub comment rank/prose availability')
        self.assertEqual(sorted(p.name for p in directory.iterdir()), ['think-gate.json'])

    def test_think_note_does_not_inject_missing_artifact_or_rank_instructions(self):
        plans = self.f.repo / 'plans'; plans.mkdir()
        (plans / 'think-current.md').write_text('Existing assigned task plan.')
        payload = fixture.craft_payload(hook_event_name='UserPromptSubmit', cwd=str(self.f.repo), prompt='Continue the assigned task.')
        result = subprocess.run(['bash', str(ROOT / 'hooks/resolver/inject-resolver.sh')], input=json.dumps(payload),
            cwd=self.f.repo, env={**self.f.env, 'CRAFT_AGENT_PLANS_PATH': str(plans)}, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('DO NOT proceed to implementation', result.stdout)
        self.assertNotIn('PIPELINE STATUS', result.stdout)

    def test_unavailable_diagnostic_inputs_never_derive_authority_or_call_remote_tools(self):
        directory = self.f.task('own', self.f.a, artifacts=False)
        invalid = self.f.ws/'invalid.json'; invalid.write_text('{not json')
        nonobject = self.f.ws/'nonobject.json'; nonobject.write_text('[]')
        stub = self.f.ws/'no-remote'; stub.mkdir()
        marker = self.f.ws/'unexpected-remote'
        remote = stub/'gh'; remote.write_text('#!/bin/sh\ntouch "'+str(marker)+'"\nexit 1\n'); remote.chmod(0o755)
        env = {**self.f.env, 'PATH': str(stub)+os.pathsep+self.f.env['PATH']}
        before = {str(path):path.read_bytes() for path in self.f.ws.rglob('*.json')}
        for args in ([], [str(self.f.ws/'missing.json')], [str(invalid)], [str(nonobject)]):
            with self.subTest(args=args):
                result = subprocess.run([sys.executable, str(ROOT/'hooks/lib/pipeline_state.py'), *args],
                    env=env, text=True, capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('Task metadata unavailable:', result.stdout)
                self.assertIn('No preparation authority was derived.', result.stdout)
                self.assertNotIn('status=implementing', result.stdout)
                self.assertEqual({str(path):path.read_bytes() for path in self.f.ws.rglob('*.json')}, before)
        self.assertFalse(marker.exists())
        self.assertEqual(sorted(path.name for path in directory.iterdir()), ['think-gate.json'])

if __name__ == '__main__':
    unittest.main()
