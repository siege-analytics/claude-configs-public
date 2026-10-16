#!/usr/bin/env python3
"""Real build/Git release objects and disposable generation transitions."""
import copy
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('package_generation', ROOT / 'bin/package-generation.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE).decode().strip()


def commit(root):
    git(root, 'add', '--force', '-A'); git(root, 'commit', '-qm', 'Synthetic fixture')
    return git(root, 'rev-parse', 'HEAD')


class PackageGenerationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='package-generation-parent-')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.base = Path(cls.temporary.name); cls.parent = cls.base / 'parent'
        subprocess.run(['git', 'clone', '-q', '--no-local', str(ROOT), str(cls.parent)], check=True)
        git(cls.parent, 'checkout', '-q', '--detach', git(ROOT, 'rev-parse', 'HEAD'))
        git(cls.parent, 'config', 'core.hooksPath', '/dev/null')
        git(cls.parent, 'config', 'user.name', 'Generation fixture')
        git(cls.parent, 'config', 'user.email', 'fixture@example.invalid')
        cls.first = cls.release(cls.parent, 'v99.1.0', 'first')
        cls.next_parent = cls.base / 'next-parent'
        git(cls.parent, 'worktree', 'add', '-q', '-b', 'fixture-next', str(cls.next_parent))
        p = cls.next_parent / 'examples/composition/skills/coding/code-review/SKILL.md'
        p.write_text(p.read_text() + '\nParent upgrade marker.\n')
        commit(cls.next_parent)
        cls.second = cls.release(cls.next_parent, 'v99.2.0', 'second')

    @classmethod
    def release(cls, root, tag, label):
        source = git(root, 'rev-parse', 'HEAD'); outputs = cls.base / label; outputs.mkdir()
        (root / 'VERSION').write_text(tag[1:] + '\n')
        subprocess.run([sys.executable, 'scripts/ci/promote-unreleased.py', '--version', tag], cwd=root, check=True, stdout=subprocess.DEVNULL)
        result = subprocess.run([sys.executable, 'bin/build.py'], cwd=root, capture_output=True)
        if result.returncode:
            raise AssertionError(result.stdout.decode() + result.stderr.decode())
        for form in m.handoff.FORMS:
            output = outputs / ('release-' + form)
            git(root, 'worktree', 'add', '--orphan', '-b', label + '-' + form, str(output))
            shutil.copytree(root / 'dist' / form, output, dirs_exist_ok=True)
            commit(output)
        assets = outputs / 'assets'
        manifest = m.handoff.record(root, outputs, assets, 'synthetic-owner/configs', tag, source)
        git(root, 'restore', '--source=HEAD', '--', 'VERSION', 'CHANGELOG.md')
        return {'parent_root': root, 'assets': assets, 'release_digest': m.digest(manifest),
                'repository': 'synthetic-owner/configs', 'tag': tag, 'source': source}

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='package-generation-consumer-')
        self.addCleanup(temporary.cleanup); self.base_case = Path(temporary.name)
        self.consumer = self.base_case / 'consumer'; self.consumer.mkdir()
        git(self.consumer, 'init', '-q', '-b', 'main')
        git(self.consumer, 'config', 'core.hooksPath', '/dev/null')
        git(self.consumer, 'config', 'user.name', 'Consumer fixture')
        git(self.consumer, 'config', 'user.email', 'fixture@example.invalid')
        self.store = self.base_case / 'store'
        self.identity = 'github.example.invalid/synthetic-org/strict-release'
        shutil.copytree(self.parent / 'examples/composition/projects/strict-release', self.consumer / 'project')
        local = self.consumer / 'operator/local-skills/checks'; local.mkdir(parents=True)
        (local / 'SKILL.md').write_text('# Local checks\nRetained nested operator skill.\n')
        (self.consumer / 'settings.json').write_text(json.dumps({'theme': 'dark', 'customTool': {'timeout': 42}}))
        hook = self.consumer / 'compatibility/review.sh'; hook.parent.mkdir()
        origin_path = 'hooks/git/self-review.sh'
        origin = m.git_files(self.parent, self.first['source'], origin_path)[origin_path]
        hook.write_bytes(origin[0]); hook.chmod(0o755 if origin[1] else 0o644)
        contract, _, _ = m.effective.load_inputs(self.parent)
        self.declaration = {'schema_version': 1, 'identity': self.identity, 'project_source': 'project',
                            'preserve': ['operator/local-skills'], 'settings': 'settings.json',
                            'legacy_hooks': [{'path': 'compatibility/review.sh', 'sha256': m.handoff.digest(origin[0]),
                                              'origin_revision': self.first['source'], 'origin_path': origin_path,
                                              'contract_sha256': m.digest(contract)}]}
        self.revision = self.save_declaration()
        self.operations = [{'type': 'feature-merge', 'target_branch': 'develop'},
                           {'type': 'feature-merge', 'target_branch': 'main'},
                           {'type': 'ticket-commit', 'message': 'Repair #123'},
                           {'type': 'ticket-commit', 'message': 'Repair without evidence'},
                           {'type': 'review-procedure'}]

    def save_declaration(self):
        (self.consumer / 'siege-project.json').write_text(json.dumps(self.declaration))
        return commit(self.consumer)

    def stage(self, version=None, **kwargs):
        return m.stage(self.store, **(version or self.first), consumer_root=self.consumer,
                       consumer_revision=kwargs.pop('consumer_revision', self.revision),
                       identity=kwargs.pop('identity', self.identity), **kwargs)['generation']

    def select(self, candidate, rollback=False):
        observation = m.observe(self.store, candidate, self.operations, rollback=rollback)
        return m.select(self.store, candidate, expected_epoch=m.current(self.store, verify_payload=not rollback)['epoch'],
                        operations=self.operations, accepted_observation=observation['sha256'], rollback=rollback)

    def test_real_build_upgrade_preserves_declared_content_and_rollback_has_new_epoch(self):
        first = self.stage(); m.select(self.store, first, expected_epoch=0)
        snapshot = m.resolve(self.store); old_payload = Path(snapshot['payload'])
        second = self.stage(self.second)
        self.assertEqual(m.resolve(self.store), snapshot)
        observation = m.observe(self.store, second, self.operations)
        self.assertEqual(observation['differences'], [])
        self.assertEqual(observation['authorization_effect'], 'none')
        self.select(second)
        selected = m.resolve(self.store); payload = Path(selected['payload'])
        self.assertEqual(selected['epoch'], 2)
        for name in ('operator/local-skills/checks/SKILL.md', 'operator-settings.json', 'compatibility/review.sh', 'content/skills/strict-release--review/SKILL.md'):
            self.assertEqual((payload / name).read_bytes(), (old_payload / name).read_bytes())
        self.assertIn('Parent upgrade marker.', (payload / 'content/skills/code-review/SKILL.md').read_text())
        self.assertNotIn('Parent upgrade marker.', (old_payload / 'content/skills/code-review/SKILL.md').read_text())
        self.assertEqual(json.loads((payload / 'runtime/package.json').read_text())['source_commit'], self.second['source'])
        self.assertFalse((payload / 'content/skills/self-review/SKILL.md').exists())
        self.select(first, rollback=True)
        restored = m.resolve(self.store)
        self.assertEqual(restored['payload'], snapshot['payload'])
        self.assertEqual(restored['epoch'], 3)
        self.assertNotEqual(restored, snapshot)
        root, manifest = m.generation(self.store, first)
        ontology = m.module('generation_test_ontology', 'bin/ontology.py')
        bindings = m.effective.read_json(ROOT / 'catalog/package-generation-bindings.json')
        registry = m.effective.read_json(ROOT / 'catalog/ontology.json')
        self.assertGreater(ontology.validate_bindings(bindings, registry, root), 0)
        self.assertEqual(m.decisions(root, manifest, self.operations), observation['before'])

    def test_real_git_adapter_corpus_before_upgrade_after_upgrade_and_rollback(self):
        first = self.stage(); second = self.stage(self.second)
        m.select(self.store, first, expected_epoch=0)
        results = []
        for index, version in enumerate((self.first, self.second, self.first)):
            if index == 1:
                self.select(second)
            elif index == 2:
                self.select(first, rollback=True)
            selected = m.resolve(self.store)
            repo = self.base_case / f'operation-{index}'; repo.mkdir()
            git(repo, 'init', '-q', '-b', 'feature/generation')
            git(repo, 'config', 'core.hooksPath', '/dev/null')
            git(repo, 'config', 'user.name', 'Operation fixture')
            git(repo, 'config', 'user.email', 'fixture@example.invalid')
            git(repo, 'remote', 'add', 'origin', 'https://' + self.identity + '.git')
            shutil.copytree(Path(selected['payload']) / 'content', repo / '.pilot')
            base = commit(repo)
            (repo / 'change.md').write_text('Synthetic operation.\n')
            git(repo, 'add', '--force', 'change.md')
            git(repo, 'commit', '-qm', 'Operation #1004')

            def probe(target):
                result = subprocess.run([
                    sys.executable, str(version['parent_root'] / 'scripts/ci/protected-policy-range.py'),
                    '--trusted-root', str(version['parent_root']), '--trusted-revision', version['source'],
                    '--candidate-repo', str(repo), '--base', base, '--head', git(repo, 'rev-parse', 'HEAD'),
                    '--canonical-identity', self.identity, '--head-branch', 'feature/generation',
                    '--target-branch', target, '--installed-pilot-receipt', '.pilot/composition.json',
                ], capture_output=True, text=True, timeout=90)
                self.assertTrue(result.stdout, result.stderr)
                receipt = json.loads(result.stdout)
                return result.returncode, receipt

            code, allowed = probe('develop')
            self.assertEqual((code, allowed['state']), (0, 'eligible'))
            self.assertEqual(allowed['trusted']['revision'], version['source'])
            self.assertEqual(allowed['authorization'], 'protected-host-check-required')
            _, manifest = m.generation(self.store, selected['generation'])
            self.assertEqual(allowed['candidate']['installed_pilot']['parent_content_sha256'], manifest['parent_content_sha256'])
            branch_code, branch_denied = probe('main')
            self.assertEqual((branch_code, branch_denied['state']), (1, 'denied'))
            git(repo, 'commit', '--amend', '-qm', 'Operation without ticket')
            ticket_code, ticket_denied = probe('develop')
            self.assertEqual((ticket_code, ticket_denied['state']), (1, 'denied'))
            self.assertIn('lacks required', ticket_denied['diagnostic'])
            git(repo, 'commit', '--amend', '-qm', 'Operation #1004')
            (repo / '.pilot/skills/RESIDENT.md').write_text('Mixed installed guidance.\n')
            git(repo, 'add', '--force', '.pilot')
            git(repo, 'commit', '-qm', 'Changed installation #1004')
            drift_code, drift_denied = probe('develop')
            self.assertEqual((drift_code, drift_denied['state']), (1, 'denied'))
            self.assertIn('differs from trusted composition', drift_denied['diagnostic'])
            results.append((code, branch_code, ticket_code, drift_code))
            self.assertEqual(selected['epoch'], index + 1)
        self.assertEqual(results, [(0, 1, 1, 1)] * 3)

    def test_selected_project_replacement_extension_and_resident_survive(self):
        first = self.stage(); second = self.stage(self.second)
        for value in (first, second):
            root, manifest = m.generation(self.store, value)
            receipt = m.effective.read_json(root / 'payload/content/composition.json')
            selected = [entry['slug'] for entry in receipt['composition']['selected']]
            self.assertIn('strict-release--review', selected)
            self.assertIn('strict-release--checks', selected)
            self.assertIn('Notes', receipt['resident']['rendered'])
            self.assertEqual(manifest['ownership']['operator/local-skills/checks/SKILL.md'], 'operator')
            self.assertEqual(manifest['ownership']['compatibility/review.sh'], 'pinned-compatibility')

    def test_missing_changed_extra_and_mode_drift_are_not_verified(self):
        generation_id = self.stage(); root, manifest = m.generation(self.store, generation_id)
        path = root / 'payload/operator-settings.json'; original = path.read_bytes()
        path.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'drift'): m.generation(self.store, generation_id)
        path.write_bytes(original); path.chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'drift'): m.generation(self.store, generation_id)
        path.chmod(0o644); path.unlink()
        with self.assertRaisesRegex(ValueError, 'drift'): m.generation(self.store, generation_id)
        path.write_bytes(original); extra = root / 'payload/extra'; extra.write_text('drift')
        with self.assertRaisesRegex(ValueError, 'drift'): m.generation(self.store, generation_id)

    def test_wrong_manifest_archive_and_mixed_source_reject_before_selection(self):
        first = self.stage(); m.select(self.store, first, expected_epoch=0); before = m.resolve(self.store)
        for overrides in ({'release_digest': '0' * 64}, {'source': self.second['source']}):
            with self.assertRaises(ValueError): self.stage({**self.first, **overrides})
        assets = self.base_case / 'altered-assets'; shutil.copytree(self.first['assets'], assets)
        archive = next(assets.glob('craft-agent-*.tar.gz')); archive.write_bytes(archive.read_bytes() + b'wrong')
        with self.assertRaisesRegex(ValueError, 'archive digest'): self.stage({**self.first, 'assets': assets})
        self.assertEqual(m.resolve(self.store), before)

    def test_copied_hook_must_match_origin_digest_and_contract(self):
        for field, value in [('sha256', '0' * 64), ('contract_sha256', 'f' * 64), ('origin_path', 'README.md')]:
            with self.subTest(field=field):
                original = copy.deepcopy(self.declaration)
                self.declaration['legacy_hooks'][0][field] = value
                revision = self.save_declaration()
                with self.assertRaises(ValueError): self.stage(consumer_revision=revision)
                self.declaration = original
        self.assertIsNone(m.current(self.store))

    def test_undeclared_ambient_and_working_tree_changes_do_not_enter_generation(self):
        original = self.stage()
        (self.consumer / 'settings.json').write_text('{bad')
        (self.consumer / 'operator/secret.txt').write_text('not declared')
        self.assertEqual(self.stage(), original)
        root, _ = m.generation(self.store, original)
        self.assertFalse((root / 'payload/operator/secret.txt').exists())

    def test_interrupted_staging_or_selection_preserves_old_coherent_generation(self):
        first = self.stage(); m.select(self.store, first, expected_epoch=0); before = m.resolve(self.store)
        with patch.object(m.composition, 'package', side_effect=OSError('injected staging failure')):
            with self.assertRaisesRegex(OSError, 'staging'): self.stage(self.second)
        second = self.stage(self.second)
        with patch.object(m.os, 'replace', side_effect=OSError('injected selection failure')):
            with self.assertRaisesRegex(OSError, 'selection'): self.select(second)
        self.assertEqual(m.resolve(self.store), before)
        self.assertFalse(list(self.store.glob('.stage-*')))
        self.assertFalse(list(self.store.glob('.selection-*')))

    def test_stale_observation_and_epoch_cannot_select(self):
        first = self.stage(); m.select(self.store, first, expected_epoch=0); second = self.stage(self.second)
        observation = m.observe(self.store, second, self.operations)
        with self.assertRaisesRegex(ValueError, 'exact observation'):
            m.select(self.store, second, expected_epoch=1, operations=self.operations, accepted_observation='0' * 64)
        self.select(second)
        with self.assertRaisesRegex(ValueError, 'stale selection'):
            m.select(self.store, first, expected_epoch=1, operations=self.operations, accepted_observation=observation['sha256'])

    def test_rollback_rejects_drift_and_nonprevious_generation(self):
        first = self.stage(); m.select(self.store, first, expected_epoch=0); second = self.stage(self.second); self.select(second)
        path = self.store / 'generations' / first / 'payload/operator-settings.json'; path.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'drift'): self.select(first, rollback=True)
        self.assertEqual(m.resolve(self.store)['generation'], second)

    def test_damaged_active_generation_can_only_recover_to_verified_previous(self):
        first = self.stage(); m.select(self.store, first, expected_epoch=0)
        second = self.stage(self.second); self.select(second)
        path = self.store / 'generations' / second / 'payload/runtime/package.json'
        path.write_text('{damaged')
        with self.assertRaisesRegex(ValueError, 'drift'): m.resolve(self.store)
        with self.assertRaisesRegex(ValueError, 'drift'): m.observe(self.store, first, self.operations)
        observation = m.observe(self.store, first, self.operations, rollback=True)
        self.assertEqual(observation['previous_verification']['state'], 'unknown')
        self.assertEqual(observation['differences'], list(range(len(self.operations))))
        restored = self.select(first, rollback=True)
        self.assertEqual(restored['epoch'], 3)
        self.assertEqual(m.resolve(self.store)['generation'], first)
        # Recovery does not bless the damaged set as a valid rollback target.
        with self.assertRaisesRegex(ValueError, 'drift'):
            m.observe(self.store, second, self.operations, rollback=True)

    def test_generation_manifest_tampering_and_symlinks_reject(self):
        value = self.stage(); root, manifest = m.generation(self.store, value)
        changed = dict(manifest, effective_policy_sha256='0' * 64)
        (root / 'generation.json').write_bytes(m.canonical(changed))
        with self.assertRaisesRegex(ValueError, 'selected ID'): m.generation(self.store, value)
        (root / 'generation.json').write_bytes(m.canonical(manifest))
        path = root / 'payload/operator-settings.json'; path.unlink(); path.symlink_to(self.consumer / 'settings.json')
        with self.assertRaisesRegex(ValueError, 'symlink'): m.generation(self.store, value)

    def test_wrong_identity_preserve_shadow_and_unmapped_heading_reject(self):
        with self.assertRaises(ValueError): self.stage(identity='github.example.invalid/synthetic-org/synthetic-trunk')
        self.declaration['preserve'] = ['runtime']
        with self.assertRaisesRegex(ValueError, 'operator/'):
            self.stage(consumer_revision=self.save_declaration())
        self.declaration['preserve'] = []
        p = self.consumer / 'project/CLAUDE.md'; p.write_text(p.read_text() + '\n## Unexpected\nUnmapped.\n')
        with self.assertRaises(ValueError): self.stage(consumer_revision=self.save_declaration())

    def test_concurrent_selections_require_the_same_epoch(self):
        first = self.stage(); m.select(self.store, first, expected_epoch=0); second = self.stage(self.second)
        observation = m.observe(self.store, second, self.operations)
        def select_once():
            try:
                return m.select(self.store, second, expected_epoch=1, operations=self.operations,
                                accepted_observation=observation['sha256'])['epoch']
            except ValueError as error:
                return str(error)
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(lambda _: select_once(), range(2)))
        self.assertCountEqual(outcomes, [2, 'stale selection epoch'])
        self.assertEqual(m.resolve(self.store)['generation'], second)

    def test_rollback_cannot_choose_an_unrelated_staged_generation(self):
        first = self.stage(); m.select(self.store, first, expected_epoch=0); second = self.stage(self.second); self.select(second)
        p = self.consumer / 'operator/local-skills/checks/SKILL.md'; p.write_text('Different operator generation.\n')
        third = self.stage(consumer_revision=commit(self.consumer))
        with self.assertRaisesRegex(ValueError, 'exact previous'):
            self.select(third, rollback=True)
        self.assertEqual(m.resolve(self.store)['generation'], second)

    def test_different_composition_tool_bytes_reject_before_generation_write(self):
        original = m.ROOT
        tools = self.base_case / 'wrong-tools'; (tools / 'bin').mkdir(parents=True)
        (tools / 'bin/compose-project.py').write_text('different implementation')
        with patch.object(m, 'ROOT', tools):
            with self.assertRaisesRegex(ValueError, 'matching trusted composition tools'):
                self.stage()
        self.assertIsNone(m.current(self.store))
        self.assertEqual(m.ROOT, original)

    def test_new_state_schema_is_not_implicitly_accepted(self):
        value = self.stage(); root, manifest = m.generation(self.store, value)
        changed = dict(manifest, state_schema_version=2)
        new_id = m.digest(changed); replacement = root.parent / new_id
        shutil.copytree(root, replacement)
        (replacement / 'generation.json').write_bytes(m.canonical(changed))
        with self.assertRaisesRegex(ValueError, 'unsupported generation/state schema'):
            m.select(self.store, new_id, expected_epoch=0)
        self.assertIsNone(m.current(self.store))

    def test_cli_resolve_returns_one_complete_generation_without_host_authority(self):
        value = self.stage(); m.select(self.store, value, expected_epoch=0)
        result = subprocess.run([sys.executable, str(ROOT / 'bin/package-generation.py'), '--store', str(self.store), 'resolve'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = json.loads(result.stdout)
        self.assertEqual(result['generation'], value)
        self.assertEqual(result['authorization_effect'], 'none')
        payload = Path(result['payload'])
        self.assertTrue((payload / 'runtime/hooks').is_dir())
        self.assertTrue((payload / 'content/skills/RESIDENT.md').is_file())


if __name__ == '__main__':
    unittest.main()
