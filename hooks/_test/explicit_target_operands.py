#!/usr/bin/env python3
"""Explicit tar/venv write destinations and own-session data/ scratch tiers (#1152).

A fully modelled `tar` or `python -m venv` invocation writes only under its
explicit destination, so that destination replaces the cwd as the mutation
target. Every other shape keeps the generic model, where the cwd stays a
target. A target in the current session's own data/ with no tracked files
floors at Tier A; tracked content and clones keep normal classification.
"""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile
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
        # content, so it keeps baseline B (needs investigation and pre-mortem).
        self.task(self.scope, tier='A', artifacts=False)
        for command in ('make install', './run.sh', 'tar -xzf src.tar.gz && make',
                        'python3 -m venv --without-pip v4'):
            with self.subTest(command=command):
                tier = self.tier(command, cwd=self.scope)
                self.assertEqual(tier['floor'], 'B', tier)
                self.assertFalse(any('own-session data scratch' in r for r in tier['reasons']), tier)
                self.f.assertGate(2, command, cwd=self.scope)

    def test_tracked_content_under_data_keeps_normal_classification(self):
        self.task(self.scope, tier='A', artifacts=False)
        (self.scope / 'tool.py').write_text('x = 1\n')
        self.git('-C', str(self.ws), 'add', '-f', 'sessions/one/data/extract/tool.py')
        tier = self.tier(f'cd {q(str(self.scope))} && tar -xzf src.tar.gz')
        self.assertEqual(tier['floor'], 'B', tier)
        self.f.assertGate(2, f'cd {q(str(self.scope))} && tar -xzf src.tar.gz', cwd=self.outside)

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

    # --- denial text -------------------------------------------------------

    def test_unscoped_denial_names_the_unowned_target(self):
        self.task(self.scope)
        result = self.f.assertGate(2, f'tar -xzf {q(str(self.scope / "src.tar.gz"))} -C {q(str(self.outside))}', cwd=self.payload)
        self.assertIn('Unscoped mutation:', result.stderr)
        self.assertIn('Unowned target: ' + str(self.outside), result.stderr)


if __name__ == '__main__':
    unittest.main()
