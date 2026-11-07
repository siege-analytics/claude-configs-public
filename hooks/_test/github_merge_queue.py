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
from unittest import mock
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
head='0'*40 if mode=='stale' else '8801a13290e9a8cb72e7a2a92fc4c4e7522f954e'
base='main' if mode=='mainbase' else 'develop'
if args[:2]==['pr','view']:
 print(json.dumps(dict(id='PR_test',number=1794,url='https://github.com/siege-analytics/siege_utilities/pull/1794',headRefOid=head,baseRefName=base)))
elif args[:4]==['api','--hostname','github.com','graphql'] and len(args)==8 and args[4]==args[6]=='-f' and args[7].startswith('id='):
 node=args[7][3:] if mode!='othernode' else 'PR_other'
 print(json.dumps(dict(data=dict(node=dict(id=node,number=1794,baseRefName=base,headRefOid=head,repository=dict(nameWithOwner='siege-analytics/siege_utilities'))))))
elif args[:3]==['api','--hostname','github.com'] and args[3] in ('repos/siege-analytics/siege_utilities/rules/branches/develop','repos/siege-analytics/siege_utilities/rules/branches/main'):
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

    def unavailable_helper_controls(self, content):
        helper = self.install/'hooks/lib/github-merge-queue.py'
        if content is None:
            helper.unlink()
        else:
            helper.write_text(content)
        self.hook('pwd')
        self.hook('gh issue view 1794')
        self.hook('gh issue edit 1794 --title "Existing review notes"')
        command = 'touch ' + str(self.f.repo/'local-edit.txt')
        self.hook(command, 2)  # Missing helper cannot create a local allowance.
        write_payload = fixture.craft_payload(tool_name='Write', cwd=str(self.f.repo),
                                             tool_input={'file_path':str(self.f.repo/'write.txt'),
                                                         'content':'fixture', 'command':None})
        def write_check(expected):
            result = subprocess.run(['bash',str(self.install/'hooks/bash/universal-mutation-gate.sh')],
                                    input=json.dumps(write_payload), env=self.env, text=True,
                                    capture_output=True, timeout=12)
            self.assertEqual(result.returncode, expected, result.stderr)
        write_check(2)
        self.f.task('own-local', self.f.repo)
        self.hook(command)
        write_check(0)
        for candidate, label in ((CLI, 'Pinned merge denied:'), (GQL, 'Queue enqueue denied:')):
            result = self.hook(candidate, 2)
            self.assertIn(label, result.stderr)
        self.assertFalse(self.calls.exists())
        self.assertFalse(self.audit.exists())

    def test_missing_helper_does_not_affect_ordinary_actions(self):
        self.unavailable_helper_controls(None)

    def test_malformed_helper_does_not_affect_ordinary_actions(self):
        self.unavailable_helper_controls('def broken(:\n')

    def test_helper_import_failure_does_not_affect_ordinary_actions(self):
        self.unavailable_helper_controls('raise ImportError("fixture missing queue dependency")\n')

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

    def test_exact_graphql_variables_and_literal_use_one_node_lookup(self):
        self.hook(GQL)
        literal='mutation{enqueuePullRequest(input:{pullRequestId:"PR_test",expectedHeadOid:"'+SHA+'"}){mergeQueueEntry{position state}}}'
        self.hook("gh api graphql -f query='"+literal+"'")
        calls=[json.loads(x) for x in self.calls.read_text().splitlines()]
        self.assertEqual([x[:4]+x[-1:] for x in calls],[['api','--hostname','github.com','graphql','id=PR_kwDOO94Kgc8AAAABJOmLuA'],
                                                         ['api','--hostname','github.com','graphql','id=PR_test']])
        rows=[json.loads(x) for x in self.audit.read_text().splitlines()]
        self.assertEqual([x['node'] for x in rows],['PR_kwDOO94Kgc8AAAABJOmLuA','PR_test'])
        for row in rows:  # The audit names the real target, not only a node string.
            self.assertEqual((row['repository'],row['pr'],row['base'],row['form']),('siege-analytics/siege_utilities',1794,'develop','graphql'))
        self.assertTrue(all(x['remote_success'] is False for x in rows))

    def test_shell_escapes_cannot_change_validated_literal_bytes(self):
        node = 'PR_kwDO\\u004f94Kgc8AAAABJOmLuA'
        double = 'gh api graphql -f query="mutation{enqueuePullRequest(input:{pullRequestId:\\"' + node + '\\",expectedHeadOid:\\"' + SHA + '\\"}){mergeQueueEntry{position state}}}"'
        mixed = "gh api graphql -f query='mutation{enqueuePullRequest(input:{pullRequestId:\"PR_kwDO'\"\\u004f\"'94Kgc8AAAABJOmLuA\",expectedHeadOid:\"" + SHA + "\"}){mergeQueueEntry{position state}}}'"
        for command in (double, mixed):
            with self.subTest(command=command):
                self.hook(command, 2)
        self.assertFalse(self.audit.exists())

    def helper(self):
        spec = importlib.util.spec_from_file_location('queue_policy', self.install/'hooks/lib/github-merge-queue.py')
        sys.path.insert(0, str(self.install/'hooks/lib')); self.addCleanup(sys.path.remove, str(self.install/'hooks/lib'))
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    def test_unreadable_proof_is_typed_and_only_cli_falls_back(self):
        queue = self.helper()
        cli = queue.parse(CLI); graphql = queue.parse(GQL)
        with mock.patch.dict(os.environ, self.env, clear=True):
            for mode in ['fail', 'bad']:
                self.mode.write_text(mode)
                with self.subTest(mode=mode):
                    with self.assertRaises(queue.ProofUnavailable):
                        queue._verify(cli, str(self.f.repo))
                    self.assertIsNone(queue.verify(cli, str(self.f.repo)))
                    with self.assertRaises(ValueError):
                        queue.verify(graphql, str(self.f.repo))
            self.mode.write_text('stale')  # A readable mismatch is not an unreadable proof.
            with self.assertRaises(ValueError) as caught:
                queue.verify(cli, str(self.f.repo))
            self.assertNotIsInstance(caught.exception, queue.ProofUnavailable)

    def test_only_policy_bases_are_exempt(self):
        policy = self.helper()
        self.assertEqual(policy.QUEUE_EXEMPT_BASES, ('develop',))
        self.mode.write_text('mainbase')  # A queued release base, like siege_utilities main.
        for command in (CLI, GQL):
            with self.subTest(no_gate=command): self.hook(command, 2)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertFalse(any('/rules/branches/' in call[-1] for call in calls))  # Base policy decides first.
        self.f.task('own-local', self.f.repo)
        self.hook(CLI)  # Not exempt is not hard-denied: the ordinary task path applies.
        predicate = subprocess.run([sys.executable, str(self.install/'hooks/lib/github-merge-queue.py'),
                                    '--queue-required', CLI, str(self.f.repo)], env=self.env, capture_output=True, timeout=10)
        self.assertNotEqual(predicate.returncode, 0)
        self.hook(GQL, 2)  # The ordinary path does not model GraphQL.
        self.assertFalse(self.audit.exists())

    def test_graphql_lookup_failure_or_mismatch_is_not_exempt(self):
        self.f.task('own-local', self.f.repo)
        for mode in ['fail', 'bad', 'huge', 'hang', 'stale', 'othernode']:
            self.mode.write_text(mode)
            with self.subTest(mode=mode): self.hook(GQL, 2)
        self.assertFalse(self.audit.exists())

    def test_cli_proof_read_failure_keeps_task_scope_without_exemption(self):
        for mode in ['fail', 'bad', 'huge', 'hang']:
            self.mode.write_text(mode)
            with self.subTest(no_gate=mode): self.hook(CLI, 2)
        self.f.task('own-local', self.f.repo)
        for mode in ['fail', 'bad', 'huge', 'hang']:
            self.mode.write_text(mode)
            with self.subTest(owned=mode): self.hook(CLI)
        self.mode.write_text('fail')
        predicate = subprocess.run([sys.executable, str(self.install/'hooks/lib/github-merge-queue.py'),
                                    '--queue-required', CLI, str(self.f.repo)], env=self.env, capture_output=True, timeout=10)
        self.assertNotEqual(predicate.returncode, 0)  # Guards still run every local check.
        self.mode.write_text('queue')
        self.env['GH_HOST'] = 'github.example'
        self.hook(CLI)
        self.hook(GQL, 2)
        self.mode.write_text('stale')
        del self.env['GH_HOST']
        result = self.hook(CLI, 2)  # A real mismatch still denies, even with a task.
        self.assertIn('Pinned merge denied:', result.stderr)
        self.assertFalse(self.audit.exists())

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
            self.assertEqual(len(calls), 3)  # CLI identity and rules; one GraphQL node lookup.
            self.assertNotIn('--repo', calls[0])
            self.assertEqual(calls[1][-1], 'repos/siege-analytics/siege_utilities/rules/branches/develop')
            self.assertEqual(calls[2][-1], 'id=PR_kwDOO94Kgc8AAAABJOmLuA')
            rows = [json.loads(line) for line in self.audit.read_text().splitlines()]
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]['repository'], 'siege-analytics/siege_utilities')
            self.assertEqual(rows[1]['node'], 'PR_kwDOO94Kgc8AAAABJOmLuA')
            self.assertEqual(rows[1]['repository'], 'siege-analytics/siege_utilities')
            self.env['GH_HOST'] = 'github.example'
            self.hook(GQL, 2, cwd=outside)
            self.assertEqual(len(self.audit.read_text().splitlines()), 2)

    def test_bad_merge_flags_and_composition_never_borrow_local_gate(self):
        self.f.task('local-review',self.f.repo)
        bad=[CLI+' --admin',CLI.replace(SHA,'8801'),CLI.replace(SHA,'z'*40),'timeout 5 '+CLI,'bash -c '+repr(CLI),'env '+CLI,'gh api -X PUT repos/siege-analytics/siege_utilities/pulls/1794/merge']
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
        self.hook(CLI.replace('--match-head-commit ', '--match-head-commit='))
        self.assertFalse(self.audit.exists())

    def test_nonqueue_pinned_merges_retain_task_scope_and_local_guards(self):
        subprocess.run(['git','-C',str(self.f.repo),'remote','add','origin','https://github.com/siege-analytics/siege_utilities.git'],check=True,timeout=5)
        subprocess.run(['git','-C',str(self.f.repo),'-c','core.hooksPath=/dev/null','-c','user.name=Fixture',
                        '-c','user.email=fixture@example.invalid','commit','--allow-empty','-qm','Unreviewed fixture HEAD'],check=True,timeout=5)
        (self.f.repo/'.gitignore').write_text('tests/\n')
        tests = self.f.repo/'tests'; tests.mkdir(); (tests/'test_ignored.py').write_text('assert True\n')
        self.mode.write_text('noqueue')
        ordinary = [CLI, CLI+' --auto', CLI.replace(' --merge',''), CLI+' --merge',
                    CLI+' --repo siege-analytics/siege_utilities --repo siege-analytics/siege_utilities', CLI.replace('--merge','--squash'), CLI.replace('--merge','--rebase'),
                    CLI+' --delete-branch', CLI+' --body "--admin"',
                    CLI.replace('--match-head-commit ', '--match-head-commit='),
                    CLI+' && touch '+str(self.f.repo/'owned.txt'), CLI+' > '+str(self.f.repo/'output.txt')]
        for command in ordinary:
            with self.subTest(no_gate=command): self.hook(command,2)
        self.f.task('own-local',self.f.repo)
        for command in ordinary:
            with self.subTest(owned=command):
                self.hook(command)
                predicate = subprocess.run([sys.executable,str(self.install/'hooks/lib/github-merge-queue.py'),
                                            '--queue-required',command,str(self.f.repo)],env=self.env,
                                           capture_output=True,timeout=5)
                self.assertNotEqual(predicate.returncode,0)
                for guard in ['git/self-review.sh','git/test-tracking-guard.sh']:
                    payload = fixture.craft_payload(tool_name='Bash',cwd=str(self.f.repo),tool_input={'command':command})
                    run = subprocess.run(['bash',str(self.install/'hooks'/guard)],input=json.dumps(payload),
                                         env=self.env,cwd=self.f.repo,text=True,capture_output=True,timeout=12)
                    self.assertEqual(run.returncode,2,(guard,command,run.stdout,run.stderr))
        self.hook(CLI+' && touch '+str(self.f.ws/'outside-owned-task.txt'),2)
        self.hook(CLI.replace(SHA,'bad'),2)
        self.hook(CLI+' --admin',2)
        self.assertFalse(self.audit.exists())

    def test_composed_admin_merge_cannot_borrow_task_scope(self):
        self.f.task('own-local',self.f.repo)
        for command in ['gh pr merge 1 --merge && gh pr merge 2 --admin',
                        CLI+' > '+str(self.f.repo/'log')+' && gh pr merge 2 --admin',
                        CLI+' && gh pr merge 2 > '+str(self.f.repo/'log')+' --admin']:
            with self.subTest(command=command):
                result = self.hook(command,2)
                self.assertIn('admin bypass is not supported',result.stderr)
                predicate = subprocess.run([sys.executable,str(self.install/'hooks/lib/github-merge-queue.py'),
                                            '--queue-required',command,str(self.f.repo)],env=self.env,
                                           capture_output=True,timeout=5)
                self.assertNotEqual(predicate.returncode,0)
        self.assertFalse(self.calls.exists())
        self.assertFalse(self.audit.exists())

    def test_admin_words_in_body_and_echo_remain_ordinary_data(self):
        self.mode.write_text('noqueue')
        self.f.task('own-local',self.f.repo)
        for command in [CLI+' --body "--admin"', CLI+' && echo --admin',
                        CLI+' && printf %s "gh pr merge 2 --admin"']:
            with self.subTest(command=command):
                self.hook(command)
                predicate = subprocess.run([sys.executable,str(self.install/'hooks/lib/github-merge-queue.py'),
                                            '--queue-required',command,str(self.f.repo)],env=self.env,
                                           capture_output=True,timeout=5)
                self.assertNotEqual(predicate.returncode,0)
        self.assertFalse(self.audit.exists())

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
        self.f.task('broad-local', self.f.repo)
        count = lambda: len(self.calls.read_text().splitlines()) if self.calls.exists() else 0
        reads = {}
        for command in [CLI+' --repo siege-analytics/siege_utilities',GQL]:
            before = count()
            self.hook(command)
            reads[(command, 'umg')] = count() - before
            payload=fixture.craft_payload(tool_name='Bash',cwd=str(self.f.repo),tool_input={'command':command})
            for guard in guards:
                before = count()
                run=subprocess.run(['bash',str(self.install/'hooks'/guard)],input=json.dumps(payload),env=self.env,cwd=self.f.repo,text=True,capture_output=True,timeout=12)
                self.assertEqual(run.returncode,0,(guard,run.stdout,run.stderr))
                reads[(command, guard)] = count() - before
        self.assertEqual(len(self.audit.read_text().splitlines()),2)
        # Every consulted proof is fresh: two CLI reads, or one GraphQL node read.
        # A guard that returns before consulting the helper for `gh api` reads nothing.
        cli = CLI+' --repo siege-analytics/siege_utilities'
        self.assertEqual({key: value for key, value in reads.items() if key[0] == cli},
                         {(cli, name): 2 for name in ['umg', *guards]})
        self.assertEqual(reads[(GQL, 'umg')], 1)
        self.assertTrue(all(reads[(GQL, guard)] in (0, 1) for guard in guards), reads)
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
