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

    def test_explicit_turn_binding_is_bounded_and_excludes_code_or_tool_data(self):
        binding = payload.turn_task_binding
        self.assertEqual(binding({'task_id': 'o/r#1292'}), 'o/r#1292')
        self.assertEqual(binding({'metadata': {'task_id': 'o/r#1292'}, 'prompt': 'CCP_TASK_ID=o/r#1292'}), 'o/r#1292')
        for text in ('> CCP_TASK_ID=o/r#1292', 'Example CCP_TASK_ID=o/r#1292',
                     '```text\nCCP_TASK_ID=o/r#1292\n```', '~~~\nCCP_TASK_ID=o/r#1292\n~~~',
                     '````text\n```\nCCP_TASK_ID=o/r#1292\n````',
                     '```text\n```not-a-close\nCCP_TASK_ID=o/r#1292\n```',
                     '    CCP_TASK_ID=o/r#1292'):
            self.assertEqual(binding({'prompt': text}), '')
        long_prompt = 'context ' * 1000 + '\nCCP_TASK_ID=o/r#1292'
        self.assertEqual(json.loads(payload.metadata_environment({'prompt': long_prompt}))['prompt'], '')
        self.assertEqual(binding({'prompt': long_prompt}), 'o/r#1292')
        with self.assertRaises(ValueError):
            binding({'prompt': long_prompt + '\nCCP_TASK_ID=o/r#other'})
        with self.assertRaises(ValueError):
            binding({'prompt': 'x' * (payload.INPUT_LIMIT + 1)})
        self.assertEqual(binding({'tool_input': {'content': 'CCP_TASK_ID=o/r#1292'}}), '')
        self.assertEqual(binding({'hook_event_name': 'PreToolUse', 'task_id': 'o/r#1292'}), '')
        for value in ({'task_id': None}, {'task_id': '../invalid task'}, {'task_id': 'x' * 513},
                      {'task_id': 'o/r#1292', 'metadata': {'task_id': 'o/r#other'}},
                      {'prompt': 'CCP_TASK_ID=o/r#1292\nCCP_TASK_ID=o/r#other'},
                      {'prompt': 'CCP_TASK_ID=$(touch /tmp/no-execution)'},
                      {'task_id': 'o/r#1292', 'prompt': 'CCP_TASK_ID=o/r#other'}):
            with self.assertRaises(ValueError):
                binding(value)

    def test_turn_binding_excludes_lazy_blockquote_continuations(self):
        binding = payload.turn_task_binding
        for quoted in ('> Example task:', '   > Example task:', '> > Example task:',
                       '> Example task:\ncontinued quoted paragraph'):
            with self.subTest(quoted=quoted):
                prompt = quoted + '\nCCP_TASK_ID=o/r#other'
                self.assertEqual(binding({'prompt': prompt}), '')
                self.assertEqual(binding({'task_id': 'o/r#1292', 'prompt': prompt}), 'o/r#1292')
                self.assertEqual(binding({'prompt': prompt + '\n\nCCP_TASK_ID=o/r#1292'}), 'o/r#1292')
        self.assertEqual(binding({'prompt': '> Example task:\n>\nCCP_TASK_ID=o/r#other'}), '')
        self.assertEqual(binding({'prompt': '```text\n> Example task:\n```\nCCP_TASK_ID=o/r#1292'}), 'o/r#1292')
        for fence in ('```text', '~~~text', '````text'):
            close = fence.removesuffix('text')
            quoted_fence = '> Example task:\n' + fence + '\n\nCCP_TASK_ID=o/r#other\n' + close
            self.assertEqual(binding({'prompt': quoted_fence}), '')
            self.assertEqual(binding({'prompt': quoted_fence + '\n\nCCP_TASK_ID=o/r#1292'}), 'o/r#1292')

    def test_non_bash_command_uses_only_metadata_limit(self):
        value = {'tool_name': 'mcp__fixture', 'tool_input': {'command': 'x' * 70000}}
        self.assertEqual(json.loads(payload.metadata_environment(value)), value)
        value['tool_input']['command'] = 'x' * 100000
        with self.assertRaises(ValueError):
            payload.metadata_environment(value)

    def test_hub_preflight_is_bounded_and_real_oversize_pipeline_stays_closed(self):
        import types
        from unittest.mock import patch
        hook = ROOT / 'hooks/agent-comms/hub-concurrency-gate.sh'
        raw = json.dumps({'tool_input': {'message': 'x' * (2 * 1024 * 1024)}}).encode()
        result = subprocess.run(['bash', str(hook)], input=raw, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn(b'1 MiB', result.stderr)
        for small in (b'{', b'{}'):
            result = subprocess.run(['bash', str(hook)], input=small, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
        preflight = hook.read_text().split("python3 -c '\n", 1)[1].split("\n'", 1)[0]
        calls = []
        class Bounded:
            def read(inner, size=-1):
                calls.append(size)
                self.assertEqual(size, 1024 * 1024 + 1)
                return raw[:size]
        with patch.object(sys, 'stdin', types.SimpleNamespace(buffer=Bounded())), \
                patch.object(json, 'loads', side_effect=AssertionError('oversize JSON was parsed')):
            with self.assertRaises(SystemExit) as exit:
                exec(compile(preflight, str(hook) + ':preflight', 'exec'), {})
        self.assertEqual(exit.exception.code, 0)
        self.assertEqual(calls, [1024 * 1024 + 1])

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

    def test_near_limit_prompt_reaches_all_advisory_guards(self):
        g = fixture.Gates(methodName='runTest'); g.setUp()
        self.addCleanup(g.tearDown)
        env = dict(g.env, AMBIENT_PADDING='p' * 100000)
        value = fixture.craft_payload(hook_event_name='UserPromptSubmit', cwd=str(g.repo), prompt='p' * 1030000)
        raw = json.dumps(value)
        self.assertLess(len(raw.encode()), 1024 * 1024)
        for name in ('investigate-gate-guard', 'think-gate-guard', 'standing-order-guard',
                     'skill-enforcement-gate', 'review-gate-guard', 'pipeline-state-guard'):
            result = subprocess.run(['bash', str(ROOT / 'hooks/resolver' / (name + '.sh'))],
                input=raw, env=env, text=True, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, (name, result.stderr))
            self.assertNotIn('Argument list too long', result.stderr)
            self.assertNotIn('metadata unavailable', result.stderr.lower())

    def test_spawn_guard_large_payload_still_enforces_prompt_contract(self):
        g = fixture.Hub(methodName='runTest'); g.setUp()
        self.addCleanup(g.tearDown)
        env = dict(g.env, AMBIENT_PADDING='p' * 100000)
        value = fixture.craft_payload(tool_name='mcp__session__spawn_session',
                    tool_input=g.spawn_input('large', 'CCP_TASK_ID=o/r#1\n' + 'a' * 800000))
        for valid in (True, False):
            if not valid:
                value['tool_input'].pop('model', None)
            result = subprocess.run(['bash', str(ROOT / 'hooks/agent-comms/spawn-guard.sh')],
                input=json.dumps(value), env=env, text=True, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0 if valid else 2, result.stderr)
            self.assertNotIn('Argument list too long', result.stderr)
            if not valid:
                self.assertIn('model must be explicit', result.stderr)

    def test_utf8_spawn_contract_survives_ascii_process_locale(self):
        g = fixture.Hub(methodName='runTest'); g.setUp()
        self.addCleanup(g.tearDown)
        g.meta('one', ['role::hub'])
        env = dict(g.env, LC_ALL='C', LANG='C', PYTHONUTF8='0', PYTHONCOERCECLOCALE='0')
        value = fixture.craft_payload(tool_name='mcp__session__spawn_session', tool_use_id='utf8',
                    tool_input=g.spawn_input('utf8', 'CCP_TASK_ID=o/r#1\n café'))
        value['tool_input'].pop('model', None)
        raw = json.dumps(value, ensure_ascii=False).encode('utf-8')
        for guard in ('spawn-guard', 'hub-concurrency-gate'):
            result = subprocess.run(['bash', str(ROOT / 'hooks/agent-comms' / (guard + '.sh'))],
                input=raw, env=env, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 2, (guard, result.stderr))
            self.assertIn(b'model must be explicit', result.stderr)
        self.assertFalse((g.ws / 'sessions/one/hub-threads.json').exists())

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
