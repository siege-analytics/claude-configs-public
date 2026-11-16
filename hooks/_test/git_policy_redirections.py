"""Real hook decisions retain Git policies and output ownership for literal redirects."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import task_keyed_gates as fixture
ROOT = Path(__file__).resolve().parents[2]
q = shlex.quote

class GitRedirections(unittest.TestCase):
    def setUp(self):
        self.f = fixture.Gates(); self.f.setUp(); self.addCleanup(self.f.tearDown)
        self.env = {key: value for key, value in self.f.env.items() if not key.startswith('GIT_')}
        self.env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
        self.git('checkout', '-qb', 'feature/export')
        self.git('config', 'user.name', 'Fixture'); self.git('config', 'user.email', 'fixture@example.invalid')
        self.source = self.f.a/'source.txt'; self.source.write_text('one\n')
        self.git('add', '.'); self.git('commit', '-qm', 'seed')
        self.git('remote', 'add', 'origin', 'https://github.com/siege-analytics/synthetic.git')
        for name in ('main', 'develop'):
            self.git('update-ref', 'refs/remotes/origin/'+name, 'HEAD')
        self.source.write_text('two\n'); self.git('add', 'a/source.txt')
        self.f.task('export-task', self.f.a, artifacts=False)
        self.output = self.f.a/'selected.patch'
        self.diff = 'CCP_TASK_ID=export-task git -C '+q(str(self.f.repo))+' diff --cached --no-ext-diff --no-textconv --binary --full-index HEAD -- a/source.txt'

    def git(self, *args):
        return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(self.f.repo), *args],
                                       env=self.env, text=True, stderr=subprocess.PIPE, timeout=15).strip()

    def hook(self, path, command, code=0):
        payload = fixture.craft_payload(tool_name='Bash', cwd=str(self.f.repo), tool_input={'command': command})
        result = subprocess.run(['bash', str(ROOT/path)], input=json.dumps(payload), env=self.env,
                                text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, code, result.stdout+result.stderr)
        return result

    def test_literal_export_runs_after_git_policy_and_output_ownership_checks(self):
        before = (self.git('rev-parse', 'HEAD'), (self.f.repo/'.git/index').read_bytes())
        for suffix in ['', ' 2>&1']:
            command = self.diff+' > '+q(str(self.output))+suffix
            for path in ['hooks/git/branch-guard.sh', 'hooks/bash/destructive-guard.sh',
                         'hooks/git/ticket-required.sh', 'hooks/bash/universal-mutation-gate.sh']:
                self.hook(path, command)
            shape = fixture.r.action(command, str(self.f.repo))
            self.assertFalse(shape['read_only']); self.assertEqual(shape['paths'], [str(self.output)])
            subprocess.run(command, shell=True, cwd=self.f.repo, env=self.env, check=True, timeout=15)
            self.assertIn('diff --git a/a/source.txt b/a/source.txt', self.output.read_text())
        self.assertEqual((self.git('rev-parse', 'HEAD'), (self.f.repo/'.git/index').read_bytes()), before)

    def test_redirect_does_not_hide_protected_commit_or_later_destructive_git(self):
        self.git('checkout', '-qb', 'main')
        commit = 'git -C '+q(str(self.f.repo))+" commit -m 'Refs: #1408'"
        result = self.hook('hooks/git/branch-guard.sh', commit+' > '+q(str(self.output)), 2)
        self.assertIn('Direct commit', result.stdout+result.stderr)
        self.hook('hooks/git/branch-guard.sh', self.diff+' > '+q(str(self.output))+'; '+commit, 2)
        for command in [commit+' --no-verify > '+q(str(self.output)),
                        self.diff+' > '+q(str(self.output))+'; git -C '+q(str(self.f.repo))+' push --force origin main']:
            self.hook('hooks/bash/destructive-guard.sh', command, 2)
        self.assertFalse(self.output.exists())

    def test_config_mutation_cannot_change_an_alias_around_a_redirected_git_call(self):
        self.git('config', 'alias.preview', 'status')
        git = 'git -C '+q(str(self.f.repo))
        redirect = git+' preview > '+q(str(self.output))
        change = git+" config alias.preview 'commit --no-verify -m subject'"
        for command in [change+'; '+redirect]:
            for guard in ['hooks/git/branch-guard.sh', 'hooks/bash/destructive-guard.sh']:
                with self.subTest(command=command, guard=guard):
                    self.hook(guard, command, 2)
        # A later config write cannot change the earlier inspected Git call.
        # Reads and per-command -c aliases remain their existing literal forms.
        for command in [redirect+'; '+change,
                        git+' config --get alias.preview; '+redirect,
                        git+' -c alias.preview=status preview > '+q(str(self.output))]:
            self.hook('hooks/git/branch-guard.sh', command)
            self.hook('hooks/bash/destructive-guard.sh', command)
        self.assertEqual(self.git('config', '--get', 'alias.preview'), 'status')
        self.assertFalse(self.output.exists())

    def test_pipeline_config_write_cannot_borrow_sequential_last_item_order(self):
        self.git('config', 'alias.preview', 'status')
        git = 'git -C ' + q(str(self.f.repo))
        change = git + " config alias.preview 'push --force origin main'"
        pipeline = git + ' preview > ' + q(str(self.output)) + ' | ' + change
        for command in [pipeline, 'bash -c ' + q(pipeline), 'eval ' + q(pipeline),
                        git + ' preview > ' + q(str(self.output)) + ' | bash -c ' + q(change)]:
            for guard in ['hooks/git/branch-guard.sh', 'hooks/bash/destructive-guard.sh']:
                with self.subTest(command=command, guard=guard):
                    result = self.hook(guard, command, 2)
                    self.assertIn('BLOCKED:', result.stdout + result.stderr)
                    if not command.startswith('eval '):
                        self.assertIn('configuration mutations', result.stdout + result.stderr)
        # A genuinely later sequential write stays ordered, even after a reader pipe.
        safe = git + ' status > ' + q(str(self.output)) + ' | cat; ' + change
        for command in [safe, git + ' preview > ' + q(str(self.output)) + ' | ' + git + ' config --get alias.preview']:
            self.hook('hooks/git/branch-guard.sh', command)
            self.hook('hooks/bash/destructive-guard.sh', command)
        self.assertFalse(self.output.exists())

    def test_barrier_proves_later_pipeline_member_can_change_dispatch(self):
        self.git('config', 'alias.preview', 'status')
        barrier = self.f.ws / 'barrier'; barrier.mkdir()
        stub = barrier / 'git'
        started, released, observed = [barrier / name for name in ['started', 'released', 'observed']]
        script = "#!/" + sys.executable.lstrip('/') + "\n"
        script += "import os,subprocess,sys,time\nfrom pathlib import Path\n"
        script += 'started=Path(' + repr(str(started)) + ');released=Path(' + repr(str(released)) + ')\n'
        script += "def wait(path):\n deadline=time.monotonic()+5\n while not path.exists():\n  if time.monotonic()>deadline:raise SystemExit(3)\n  time.sleep(.01)\n"
        script += "args=sys.argv[1:]\nif args[0]=='preview':\n started.touch();wait(released)\nelif args[0]=='config':\n wait(started)\n subprocess.run(['/usr/bin/git',*args],check=True,timeout=5)\n released.touch();raise SystemExit(0)\nos.execv('/usr/bin/git',['git',*args])\n"
        stub.write_text(script); stub.chmod(0o755)
        changed = '!printf observed > ' + q(str(observed))
        command = 'git preview > ' + q(str(self.output)) + ' | git config alias.preview ' + q(changed)
        result = subprocess.run(['/bin/bash', '-c', command], cwd=self.f.repo,
                                env={**self.env, 'PATH': str(barrier) + os.pathsep + self.env['PATH']},
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(observed.read_text(), 'observed')
        # Only a synthetic local printf alias ran; no publication command exists.

    def test_foreign_output_and_unsupported_dynamic_fd_state_stay_denied(self):
        self.hook('hooks/bash/universal-mutation-gate.sh', self.diff+' > '+q(str(self.f.b/'foreign.patch')), 2)
        for command in [self.diff+' > "$OUTPUT"', self.diff+' > '+q(str(self.f.a))+'/*.patch',
                        self.diff+' > '+q(str(self.output))+' &', self.diff+' >& "$FD"',
                        'GIT_INDEX_FILE=/tmp/foreign '+self.diff.removeprefix('CCP_TASK_ID=export-task ')+' > '+q(str(self.output)),
                        'exec '+self.diff.removeprefix('CCP_TASK_ID=export-task ')+' > '+q(str(self.output)),
                        'cd '+q(str(self.f.repo))+' && git diff > '+q(str(self.output)),
                        "bash -lc 'git commit -m subject' > "+q(str(self.output)),
                        "env bash --noprofile -c 'git commit -m subject' > "+q(str(self.output)),
                        "command '/bin/bash' -lc 'git commit -m subject' > "+q(str(self.output)),
                        "'eval' -- 'git commit -m subject' > "+q(str(self.output)),
                        "bash -c -- 'git commit -m subject' > "+q(str(self.output))]:
            with self.subTest(command=command):
                self.hook('hooks/git/branch-guard.sh', command, 2)
                self.hook('hooks/bash/destructive-guard.sh', command, 2)
        self.assertFalse(self.output.exists()); self.assertFalse((self.f.b/'foreign.patch').exists())

if __name__ == '__main__':
    unittest.main()
