#!/usr/bin/env python3
"""Real selected normal builds from immutable, physically independent sources."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


selected = module('tested_selection', 'bin/package_selection.py')
fixtures = module('composition_fixtures', 'bin/_test/selected_composition_test.py')


class PackageSelectionTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.SelectedCompositionTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.source = self.fixture.source
        self.output = self.fixture.output
        for name in selected.SCAFFOLD_FILES:
            destination = self.source / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, destination)
        self.descriptors = []
        self.seal()

    def seal(self):
        revision = self.fixture.fixture.commit()
        self.selection = {
            'schema_version': 1, 'identity': self.fixture.identity, 'content_root': '.',
            'scaffold': selected.describe_component(self.source, 'scaffold', revision, sorted(selected.SCAFFOLD_FILES)),
            'project': selected.describe_component(self.source, 'independent', revision, ['projects/independent']),
            'bundles': [
                {'component': selected.describe_component(self.source, ident, revision, sorted([descriptor, root])),
                 'descriptor': descriptor}
                for ident, descriptor, root in self.descriptors
            ],
            'workflow_profile': 'independent', 'content': copy.deepcopy(self.fixture.selection),
            'backend': 'resolver-only', 'required_capabilities': [],
        }

    def bundle(self, ident='siege', *, profiles=(), qualified=True, skill='format'):
        self.fixture.publisher(ident, qualified=qualified, skill=skill)
        publisher = self.fixture.selection['publishers'][-1]
        descriptor = f'bundles/{ident}/bundle.json'
        self.fixture.fixture.write_json(descriptor, {'schema_version': 1, 'id': ident,
            'publisher': publisher, 'requires_profiles': list(profiles)})
        self.descriptors.append((ident, descriptor, publisher['skills_root']))
        self.seal()

    def build(self, *, selection=None, extra=(), copied=True):
        value = self.selection if selection is None else selection
        declaration = self.source / 'selected-build.json'
        declaration.write_text(json.dumps(value))
        command = [sys.executable, '-B', str((self.source if copied else ROOT) / 'bin/build.py'),
                   '--selection', str(declaration), '--source', str(self.source), '--dist', str(self.output),
                   '--policy-root', str(self.source), '--policy-inputs', str(self.fixture.fixture.source),
                   '--policy-inputs-sha256', self.fixture.fixture.pin, *extra]
        return subprocess.run(command, cwd='/', text=True, capture_output=True, timeout=60)

    def assert_rejected(self, result, diagnostic):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(diagnostic, result.stderr)
        self.assertEqual(json.loads(result.stderr)['authorization_effect'], 'none')
        self.assertFalse(self.output.exists())

    def test_normal_build_and_resolver_with_all_siege_input_locations_absent(self):
        for name in ('skills', 'bundles', 'hooks', '.githooks', 'examples', 'craft-agent',
                     'catalog/gate-contracts.json', 'catalog/effective-policy.json',
                     'catalog/effective-policy-selection.json', 'catalog/review-risk-policy.json'):
            self.assertFalse((self.source / name).exists(), name)
        result = self.build()
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt['authorization_effect'], 'none')
        self.assertEqual(receipt['registration_state'], 'unsupported-unverified')
        self.assertEqual(receipt['observed_capabilities'], [])
        self.assertEqual([c['role'] for c in receipt['components']], ['scaffold', 'project'])
        self.assertNotEqual(receipt['components'][0]['sha256'], receipt['components'][1]['sha256'])
        self.assertEqual(receipt['components'][0]['revision'], receipt['components'][1]['revision'])
        for layout in ('nested', 'flat'):
            runtime = self.output / layout
            run = subprocess.run([sys.executable, '-B', str(runtime / 'bin/resolve-load-set.py'),
                '--prompt', 'inspect changes', '--repo', self.fixture.identity, '--render-hook', '--mode', 'on'],
                cwd='/', text=True, capture_output=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn('PROJECT_RESIDENT', run.stdout)
            self.assertNotIn('Siege', run.stdout)
            self.assertNotIn('ticket required', run.stdout)
            self.assertFalse((runtime / 'hooks').exists())
            self.assertFalse((runtime / '.githooks').exists())
            self.assertFalse((runtime / 'skills/KERNEL.md').exists())
            inventory = json.loads((runtime / 'catalog/skills-inventory.json').read_text())
            self.assertEqual([item['slug'] for item in inventory['items']], ['independent--review'])
            self.assertEqual(json.loads((runtime / 'selected-build.json').read_text()), receipt)
            self.assertEqual({p.relative_to(runtime).as_posix() for p in runtime.rglob('*') if p.is_file()}, {
                'bin/resolve-load-set.py', 'bin/procedure_composition.py', 'composition.json', 'selected-build.json',
                'catalog/resolver-manifest.json', 'catalog/skills-inventory.json', 'skills/RESIDENT.md',
                'skills/RULES_BUNDLE.md', 'skills/independent--review/SKILL.md'})

    def test_synthetic_siege_content_selection_does_not_adopt_its_workflow(self):
        self.bundle()
        result = self.build()
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt['workflow_profile'], 'independent')
        values = receipt['policy']['values']
        self.assertFalse(values['ticket-requirement']['required'])
        self.assertEqual(values['branch-policy']['integration_branch'], 'trunk')
        self.assertEqual(values['review-procedure-binding']['procedure'], 'independent--review')
        self.assertIn('SIEGE_CONTENT_ONLY', (self.output / 'flat/skills/siege--format/SKILL.md').read_text())
        self.assertEqual(receipt['components'][-1]['role'], 'bundle')
        self.assertEqual(len({c['sha256'] for c in receipt['components']}), 3)

    def test_profile_dependency_never_silently_adopts(self):
        self.bundle(profiles=['strict-release'])
        self.assert_rejected(self.build(), 'unmet workflow profile dependency: strict-release')
        self.selection['workflow_profile'] = 'strict-release'
        self.assert_rejected(self.build(), 'differs from independently approved adoption')

    def test_missing_adapter_and_wrong_backend_reject(self):
        self.selection['required_capabilities'] = ['native-git']
        self.assert_rejected(self.build(), 'missing implemented registration adapter: native-git')
        self.selection['required_capabilities'] = []
        self.selection['backend'] = 'pi'
        self.assert_rejected(self.build(), 'unsupported selected build backend')

    def test_candidate_cannot_supply_or_replace_policy_pin(self):
        self.selection['policy_inputs_sha256'] = self.fixture.fixture.pin
        self.assert_rejected(self.build(), 'selected build: fields differ')
        del self.selection['policy_inputs_sha256']
        self.assert_rejected(self.build(extra=['--policy-inputs-sha256', '0' * 64]), 'registration digest differs')
        self.selection['workflow_profile'] = None
        self.assert_rejected(self.build(), 'differs from independently approved adoption')

    def test_changed_committed_bundle_bytes_reject_old_digest(self):
        self.bundle()
        p = self.source / 'bundles/siege/skills/format/SKILL.md'
        p.write_text(p.read_text() + '\nChanged bundle.\n')
        self.selection['bundles'][0]['component']['revision'] = self.fixture.fixture.commit()
        self.assert_rejected(self.build(), 'component digest differs from selected bytes')

    def test_dirty_unselected_bytes_cannot_change_pinned_build(self):
        self.bundle()
        (self.source / 'bundles/siege/skills/format/SKILL.md').write_text('DIRTY_UNSELECTED_BYTES')
        result = self.build()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('DIRTY_UNSELECTED_BYTES', (self.output / 'flat/skills/siege--format/SKILL.md').read_text())

    def test_wrong_scaffold_bytes_reject_even_with_resealed_component(self):
        p = self.source / 'bin/resolve-load-set.py'
        p.write_text(p.read_text() + '\n# Changed evaluator tool.\n')
        self.seal()
        self.assert_rejected(self.build(copied=False), 'run matching selected scaffold tools')

    def test_duplicate_bundles_and_ambiguous_names_reject(self):
        self.bundle('first', qualified=False)
        self.selection['bundles'].append(copy.deepcopy(self.selection['bundles'][0]))
        self.assert_rejected(self.build(), 'duplicate bundle identity')
        self.bundle('second', qualified=False)
        self.assert_rejected(self.build(), 'duplicate qualified skill format')

    def test_alias_and_prerequisite_cycles_reject_before_publication(self):
        self.selection['content']['prerequisites'] = {'independent--review': ['independent--review']}
        self.assert_rejected(self.build(), 'cycle')
        self.selection['content']['prerequisites'] = {}
        config = self.source / 'projects/independent/composition.json'
        value = json.loads(config.read_text())
        value['bindings']['aliases'] = [{'alias': 'one', 'target': 'two', 'source': 'project'},
                                       {'alias': 'two', 'target': 'one', 'source': 'project'}]
        config.write_text(json.dumps(value))
        self.seal()
        self.assert_rejected(self.build(), 'cycle')

    def test_unselected_publisher_and_foreign_project_reject(self):
        self.selection['content']['publishers'] = [{'id': 'hidden', 'skills_root': 'hidden', 'qualified': True}]
        self.assert_rejected(self.build(), 'publishers differ from pinned bundle declarations')
        self.selection['content']['publishers'] = []
        self.selection['project']['paths'] = ['projects/foreign']
        self.assert_rejected(self.build(), 'exactly the selected project directory')

    def test_symlink_git_sources_and_path_traversal_reject(self):
        self.bundle()
        p = self.source / 'bundles/siege/skills/format/SKILL.md'
        p.unlink()
        p.symlink_to(self.source / 'projects/independent/skills/review/SKILL.md')
        revision = self.fixture.fixture.commit()
        self.selection['bundles'][0]['component']['revision'] = revision
        self.assert_rejected(self.build(), 'unsupported Git input')
        self.selection['scaffold']['paths'] = ['../outside']
        self.assert_rejected(self.build(), 'unsafe path')

    def test_interrupted_composition_and_publication_leave_no_package(self):
        kwargs = dict(policy_root=self.source, policy_source=self.fixture.fixture.source,
                      policy_sha256=self.fixture.fixture.pin)
        with patch.object(selected.os, 'rename', side_effect=OSError('interrupted publication')):
            with self.assertRaisesRegex(OSError, 'interrupted publication'):
                selected.build(self.source, self.output, self.selection, **kwargs)
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.output.parent.glob('.selected-build-*')), [])
        self.selection['content']['resident_blocks'][0]['content'] = '[skill:missing]'
        self.assert_rejected(self.build(), 'missing')
        self.assertEqual(list(self.output.parent.glob('.selected-build-*')), [])

    def test_existing_output_is_never_overwritten_and_check_has_no_output(self):
        result = self.build(extra=['--check'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.output.exists())
        self.output.mkdir()
        sentinel = self.output / 'keep'
        sentinel.write_text('operator bytes')
        result = self.build()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('already exists', result.stderr)
        self.assertEqual(sentinel.read_text(), 'operator bytes')

    def test_legacy_installer_cannot_register_composition_only_output(self):
        result = self.build()
        self.assertEqual(result.returncode, 0, result.stderr)
        settings = self.output.parent / 'operator-settings.json'
        settings.write_text('{"theme":"operator-customization"}\n')
        before = settings.read_bytes()
        prior_hooks = self.fixture.fixture.git('config', '--local', '--get', 'core.hooksPath')
        result = subprocess.run(['bash', str(ROOT / 'bin/install-hooks.sh'),
            '--hooks-root', str(self.output / 'flat'), '--target-file', str(settings),
            '--git-repo', str(self.source)], capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('settings-snippet.json', result.stderr)
        self.assertEqual(settings.read_bytes(), before)
        self.assertEqual(self.fixture.fixture.git('config', '--local', '--get', 'core.hooksPath'), prior_hooks)

    def test_malformed_components_and_duplicate_json_keys_have_non_authorizing_diagnostics(self):
        for change in ({'project': None}, {'identity': None}, {'scaffold': []},
                       {'bundles': [None]}, {'required_capabilities': [None]}, {'content_root': '../outside'}):
            with self.subTest(change=change):
                result = self.build(selection={**self.selection, **change})
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertEqual(json.loads(result.stderr)['authorization_effect'], 'none')
                self.assertFalse(self.output.exists())
        invalid = self.source / 'invalid-selection.json'
        invalid.write_text('{"schema_version":1,"schema_version":1}')
        self.assert_rejected(self.build(extra=['--selection', str(invalid)]), 'duplicate JSON key')

    def test_executable_examples_use_normal_selected_build(self):
        for case in ('independent', 'siege'):
            with self.subTest(case=case):
                target = self.output.parent / ('example-' + case)
                run = subprocess.run([sys.executable, '-B', str(ROOT / 'examples/selected-build/run.py'),
                    '--case', case, '--output', str(target)], capture_output=True, text=True, timeout=60)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                self.assertEqual(json.loads(run.stdout)['authorization_effect'], 'none')
                if case == 'siege':
                    parity = json.loads((target / 'parity.json').read_text())
                    self.assertTrue(parity['equal_files'])
                    self.assertEqual(len(parity['decisions']), 15)

    def test_only_bundle_upgrade_preserves_project_component_and_customization(self):
        self.bundle()
        before = copy.deepcopy(self.selection)
        p = self.source / 'bundles/siege/skills/format/SKILL.md'
        p.write_text(p.read_text() + '\nBUNDLE_UPGRADE\n')
        revision = self.fixture.fixture.commit()
        bundle = self.selection['bundles'][0]['component']
        self.selection['bundles'][0]['component'] = selected.describe_component(self.source, bundle['id'], revision, bundle['paths'])
        result = self.build()
        self.assertEqual(result.returncode, 0, result.stderr)
        after = json.loads(result.stdout)
        self.assertEqual(after['components'][1], {'role': 'project', **before['project']})
        self.assertIn('PROJECT_RESIDENT', (self.output / 'flat/skills/RESIDENT.md').read_text())
        self.assertIn('BUNDLE_UPGRADE', (self.output / 'flat/skills/siege--format/SKILL.md').read_text())
        self.assertEqual((self.source / 'projects/independent/CLAUDE.md').read_text(), '')


if __name__ == '__main__':
    unittest.main(verbosity=2)
