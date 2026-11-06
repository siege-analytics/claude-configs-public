#!/usr/bin/env python3
"""Real hook queue decisions with fixed read transport, never a remote mutation."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import task_keyed_gates as fixture

ROOT = Path(__file__).resolve().parents[2]
SHA = '8801a13290e9a8cb72e7a2a92fc4c4e7522f954e'
CLI = 'gh pr merge 1794 --merge --match-head-commit ' + SHA
QUERY = 'mutation($id:ID!,$oid:GitObjectID!){enqueuePullRequest(input:{pullRequestId:$id,expectedHeadOid:$oid}){mergeQueueEntry{position state}}}'
GQL = "gh api graphql -f query='" + QUERY + "' -f id=PR_kwDOO94Kgc8AAAABJOmLuA -f oid=" + SHA


class Queue(unittest.TestCase):
    def setUp(self):
        self.f = fixture.Gates(); self.f.setUp(); self.addCleanup(self.f.tearDown)
        self.install = self.f.ws / 'installed'
        shutil.copytree(ROOT/'hooks', self.install/'hooks')
        self.bin = self.f.ws/'bin'; self.bin.mkdir()
        self.calls = self.f.ws/'calls.jsonl'
        self.mode = self.f.ws/'mode'; self.mode.write_text('queue')
        gh = self.bin/'gh'
        gh.write_text('#!' + sys.executable + '\n' + '''import json,os,sys,time
from pathlib import Path
args=sys.argv[1:]
with open(os.environ['QUEUE_CALLS'],'a') as out: out.write(json.dumps(args)+'\\n')
mode=Path(os.environ['QUEUE_MODE']).read_text()
if mode=='hang': time.sleep(20)
if mode=='fail': sys.exit(1)
if mode=='bad': print('{'); sys.exit(0)
if mode=='huge': print('x'*1100000); sys.exit(0)
if mode=='envrepo' and (os.environ.get('GH_REPO')!='siege-analytics/siege_utilities' or '--repo' in args): sys.exit(98)
if args[:2]==['pr','view']:
 print(json.dumps(dict(id='PR_test',number=1794,url='https://github.com/siege-analytics/siege_utilities/pull/1794',headRefOid=('0'*40 if mode=='stale' else '8801a13290e9a8cb72e7a2a92fc4c4e7522f954e'),baseRefName='develop')))
elif args==['api','--hostname','github.com','repos/siege-analytics/siege_utilities/rules/branches/develop']:
 print(json.dumps([] if mode=='noqueue' else [{'type':'merge_queue'}]))
else: sys.exit(99)
''')
        gh.chmod(0o755)
        self.env = dict(self.f.env, PATH=str(self.bin)+os.pathsep+self.f.env['PATH'], QUEUE_CALLS=str(self.calls), QUEUE_MODE=str(self.mode))
        self.audit = self.f.ws/'sessions/one/data/merge-queue-decisions.jsonl'

    def hook(self, command, code=0, cwd=None):
        payload=fixture.craft_payload(tool_name='Bash',cwd=str(cwd or self.f.repo),tool_input={'command':command})
        run=subprocess.run(['bash',str(self.install/'hooks/bash/universal-mutation-gate.sh')],input=json.dumps(payload),env=self.env,text=True,capture_output=True,timeout=12)
        self.assertEqual(run.returncode,code,(command,run.stdout,run.stderr))
        return run

    def test_cli_no_gate_requires_queue_and_audits(self):
        self.hook(CLI)
        self.hook(CLI+' --repo siege-analytics/siege_utilities')
        self.hook(CLI+' -R siege-analytics/siege_utilities')
        rows=[json.loads(x) for x in self.audit.read_text().splitlines()]
        self.assertEqual(len(rows),3)
        self.assertTrue(all(x['decision']=='allow-enqueue' and x['session']=='one' and x['head']==SHA and x['pr']==1794 and x['remote_success'] is False for x in rows))
        calls=[json.loads(x) for x in self.calls.read_text().splitlines()]
        self.assertEqual(len(calls),6)
        self.assertTrue(all(x[:2]==['pr','view'] or '/rules/branches/' in x[-1] for x in calls))

    def test_exact_graphql_variables_and_literal_no_network(self):
        self.hook(GQL)
        literal='mutation{enqueuePullRequest(input:{pullRequestId:"PR_test",expectedHeadOid:"'+SHA+'"}){mergeQueueEntry{position state}}}'
        self.hook("gh api graphql -f query='"+literal+"'")
        self.assertFalse(self.calls.exists())
        rows=[json.loads(x) for x in self.audit.read_text().splitlines()]
        self.assertEqual([x['node'] for x in rows],['PR_kwDOO94Kgc8AAAABJOmLuA','PR_test'])
        self.assertTrue(all(x['remote_success'] is False for x in rows))

    def test_repository_environment_routes_cli_without_a_local_repository(self):
        with tempfile.TemporaryDirectory(prefix='queue-cwd-') as folder:
            outside = Path(folder).resolve()
            probe = subprocess.run(['git', '-C', str(outside), 'rev-parse', '--is-inside-work-tree'],
                                   capture_output=True, text=True, timeout=10)
            self.assertNotEqual(probe.returncode, 0)
            self.env['GH_REPO'] = 'siege-analytics/siege_utilities'
            self.mode.write_text('envrepo')
            self.hook(CLI, cwd=outside)
            self.hook(GQL, cwd=outside)
            calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
            self.assertEqual(len(calls), 2)  # Only CLI proof; GraphQL has no lookup.
            self.assertNotIn('--repo', calls[0])
            self.assertEqual(calls[1][-1], 'repos/siege-analytics/siege_utilities/rules/branches/develop')
            rows = [json.loads(line) for line in self.audit.read_text().splitlines()]
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]['repository'], 'siege-analytics/siege_utilities')
            self.assertEqual(rows[1]['node'], 'PR_kwDOO94Kgc8AAAABJOmLuA')
            self.env['GH_HOST'] = 'github.example'
            self.hook(GQL, 2, cwd=outside)
            self.assertEqual(len(self.audit.read_text().splitlines()), 2)

    def test_bad_merge_flags_and_composition_never_borrow_local_gate(self):
        self.f.task('local-review',self.f.repo)
        bad=[CLI+' --admin',CLI+' --auto',CLI.replace(SHA,'8801'),CLI.replace(SHA,'z'*40),CLI+' --delete-branch',CLI+' --merge',CLI+' --squash',CLI+' --repo other/repo --repo other/repo',CLI+' && rm -rf x','timeout 5 '+CLI,'bash -c '+repr(CLI),CLI+' > output',CLI+' | cat','env '+CLI,'gh api -X PUT repos/siege-analytics/siege_utilities/pulls/1794/merge']
        for command in bad:
            with self.subTest(command=command): self.hook(command,2)
        self.assertFalse(self.audit.exists())

    def test_unpinned_merge_is_scoped_not_queue_permission(self):
        command = 'gh pr merge 1794 --merge'
        self.hook(command, 2)  # No task gate: no universal allowance.
        classified = subprocess.run([sys.executable, str(self.install/'hooks/lib/github-merge-queue.py'), '--classify', command],
                                    env=self.env, capture_output=True, timeout=5)
        self.assertNotEqual(classified.returncode, 0)
        self.assertFalse(self.audit.exists())
        self.f.task('own-local', self.f.repo)
        self.hook(command)
        self.assertFalse(self.audit.exists())
        self.hook(CLI.replace('--match-head-commit ', '--match-head-commit='), 2)

    def test_bad_graphql_forms(self):
        bad=[GQL.replace('enqueuePullRequest','dequeuePullRequest'),GQL.replace(',expectedHeadOid:$oid',''),GQL.replace(SHA,'abc'),GQL+' -f oid='+SHA,GQL.replace('position state','position state}} deleteIssue(input:{id:$id}){clientMutationId'),GQL+' && touch x',GQL.replace('-f query=', '--input '),GQL.replace('graphql','/graphql'),GQL.replace("'mutation(", '"mutation(').replace("}}}'", '}}}"')]
        for command in bad:
            with self.subTest(command=command): self.hook(command,2)
        self.assertFalse(self.audit.exists())

    def test_literal_tokens_cannot_join_or_change_quoted_values(self):
        literal='mutation{enqueuePullRequest(input:{pullRequestId:"PR_test",expectedHeadOid:"'+SHA+'"}){mergeQueueEntry{position state}}}'
        for query in [literal.replace('PR_test','PR test'),literal.replace(SHA,SHA[:20]+' '+SHA[20:]),literal.replace('position state','positionstate'),literal.replace('enqueuePullRequest','enqueue PullRequest')]:
            command="gh api graphql -f query='"+query+"'"
            with self.subTest(query=query):
                self.hook(command,2)
                classified=subprocess.run([sys.executable,str(self.install/'hooks/lib/github-merge-queue.py'),'--classify',command],env=self.env,capture_output=True,timeout=5)
                self.assertNotEqual(classified.returncode,0)
        self.assertFalse(self.audit.exists())

    def test_entire_local_publication_stack_ignores_unrelated_head_once(self):
        subprocess.run(['git','-C',str(self.f.repo),'remote','add','origin','https://github.com/siege-analytics/siege_utilities.git'],check=True,timeout=5)
        subprocess.run(['git','-C',str(self.f.repo),'-c','core.hooksPath=/dev/null','-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','--allow-empty','-qm','Unrelated local fixture HEAD'],check=True,timeout=5)
        (self.f.repo/'.gitignore').write_text('tests/\n')
        tests=self.f.repo/'tests';tests.mkdir();(tests/'test_ignored.py').write_text('assert True\n')
        guards=['git/self-review.sh','git/test-guard.sh','git/test-tracking-guard.sh','git/decomposition-guard.sh','git/fix-shape-guard.sh','git/detect-ai-fingerprints.sh','git/survey-context.sh','bash/destructive-guard.sh']
        for command in [CLI+' --repo siege-analytics/siege_utilities',GQL]:
            self.hook(command)
            payload=fixture.craft_payload(tool_name='Bash',cwd=str(self.f.repo),tool_input={'command':command})
            for guard in guards:
                run=subprocess.run(['bash',str(self.install/'hooks'/guard)],input=json.dumps(payload),env=self.env,cwd=self.f.repo,text=True,capture_output=True,timeout=12)
                self.assertEqual(run.returncode,0,(guard,run.stdout,run.stderr))
        self.assertEqual(len(self.audit.read_text().splitlines()),2)
        # Ordinary local publication still checks the unrelated local state.
        for guard in ['git/self-review.sh','git/test-tracking-guard.sh']:
            payload=fixture.craft_payload(tool_name='Bash',cwd=str(self.f.repo),tool_input={'command':'git push'})
            run=subprocess.run(['bash',str(self.install/'hooks'/guard)],input=json.dumps(payload),env=self.env,cwd=self.f.repo,text=True,capture_output=True,timeout=12)
            self.assertEqual(run.returncode,2,(guard,run.stdout,run.stderr))

    def test_cli_proof_failure_modes(self):
        for mode in ['noqueue','stale','fail','bad','huge','hang']:
            self.mode.write_text(mode)
            with self.subTest(mode=mode): self.hook(CLI,2)
        self.assertFalse(self.audit.exists())

    def test_audit_failure_and_binding_fail_closed(self):
        self.audit.parent.mkdir()
        elsewhere=self.f.ws/'outside'; elsewhere.write_text('original')
        self.audit.symlink_to(elsewhere)
        self.hook(GQL,2)
        self.assertEqual(elsewhere.read_text(),'original')
        self.audit.unlink(); os.link(elsewhere,self.audit)
        self.hook(GQL,2)
        self.assertEqual(elsewhere.read_text(),'original')
        self.audit.unlink()
        self.env['CRAFT_SESSION_DIR']='{{SESSION_PATH}}'
        self.hook(GQL,2)
        self.assertFalse(self.audit.exists())

    def test_inert_examples_and_script_are_not_queue_carveout(self):
        self.hook('printf %s '+repr(CLI))
        script=self.f.repo/'queue.sh'; script.write_text('#!/bin/sh\n'+CLI+'\n'); script.chmod(0o755)
        self.hook(str(script),2)
        self.assertFalse(self.audit.exists())


if __name__=='__main__': unittest.main()
