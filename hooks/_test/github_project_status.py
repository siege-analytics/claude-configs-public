#!/usr/bin/env python3
"""Real-hook status authorization with a controlled gh transport, no live writes."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('project_add_fixture', ROOT / 'hooks/_test/github_project_scope.py')
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
EDIT = 'gh project item-edit --project-id PVT_project --id PVTI_item --field-id PVTSSF_status --single-select-option-id progress'
GRANT = {**base.GRANT, 'operation':'item-edit', 'field_name':'Status', 'field_type':'SINGLE_SELECT', 'values':['In Progress','In Review']}
PROJECT = {'id':'PVT_project','number':1,'owner':{'__typename':'Organization','login':'electinfo'},
           'fields':{'pageInfo':{'hasNextPage':False},'nodes':[{'__typename':'ProjectV2SingleSelectField','id':'PVTSSF_status','name':'Status'}]}}
REPLY = {'data':{'item':{'__typename':'ProjectV2Item','id':'PVTI_item','isArchived':False,'project':PROJECT,
                       'content':{'__typename':'Issue','url':'https://github.com/electinfo/enterprise/issues/3300','number':3300,'repository':{'nameWithOwner':'electinfo/enterprise'}},'status':None},
                 'field':{'__typename':'ProjectV2SingleSelectField','id':'PVTSSF_status','name':'Status','dataType':'SINGLE_SELECT',
                          'project':{'id':'PVT_project'},'options':[{'id':'progress','name':'In Progress'},{'id':'review','name':'In Review'},{'id':'done','name':'Done'}]}}}


class StatusScope(unittest.TestCase):
    def setUp(self):
        self.f = base.ProjectScope(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.f.task()
        self.f.policy.write_text(json.dumps({'schema_version':1,'grants':[base.GRANT,GRANT]}))
        self.reply = self.f.f.ws / 'reply.json'; self.reply.write_text(json.dumps(REPLY))
        self.calls = self.f.f.ws / 'gh-calls.jsonl'
        tools = self.f.f.ws / 'tools'; tools.mkdir()
        gh = tools / 'gh'
        self.heartbeat = self.f.f.ws / 'child-heartbeat'
        gh.write_text('#!' + sys.executable + '\n' + f"""import json,os,sys,time
from pathlib import Path
with open({str(self.calls)!r}, 'a') as log:
    log.write(json.dumps(sys.argv[1:]) + '\\n')
v = Path({str(self.reply)!r}).read_text()
if v == 'CHILD':
    if os.fork() == 0:
        while True:
            Path({str(self.heartbeat)!r}).write_text(str(time.monotonic()))
            time.sleep(0.05)
    time.sleep(30)
elif v == 'HANG':
    time.sleep(30)
elif v == 'FLOOD':
    print('x' * 1100000)
else:
    print(v)
""")
        gh.chmod(0o755)
        self.env = {**self.f.f.env, 'PATH':str(tools)+os.pathsep+self.f.f.env['PATH']}

    def hook(self, command=EDIT, code=0):
        return self.f.hook(command,code,self.env)

    def test_exact_status_values_use_live_membership_and_fixed_query(self):
        self.hook(); self.hook(EDIT.replace('progress','review'))
        calls=[json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(len(calls),2)
        for args in calls:
            self.assertEqual(args[:4],['api','graphql','--hostname','github.com'])
            query=next(arg for arg in args if arg.startswith('query='))
            self.assertTrue(query.startswith('query=query ')); self.assertNotIn('mutation',query)

    def test_wrong_membership_field_option_and_content_are_denied(self):
        cases=[('project',lambda x:x['data']['item']['project'].update(number=2)),
               ('item',lambda x:x['data']['item'].update(id='other')),
               ('owner',lambda x:x['data']['item']['project']['owner'].update(login='other')),
               ('archived',lambda x:x['data']['item'].update(isArchived=True)),
               ('done-reset',lambda x:x['data']['item'].update(status={'__typename':'ProjectV2ItemFieldSingleSelectValue','optionId':'done','field':{'id':'PVTSSF_status'}})),
               ('issue',lambda x:x['data']['item']['content'].update(number=3301,url='https://github.com/electinfo/enterprise/issues/3301')),
               ('field',lambda x:x['data']['field']['project'].update(id='other')),
               ('malformed-owner',lambda x:x['data']['item']['project']['owner'].update(login=7)),
               ('name',lambda x:x['data']['field'].update(name='Priority')),
               ('type',lambda x:x['data']['item']['content'].update(__typename='PullRequest')),
               ('page',lambda x:x['data']['item']['project']['fields']['pageInfo'].update(hasNextPage=True)),
               ('duplicate',lambda x:x['data']['item']['project']['fields']['nodes'].append(copy.deepcopy(x['data']['item']['project']['fields']['nodes'][0]))),
               ('errors',lambda x:x.update(errors=[{'message':'no permission'}]))]
        for name,change in cases:
            with self.subTest(name=name):
                value=copy.deepcopy(REPLY);change(value);self.reply.write_text(json.dumps(value));self.hook(code=2)
        self.reply.write_text(json.dumps(REPLY));self.hook(EDIT.replace('progress','done'),2)
        self.hook(EDIT.replace('progress','foreign'),2)

    def test_fixed_policy_must_grant_status_before_network(self):
        self.f.policy.write_text(json.dumps({'schema_version':1,'grants':[base.GRANT]}));self.hook(code=2)
        self.assertFalse(self.calls.exists())

    def test_unsupported_shapes_and_composition_do_not_lend_authority(self):
        for command in [EDIT+' --clear',EDIT+' --field-id other',EDIT.replace('--single-select-option-id progress','--text hello'),
                        EDIT+' > '+str(self.f.f.b/'foreign.txt'),EDIT+'; gh project delete 1 --owner electinfo',
                        "gh api /graphql -f 'query=mutation { x }'",'env GH_HOST=other '+EDIT]:
            with self.subTest(command=command):self.hook(command,2)

    def test_task_binding_native_shape_and_same_task_composition(self):
        directory = next((self.f.f.ws / 'sessions/one/tasks').glob('*/think-gate.json'))
        data = json.loads(directory.read_text()); data['task_id'] = data.pop('ticket')
        directory.write_text(json.dumps(data))
        self.hook()
        mixed = EDIT + '; touch ' + str(self.f.f.a / 'notes.md')
        self.hook(mixed, 2)  # Remote permission cannot replace local artifacts.
        self.f.f.task('electinfo/enterprise#3300', self.f.f.a, artifacts=True)
        self.hook(mixed)
        data['ticket'] = 'electinfo/enterprise#3301'
        directory.write_text(json.dumps(data)); self.hook(code=2)

    def test_unrelated_tasks_do_not_block_exact_item_owner(self):
        self.f.f.task('electinfo/enterprise#3301', self.f.f.b, artifacts=False)
        self.hook()
        self.f.f.task('electinfo/enterprise#3302', self.f.f.ws, status='designing', artifacts=False)
        self.hook()
        self.f.f.task('electinfo/enterprise#3303', self.f.f.ws, status='disposed', artifacts=False)
        self.hook()
        self.f.f.task('electinfo/enterprise#3300', self.f.f.a, slug='duplicate-owner', artifacts=False)
        self.hook(code=2)

    def test_missing_designing_and_foreign_session_cannot_borrow_another_task(self):
        directory = next((self.f.f.ws / 'sessions/one/tasks').glob('*/think-gate.json'))
        original = json.loads(directory.read_text())
        self.f.f.task('electinfo/enterprise#3301', self.f.f.b, artifacts=False)
        directory.write_text(json.dumps({**original, 'status':'designing'})); self.hook(code=2)
        directory.unlink(); self.hook(code=2)
        self.f.f.task('electinfo/enterprise#3300', self.f.f.a, sid='two', artifacts=False)
        self.hook(code=2)  # Another session's exact issue cannot lend authority.
        directory.write_text(json.dumps(original)); self.hook()

    def test_duplicate_remote_edits_do_not_amplify_network_deadline(self):
        self.hook(EDIT + '; ' + EDIT, 2)
        self.assertFalse(self.calls.exists())

    def test_policy_cannot_grant_other_values_fields_or_duplicate_values(self):
        for patch in [{'values':['Closed']}, {'field_name':'Priority'}, {'values':['In Progress','In Progress']}]:
            with self.subTest(patch=patch):
                self.f.policy.write_text(json.dumps({'schema_version':1,'grants':[{**GRANT,**patch}]}))
                self.hook(code=2)
        self.assertFalse(self.calls.exists())

    def test_done_needs_its_explicit_installed_value_grant(self):
        done = EDIT.replace('progress', 'done')
        self.hook(done, 2)
        grant = {**GRANT, 'values':['Done']}
        self.f.policy.write_text(json.dumps({'schema_version':1, 'grants':[grant]}))
        completed = copy.deepcopy(REPLY)
        # Business completion is context, not a new Core Issue-state gate.
        completed['data']['item']['content']['state'] = 'CLOSED'
        self.reply.write_text(json.dumps(completed))
        self.hook(done)
        self.hook(EDIT, 2)
        self.hook(EDIT.replace('progress', 'review'), 2)

    def test_done_grant_does_not_expand_task_project_owner_or_field(self):
        self.f.policy.write_text(json.dumps({'schema_version':1, 'grants':[{**GRANT, 'values':['Done']}]}))
        done = EDIT.replace('progress', 'done')
        for name, change in [
                ('foreign-task', lambda value:value['data']['item']['content'].update(number=3301, url='https://github.com/electinfo/enterprise/issues/3301')),
                ('foreign-project', lambda value:value['data']['item']['project'].update(number=2)),
                ('foreign-owner', lambda value:value['data']['item']['project']['owner'].update(login='other')),
                ('foreign-field', lambda value:value['data']['field']['project'].update(id='other'))]:
            with self.subTest(name=name):
                value = copy.deepcopy(REPLY); change(value)
                self.reply.write_text(json.dumps(value)); self.hook(done, 2)

    def test_done_grant_cannot_reset_an_already_done_item(self):
        self.f.policy.write_text(json.dumps({'schema_version':1, 'grants':[{**GRANT, 'values':['In Progress','In Review','Done']}]}))
        value = copy.deepcopy(REPLY)
        value['data']['item']['status'] = {'__typename':'ProjectV2ItemFieldSingleSelectValue', 'optionId':'done', 'field':{'id':'PVTSSF_status'}}
        self.reply.write_text(json.dumps(value))
        for option in ('progress', 'review', 'done'):
            with self.subTest(option=option):self.hook(EDIT.replace('progress', option), 2)

    def test_timeout_stops_descendant_writer(self):
        import time
        self.reply.write_text('CHILD'); self.hook(code=2)
        self.assertTrue(self.heartbeat.is_file())
        before = self.heartbeat.read_text()
        time.sleep(0.3)
        self.assertEqual(self.heartbeat.read_text(), before)

    def test_bad_or_excessive_response_fails_closed_with_bounded_wait(self):
        import time
        for response in ['{}','{bad','{"data":{},"data":{}}','{"data":null}','{"data":{"item":null,"field":null}}','FLOOD','HANG']:
            with self.subTest(response=response):
                self.reply.write_text(response);start=time.monotonic();result=self.hook(code=2)
                self.assertIn('cannot verify live Status membership', result.stderr)
                self.assertLess(time.monotonic()-start,8)


if __name__=='__main__':unittest.main()
