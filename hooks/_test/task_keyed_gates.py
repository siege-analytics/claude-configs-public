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
SDK_UUID = 'ffe0010a-0000-4000-8000-000000000000'
TRANSCRIPT = str(Path.home() / '.claude/projects/-fixture-workspace-sessions-one' / (SDK_UUID + '.jsonl'))

def craft_payload(**fields):
    return {'session_id': SDK_UUID, 'transcript_path': TRANSCRIPT, 'hook_event_name': 'PreToolUse', **fields}
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
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.a = self.repo / 'a'; self.a.mkdir()
        self.b = self.repo / 'b'; self.b.mkdir()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(('CRAFT_', 'CLAUDE_', 'CCP_', 'SESSION_', 'HUB_'))}
        self.env.update(CRAFT_SESSION_DIR=str(self.ws / 'sessions/one'), CRAFT_AGENT_WORKSPACE=str(self.ws))
        write(self.ws / 'sessions/one/session.jsonl', {'id': 'one', 'sdkSessionId': SDK_UUID, 'sessionStatus': 'in_progress'})
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
        ti = {'command': command} if tool == 'Bash' else {('notebook_path' if tool == 'NotebookEdit' else 'file_path'): str(path)}
        return subprocess.run(['bash', str(ROOT / 'hooks/bash/universal-mutation-gate.sh')], input=json.dumps(craft_payload(tool_name=tool, cwd=str(cwd or self.repo), tool_input=ti)), env=env or self.env, text=True, capture_output=True)

    def assertGate(self, code, command='', **kwargs):
        result = self.hook(command, **kwargs)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def identity_env(self, payload, missing=False):
        env = {k:v for k,v in self.env.items() if not missing or k not in {'CRAFT_SESSION_ID','CRAFT_SESSION_DIR'}}
        return {**env, 'CCP_HOOK_INPUT_JSON': json.dumps(payload)}

    def real_identity_hooks(self, payload, env):
        results = []
        for hook in ['hooks/bash/universal-mutation-gate.sh', 'hooks/resolver/investigate-gate-guard.sh']:
            results.append(subprocess.run(['bash', str(ROOT / hook)], input=json.dumps(payload),
                                          env=env, text=True, capture_output=True))
        return results

    def test_sdk_uuid_real_transcript_uses_host_directory(self):
        self.task('o/r#uuid-transcript', self.a, artifacts=False)
        payload = {'session_id': 'ffe0010a-0000-4000-8000-000000000000',
                   'transcript_path': TRANSCRIPT}
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
        env = self.identity_env(payload, missing=True)
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
                   'transcript_path': TRANSCRIPT,
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
        self.assertGate(2, 'git -C ' + str(self.b) + ' add file')  # repo-wide, not nested ownership
        self.assertGate(2, 'touch ' + str(self.a / 'x') + ' ' + str(self.b / 'x'))
        self.assertGate(0, 'cp ' + str(self.a / 'source') + ' ' + str(self.b / 'dest'))
        self.assertGate(2, 'echo x > ' + str(self.a / 'x'), cwd=self.b)
        self.assertGate(2, 'touch ../../escape', cwd=self.b)
        self.assertGate(2, 'touch "$(echo /elsewhere)"', cwd=self.b)
        self.assertGate(2, 'touch "x"', cwd=self.b, env={**self.env, 'CCP_TASK_ID': 'no-such-task'})
        self.assertGate(2, "CCP_TASK_ID='o/r#1' touch x", cwd=self.b, env={**self.env, 'CCP_TASK_ID': 'o/r#2'})

    def test_option_values_cannot_redirect_targets(self):
        # Review of #1055 at 2bc6e62: trailing or attached option values were
        # taken as targets (or dropped), so a write into task B's scope was
        # charged to task A's cwd, or to an own-session path with no gate.
        self.task('o/r#1', self.a)                    # A implementing
        self.task('o/r#2', self.b, 'designing')       # B designing: writes into b blocked
        b = str(self.b / 'f')
        for command in [
            'cp src ' + b + ' -S .bak',
            'cp src ' + b + ' --suffix .bak',
            'cp -aS .bak src ' + b,
            'mv src ' + b + ' -S .bak',
            'chmod --reference=src ' + b,
            'chmod --reference src ' + b,
            'chown --reference=src ' + b,
            'cp -t ' + str(self.b) + ' src',
            'mv -vt ' + str(self.b) + ' src',
            'touch -- ' + b,
            'sort -o' + b + ' src',
            'sort --output=' + b + ' src',
        ]:
            with self.subTest(command=command):
                self.assertGate(2, command, cwd=self.a)
        sd = self.ws / 'sessions/one/plans'; sd.mkdir(parents=True, exist_ok=True)
        self.assertGate(2, 'cp notes.md ' + b + ' -S .bak', cwd=sd)
        # Legitimate forms inside A's own scope still pass.
        self.assertGate(0, 'cp src dst -S .bak', cwd=self.a)
        self.assertGate(0, 'chmod --reference=src dst', cwd=self.a)
        self.assertGate(0, 'chmod 644 dst', cwd=self.a)
        self.assertGate(0, 'cp ' + str(self.b / 'src') + ' dst', cwd=self.a)  # sources are reads

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
        # Cleanup cannot reactivate an old legacy copy in a migrated session.
        self.assertGate(0, 'rm ' + str(directory / 'think-gate.json'))
        (directory / 'think-gate.json').unlink()
        self.assertGate(2, 'touch file', cwd=self.b)
        # A genuinely legacy-only session remains supported, with root companions.
        legacy_only = self.ws / 'sessions/legacy-only'
        for source in [legacy / 'think-gate.json', *directory.glob('*-gate.json')]:
            data = json.loads(source.read_text()); data['sessionId'] = 'legacy-only'
            write(legacy_only / source.name, data)
        env = {'CRAFT_SESSION_DIR': str(legacy_only)}
        self.assertGate(0, 'touch file', cwd=self.b, env=env)
        self.assertGate(2, 'touch file', cwd=self.a, env=env)
        # Another task's canonical state must not retire this legacy task.
        self.task('o/r#other', self.a, status='designing', sid='legacy-only')
        self.assertGate(0, 'touch file', cwd=self.b, env=env)
        self.assertGate(2, 'touch file', cwd=self.a, env=env)

    def test_concurrent_pipeline_writers(self):
        # Copy real production hook and helper tree into an isolated workspace.
        shutil.copytree(ROOT / 'hooks', self.ws / 'hooks')
        fakebin = self.ws / 'fakebin'; fakebin.mkdir()
        gh = fakebin / 'gh'
        gh.write_text('#!/bin/sh\necho "current behavior intended behavior steps to get there success criteria what could go wrong hasty mistakes observable behavior over-focusing leave out prior work right environment failure case instance or class done match skip if nobody findings citations disposition fact sheet investigation verified evidence severity: tiger risks pre-mortem elephant mitigation"\n')
        gh.chmod(0o755)
        def run(sid, ticket, legacy=False):
            directory = self.task(ticket, self.repo, sid=sid)
            if legacy:
                # Artifact-only migration must not deactivate a legacy owner.
                for source in directory.glob('*-gate.json'):
                    shutil.copyfile(source, directory.parent.parent / source.name)
                shutil.rmtree(directory)
                self.task('o/r#other', self.a, status='designing', sid=sid)
            env = {**self.env, 'CRAFT_SESSION_DIR': str(directory.parent.parent), 'PATH': str(fakebin) + os.pathsep + self.env['PATH']}
            result = subprocess.run(['bash', str(self.ws / 'hooks/resolver/pipeline-state-guard.sh')], input=json.dumps(craft_payload(cwd=str(self.repo))), env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            for name in ('junior-senior', 'artifacts-posted'):
                self.assertEqual(json.loads((directory / (name + '-gate.json')).read_text())['ticket'], ticket)
            return directory
        with concurrent.futures.ThreadPoolExecutor() as pool:
            dirs = list(pool.map(lambda v: run(*v), [('one', 'o/r#1'), ('two', 'o/r#2')]))
        self.assertFalse(list(self.ws.glob('*gate*.json')))
        self.assertNotEqual(dirs[0], dirs[1])
        legacy_dir = run('legacy-writer', 'o/r#3', legacy=True)
        env = {'CRAFT_SESSION_DIR': str(legacy_dir.parent.parent)}
        self.assertGate(0, 'touch file', cwd=self.b, env=env)
        self.assertGate(2, 'touch file', cwd=self.a, env=env)


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


    def test_own_session_gate_lifecycle_end_to_end(self):
        self.assertNotIn('CRAFT_SESSION_ID', self.env)
        self.assertNotIn('CCP_TASK_ID', self.env)
        own = Path(self.env['CRAFT_SESSION_DIR'])
        directory = own / 'tasks' / r.task_slug('o/r#lifecycle')
        self.assertGate(0, 'mkdir -p ' + str(directory), cwd=self.ws)
        directory.mkdir(parents=True)
        gate = directory / 'think-gate.json'
        data = dict(ticket='o/r#lifecycle', sessionId='one', repo_root=str(self.repo), scope_paths=[str(self.a)], status='designing')
        def approved(path, content, tool='Write'):
            self.assertGate(0, tool=tool, path=path, cwd=self.ws)
            if isinstance(content, str):
                path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content)
            else:
                write(path, content)
        approved(gate, data)  # bootstrap requires no existing gate
        approved(own / 'plans/design.md', 'design')
        approved(own / 'data/probe.ipynb', {'cells': []}, tool='NotebookEdit')
        self.assertGate(2, 'touch file', cwd=self.a)
        for name, fields in {
            'investigate': {'findings': [{'claim': 'verified'}]},
            'junior-senior': {'junior_found': True, 'senior_found': True},
            'artifacts-posted': {'investigate_posted': True, 'premortem_posted': True},
        }.items():
            approved(directory / (name + '-gate.json'), {**data, **fields}, tool='MultiEdit')
        approved(own / 'plans/pre-mortem-lifecycle.md', 'Ticket: o/r#lifecycle\nSeverity: 50\nImplementation may proceed: YES\n')
        data['status'] = 'implementing'; approved(gate, data, tool='Edit')
        self.assertGate(0, 'touch file', cwd=self.a)
        subprocess.run(['touch', str(self.a / 'file')], check=True)
        self.assertTrue((self.a / 'file').is_file())
        data['status'] = 'disposed'; approved(gate, data, tool='Edit')
        self.assertGate(2, 'touch another', cwd=self.a)
        for artifact in directory.glob('*-gate.json'):
            self.assertGate(0, 'rm ' + str(artifact), cwd=self.ws)
            artifact.unlink()
        self.assertGate(0, 'rmdir ' + str(directory), cwd=self.ws)
        directory.rmdir()
        self.assertFalse(directory.exists())
        self.assertGate(2, 'rmdir ' + str(own / 'tasks'))  # persistent migration fence

    def test_self_management_exemption_cannot_escape_session_or_signal_shape(self):
        own = Path(self.env['CRAFT_SESSION_DIR'])
        for path in [self.ws / 'think-gate.json', self.ws / 'sessions/two/tasks/a/think-gate.json',
                     self.ws / 'sessions/one-other/data/x', own / 'session.jsonl',
                     own / 'tasks/a/script.py', own]:
            for tool in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
                self.assertGate(2, tool=tool, path=path)
        foreign = self.ws / 'sessions/two/data'; foreign.mkdir(parents=True)
        (own / 'data').mkdir()
        (own / 'data/alias').symlink_to(foreign, target_is_directory=True)
        self.assertGate(2, tool='Write', path=own / 'data/alias/stolen')
        self.assertGate(2, 'rm -rf ' + str(own))
        self.assertGate(2, 'rm -rf ' + str(own / 'tasks'))
        self.assertGate(2, tool='Write', path=own / 'tasks/.canonical/think-gate.json')
        self.assertGate(2, 'mkdir -p ' + str(own / 'tasks') + ' && rm -rf ' + str(own / 'tasks'))
        disguised = own / 'tasks/disguised/think-gate.json'; disguised.mkdir(parents=True)
        self.assertGate(2, 'rm -rf ' + str(disguised))
        self.assertGate(2, 'printf x > ' + str(own / 'data/x') + '; touch ' + str(foreign / 'x'))
        self.assertGate(2, "python3 -c 'open(\"/outside\",\"w\")'", cwd=own / 'data')
        self.assertGate(0, "printf '{}' > " + str(own / 'tasks/a/think-gate.json'))

        # Reserved bookkeeping never follows a final symlink, even to a FIFO.
        gate_dir = self.task('o/r#claim-fifo', self.a)
        claim = Path(r._canonical_claim(str(own), 'one', 'o/r#claim-fifo'))
        claim.parent.mkdir(parents=True, exist_ok=True)
        fifo = self.ws / 'blocking-fifo'; os.mkfifo(fifo)
        claim.symlink_to(fifo)
        result = self.hook(tool='Edit', path=gate_dir / 'think-gate.json')
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('canonical', result.stderr + result.stdout)

    def test_repository_wide_git_uses_toplevel_owner_not_nested_gate(self):
        parent = self.task('o/r#parent', self.repo, status='designing')
        nested = self.task('o/r#nested', self.b)
        file = self.repo / 'parent-uncommitted'; file.write_text('parent work')
        commands = ['reset --hard', 'add -A', 'stash', 'add file', 'clean -fd', 'commit -am changes']
        for command in commands:
            self.assertGate(2, 'git -C ' + str(self.b) + ' ' + command)
            self.assertEqual(file.read_text(), 'parent work')
        d = json.loads((parent / 'think-gate.json').read_text()); d['status'] = 'implementing'; write(parent / 'think-gate.json', d)
        for command in commands:
            self.assertGate(0, 'git -C ' + str(self.b) + ' ' + command)
        self.assertGate(2, "CCP_TASK_ID='o/r#nested' git -C " + str(self.b) + ' reset --hard')
        for command in ['diff --output=' + str(self.ws / 'outside.txt'), 'config --file=' + str(self.ws / 'outside.cfg') + ' key value']:
            self.assertGate(2, 'git -C ' + str(self.b) + ' ' + command)

    def test_git_and_tree_mutation_forms_never_bypass_without_gate(self):
        mutations = ['git tag -a probe-tag --message=x', 'git tag -a probe-tag -F msg.txt',
                     'git tag --annotate probe-tag --message x', 'git tag --list -a x',
                     'git remote -v add evil https://example.invalid/evil.git',
                     'git remote -v set-url origin https://example.invalid/evil.git',
                     'git branch -v probe-branch', 'git branch -v -u origin/main',
                     'git branch --list --set-upstream-to=origin/main',
                     "printf '%n' PATH", 'printf -vNAME value', "date -us '2024-01-01'", "date --set='2024-01-01'", 'date 10182300', 'tree -o out.txt', 'tree -R', 'tree -H .', 'tree --out=out.txt', 'tree -aoout.txt', 'tree *', 'git branch --list *']
        for command in mutations:
            with self.subTest(command=command): self.assertGate(2, command)
        for command in ['git branch', 'git branch -a -vv', "git branch --list 'feature*'", 'git branch --show-current', 'date', "date -u '+%Y-%m-%d'", 'date --iso-8601=seconds', "printf '%s' text",
                        'git tag', "git tag --list 'v*'", 'git remote', 'git remote -v',
                        'git remote show -n origin', 'git remote get-url --all origin', 'tree -a -L 2 .']:
            with self.subTest(command=command): self.assertGate(0, command)

    def test_literal_prefix_glob_reads_and_diagnostics_in_real_hooks(self):
        # V2: actual option-named files cannot turn these expansions into
        # options. Only a genuine -- permits standalone leading glob words.
        for name in ('-o', '--output=pwn', '-delete', '--pre=evil'):
            (self.repo / name).write_text('option injection sentinel')
        commands = ['ls ./*.md', 'cat plans/*.md', 'grep -n foo src/*.py',
                    'wc -l hooks/*.sh', 'head src/[a-z]*.py', 'head -n 5 src/[a-z]*.py',
                    'git diff HEAD -- src/*.py', 'git diff HEAD -- *.py',
                    'cat -- *', 'grep foo -- *.py', "find . -name '*.py'",
                    'grep --include=*.py foo .', 'grep -n foo --include=*.py .',
                    'gh api repos/o/r/contents/x?ref=abc', 'pytest tests/test_*.py',
                    'python3 -m pytest tests/test_*.py', "ls '*.md'",
                    "git diff HEAD -- '*.py'", "grep foo --include='*.py' ."]
        for phase in ('no gate', 'implementing'):
            if phase == 'implementing':
                self.task('o/r#glob', self.repo)
            for command in commands:
                with self.subTest(phase=phase, command=command):
                    payload = craft_payload(tool_name='Bash', cwd=str(self.repo), tool_input={'command': command})
                    for result in self.real_identity_hooks(payload, self.identity_env(payload)):
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                        self.assertNotIn('INVESTIGATION REQUIRED', result.stdout)

    def test_leading_glob_injection_and_mutation_globs_remain_denied(self):
        for name in ('-o', '--output=pwn', '-delete', '--pre=evil'):
            (self.repo / name).write_text('option injection sentinel')
        # Read proof is the released classifier's (hooks/lib/read-only-command.py,
        # #1057/#1087): a glob may reach a verb only when no option of that verb
        # writes or runs a program, or when it cannot form an option (it does not
        # start the word and the word does not start with "-"). Plain readers stay
        # reads even with the injection sentinels above present: cat/ls/grep/wc/
        # head have no writing or executing option. tree is never proven (tree -o
        # FILE writes), so tree with any glob needs a gate.
        reads = ['ls *.md', 'cat *', 'grep -n foo *.py', 'wc -l *.sh', 'head [a-z]*.py',
                 'ls --ign*=x', 'grep foo *', 'grep -e -- *', 'head -n -- *', 'cat ~/*.md',
                 'sort dir/*', 'find . -name x*', 'find . -- dir/*',
                 'cat {-o,x}', 'cat x{,-o}', 'cat $X']
        # A glob or expansion that can become an option of a verb that writes or
        # runs programs (rg --pre, sort -o, tree -o, git options) stays denied.
        commands = ['rg foo *', 'rg foo ?x', 'rg foo [a]*', 'rg -e -- *',
                    'git diff --word-diff-regex -- *']
        mixed = ['pytest *.py', 'sort *', 'tree dir/*', 'tree -- dir/*', 'git branch --list *', 'git diff --help src/*.py',
                 'git log --help src/*.py', 'cat $(pwd)', 'cat `pwd`',
                 'cat ' + '\\' + '\n' + '*', 'cat "' + '\\' + '\n' + '"*']
        for command in reads:
            with self.subTest(phase='no gate', command=command): self.assertGate(0, command)
        for phase in ('no gate', 'implementing'):
            if phase == 'implementing':
                self.task('o/r#glob-negative', self.repo)
            for command in commands:
                with self.subTest(phase=phase, command=command):
                    result = self.assertGate(2, command)
                    self.assertIn('prefix ./ or quote the pattern', result.stderr + result.stdout)
            for command in mixed:
                with self.subTest(phase=phase, command=command): self.assertGate(2, command)
        # Prefixing a mutation glob does not make it an explicit concrete path.
        for command in ['touch ./*.md', 'rm plans/*.md', 'git add ./src/*.py', 'printf x > ./out*.txt', 'rg foo --pre*=evil']:
            with self.subTest(command=command): self.assertGate(2, command)

    def test_tiered_task_gates_require_only_their_tier(self):
        """#1086: an implementing task needs only its effective tier's artifacts.
        The tier is the higher of the gate's declared tier and the floor that
        bin/review-risk.py computes for the mutation's targets."""
        (self.repo / 'docs').mkdir(); (self.repo / 'src').mkdir(); (self.repo / 'hooks/bash').mkdir(parents=True)
        def gate_only(identity, **extra):
            d = self.task(identity, self.repo, artifacts=False)
            data = json.loads((d / 'think-gate.json').read_text()); data.update(extra)
            write(d / 'think-gate.json', data)
            return d, data
        def add(d, data, *names):
            fields = {'investigate': {'findings': [{'claim': 'verified'}]},
                      'junior-senior': {'junior_found': True, 'senior_found': True},
                      'artifacts-posted': {'investigate_posted': True, 'premortem_posted': True}}
            for name in names:
                if name == 'pre-mortem':
                    plans = self.repo / 'plans'; plans.mkdir(exist_ok=True)
                    (plans / ('pre-mortem-' + r.task_slug(data['ticket']) + '.md')).write_text(
                        'Ticket: ' + data['ticket'] + '\nSeverity: 50\nImplementation may proceed: YES\n')
                else:
                    write(d / (name + '-gate.json'), {**data, **fields[name]})
        # Tier A floor (docs, plans, *.md): the implementing gate alone suffices.
        d, data = gate_only('o/r#tier-a')
        self.assertGate(0, f'touch {self.repo}/docs/notes.md')
        # Tier B floor (ordinary code): needs investigation + pre-mortem, not junior/senior.
        result = self.assertGate(2, f'touch {self.repo}/src/app.py')
        self.assertIn('review tier is B', result.stderr)
        add(d, data, 'investigate', 'pre-mortem')
        self.assertGate(0, f'touch {self.repo}/src/app.py')
        # Tier C floor (hooks/bash/**): B's artifacts are not enough; the full set is.
        result = self.assertGate(2, f'touch {self.repo}/hooks/bash/x.sh')
        self.assertIn('review tier is C', result.stderr)
        self.assertIn('Junior', result.stderr)
        add(d, data, 'junior-senior', 'artifacts-posted')
        self.assertGate(0, f'touch {self.repo}/hooks/bash/x.sh')

    def test_tree_wide_targets_are_classified_by_their_contents(self):
        """#1086 review: a directory or repository-wide target is as risky as the
        files under it. A lone git commit is as risky as what it records."""
        git = lambda *a: subprocess.run(['git', '-C', str(self.repo), *a], check=True, capture_output=True)
        (self.repo / 'hooks/bash').mkdir(parents=True); (self.repo / 'docs').mkdir(); (self.repo / 'src').mkdir()
        (self.repo / 'hooks/bash/guard.sh').write_text('x'); (self.repo / 'docs/a.md').write_text('x')
        git('add', 'hooks/bash/guard.sh', 'docs/a.md')
        git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', 'init')
        d = self.task('o/r#tree-tier', self.repo, artifacts=False)
        data = json.loads((d / 'think-gate.json').read_text())
        write(d / 'investigate-gate.json', {**data, 'findings': [{'claim': 'verified'}]})
        plans = self.repo / 'plans'; plans.mkdir(exist_ok=True)
        (plans / ('pre-mortem-' + r.task_slug(data['ticket']) + '.md')).write_text(
            'Ticket: ' + data['ticket'] + '\nSeverity: 50\nImplementation may proceed: YES\n')
        # Tier B evidence is present; tree-wide commands over Tier C files need C.
        for command in [f'rm -rf {self.repo}/hooks/bash', f'cp -r {self.repo}/src {self.repo}/hooks/bash',
                        f'git -C {self.repo} apply p.diff', f'git -C {self.repo} reset --hard']:
            with self.subTest(command=command):
                result = self.assertGate(2, command)
                self.assertIn('review tier is C', result.stderr)
        # A tree-wide command over B-only files stays B (passes with B evidence).
        self.assertGate(0, f'rm -rf {self.repo}/src')
        # A lone git commit is classified by what it records.
        (self.repo / 'docs/a.md').write_text('y'); git('add', 'docs/a.md')
        self.assertGate(0, f'git -C {self.repo} commit -m docs')
        (self.repo / 'hooks/bash/guard.sh').write_text('y')
        result = self.assertGate(2, f'git -C {self.repo} commit -m hook')
        self.assertIn('review tier is C', result.stderr)

    def test_lone_commit_with_conventional_message_is_classified_by_what_it_records(self):
        """#1092 review: quoted parentheses, arrows and slashes in a commit
        message do not turn a lone commit into a repository-wide target."""
        git = lambda *a: subprocess.run(['git', '-C', str(self.repo), *a], check=True, capture_output=True)
        (self.repo / 'hooks/bash').mkdir(parents=True); (self.repo / 'docs').mkdir()
        (self.repo / 'hooks/bash/guard.sh').write_text('x'); (self.repo / 'docs/a.md').write_text('x')
        git('add', 'hooks/bash/guard.sh', 'docs/a.md')
        git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', 'init')
        self.task('o/r#conventional', self.repo, artifacts=False)   # Tier A evidence only
        (self.repo / 'docs/a.md').write_text('y'); git('add', 'docs/a.md')
        self.assertGate(0, f'git -C {self.repo} commit -m "fix(docs): a -> b, see docs/a.md"')
        (self.repo / 'hooks/bash/guard.sh').write_text('y')
        result = self.assertGate(2, f'git -C {self.repo} commit -m "fix(hooks): a -> b"')
        self.assertIn('review tier is C', result.stderr)

    def test_native_pre_push_finds_root_test_gate_without_a_session(self):
        """#1092 review: a terminal push (no session identity) uses the
        workspace or repository test-gate.json, as before #1051."""
        write(self.repo / 'test-gate.json', {'evidence': [{'source': 'x.py', 'test': 't', 'result': 'pass'}]})
        env = {k: v for k, v in os.environ.items() if not k.startswith(('CRAFT_', 'CLAUDE_', 'CCP_'))}
        with patch.dict(os.environ, env, clear=True):
            found = r.find_gate_for_repo(str(self.repo), str(self.repo), gate_name='test-gate')
        self.assertTrue(found and found['path'].endswith('test-gate.json'), found)

    def test_proven_read_selects_by_repository_not_empty_targets(self):
        self.task('o/r#read-select', self.repo, artifacts=False)
        payload = craft_payload(cwd=str(self.repo), tool_input={'command': 'git status'})
        with patch.dict(os.environ, {**os.environ, 'CCP_HOOK_INPUT_JSON': json.dumps(payload)}):
            found = r.find_gate_for_repo(str(self.ws), str(self.repo))
        self.assertTrue(found, 'a proven read should still resolve the repository task gate')

    def test_declared_tier_never_lowers_the_floor(self):
        d = self.task('o/r#tier-declared-low', self.repo, artifacts=False)
        data = json.loads((d / 'think-gate.json').read_text()); data['tier'] = 'A'
        write(d / 'think-gate.json', data)
        (self.repo / 'hooks/bash').mkdir(parents=True)
        result = self.assertGate(2, f'touch {self.repo}/hooks/bash/x.sh')
        self.assertIn('review tier is C', result.stderr)

    def test_declared_tier_can_raise_the_floor(self):
        d = self.task('o/r#tier-declared-high', self.repo, artifacts=False)
        data = json.loads((d / 'think-gate.json').read_text()); data['tier'] = 'C'
        write(d / 'think-gate.json', data)
        (self.repo / 'docs').mkdir()
        result = self.assertGate(2, f'touch {self.repo}/docs/notes.md')
        self.assertIn('review tier is C', result.stderr)

    def test_stdio_redirect_reads_and_diagnostics_in_real_hooks(self):
        commands = ['cat x 2>/dev/null', 'grep foo f 2>&1', 'ls 2>&1 | head',
                    'pytest tests 2>&1 | tail', 'python3 -m pytest -q 2>&1 | tail',
                    'cat x >&1', 'cat x 3>&12', 'cat x 0<&1',
                    'cat x 2>&-', 'cat x 3<&-', 'cat x >/dev/null',
                    'cat x >>/dev/null', 'cat x 2>>/dev/null',
                    'cat x &>/dev/null', 'cat x &>>/dev/null',
                    'cat x >&/dev/null', 'cat x 7</dev/null',
                    'ls >/dev/null 2>&1', 'cat x >|/dev/null', 'cat x 2>|/dev/null',
                    'cat x 2>"/dev/null"', "cat x >'/dev/null'", 'cat x >&3']
        for phase in ('no gate', 'designing', 'implementing', 'done-awaiting-pr', 'disposed'):
            if phase != 'no gate':
                self.task('o/r#stdio', self.repo, status=phase)
            # Full operator vocabulary in required no-gate/implementing states;
            # representative read/diagnostic forms also prove terminal/designing
            # independence without duplicating the full cross-product.
            matrix = commands if phase in ('no gate', 'implementing') else commands[:4]
            for command in matrix:
                with self.subTest(phase=phase, command=command):
                    payload = craft_payload(tool_name='Bash', cwd=str(self.repo), tool_input={'command': command})
                    for result in self.real_identity_hooks(payload, self.identity_env(payload)):
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                        self.assertNotIn('INVESTIGATION REQUIRED', result.stdout)

    def test_stdio_redirect_authorized_mutations_and_scoped_outputs(self):
        commands = [f"git -C '{self.repo}' commit -m x 2>&1",
                    f"git -C '{self.repo}' commit -m x 2>/dev/null",
                    'touch f 2>&1', 'touch f 2>/dev/null', 'touch f &>/dev/null',
                    'cat x 2>out', 'cat x 2>>out', 'cat x &>out',
                    'cat x &>>out', 'ls >&out', 'cat x >|out',
                    '3>out cat x', 'cat x 3>out >&3']
        for command in commands:
            with self.subTest(phase='no gate', command=command): self.assertGate(2, command)
        self.task('o/r#stdio-mutation', self.repo)
        for command in commands:
            with self.subTest(phase='implementing', command=command): self.assertGate(0, command)

    def test_stdio_file_redirects_and_expanded_targets_remain_scoped(self):
        outside = self.ws / 'outside'
        outside.mkdir()
        link = self.repo / 'null-link'; link.symlink_to('/dev/null')
        commands = [f'cat x 2>{outside}/file', f'cat x 2>>{outside}/file',
                    f'ls >&{outside}/file', f'echo x &>{outside}/file',
                    f'echo x &>>{outside}/file', f'cat x 2>&1 >{outside}/file',
                    f'cat x >{outside}/file 2>&1', f'cat x >{outside}/file >/dev/null',
                    f'touch {outside}/file 2>/dev/null',
                    'cat x 2>./out*', 'cat x 2>&./out*', 'cat x &>>./out*',
                    'cat x 2>$OUTPUT', 'cat x 2>&$FD', 'cat x 2>$(pwd)',
                    'cat x 2>&', 'cat x 2<&word', 'cat x 2>/dev/nul*',
                    'cat x 2>null-link', 'cat x >/dev/null.txt',
                    'cat x >/dev/nullx', 'cat x 2>/dev/fd/3',
                    'cat x >/dev/stdout', 'cat x >/dev/stderr', 'cat x >/dev/tty',
                    'cat x >/dev/null/../tmp/x', 'cat x >/dev//null',
                    'exec 3>f; cat x >&3', f'3>{outside}/file cat x',
                    f'cat x 3>{outside}/file >&3', f'cat x >|{outside}/file',
                    'cat x >|./out*', 'cat x >|$OUTPUT', 'cat x 2>~/file']
        for phase in ('no gate', 'implementing'):
            if phase == 'implementing': self.task('o/r#stdio-negative', self.repo)
            for command in commands:
                with self.subTest(phase=phase, command=command): self.assertGate(2, command)
        from task_actions import shell_tokens
        for word in ('"2"', "'2'", r'\2'):
            self.assertEqual([t[0] for t in shell_tokens('cat '+word+'>/dev/null')],
                             ['cat', '2', '>', '/dev/null'])
        self.assertEqual([t[0] for t in shell_tokens('cat 2>/dev/null')],
                         ['cat', '2>', '/dev/null'])

    def test_bounded_investigation_policy_without_gate_and_while_designing(self):
        commands = ['bash -n tests/run.sh', 'shellcheck hooks/x.sh', 'python3 -m pytest -q', 'pytest tests',
                    'python3 -m py_compile x.py', 'ruff check .', 'markitdown doc.pdf', 'pdf-tool info doc.pdf',
                    'pdf-tool extract doc.pdf', 'xlsx-tool read file.xlsx', 'pptx-tool info deck.pptx',
                    'ical-tool read events.ics', 'doc-diff a.docx b.docx', 'git fetch origin', 'npm list',
                    'yarn list', 'pnpm list', 'brew list', 'type python3', 'mypy x.py', 'flake8 x.py',
                    'pylint x.py', 'black --check x.py', 'isort --check-only x.py', 'python3 -m pip list']
        for command in commands:
            with self.subTest(phase='no gate', command=command): self.assertGate(0, command)
        self.task('o/r#design', self.a, status='designing', artifacts=False)
        for command in commands:
            with self.subTest(phase='designing', command=command): self.assertGate(0, command, cwd=self.a)
        for command in ['bash tests/run.sh', 'python3 tools/check.py', 'git clone https://example.invalid/x repo',
                        "bash -c 'touch x'", 'ruff check --fix .', 'ruff check --output-file=x .',
                        'pytest --junitxml=out.xml tests', 'pytest -p arbitrary tests',
                        'shellcheck --unknown=x x.sh', 'markitdown -o out.md doc.pdf', 'pdf-tool extract doc.pdf -o out.txt',
                        'npm audit fix', 'npm list; touch file', 'brew install package', 'python3 -m pip install pkg',
                        'git fetch --upload-pack=touch origin', 'git fetch origin HEAD:refs/heads/main',
                        "git fetch 'ext::sh -c touch x'", 'python3 -m pip list --log=outside.log', 'ack --pager=touch x',
                        'file -Cm magic', 'xxd input output -p']:
            with self.subTest(command=command): self.assertGate(2, command, cwd=self.a)
        decision = r.resolve_action(str(self.ws), craft_payload(cwd=str(self.a), tool_input={'command': 'pytest tests'}))
        self.assertTrue(decision['investigation'])
        self.assertFalse(decision['read_only'])

    def test_terminal_gates_do_not_compete_and_stale_legacy_cannot_resurrect(self):
        for status in ['disposed', 'complete', 'done-awaiting-pr']:
            terminal = self.task('o/r#old', self.a, status=status)
            stale = json.loads((terminal / 'think-gate.json').read_text()); stale['status'] = 'implementing'
            write(self.ws / 'sessions/one/think-gate.json', stale)
            active = self.task('o/r#new', self.a)
            self.assertGate(0, 'touch file', cwd=self.a)
            self.assertGate(0, tool='Write', path=self.a / 'x')
            self.assertGate(2, "CCP_TASK_ID='o/r#old' touch file", cwd=self.a)
            d = json.loads((active / 'think-gate.json').read_text()); d['status'] = 'designing'; write(active / 'think-gate.json', d)
            self.assertGate(2, 'touch file', cwd=self.a)
            self.assertGate(0, 'rm ' + str(terminal / 'think-gate.json'))
            (terminal / 'think-gate.json').unlink()
            d['status'] = 'implementing'; write(active / 'think-gate.json', d)
            self.assertGate(0, 'touch after-cleanup', cwd=self.a)
            self.assertGate(0, tool='Write', path=self.a / 'after-cleanup')
            self.assertGate(2, "CCP_TASK_ID='o/r#old' touch file", cwd=self.a)


class Hub(unittest.TestCase):
    setUp = Gates.setUp
    tearDown = Gates.tearDown
    # Inherit fixture helpers but do not repeat gate tests.
    task = Gates.task

    def meta(self, sid, labels=None, parent=None, **fields):
        write(self.ws / 'sessions' / sid / 'session.jsonl', {'id': sid, 'sdkSessionId': SDK_UUID, 'sessionStatus': 'in_progress', 'labels': labels or [], 'parentSessionId': parent, **fields})

    def send(self, target, task='o/r#1', role='role::hub'):
        if role is not None: self.meta('one', [role])
        env = self.env
        return subprocess.run(['bash', str(ROOT / 'hooks/agent-comms/hub-concurrency-gate.sh')], input=json.dumps(craft_payload(tool_name='mcp__session__send_agent_message', tool_input={'sessionId': target, 'message': 'CCP_TASK_ID=' + task + '\ndispatch'})), env=env, capture_output=True, text=True)

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
        payload = craft_payload(tool_name='mcp__session__spawn_session', hook_event_name=phase, tool_use_id=key,
                                tool_input={'name': key, 'prompt': 'CCP_TASK_ID=' + task + '\nbounded work'})
        if response is not None: payload['tool_response'] = response
        return subprocess.run(['bash', str(ROOT / 'hooks/agent-comms/hub-concurrency-gate.sh')], input=json.dumps(payload), env=self.env, capture_output=True, text=True)

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
        payload = craft_payload(tool_name='mcp__session__spawn_session', tool_input={'name': 'identical', 'prompt': 'CCP_TASK_ID=o/r#1\nwork'})
        env = {**self.env, 'HUB_THREAD_CAP': '1'}
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

    def test_hub_cap_uses_host_directory_not_sdk_uuid(self):
        self.meta('one', ['role::hub'])
        env = self.env
        for i in range(4):
            payload = {'session_id':'ffe0010a-0000-4000-8000-000000000000',
                       'transcript_path':TRANSCRIPT,
                       'tool_name':'mcp__session__spawn_session', 'tool_use_id':str(i),
                       'tool_input':{'name':'worker', 'prompt': 'CCP_TASK_ID=o/r#1\nwork'}}
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


    def test_real_header_concluded_children_do_not_permanently_block_hub(self):
        self.meta('one', ['role::hub'])
        for i, status in enumerate(['done', 'needs-review', 'retired', 'archived', 'complete']):
            self.meta('historical-' + str(i), ['role::worker'], parent='one', sessionStatus=status, isArchived=(i == 3))
        for key in ['active-a', 'active-b', 'active-c']:
            self.assertEqual(self.spawn(key).returncode, 0)
            self.meta(key, ['role::worker'], parent='one')
            self.assertEqual(self.spawn(key, phase='PostToolUse', response={'sessionId': key}).returncode, 0)
        self.assertEqual(self.spawn('fourth').returncode, 2)
        self.meta('active-a', ['role::worker'], parent='one', sessionStatus='needs-review')
        self.meta('active-b', ['role::worker'], parent='one', sessionStatus='retired')
        self.meta('active-c', ['role::worker'], parent='one', isArchived=True)
        self.assertEqual(self.spawn('replacement').returncode, 0)
        state = json.loads((self.ws / 'sessions/one/hub-threads.json').read_text())
        self.assertEqual(state['administered_spokes'], [])
        self.assertEqual(next(iter(state['pending_spawns'].values()))['task'], 'o/r#1')
        header = json.loads((self.ws / 'sessions/one/session.jsonl').read_text())
        self.assertFalse({'ticket', 'taskId', 'status', 'todoState', 'archived'} & set(header))
        self.assertNotIn('CCP_TASK_ID', self.env)
        self.assertNotIn('CRAFT_SESSION_ID', self.env)

    def test_unwitnessed_unknown_history_never_collapses_into_one_task_bucket(self):
        self.meta('one', ['role::hub'])
        for i in range(5):
            self.meta('child-' + str(i), ['role::worker'], parent='one')
        self.assertEqual(self.spawn('new-known-task').returncode, 0)
        state = json.loads((self.ws / 'sessions/one/hub-threads.json').read_text())
        self.assertEqual(state['administered_spokes'], [])
        self.assertEqual(next(iter(state['pending_spawns'].values()))['task'], 'o/r#1')

    def test_task_binding_from_sole_active_gate_and_unresolved_task_audit(self):
        self.meta('one', ['role::hub'])
        def raw(key):
            payload = craft_payload(tool_name='mcp__session__spawn_session', tool_use_id=key,
                                    tool_input={'name': key, 'prompt': 'bounded work'})
            return subprocess.run(['bash', str(ROOT / 'hooks/agent-comms/hub-concurrency-gate.sh')],
                                  input=json.dumps(payload), env=self.env, capture_output=True, text=True)
        self.assertEqual(raw('unresolved').returncode, 0)
        audit = self.ws / 'sessions/one/hub-threads.json.audit.jsonl'
        self.assertIn('unresolved spawn task', audit.read_text())
        self.task('o/r#sole', self.repo, status='designing', artifacts=False)
        for key in ['a', 'b', 'c']: self.assertEqual(raw(key).returncode, 0)
        self.assertEqual(raw('d').returncode, 2)
        self.assertEqual(self.spawn('different', task='o/r#other').returncode, 0)
        self.task('o/r#ambiguous', self.repo, status='designing', artifacts=False)
        self.assertEqual(raw('ambiguous').returncode, 0)
        self.assertIn('unresolved spawn task', audit.read_text())


if __name__ == '__main__':
    import unittest.mock
    unittest.main(verbosity=2)
