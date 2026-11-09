#!/usr/bin/env python3
"""Actual coordinator hook, fixed read-only GitHub transport fixtures (#1218)."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import task_keyed_gates as fixture

ROOT = Path(__file__).resolve().parents[2]
SHA = 'a' * 40


class Mechanical(unittest.TestCase):
    def setUp(self):
        self.f = fixture.Gates(); self.f.setUp(); self.addCleanup(self.f.tearDown)
        subprocess.run(['git', '-C', str(self.f.repo), 'checkout', '-qb', 'fix/31'], check=True, timeout=15)
        subprocess.run(['git', '-C', str(self.f.repo), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '--allow-empty', '-qm', 'fixture'], check=True, timeout=15)
        self.head = subprocess.check_output(['git', '-C', str(self.f.repo), 'rev-parse', 'HEAD'], text=True, timeout=15).strip()
        self.f.task('example/target#31', self.f.repo)
        self.bin = self.f.ws/'bin'; self.bin.mkdir()
        self.calls = self.f.ws/'calls.jsonl'
        self.mode = self.f.ws/'mode'; self.mode.write_text('ok')
        gh = self.bin/'gh'
        gh.write_text('#!' + sys.executable + '\n' + '''import json,os,sys,time
from pathlib import Path
a=sys.argv[1:]; mode=Path(os.environ['MECHANICAL_MODE']).read_text()
with open(os.environ['MECHANICAL_CALLS'],'a') as f:f.write(json.dumps(a)+'\\n')
if mode=='fail':sys.exit(1)
if mode=='bad':print('{');sys.exit(0)
if mode=='huge':print('x'*1100000);sys.exit(0)
if mode=='hang':time.sleep(20)
if len(a)>3 and a[:3]==['api','--hostname','github.com']:
 parts=a[3].split('/')
 if len(parts)>=3 and parts[0]=='repos':a[3]='/'.join([parts[0],parts[1].lower(),parts[2].lower(),*parts[3:]])
def item_url(number,resource):
 value='https://github.com/example/target/'+resource+'/'+str(number)
 if mode=='urlcase' or mode=='issueurlcase' and resource=='issues':value=value.replace('/example/target/','/Example/Target/')
 if mode=='urlhost':value=value.replace('https://github.com/','https://GITHUB.com/')
 if mode=='urlforeign':value=value.replace('/example/target/','/other/target/')
 if mode=='urlresource':value=value.replace('/'+resource+'/','/'+resource+'s/')
 if mode=='urlnumber':value=value.rsplit('/',1)[0]+'/'+str(number+1)
 if mode=='urlquery':value+='?unexpected=1'
 return value
if a[:4]==['api','--hostname','github.com','user']:
 if mode in ['appbot','appforeign']:
  print(json.dumps({'message':'Resource not accessible by integration','status':'403'}));sys.exit(1)
 print(json.dumps({'login':'agent'}))
elif a==['api','--hostname','github.com','graphql','-f','query=query { viewer { login } }']:
 if mode=='viewer_missing':print(json.dumps({'data':{}}))
 elif mode=='viewer_null':print(json.dumps({'data':{'viewer':None}}))
 elif mode=='viewer_malformed':print(json.dumps({'data':{'viewer':{'login':[]}}}))
 elif mode=='viewer_blank':print(json.dumps({'data':{'viewer':{'login':' '}}}))
 elif mode=='viewer_wrongdata':print(json.dumps({'data':[]}))
 elif mode=='viewer_errors':print(json.dumps({'data':{'viewer':{'login':'agent'}},'errors':[{'message':'identity proof unavailable'}]}))
 else:print(json.dumps({'data':{'viewer':{'login':'electinfo-platform[bot]' if mode in ['appbot','appforeign'] else 'agent'}}}))
elif a[:4]==['api','--hostname','github.com','repos/electinfo/spark-on-kubernetes/pulls/95']:
 body={'cross_relative':'Refs #3304','cross_foreign':'Refs other/enterprise#3304','cross_wrongnumber':'Refs electinfo/enterprise#3305'}.get(mode,'Refs electinfo/enterprise#3304')
 print(json.dumps(dict(number=95,html_url='https://github.com/electinfo/spark-on-kubernetes/pull/95',state='open',draft=True,user={'login':'agent'},head={'sha':os.environ['MECHANICAL_HEAD'],'ref':'fix/3304','repo':{'full_name':'electinfo/spark-on-kubernetes'}},base={'ref':'develop','repo':{'full_name':'electinfo/spark-on-kubernetes'}},body=body)))
elif a[:4]==['api','--hostname','github.com','repos/example/target/pulls/50']:
 print(json.dumps(dict(number=50,html_url=item_url(50,'pull'),state='open',draft=True,user={'login':'other' if mode=='other' else ('different-app[bot]' if mode=='appforeign' else ('electinfo-platform[bot]' if mode=='appbot' else 'agent'))},head={'sha':('b'*40 if mode=='head' else os.environ['MECHANICAL_HEAD']),'ref':'fix/31','repo':{'full_name':'example/target'}},base={'ref':'develop','repo':{'full_name':'example/target'}},body={'refs':'Refs example/target#31','multirefs':'Refs #99, example/target#31, #77.','quotedrefs':'"Refs #31"','foreignrefs':'Refs foreign/target#31','longfencedrefs':'````text\\n```\\nRefs #31\\n````','lazyquotedrefs':'> Example\\nRefs #31','negatedrefs':'Does not reference #31','fencedrefs':'```text\\nRefs #31\\n```','examplerefs':'Example:\\nRefs #31'}.get(mode,'Fixes #31'))))
elif a[:4]==['api','--hostname','github.com','repos/example/target/pulls/60']:
 relation={'refs':'Refs example/target#31.','multirefs':'Refs #99, example/target#31, #77.','quotedrefs':'"Refs #31"','foreignrefs':'Refs foreign/target#31','longfencedrefs':'````text\\n```\\nRefs #31\\n````','lazyquotedrefs':'> Example\\nRefs #31','negatedrefs':'Does not reference #31','fencedrefs':'```text\\nRefs #31\\n```','examplerefs':'Example:\\nRefs #31','unrelated':'Fixes #99','issuesuperseded':'Supersedes issue #31.','fencedfix':'```text\\nFixes #31\\n```'}.get(mode,'Fixes #31.')
 print(json.dumps(dict(number=60,html_url=item_url(60,'pull'),state=('open' if mode=='unlanded' else 'closed'),merged=mode!='unlanded',merge_commit_sha='a'*40,user={'login':'other' if mode=='sourceother' else 'agent'},base={'ref':'develop','repo':{'full_name':'example/target'}},body=relation+' Supersedes PR #50.')))
elif a[:4]==['api','--hostname','github.com','repos/example/target/issues/31']:
 print(json.dumps({'number':31,'html_url':item_url(31,'issues'),'state':'open'}))
elif a[:4]==['api','--hostname','github.com','repos/example/target']:
 print(json.dumps({'full_name':'example/target','default_branch':'main'}))
elif a[:4]==['api','--hostname','github.com','repos/example/target/compare/main...'+('a'*40)]:
 print(json.dumps({'status':'ahead' if mode=='default' else 'behind'}))
elif a[:4]==['api','--hostname','github.com','repos/example/target/compare/develop...'+('a'*40)]:
 print(json.dumps({'status':'ahead' if mode=='base' else 'behind'}))
else:sys.exit(99)
'''); gh.chmod(0o755)
        self.env = dict(self.f.env, PATH=str(self.bin)+os.pathsep+self.f.env['PATH'], MECHANICAL_MODE=str(self.mode), MECHANICAL_CALLS=str(self.calls), MECHANICAL_HEAD=self.head)

    def hook(self, command, expected, cwd=None):
        payload=fixture.craft_payload(tool_name='Bash',cwd=str(cwd or self.f.repo),tool_input={'command':command})
        r=subprocess.run(['bash',str(ROOT/'hooks/bash/coordinator-status-guard.sh')],input=json.dumps(payload),env=self.env,text=True,capture_output=True,timeout=15)
        self.assertEqual(r.returncode,expected,(command,r.stdout,r.stderr))
        return r

    def test_repository_case_identity_only(self):
        for mode,command in [
            ('urlcase','gh pr ready 50 --repo example/target'),
            ('ok','gh pr ready 50 -R Example/Target'),
            ('issueurlcase',"gh issue close 31 --repo example/target --comment 'Fixed by PR #60\nRollout: N/A: verified publication metadata.'"),
        ]:
            with self.subTest(mode=mode):
                self.mode.write_text(mode)
                self.hook(command,0)
        for mode in ['urlhost','urlforeign','urlresource','urlnumber','urlquery']:
            with self.subTest(reject=mode):
                self.mode.write_text(mode)
                self.hook('gh pr ready 50 --repo example/target',2)

    def test_app_installation_identity_uses_same_actor_viewer(self):
        self.mode.write_text('appbot')
        self.hook('gh pr ready 50 --repo example/target',0)
        self.hook("gh pr close 50 --repo example/target --comment 'Superseded by PR #60\nRollout: N/A: duplicate metadata only.'",0)
        calls=[json.loads(x) for x in self.calls.read_text().splitlines()]
        identity=['api','--hostname','github.com','graphql','-f','query=query { viewer { login } }']
        self.assertEqual(sum(x==identity for x in calls),2)
        self.assertFalse(any(x[-1:] == ['user'] for x in calls))
        self.mode.write_text('appforeign')
        self.hook('gh pr ready 50 --repo example/target',2)
        self.hook("gh pr close 50 --repo example/target --comment 'Superseded by PR #60\nRollout: N/A.'",2)

    def test_viewer_identity_missing_malformed_or_partial_fails_closed(self):
        for mode in ['viewer_missing','viewer_null','viewer_malformed','viewer_blank','viewer_wrongdata','viewer_errors']:
            with self.subTest(mode=mode):
                self.mode.write_text(mode)
                self.hook('gh pr ready 50 --repo example/target',2)

    def test_own_ready(self):
        self.hook('gh pr ready 50 --repo example/target',0)

    def central_task(self):
        shutil.rmtree(self.f.ws/'sessions/one/tasks')
        subprocess.run(['git','-C',str(self.f.repo),'branch','-m','fix/3304'],check=True,timeout=15)
        return self.f.task('electinfo/enterprise#3304',self.f.repo)

    def test_cross_repository_ready_real_central_ticket_shape(self):
        self.central_task()
        self.hook('gh pr ready 95 --repo electinfo/spark-on-kubernetes',0)

    def test_cross_repository_ready_requires_canonical_not_relative_reference(self):
        self.central_task()
        for mode in ['cross_relative','cross_foreign','cross_wrongnumber']:
            with self.subTest(mode=mode):
                self.mode.write_text(mode)
                self.hook('gh pr ready 95 --repo electinfo/spark-on-kubernetes',2)

    def test_cross_repository_ready_existing_inline_task_binding(self):
        self.central_task()
        self.f.task('electinfo/enterprise#3305',self.f.repo)
        command='gh pr ready 95 --repo electinfo/spark-on-kubernetes'
        self.hook(command,2)
        self.hook("CCP_TASK_ID='electinfo/enterprise#3304' "+command,0)
        self.env['CCP_TASK_ID']='electinfo/enterprise#3305'
        self.hook("CCP_TASK_ID='electinfo/enterprise#3304' "+command,2)

    def test_cross_repository_does_not_expand_close_grammar(self):
        self.central_task()
        for command in ["gh issue close 3304 --repo electinfo/spark-on-kubernetes --comment 'Fixed by PR #60\nRollout: N/A.'", "gh pr close 95 --repo electinfo/spark-on-kubernetes --comment 'Superseded by PR #60\nRollout: N/A.'"]:
            self.hook(command,2)

    def test_same_repository_close_uses_existing_literal_binding_full_chain(self):
        self.f.task('example/target#32',self.f.repo)
        settings=json.loads((ROOT/'hooks/settings-snippet.json').read_text())
        hooks=[ROOT/h['command'].split('/claude-configs-public/',1)[1]
               for group in settings['hooks']['PreToolUse'] if group.get('matcher')=='Bash'
               for h in group['hooks']]
        def chain(command):
            payload=fixture.craft_payload(tool_name='Bash',cwd=str(self.f.repo),tool_input={'command':command})
            outcomes={}
            for hook in hooks:
                result=subprocess.run(['bash',str(hook)],input=json.dumps(payload),env=self.env,text=True,capture_output=True,timeout=15,cwd=self.f.repo)
                self.assertIn(result.returncode,[0,2],(hook.name,result.stderr))
                outcomes[hook.name]=result.returncode
            self.assertEqual(len(outcomes),16)
            return outcomes
        commands=["gh issue close 31 --repo example/target --comment 'Fixed by PR #60\nRollout: N/A: verified publication metadata.'",
                  "gh pr close 50 --repo example/target --comment 'Superseded by PR #60\nRollout: N/A: duplicate metadata only.'"]
        for command in commands:
            with self.subTest(command=command):
                self.hook(command,2)  # The existing two-task ambiguity is real.
                selected="CCP_TASK_ID='example/target#31' "+command
                self.assertTrue(all(code==0 for code in chain(selected).values()))
                self.assertEqual(chain("CCP_TASK_ID='example/target#32' "+command)['coordinator-status-guard.sh'],2)
                self.assertEqual(chain("CCP_TASK_ID='foreign/repository#31' "+command)['coordinator-status-guard.sh'],2)
                self.env['CCP_TASK_ID']='example/target#32'
                outcomes=chain(selected)
                self.assertEqual(outcomes['coordinator-status-guard.sh'],2)
                self.assertEqual(outcomes['universal-mutation-gate.sh'],2)
                self.env.pop('CCP_TASK_ID')

    def cross_ready_chain(self, binding='', cwd=None):
        settings=json.loads((ROOT/'hooks/settings-snippet.json').read_text())
        hooks=[ROOT/h['command'].split('/claude-configs-public/',1)[1]
               for group in settings['hooks']['PreToolUse'] if group.get('matcher')=='Bash'
               for h in group['hooks']]
        command='cd '+str(self.f.repo)+' && '+binding+'gh pr ready 95 --repo electinfo/spark-on-kubernetes'
        payload=fixture.craft_payload(tool_name='Bash',cwd=str(cwd or self.f.ws/'sessions/one'),tool_input={'command':command})
        outcomes={}
        for hook in hooks:
            result=subprocess.run(['bash',str(hook)],input=json.dumps(payload),env=self.env,text=True,capture_output=True,timeout=15,cwd=self.f.repo)
            outcomes[hook.name]=result.returncode
            self.assertIn(result.returncode,[0,2],(hook.name,result.stderr))
        self.assertEqual(len(outcomes),16)
        return outcomes

    def test_cross_ready_binding_full_guard_chain_and_ambiguity(self):
        self.central_task()
        self.f.task('electinfo/enterprise#3305',self.f.repo)
        self.assertEqual(self.cross_ready_chain()['universal-mutation-gate.sh'],2)
        self.assertTrue(all(code==0 for code in self.cross_ready_chain("CCP_TASK_ID='electinfo/enterprise#3304' ").values()))

    def test_cross_ready_lifecycle_and_scope_stay_with_actual_mutation_guard(self):
        directory=self.central_task()
        path=directory/'think-gate.json';data=json.loads(path.read_text())
        fixture.write(path,{**data,'status':'reviewing'})
        outcomes=self.cross_ready_chain()
        self.assertEqual(outcomes['coordinator-status-guard.sh'],0)  # No new phase gate here.
        self.assertEqual(outcomes['universal-mutation-gate.sh'],2)
        for fields in [{'status':'disposed'},{'scope_paths':[str(self.f.b)]}]:
            fixture.write(path,{**data,**fields})
            self.assertEqual(self.cross_ready_chain()['universal-mutation-gate.sh'],2)

    def test_ready_binding_is_literal_conflict_checked_and_not_an_env_wrapper(self):
        self.central_task()
        command='gh pr ready 95 --repo electinfo/spark-on-kubernetes'
        for prefix in ['env CCP_TASK_ID=electinfo/enterprise#3304 ', 'OTHER=x ', 'CCP_TASK_ID=electinfo/enterprise#3304 OTHER=x ']:
            self.hook(prefix+command,2)

    def test_same_repository_ready_selection_is_not_broadened_by_other_tasks(self):
        self.f.task('electinfo/enterprise#3304',self.f.repo)
        self.hook('gh pr ready 50 --repo example/target',0)

    def test_landed_issue_close(self):
        self.hook("gh issue close 31 --repo example/target --comment 'Fixed by PR #60\nRollout: N/A.'",0)

    def test_landed_pr_supersession(self):
        self.hook("gh pr close 50 --repo example/target --comment 'Superseded by PR #60\nRollout: N/A.'",0)

    def test_ready_accepts_refs_only_in_ready_lane(self):
        self.mode.write_text('refs')
        self.hook('gh pr ready 50 --repo example/target',0)
        for mode in ['quotedrefs','foreignrefs','negatedrefs','fencedrefs','longfencedrefs','lazyquotedrefs','examplerefs']:
            self.mode.write_text(mode)
            self.hook('gh pr ready 50 --repo example/target',2)

    def test_landed_issue_close_accepts_realistic_reference_list(self):
        self.mode.write_text('multirefs')
        self.hook("gh issue close 31 --repo example/target --comment 'Fixed by PR #60\nRollout: N/A: verified publication metadata.'",0)
        self.hook('gh pr ready 50 --repo example/target',0)

    def test_other_author_landed_source_allowed_other_actor_target_denied(self):
        self.mode.write_text('sourceother')
        self.hook("gh issue close 31 --repo example/target --comment 'Fixed by PR #60\nRollout: N/A: metadata after verified integration.'",0)
        self.hook("gh pr close 50 --repo example/target --comment 'Superseded by PR #60\nRollout: N/A: duplicate metadata.'",0)
        calls=[json.loads(x) for x in self.calls.read_text().splitlines()]
        self.assertEqual(sum(x[:4] == ['api','--hostname','github.com','graphql'] for x in calls),1)
        self.assertFalse(any(x[-1:] == ['user'] for x in calls))
        self.mode.write_text('other')
        self.hook("gh pr close 50 --repo example/target --comment 'Superseded by PR #60\nRollout: N/A.'",2)

    def test_issue_supersession(self):
        self.mode.write_text('issuesuperseded')
        self.hook("gh issue close 31 --repo example/target --comment 'Superseded by PR #60\nRollout: N/A: supersession metadata after integration.'",0)

    def test_negative_proofs(self):
        for mode in ['other','head']:
            self.mode.write_text(mode)
            self.hook('gh pr ready 50 --repo example/target',2)
        for mode in ['unlanded','unrelated','fencedfix','quotedrefs','foreignrefs','negatedrefs','fencedrefs','longfencedrefs','lazyquotedrefs','examplerefs','base','default','bad','fail','huge']:
            self.mode.write_text(mode)
            self.hook("gh issue close 31 --repo example/target --comment 'Fixed by PR #60\nRollout: N/A.'",2)

    def test_no_task_or_review_role(self):
        self.f.task('example/target#31',self.f.repo,status='reviewing')
        self.hook('gh pr ready 50 --repo example/target',0)
        self.f.task('example/target#31',self.f.repo)
        fixture.write(self.f.ws/'sessions/one/session.jsonl',{'id':'one','sdkSessionId':fixture.SDK_UUID,'labels':['role::reviewer']})
        self.hook('gh pr ready 50 --repo example/target',2)

    def test_explicit_task_role_boundary_without_verifier_ceremony(self):
        directory=self.f.task('example/target#31',self.f.repo)
        path=directory/'think-gate.json'; task=json.loads(path.read_text())
        for role in ['read-only','review-only','comment-only','observer']:
            fixture.write(path,{**task,'role':role})
            self.hook('gh pr ready 50 --repo example/target',2)
        fixture.write(path,{**task,'role':'verifier'})
        fixture.write(self.f.ws/'sessions/one/session.jsonl',{'id':'one','sdkSessionId':fixture.SDK_UUID,'labels':['role::verifier']})
        self.hook('gh pr ready 50 --repo example/target',0)

    def test_no_compound_or_unrelated_allowance(self):
        for cmd in ['gh pr ready 50 --repo example/target; gh pr ready 99 --repo example/target', 'gh pr reopen 50 --repo example/target', 'gh pr merge 50 --repo example/target', 'gh api graphql -f query=enqueuePullRequest', 'gh api -X PUT repos/example/target/rulesets/1']:
            # Coordinator has never independently gated every merge/protection
            # command: assert no mechanical lookup/allowance, then run UMG too.
            if self.calls.exists():self.calls.unlink()
            self.hook(cmd,2 if 'ready' in cmd or 'reopen' in cmd else 0)
            self.assertFalse(self.calls.exists())

    def test_actual_mutation_guard_stays_separate(self):
        for command in ['gh pr ready 50 --repo example/target', "gh issue close 31 --repo example/target --comment 'Fixed by PR #60\nRollout: N/A.'"]:
            result = self.f.hook(command, env=self.env)
            self.assertEqual(result.returncode, 0, result.stderr)
        shutil.rmtree(self.f.ws/'sessions/one/tasks')
        for command in ['gh pr merge 50 --repo example/target', 'gh api graphql -f query=enqueuePullRequest', 'gh api -X PUT repos/example/target/rulesets/1']:
            result = self.f.hook(command, env=self.env)
            self.assertEqual(result.returncode, 2, result.stderr)

    def test_missing_wrong_task_and_ambiguous_options(self):
        for command in ['gh pr ready 99 --repo example/target', 'gh pr ready 50 --repo example/target -R example/target', 'gh pr ready 50 --repo other/target', "gh issue close 99 --repo example/target --comment 'Fixed by PR #60\nRollout: N/A.'", "gh issue close 31 --repo example/target --comment 'Fixed by PR #99'", "gh issue close 31 --repo example/target --comment 'Fixed by PR #60\nRollout: N/A.' --reason 'not planned'"]:
            self.hook(command,2)
        shutil.rmtree(self.f.ws/'sessions/one/tasks')
        self.hook('gh pr ready 50 --repo example/target',2)

    def test_time_bounded_failure(self):
        self.mode.write_text('hang')
        self.hook('gh pr ready 50 --repo example/target',2)

    def test_malformed_mechanical_helper_fails_closed(self):
        install=self.f.ws/'installed'
        shutil.copytree(ROOT/'hooks',install/'hooks')
        (install/'hooks/lib/github-mechanical-completion.py').write_text('def broken(:\n')
        command='gh pr ready 50 --repo example/target'
        payload=fixture.craft_payload(tool_name='Bash',cwd=str(self.f.repo),tool_input={'command':command})
        result=subprocess.run(['bash',str(install/'hooks/bash/coordinator-status-guard.sh')],input=json.dumps(payload),env=self.env,text=True,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,2,result.stderr)
        self.assertIn('lacks required evidence',result.stderr)

    def test_1210_typed_reply_composition(self):
        # The actual tracked combined source supplies the shared parser and
        # typed reply classifier. Missing joint dependencies fail this test.
        actions=ROOT/'hooks/lib/task_actions.py'
        self.assertIn('\ndef github_review_reply(',actions.read_text())
        self.assertIn('\ndef github_ticket_reference(',actions.read_text())
        install=self.f.ws/'reply-installed'
        shutil.copytree(ROOT/'hooks',install/'hooks')
        shutil.copyfile(actions,install/'hooks/lib/task_actions.py')
        endpoint='repos/example/target/pulls/50/comments/90/replies'
        for command,expected in [
            ("gh api "+endpoint+" -X POST -f 'body=Complete: missing edge case is now covered.'",0),
            ("gh api "+endpoint+" -f 'body=Complete: missing edge case is now covered.' --jq '.id'",0),
            ("gh api "+endpoint+" -X DELETE -f 'body=Complete.'",2),
            ("gh api "+endpoint+" -X GET -f 'body=Complete.'",2),
            ("gh api "+endpoint+" -f 'body=Complete.' --jq '.id' -q '.id'",2),
            ("gh api repos/example/target/pulls/50/comments -X POST -f 'body=Complete: missing edge case.'",2),
        ]:
            payload=fixture.craft_payload(tool_name='Bash',cwd=str(self.f.repo),tool_input={'command':command})
            result=subprocess.run(['bash',str(install/'hooks/bash/coordinator-status-guard.sh')],input=json.dumps(payload),env=self.env,text=True,capture_output=True,timeout=15)
            self.assertEqual(result.returncode,expected,(command,result.stderr))
        self.assertFalse(self.calls.exists())  # Coordinator duplicates no network authorization.

    def test_shared_parser_keeps_relative_references_in_actual_pr_repository(self):
        from task_actions import github_ticket_reference
        cases=[
            ('Refs #3304',False),
            ('References electinfo/enterprise#3304',True),
            ('Refs #95, electinfo/enterprise#3304.',True),
            ('Refs https://github.com/electinfo/enterprise/issues/3304',True),
            ('Refs other/enterprise#3304',False),
            ('Not Refs electinfo/enterprise#3304',False),
            ('"Refs electinfo/enterprise#3304"',False),
            ('```text\nRefs electinfo/enterprise#3304\n```',False),
            ('````text\n```\nRefs electinfo/enterprise#3304\n````',False),
            ('Example:\nRefs electinfo/enterprise#3304',False),
            ('> Example\nRefs electinfo/enterprise#3304',False),
        ]
        for body,expected in cases:
            self.assertEqual(github_ticket_reference(body,3304,'electinfo/enterprise','reference',source_repo='electinfo/spark-on-kubernetes'),expected,body)
        self.assertTrue(github_ticket_reference('Refs #3304',3304,'electinfo/enterprise','reference'))
        self.assertTrue(github_ticket_reference('Fixes #31',31,'example/target'))
        self.assertTrue(github_ticket_reference('Supersedes PR #50',50,'example/target','supersede','pull'))
        self.assertFalse(self.calls.exists())  # Data parsing performs no remote reads.

    def test_close_retains_rollout_evidence(self):
        result = self.hook("gh issue close 31 --repo example/target --comment 'Fixed by PR #60'",2)
        self.assertIn('Missing: rollout',result.stderr)

    def test_full_bash_guard_chain_positive(self):
        settings=json.loads((ROOT/'hooks/settings-snippet.json').read_text())
        hooks=[ROOT/h['command'].split('/claude-configs-public/',1)[1]
               for group in settings['hooks']['PreToolUse'] if group.get('matcher')=='Bash'
               for h in group['hooks']]
        self.assertEqual(len(hooks),16)
        self.mode.write_text('multirefs')
        for command in ['gh pr ready 50 --repo example/target', "gh issue close 31 --repo example/target --comment 'Fixed by PR #60\nRollout: N/A: metadata cleanup after verified publication.'", "gh pr close 50 --repo example/target --comment 'Superseded by PR #60\nRollout: N/A: duplicate PR metadata only.'"]:
            command='cd '+str(self.f.repo)+' && '+command
            payload=fixture.craft_payload(tool_name='Bash',cwd=str(self.f.ws/'sessions/one'),tool_input={'command':command})
            for hook in hooks:
                result=subprocess.run(['bash',str(hook)],input=json.dumps(payload),env=self.env,text=True,capture_output=True,timeout=15,cwd=self.f.repo)
                self.assertEqual(result.returncode,0,(hook.name,command,result.stderr))


if __name__ == '__main__':unittest.main()
