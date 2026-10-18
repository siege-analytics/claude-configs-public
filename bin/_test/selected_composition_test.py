#!/usr/bin/env python3
"""Exercise copied composer/resolver modules with explicit independent inputs.

This verifies content composition, not the source builder, installation or live
host capabilities. The approved-policy fixture is shared with its verifier's
tests; no load/evaluation path is mocked.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('policy_fixture_tests', ROOT / 'bin/_test/effective_policy_test.py')
policy_tests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy_tests)


class GeneratedOwnershipCases:
    """Replay the same output contracts through direct and pinned build CLIs."""

    def write_asset(self, publisher, relative, data):
        path = self.source / f'bundles/{publisher}/skills' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path.relative_to(self.source).as_posix()

    def assert_ownership_rejected(self, target, owners, *, early_diagnostic=None):
        original = list(self.content_fixture.selection['publishers'])
        for reverse in (False, True):
            self.content_fixture.selection['publishers'] = original[::-1] if reverse else original
            for existing in (False, True):
                with self.subTest(reverse=reverse, existing=existing, target=target):
                    if self.output.exists():
                        shutil.rmtree(self.output)
                    if existing:
                        self.output.mkdir()
                        sentinel = self.output / 'keep.bin'
                        sentinel.write_bytes(b'EXISTING_DESTINATION\x00\xff')
                        before = sentinel.stat()
                    result = self.ownership_run()
                    diagnostic = json.loads(result.stdout or result.stderr).get('diagnostic', '')
                    self.assertNotEqual(result.returncode, 0, diagnostic)
                    if existing:
                        self.assertTrue('destination already exists' in diagnostic
                                        or early_diagnostic is not None and early_diagnostic in diagnostic, diagnostic)
                        self.assertEqual(list(self.output.iterdir()), [sentinel])
                        self.assertEqual(sentinel.stat(), before)
                        self.assertEqual(sentinel.read_bytes(), b'EXISTING_DESTINATION\x00\xff')
                        shutil.rmtree(self.output)
                    else:
                        if early_diagnostic is None or early_diagnostic not in diagnostic:
                            self.assertIn('generated path collision', diagnostic)
                            self.assertIn(target, diagnostic)
                            for owner in owners:
                                self.assertIn(unicodedata.normalize('NFC', owner),
                                              unicodedata.normalize('NFC', diagnostic))
                        self.assertNotIn(str(self.source), diagnostic)
                        self.assertNotIn('PRIVATE_CONTENT', diagnostic)
                        self.assertFalse(self.output.exists())
                    self.assertFalse(list(self.output.parent.glob('.selected-build-*')))
        self.content_fixture.selection['publishers'] = original

    def test_unqualified_cross_publisher_nested_assets_reject_even_equal_bytes(self):
        self.ownership_publisher('first', qualified=False, skill='outer')
        self.ownership_publisher('second', qualified=False, skill='outer/inner')
        for equal in (False, True):
            owners = [self.write_asset(name, 'outer/inner/shared.txt',
                      b'FIRST_PRIVATE_CONTENT\n' if equal or name == 'first' else b'SECOND_PRIVATE_CONTENT\n')
                      for name in ('first', 'second')]
            with self.subTest(equal=equal):
                self.assert_ownership_rejected('skills/outer/inner/shared.txt', owners)

    def test_flat_router_asset_collision_rejects_before_either_layout_is_written(self):
        self.ownership_publisher('first', qualified=False, skill='outer/inner')
        self.write_asset('first', 'outer/inner/child/SKILL.md', b'---\nname: child\ndescription: Child fixture.\n---\n\n# Child\n')
        self.ownership_publisher('second', qualified=False, skill='category/outer')
        for equal in (False, True):
            owners = [self.write_asset('first', 'outer/inner/shared.txt', b'FIRST_PRIVATE_CONTENT\n'),
                      self.write_asset('second', 'category/outer/inner/shared.txt',
                                       b'FIRST_PRIVATE_CONTENT\n' if equal else b'SECOND_PRIVATE_CONTENT\n')]
            with self.subTest(equal=equal):
                self.assert_ownership_rejected('skills/outer/inner/shared.txt', owners)

    def test_primary_asset_case_alias_rejects(self):
        self.ownership_publisher('first', qualified=False, skill='category/outer')
        self.ownership_publisher('second', qualified=False, skill='category')
        asset = self.write_asset('second', 'category/outer/skill.md', b'# PRIVATE_CONTENT\n')
        # Case-insensitive source discovery can reject this as a duplicate
        # skill before rendering. Case-sensitive discovery copies it as an asset.
        self.assert_ownership_rejected('skills/category/outer/',
                                       ['bundles/first/skills/category/outer/SKILL.md', asset],
                                       early_diagnostic='duplicate qualified skill outer')

    def test_file_directory_and_unicode_aliases_reject(self):
        self.ownership_publisher('first', qualified=False, skill='outer')
        self.ownership_publisher('second', qualified=False, skill='outer/inner')
        for first, second in (('shared-one', 'shared-one/data.txt'), ('Shared-two', 'shared-two/data.txt'),
                              ('caf\u00e9.txt', 'cafe\u0301.txt'), ('\u0390.txt', '\u03aa\u0301.txt')):
            owners = [self.write_asset('first', 'outer/inner/' + first, b'FIRST_PRIVATE_CONTENT\n'),
                      self.write_asset('second', 'outer/inner/' + second, b'SECOND_PRIVATE_CONTENT\n')]
            with self.subTest(paths=(first, second)):
                self.assert_ownership_rejected('skills/outer/inner/', owners)
            for owner in owners:
                (self.source / owner).unlink()

    def test_qualified_nested_publishers_keep_both_assets_deterministically(self):
        self.ownership_publisher('first', skill='outer')
        self.ownership_publisher('second', skill='outer/inner')
        for name in ('first', 'second'):
            self.write_asset(name, 'outer/inner/shared.txt', name.encode())
        for reverse in (False, True):
            if reverse:
                self.content_fixture.selection['publishers'].reverse()
            previous = None
            for replay in range(2):
                result = self.ownership_run()
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                for layout in ('nested', 'flat'):
                    for name, relative in (('first', 'first--outer/inner'), ('second', 'second--inner')):
                        self.assertEqual((self.output / layout / 'skills' / relative / 'shared.txt').read_bytes(),
                                         name.encode())
                current = {p.relative_to(self.output).as_posix(): p.read_bytes()
                           for p in self.output.rglob('*') if p.is_file()}
                if replay:
                    self.assertEqual(current, previous)
                previous = current
                shutil.rmtree(self.output)

    def test_collision_preserves_an_existing_complete_package(self):
        self.ownership_publisher('first', qualified=False, skill='outer')
        self.write_asset('first', 'outer/inner/shared.txt', b'FIRST_PRIVATE_CONTENT\n')
        result = self.ownership_run()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        before = {p.relative_to(self.output).as_posix(): (p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns)
                  for p in self.output.rglob('*') if p.is_file()}
        self.ownership_publisher('second', qualified=False, skill='outer/inner')
        self.write_asset('second', 'outer/inner/shared.txt', b'SECOND_PRIVATE_CONTENT\n')
        result = self.ownership_run()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('destination already exists', result.stdout + result.stderr)
        after = {p.relative_to(self.output).as_posix(): (p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns)
                 for p in self.output.rglob('*') if p.is_file()}
        self.assertEqual(after, before)


class SelectedCompositionTest(GeneratedOwnershipCases, unittest.TestCase):
    @property
    def content_fixture(self):
        return self

    def ownership_publisher(self, name, **kwargs):
        self.publisher(name, **kwargs)

    def ownership_run(self):
        return self.compose()

    def setUp(self):
        self.fixture = policy_tests.RegisteredPolicyInputsTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.source = self.fixture.root
        temporary = tempfile.TemporaryDirectory(prefix='selected-composition-output-')
        self.addCleanup(temporary.cleanup)
        self.output = Path(temporary.name) / 'output'
        self.identity = 'github.example.invalid/independent-org/application'
        for relative in ('bin/compose-project.py', 'bin/build.py', 'bin/frontmatter_validation.py',
                         'bin/procedure_composition.py', 'bin/resolve-load-set.py'):
            shutil.copy2(ROOT / relative, self.source / relative)
        self.project = self.source / 'projects/independent'
        self.fixture.write_json('projects/independent/composition.json', {
            'bindings': {'replacements': [], 'extensions': [], 'aliases': []},
            'heading_map': {}, 'resident_budget': {'max_characters': 2500, 'max_estimated_tokens': 625},
        })
        (self.project / 'CLAUDE.md').write_text('')
        self.selection = {
            'schema_version': 1, 'publishers': [], 'policy_aliases': [], 'prerequisites': {},
            'routes': [{'id': 'project-review', 'priority': 100, 'terms': ['inspect changes'],
                        'skills': ['${policy.review_procedure}']}],
            'resident_blocks': [{'id': 'independent--instructions',
                                 'content': '# Project instructions\n\nPROJECT_RESIDENT\n\n${policy.resident_workflow}',
                                 'source': '${policy.source}', 'allow': []}],
        }

    def compose(self, *, pin=None):
        self.fixture.write_json('projects/independent/content-selection.json', self.selection)
        return subprocess.run([
            sys.executable, str(self.source / 'bin/compose-project.py'),
            '--source', str(self.source), '--output', str(self.output), '--identity', self.identity,
            '--policy-root', str(self.source), '--policy-inputs', str(self.fixture.source),
            '--policy-inputs-sha256', pin or self.fixture.pin,
            '--content-selection', 'projects/independent/content-selection.json',
        ], cwd='/', capture_output=True, text=True, timeout=60)

    def resolve(self, prompt, *, identity=None, layout='flat', render=False):
        command = [sys.executable, str(self.output / layout / 'bin/resolve-load-set.py'),
                   '--prompt', prompt, '--repo', identity or self.identity]
        if render:
            command += ['--render-hook', '--mode', 'on']
        result = subprocess.run(command, cwd='/', capture_output=True, text=True, timeout=60)
        return result, result.stdout if render else json.loads(result.stdout)

    def publisher(self, name, *, qualified=True, root=None, skill='format'):
        root = root or f'bundles/{name}/skills'
        path = self.source / root / skill / 'SKILL.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        # Packaged skills need valid frontmatter (#1046); the body is the fixture.
        path.write_text(f'---\nname: {skill.rsplit("/", 1)[-1]}\ndescription: {name} formatting fixture.\n---\n\n'
                        f'# {name} formatting\n\n{name.upper()}_CONTENT_ONLY\n')
        self.selection['publishers'].append({'id': name, 'skills_root': root, 'qualified': qualified})

    def test_real_composer_and_resolver_without_any_siege_inputs(self):
        absent = ('skills', 'bundles', 'hooks', 'examples', 'catalog/gate-contracts.json',
                  'catalog/effective-policy.json', 'catalog/effective-policy-selection.json')
        for relative in absent:
            self.assertFalse((self.source / relative).exists(), relative)
        result = self.compose()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for layout in ('flat', 'nested'):
            selected, value = self.resolve('inspect changes', layout=layout)
            self.assertEqual(selected.returncode, 0, value)
            self.assertEqual([item['slug'] for item in value['selected']], ['independent--review'])
            receipt = json.loads((self.output / layout / 'composition.json').read_bytes())
            self.assertEqual(receipt['publishers'], [])
            self.assertEqual(receipt['authorization_effect'], 'none')
            self.assertFalse(receipt['policy']['values']['ticket-requirement']['required'])
            self.assertEqual(receipt['policy']['decision']['final'], 'unknown')
            self.assertEqual(receipt['policy']['policy_selection']['source'], 'project/selection.json')
            resident = (self.output / layout / 'skills/RESIDENT.md').read_text()
            self.assertIn('PROJECT_RESIDENT', resident)
            self.assertNotIn('Shared conventions', resident)
            self.assertNotIn('Siege', resident)
            self.assertFalse((self.output / layout / 'skills/code-review').exists())
            rendered, text = self.resolve('inspect changes', layout=layout, render=True)
            self.assertEqual(rendered.returncode, 0, text + rendered.stderr)
            self.assertEqual(text.count('PROJECT_RESIDENT'), 1)

    def test_siege_content_does_not_adopt_siege_workflow(self):
        self.publisher('siege')
        result = self.compose()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        selected, value = self.resolve('[skill:siege--format]')
        self.assertEqual(selected.returncode, 0, value)
        self.assertEqual([(item['slug'], item['project'], item['publisher']) for item in value['selected']],
                         [('siege--format', None, 'siege')])
        receipt = json.loads((self.output / 'flat/composition.json').read_bytes())
        self.assertEqual(receipt['policy']['values']['branch-policy']['integration_branch'], 'trunk')
        self.assertFalse(receipt['policy']['values']['ticket-requirement']['required'])
        self.assertEqual(receipt['policy']['values']['review-procedure-binding']['procedure'], 'independent--review')
        self.assertEqual(receipt['policy']['decision']['final'], 'unknown')
        self.assertEqual(receipt['publishers'][0]['id'], 'siege')

    def test_same_local_name_uses_distinct_publisher_namespaces(self):
        self.publisher('first')
        self.publisher('second')
        result = self.compose()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        _, value = self.resolve('[skill:first--format] [skill:second--format]')
        self.assertEqual([item['slug'] for item in value['selected']], ['first--format', 'second--format'])
        for publisher in ('first', 'second'):
            self.assertIn(publisher.upper() + '_CONTENT_ONLY',
                          (self.output / f'flat/skills/{publisher}--format/SKILL.md').read_text())

    def test_installed_resolver_rejects_forged_publisher_scope_before_resident_output(self):
        self.publisher('first')
        result = self.compose()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        path = self.output / 'flat/catalog/skills-inventory.json'
        original = json.loads(path.read_bytes())
        for change in (
            {'project': 'independent'},
            {'publisher': 'second'},
            {'publisher_root': 'projects/foreign/skills'},
            {'source_path': 'projects/foreign/skills/format/SKILL.md'},
        ):
            changed = copy.deepcopy(original)
            item = next(item for item in changed['items'] if item['slug'] == 'first--format')
            item.update(change)
            path.write_text(json.dumps(changed))
            with self.subTest(change=change):
                process, text = self.resolve('[skill:first--format]', render=True)
                self.assertNotEqual(process.returncode, 0, text)
                self.assertNotIn('PROJECT_RESIDENT', text)
                self.assertNotIn('<project-resident>', text)

    def test_ambiguous_legacy_names_fail_before_output(self):
        self.publisher('first', qualified=False)
        self.publisher('second', qualified=False)
        result = self.compose()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('duplicate qualified skill', result.stdout)
        self.assertFalse(self.output.exists())

    def test_installed_publisher_qualification_mutations_reject_before_resident_output(self):
        self.publisher('first')
        self.publisher('legacy', qualified=False, skill='plain')
        result = self.compose()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        mutations = (
            ('first--format', {'publisher_qualified': False}, 'qualification disagrees'),
            ('plain', {'publisher_qualified': True}, 'qualification disagrees'),
            ('first--format', {'slug': 'second--format'}, 'qualification disagrees'),
            ('first--format', {'slug': 'first--other'}, 'qualification disagrees'),
            ('plain', {'slug': 'other'}, 'qualification disagrees'),
            ('first--format', {'publisher_local_slug': None}, 'invalid qualified slug'),
            ('first--format', {'publisher_local_slug': '../format'}, 'invalid qualified slug'),
            ('first--format', {'publisher_local_slug': 'other', 'slug': 'first--other'}, 'local slug disagrees'),
            ('first--format', {'publisher_qualified': False, 'publisher_local_slug': 'first--format'}, 'local slug disagrees'),
            ('first--format', {'source_path': 'bundles/first/skills/other/SKILL.md'}, 'local slug disagrees'),
            ('first--format', {'source_path': 'bundles/first/skills/shelves/format/SKILL.md'}, 'local slug disagrees'),
            ('first--format', {'source_path': 'bundles/first/skills/first--format/SKILL.md',
                               'publisher_local_slug': 'first--format', 'slug': 'first--first--format'},
             'publisher source directory must be unqualified'),
            ('first--format', {'source_path': 'bundles/first/skills/format/OTHER.md'}, 'publisher source must be SKILL.md'),
        )
        for layout in ('flat', 'nested'):
            path = self.output / layout / 'catalog/skills-inventory.json'
            original = json.loads(path.read_bytes())
            for slug, change, diagnostic in mutations:
                with self.subTest(layout=layout, slug=slug, change=change):
                    changed = copy.deepcopy(original)
                    item = next(item for item in changed['items'] if item['slug'] == slug)
                    item.update(change)
                    path.write_text(json.dumps(changed))
                    # Even an unrelated project request must reject the invalid
                    # inventory before any resident or selected content escapes.
                    process, text = self.resolve('inspect changes', layout=layout, render=True)
                    self.assertNotEqual(process.returncode, 0, text + process.stderr)
                    self.assertIn(diagnostic, process.stderr)
                    self.assertIn('state: error', text)
                    self.assertNotIn('PROJECT_RESIDENT', text)
                    self.assertNotIn('<project-resident>', text)
                    self.assertNotIn('CONTENT_ONLY', text)
            path.write_text(json.dumps(original))

    def test_publisher_local_slugs_match_discovery_and_both_installed_layouts(self):
        self.publisher('first', skill='category/format')
        self.publisher('legacy', qualified=False, skill='shelves/reference')
        self.publisher('books', skill='shelves/reference')
        self.publisher('plain', qualified=False, skill='plain')
        result = self.compose()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for layout in ('flat', 'nested'):
            inventory = json.loads((self.output / layout / 'catalog/skills-inventory.json').read_bytes())
            manifest = json.loads((self.output / layout / 'catalog/resolver-manifest.json').read_bytes())
            for slug, local in (('first--format', 'format'), ('shelves--reference', 'shelves--reference'),
                                ('books--shelves--reference', 'shelves--reference'), ('plain', 'plain')):
                item = next(item for item in inventory['items'] if item['slug'] == slug)
                self.assertEqual(item['publisher_local_slug'], local)
                self.assertEqual(manifest['known'][slug], item)
                process, text = self.resolve(f'[skill:{slug}]', layout=layout, render=True)
                self.assertEqual(process.returncode, 0, text + process.stderr)
                self.assertEqual(text.count('PROJECT_RESIDENT'), 1)

    def test_invalid_discovered_publisher_local_slug_rejects_before_output(self):
        self.publisher('first', skill='bad_name')
        result = self.compose()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertFalse(self.output.exists())

    def test_publisher_cannot_borrow_foreign_project_source(self):
        self.publisher('foreign', root='projects/foreign/skills')
        result = self.compose()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('cannot borrow project scope', result.stdout)
        self.assertFalse(self.output.exists())

    def test_publisher_and_project_qualifier_collision_rejects(self):
        self.publisher('independent', skill='review')
        result = self.compose()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('duplicate qualified skill independent--review', result.stdout)
        self.assertFalse(self.output.exists())

    def test_duplicate_publishers_missing_sources_symlinks_and_cycles_reject(self):
        baseline = copy.deepcopy(self.selection)
        self.publisher('first')
        publisher = copy.deepcopy(self.selection['publishers'][0])
        (self.source / 'linked').symlink_to(self.source / 'bundles/first/skills', target_is_directory=True)
        variants = [
            {'publishers': [publisher, publisher]},
            {'publishers': [{**publisher, 'skills_root': 'absent'}]},
            {'publishers': [{**publisher, 'skills_root': 'linked'}]},
            {'publishers': [{**publisher, 'skills_root': '.'}]},
            {'publishers': [{**publisher, 'skills_root': '../escape'}]},
            {'prerequisites': {'independent--review': ['independent--review']}},
            {'routes': [{'id': 'missing', 'priority': 1, 'terms': ['missing'], 'skills': ['absent']}]},
            {'policy_aliases': ['independent--review']},
            {'authorization_effect': 'allow'},
        ]
        for variant in variants:
            self.selection = {**copy.deepcopy(baseline), **variant}
            with self.subTest(variant=variant):
                result = self.compose()
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertFalse(self.output.exists())

    def test_content_selection_cannot_replace_independently_pinned_policy(self):
        self.fixture.inputs['review_repository'] = 'github.com/candidate/policy'
        self.fixture.write_json(self.fixture.source, self.fixture.inputs)
        result = self.compose()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('registration digest differs from independent pin', result.stdout)
        self.assertFalse(self.output.exists())

    def test_empty_resident_rejects_before_generating_an_unusable_package(self):
        for blocks in ([], [{'id': 'independent--blank', 'content': ' \n ', 'source': 'blank.md', 'allow': []}]):
            self.selection['resident_blocks'] = blocks
            with self.subTest(blocks=blocks):
                result = self.compose()
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn('selected resident composition must not be empty', result.stdout)
                self.assertFalse(self.output.exists())

    def test_foreign_resolver_identity_and_unused_wrong_project_binding_reject(self):
        result = self.compose()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        selected, value = self.resolve('inspect changes', identity='github.example.invalid/foreign/application')
        self.assertNotEqual(selected.returncode, 0)
        self.assertIn('identity differs', value['diagnostic'])
        self.output = self.output.parent / 'invalid'
        path = self.project / 'composition.json'
        config = json.loads(path.read_bytes())
        config['bindings']['aliases'].append({'alias': 'foreign', 'target': 'foreign--review', 'source': 'foreign.json'})
        path.write_text(json.dumps(config))
        result = self.compose()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())


class GeneratedFileClaimsTest(unittest.TestCase):
    def test_primary_rule_asset_and_reserved_claims_never_overwrite(self):
        spec = importlib.util.spec_from_file_location('ownership_composer', ROOT / 'bin/compose-project.py')
        composer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(composer)
        for path in ('skills/example/SKILL.md', 'skills/_checks.md', 'skills/RESIDENT.md',
                     'skills/RULES_BUNDLE.md', 'catalog/resolver-manifest.json',
                     'catalog/skills-inventory.json', 'bin/resolve-load-set.py', 'composition.json'):
            for equal in (False, True):
                with self.subTest(path=path, equal=equal):
                    output = composer.GeneratedFiles()
                    output.add(path, b'first', 'first source')
                    with self.assertRaisesRegex(ValueError, 'generated path collision') as error:
                        output.add(path, b'first' if equal else b'second', 'second source')
                    self.assertIn(path, str(error.exception))
                    self.assertIn('first source', str(error.exception))
                    self.assertIn('second source', str(error.exception))
                    self.assertEqual(output.files, {path: b'first'})


class SiegeCompatibilityTest(unittest.TestCase):
    def test_explicit_siege_and_compatibility_use_identical_composer_outputs(self):
        with tempfile.TemporaryDirectory(prefix='explicit-siege-composition-') as temporary:
            root = Path(temporary)
            source = root / 'source'
            shutil.copytree(ROOT / 'examples/composition', source)
            shutil.copy2(ROOT / 'bundles/siege/composition-inputs.json', source / 'selected-content.json')
            inputs = json.loads((ROOT / 'bundles/siege/policy-inputs.json').read_bytes())
            pin = policy_tests.policy.digest(inputs)
            for project in ('strict-release', 'synthetic-trunk'):
                identity = 'github.example.invalid/synthetic-org/' + project
                outputs = []
                for mode in ('compatibility', 'explicit'):
                    output = root / project / mode
                    command = [sys.executable, str(ROOT / 'bin/compose-project.py'),
                               '--source', str(source), '--output', str(output), '--identity', identity]
                    if mode == 'explicit':
                        command += ['--policy-inputs', 'bundles/siege/policy-inputs.json',
                                    '--policy-inputs-sha256', pin, '--content-selection', 'selected-content.json']
                    result = subprocess.run(command, cwd='/', capture_output=True, text=True, timeout=60)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    outputs.append({p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in output.rglob('*') if p.is_file()})
                self.assertEqual(outputs[0], outputs[1], project)


if __name__ == '__main__':
    unittest.main(verbosity=2)
