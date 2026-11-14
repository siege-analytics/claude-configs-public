"""Actual fresh Git repositories must be creatable under their own task (#1240)."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import task_keyed_gates as fixture


class GitBootstrap(unittest.TestCase):
    def setUp(self):
        # Git hooks can export repository/index targeting. Isolate before Gates
        # itself runs Git, and restore the caller's environment after tearDown.
        inherited_git = {'GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_INDEX_FILE',
                         'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES',
                         'GIT_PREFIX', 'GIT_CONFIG', 'GIT_CONFIG_PARAMETERS',
                         'GIT_CONFIG_COUNT', 'GIT_TEMPLATE_DIR', 'GIT_SSH',
                         'GIT_SSH_COMMAND', 'GIT_EXEC_PATH'}
        isolated = patch.dict(os.environ, {k: v for k, v in os.environ.items()
                                          if k not in inherited_git}, clear=True)
        isolated.start()
        self.addCleanup(isolated.stop)
        self.f = fixture.Gates()
        original = tempfile.TemporaryDirectory
        with patch.object(fixture.tempfile, 'TemporaryDirectory', side_effect=lambda **kw: original(prefix=kw['prefix'], dir=os.path.realpath(tempfile.gettempdir()))):
            self.f.setUp()
        self.ws = self.f.ws
        self.f.env.update(GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_NOSYSTEM='1')
        os.environ.update(GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_NOSYSTEM='1')
        self.source = self.ws / 'source'
        subprocess.run(['git', 'init', '-q', str(self.source)], check=True, timeout=30)
        (self.source / 'note.txt').write_text('preserve me\n')
        subprocess.run(['git', '-C', str(self.source), 'add', 'note.txt'], check=True, timeout=30)
        subprocess.run(['git', '-C', str(self.source), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture'], check=True, timeout=30)
        self.bundle = self.ws / 'saved.bundle'
        subprocess.run(['git', '-C', str(self.source), 'bundle', 'create', str(self.bundle), '--all'], check=True, timeout=30)

    def tearDown(self):
        self.f.tearDown()

    def task(self, destination, *, artifacts=True, sid='one', status='implementing'):
        gate = self.f.task('bootstrap1240', destination, artifacts=artifacts, sid=sid, status=status)
        for p in gate.glob('*.json'):
            data = json.loads(p.read_text()); data['repo_root'] = str(destination)
            fixture.write(p, data)
        return gate

    def shape(self, args, cwd=None):
        return fixture.r.action(shlex.join(args), str(cwd or self.ws))

    def run_allowed(self, args, destination, cwd=None):
        self.task(destination)
        command = shlex.join(args)
        result = self.f.assertGate(0, command, cwd=cwd or self.ws)
        subprocess.run(args, cwd=cwd or self.ws, env=self.f.env, check=True, capture_output=True, timeout=15)
        return result

    def test_real_init_current_explicit_subdirectory_and_git_C(self):
        for index, form in enumerate(('current', 'subdir', 'git-C', 'bare')):
            with self.subTest(form=form):
                target = self.ws / ('init-' + str(index))
                target.mkdir()
                if form == 'current': args, cwd = ['git', 'init', '-q', '.'], target
                elif form == 'git-C': args, cwd = ['git', '-C', str(target), 'init', '-q'], self.ws
                elif form == 'bare': args, cwd = ['git', 'init', '--bare', '-q', str(target)], self.ws
                else:
                    target.rmdir(); args, cwd = ['git', 'init', '-q', '-b', 'develop', str(target)], self.ws
                self.assertEqual(self.shape(args, cwd)['paths'], [str(target)])
                self.run_allowed(args, target, cwd)
                actual = subprocess.check_output(['git', '-C', str(target), 'rev-parse', '--absolute-git-dir'], text=True, timeout=30).strip()
                self.assertEqual(actual, str(target if form == 'bare' else target / '.git'))
                # This test's task must not lend another bootstrap scope.
                for p in (self.ws / 'sessions/one/tasks').glob('*/think-gate.json'):
                    data=json.loads(p.read_text());data['status']='disposed';fixture.write(p,data)

    def test_real_mirror_bundle_and_local_clone_source_is_not_write_target(self):
        before = self.bundle.read_bytes()
        for index, source in enumerate((self.bundle, self.source)):
            with self.subTest(source=source):
                target = self.ws / ('mirror-' + str(index))
                args = ['git', 'clone', '--mirror', *(['--no-local'] if source.is_dir() else []), str(source), str(target)]
                self.assertEqual(self.shape(args)['paths'], [str(target)])
                self.run_allowed(args, target)
                refs = subprocess.check_output(['git', '-C', str(target), 'show-ref'], text=True, timeout=30)
                self.assertIn('refs/heads/', refs)
                if source.is_dir():
                    originals=[p for p in (source/'.git/objects').rglob('*') if p.is_file()]
                    copies=[p for p in (target/'objects').rglob('*') if p.is_file()]
                    self.assertTrue(originals);self.assertTrue(copies)
                    for obj in originals:
                        self.assertEqual(obj.stat().st_nlink,1)
                    source_inodes={(p.stat().st_dev,p.stat().st_ino) for p in originals}
                    for copied in copies:
                        self.assertNotIn((copied.stat().st_dev,copied.stat().st_ino),source_inodes)
                        self.assertEqual(copied.stat().st_nlink,1)
                    self.assertFalse((target/'objects/info/alternates').exists())
                gate=self.ws/'sessions/one/tasks'/fixture.r.task_slug('bootstrap1240')/'think-gate.json'
                data=json.loads(gate.read_text());data['status']='disposed';fixture.write(gate,data)
        self.assertEqual(self.bundle.read_bytes(), before)
        self.assertEqual((self.source/'note.txt').read_text(), 'preserve me\n')

    def test_local_source_with_alternates_becomes_independent_under_no_local(self):
        borrowed=self.ws/'borrowed'
        subprocess.run(['git','clone','--shared','--no-checkout',str(self.source),str(borrowed)],check=True,capture_output=True, timeout=30)
        self.assertTrue((borrowed/'.git/objects/info/alternates').is_file())
        target=self.ws/'independent'
        self.run_allowed(['git','clone','--mirror','--no-local',str(borrowed),str(target)],target)
        self.assertFalse((target/'objects/info/alternates').exists())
        original_inodes={(p.stat().st_dev,p.stat().st_ino) for base in (self.source/'.git/objects',borrowed/'.git/objects') for p in base.rglob('*') if p.is_file()}
        for p in (target/'objects').rglob('*'):
            if p.is_file():
                self.assertNotIn((p.stat().st_dev,p.stat().st_ino),original_inodes)
                self.assertEqual(p.stat().st_nlink,1)
        self.source.rename(self.ws/'source-now-unavailable')
        subprocess.run(['git','-C',str(target),'fsck','--full'],check=True,capture_output=True, timeout=30)
        self.assertEqual(subprocess.check_output(['git','-C',str(target),'show','HEAD:note.txt'],text=True, timeout=30),'preserve me\n')

    def test_missing_gate_foreign_task_wrong_scope_and_nonimplementing_deny(self):
        target = self.ws / 'denied'
        command = shlex.join(['git', 'init', str(target)])
        self.f.assertGate(2, command, cwd=self.ws)
        self.task(target, sid='two'); self.f.assertGate(2, command, cwd=self.ws)
        self.task(target, status='designing'); self.f.assertGate(2, command, cwd=self.ws)
        self.task(self.ws/'other'); self.f.assertGate(2, command, cwd=self.ws)
        self.assertFalse(target.exists())

    def test_fresh_repo_preserves_C_risk_but_needs_no_preedit_artifacts(self):
        target=self.ws/'risk'
        gate=self.task(target, artifacts=False)
        data=json.loads((gate/'think-gate.json').read_text());data['tier']='A';fixture.write(gate/'think-gate.json',data)
        command=shlex.join(['git','init',str(target)])
        tier=fixture.r.task_tier(data,[str(target)],command,str(self.ws))
        self.assertEqual(tier['floor'],'C');self.assertEqual(tier['effective'],'C')
        self.f.assertGate(0,command,cwd=self.ws)
        self.f.assertGate(2,shlex.join(['git','init',str(self.ws/'outside-task')]),cwd=self.ws)
        self.assertFalse(target.exists())

    def test_unknown_helpers_metadata_options_and_transports_deny(self):
        target=self.ws/'escape'; self.task(target)
        forms=[['git','clone',str(self.source),str(target)],
               ['git','clone','--no-hardlinks',str(self.source),str(target)],
               ['git','clone','--no-local','--local',str(self.source),str(target)],
               ['git','clone','--shared',str(self.source),str(target)],
               ['git','init','--separate-git-dir',str(self.ws/'elsewhere'),str(target)],
               ['git','init','--template='+str(self.source),str(target)],
               ['git','-c','core.hooksPath='+str(self.source),'init',str(target)],
               ['git','clone',str(self.bundle)],
               ['git','clone','--reference',str(self.source),str(self.bundle),str(target)],
               ['git','clone','--upload-pack=evil',str(self.bundle),str(target)],
               ['git','clone','--config=core.hooksPath=/outside',str(self.bundle),str(target)],
               ['git','clone','ext::sh bad',str(target)],
               ['git','clone','file:///outside/repo',str(target)],
               ['git','clone','https://example.invalid/repo','--mystery',str(target)],
               ['git','init',str(target/'missing-parent'/'nested')]]
        for args in forms:
            with self.subTest(args=args):
                self.assertTrue(self.shape(args).get('error'))
                self.f.assertGate(2,shlex.join(args),cwd=self.ws)
        self.assertFalse(target.exists())

    def test_existing_nonempty_repo_and_symlink_destinations_deny(self):
        empty=self.ws/'empty';empty.mkdir();link=self.ws/'link';link.symlink_to(empty,target_is_directory=True)
        nonempty=self.ws/'nonempty';nonempty.mkdir();(nonempty/'keep').write_text('keep')
        self.assertTrue(self.shape(['git','clone',str(self.bundle),str(nonempty)]).get('error'))
        for destination in (self.source,link,link/'nested'):
            for action in (['git','init',str(destination)],['git','clone',str(self.bundle),str(destination)]):
                with self.subTest(action=action):self.assertTrue(self.shape(action).get('error'))
        self.assertEqual((nonempty/'keep').read_text(),'keep')
        self.assertFalse((empty/'.git').exists())

    def test_init_nonempty_project_preserves_files_and_rejects_reinitialization(self):
        project=self.ws/'ordinary';project.mkdir();(project/'keep.txt').write_text('keep')
        self.run_allowed(['git','init','-q',str(project)],project)
        self.assertEqual((project/'keep.txt').read_text(),'keep')
        nested=project/'nested';nested.mkdir()
        self.assertEqual(self.shape(['git','init',str(nested)])['paths'],[str(nested)])
        self.assertTrue(self.shape(['git','init','--bare',str(project)]).get('error'))
        self.assertTrue(self.shape(['git','init',str(project)]).get('error'))

    def test_nested_workspace_task_binding_tracks_new_repository_truth(self):
        scratch=self.f.repo/'data'/'scratch';scratch.parent.mkdir()
        gate=self.f.task('nested-bootstrap',scratch)
        command=shlex.join(['git','init','-q',str(scratch)])
        self.f.assertGate(0,command,cwd=self.f.repo)
        subprocess.run(['git','init','-q',str(scratch)],check=True, timeout=30)
        (scratch/'note.txt').write_text('scoped')
        staging=shlex.join(['git','-C',str(scratch),'add','note.txt'])
        # A workspace-root declaration cannot masquerade as the new repo.
        self.f.assertGate(2,staging,cwd=self.f.repo)
        for p in gate.glob('*.json'):
            data=json.loads(p.read_text());data['repo_root']=str(scratch);fixture.write(p,data)
        self.f.assertGate(0,staging,cwd=self.f.repo)
        subprocess.run(['git','-C',str(scratch),'add','note.txt'],check=True, timeout=30)
        self.assertEqual(subprocess.check_output(['git','-C',str(scratch),'diff','--cached','--name-only'],text=True, timeout=30).strip(),'note.txt')

    def test_existing_bare_and_linked_repository_metadata_cannot_be_reinitialized(self):
        bare=self.ws/'existing-bare'
        subprocess.run(['git','init','--bare','-q',str(bare)],check=True, timeout=30)
        linked=self.ws/'linked'
        subprocess.run(['git','-C',str(self.source),'worktree','add','--detach','--no-checkout',str(linked),'HEAD'],check=True,capture_output=True, timeout=30)
        self.assertTrue((linked/'.git').is_file())
        for destination in (bare,linked):
            for args in (['git','init',str(destination)],['git','init','--bare',str(destination)]):
                with self.subTest(args=args):self.assertTrue(self.shape(args).get('error'))
        self.assertTrue((bare/'HEAD').is_file())
        self.assertTrue((linked/'.git').is_file())

    def test_safe_remote_shapes_still_need_destination_task_no_transport_execution(self):
        target=self.ws/'network'
        for source in ('https://github.com/example/repo.git','ssh://git@example.invalid/repo','git@example.invalid:repo.git'):
            args=['git','clone','--no-checkout',source,str(target)]
            self.assertEqual(self.shape(args)['paths'],[str(target)])
            self.f.assertGate(2,shlex.join(args),cwd=self.ws)
        self.assertFalse(target.exists())

    def test_all_configured_Bash_PreToolUse_hooks_before_actual_creation(self):
        settings=json.loads((fixture.ROOT/'hooks/settings-snippet.json').read_text())
        hooks=[fixture.ROOT/h['command'].split('/claude-configs-public/',1)[1]
               for group in settings['hooks']['PreToolUse'] if group.get('matcher')=='Bash'
               for h in group['hooks']]
        self.assertEqual(len(hooks),16)
        template=self.ws/'native-template';template.mkdir()
        outside=self.ws/'native-outside';outside.mkdir()
        (template/'objects').symlink_to(outside,target_is_directory=True)
        config=self.ws/'native-global.config';config.write_text('[init]\n templateDir = '+str(template)+'\n')
        self.f.env['GIT_CONFIG_GLOBAL']=str(config)
        for index,kind in enumerate(('init','clone')):
            target=self.ws/('native-'+kind)
            if kind=='init':
                target.mkdir();args=['git','init','--template=','-q','.'];cwd=target
            else:
                args=['git','clone','--mirror','--template','',str(self.bundle),str(target)];cwd=self.ws
            self.task(target)
            command='cd '+shlex.quote(str(cwd))+' && '+shlex.join(args)
            payload=fixture.craft_payload(tool_name='Bash',cwd=str(self.ws/'sessions/one'),tool_input={'command':command})
            outcomes=[]
            for hook in hooks:
                result=subprocess.run(['bash',str(hook)],input=json.dumps(payload),env=self.f.env,
                                      text=True,capture_output=True,timeout=20,cwd=self.f.repo)
                outcomes.append((hook.name,result.returncode))
                self.assertEqual(result.returncode,0,(kind,hook.name,result.stderr,result.stdout))
                self.assert_hook_output_allows(result.stdout)
            subprocess.run(args,cwd=cwd,env=self.f.env,check=True,capture_output=True,timeout=15)
            self.assertTrue((target/('HEAD' if kind=='clone' else '.git/HEAD')).is_file())
            print('native-shaped '+kind+' all '+str(len(outcomes))+' configured Bash hooks permit; explicit empty template and actual Git creation verified')
            self.assertEqual(list(outside.iterdir()),[])
            gate=self.ws/'sessions/one/tasks'/fixture.r.task_slug('bootstrap1240')/'think-gate.json'
            data=json.loads(gate.read_text());data['status']='disposed';fixture.write(gate,data)

    def assert_hook_output_allows(self, output):
        text = output.strip()
        encoded = [text] if text.startswith('{') else [line for line in text.splitlines() if line.lstrip().startswith('{')]
        for value in encoded:
            # Malformed or mixed machine output fails the acceptance fixture;
            # it cannot be silently skipped as permission to run the command.
            response = json.loads(value)
            if isinstance(response, dict):
                self.assertIsNot(response.get('continue'), False, response)
                self.assertNotEqual(response.get('decision'), 'block', response)
                specific = response.get('hookSpecificOutput', {})
                if isinstance(specific, dict):
                    self.assertNotIn(specific.get('permissionDecision'), ('deny', 'ask', 'defer'), response)

    def test_machine_output_parser_checks_complete_pretty_controls(self):
        self.assert_hook_output_allows('ordinary advisory text')
        self.assert_hook_output_allows(json.dumps({'continue': True}, indent=2))
        for response in ({'continue': False}, {'decision': 'block'},
                         *({'hookSpecificOutput': {'permissionDecision': decision}} for decision in ('deny', 'ask', 'defer'))):
            with self.subTest(response=response), self.assertRaises(AssertionError):
                self.assert_hook_output_allows(json.dumps(response, indent=2))
        with self.assertRaises(json.JSONDecodeError):
            self.assert_hook_output_allows('{broken machine output')

    def test_actual_global_URL_rewrites_validate_effective_source_once_without_transport(self):
        config=self.ws/'global.config';target=self.ws/'rewritten'
        def configured(prefix,replacement,extra=''):
            config.write_text('[url "'+replacement+'"]\n    insteadOf = '+prefix+'\n'+extra)
        url='https://example.test/project.git'
        with patch.dict(os.environ,{'GIT_CONFIG_GLOBAL':str(config),'GIT_CONFIG_NOSYSTEM':'1'}):
            configured('https://example.test/','ext::private-fixture-helper ')
            actual=subprocess.check_output(['git','ls-remote','--get-url','--',url],text=True, timeout=30).strip()
            self.assertEqual(actual,'ext::private-fixture-helper project.git')
            self.assertTrue(self.shape(['git','clone',url,str(target)]).get('error'))
            for prefix,replacement,value in (
                ('https://example.test/','ssh://git@example.test/','https://example.test/project.git'),
                ('ssh://git@example.test/','https://example.test/','ssh://git@example.test/project.git')):
                configured(prefix,replacement)
                self.assertEqual(self.shape(['git','clone',value,str(target)])['paths'],[str(target)])
            # Git expands insteadOf once: do not reinterpret the returned URL.
            configured('https://example.test/','ssh://git@example.test/',
                       '[url "ext::must-not-expand-twice "]\n    insteadOf = ssh://git@example.test/\n')
            self.assertEqual(self.shape(['git','clone',url,str(target)])['paths'],[str(target)])
            configured('local-alias:',str(self.source)+'/')
            self.assertTrue(self.shape(['git','clone','local-alias:',str(target)]).get('error'))
            self.assertEqual(self.shape(['git','clone','--no-local','local-alias:',str(target)])['paths'],[str(target)])
            old_env=dict(self.f.env)
            try:
                self.f.env.update(GIT_CONFIG_GLOBAL=str(config),GIT_CONFIG_NOSYSTEM='1')
                self.run_allowed(['git','clone','--mirror','--no-local','local-alias:',str(target)],target)
                self.assertEqual(subprocess.check_output(['git','-C',str(target),'show','HEAD:note.txt'],text=True, timeout=30),'preserve me\n')
            finally:
                self.f.env.clear();self.f.env.update(old_env)
        self.assertTrue((target/'HEAD').is_file())

    def test_actual_global_template_symlink_cannot_write_outside_destination(self):
        template=self.ws/'custom-template';template.mkdir()
        outside=self.ws/'outside-template-scope';outside.mkdir()
        (template/'objects').symlink_to(outside,target_is_directory=True)
        config=self.ws/'global-template.config'
        config.write_text('[init]\n templateDir = '+str(template)+'\n')
        target=self.ws/'template-target';self.task(target)
        old_env=dict(self.f.env)
        try:
            self.f.env.update(GIT_CONFIG_GLOBAL=str(config),GIT_CONFIG_NOSYSTEM='1',GIT_TEMPLATE_DIR=str(template))
            with patch.dict(os.environ,{'GIT_CONFIG_GLOBAL':str(config),'GIT_CONFIG_NOSYSTEM':'1','GIT_TEMPLATE_DIR':str(template)}):
                actual=subprocess.check_output(['git','config','--path','--get','init.templateDir'],text=True, timeout=30).strip()
                self.assertEqual(actual,str(template))
                for args in (['git','init',str(target)],['git','clone','--mirror',str(self.bundle),str(target)]):
                    self.assertTrue(self.shape(args).get('error'))
                    self.f.assertGate(2,shlex.join(args),cwd=self.ws,env=self.f.env)
                for name,args in (
                    ('init',['git','init','--template=']),
                    ('clone',['git','clone','--mirror','--template','',str(self.bundle)])):
                    clean=self.ws/('empty-template-'+name)
                    self.run_allowed([*args,str(clean)],clean)
                    objects=clean/('objects' if name=='clone' else '.git/objects')
                    self.assertTrue(objects.is_dir());self.assertFalse(objects.is_symlink())
        finally:
            self.f.env.clear();self.f.env.update(old_env)
        self.assertEqual(list(outside.iterdir()),[])
        self.assertFalse(target.exists())

    def test_whitespace_template_is_a_real_path_not_an_empty_override(self):
        for index,value in enumerate((b' ',b'\t',b'\r',b'\n')):
            with self.subTest(value=value):
                target=self.ws/('space-template-target-'+str(index));target.mkdir()
                outside=self.ws/('space-template-outside-'+str(index));outside.mkdir()
                template=target/value.decode('ascii');template.mkdir()
                (template/'objects').symlink_to(outside,target_is_directory=True)
                config=self.ws/'space-template.config'
                setting=value.replace(b'\t',b'\\t').replace(b'\n',b'\\n')
                config.write_bytes(b'[init]\n templateDir = "'+setting+b'"\n')
                self.task(target)
                self.f.env['GIT_CONFIG_GLOBAL']=str(config)
                with patch.dict(os.environ,{'GIT_CONFIG_GLOBAL':str(config)}):
                    raw=subprocess.check_output(['git','config','--path','--get','init.templateDir'], timeout=30)
                    self.assertEqual(raw,value+b'\n')
                    args=['git','init',str(target)]
                    self.assertTrue(self.shape(args).get('error'))
                    self.f.assertGate(2,shlex.join(args),cwd=self.ws)
                    self.assertEqual(list(outside.iterdir()),[])
                    self.assertFalse((target/'.git').exists())
                    self.run_allowed(['git','init','--template=',str(target)],target)
                self.assertFalse((target/'.git/objects').is_symlink())
                self.assertEqual(list(outside.iterdir()),[])

    def test_env_template_only_has_bounded_empty_override_route(self):
        template=self.ws/'env-template';template.mkdir()
        outside=self.ws/'env-outside';outside.mkdir()
        (template/'objects').symlink_to(outside,target_is_directory=True)
        target=self.ws/'env-target';self.task(target)
        self.f.env['GIT_TEMPLATE_DIR']=str(template)
        with patch.dict(os.environ,{'GIT_TEMPLATE_DIR':str(template)}):
            for args in (['git','init',str(target)],['git','clone','--mirror',str(self.bundle),str(target)]):
                self.assertTrue(self.shape(args).get('error'))
                self.f.assertGate(2,shlex.join(args),cwd=self.ws)
            for name,args in (('init',['git','init','--template=']),
                              ('clone',['git','clone','--mirror','--template','',str(self.bundle)])):
                clean=self.ws/('env-clean-'+name)
                self.run_allowed([*args,str(clean)],clean)
                self.assertFalse((clean/('objects' if name=='clone' else '.git/objects')).is_symlink())
        self.assertEqual(list(outside.iterdir()),[])
        self.assertFalse(target.exists())

    def test_effective_source_CR_cannot_erase_directory_into_bundle_file(self):
        source=self.ws/'rewrite-source\r'
        self.source.rename(source)
        (self.ws/'rewrite-source').write_bytes(self.bundle.read_bytes())
        config=self.ws/'control-source.config'
        config.write_bytes(b'[url "'+str(source).encode()+b'"]\n insteadOf = alias:\n')
        target=self.ws/'control-source-target';self.task(target)
        self.f.env['GIT_CONFIG_GLOBAL']=str(config)
        with patch.dict(os.environ,{'GIT_CONFIG_GLOBAL':str(config)}):
            raw=subprocess.check_output(['git','ls-remote','--get-url','--','alias:'], timeout=30)
            self.assertEqual(raw,str(source).encode()+b'\n')
            args=['git','clone','--mirror','alias:',str(target)]
            self.assertTrue(self.shape(args).get('error'))
            self.f.assertGate(2,shlex.join(args),cwd=self.ws)
        self.assertFalse(target.exists())
        for obj in (source/'.git/objects').rglob('*'):
            if obj.is_file():self.assertEqual(obj.stat().st_nlink,1)

    def assert_independent_objects(self, source_gitdir, target_gitdir):
        originals=[p for p in (source_gitdir/'objects').rglob('*') if p.is_file()]
        copied=[p for p in (target_gitdir/'objects').rglob('*') if p.is_file()]
        self.assertTrue(originals);self.assertTrue(copied)
        original_ids={(p.stat().st_dev,p.stat().st_ino) for p in originals}
        for obj in copied:
            self.assertNotIn((obj.stat().st_dev,obj.stat().st_ino),original_ids)
            self.assertEqual(obj.stat().st_nlink,1)
        for obj in originals:self.assertEqual(obj.stat().st_nlink,1)
        self.assertFalse((target_gitdir/'objects/info/alternates').exists())

    def test_gitfile_pointer_requires_no_local_and_actual_clone_is_independent(self):
        pointer=self.ws/'pointer';pointer.write_text('gitdir: '+str(self.source/'.git')+'\n')
        target=self.ws/'gitfile-clone';self.task(target)
        args=['git','clone','--template=','--mirror',str(pointer),str(target)]
        self.assertTrue(self.shape(args).get('error'))
        self.f.assertGate(2,shlex.join(args),cwd=self.ws)
        self.assertFalse(target.exists())
        self.run_allowed(['git','clone','--template=','--mirror','--no-local',str(pointer),str(target)],target)
        self.assert_independent_objects(self.source/'.git',target)

    def test_git_suffix_beats_literal_remote_looking_source(self):
        for index,source in enumerate(('a@b:c','https://h/r')):
            with self.subTest(source=source):
                candidate=self.ws/(source+'.git');candidate.parent.mkdir(parents=True,exist_ok=True)
                subprocess.run(['git','clone','--template=','--mirror','--no-local',str(self.source),str(candidate)],check=True,capture_output=True,env=self.f.env, timeout=30)
                target=self.ws/('suffix-clone-'+str(index));self.task(target)
                args=['git','clone','--template=','--mirror',source,str(target)]
                self.assertTrue(self.shape(args).get('error'))
                self.f.assertGate(2,shlex.join(args),cwd=self.ws)
                self.assertFalse(target.exists())
                if '://' in source:
                    # Native Git cannot use --no-local on this URL-shadow form:
                    # its literal absolute path becomes an unsupported protocol.
                    self.assertTrue(self.shape(['git','clone','--template=','--mirror','--no-local',source,str(target)]).get('error'))
                    safe_source=str(candidate)
                else:
                    safe_source=source
                self.run_allowed(['git','clone','--template=','--mirror','--no-local',safe_source,str(target)],target)
                self.assert_independent_objects(candidate,target)
                actual=subprocess.check_output(['git','-C',str(target),'config','--local','remote.origin.url'],text=True,env=self.f.env, timeout=30)
                self.assertEqual(actual,os.path.join(str(self.ws),safe_source)+'\n')

    def test_bundle_suffix_is_a_read_input_not_a_repository_alias(self):
        target=self.ws/'bundle-suffix-clone'
        self.run_allowed(['git','clone','--template=','--mirror','saved',str(target)],target)
        self.assertEqual(subprocess.check_output(['git','-C',str(target),'show','HEAD:note.txt'],text=True, timeout=30),'preserve me\n')
        self.assertFalse((target/'objects/info/alternates').exists())

    def test_parent_config_and_source_remote_names_do_not_sanitize_helper(self):
        parent=self.f.repo;target=self.ws/'parent-config-target';self.task(target)
        literal='reviewfixture1240::x'
        subprocess.run(['git','-C',str(parent),'config','url.https://example.invalid/.insteadOf','reviewfixture1240::'],check=True,env=self.f.env, timeout=30)
        old=subprocess.check_output(['git','-C',str(parent),'ls-remote','--get-url','--',literal],text=True,env=self.f.env, timeout=30)
        self.assertEqual(old,'https://example.invalid/x\n')
        original=tempfile.TemporaryDirectory
        # Even a scratch below that repository must stop upward discovery.
        with patch('tempfile.TemporaryDirectory',side_effect=lambda **kw: original(prefix=kw['prefix'],dir=parent)):
            args=['git','clone','--template=',literal,str(target)]
            self.assertTrue(self.shape(args,parent).get('error'))
        self.f.assertGate(2,shlex.join(args),cwd=parent)
        global_config=self.ws/'global-source-alias.config'
        global_config.write_text('[remote "'+literal+'"]\n url = https://example.invalid/safe\n')
        with patch.dict(os.environ,{'GIT_CONFIG_GLOBAL':str(global_config)}):
            misleading=subprocess.check_output(['git','-C',str(self.ws),'ls-remote','--get-url','--',literal],text=True, timeout=30)
            self.assertEqual(misleading,'https://example.invalid/safe\n')
            self.assertTrue(self.shape(args,parent).get('error'))
        self.assertFalse(target.exists())

    def test_parent_template_ignored_but_real_global_URL_rewrite_preserved(self):
        parent=self.f.repo;target=self.ws/'ignore-parent-template';outside=self.ws/'parent-template-outside';outside.mkdir()
        template=self.ws/'parent-template';template.mkdir();(template/'objects').symlink_to(outside,target_is_directory=True)
        subprocess.run(['git','-C',str(parent),'config','init.templateDir',str(template)],check=True,env=self.f.env, timeout=30)
        self.run_allowed(['git','clone','--mirror',str(self.bundle),str(target)],target,cwd=parent)
        self.assertEqual(list(outside.iterdir()),[])
        global_config=self.ws/'global-rewrite.config'
        global_config.write_text('[url "ssh://git@example.invalid/"]\n insteadOf = https://example.invalid/\n')
        subprocess.run(['git','-C',str(parent),'config','url.ext::must-not-run .insteadOf','https://example.invalid/'],check=True,env=self.f.env, timeout=30)
        with patch.dict(os.environ,{'GIT_CONFIG_GLOBAL':str(global_config)}):
            from task_actions import _git_clone_effective_source
            self.assertEqual(_git_clone_effective_source('https://example.invalid/repo'),'ssh://git@example.invalid/repo')
            shape=self.shape(['git','clone','https://example.invalid/repo',str(self.ws/'network-rewrite')],parent)
            self.assertFalse(shape.get('error'),shape)

    def test_global_default_remote_and_URL_order_match_actual_clone(self):
        other=self.ws/'other-source'
        subprocess.run(['git','clone','--template=','--no-local',str(self.source),str(other)],check=True,capture_output=True,env=self.f.env, timeout=30)
        (other/'note.txt').write_text('other source\n')
        subprocess.run(['git','-C',str(other),'add','note.txt'],check=True,env=self.f.env, timeout=30)
        subprocess.run(['git','-C',str(other),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','other'],check=True,env=self.f.env, timeout=30)
        config=self.ws/'global-remote-order.config'
        config.write_text('[clone]\n defaultRemoteName = upstream=name\n[remote "upstream=name"]\n url = '+str(other)+'\n')
        self.f.env['GIT_CONFIG_GLOBAL']=str(config)
        target=self.ws/'global-remote-target'
        with patch.dict(os.environ,{'GIT_CONFIG_GLOBAL':str(config)}):
            from task_actions import _git_clone_effective_source
            self.assertEqual(_git_clone_effective_source(str(self.source)),str(other))
            self.run_allowed(['git','clone','--template=','--mirror','--no-local',str(self.source),str(target)],target)
        self.assertEqual(subprocess.check_output(['git','-C',str(target),'show','HEAD:note.txt'],text=True,env=self.f.env, timeout=30),'other source\n')
        self.assert_independent_objects(other/'.git',target)

    def test_existing_bare_whitespace_name_keeps_exact_metadata_identity(self):
        bare=self.ws/'existing-bare '
        subprocess.run(['git','init','--template=','--bare','-q',str(bare)],check=True,env=self.f.env, timeout=30)
        original=(bare/'HEAD').read_bytes();self.task(bare)
        args=['git','init',str(bare)]
        self.assertTrue(self.shape(args).get('error'))
        self.f.assertGate(2,shlex.join(args),cwd=self.ws)
        self.assertEqual((bare/'HEAD').read_bytes(),original)
        self.assertFalse((bare/'.git').exists())

    def conditional_config(self, target, rewrite=None, *, bare=False, nested=False, unrelated=False):
        included=self.ws/'destination-include.config'
        included.write_text(('[url "'+rewrite+'"]\n insteadOf = https://example.invalid/source\n') if rewrite else '[user]\n name = Conditional User\n')
        if nested:
            outer=self.ws/'outer-include.config';outer.write_text('[include]\n path = '+included.name+'\n');included=outer
        gitdir=(self.ws/'unrelated/.git') if unrelated else target if bare else target/'.git'
        config=self.ws/'conditional-global.config'
        config.write_text('[includeIf "gitdir:'+str(gitdir)+'"]\n path = '+included.name+'\n[protocol "ext"]\n allow = always\n')
        self.f.env.update(GIT_CONFIG_GLOBAL=str(config),GIT_ALLOW_PROTOCOL='file:ext')
        return {'GIT_CONFIG_GLOBAL':str(config),'GIT_ALLOW_PROTOCOL':'file:ext'}

    def test_conditional_helper_rewrite_denied_before_any_helper_or_target_write(self):
        for bare in (False,True):
            with self.subTest(bare=bare):
                target=self.ws/('conditional-helper-'+str(bare));marker=self.ws/('helper-marker-'+str(bare))
                environment=self.conditional_config(target,'ext::/usr/bin/touch '+str(marker),bare=bare,nested=True)
                args=['git','clone','--template=',*(['--mirror'] if bare else []),'https://example.invalid/source',str(target)]
                self.task(target)
                with patch.dict(os.environ,environment):
                    missing=self.shape(args);self.assertIn('existing empty destination',missing.get('error',''))
                    self.f.assertGate(2,shlex.join(args),cwd=self.ws)
                    self.assertFalse(target.exists());self.assertFalse(marker.exists())
                    target.mkdir()
                    self.assertIn('unsupported Git clone transport',self.shape(args).get('error',''))
                    self.f.assertGate(2,shlex.join(args),cwd=self.ws)
                    self.assertEqual(list(target.iterdir()),[]);self.assertFalse(marker.exists())
                    # Counterfactual actual Git proves this exact destination
                    # include executes the private helper if the gate is ignored.
                    actual=subprocess.run(args,cwd=self.ws,env=self.f.env,capture_output=True,timeout=10)
                    self.assertNotEqual(actual.returncode,0);self.assertTrue(marker.exists())

    def test_conditional_local_rewrite_mkdir_retry_actual_independent_clone(self):
        for bare in (False,True):
            with self.subTest(bare=bare):
                target=self.ws/('conditional-local-'+str(bare))
                environment=self.conditional_config(target,str(self.source),bare=bare,nested=True)
                args=['git','clone','--template=','--no-local',*(['--mirror'] if bare else []),'https://example.invalid/source',str(target)]
                with patch.dict(os.environ,environment):
                    self.assertIn('existing empty destination',self.shape(args).get('error',''))
                    target.mkdir()
                    self.run_allowed(args,target)
                metadata=target if bare else target/'.git'
                self.assert_independent_objects(self.source/'.git',metadata)
                self.assertEqual(subprocess.check_output(['git','-C',str(target),'show','HEAD:note.txt'],env=self.f.env,text=True, timeout=30),'preserve me\n')

    def test_conditional_safe_transport_uses_actual_destination_not_unrelated_include(self):
        target=self.ws/'conditional-safe';target.mkdir()
        environment=self.conditional_config(target,'ssh://git@example.invalid/safe')
        args=['git','clone','https://example.invalid/source',str(target)]
        with patch.dict(os.environ,environment):
            from task_actions import _git_clone_effective_source
            self.assertEqual(_git_clone_effective_source('https://example.invalid/source',git_dir=str(target/'.git')),'ssh://git@example.invalid/safe')
            self.assertFalse(self.shape(args).get('error'))
        environment=self.conditional_config(target,'ext::never-execute',unrelated=True)
        with patch.dict(os.environ,environment):
            self.assertFalse(self.shape(args).get('error'))
        self.assertEqual(list(target.iterdir()),[])

    def test_non_URL_conditional_include_preserves_absent_destination_clone(self):
        target=self.ws/'conditional-user-only'
        environment=self.conditional_config(target,nested=True)
        with patch.dict(os.environ,environment):
            self.run_allowed(['git','clone','--template=','--no-local',str(self.source),str(target)],target)
        self.assert_independent_objects(self.source/'.git',target/'.git')

    def test_conditional_remote_selection_matches_actual_clone_and_rejects_helper(self):
        target=self.ws/'conditional-remote';target.mkdir()
        included=self.ws/'remote-selection.config'
        included.write_text('[clone]\n defaultRemoteName = UPstream\n')
        config=self.ws/'remote-global.config'
        config.write_text('[includeIf "gitdir:'+str(target/'.git')+'"]\n path = '+str(included)+'\n[remote "UPstream"]\n url = '+str(self.source)+'\n')
        environment={'GIT_CONFIG_GLOBAL':str(config),'GIT_ALLOW_PROTOCOL':'file'}
        self.f.env.update(environment)
        with patch.dict(os.environ,environment):
            args=['git','clone','--template=','--no-local','https://example.invalid/source',str(target)]
            from task_actions import _git_clone_effective_source
            self.assertEqual(_git_clone_effective_source('https://example.invalid/source',git_dir=str(target/'.git')),str(self.source))
            self.run_allowed(args,target)
            remote=subprocess.check_output(['git','-C',str(target),'config','--local','--get','remote.UPstream.url'],env=self.f.env,text=True, timeout=30)
            self.assertEqual(remote,'https://example.invalid/source\n')
            self.assert_independent_objects(self.source/'.git',target/'.git')
        # A conditional remote URL alone is also transport configuration.
        denied=self.ws/'conditional-remote-helper';denied.mkdir()
        included.write_text('[remote "origin"]\n url = ext::never-execute\n')
        config.write_text('[includeIf "gitdir:'+str(denied/'.git')+'"]\n path = '+str(included)+'\n')
        with patch.dict(os.environ,environment):
            shape=self.shape(['git','clone','https://example.invalid/source',str(denied)])
            self.assertIn('unsupported Git clone transport',shape.get('error',''))
        self.assertEqual(list(denied.iterdir()),[])

    def test_missing_conditional_include_is_ignored_like_actual_Git(self):
        target=self.ws/'missing-include-target'
        config=self.ws/'missing-include-global.config'
        config.write_text('[includeIf "gitdir:'+str(target/'.git')+'"]\n path = missing.config\n')
        self.f.env['GIT_CONFIG_GLOBAL']=str(config)
        with patch.dict(os.environ,{'GIT_CONFIG_GLOBAL':str(config)}):
            self.run_allowed(['git','clone','--template=','--no-local',str(self.source),str(target)],target)
        self.assert_independent_objects(self.source/'.git',target/'.git')

    def test_remote_vcs_helper_is_transport_even_without_URL_rewrite(self):
        for conditional in (False,True):
            with self.subTest(conditional=conditional):
                target=self.ws/('vcs-target-'+str(conditional));target.mkdir()
                marker=self.ws/('vcs-marker-'+str(conditional));helpers=self.ws/('helpers-'+str(conditional));helpers.mkdir()
                helper=helpers/'git-remote-fixture';helper.write_text('#!/bin/sh\n/usr/bin/touch '+shlex.quote(str(marker))+'\nexit 1\n');helper.chmod(0o755)
                included=self.ws/'vcs-include.config';included.write_text('[remote "origin"]\n vcs = fixture\n')
                config=self.ws/'vcs-global.config';config.write_text(('[includeIf "gitdir:'+str(target/'.git')+'"]\n path = '+str(included)+'\n') if conditional else included.read_text())
                environment={'GIT_CONFIG_GLOBAL':str(config),'GIT_ALLOW_PROTOCOL':'fixture','PATH':str(helpers)+':'+os.environ['PATH']}
                self.f.env.update(environment)
                args=['git','clone','--template=','https://example.invalid/source',str(target)]
                self.task(target)
                with patch.dict(os.environ,environment):
                    self.assertIn('unsupported Git clone custom remote transport',self.shape(args).get('error',''))
                    self.f.assertGate(2,shlex.join(args),cwd=self.ws)
                    self.assertFalse(marker.exists());self.assertEqual(list(target.iterdir()),[])
                    actual=subprocess.run(args,cwd=self.ws,env=self.f.env,capture_output=True,timeout=10)
                    self.assertNotEqual(actual.returncode,0);self.assertTrue(marker.exists())

    def test_matching_onbranch_default_does_not_select_transport_during_clone(self):
        for branch in ('master','main'):
            with self.subTest(branch=branch):
                target=self.ws/('onbranch-'+branch);target.mkdir();marker=self.ws/('onbranch-marker-'+branch)
                included=self.ws/'onbranch-include.config';included.write_text('[url "ext::/usr/bin/touch '+str(marker)+'"]\n insteadOf = https://example.invalid/source\n')
                config=self.ws/'onbranch-global.config';config.write_text('[init]\n defaultBranch = '+branch+'\n[includeIf "onbranch:'+branch+'"]\n path = '+str(included)+'\n[protocol "ext"]\n allow = always\n')
                environment={'GIT_CONFIG_GLOBAL':str(config),'GIT_ALLOW_PROTOCOL':'ext'};self.f.env.update(environment)
                with patch.dict(os.environ,environment):
                    args=['git','clone','--template=','https://example.invalid/source',str(target)]
                    self.assertFalse(self.shape(args).get('error'))
                    actual=subprocess.run(args,cwd=self.ws,env=self.f.env,capture_output=True,timeout=10)
                    self.assertNotEqual(actual.returncode,0);self.assertIn(b"transport 'https' not allowed",actual.stderr)
                    self.assertFalse(marker.exists())

    def test_destination_lookup_preserves_unrelated_multiline_equals_and_spaces(self):
        target=self.ws/'unrelated-config-values';target.mkdir()
        environment=self.conditional_config(target,'ssh://git@example.invalid/safe')
        config=Path(environment['GIT_CONFIG_GLOBAL'])
        config.write_text(config.read_text()+'[alias]\n multiline = "first\\nsecond=value "\n[core]\n hooksPath = "ordinary hooks=path "\n[clone]\n defaultRemoteName = previous\n defaultRemoteName = origin\n')
        before=config.read_bytes()
        with patch.dict(os.environ,environment):
            from task_actions import _git_clone_effective_source
            self.assertEqual(_git_clone_effective_source('https://example.invalid/source',git_dir=str(target/'.git')),'ssh://git@example.invalid/safe')
            self.assertFalse(self.shape(['git','clone','https://example.invalid/source',str(target)]).get('error'))
        self.assertEqual(config.read_bytes(),before);self.assertEqual(list(target.iterdir()),[])

    def test_hasconfig_vcs_sees_new_remote_URL_before_transport(self):
        target=self.ws/'hasconfig-vcs';marker=self.ws/'hasconfig-marker';helpers=self.ws/'hasconfig-helpers';helpers.mkdir()
        helper=helpers/'git-remote-fixture';helper.write_text('#!/bin/sh\n/usr/bin/touch '+shlex.quote(str(marker))+'\nexit 1\n');helper.chmod(0o755)
        included=self.ws/'hasconfig-include.config';included.write_text('[remote "origin"]\n vcs = fixture\n')
        config=self.ws/'hasconfig-global.config';config.write_text('[includeIf "hasconfig:remote.*.url:https://example.invalid/source"]\n path = '+str(included)+'\n')
        environment={'GIT_CONFIG_GLOBAL':str(config),'GIT_ALLOW_PROTOCOL':'fixture','PATH':str(helpers)+':'+os.environ['PATH']};self.f.env.update(environment)
        args=['git','clone','--template=','https://example.invalid/source',str(target)]
        self.task(target)
        with patch.dict(os.environ,environment):
            self.assertIn('unsupported Git clone custom remote transport',self.shape(args).get('error',''))
            self.f.assertGate(2,shlex.join(args),cwd=self.ws)
            self.assertFalse(target.exists());self.assertFalse(marker.exists())
            actual=subprocess.run(args,cwd=self.ws,env=self.f.env,capture_output=True,timeout=10)
            self.assertNotEqual(actual.returncode,0);self.assertTrue(marker.exists())

    def test_inherited_git_targeting_environment_denies_bootstrap(self):
        for key in ('GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_TEMPLATE_DIR','GIT_CONFIG_COUNT','GIT_SSH_COMMAND'):
            with self.subTest(key=key),patch.dict(os.environ,{key:str(self.source)}):
                self.assertTrue(self.shape(['git','init',str(self.ws/'new')]).get('error'))


if __name__ == '__main__': unittest.main()
