#!/usr/bin/env python3
"""Exercise release handoff against real disposable Git objects and remotes."""
import copy
import gzip
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('handoff', ROOT / 'scripts/ci/release-handoff.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class ReleaseHandoffTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='release-handoff-')
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.root = self.base / 'source'; self.root.mkdir()
        self.remote = self.base / 'remote.git'
        self.assets = self.base / 'assets'
        self.repository = 'synthetic-owner/configs'
        self.tag = 'v1.2.3'
        subprocess.run(['git', 'init', '-q', '--bare', str(self.remote)], check=True)
        m.git(self.root, 'init', '-q', '-b', 'main')
        m.git(self.root, 'config', 'user.name', 'Release fixture')
        m.git(self.root, 'config', 'user.email', 'fixture@example.invalid')
        m.git(self.root, 'remote', 'add', 'origin', str(self.remote))
        (self.root / 'VERSION').write_text('1.2.3\n')
        (self.root / 'CHANGELOG.md').write_text('# Changes\n\n## [Unreleased]\n\n- Fixture change.\n')
        self.commit(self.root)
        self.source = m.revision(self.root, 'HEAD')
        m.git(self.root, 'push', '-q', 'origin', 'main')
        subprocess.run([sys.executable, str(ROOT / 'scripts/ci/promote-unreleased.py'), '--changelog', str(self.root / 'CHANGELOG.md'), '--version', self.tag, '--date', '2026-10-16'], check=True, stdout=subprocess.DEVNULL)
        for form in m.FORMS:
            out = self.base / ('release-' + form)
            m.git(self.root, 'worktree', 'add', '-q', '-b', 'release/' + form, str(out), self.source)
            (out / 'CHANGELOG.md').write_bytes((self.root / 'CHANGELOG.md').read_bytes())
            (out / 'content.md').write_text(form + '\n')
            if form in ('claude-code', 'craft-agent'):
                (out / 'package.json').write_text(json.dumps({'package': form, 'version': '1.2.3', 'source_commit': self.source}))
            self.commit(out)
        self.data = m.record(self.root, self.base, self.assets, self.repository, self.tag, self.source)

    def commit(self, root):
        m.git(root, 'add', '--force', '-A')
        m.git(root, 'commit', '-qm', 'fixture')

    def verify(self, data=None):
        return m.verify(self.root, data or self.data, self.assets, self.repository, self.tag, self.source)

    def publish(self, data=None, **kwargs):
        return m.publish(self.root, data or self.data, self.assets, self.repository, self.tag, self.source, **kwargs)

    def refs(self):
        return m.git(self.root, 'ls-remote', 'origin')

    def test_producer_publishes_all_exact_refs_and_repair_is_idempotent(self):
        self.publish(branches=True)
        before = self.refs()
        self.publish(fetch=True)
        self.assertEqual(self.refs(), before)
        expected = {self.tag: self.source, **{self.tag + '-' + form: self.data['outputs'][form]['commit'] for form in m.FORMS}}
        self.assertEqual(m.remote_tags(self.root, expected), expected)
        for form in m.FORMS:
            self.assertIn(('refs/heads/release/' + form).encode(), before)

    def test_moved_branch_cannot_change_repair_target(self):
        self.publish(branches=True)
        form = 'flat'; expected = self.data['outputs'][form]['commit']
        out = self.base / ('release-' + form)
        (out / 'content.md').write_text('later unrelated release\n'); self.commit(out)
        later = m.revision(out, 'HEAD')
        m.git(self.root, 'push', '-q', 'origin', f'{later}:refs/heads/release/{form}', ':refs/tags/' + self.tag + '-' + form)
        self.publish(fetch=True)
        self.assertEqual(m.remote_tags(self.root, [self.tag + '-flat'])[self.tag + '-flat'], expected)
        self.assertIn(later.encode(), self.refs())

    def test_wrong_existing_tag_rejects_before_any_missing_tag_is_created(self):
        m.git(self.root, 'push', '-q', 'origin', self.source + ':refs/tags/' + self.tag, self.source + ':refs/tags/' + self.tag + '-flat')
        before = self.refs()
        with self.assertRaisesRegex(ValueError, 'existing tag'):
            self.publish(branches=True)
        self.assertEqual(self.refs(), before)

    def test_matching_annotated_tag_is_preserved(self):
        name = self.tag + '-flat'; target = self.data['outputs']['flat']['commit']
        m.git(self.root, 'tag', '-a', name, target, '-m', 'existing exact tag')
        m.git(self.root, 'push', '-q', 'origin', 'refs/tags/' + name)
        oid = m.revision(self.root, 'refs/tags/' + name)
        self.publish(branches=True)
        self.assertIn(oid.encode(), self.refs())

    def test_manifest_identity_schema_and_object_mutations_fail_without_remote_changes(self):
        mutations = [
            ('schema_version', 2), ('repository', 'foreign/repo'), ('tag', 'v9.9.9'),
            ('source_commit', '0' * 40), ('source_tree', '0' * 40), ('changelog_sha256', '0' * 64),
        ]
        before = self.refs()
        for key, value in mutations:
            data = copy.deepcopy(self.data); data[key] = value
            with self.subTest(key=key), self.assertRaises((ValueError, subprocess.CalledProcessError)):
                self.publish(data, branches=True)
            self.assertEqual(self.refs(), before)
        for key, value in (('commit', '0' * 40), ('tree', '0' * 40), ('archive', '../private'), ('sha256', '0' * 64)):
            data = copy.deepcopy(self.data); data['outputs']['flat'][key] = value
            with self.subTest(key=key), self.assertRaises((ValueError, subprocess.CalledProcessError)):
                self.publish(data, branches=True)
            self.assertEqual(self.refs(), before)
        data = copy.deepcopy(self.data); del data['outputs']['flat']
        with self.assertRaisesRegex(ValueError, 'invalid fields'):
            self.publish(data, branches=True)

    def test_missing_and_corrupt_archives_cannot_publish(self):
        archive = self.assets / self.data['outputs']['flat']['archive']
        original = archive.read_bytes(); before = self.refs()
        archive.unlink()
        with self.assertRaisesRegex(ValueError, 'missing archive'): self.publish(branches=True)
        archive.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'digest mismatch'): self.publish(branches=True)
        archive.write_bytes(original)
        self.assertEqual(self.refs(), before)

    def test_archive_digest_alone_does_not_hide_wrong_commit_content(self):
        data = copy.deepcopy(self.data)
        archive = self.assets / data['outputs']['flat']['archive']
        raw = gzip.compress(b'wrong tar content', mtime=0); archive.write_bytes(raw)
        data['outputs']['flat']['sha256'] = m.digest(raw)
        with self.assertRaisesRegex(ValueError, 'does not represent'): self.publish(data, branches=True)

    def test_repair_requires_source_tag_and_record_refuses_overwrite(self):
        with self.assertRaisesRegex(ValueError, 'existing source tag'): self.publish()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            m.record(self.root, self.base, self.assets, self.repository, self.tag, self.source)

    def test_stale_changelog_and_package_metadata_reject_before_publication(self):
        for variant in ('changelog', 'version', 'source'):
            out = self.base / 'release-craft-agent'
            if variant == 'changelog':
                (out / 'CHANGELOG.md').write_text('## [Unreleased]\n- stale\n')
            else:
                (out / 'CHANGELOG.md').write_bytes((self.root / 'CHANGELOG.md').read_bytes())
                package = {'package': 'craft-agent', 'version': '1.2.3', 'source_commit': self.source}
                package['version' if variant == 'version' else 'source_commit'] = 'wrong'
                (out / 'package.json').write_text(json.dumps(package))
            self.commit(out)
            with self.subTest(variant=variant), self.assertRaisesRegex(ValueError, 'changelog|version|source'):
                m.record(self.root, self.base, self.base / ('bad-' + variant), self.repository, self.tag, self.source)
            self.assertFalse((self.base / ('bad-' + variant) / m.MANIFEST).exists())

    def test_cli_reports_missing_manifest_as_failure(self):
        process = subprocess.run([sys.executable, str(ROOT / 'scripts/ci/release-handoff.py'), 'publish', '--root', str(self.root), '--assets', str(self.base / 'absent'), '--repository', self.repository, '--tag', self.tag, '--source', self.source], capture_output=True, text=True)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn('release handoff failed', process.stderr)

    def test_server_rejection_keeps_entire_remote_ref_set_unchanged(self):
        hook = self.remote / 'hooks/pre-receive'
        hook.write_text('#!/bin/sh\nwhile read old new ref; do\n case "$ref" in *-craft-agent) exit 1;; esac\ndone\n')
        hook.chmod(0o755)
        before = self.refs()
        with self.assertRaises(subprocess.CalledProcessError): self.publish(branches=True)
        self.assertEqual(self.refs(), before)

    def test_fresh_source_only_clone_fetches_exact_output_objects(self):
        self.publish(branches=True)
        # Local clones can copy unreachable objects; explicitly ask Git to use
        # transport negotiation so this check starts without consumer objects.
        remote_url = 'file://' + str(self.remote)
        isolated = self.base / 'isolated-repair'
        subprocess.run(['git', 'clone', '-q', '--single-branch', '--branch', 'main', '--no-tags', remote_url, str(isolated)], check=True)
        with self.assertRaises(subprocess.CalledProcessError):
            m.revision(isolated, self.data['outputs']['flat']['commit'] + '^{commit}')
        m.publish(isolated, self.data, self.assets, self.repository, self.tag, self.source, fetch=True)

    def test_git_export_attributes_cannot_hide_archive_version_metadata(self):
        out = self.base / 'release-flat'
        (out / '.gitattributes').write_text('CHANGELOG.md export-ignore\n')
        self.commit(out)
        with self.assertRaisesRegex(ValueError, 'archive missing release metadata'):
            m.record(self.root, self.base, self.base / 'export-assets', self.repository, self.tag, self.source)
        self.assertFalse((self.base / 'export-assets' / m.MANIFEST).exists())

    def test_uncommitted_source_changes_cannot_claim_the_recorded_source(self):
        (self.root / 'VERSION').write_text('1.2.3\n')
        (self.root / 'other.py').write_text('changed input\n')
        with self.assertRaisesRegex(ValueError, 'untracked input'):
            m.record(self.root, self.base, self.base / 'dirty-assets', self.repository, self.tag, self.source)
        m.git(self.root, 'add', 'other.py')
        with self.assertRaisesRegex(ValueError, 'uncommitted changes'):
            m.record(self.root, self.base, self.base / 'dirty-assets', self.repository, self.tag, self.source)

    def test_workflow_prepares_before_build_and_repairs_only_recorded_outputs(self):
        workflow = (ROOT / '.github/workflows/build-and-publish.yml').read_text()
        publish = workflow[workflow.index('  publish:\n'):]
        self.assertLess(publish.index('promote-unreleased.py'), publish.index('run: python3 bin/build.py'))
        self.assertLess(publish.index('release-handoff.py record'), publish.index('release-handoff.py publish'))
        self.assertLess(publish.index('release-handoff.py publish'), publish.index('gh release create'))
        self.assertEqual(publish.count('promote-unreleased.py'), 1)
        self.assertNotIn('git push origin release/', publish)
        repair = (ROOT / '.github/workflows/publish-consumption-tags.yml').read_text()
        self.assertNotIn('ls-remote', repair)
        self.assertIn('release-handoff.py publish --fetch', repair)
        self.assertIn('--pattern release-manifest.json', repair)


if __name__ == '__main__': unittest.main(verbosity=2)
