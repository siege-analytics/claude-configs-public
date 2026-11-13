#!/usr/bin/env python3
"""Explicit tar/venv write destinations and own-session data/ scratch tiers (#1152).

A fully modelled `tar` or `python -m venv` invocation writes only under its
explicit destination, so that destination replaces the cwd as the mutation
target. Every other shape keeps the generic model, where the cwd stays a
target. A target in the current session's own data/ with no tracked files
floors at Tier A; tracked content and clones keep normal classification.
The value of a gh -R/--repo repository selector is never a local target;
the cwd stays the target of those unmodelled gh writes (#1347).
"""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import task_keyed_gates as fixture  # noqa: E402

q = shlex.quote


class ExplicitTargets(unittest.TestCase):
    def setUp(self):
        self.f = fixture.Gates()
        self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.ws = self.f.ws
        self.git('init', '-q', str(self.ws))  # the workspace is itself a repository
        self.scope = self.ws / 'sessions/one/data/extract'
        self.scope.mkdir(parents=True)
        self.outside = self.f.repo  # an existing directory no task owns
        payload = self.ws / 'payload'
        payload.mkdir()
        (payload / 'hello.txt').write_text('hi\n')
        with tarfile.open(self.scope / 'src.tar.gz', 'w:gz') as archive:
            archive.add(payload / 'hello.txt', arcname='pkg/hello.txt')
        self.payload = payload

    def git(self, *args, cwd=None):
        return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', *args], cwd=cwd, check=True,
                              capture_output=True, text=True, timeout=30)

    def task(self, scope, *, repo_root=None, tier=None, artifacts=True, identity='extract1152'):
        gate = self.f.task(identity, scope, artifacts=artifacts)
        for p in gate.glob('*.json'):
            data = json.loads(p.read_text())
            data['repo_root'] = str(repo_root or self.ws)
            if tier:
                data['tier'] = tier
            fixture.write(p, data)
        return gate

    def paths(self, command, cwd=None):
        shape = fixture.r.action(command, str(cwd or self.outside))
        self.assertFalse(shape.get('error'), shape)
        return shape['paths']

    def tier(self, command, cwd=None):
        payload = fixture.craft_payload(tool_name='Bash', cwd=str(cwd or self.outside), tool_input={'command': command})
        result = fixture.r.resolve_action(str(self.ws), payload)
        self.assertTrue(result.get('gate'), result)
        return result['tier']

    def run_command(self, command, cwd=None):
        return subprocess.run(command, shell=True, cwd=str(cwd or self.outside), env=self.f.env,
                              capture_output=True, text=True, timeout=120, check=True)

    # --- tar -------------------------------------------------------------

    def test_tar_extract_directory_operand_replaces_cwd(self):
        self.task(self.scope)
        archive, target = q(str(self.scope / 'src.tar.gz')), q(str(self.scope))
        forms = [
            f'tar -xzf {archive} -C {target}',
            f'tar -x -z -f {archive} -C {target}',
            f'tar xzf {archive} -C {target}',
            f'tar -xzf {archive} --directory={target}',
            f'tar -xzf {archive} --directory {target}',
            f'tar -xzvf {archive} -C {target} --strip-components=1',
            f'tar -xz -C {target} -f - < {archive}',
            f'tar -xzf {archive} -C {target} pkg',
        ]
        for command in forms:
            with self.subTest(command=command):
                paths = self.paths(command)
                self.assertNotIn(str(self.outside), paths)
                self.assertIn(str(self.scope), paths)
                self.f.assertGate(0, command, cwd=self.outside)
        self.run_command(forms[0])
        self.assertEqual((self.scope / 'pkg/hello.txt').read_text(), 'hi\n')
        # Slash operands stay conservative targets (resolved from the cwd), so a
        # member path with a slash is still counted and an outside cwd denies.
        member = f'tar -xzf {archive} -C {target} pkg/hello.txt'
        self.assertIn(str(self.outside / 'pkg/hello.txt'), self.paths(member))
        self.f.assertGate(2, member, cwd=self.outside)

    def test_tar_relative_directory_resolves_from_effective_cwd(self):
        self.task(self.scope)
        (self.scope / 'sub').mkdir()
        command = f'cd {q(str(self.scope))} && tar -xzf src.tar.gz -C sub'
        self.assertEqual(self.paths(command), [str(self.scope / 'sub')])
        self.f.assertGate(0, command, cwd=self.outside)

    def test_tar_create_counts_only_the_archive(self):
        self.task(self.scope)
        out = self.scope / 'out.tgz'
        command = f'tar -czf {q(str(out))} hello.txt'
        self.assertEqual(self.paths(command, cwd=self.payload), [str(out)])
        self.f.assertGate(0, command, cwd=self.payload)
        self.run_command(command, cwd=self.payload)
        with tarfile.open(out) as archive:
            self.assertIn('hello.txt', archive.getnames())  # bsdtar may add ._ AppleDouble entries

    def test_out_of_scope_destinations_still_deny(self):
        self.task(self.scope)
        archive = q(str(self.scope / 'src.tar.gz'))
        for command in (f'tar -xzf {archive} -C {q(str(self.outside))}',
                        f'tar -czf {q(str(self.outside / "o.tgz"))} hello.txt',
                        f'python3 -m venv {q(str(self.outside / "v"))}',
                        f'python3 -m venv {q(str(self.scope / "ok"))} {q(str(self.outside / "v"))}'):
            with self.subTest(command=command):
                self.f.assertGate(2, command, cwd=self.payload)

    def test_unmodelled_tar_shapes_keep_the_cwd_target(self):
        self.task(self.scope)
        archive, target = q(str(self.scope / 'src.tar.gz')), q(str(self.scope))
        shapes = [
            f'tar -xzPf {archive} -C {target}',
            f'tar -xzf {archive} -C {target} --absolute-names',
            f'tar -xzf {archive} -C {target} --to-command=cat',
            f'tar -xf {archive} -C {target} -I gzip',
            f'tar -xf {archive} -C {target} --use-compress-program=gzip',
            f'tar -xzOf {archive} -C {target}',
            f'tar -xzf {archive} -C {target} --to-stdout',
            f'tar -xzf {archive} -C {target} -C {target}',
            f'tar -xzf {archive} pkg/hello.txt -C {target}',
            f'tar -xzf {archive} -C {target} --transform=s/a/b/',
            f'tar -xzf {archive} -C {target} -T {target}/list',
            f'tar -xzf {archive} -C {target} --overwrite',
            f'tar -xzf {archive} -C {target} --checkpoint-action=exec=true',
            f'tar -xzf {archive} -C {target} --unknown-option',
            f'tar -xzf host:{archive} -C {target}',
            f'tar -xzf {archive} -C {target} --',
            f'tar -tzf {archive} -C {target}',
            f'tar -rf {archive} -C {target} x',
            f'tar -xczf {archive} -C {target}',
            f'tar -czf - {target}',
            f'tar -cz {target}',
            f'tar -czf {q(str(self.scope / "o.tgz"))} -C {target} --files-from=x',
            f'tar -czf {q(str(self.scope / "o2.tgz"))} -C {target} x',
            f'tar -C {target} -czf {q(str(self.scope / "o3.tgz"))} x',
        ]
        for command in shapes:
            with self.subTest(command=command):
                self.assertIn(str(self.outside), self.paths(command))
                self.f.assertGate(2, command, cwd=self.outside)

    # --- python -m venv ----------------------------------------------------

    # Only the isolated form `python -I -m venv` is modelled: without -I, `-m`
    # puts the cwd first on sys.path for every module venv imports.

    def test_isolated_venv_destination_operands_replace_cwd(self):
        self.task(self.scope)
        v = self.scope / 'v1'
        forms = [
            f'python3 -I -m venv --without-pip {q(str(v))}',
            f'python3 -I -m venv {q(str(v))}',
            f'python -I -m venv --clear --symlinks --prompt demo {q(str(v))}',
            f'python3 -I -m venv --prompt=demo --system-site-packages --copies --upgrade {q(str(v))}',
            f'python3 -I -m venv --without-pip {q(str(v))} {q(str(self.scope / "v2"))}',
            f'{q(sys.executable)} -I -m venv --without-pip {q(str(v))}',
        ]
        for command in forms:
            with self.subTest(command=command):
                paths = self.paths(command)
                self.assertNotIn(str(self.outside), paths)
                self.assertIn(str(v), paths)
                self.f.assertGate(0, command, cwd=self.outside)
        self.run_command(f'python3 -I -m venv --without-pip {q(str(v))}')
        self.assertTrue((v / 'pyvenv.cfg').is_file())

    def test_isolated_venv_does_not_run_cwd_modules(self):
        # Real run: a marker-writing types.py in the cwd must not execute.
        self.task(self.scope)
        marker = self.ws / 'MARKER'
        (self.outside / 'types.py').write_text(f'open({str(marker)!r}, "w").write("ran")\n')
        v = self.scope / 'iso'
        command = f'python3 -I -m venv --without-pip {q(str(v))}'
        self.assertEqual(self.paths(command), [str(v)])
        self.run_command(command)
        self.assertTrue((v / 'pyvenv.cfg').is_file())
        self.assertFalse(marker.exists())

    def test_unmodelled_venv_shapes_keep_the_cwd_target(self):
        self.task(self.scope)
        v = q(str(self.scope / 'v1'))
        shapes = [
            f'python3 -m venv {v}',
            f'python3 -m venv --without-pip {v}',
            f'python3 -I -m venv --upgrade-deps {v}',
            f'python3 -I -m venv --sys {v}',
            f'python3 -I -m venv --unknown {v}',
            f'python3 -I -m venv -h {v}',
            f'python3 -I -m venv -- {v}',
            f'python3 -I -m venv --prompt',
            'python3 -I -m venv',
            f'python3 -Im venv {v}',
            f'python3 -P -m venv {v}',
            f'python3 -I -m venvx {v}',
            f'python3 -m pip install --target {v} x',
        ]
        for command in shapes:
            with self.subTest(command=command):
                self.assertIn(str(self.outside), self.paths(command))
                self.f.assertGate(2, command, cwd=self.outside)

    def test_unisolated_venv_keeps_the_cwd_target_for_any_cwd_module(self):
        self.task(self.scope)
        command = f'python3 -m venv --without-pip {q(str(self.scope / "v1"))}'
        for shadow in ('venv.py', 'types.py', 'shutil.py', 'argparse.py', 'logging/__init__.py', None):
            with self.subTest(shadow=shadow):
                if shadow:
                    path = self.outside / shadow
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text('')
                self.assertIn(str(self.outside), self.paths(command))
                self.f.assertGate(2, command, cwd=self.outside)
                if shadow:
                    path.unlink()

    # --- own-session data/ tier floor --------------------------------------

    def test_own_session_data_scratch_floors_at_tier_a(self):
        self.task(self.scope, tier='A', artifacts=False)
        for command in (f'cd {q(str(self.scope))} && tar -xzf src.tar.gz',
                        f'tar -xzf {q(str(self.scope / "src.tar.gz"))} -C {q(str(self.scope))}',
                        f'cd {q(str(self.scope))} && python3 -I -m venv --without-pip v3'):
            with self.subTest(command=command):
                tier = self.tier(command)
                self.assertEqual((tier['floor'], tier['effective']), ('A', 'A'), tier)
                self.assertTrue(any('own-session data scratch' in r for r in tier['reasons']), tier)
                self.f.assertGate(0, command, cwd=self.outside)

    def test_cwd_fallback_in_own_data_is_never_scratch(self):
        # An unmodelled command's cwd stands for unknown writes, not untracked
        # content, so it keeps baseline B for publication review.
        self.task(self.scope, tier='A', artifacts=False)
        for command in ('make install', './run.sh', 'tar -xzf src.tar.gz && make',
                        'python3 -m venv --without-pip v4'):
            with self.subTest(command=command):
                tier = self.tier(command, cwd=self.scope)
                self.assertEqual(tier['floor'], 'B', tier)
                self.assertFalse(any('own-session data scratch' in r for r in tier['reasons']), tier)
                self.f.assertGate(0, command, cwd=self.scope)
                self.f.assertGate(2, command, cwd=self.outside)

    def test_tracked_content_under_data_keeps_normal_classification(self):
        self.task(self.scope, tier='A', artifacts=False)
        (self.scope / 'tool.py').write_text('x = 1\n')
        self.git('-C', str(self.ws), 'add', '-f', 'sessions/one/data/extract/tool.py')
        tier = self.tier(f'cd {q(str(self.scope))} && tar -xzf src.tar.gz')
        self.assertEqual(tier['floor'], 'B', tier)
        self.f.assertGate(0, f'cd {q(str(self.scope))} && tar -xzf src.tar.gz', cwd=self.outside)
        self.f.assertGate(2, f'tar -xzf src.tar.gz', cwd=self.outside)

    def test_hardlinked_file_under_data_is_not_scratch(self):
        self.task(self.scope, tier='A', artifacts=False)
        tracked = self.ws / 'tracked'
        tracked.write_text('x\n')
        self.git('-C', str(self.ws), 'add', '-f', 'tracked')
        os.link(tracked, self.scope / 'alias')
        tier = self.tier(f'printf x > {q(str(self.scope / "alias"))}')
        self.assertEqual(tier['floor'], 'B', tier)

    def test_clone_inside_data_keeps_its_own_classification(self):
        clone = self.ws / 'sessions/one/data/clone'
        (clone / 'hooks/bash').mkdir(parents=True)
        self.git('init', '-q', str(clone))
        (clone / 'hooks/bash/guard.sh').write_text('#!/bin/sh\n')
        self.git('-C', str(clone), 'add', 'hooks/bash/guard.sh')
        self.task(clone, repo_root=clone, tier='A', artifacts=False, identity='clone1152')
        tier = self.tier(f'cd {q(str(clone))} && tar -xzf src.tar.gz')
        self.assertEqual(tier['floor'], 'C', tier)

    def test_another_sessions_data_is_not_own_scratch(self):
        other = self.ws / 'sessions/two/data/x'
        other.mkdir(parents=True)
        self.task(other, tier='A', artifacts=False)
        tier = self.tier(f'cd {q(str(other))} && tar -xzf src.tar.gz')
        self.assertEqual(tier['floor'], 'B', tier)

    def test_symlinked_data_directory_is_not_own_scratch(self):
        real = self.ws / 'elsewhere'
        real.mkdir()
        os.rename(self.ws / 'sessions/one/data', real / 'data')
        os.symlink(real / 'data', self.ws / 'sessions/one/data')
        target = real / 'data/extract'
        self.task(target, tier='A', artifacts=False)
        tier = self.tier(f'cd {q(str(target))} && tar -xzf src.tar.gz')
        self.assertEqual(tier['floor'], 'B', tier)

    # --- gh -R/--repo repository selector (#1347) ----------------------------

    # cli/cli cmdutil.EnableRepoOverride: these groups take -R/--repo as a
    # [HOST/]OWNER/REPO selector, never a local path. The cwd stays the target.
    GH_SELECTOR_FORMS = (
        'gh issue close 5 -R example/target',
        'gh issue close 5 --repo example/target',
        'gh issue close 5 --repo=example/target',
        'gh issue close 5 -Rexample/target',
        'gh issue close 5 -R=example/target',
        'gh issue -R example/target close 5',
        'gh pr close 5 --repo example/target --delete-branch',
        'gh pr merge 5 -R github.example.com/example/target',
        'gh release delete v1 -R example/.github --yes',
        'gh run cancel 9 -R example/target',
        'gh workflow disable ci.yml -R example/target',
        'gh label delete bug -R example/target --yes',
        'gh secret delete TOKEN -R example/target',
        'gh variable delete NAME -R example/target',
        'gh cache delete 7 -R example/target',
        'gh ruleset view 1 -R example/target',
        # Global position: cobra finds the group after stripping flags.
        'gh -R example/target issue close 5',
        'gh --repo example/target pr close 5',
        'gh --repo=example/target issue close 5',
        'gh -Rexample/target issue close 5',
        'gh -R=example/target run cancel 9',
        'gh -R example/target -R other/repo pr close 5',
        'gh issue close 5 -R example/target --repo other/repo',
    )

    def nonrepo_dir(self):
        path = Path(os.path.realpath(tempfile.mkdtemp(prefix='gh1347-')))
        self.addCleanup(shutil.rmtree, path, True)
        return path

    def test_gh_repo_selector_is_not_a_path_target(self):
        clone = self.f.repo
        for cwd in (self.nonrepo_dir(), self.scope, clone):
            for command in self.GH_SELECTOR_FORMS:
                with self.subTest(cwd=str(cwd), command=command):
                    self.assertEqual(self.paths(command, cwd=cwd), [str(cwd)])

    def test_gh_repo_selector_passes_from_an_owned_cwd(self):
        clone = self.f.repo
        self.task(clone, repo_root=clone, identity='gh1347')
        for command in self.GH_SELECTOR_FORMS:
            with self.subTest(command=command):
                self.f.assertGate(0, command, cwd=clone)

    def test_gh_repo_selector_keeps_the_owned_cwd_requirement(self):
        # A cwd no task owns still refuses, and the denial names only the cwd.
        self.task(self.scope)
        for cwd in (self.nonrepo_dir(), self.f.repo):
            for command in self.GH_SELECTOR_FORMS[:6]:
                with self.subTest(cwd=str(cwd), command=command):
                    result = self.f.assertGate(2, command, cwd=cwd)
                    self.assertIn('Unowned target: ' + str(cwd), result.stderr)
                    self.assertNotIn(str(cwd / 'example'), result.stderr)
                    self.assertNotIn('Unowned target: /target', result.stderr)

    def test_gh_genuine_paths_and_unproven_selectors_stay_targets(self):
        clone = self.f.repo
        cases = {
            # Genuine path operands beside a selector are still counted.
            'gh release create v1 ./dist/x.tgz -R example/target': [clone / 'dist/x.tgz'],
            'gh issue close 5 -R example/target sub/dir': [clone / 'sub/dir'],
            'gh release upload v1 ' + q(str(self.payload / 'x.tgz')) + ' -R example/target': [self.payload / 'x.tgz'],
            # Values outside the [HOST/]OWNER/REPO grammar keep the old model.
            'gh issue close 5 -R ./example/target': [clone / 'example/target'],
            'gh issue close 5 -R ../escape': [self.ws / 'escape'],
            'gh issue close 5 -R a/b/c/d': [clone / 'a/b/c/d'],
            'gh issue close 5 --repo=example/../../escape': [self.ws / 'escape'],
            'gh issue close 5 -R' + str(self.payload / 'x'): [self.payload / 'x'],
            # After `--` a token is an operand, not an option.
            'gh issue close 5 -- -R example/target': [clone / 'example/target'],
            # Groups without the repo override, extensions and root flags.
            'gh repo clone example/target dest/dir': [clone / 'example/target', clone / 'dest/dir'],
            'gh myext -R example/target': [clone / 'example/target'],
            'gh -R example/target repo delete x': [clone / 'example/target'],
            'gh -R example/target myext': [clone / 'example/target'],
            # Any other leading token keeps the generic model.
            'gh --foo -R example/target issue close 5': [clone / 'example/target'],
            'gh -R ./example/target issue close 5': [clone / 'example/target'],
            # A genuine path next to a global selector is still counted.
            'gh -R example/target issue close 5 ' + q(str(self.payload / 'x')): [self.payload / 'x'],
            # An absolute gh path is not modelled.
            '/usr/local/bin/gh issue close 5 -Rexample/target': ['/target'],
        }
        for command, expected in cases.items():
            with self.subTest(command=command):
                paths = self.paths(command, cwd=clone)
                for path in expected:
                    self.assertIn(str(path), paths)
                self.assertIn(str(clone), paths)

    def unmodelled_paths(self, command, cwd):
        # Oracle for "unchanged": the same words under an unmodelled gh name.
        return self.paths(command.replace('gh issue ', 'gh unmodelled-ext ', 1), cwd=cwd)

    def test_gh_selector_grammar_negatives_keep_the_generic_model(self):
        clone = self.f.repo
        cases = {
            'gh issue close 5 -R /a/b': ['/a/b'],
            'gh issue close 5 -R ./a/b': [clone / 'a/b'],
            'gh issue close 5 -R ../a': [self.ws / 'a'],
            'gh issue close 5 -R a/../b': [clone / 'b'],
            'gh issue close 5 --repo a/b/': [clone / 'a/b'],
            'gh issue close 5 --repo=a/b/c/d': [clone / 'a/b/c/d'],
            'gh issue close 5 -R -a/b': [],
            "gh issue close 5 -R ''": [],
            'gh issue close 5 --repo=': [],
            'gh issue close 5 -R': [],
            'gh issue close 5 --repo': [],
            # Look-alike flags are not the selector (pflag has no abbreviations).
            'gh issue close 5 --repository o/r': [clone / 'o/r'],
            'gh issue close 5 --repo-x=o/r': [clone / 'o/r'],
            'gh issue close 5 -dRo/r': ['/r'],
        }
        for command, expected in cases.items():
            with self.subTest(command=command):
                paths = self.paths(command, cwd=clone)
                self.assertEqual(paths, self.unmodelled_paths(command, clone))
                self.assertIn(str(clone), paths)
                for path in expected:
                    self.assertIn(str(path), paths)
        # A tilde value still fails closed as an expanded target.
        for command in ('gh issue close 5 -R ~/a', 'gh issue close 5 --repo=~/a'):
            with self.subTest(command=command):
                self.assertTrue(fixture.r.action(command, str(clone)).get('error'))
        self.task(clone, repo_root=clone, identity='gh1347')
        for command in ('gh issue close 5 -R /a/b', 'gh issue close 5 -R ../a', 'gh issue close 5 -R ~/a'):
            with self.subTest(command=command):
                self.f.assertGate(2, command, cwd=clone)
        nonrepo = self.nonrepo_dir()
        for command in ('gh issue close 5 -R', 'gh issue close 5 --repo'):
            with self.subTest(command=command):
                self.f.assertGate(2, command, cwd=nonrepo)
                self.f.assertGate(0, command, cwd=clone)

    def test_gh_selector_positive_grammar(self):
        clone = self.f.repo
        for value in ('github.com/o/r', 'o/r', 'o-1/r_2.x', 'o/.github', 'ghe.example.com/o/r', 'o_emu/r'):
            for form in ('-R {}', '--repo {}', '--repo={}', '-R{}', '-R={}'):
                command = 'gh issue close 5 ' + form.format(value)
                with self.subTest(command=command):
                    self.assertEqual(self.paths(command, cwd=clone), [str(clone)])

    def test_gh_selector_naming_an_existing_local_directory_is_still_dropped(self):
        # gh never reads -R/--repo as a path: it parses [HOST/]OWNER/REPO, so a
        # same-named directory (or a symlink out of scope) under the cwd is not touched.
        clone = self.f.repo
        (clone / 'example/target').mkdir(parents=True)
        (clone / 'o').mkdir()
        os.symlink(self.payload, clone / 'o/r')
        for command in ('gh issue close 5 -R example/target', 'gh pr close 5 --repo=o/r'):
            with self.subTest(command=command):
                self.assertEqual(self.paths(command, cwd=clone), [str(clone)])
        self.task(clone, repo_root=clone, identity='gh1347')
        self.f.assertGate(0, 'gh pr close 5 --repo=o/r', cwd=clone)

    def test_gh_groups_without_repo_override_are_unchanged(self):
        clone = self.f.repo
        for command in ('gh repo edit --repo o/r --description x', 'gh repo delete o/r --yes',
                        'gh unmodelled-ext -R o/r', 'gh unmodelled-ext --repo=o/r', 'gh gist create o/r'):
            with self.subTest(command=command):
                self.assertIn(str(clone / 'o/r'), self.paths(command, cwd=clone))
        # Search is a released reader; it never reaches the mutation branch.
        for command in ('gh search issues --repo o/r bug', 'gh search prs -R o/r'):
            with self.subTest(command=command):
                self.assertTrue(fixture.r.action(command, str(clone)).get('read_only'))

    def test_gh_selector_after_a_bare_option_may_be_its_value(self):
        # pflag gives a value-taking flag the next token even when it starts
        # with '-': `--title -R o/r` makes o/r an upload asset, `-D -Ro/r`
        # downloads into ./-Ro/r. Such a selector is kept (fail closed).
        clone = self.f.repo
        (clone / 'o').mkdir()
        os.symlink(self.payload, clone / 'o/r')
        cases = {
            'gh release create v1 --title -R o/r': [str(self.payload)],
            'gh run download 9 -D -Ro/r': ['/r'],
            'gh issue close 5 -R -R o/r': [str(self.payload)],
            'gh pr close 5 -c -R o/r -R c/d': [str(self.payload)],
            'gh pr merge 5 --squash -Ro/r': ['/r'],
            'gh -R -R o/r issue close 5': [str(self.payload)],
        }
        for command, expected in cases.items():
            with self.subTest(command=command):
                paths = self.paths(command, cwd=clone)
                self.assertIn(str(clone), paths)
                for path in expected:
                    self.assertIn(path, paths)
        self.task(clone, repo_root=clone, identity='gh1347')
        for command in cases:
            with self.subTest(gate=command):
                self.f.assertGate(2, command, cwd=clone)
        # After an attached value or a dropped selector, a selector is dropped.
        for command in ('gh pr close 5 --comment=x -R o/r', 'gh pr close 5 -R c/d -R o/r', 'gh pr close 5 -Rc/d -Ro/r'):
            with self.subTest(command=command):
                self.assertEqual(self.paths(command, cwd=clone), [str(clone)])
                self.f.assertGate(0, command, cwd=clone)

    def test_gh_unowned_genuine_target_still_refuses(self):
        clone = self.f.repo
        self.task(clone, repo_root=clone, identity='gh1347')
        for command in ('gh release upload v1 ' + q(str(self.payload / 'x.tgz')) + ' -R example/target',
                        'gh issue close 5 -R ../escape',
                        'gh issue close 5 -R' + str(self.payload / 'x'),
                        'gh myext -R ' + q(str(self.payload / 'x'))):
            with self.subTest(command=command):
                self.f.assertGate(2, command, cwd=clone)

    # --- denial text -------------------------------------------------------

    def test_unscoped_denial_names_the_unowned_target(self):
        self.task(self.scope)
        result = self.f.assertGate(2, f'tar -xzf {q(str(self.scope / "src.tar.gz"))} -C {q(str(self.outside))}', cwd=self.payload)
        self.assertIn('Unscoped mutation:', result.stderr)
        self.assertIn('Unowned target: ' + str(self.outside), result.stderr)

    # --- gh free-text option values (#1355) ---------------------------------

    # cli/cli v2.104.0: in these subcommands the values below are free text or
    # other API strings that gh never reads as a local file, so the cwd stays
    # the only target. These are action-classification checks: they call
    # action() and the source gate; no real close, merge or release runs.
    GH_TEXT_FORMS = (
        # The issue's reproduction table.
        "gh pr close 5 --comment 'see a/b'",
        "gh pr close 5 --comment='see a/b'",
        "gh pr merge 5 --squash --subject 'fix: a/b handling'",
        "gh release create v1 --notes 'covers a/b'",
        "gh issue close 5 -c 'dup of other/repo#3'",
        'gh pr merge 5 -tfix/x',
        # Other spellings pflag accepts for the same values.
        'gh pr merge 5 -t=fix/x',
        'gh pr merge 5 -t fix/x',
        'gh pr merge 5 -dtfix/x',
        'gh pr merge 5 -sdt fix/x',
        "gh pr merge 5 --body '../../etc/x' -b /abs/y",
        'gh pr merge 5 -b/abs/y --subject=/abs/z',
        'gh pr close 5 -c ../outside/x --delete-branch',
        'gh pr close 5 -dc/abs/x',
        "gh issue close 5 --comment /etc/x --reason 'not planned'",
        'gh issue close 5 -r completed --duplicate-of other/repo#3',
        "gh issue reopen 5 -c 'see a/b'",
        'gh issue reopen 5 --comment=/abs/x',
        "gh pr reopen 5 -c '../x'",
        'gh pr merge 5 --author-email a/b@example.com -A c/d@example.com',
        "gh release create v1 --title 'v1/beta' --target release/1.x --notes-start-tag v0/x --discussion-category a/b",
        'gh release create v1 -tv1/x -n/abs/notes -dp --latest --generate-notes',
        # pflag hands a text flag the next token even when it starts with '-'.
        'gh pr close 5 -c -Ro/r',
        "gh pr merge 5 --body '-x a/b'",
        # Combined with #1347 repository selectors, in every position.
        "gh -R example/target pr close 5 -c 'a/b'",
        "gh pr -R example/target merge 5 -tfix/x",
        "gh issue close 5 -c 'a/b' -R example/target",
        "gh release create v1 --notes=a/b --repo=example/target",
    )

    def plain_dir(self):
        path = Path(os.path.realpath(tempfile.mkdtemp(prefix='gh1355-')))
        self.addCleanup(shutil.rmtree, path, True)
        return path

    def test_gh_text_values_are_not_path_targets(self):
        clone = self.f.repo
        for cwd in (self.plain_dir(), self.scope, clone):
            for command in self.GH_TEXT_FORMS:
                with self.subTest(cwd=str(cwd), command=command):
                    self.assertEqual(self.paths(command, cwd=cwd), [str(cwd)])

    def test_gh_text_values_pass_from_an_owned_cwd(self):
        clone = self.f.repo
        self.task(clone, repo_root=clone, identity='gh1355')
        for command in self.GH_TEXT_FORMS:
            with self.subTest(command=command):
                self.f.assertGate(0, command, cwd=clone)

    def test_gh_text_values_keep_the_owned_cwd_requirement(self):
        # A cwd no task owns still refuses, and the denial names only the cwd.
        self.task(self.scope)
        for cwd in (self.plain_dir(), self.f.repo):
            for command in self.GH_TEXT_FORMS[:6]:
                with self.subTest(cwd=str(cwd), command=command):
                    result = self.f.assertGate(2, command, cwd=cwd)
                    self.assertIn('Unowned target: ' + str(cwd), result.stderr)
                    self.assertNotIn('Unowned target: /x', result.stderr)
                    self.assertNotIn(str(cwd / 'see a'), result.stderr)

    def test_gh_path_values_and_operands_stay_targets(self):
        clone = self.f.repo
        outside = self.payload / 'x'
        cases = {
            # Path-valued flags of the modelled subcommands.
            'gh pr merge 5 --body-file notes/b.md': [clone / 'notes/b.md'],
            'gh pr merge 5 -F ' + q(str(outside)): [outside],
            'gh pr merge 5 --body-file=' + q(str(outside)): [outside],
            'gh pr merge 5 -s -F' + q(str(outside)): [outside],
            'gh release create v1 --notes-file ./n/x.md': [clone / 'n/x.md'],
            'gh release create v1 -F ../escape': [self.ws / 'escape'],
            # Release asset files are positional paths.
            "gh release create v1 dist/x.tgz --notes 'a/b'": [clone / 'dist/x.tgz'],
            "gh release create v1 --notes 'a/b' " + q(str(outside)): [outside],
            'gh release create v1 -n x ' + q(str(outside)) + '#label': [str(outside) + '#label'],
            # Download destinations of unmodelled subcommands.
            'gh release download v1 -D out/dir': [clone / 'out/dir'],
            'gh release download v1 --dir=out/dir': [clone / 'out/dir'],
            'gh release download v1 -O ' + q(str(outside)): [outside],
            'gh run download 9 -D out/dir': [clone / 'out/dir'],
            # Positionals are unchanged, including after a swallowed value.
            'gh pr merge feature/x --squash': [clone / 'feature/x'],
            'gh pr merge 5 --subject -R o/r': [clone / 'o/r'],
            'gh release create v1 --title -R o/r': [clone / 'o/r'],
        }
        for command, expected in cases.items():
            with self.subTest(command=command):
                paths = self.paths(command, cwd=clone)
                for path in expected:
                    self.assertIn(str(path), paths)
                self.assertIn(str(clone), paths)

    def test_gh_unowned_genuine_text_command_target_still_refuses(self):
        clone = self.f.repo
        outside = self.payload / 'x'
        self.task(clone, repo_root=clone, identity='gh1355')
        for command in ('gh pr merge 5 --squash --body-file ' + q(str(outside)) + " --subject 'a/b'",
                        "gh release create v1 --notes 'a/b' " + q(str(outside)),
                        "gh pr close 5 -c 'a/b' -- " + q(str(outside)),
                        'gh pr merge 5 --foo ' + q(str(outside)) + ' -tfix/x'):
            with self.subTest(command=command):
                self.f.assertGate(2, command, cwd=clone)

    @staticmethod
    def unmodelled(command):
        # Oracle for "unchanged": the same words under an unmodelled gh name.
        for group in ('gh pr ', 'gh issue ', 'gh release '):
            command = command.replace(group, 'gh unmodelled-ext ', 1)
        return command

    def test_gh_unknown_flags_and_shapes_keep_the_generic_model(self):
        clone = self.f.repo
        cases = {
            # An unknown flag may own the next token, whatever it looks like.
            "gh pr merge 5 --foo 'a/b'": [clone / 'a/b'],
            'gh pr merge 5 --foo -tfix/x': ['/x'],
            'gh pr merge 5 --foo --subject a/b': [clone / 'a/b'],
            'gh pr merge 5 -ztfix/x': ['/x'],
            'gh pr close 5 -zc a/b': [clone / 'a/b'],
            # After `--` every token is an operand.
            "gh pr close 5 -- --comment 'a/b'": [clone / 'a/b'],
            "gh pr close 5 --comment -- 'a/b'": [clone / 'a/b'],
            'gh pr close 5 -c x -- -c/abs/x': ['/abs/x'],
        }
        for command, expected in cases.items():
            with self.subTest(command=command):
                paths = self.paths(command, cwd=clone)
                self.assertEqual(paths, self.paths(self.unmodelled(command), cwd=clone))
                self.assertIn(str(clone), paths)
                for path in expected:
                    self.assertIn(str(path), paths)

    def test_gh_unmodelled_subcommands_and_executables_are_unchanged(self):
        clone = self.f.repo
        cases = {
            "gh pr create --title 'a/b'": [clone / 'a/b'],
            "gh release edit v1 --notes 'a/b'": [clone / 'a/b'],
            'gh pr ready 5 --comment a/b': [clone / 'a/b'],
            'gh unmodelled-ext close 5 --comment a/b': [clone / 'a/b'],
            '/usr/local/bin/gh pr close 5 -ctext/x': ['/x'],
            '/usr/local/bin/gh pr close 5 --comment a/b': [clone / 'a/b'],
        }
        for command, expected in cases.items():
            with self.subTest(command=command):
                paths = self.paths(command, cwd=clone)
                self.assertIn(str(clone), paths)
                for path in expected:
                    self.assertIn(str(path), paths)

    def test_gh_pinned_merge_policy_is_unchanged(self):
        # A head pin routes `gh pr merge` through the pinned merge-queue policy
        # before action() is consulted; dropping a text value changes nothing there.
        clone = self.f.repo
        commands = ('gh pr merge 5 --match-head-commit abc/def -tfix/x',
                    "gh pr merge 5 --squash --match-head-commit abc/def --subject 'a/b'")
        for command in commands:
            with self.subTest(command=command):
                self.assertEqual(self.paths(command, cwd=clone), [str(clone)])
        self.task(clone, repo_root=clone, identity='gh1355')
        for command in commands:
            with self.subTest(gate=command):
                result = self.f.assertGate(2, command, cwd=clone)
                self.assertIn('Pinned merge denied', result.stderr)

    def test_gh_text_values_keep_expansion_and_substitution_checks(self):
        clone = self.f.repo
        commands = ('gh pr close 5 --comment "see $(touch x)/b"',
                    'gh pr close 5 -c "a/`id`"',
                    'gh pr close 5 -c "$HOME/x"',
                    'gh pr merge 5 -t"$(id)"/x',
                    "gh pr close 5 -c '~/x'",
                    'gh issue close 5 --comment=~/x',
                    "gh pr close 5 -c 'a/b?'",
                    "gh release create v1 --notes 'a/*'")
        for command in commands:
            with self.subTest(command=command):
                self.assertTrue(fixture.r.action(command, str(clone)).get('error'))
        self.task(clone, repo_root=clone, identity='gh1355')
        for command in commands:
            with self.subTest(gate=command):
                self.f.assertGate(2, command, cwd=clone)

    def test_gh_text_values_never_authorize_another_repository(self):
        # Text that names an owned path is not a target, so it cannot lend that
        # path's ownership to an unowned cwd; genuine path flags still count.
        owned = self.f.repo
        other = self.plain_dir() / 'other'
        self.git('init', '-q', str(other))
        self.task(owned, repo_root=owned, identity='gh1355')
        for command in ('gh pr close 5 -c ' + q(str(owned / 'x')),
                        'gh pr merge 5 --squash --subject=' + q(str(owned)),
                        'gh pr merge 5 -t' + q(str(owned)),
                        "gh release create v1 --notes 'see " + str(owned) + "'"):
            with self.subTest(command=command):
                self.assertEqual(self.paths(command, cwd=other), [str(other)])
                result = self.f.assertGate(2, command, cwd=other)
                self.assertIn('Unowned target: ' + str(other), result.stderr)
        self.f.assertGate(2, 'gh pr merge 5 --body-file ' + q(str(other / 'b.md')), cwd=owned)


if __name__ == '__main__':
    unittest.main()
