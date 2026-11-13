#!/usr/bin/env python3
"""Actual scanner hook/producer controls; selected project code is never executed."""
import hashlib
import builtins
import importlib.util
import json
import os
import select
import signal
import shutil
import sys
import tempfile
from pathlib import Path
import shlex
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('scanner_task_fixture', ROOT/'hooks/_test/task_keyed_gates.py')
f = importlib.util.module_from_spec(spec); spec.loader.exec_module(f)

class ScannerExecution(unittest.TestCase):
    def setUp(self):
        self.f=f.Gates(); self.f.setUp(); self.addCleanup(self.f.tearDown)
        self.repo=self.f.repo
        self.gate=self.f.task('example/app#1211',self.repo,status='reviewing',artifacts=False)
        self.data=self.f.ws/'sessions/one/data';self.data.mkdir(parents=True)
        self.scratch=self.data/'scanner';self.scratch.mkdir(mode=0o700)
        self.message=self.data/'message.txt';self.message.write_text('fix: own fixture #1211\n')
        f.fixture_git(*['-C',str(self.repo),'remote','add','origin','https://github.com/example/app.git'],check=True,capture_output=True,timeout=10)
        value=json.loads((self.gate/'think-gate.json').read_text());value['scope_paths'].append(str(self.data));f.write(self.gate/'think-gate.json',value)

    def test_fixture_git_writes_preserve_the_outer_repository(self):
        outer=self.f.ws/'outer';outer.mkdir()
        clean={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
        def outer_git(*args):
            return subprocess.run(['git','-C',str(outer),*args],env=clean,
                                  check=True,capture_output=True,text=True,timeout=10)
        outer_git('init','-q')
        (outer/'original.txt').write_text('outer content must remain unchanged\n')
        outer_git('add','original.txt')
        outer_git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
                  'commit','-qm','outer fixture')
        def snapshot():
            return {str(p.relative_to(outer)):(p.stat().st_mode & 0o777,
                    hashlib.sha256(p.read_bytes()).hexdigest())
                    for p in outer.rglob('*') if p.is_file()}
        before=snapshot()
        variables={'GIT_DIR':str(outer/'.git'),'GIT_WORK_TREE':str(outer),
                   'GIT_COMMON_DIR':str(outer/'.git'),'GIT_INDEX_FILE':str(outer/'.git/index'),
                   'GIT_OBJECT_DIRECTORY':str(outer/'.git/objects'),
                   'GIT_ALTERNATE_OBJECT_DIRECTORIES':str(outer/'.git/objects')}
        for inherited in ({'GIT_DIR':variables['GIT_DIR']},variables):
            with self.subTest(inherited=sorted(inherited)),patch.dict(os.environ,inherited):
                nested=ScannerExecution()
                try:
                    nested.setUp()
                    self.assertEqual(snapshot(),before,'fixture init/remote modified outer repository')
                    source=nested.repo/'candidate.txt';source.write_text('owned fixture change\n')
                    poisoned={**nested.f.env,**inherited}
                    with patch.dict(os.environ,inherited):
                        f.fixture_git('-C',nested.repo,'remote','set-url','origin',
                                      'https://github.com/example/owned-fixture.git',env=poisoned,check=True,timeout=10)
                        self.assertEqual(snapshot(),before,'fixture remote modified outer config')
                        f.fixture_git('-C',nested.repo,'add','candidate.txt',check=True,timeout=10)
                        self.assertEqual(snapshot(),before,'fixture add modified outer index or objects')
                        f.fixture_git('-C',nested.repo,'-c','user.name=Fixture',
                                      '-c','user.email=fixture@example.invalid',
                                      'commit','-qm','owned fixture',env=poisoned,check=True,capture_output=True,timeout=10)
                    location=f.fixture_git('-C',nested.repo,'rev-parse','--show-toplevel',
                                           check=True,capture_output=True,text=True,timeout=10)
                    self.assertEqual(Path(location.stdout.strip()).resolve(),nested.repo.resolve())
                    self.assertEqual(snapshot(),before,'fixture commit modified outer repository')
                finally:
                    nested.doCleanups()
        self.assertEqual(snapshot(),before)

    def command(self,*mode):
        return shlex.join(['python3','-I','-B',str(ROOT/'hooks/lib/scanner-exec.py'),'--repo',str(self.repo),'--think-gate',str(self.gate/'think-gate.json'),'--tmp-root',str(self.scratch),*mode])

    def test_review_task_can_run_required_message_and_staged_modes(self):
        for mode in [('--commit-message-file',str(self.message)),('--staged',),('--working',),('--pr','1805'),('--message','fix: bounded text #1211')]:
            with self.subTest(mode=mode):
                shape=f.r.action(self.command(*mode),str(self.f.ws))
                self.assertFalse(shape.get('error'),shape)
                self.assertFalse(shape['read_only'])
                self.f.assertGate(0,self.command(*mode),cwd=self.f.ws)
        original='bash '+shlex.quote(str(ROOT/'skills/detect-ai-fingerprints/scan.sh'))+' --commit-message-file '+shlex.quote(str(self.message))
        self.f.assertGate(2,original)
        self.f.assertGate(0,'touch '+shlex.quote(str(self.data/'scanner-exec.py')))  # A data filename grants no scanner role.

    def run_scanner(self,*mode,env=None):
        return subprocess.run(shlex.split(self.command(*mode)),env=env or self.f.env,
                              capture_output=True,text=True,timeout=60)

    def test_host_session_spelling_preserves_physical_task_authority(self):
        session=self.f.ws/'sessions/one'
        alias=self.f.ws/'session-directory-alias'
        alias.symlink_to(session.parent,target_is_directory=True)
        for spelling in (str(session)+'/',str(alias/'one'),str(alias/'one')+'/'):
            with self.subTest(session=spelling):
                env={**self.f.env,'CRAFT_SESSION_DIR':spelling}
                self.f.assertGate(0,self.command('--commit-message-file',str(self.message)),env=env)
        foreign=self.f.ws/'sessions/foreign'
        foreign.mkdir()
        alias.unlink();alias.symlink_to(foreign,target_is_directory=True)
        self.f.assertGate(2,self.command('--commit-message-file',str(self.message)),
                          env={**self.f.env,'CRAFT_SESSION_DIR':str(alias)})

    def test_no_task_foreign_session_status_and_paths_are_denied(self):
        path=self.gate/'think-gate.json';original=path.read_text()
        for patch in [dict(status='designing'),dict(sessionId='other'),dict(scope_paths=[str(self.repo/'a')])]:
            with self.subTest(patch=patch):
                value=json.loads(original);value.update(patch);f.write(path,value)
                self.f.assertGate(2,self.command('--staged'))
        path.write_text(original)
        foreign=self.f.ws/'foreign';foreign.mkdir(mode=0o700)
        self.f.assertGate(2,self.command('--staged').replace(str(self.scratch),str(foreign)))
        self.f.assertGate(2,self.command('--commit-message-file',str(self.message)).replace(str(self.message),str(ROOT/'VERSION')))
        path.unlink();self.f.assertGate(2,self.command('--staged'))

    def test_narrow_task_scopes_allow_diagnostics_without_repo_write_authority(self):
        gate=self.gate/'think-gate.json';value=json.loads(gate.read_text())
        logs=self.data/'logs';logs.mkdir(mode=0o700)
        source=self.repo/'sample.py';source.write_text('value = 1\n')
        f.fixture_git(*['-C',str(self.repo),'add','sample.py'],check=True,capture_output=True,timeout=10)
        source.write_text('value = 2\n')
        value['scope_paths']=[str(self.repo/'sample.py'),str(self.scratch),str(self.message),str(logs)]
        f.write(gate,value)
        for mode in [('--staged',),('--working',),('--commit-message-file',str(self.message)),('--message','fix: bounded text #1211')]:
            with self.subTest(mode=mode):
                command=self.command(*mode)+' --log-dir '+shlex.quote(str(logs))
                self.f.assertGate(0,command)
                result=subprocess.run(shlex.split(command),env=self.f.env,capture_output=True,text=True,timeout=60)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(source.read_text(),'value = 2\n')
        self.assertEqual(json.loads(gate.read_text())['scope_paths'],value['scope_paths'])
        self.f.assertGate(2,'CCP_TASK_ID=example/app#other '+self.command('--staged'))
        self.f.assertGate(2,'touch '+shlex.quote(str(self.repo/'outside.py')))
        value['repo_root']=str(self.f.ws);f.write(gate,value)
        self.f.assertGate(2,self.command('--staged'))

    def test_message_scans_accept_a_real_non_git_operational_task(self):
        with tempfile.TemporaryDirectory(prefix='scanner-nongit-') as temporary:
            workspace=Path(temporary).resolve();repo=workspace/'private';repo.mkdir()
            session=workspace/'sessions/one';data=session/'data';data.mkdir(parents=True)
            scratch=data/'scanner';scratch.mkdir(mode=0o700)
            logs=data/'logs';logs.mkdir(mode=0o700)
            message=data/'body.txt';message.write_text('fix: own operational report #1211\n')
            gate=session/'tasks/operational/think-gate.json'
            value={'task_id':'own-operational-report','sessionId':'one','repo_root':str(repo),
                   'scope_paths':[str(message),str(scratch),str(logs)],'status':'reviewing'}
            f.write(gate,value);f.write(session/'session.jsonl',{'id':'one','sdkSessionId':f.SDK_UUID,'sessionStatus':'in_progress'})
            env={**self.f.env,'CRAFT_SESSION_DIR':str(session),'CRAFT_AGENT_WORKSPACE':str(workspace)}
            outside=f.fixture_git(*['-C',str(repo),'rev-parse','--show-toplevel'],env=env,capture_output=True,text=True,timeout=10)
            self.assertNotEqual(outside.returncode,0,'fixture must be outside Git')
            def command(*mode):
                return shlex.join(['python3','-I','-B',str(ROOT/'hooks/lib/scanner-exec.py'),'--repo',str(repo),
                    '--think-gate',str(gate),'--tmp-root',str(scratch),'--log-dir',str(logs),*mode])
            for mode in [('--message','fix: own text #1211'),('--message-file',str(message)),('--commit-message-file',str(message))]:
                self.f.assertGate(0,command(*mode),env=env,cwd=repo)
                result=subprocess.run(shlex.split(command(*mode)),env=env,capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            bad='This is explicit'+'ly useful.'
            message.write_text('fix: own report #1211\n\n'+bad+'\n')
            for mode in [('--message',bad),('--message-file',str(message)),('--commit-message-file',str(message))]:
                inherited={**env,'GIT_DIR':'/foreign/missing','GIT_INDEX_FILE':'/foreign/index'}
                self.f.assertGate(0,command(*mode),env=inherited,cwd=repo)
                result=subprocess.run(shlex.split(command(*mode)),env=inherited,capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,1,result.stdout+result.stderr)
            for mode in [('--staged',),('--working',),('--pr','1805')]:
                self.f.assertGate(2,command(*mode),env=env,cwd=repo)
                result=subprocess.run(shlex.split(command(*mode)),env=env,capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,2,result.stdout+result.stderr)
            foreign=workspace/'foreign';foreign.mkdir(mode=0o700)
            self.f.assertGate(2,command('--message','own').replace(str(logs),str(foreign)),env=env,cwd=repo)
            self.f.assertGate(2,command('--message','own').replace(str(repo),str(foreign)),env=env,cwd=repo)
            self.f.assertGate(2,'CCP_TASK_ID=foreign-report '+command('--message','own'),env=env,cwd=repo)
            self.assertEqual(json.loads(gate.read_text()),value)

    def test_wrong_producer_path_is_a_structured_deny(self):
        command=self.command('--staged').replace(str(ROOT/'hooks/lib/scanner-exec.py'),str(self.data/'scanner-exec.py'))
        shape=f.r.action(command,str(self.f.ws))
        self.assertIn('exact selected installed entry',shape['error'])
        self.assertNotIn('NameError',str(shape));self.assertNotIn('Traceback',str(shape))
        self.f.assertGate(2,command)

    def test_unknown_modes_copies_shell_composition_and_aliases_are_denied(self):
        for suffix in ['--ignore *','--staged --working','--pr 0','--staged; touch /foreign/out']:
            with self.subTest(suffix=suffix):self.f.assertGate(2,self.command('--staged')+' '+suffix)
        self.f.assertGate(2,self.command('--staged').replace('python3 -I -B','env python3 -I -B'))
        copy=self.data/'scanner-exec.py';shutil.copyfile(ROOT/'hooks/lib/scanner-exec.py',copy)
        self.f.assertGate(2,self.command('--staged').replace(str(ROOT/'hooks/lib/scanner-exec.py'),str(copy)))
        alias=self.data/'alias';alias.symlink_to(self.scratch,target_is_directory=True)
        self.f.assertGate(2,self.command('--staged').replace(str(self.scratch),str(alias)))
        alias.unlink();alias.symlink_to(self.message)
        self.f.assertGate(2,self.command('--commit-message-file',str(alias)))

    def test_actual_message_staged_working_and_incomplete_results(self):
        clean=self.run_scanner('--commit-message-file',str(self.message));self.assertEqual(clean.returncode,0,clean.stderr)
        inline=self.run_scanner('--message','fix: text #1211\n\nThis is explicitly useful; touch /foreign/out.')
        self.assertEqual(inline.returncode,1,inline.stdout+inline.stderr)
        self.message.write_text('fix: fixture #1211\n\nThis is explicitly useful.\n')
        findings=self.run_scanner('--message-file',str(self.message));self.assertEqual(findings.returncode,1,findings.stdout+findings.stderr)
        git=lambda *args:f.fixture_git(*['-C',str(self.repo),*args],env=self.f.env,check=True,capture_output=True,text=True,timeout=10)
        git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid')
        source=self.repo/'sample.py';source.write_text('raise RuntimeError("selected code is data")\n')
        git('add','sample.py');before=git('write-tree').stdout.strip()
        for mode in ['--staged','--working']:
            result=self.run_scanner(mode);self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            record=next(line.removeprefix('scanner input identity: ') for line in result.stderr.splitlines() if line.startswith('scanner input identity: '))
            identity=json.loads(record)['selection']
            self.assertEqual(identity['files_sha256']['sample.py'],hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(len(identity['diff_sha256']),64)
            if mode == '--staged':self.assertEqual(identity['tree'],before)
        self.assertEqual(git('write-tree').stdout.strip(),before)
        config=self.repo/'.claude';config.mkdir();(config/'scanner-config.toml').write_text('invalid = [')
        result=self.run_scanner('--working');self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        self.assertIn('incomplete',result.stdout+result.stderr)
        self.assertEqual(list(self.scratch.iterdir()),[])

    def test_missing_selection_identity_is_incomplete_even_after_child_success(self):
        import contextlib,io
        spec=importlib.util.spec_from_file_location('scanner_missing_identity',ROOT/'hooks/lib/scanner-exec.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        original=subprocess.Popen
        for child_exit in (0,1):
            def controlled_child(command,*args,**kwargs):
                if command[0] == '/bin/bash':
                    command=[sys.executable,'-I','-c',f'raise SystemExit({child_exit})']
                return original(command,*args,**kwargs)
            error=io.StringIO()
            with patch.dict(os.environ,self.f.env,clear=True),patch.object(sys,'argv',shlex.split(self.command('--staged'))[3:]),patch.object(module.subprocess,'Popen',side_effect=controlled_child),contextlib.redirect_stderr(error):
                result=module.main()
            self.assertEqual(result,2,error.getvalue())
            self.assertIn('scanner input identity: ',error.getvalue())
            record=next(line.removeprefix('scanner input identity: ') for line in error.getvalue().splitlines() if line.startswith('scanner input identity: '))
            identity=json.loads(record)
            self.assertEqual(identity['child_exit'],child_exit)
            self.assertTrue(identity['selection_incomplete'])
        self.assertEqual(list(self.scratch.iterdir()),[])

    def test_raw_logs_are_complete_private_and_owned_without_shell_redirects(self):
        logs=self.data/'logs';logs.mkdir(mode=0o700)
        command=self.command('--message','fix: text #1211\n\nThis is explicitly useful.')+' --log-dir '+shlex.quote(str(logs))
        self.f.assertGate(0,command)
        result=subprocess.run(shlex.split(command),env=self.f.env,capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,1,result.stdout+result.stderr)
        children=list(logs.iterdir());self.assertEqual(len(children),1)
        self.assertEqual({p.name for p in children[0].iterdir()},{'stdout.log','stderr.log','selection.json'})
        identity=json.loads((children[0]/'selection.json').read_text())
        self.assertEqual(identity['mode'],'message')
        self.assertEqual(identity['child_exit'],1)
        self.assertEqual(len(identity['input_sha256']),64)
        self.assertIn('writing-prose', (children[0]/'stdout.log').read_text())
        self.assertIn('violations:', (children[0]/'stderr.log').read_text())
        for path in children[0].iterdir():self.assertEqual(path.stat().st_mode & 0o777,0o600)
        foreign=self.f.ws/'foreign-logs';foreign.mkdir(mode=0o700)
        self.f.assertGate(2,command.replace(str(logs),str(foreign)))
        self.assertEqual(list(foreign.iterdir()),[])

    def test_private_index_is_explicit_and_default_index_is_preserved(self):
        def git(*args,index_file=None):
            return f.fixture_git(*['-C',str(self.repo),*args],env=self.f.env,index_file=index_file,check=True,capture_output=True,text=True,timeout=10)
        git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid')
        (self.repo/'sample.py').write_text('value = 1\n');git('add','sample.py')
        normal=git('write-tree').stdout.strip()
        index=self.data/'private-index';shutil.copyfile(self.repo/'.git/index',index)
        (self.repo/'note.txt').write_text('This is explicitly useful.\n')
        indexed={**self.f.env,'GIT_INDEX_FILE':str(index)};git('add','note.txt',index_file=index)
        selected=git('write-tree',index_file=index).stdout.strip();self.assertNotEqual(normal,selected)
        command=self.command('--staged')+' --index-file '+shlex.quote(str(index))
        self.f.assertGate(0,command)
        result=subprocess.run(shlex.split(command),env=self.f.env,capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,1,result.stdout+result.stderr)
        self.assertEqual(git('write-tree').stdout.strip(),normal)
        self.assertEqual(git('write-tree',index_file=index).stdout.strip(),selected)
        self.f.assertGate(2,self.command('--staged'),env=indexed)
        self.f.assertGate(2,self.command('--working')+' --index-file '+shlex.quote(str(index)))

    def test_incomplete_gate_and_owned_process_timeout_do_not_claim_findings(self):
        path=self.gate/'think-gate.json';original=json.loads(path.read_text())
        for content in ['not json','[]',json.dumps({**original,'status':[]}),json.dumps({**original,'repo_root':True}),json.dumps({**original,'scope_paths':['relative']})]:
            with self.subTest(content=content):
                path.write_text(content)
                result=self.run_scanner('--staged');self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        spec=importlib.util.spec_from_file_location('scanner_adapter_runtime',ROOT/'hooks/lib/scanner-exec.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        process=subprocess.Popen([sys.executable,'-I','-c','import time; time.sleep(30)'],start_new_session=True)
        self.addCleanup(lambda: process.kill() if process.poll() is None else None)
        with self.assertRaises(module.ScannerError):module.wait_scanner(process,budget=0.01,interval=0.05)
        self.assertIsNotNone(process.poll())

    def test_startup_diagnostic_failure_cleans_the_owned_process(self):
        spec=importlib.util.spec_from_file_location('scanner_startup_runtime',ROOT/'hooks/lib/scanner-exec.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        real_popen=subprocess.Popen
        for failure in (OSError('startup stderr unavailable'),KeyboardInterrupt('startup signal')):
            with self.subTest(failure=type(failure).__name__):
                children=[]
                def owned_child(*args,**kwargs):
                    self.assertEqual(args[0][0],'/bin/bash')
                    child=real_popen([sys.executable,'-I','-c','import time; time.sleep(30)'],start_new_session=True)
                    children.append(child)
                    return child
                def diagnostic(*args,**kwargs):
                    if str(args[0]).startswith('scanner owned process group:'):
                        raise failure
                    return builtins.print(*args,**kwargs)
                try:
                    with patch.dict(os.environ,self.f.env,clear=True),patch.object(sys,'argv',shlex.split(self.command('--message','fix: own fixture #1361'))[3:]),patch.object(module.subprocess,'Popen',side_effect=owned_child),patch.object(module,'print',side_effect=diagnostic,create=True):
                        self.assertEqual(module.main(),2)
                    self.assertEqual(len(children),1)
                    self.assertIsNotNone(children[0].poll(),'adapter left its owned child alive after startup failure')
                finally:
                    for child in children:
                        if child.poll() is None:
                            os.killpg(child.pid,signal.SIGKILL)
                        child.wait(timeout=5)

    def test_late_ownership_io_failure_and_symlink_loop_fail_closed(self):
        import task_actions
        payload=f.craft_payload(tool_name='Bash',cwd=str(self.f.ws),tool_input={'command':self.command('--staged')})
        with patch.object(task_actions,'scanner_owned_plan',side_effect=OSError('fixture late I/O failure')):
            result=f.r.resolve_action(str(self.f.ws),payload)
        self.assertIsNone(result['gate']);self.assertIn('Scanner authority denied',result['error'])
        loop=self.data/'loop';loop.symlink_to(loop)
        command=self.command('--staged').replace(str(self.scratch),str(loop))
        self.f.assertGate(2,command)
        result=subprocess.run(shlex.split(command),env=self.f.env,capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,2,result.stdout+result.stderr)

    def test_timeout_escalates_for_an_owned_process_ignoring_term(self):
        spec=importlib.util.spec_from_file_location('scanner_timeout_runtime',ROOT/'hooks/lib/scanner-exec.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        process=subprocess.Popen([sys.executable,'-I','-c','import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); print("ready",flush=True); time.sleep(30)'],start_new_session=True,stdout=subprocess.PIPE)
        self.addCleanup(lambda:process.kill() if process.poll() is None else None)
        ready,_,_=select.select([process.stdout],[],[],10);self.assertTrue(ready)
        self.assertIn(b'ready',os.read(process.stdout.fileno(),100))
        with self.assertRaises(module.ScannerError):module.wait_scanner(process,budget=0.01,interval=0.05)
        self.assertIsNotNone(process.poll())
        process.stdout.close()

    def test_actual_adapter_signal_and_nonrepository_failures_are_incomplete(self):
        invalid=self.data/'not-a-repository';invalid.mkdir();(invalid/'.git').mkdir()
        command=self.command('--staged').replace(str(self.repo),str(invalid))
        result=subprocess.run(shlex.split(command),env=self.f.env,capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        self.f.assertGate(2,command)
        (self.repo/'sample.md').write_text('ordinary source line\n'*300)
        f.fixture_git(*['-C',str(self.repo),'add','sample.md'],env=self.f.env,check=True,capture_output=True,timeout=10)
        self.f.assertGate(0,self.command('--staged'))
        process=subprocess.Popen(shlex.split(self.command('--staged')),env=self.f.env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.addCleanup(lambda:process.kill() if process.poll() is None else None)
        ready,_,_=select.select([process.stderr],[],[],10)
        self.assertTrue(ready,'adapter did not report an owned scanner handle')
        first=os.read(process.stderr.fileno(),4096).decode()
        self.assertIn('scanner owned process group:',first)
        process.terminate()
        output,error=process.communicate(timeout=10)
        self.assertEqual(process.returncode,2,output+first+error)
        self.assertIn('interrupted',error)
        self.assertEqual(list(self.scratch.iterdir()),[])

    def test_handled_signal_cleans_its_owned_process(self):
        program = """import hashlib
import importlib.util,subprocess,signal,threading,os,sys,json
spec=importlib.util.spec_from_file_location('adapter',sys.argv[1]);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
child=subprocess.Popen([sys.executable,'-I','-c','import time; time.sleep(30)'],start_new_session=True)
signal.signal(signal.SIGTERM,module.interrupted)
threading.Timer(0.1,lambda:os.kill(os.getpid(),signal.SIGTERM)).start()
try: module.wait_scanner(child)
except KeyboardInterrupt:
 print(json.dumps({'stopped':child.poll() is not None}));raise SystemExit(2)
"""
        result=subprocess.run([sys.executable,'-I','-c',program,str(ROOT/'hooks/lib/scanner-exec.py')],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        self.assertTrue(json.loads(result.stdout)['stopped'])

    def test_actual_pr_mode_fetches_exact_objects_without_moving_target_refs(self):
        def git(repo,*args,check=True):
            return f.fixture_git(*['-C',str(repo),*args],env=self.f.env,check=check,capture_output=True,text=True,timeout=15)
        git(self.repo,'config','user.name','Fixture');git(self.repo,'config','user.email','fixture@example.invalid')
        (self.repo/'sample.py').write_text('value = 1\n');git(self.repo,'add','sample.py');git(self.repo,'commit','-qm','fixture base')
        base=git(self.repo,'rev-parse','HEAD').stdout.strip()
        remote=self.f.ws/'remote.git';f.fixture_git(*['clone','--bare',str(self.repo),str(remote)],env=self.f.env,check=True,capture_output=True,timeout=15)
        git(self.repo,'remote','set-url','origin',str(remote))
        gate=self.gate/'think-gate.json';value=json.loads(gate.read_text());value['scope_paths']=[str(self.repo/'sample.py'),str(self.scratch),str(self.message),str(remote)];f.write(gate,value)
        author=self.f.ws/'source';f.fixture_git(*['clone',str(remote),str(author)],env=self.f.env,check=True,capture_output=True,timeout=15)
        git(author,'config','user.name','Fixture');git(author,'config','user.email','fixture@example.invalid')
        git(author,'checkout','-qb','review-source');(author/'sample.py').write_text('value = 2\n')
        git(author,'add','sample.py');git(author,'commit','-qm','fixture source');git(author,'push','origin','HEAD')
        head=git(author,'rev-parse','HEAD').stdout.strip()
        self.assertNotEqual(git(self.repo,'cat-file','-e',head,check=False).returncode,0)
        tools=self.data/'tools';tools.mkdir();gh=tools/'gh'
        gh.write_text('#!'+sys.executable+'\nimport json,sys\nassert sys.argv[1:]==["pr","view","1805","--json","baseRefOid,headRefOid"]\nprint('+repr(json.dumps({'baseRefOid':base,'headRefOid':head}))+')\n');gh.chmod(0o700)
        refs=git(self.repo,'for-each-ref','--format=%(refname) %(objectname)').stdout
        self.f.assertGate(0,self.command('--pr','1805'))
        result=self.run_scanner('--pr','1805',env={**self.f.env,'PATH':str(tools)+os.pathsep+self.f.env['PATH']})
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(git(self.repo,'rev-parse','HEAD').stdout.strip(),base)
        self.assertEqual(git(self.repo,'cat-file','-e',head,check=False).returncode,0)
        self.assertEqual(git(self.repo,'status','--porcelain').stdout,'')
        self.assertEqual(git(self.repo,'for-each-ref','--format=%(refname) %(objectname)').stdout,refs)
        self.assertEqual(list(self.scratch.iterdir()),[])

    def test_inherited_git_config_cannot_mask_repository_helper_audit(self):
        marker=self.data/'masked-helper-executed'
        helper=self.data/'masked-helper'
        helper.write_text('#!/bin/sh\ntouch '+shlex.quote(str(marker))+'\n');helper.chmod(0o700)
        f.fixture_git('-C',self.repo,'config','core.sshCommand',str(helper),check=True,timeout=10)
        env={**self.f.env,'GIT_CONFIG':'/dev/null'}
        self.f.assertGate(2,self.command('--pr','1805'),env=env)
        result=self.run_scanner('--pr','1805',env=env)
        self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        self.assertFalse(marker.exists())
        # Pure text scanning does not inspect or use repository Git settings.
        result=self.run_scanner('--message','fix: own text #1361',env=env)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertFalse(marker.exists())

    def test_pr_alternate_refs_helper_is_denied(self):
        marker=self.data/'alternate-refs-helper-executed'
        helper=self.data/'alternate-refs-helper'
        helper.write_text('#!/bin/sh\ntouch '+shlex.quote(str(marker))+'\n');helper.chmod(0o700)
        f.fixture_git('-C',self.repo,'config','core.alternateRefsCommand',str(helper),check=True,timeout=10)
        self.f.assertGate(2,self.command('--pr','1805'))
        result=self.run_scanner('--pr','1805')
        self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        self.assertFalse(marker.exists())

    def test_repository_git_helpers_never_execute_as_scanner_input(self):
        marker=self.data/'repository-code-executed';helper=self.data/'fsmonitor'
        helper.write_text('#!/bin/sh\ntouch '+shlex.quote(str(marker))+'\nprintf "token\\000"\n');helper.chmod(0o700)
        f.fixture_git(*['-C',str(self.repo),'config','core.fsmonitor',str(helper)],check=True,timeout=10)
        result=self.run_scanner('--staged')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertFalse(marker.exists())
        for key in ['core.sshCommand','remote.origin.uploadpack','credential.helper','url.file:///foreign/.insteadOf']:
            with self.subTest(key=key):
                f.fixture_git(*['-C',str(self.repo),'config',key,str(helper)],check=True,timeout=10)
                self.f.assertGate(2,self.command('--pr','1805'))
                result=self.run_scanner('--pr','1805')
                self.assertEqual(result.returncode,2,result.stdout+result.stderr)
                self.assertIn('transport/helper',result.stderr)
                self.assertFalse(marker.exists())
                f.fixture_git(*['-C',str(self.repo),'config','--unset',key],check=True,timeout=10)

    def test_closure_mutation_and_startup_injection(self):
        from scanner_capability import validate_files,parse_arguments,ScannerError,CLOSURE
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve()
            for relative in CLOSURE:
                target=root/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/relative,target)
            target=root/'hooks/lib/scanner-exec.py';target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'hooks/lib/scanner-exec.py',target)
            plan=parse_arguments(shlex.split(self.command('--staged'))[4:])
            validate_files(plan,root/'hooks/lib/scanner-exec.py')
            for relative in CLOSURE:
                target=root/relative;raw=target.read_bytes();target.write_bytes(raw+b'\n# drift\n')
                with self.assertRaises(ScannerError):validate_files(plan,root/'hooks/lib/scanner-exec.py')
                target.write_bytes(raw)
        marker=self.data/'injected';startup=self.data/'startup.sh';startup.write_text('touch '+shlex.quote(str(marker))+'\n')
        result=self.run_scanner('--commit-message-file',str(self.message),env={**self.f.env,'BASH_ENV':str(startup),'ENV':str(startup),'PYTHONPATH':'/foreign'})
        self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertFalse(marker.exists())

if __name__=='__main__': unittest.main()
