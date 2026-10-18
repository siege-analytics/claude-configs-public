#!/usr/bin/env python3
"""Real resolver/hook isolation, classifier and cap acceptance for #1051."""
import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / 'hooks/lib'
sys.path.insert(0, str(LIB))
spec = importlib.util.spec_from_file_location('resolver', LIB / 'resolve-think-gate.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


class Gates(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='.1051-test-', dir=ROOT)
        self.ws = Path(self.tmp.name)
        self.repo = self.ws / 'repo'
        self.repo.mkdir()
        self.a = self.repo / 'a'; self.a.mkdir()
        self.b = self.repo / 'b'; self.b.mkdir()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(('CRAFT_', 'CLAUDE_', 'CCP_', 'SESSION_', 'HUB_'))}
        self.env.update(CRAFT_SESSION_ID='one', CRAFT_SESSION_DIR=str(self.ws / 'sessions/one'), CRAFT_AGENT_WORKSPACE=str(self.ws))
        self.old = dict(os.environ)
        os.environ.clear(); os.environ.update(self.env)

    def tearDown(self):
        os.environ.clear(); os.environ.update(self.old)
        self.tmp.cleanup()

    def task(self, identity, scope, status='implementing', sid='one', slug=None, artifacts=True):
        directory = self.ws / 'sessions' / sid / 'tasks' / (slug or r.task_slug(identity))
        data = dict(ticket=identity, sessionId=sid, repo_root=str(self.repo), scope_paths=[str(scope)], status=status)
        write(directory / 'think-gate.json', data)
        if artifacts:
            for name, fields in {
                'investigate': {'findings': [{'claim': 'verified'}]},
                'junior-senior': {'junior_found': True, 'senior_found': True},
                'artifacts-posted': {'investigate_posted': True, 'premortem_posted': True},
            }.items():
                write(directory / (name + '-gate.json'), {**data, **fields})
            plans = self.repo / 'plans'; plans.mkdir(exist_ok=True)
            (plans / ('pre-mortem-' + r.task_slug(identity) + '.md')).write_text('Ticket: ' + identity + '\nSeverity: 50\nImplementation may proceed: YES\n')
        return directory

    def hook(self, command='', cwd=None, env=None, tool='Bash', path=None):
        ti = {'command': command} if tool == 'Bash' else {'file_path': str(path)}
        return subprocess.run(['bash', str(ROOT / 'hooks/bash/universal-mutation-gate.sh')], input=json.dumps({'tool_name': tool, 'cwd': str(cwd or self.repo), 'tool_input': ti}), env=env or self.env, text=True, capture_output=True)

    def assertGate(self, code, command='', **kwargs):
        result = self.hook(command, **kwargs)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def identity_env(self, payload):
        env = {k:v for k,v in self.env.items() if k not in {'CRAFT_SESSION_ID','CRAFT_SESSION_DIR'}}
        return {**env, 'CCP_HOOK_INPUT_JSON': json.dumps(payload)}

    def real_identity_hooks(self, payload, env):
        results = []
        for hook in ['hooks/bash/universal-mutation-gate.sh', 'hooks/resolver/investigate-gate-guard.sh']:
            results.append(subprocess.run(['bash', str(ROOT / hook)], input=json.dumps(payload),
                                          env=env, text=True, capture_output=True))
        return results

    def test_uuid_plus_transcript_resolves_craft_directory(self):
        self.task('o/r#uuid-transcript', self.a, artifacts=False)
        payload = {'session_id': 'ffe0010a-0000-4000-8000-000000000000',
                   'transcript_path': str(self.ws / 'sessions/one/session.jsonl')}
        with patch.dict(os.environ, self.identity_env(payload), clear=True):
            self.assertEqual(r.session_id_from_env(), 'one')
            self.assertIn(str(self.ws / 'sessions/one'), r.session_dirs(str(self.ws)))
        payload.update(cwd=str(self.a), tool_name='Bash', tool_input={'command':'touch file'})
        mutation, guard = self.real_identity_hooks(payload, self.identity_env(payload))
        self.assertEqual(mutation.returncode, 2)
        self.assertNotIn('Session id unresolved', mutation.stderr)
        self.assertIn('required artifacts are missing', mutation.stderr)
        self.assertIn('INVESTIGATION REQUIRED', guard.stdout)
        self.assertIn('o/r#uuid-transcript', guard.stdout)

    def test_uuid_only_has_actionable_diagnostic_not_wrong_directory(self):
        uuid = 'ffe0010a-0000-4000-8000-000000000000'
        self.task('o/r#uuid', self.a, sid=uuid)
        payload = {'session_id': uuid, 'cwd': str(self.a), 'tool_input': {'command': 'touch file'}}
        env = self.identity_env(payload)
        result = subprocess.run(['python3', str(LIB / 'resolve-think-gate.py'), '--workspace', str(self.ws), '--action-json'], env=env, text=True, capture_output=True)
        selected = json.loads(result.stdout)
        self.assertIsNone(selected['gate'])
        self.assertIn('Session id unresolved', selected['error'])
        self.assertIn('CRAFT_SESSION_DIR', selected['error'])
        result = subprocess.run(['python3', str(LIB / 'resolve-think-gate.py'), '--workspace', str(self.ws), '--repo-root', str(self.a), '--gate-name', 'investigate-gate'], env=env, text=True, capture_output=True)
        self.assertIsNone(json.loads(result.stdout))
        self.assertIn('Session id unresolved', result.stderr)
        payload['tool_name'] = 'Bash'
        mutation, guard = self.real_identity_hooks(payload, env)
        self.assertEqual(mutation.returncode, 2)
        self.assertIn('Session id unresolved', mutation.stderr)
        self.assertIn('Session id unresolved', guard.stderr)

    def test_craft_stamped_gate_accepted_with_sdk_uuid_payload(self):
        self.task('o/r#craft', self.a)
        payload = {'session_id': 'ffe0010a-0000-4000-8000-000000000000',
                   'transcript_path': str(self.ws / 'sessions/one/session.jsonl'),
                   'cwd': str(self.a), 'tool_name': 'Bash', 'tool_input': {'command': 'touch file'}}
        result = subprocess.run(['bash', str(ROOT / 'hooks/bash/universal-mutation-gate.sh')], input=json.dumps(payload), env=self.identity_env(payload), text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        mutation, guard = self.real_identity_hooks(payload, self.identity_env(payload))
        self.assertEqual(mutation.returncode, 0, mutation.stderr)
        self.assertIn('o/r#craft', guard.stdout)
        self.assertNotIn('Session id unresolved', guard.stderr)

    def test_environment_craft_session_dir_wins_conflicting_payload(self):
        self.task('o/r#envdir', self.a)
        payload = {'session_id': 'ffe0010a-0000-4000-8000-000000000000',
                   'transcript_path': str(self.ws / 'sessions/other/session.jsonl'),
                   'cwd': str(self.a), 'tool_input': {'command': 'touch file'}}
        env = {**self.env, 'CRAFT_SESSION_ID': 'conflicting', 'CCP_HOOK_INPUT_JSON': json.dumps(payload)}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(r.session_id_from_env(), 'one')
            self.assertIsNotNone(r.resolve_action(str(self.ws), payload)['gate'])
        payload['tool_name'] = 'Bash'
        mutation, guard = self.real_identity_hooks(payload, env)
        self.assertEqual(mutation.returncode, 0, mutation.stderr)
        self.assertIn('o/r#envdir', guard.stdout)
        self.assertNotIn('Session id unresolved', guard.stderr)

    def target_repositories(self):
        for path, origin in [(self.ws, 'https://example.invalid/owner/configs.git'),
                             (self.repo, 'https://example.invalid/owner/utilities.git')]:
            subprocess.run(['git', 'init', '-q', str(path)], check=True)
            subprocess.run(['git', '-C', str(path), 'config', 'remote.origin.url', origin], check=True)

    def test_workspace_repo_metadata_for_other_origin_rejected_with_diagnostic(self):
        self.target_repositories()
        directory = self.task('o/r#target', self.a)
        gate = directory / 'think-gate.json'
        data = json.loads(gate.read_text()); data['repo_root'] = str(self.ws); write(gate, data)
        result = self.assertGate(2, 'touch file', cwd=self.a)
        for detail in [str(gate), 'repo_root=' + str(self.ws), 'configs.git', str(self.repo), 'utilities.git', 'TARGET repository']:
            self.assertIn(detail, result.stderr)

    def test_correct_target_repo_metadata_accepted(self):
        self.target_repositories()
        self.task('o/r#target', self.a)
        self.assertGate(0, 'touch file', cwd=self.a)
        artifact = self.ws / 'sessions/one/tasks' / r.task_slug('o/r#target') / 'investigate-gate.json'
        data = json.loads(artifact.read_text()); data['repo_root'] = str(self.ws); write(artifact, data)
        result = self.assertGate(2, 'touch file', cwd=self.a)
        self.assertIn(str(artifact), result.stderr)
        self.assertIn('utilities.git', result.stderr)

    def test_workspace_cwd_does_not_override_correct_target_repo(self):
        self.target_repositories()
        directory = self.task('o/r#target', self.a)
        self.assertGate(0, 'touch ' + str(self.a / 'file'), cwd=self.ws)
        with patch.dict(os.environ, {'CCP_HOOK_INPUT_JSON': json.dumps({'cwd':str(self.ws)})}):
            found = r.find_gate_for_repo(str(self.ws), str(self.a))
        self.assertEqual(found['path'], str(directory / 'think-gate.json'))

    def test_independent_tasks_and_state_changes(self):
        a = self.task('o/r#1', self.a, 'designing')
        self.task('o/r#2', self.b)
        self.assertGate(0, 'touch file', cwd=self.b)
        self.assertGate(2, 'touch file', cwd=self.a)
        self.assertGate(0, 'touch ' + str(self.b / 'file'))
        write(a / 'think-gate.json', dict(ticket='o/r#1', sessionId='one', repo_root=str(self.repo), scope_paths=[str(self.a)], status='disposed'))
        self.assertGate(0, 'touch file', cwd=self.b)
        self.assertGate(2, 'touch file', cwd=self.a, env={**self.env, 'CCP_TASK_ID': 'o/r#2'})

    def test_scope_specificity_and_true_tie(self):
        self.task('o/r#1', self.repo, 'designing')
        self.task('o/r#2', self.b)
        self.assertGate(0, 'touch file', cwd=self.b)
        self.task('o/r#3', self.b)
        blocked = self.assertGate(2, 'touch file', cwd=self.b)
        self.assertIn('o/r#2', blocked.stderr); self.assertIn('o/r#3', blocked.stderr)
        self.assertGate(0, 'touch file', cwd=self.b, env={**self.env, 'CCP_TASK_ID': 'o/r#2'})
        self.assertGate(0, "CCP_TASK_ID='o/r#2' touch file", cwd=self.b)
        self.assertGate(0, 'cmp x y', cwd=self.b)

    def test_multitarget_cd_git_and_escape(self):
        self.task('o/r#1', self.a, 'designing'); self.task('o/r#2', self.b)
        self.assertGate(0, 'cd ' + str(self.b) + ' && touch file')
        self.assertGate(0, 'git -C ' + str(self.b) + ' add file')
        self.assertGate(2, 'touch ' + str(self.a / 'x') + ' ' + str(self.b / 'x'))
        self.assertGate(0, 'cp ' + str(self.a / 'source') + ' ' + str(self.b / 'dest'))
        self.assertGate(2, 'echo x > ' + str(self.a / 'x'), cwd=self.b)
        self.assertGate(2, 'touch ../../escape', cwd=self.b)
        self.assertGate(2, 'touch "$(echo /elsewhere)"', cwd=self.b)
        self.assertGate(2, 'touch "x"', cwd=self.b, env={**self.env, 'CCP_TASK_ID': 'no-such-task'})
        self.assertGate(2, "CCP_TASK_ID='o/r#1' touch x", cwd=self.b, env={**self.env, 'CCP_TASK_ID': 'o/r#2'})

    def test_symlink_and_prefix_do_not_match(self):
        self.task('o/r#2', self.b)
        outside = self.ws / 'outside'; outside.mkdir()
        (self.b / 'link').symlink_to(outside, target_is_directory=True)
        self.assertGate(2, 'touch link/file', cwd=self.b)
        sibling = self.repo / 'b-foreign'; sibling.mkdir()
        self.assertGate(2, 'touch file', cwd=sibling)

    def test_exact_artifact_identity_and_wrong_session(self):
        directory = self.task('o/r#2', self.b)
        artifact = directory / 'investigate-gate.json'
        for identity in ('o/r#20', 'foreign/r#2', '#2'):
            write(artifact, {'ticket': identity, 'findings': [1]})
            self.assertGate(2, 'touch file', cwd=self.b)
        write(artifact, {'ticket': 'o/r#2', 'sessionId': 'other', 'findings': [1]})
        self.assertGate(2, 'touch file', cwd=self.b)

    def test_root_singletons_never_authorize_or_satisfy(self):
        self.task('o/r#2', self.b, artifacts=False)
        for name in ('think', 'investigate', 'junior-senior', 'artifacts-posted', 'review'):
            write(self.ws / (name + '-gate.json'), {'ticket': 'o/r#2', 'repo_root': str(self.repo), 'status': 'implementing', 'findings': [1], 'junior_found': True, 'senior_found': True, 'investigate_posted': True, 'premortem_posted': True})
        self.assertGate(2, 'touch file', cwd=self.b)
        self.assertGate(2, 'touch file', cwd=self.a)
        unknown = {k: v for k, v in self.env.items() if not k.startswith('CRAFT_SESSION')}
        self.assertGate(2, 'touch file', env=unknown)
        # Diagnostic-only unknown-session legacy read is exact canonical repo.
        with unittest.mock.patch.dict(os.environ, unknown, clear=True):
            self.assertIsNotNone(r.find_gate_for_repo(str(self.ws), str(self.repo)))
            self.assertIsNone(r.find_gate_for_repo(str(self.ws), str(self.a)))

    def test_no_gate_reads_and_hostile_unknown_shapes(self):
        reads = ['cmp x y', "grep 'pip install' x", 'grep "quoted \'pattern\'" x | wc -l', 'git -C /x rev-parse HEAD && ls /x', "python3 -I -c 'import json; d=json.load(open(\"x\")); print(d)'", "python3 -I -c 'import ast; print(ast.dump(ast.parse(open(\"x\").read())))'"]
        for command in reads:
            with self.subTest(command=command): self.assertGate(0, command)
        mutations = ['touch x', "python3 -I -c 'open(\"x\",\"w\")'", "python3 -I -c 'import os; os.remove(\"x\")'", "python3 -I -c 'print(1,file=open(\"x\",\"w\"))'", 'find . -exec touch x \\;', 'rg --pre touch x', 'git log --ext-diff', 'git status | tee x', 'jq . $(touch x)', 'echo x > y', 'env touch x', 'git branch new', 'git tag new', 'printf -v var x', 'xxd -r input output', 'gh api x -XPOST', 'gh api x -fkey=value', 'git branch --list --delete x', 'touch ~/outside', 'touch *.txt']
        for command in mutations:
            with self.subTest(command=command): self.assertGate(2, command)
        result = self.assertGate(2, 'touch x')
        self.assertIn('Unscoped mutation', result.stderr)
        self.assertNotIn('o/r#', result.stderr)

    def test_missing_artifacts_and_terminal_do_not_bypass(self):
        directory = self.task('o/r#2', self.b, artifacts=False)
        self.assertGate(2, 'touch file', cwd=self.b)
        data = json.loads((directory / 'think-gate.json').read_text()); data['status'] = 'complete'
        write(directory / 'think-gate.json', data)
        write(directory / 'investigate-gate.json', {**data, 'findings': [1]})
        self.assertGate(2, 'touch file', cwd=self.b)

    def test_hostile_review_opaque_and_nested_targets(self):
        self.task('o/r#2', self.b)
        for command in ["python3 -c 'open(\"/outside\",\"w\").write(\"x\")'", "bash -c 'touch /outside'", 'some-writer nested/../../../outside', 'writer --output=/outside']:
            self.assertGate(2, command, cwd=self.b)

    def test_path_tools(self):
        self.task('o/r#1', self.a, 'designing'); self.task('o/r#2', self.b)
        for tool in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
            self.assertGate(0, tool=tool, path=self.b / 'x')
            self.assertGate(2, tool=tool, path=self.a / 'x')

    def test_session_legacy_read(self):
        identity = 'o/r#2'
        directory = self.task(identity, self.b)
        legacy = directory.parent.parent
        shutil.copyfile(directory / 'think-gate.json', legacy / 'think-gate.json')
        # Canonical gate wins during migration, then legacy is a single task.
        (directory / 'think-gate.json').unlink()
        self.assertGate(0, 'touch file', cwd=self.b)
        self.assertGate(2, 'touch file', cwd=self.a)

    def test_concurrent_pipeline_writers(self):
        # Copy real production hook and helper tree into an isolated workspace.
        shutil.copytree(ROOT / 'hooks', self.ws / 'hooks')
        fakebin = self.ws / 'fakebin'; fakebin.mkdir()
        gh = fakebin / 'gh'
        gh.write_text('#!/bin/sh\necho "current behavior intended behavior steps to get there success criteria what could go wrong hasty mistakes observable behavior over-focusing leave out prior work right environment failure case instance or class done match skip if nobody findings citations disposition fact sheet investigation verified evidence severity: tiger risks pre-mortem elephant mitigation"\n')
        gh.chmod(0o755)
        def run(sid, ticket):
            directory = self.task(ticket, self.repo, sid=sid)
            env = {**self.env, 'CRAFT_SESSION_ID': sid, 'CRAFT_SESSION_DIR': str(directory.parent.parent), 'PATH': str(fakebin) + os.pathsep + self.env['PATH']}
            result = subprocess.run(['bash', str(self.ws / 'hooks/resolver/pipeline-state-guard.sh')], input=json.dumps({'cwd': str(self.repo)}), env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            for name in ('junior-senior', 'artifacts-posted'):
                self.assertEqual(json.loads((directory / (name + '-gate.json')).read_text())['ticket'], ticket)
            return directory
        with concurrent.futures.ThreadPoolExecutor() as pool:
            dirs = list(pool.map(lambda v: run(*v), [('one', 'o/r#1'), ('two', 'o/r#2')]))
        self.assertFalse(list(self.ws.glob('*gate*.json')))
        self.assertNotEqual(dirs[0], dirs[1])


    def test_ticketless_pipeline_does_not_borrow_other_task_plans(self):
        gate = self.task('design-task', self.a, status='designing', artifacts=False) / 'think-gate.json'
        data = json.loads(gate.read_text())
        data.pop('ticket')
        data['task_id'] = 'explicit-task-a'
        gate.write_text(json.dumps(data))
        plans = self.ws / 'plans'
        plans.mkdir()
        (plans / 'fact-sheet-other.md').write_text('unrelated-task-b findings')
        (plans / 'pre-mortem-other.md').write_text('unrelated-task-b Severity: low')
        result = subprocess.run(['python3', str(LIB / 'pipeline_state.py'), str(gate), str(self.ws), str(LIB)],
                                env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('No investigation artifact found', result.stdout)
        self.assertIn('No pre-mortem artifact found', result.stdout)


class Hub(unittest.TestCase):
    setUp = Gates.setUp
    tearDown = Gates.tearDown
    # Inherit fixture helpers but do not repeat gate tests.
    def meta(self, sid, labels=None, parent=None):
        write(self.ws / 'sessions' / sid / 'session.json', {'labels': labels or [], 'parentSessionId': parent})

    def send(self, target, task='o/r#1', role='role::hub'):
        if role is not None: self.meta('one', [role])
        env = {**self.env, 'CCP_TASK_ID': task}
        return subprocess.run(['bash', str(ROOT / 'hooks/agent-comms/hub-concurrency-gate.sh')], input=json.dumps({'session_id': 'one', 'tool_input': {'sessionId': target, 'message': 'dispatch'}}), env=env, capture_output=True, text=True)

    def test_hub_per_task_and_exemptions(self):
        for peer in ('a', 'b', 'c'):
            self.assertEqual(self.send(peer).returncode, 0)
        self.assertEqual(self.send('four').returncode, 0)
        self.assertEqual(self.send('other-task', task='o/r#2').returncode, 0)
        self.meta('child', ['role::worker'], parent='one')
        self.meta('steward', ['role::traffic-cop'])
        self.assertEqual(self.send('child').returncode, 0)
        self.assertEqual(self.send('steward').returncode, 0)
        self.meta('one', ['role::hub'], parent='parent')
        self.assertEqual(self.send('parent', role=None).returncode, 0)
        self.assertEqual(self.send('four', role=None).returncode, 0)
        state = json.loads((self.ws / 'sessions/one/hub-threads.json').read_text())
        self.assertEqual(len(state['open_threads']), 5)

    def spawn(self, key, task='o/r#1', phase='PreToolUse', response=None):
        payload = {'session_id': 'one', 'tool_name': 'mcp__session__spawn_session',
                   'hook_event_name': phase, 'tool_use_id': key,
                   'tool_input': {'name': key, 'prompt': 'bounded work'}}
        if response is not None: payload['tool_response'] = response
        return subprocess.run(['bash', str(ROOT / 'hooks/agent-comms/hub-concurrency-gate.sh')], input=json.dumps(payload), env={**self.env, 'CCP_TASK_ID': task}, capture_output=True, text=True)

    def test_administration_cap_never_caps_communication(self):
        self.meta('one', ['role::hub'])
        for key in ('first', 'second', 'third'):
            self.assertEqual(self.spawn(key).returncode, 0)
            self.assertEqual(self.spawn(key, phase='PostToolUse', response={'sessionId': key}).returncode, 0)
        blocked = self.spawn('fourth')
        self.assertEqual(blocked.returncode, 2, blocked.stderr)
        self.assertIn('Drain/retire', blocked.stderr)
        self.meta('one', ['role::hub'], parent='parent')
        self.meta('first', ['role::worker'], parent='one')
        self.meta('other-hub', ['role::hub'])
        self.meta('traffic-cop', ['role::traffic-cop'])
        for target in ('parent', 'first', 'other-hub', 'traffic-cop', 'anyone'):
            self.assertEqual(self.send(target, role=None).returncode, 0)
        self.assertEqual(self.spawn('another-task', task='o/r#2').returncode, 0)
        self.meta('one', ['role::traffic-cop'])
        self.assertEqual(self.spawn('steward-uncapped').returncode, 0)

    def test_pending_reservations_and_failed_spawn_release(self):
        self.meta('one', ['role::hub'])
        for key in ('a', 'b', 'c'): self.assertEqual(self.spawn(key).returncode, 0)
        self.assertEqual(self.spawn('d').returncode, 2)
        self.assertEqual(self.spawn('c', phase='PostToolUse', response={'error': 'failed'}).returncode, 0)
        self.assertEqual(self.spawn('d').returncode, 0)

    def test_same_arguments_without_request_id_cannot_reuse_reservation(self):
        self.meta('one', ['role::hub'])
        payload = {'session_id': 'one', 'tool_name': 'mcp__session__spawn_session', 'tool_input': {'name': 'identical', 'prompt': 'work'}}
        env = {**self.env, 'CCP_TASK_ID': 'o/r#1', 'HUB_THREAD_CAP': '1'}
        def invoke():
            return subprocess.run(['bash', str(ROOT / 'hooks/agent-comms/hub-concurrency-gate.sh')], input=json.dumps(payload), env=env, capture_output=True, text=True).returncode
        with concurrent.futures.ThreadPoolExecutor() as pool:
            codes = list(pool.map(lambda _: invoke(), range(2)))
        self.assertEqual(sorted(codes), [0, 2])

    def test_fallback_reservations_reconcile_without_double_counting(self):
        self.meta('one', ['role::hub'])
        self.assertEqual(self.spawn(None).returncode, 0)
        self.assertEqual(self.spawn(None).returncode, 0)
        self.assertEqual(self.spawn(None, phase='PostToolUse', response={'error': 'failed'}).returncode, 0)
        self.assertEqual(self.spawn(None, phase='PostToolUse', response={'sessionId': 'fallback-child'}).returncode, 0)
        state = json.loads((self.ws / 'sessions/one/hub-threads.json').read_text())
        self.assertEqual(len(state['administered_spokes']), 1)
        self.assertEqual(state['pending_spawns'], {})

    def test_hub_cap_uses_craft_transcript_identity_not_sdk_uuid(self):
        self.meta('one', ['role::hub'])
        env = {k:v for k,v in self.env.items() if k not in {'CRAFT_SESSION_ID','CRAFT_SESSION_DIR'}}
        for i in range(4):
            payload = {'session_id':'ffe0010a-0000-4000-8000-000000000000',
                       'transcript_path':str(self.ws / 'sessions/one/session.jsonl'),
                       'tool_name':'mcp__session__spawn_session', 'tool_use_id':str(i),
                       'tool_input':{'name':'worker'}}
            result = subprocess.run(['bash', str(ROOT / 'hooks/agent-comms/hub-concurrency-gate.sh')], input=json.dumps(payload), env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0 if i < 3 else 2, result.stdout + result.stderr)

    def test_wrapped_spawn_results_reconcile(self):
        self.meta('one', ['role::hub'])
        self.assertEqual(self.spawn('wrapped').returncode, 0)
        result = {'content': [{'type': 'text', 'text': json.dumps({'sessionId': 'wrapped-child'})}]}
        self.assertEqual(self.spawn('wrapped', phase='PostToolUse', response=result).returncode, 0)
        state = json.loads((self.ws / 'sessions/one/hub-threads.json').read_text())
        self.assertEqual(state['administered_spokes'][0]['sessionId'], 'wrapped-child')
        self.assertEqual(state['pending_spawns'], {})

    def test_only_hubs_capped_unknown_role_audited(self):
        for role in ('role::traffic-cop', 'role::workspace-config', 'role::deep-think', 'role::worker', 'role::reviewer'):
            for peer in ('a', 'b', 'c', 'd', 'e'):
                self.assertEqual(self.send(peer, role=role).returncode, 0)
        self.meta('one', ['project::only'])
        self.assertEqual(self.send('x', role=None).returncode, 0)
        self.meta('one', [])
        self.assertEqual(self.send('x', role=None).returncode, 0)
        self.assertIn('unresolved sender role', (self.ws / 'sessions/one/hub-threads.json.audit.jsonl').read_text())


if __name__ == '__main__':
    import unittest.mock
    unittest.main(verbosity=2)
