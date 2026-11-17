#!/usr/bin/env python3
"""Task-owned project administration: hook decisions, never live gh execution."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('task_fixture', ROOT / 'hooks/_test/task_keyed_gates.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
ADD = 'gh project item-add 1 --owner electinfo --url https://github.com/electinfo/enterprise/issues/3300'
GRANT = dict(host='github.com', owner='electinfo', project=1, operation='item-add',
             issue_owner='electinfo', issue_binding='current-task-ticket',
             authority_source='resident/AGENTS.md:15-18;skills/_ticket-lifecycle--electinfo-workflow.md:34-37,74,164-165')


class ProjectScope(unittest.TestCase):
    def setUp(self):
        self.f = fixture.Gates()
        self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.install = self.f.ws / 'installed'
        shutil.copytree(ROOT / 'hooks/lib', self.install / 'hooks/lib')
        (self.install / 'hooks/bash').mkdir()
        shutil.copy2(ROOT / 'hooks/bash/universal-mutation-gate.sh', self.install / 'hooks/bash/universal-mutation-gate.sh')
        self.policy = self.install / 'hooks/github-project-policy.json'
        self.policy.write_text(json.dumps({'schema_version': 1, 'grants': [GRANT]}))

    def task(self, identity='electinfo/enterprise#3300', **kwargs):
        return self.f.task(identity, self.f.a, artifacts=False, **kwargs)

    def hook(self, command=ADD, code=0, env=None):
        payload = fixture.craft_payload(tool_name='Bash', cwd=str(self.f.ws), tool_input={'command': command})
        result = subprocess.run(['bash', str(self.install / 'hooks/bash/universal-mutation-gate.sh')],
                                input=json.dumps(payload), env=env or self.f.env,
                                text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def board_manager(self):
        grant = {**GRANT, 'issue_binding': 'current-task-or-declared-targets',
                 'declared_issue_repositories': ['electinfo/airflow', 'electinfo/fec-api']}
        self.policy.write_text(json.dumps({'schema_version': 1, 'grants': [grant, {**grant, 'project': 4}]}))
        directory = self.task('electinfo/enterprise#3133')
        data = json.loads((directory/'think-gate.json').read_text())
        data['task_id'] = 'tc-3133-overnight-financial-delivery-20261112'
        data['github_project_targets'] = [dict(owner='electinfo', project=board, repository=repo,
                                              issue=issue, operation='item-add')
            for board in (1, 4) for repo, issue in [('electinfo/airflow', 1074), ('electinfo/fec-api', 732)]]
        fixture.write(directory/'think-gate.json', data)
        return directory, data

    def board_command(self, board=4, repo='airflow', issue=1074):
        return ('CCP_TASK_ID=tc-3133-overnight-financial-delivery-20261112 gh project item-add '
                +str(board)+' --owner electinfo --url https://github.com/electinfo/'+repo+'/issues/'+str(issue)+' --format json')

    def test_declared_board_manager_targets_are_exact_metadata_only(self):
        self.board_manager()
        for board in (1, 4):
            for repo, issue in [('airflow', 1074), ('fec-api', 732)]:
                self.hook(self.board_command(board, repo, issue))
        for command in [self.board_command(issue=1075), self.board_command(board=2),
                        self.board_command(repo='enterprise'), self.board_command().replace('--owner electinfo', '--owner other'),
                        self.board_command().replace('item-add', 'item-delete'),
                        self.board_command().replace('--format json', '--format xml'),
                        self.board_command().replace('--format json', '--format json --jq .'),
                        self.board_command().replace('CCP_TASK_ID=tc-3133-overnight-financial-delivery-20261112 ', ''),
                        self.board_command().replace('CCP_TASK_ID=tc-3133-overnight-financial-delivery-20261112', 'CCP_TASK_ID=unrelated'),
                        self.board_command()+'; touch '+str(self.f.b/'foreign.py')]:
            with self.subTest(command=command):
                self.hook(command, 2)
        self.assertFalse((self.f.b/'foreign.py').exists())

    def test_declared_targets_do_not_replace_policy_owner_or_lifecycle(self):
        directory, data = self.board_manager()
        for field, value in [('sessionId', 'foreign'), ('status', 'designing'),
                             ('github_project_targets', []),
                             ('github_project_targets', [{**data['github_project_targets'][0], 'operation': 'item-edit'}])]:
            changed = {**data, field: value}
            fixture.write(directory/'think-gate.json', changed)
            self.hook(self.board_command(), 2)
        fixture.write(directory/'think-gate.json', data)
        self.policy.write_text(json.dumps({'schema_version': 1, 'grants': [GRANT]}))
        self.hook(self.board_command(), 2)

    def test_declared_task_ambiguity_and_claim_shape_fail_closed(self):
        directory, data = self.board_manager()
        duplicate = self.task('electinfo/enterprise#3133', slug='duplicate-board-task')
        fixture.write(duplicate/'think-gate.json', data)
        self.hook(self.board_command(), 2)
        shutil.rmtree(duplicate)
        self.hook(self.board_command())
        for claim in [{**data['github_project_targets'][0], 'project': True},
                      {**data['github_project_targets'][0], 'issue': '*'},
                      {**data['github_project_targets'][0], 'host': 'github.com'},
                      {**data['github_project_targets'][0], 'repository': 'electinfo/enterprise'}]:
            changed = {**data, 'github_project_targets': [claim]}
            fixture.write(directory/'think-gate.json', changed)
            self.hook(self.board_command(board=1), 2)
        fixture.write(directory/'think-gate.json', {**data, 'task_id': 'electinfo/enterprise#9999'})
        self.hook(self.board_command().replace('CCP_TASK_ID=tc-3133-overnight-financial-delivery-20261112',
                                             'CCP_TASK_ID=electinfo/enterprise#9999'), 2)

    def test_declared_mode_cannot_enable_status_or_arbitrary_repositories(self):
        self.board_manager()
        grant = {**GRANT, 'issue_binding': 'current-task-or-declared-targets',
                 'declared_issue_repositories': ['electinfo/airflow']}
        for change in [{'operation': 'item-edit'}, {'declared_issue_repositories': []},
                       {'declared_issue_repositories': ['other/airflow']},
                       {'declared_issue_repositories': ['electinfo/airflow', 'electinfo/airflow']},
                       {'declared_issue_repositories': '*'}]:
            self.policy.write_text(json.dumps({'schema_version': 1, 'grants': [{**grant, **change}]}))
            self.assertIn('standing policy', self.hook(self.board_command(board=1), 2).stderr)

    def test_exact_add_uses_ticket_not_slug_and_no_code_artifacts(self):
        directory = self.task()
        data = json.loads((directory / 'think-gate.json').read_text())
        data['task_id'] = 'assessment-slug'
        fixture.write(directory / 'think-gate.json', data)
        self.hook()
        self.hook(ADD + ' # [destructive-ok: Reason: board tracking; Evidence: filed issue; Falsification: absent item]')
        self.hook(ADD + ' --format json')
        shape = fixture.r.action(ADD, str(self.f.ws))
        self.assertEqual(shape['paths'], [])
        self.assertFalse(shape.get('metadata_only'))
        self.assertEqual(shape['remote_actions'][0]['issue'], 3300)
        self.hook('gh project item-add 1 --url https://github.com/electinfo/enterprise/issues/3300 --owner electinfo')

    def test_original_reporter_canonical_task_id_needs_no_new_ticket_field(self):
        directory = self.task()
        data = json.loads((directory / 'think-gate.json').read_text())
        data['task_id'] = data.pop('ticket')
        data['tier'] = 'trivial'  # Actual reporter's legacy value; no code edit here.
        fixture.write(directory / 'think-gate.json', data)
        self.hook()
        data['task_id'] = 'assessment-slug'
        fixture.write(directory / 'think-gate.json', data)
        self.hook(code=2)

    def test_other_issue_owner_project_host_and_flags_denied(self):
        self.task()
        for command in [ADD.replace('/3300', '/3301'), ADD.replace('item-add 1', 'item-add 2'),
                        ADD.replace('--owner electinfo', '--owner other'),
                        ADD.replace('github.com', 'example.invalid'),
                        ADD.replace('/electinfo/enterprise/', '/other/enterprise/'),
                        ADD + ' --owner electinfo', ADD + ' --format xml',
                        'gh --hostname github.com ' + ADD[3:],
                        'env GH_HOST=example.invalid ' + ADD,
                        ADD.replace('issues/3300', 'pull/3300')]:
            with self.subTest(command=command):
                self.hook(command, 2)

    def test_gate_and_policy_absence_are_explained(self):
        result = self.hook(code=2)
        self.assertIn('current-session task', result.stderr)
        directory = self.task()
        self.policy.write_text('{"schema_version":1,"grants":[]}')
        data = json.loads((directory / 'think-gate.json').read_text())
        data['remote_resources'] = [GRANT]
        fixture.write(directory / 'think-gate.json', data)
        self.assertIn('standing policy', self.hook(code=2).stderr)
        self.policy.unlink()
        self.assertIn('standing policy', self.hook(code=2).stderr)

    def test_wrong_session_status_binding_and_ambiguous_ticket_denied(self):
        directory = self.task(sid='other')
        self.hook(code=2)
        shutil.rmtree(directory)
        directory = self.task()
        for status in ('designing', 'reviewing', 'disposed', 'revoked'):
            data = json.loads((directory / 'think-gate.json').read_text())
            data['status'] = status
            fixture.write(directory / 'think-gate.json', data)
            self.hook(code=2)
        data['status'] = 'implementing'
        fixture.write(directory / 'think-gate.json', data)
        self.hook('CCP_TASK_ID=unrelated ' + ADD, 2)
        other = self.task(slug='duplicate')
        self.hook(code=2)
        shutil.rmtree(other)
        self.hook()

    def test_conflicting_canonical_task_id_cannot_hide_behind_ticket(self):
        directory = self.task()
        data = json.loads((directory / 'think-gate.json').read_text())
        data['task_id'] = 'electinfo/enterprise#3301'
        fixture.write(directory / 'think-gate.json', data)
        result = self.hook(code=2)
        self.assertIn('conflicting canonical issue', result.stderr)

    def test_unrelated_local_and_remote_companions_do_not_early_allow(self):
        self.task()
        target = self.f.b / 'bad.md'
        for command in [ADD + ' > ' + str(target), ADD + ' | tee ' + str(target),
                        ADD + '; touch ' + str(target), 'touch ' + str(target) + ' && ' + ADD,
                        ADD + '; ' + ADD.replace('/3300', '/3301'),
                        ADD + '; gh project delete 1 --owner electinfo',
                        ADD + ' --url "$(touch ' + str(target) + ')"',
                        ADD + ' && bash -c "touch ' + str(target) + '"']:
            with self.subTest(command=command):
                self.hook(command, 2)
                self.assertFalse(target.exists())

    def test_same_task_local_companion_requires_owned_implementing_scope(self):
        self.task()
        command = ADD + '; touch ' + str(self.f.a / 'own.md')
        self.hook(command)
        self.hook(ADD + '; touch ' + str(self.f.b / 'foreign.md'), 2)
        self.f.task('electinfo/enterprise#3300', self.f.a, status='designing', artifacts=False)
        self.hook(command, 2)

    def test_unsupported_remote_mutations_fail_with_broad_local_gate(self):
        self.f.task('electinfo/enterprise#3300', self.f.ws, artifacts=True)
        denied = self.hook('gh project item-edit --project-id PVT_x --id PVTI_x --field-id PVTF_x --single-select-option-id option', 2)
        self.assertIn('installed standing policy has no Status item-edit grant', denied.stderr)
        for command in ['gh project item-delete 1 --owner electinfo --id PVTI_x',
                        'gh project delete 1 --owner electinfo',
                        "gh api graphql -f 'query=mutation { deleteProjectV2(input:{projectId:\"x\"}) { clientMutationId } }'",
                        'gh api graphql',
                        "gh api /graphql -f 'query=mutation { x }'",
                        "gh api https://api.github.com/graphql -f 'query=mutation { x }'",
                        "gh api --hostname example.invalid /graphql -f 'query=mutation { x }'",
                        "gh --hostname example.invalid api /graphql -f 'query=mutation { x }'",
                        "gh api /graphql/ -f 'query=mutation { x }'",
                        "gh api /%67raphql -f 'query=mutation { x }'",
                        "gh api //graphql -f 'query=mutation { x }'",
                        "gh api /x/../graphql -f 'query=mutation { x }'",
                        "gh api ./graphql -f 'query=mutation { x }'",
                        "gh api x/../graphql -f 'query=mutation { x }'",
                        "gh api %67raphql -f 'query=mutation { x }'",
                        'gh api /graphql --input request.json',
                        'gh api repos/electinfo/enterprise/issues/3300 -X DELETE',
                        'GH_HOST=example.invalid ' + ADD,
                        '/usr/bin/gh project delete 1 --owner electinfo']:
            with self.subTest(command=command):
                result = self.hook(command, 2)
                # Unsupported API mutations still fail before local gate authority;
                # unrelated GraphQL is no longer mislabeled as a queue enqueue.
                self.assertIn('Cannot resolve mutation targets', result.stderr)

    def test_wrapped_remote_mutations_cannot_borrow_a_broad_local_gate(self):
        self.f.task('electinfo/enterprise#3300', self.f.ws, artifacts=True)
        for prefix in ('timeout 5 ', 'nice ', 'time ', 'timeout --signal=KILL 5 ', '/usr/bin/nice '):
            for operation in ('gh project delete 1 --owner electinfo',
                              'gh project item-delete 1 --owner electinfo --id PVTI_x',
                              "gh api /graphql -f 'query=mutation {x}'"):
                command = 'cd ' + str(self.f.repo) + ' && ' + prefix + operation
                with self.subTest(command=command):
                    shape = fixture.r.action(command, str(self.f.ws))
                    reader = subprocess.run([sys.executable, str(ROOT / 'hooks/lib/read-only-command.py'), command],
                                            capture_output=True, text=True, timeout=10)
                    result = self.hook(command, 2)
                    self.assertNotEqual(reader.returncode,0)
                    self.assertTrue(shape.get('error'),shape)
                    self.assertIn('Wrapped GitHub',result.stderr)
        self.hook(ADD)
        self.hook('timeout 5 gh project list --owner electinfo')
        self.hook('nice gh project view 1 --owner electinfo')
        self.hook('cd ' + str(self.f.repo) + ' && timeout 5 pytest')

    def test_ambient_host_and_repository_overrides_are_not_authority(self):
        self.task()
        for fields in ({'GH_HOST':'example.invalid'}, {'GH_REPO':'other/repo'}):
            self.hook(code=2, env={**self.f.env, **fields})

    def test_metadata_words_do_not_become_project_operations(self):
        self.hook("gh issue edit 3300 --repo electinfo/enterprise --body project")
        self.hook("gh issue edit 3300 --repo electinfo/enterprise --body graphql")

    def test_policy_is_fixed_strict_and_not_a_symlink(self):
        self.task()
        for raw in ['{}', '{"schema_version":1,"schema_version":1,"grants":[]}',
                    json.dumps({'schema_version':1,'grants':[{**GRANT,'operation':'item-delete'}]})]:
            self.policy.write_text(raw)
            self.hook(code=2)
        source = self.f.ws / 'forged-policy.json'
        source.write_text(json.dumps({'schema_version':1,'grants':[GRANT]}))
        self.policy.unlink()
        self.policy.symlink_to(source)
        self.hook(code=2)
        self.policy.unlink()
        os.mkfifo(self.policy)
        self.hook(code=2)

    def test_readers_need_no_mutation_grant(self):
        self.policy.unlink()
        self.hook('gh project list --owner electinfo')
        self.hook('gh issue view 3300 --repo electinfo/enterprise')


if __name__ == '__main__':
    unittest.main()
