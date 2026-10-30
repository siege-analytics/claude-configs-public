#!/usr/bin/env python3
"""Real hook transport controls; content never travels through the environment."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'hooks/_test'))
import task_keyed_gates as fixture
spec = importlib.util.spec_from_file_location('payload', ROOT / 'hooks/lib/hook_payload.py')
payload = importlib.util.module_from_spec(spec)
spec.loader.exec_module(payload)


class Payload(unittest.TestCase):
    def test_bounds_and_required_fields(self):
        value = {'session_id': 'one', 'tool_name': 'MultiEdit', 'tool_input': {
            'file_path': '/exact/target', 'edits': [{'old_string': 'a' * 4000, 'new_string': 'b' * 4000}] * 30}}
        result = json.loads(payload.metadata_environment(value))
        self.assertEqual(result['tool_input'], {'file_path': '/exact/target', 'edits': []})
        nested = {'metadata': {'session': {'conversation': {'metadata': {'craftSessionId': 'deep'}}}}}
        self.assertEqual(json.loads(payload.metadata_environment(nested)), nested)
        value = {'tool_name': 'Bash', 'tool_input': {'command': 'x' * 65536}}
        self.assertEqual(json.loads(payload.metadata_environment(value)), value)
        value['tool_input']['command'] += 'x'
        with self.assertRaises(ValueError):
            payload.metadata_environment(value)
        value['tool_input']['command'] = 'x'
        value['cwd'] = 'x' * 98304
        with self.assertRaises(ValueError):
            payload.metadata_environment(value)

    def test_cli_rejects_ambiguous_invalid_and_oversize_input(self):
        for raw in ('{"cwd":"a","cwd":"b"}', '{"cwd":NaN}', '[1]', 'x' * (1024 * 1024 + 1), b'\xff'):
            result = subprocess.run([sys.executable, str(ROOT / 'hooks/lib/hook_payload.py')], input=raw.encode() if isinstance(raw, str) else raw, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 2)

    def test_real_multiedit_scope_and_large_advisory_guards(self):
        g = fixture.Gates(methodName='runTest'); g.setUp()
        self.addCleanup(g.tearDown)
        g.task('own', g.a); g.task('other', g.b, status='designing')
        env = dict(g.env, AMBIENT_PADDING='p' * 100000)
        value = fixture.craft_payload(tool_name='MultiEdit', cwd=str(g.a), tool_input={
            'file_path': str(g.a / 'file.txt'), 'edits': [{'old_string': 'a' * 4000, 'new_string': 'b' * 4000}] * 100})
        def run(hook):
            return subprocess.run(['bash', str(ROOT / hook)], input=json.dumps(value), env=env, text=True, capture_output=True, timeout=60)
        result = run('hooks/bash/universal-mutation-gate.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        value['tool_input']['file_path'] = str(g.b / 'file.txt')
        result = run('hooks/bash/universal-mutation-gate.sh')
        self.assertEqual(result.returncode, 2, result.stderr)
        for name in ('investigate-gate-guard', 'think-gate-guard', 'standing-order-guard', 'skill-enforcement-gate', 'review-gate-guard', 'pipeline-state-guard'):
            result = run('hooks/resolver/' + name + '.sh')
            self.assertEqual(result.returncode, 0, (name, result.stderr))
            self.assertNotIn('Argument list too long', result.stderr)
            self.assertNotIn('metadata unavailable', result.stderr.lower())

    def test_git_cd_guards_have_no_invalid_regex(self):
        g = fixture.Gates(methodName='runTest'); g.setUp()
        self.addCleanup(g.tearDown)
        for name in ('detect-ai-fingerprints', 'pr-base-guard', 'survey-context'):
            for command in ('cd ' + str(g.repo) + ' && gh pr create --help', 'cd x; gh pr create', 'cd x || gh pr create', 'cd x\ngh pr create'):
                value = fixture.craft_payload(tool_name='Bash', cwd=str(g.repo), tool_input={'command': command})
                result = subprocess.run(['bash', str(ROOT / 'hooks/git' / (name + '.sh'))], input=json.dumps(value), env=g.env, text=True, capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn('empty (sub)expression', result.stderr)

    def test_hub_large_raw_prompt_and_response_preserve_replay_identity(self):
        g = fixture.Hub(methodName='runTest'); g.setUp()
        self.addCleanup(g.tearDown)
        g.meta('one', ['role::hub'])
        env = dict(g.env, AMBIENT_PADDING='p' * 100000)
        value = fixture.craft_payload(tool_name='mcp__session__spawn_session', tool_use_id='large',
                    tool_input=g.spawn_input('large', 'CCP_TASK_ID=o/r#1\n' + 'a' * 800000))
        def run():
            return subprocess.run(['bash', str(ROOT / 'hooks/agent-comms/hub-concurrency-gate.sh')], input=json.dumps(value), env=env, text=True, capture_output=True, timeout=60)
        result = run()
        self.assertEqual(result.returncode, 0, result.stderr)
        value['tool_input']['prompt'] = value['tool_input']['prompt'].replace('a' * 100, 'b' * 100, 1)
        result = run()
        self.assertEqual(result.returncode, 2, result.stderr)
        value['tool_input']['prompt'] = value['tool_input']['prompt'].replace('b' * 100, 'a' * 100, 1)
        value['hook_event_name'] = 'PostToolUse'
        value['tool_response'] = [{'type': 'text', 'text': json.dumps({'sessionId': 'large-child', 'padding': 'r' * 100000})}]
        result = run()
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((g.ws / 'sessions/one/hub-threads.json').read_text())
        self.assertEqual(state['pending_spawns'], {})
        self.assertIn('large-child', json.dumps(state['administered_spokes']))

    def test_hub_malformed_advisory_input_does_not_allow_oversize_metadata(self):
        g = fixture.Hub(methodName='runTest'); g.setUp()
        self.addCleanup(g.tearDown)
        g.meta('one', ['role::hub'])
        for raw, expected in (
            ('not json', 0), ('', 0), ('[]', 0),
            (json.dumps(fixture.craft_payload(tool_name='mcp__session__spawn_session',
                cwd='x' * 98305, tool_input=g.spawn_input('oversize', 'CCP_TASK_ID=o/r#1\nbounded work'))), 2),
        ):
            result = subprocess.run(['bash', str(ROOT / 'hooks/agent-comms/hub-concurrency-gate.sh')],
                input=raw, env=g.env, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, expected, result.stderr)
        self.assertFalse((g.ws / 'sessions/one/hub-threads.json').exists())


if __name__ == '__main__':
    unittest.main()
