#!/usr/bin/env python3
"""Exercise actual resolver and packaged links for the two accepted identities."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('compose_project', ROOT / 'bin/compose-project.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}


class ProjectCompositionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='composition-packages-')
        cls.root = Path(cls.temp.name)
        cls.source = ROOT / 'examples/composition'
        cls.before = hashes(cls.source)
        for project in ('strict-release', 'synthetic-trunk'):
            m.package(cls.source, cls.root / project, 'github.example.invalid/synthetic-org/' + project)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def select(self, project, prompt, layout='flat', identity=None):
        path = self.root / project / layout
        process = subprocess.run([sys.executable, str(path / 'bin/resolve-load-set.py'), '--prompt', prompt, '--repo', identity or 'github.example.invalid/synthetic-org/' + project], text=True, capture_output=True, cwd='/')
        return process.returncode, json.loads(process.stdout)

    def test_all_routes_share_replacement_extension_and_order(self):
        expected = ['strict-release--review', 'strict-release--checks']
        for layout in ('flat', 'nested'):
            for prompt in ('[skill:self-review]', '/self-review', '[skill:review]', 'review candidate', '[skill:code-review]', '[skill:strict-release--checks] [skill:review]'):
                with self.subTest(layout=layout, prompt=prompt):
                    code, result = self.select('strict-release', prompt, layout)
                    self.assertEqual(code, 0, result)
                    self.assertEqual(result['state'], 'matched', result)
                    want = expected + (['code-review'] if 'code-review' in prompt else [])
                    self.assertEqual([item['slug'] for item in result['selected']], want)
                    for item in result['selected']:
                        self.assertTrue((self.root / 'strict-release' / layout / item['load_path']).is_file())

    def test_second_project_uses_its_selected_default(self):
        for layout in ('flat', 'nested'):
            code, result = self.select('synthetic-trunk', 'review candidate [skill:review]', layout)
            self.assertEqual(code, 0, result)
            self.assertEqual([i['slug'] for i in result['selected']], ['hostile-review'])
            self.assertFalse((self.root / 'synthetic-trunk' / layout / 'skills/strict-release--review').exists())

    def test_alias_and_prerequisite_trace_retains_original_source(self):
        code, result = self.select('strict-release', '[skill:code-review]')
        item = result['selected'][0]
        self.assertEqual(item['source_path'], 'projects/strict-release/skills/review/SKILL.md')
        self.assertEqual([edge['kind'] for edge in item['binding_traces'][0]], ['prerequisite', 'alias', 'replacement'])

    def test_scoped_package_rejects_foreign_or_missing_identity(self):
        for identity in ('github.example.invalid/foreign/strict-release', 'github.example.invalid/synthetic-org/synthetic-trunk', 'strict-release'):
            code, result = self.select('strict-release', '[skill:review]', identity=identity)
            self.assertEqual(code, 1, result)
            self.assertIn('identity differs', result['diagnostic'])

    def test_cross_references_and_rules_bundle_use_the_same_effective_paths(self):
        for layout in ('flat', 'nested'):
            path = self.root / 'strict-release' / layout
            self.assertFalse((path / 'skills/self-review/SKILL.md').exists())
            caller = 'skills/coding/code-review/SKILL.md' if layout == 'nested' else 'skills/code-review/SKILL.md'
            for name in (caller, 'skills/_review.md', 'skills/_strict-release--rules.md', 'skills/RULES_BUNDLE.md', 'skills/RESIDENT.md'):
                content = (path / name).read_text()
                self.assertIn('strict-release--review/SKILL.md', content)
                self.assertIn('strict-release--checks/SKILL.md', content)
                self.assertNotIn('self-review/SKILL.md', content)
            self.assertTrue((path / 'skills/strict-release--review/references/steps.md').is_file())

    def test_parent_unchanged_and_project_content_isolated(self):
        self.assertEqual(hashes(self.source), self.before)
        for layout in ('flat', 'nested'):
            strict = self.root / 'strict-release' / layout
            trunk = self.root / 'synthetic-trunk' / layout
            self.assertNotIn('TRUNK_PROJECT_RULE', (strict / 'skills/RULES_BUNDLE.md').read_text())
            self.assertNotIn('STRICT_PROJECT_RULE', (trunk / 'skills/RULES_BUNDLE.md').read_text())
            a = json.loads((strict / 'composition.json').read_text())
            b = json.loads((trunk / 'composition.json').read_text())
            self.assertEqual(a['parent_content_sha256'], b['parent_content_sha256'])
            for project, branch, marker in (('strict-release', 'develop', 'STRICT_OVERLAY'), ('synthetic-trunk', 'main', 'TRUNK_OVERLAY')):
                resident = (self.root / project / layout / 'skills/RESIDENT.md').read_text()
                self.assertIn('`' + branch + '`', resident)
                self.assertIn(marker, resident)

    def test_composition_preserves_locked_policy_and_cannot_authorize(self):
        for project in ('strict-release', 'synthetic-trunk'):
            receipt = json.loads((self.root / project / 'flat/composition.json').read_text())
            self.assertEqual(receipt['authorization_effect'], 'none')
            self.assertEqual(receipt['policy']['decision']['final'], 'unknown')
            self.assertTrue(receipt['policy']['values']['ticket-requirement']['required'])
            self.assertTrue(receipt['policy']['provenance']['ticket-requirement']['required']['locked'])
            self.assertLessEqual(receipt['resident']['characters'], 2500)
            self.assertLessEqual(receipt['resident']['estimated_tokens'], 625)

    def changed_source(self):
        temp = tempfile.TemporaryDirectory(prefix='composition-negative-')
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        source = root / 'source'
        shutil.copytree(self.source, source)
        return source, root / 'output'

    def test_missing_reference_conflict_and_cycle_fail_before_output(self):
        for variant in ('missing', 'conflict', 'cycle'):
            source, output = self.changed_source()
            path = source / 'projects/strict-release/composition.json'
            data = json.loads(path.read_text())
            if variant == 'missing':
                data['bindings']['replacements'][0]['replacement'] = 'missing'
            elif variant == 'conflict':
                data['bindings']['replacements'].append({'target': 'self-review', 'replacement': 'hostile-review', 'source': 'conflicting.json'})
            else:
                data['bindings']['extensions'].append({'target': 'strict-release--checks', 'append': ['self-review'], 'source': 'cycle.json'})
            path.write_text(json.dumps(data))
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                m.package(source, output, 'github.example.invalid/synthetic-org/strict-release')
            self.assertFalse(output.exists())

    def test_legacy_mapping_and_final_budget_fail_before_output(self):
        for variant in ('heading', 'budget', 'locked'):
            source, output = self.changed_source()
            path = source / 'projects/strict-release/composition.json'
            data = json.loads(path.read_text())
            if variant == 'heading': data['heading_map'] = {}
            if variant == 'budget': data['resident_budget']['max_characters'] = 50
            if variant == 'locked': data['heading_map']['Conventions'] = {'id': 'workflow', 'mode': 'replace'}
            path.write_text(json.dumps(data))
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                m.package(source, output, 'github.example.invalid/synthetic-org/strict-release')
            self.assertFalse(output.exists())

    def test_raw_link_to_replaced_default_rejects_with_diagnostic(self):
        source, output = self.changed_source()
        path = source / 'skills/coding/code-review/SKILL.md'
        path.write_text(path.read_text() + '\n[Old review](../self-review/SKILL.md)\n')
        with self.assertRaisesRegex(ValueError, 'missing or out-of-scope packaged link'):
            m.package(source, output, 'github.example.invalid/synthetic-org/strict-release')
        self.assertFalse(output.exists())

    def test_foreign_project_reference_rejects(self):
        source, output = self.changed_source()
        path = source / 'skills/coding/code-review/SKILL.md'
        path.write_text(path.read_text() + '\n[skill:synthetic-trunk--secret]\n')
        with self.assertRaisesRegex(ValueError, 'missing procedure'):
            m.package(source, output, 'github.example.invalid/synthetic-org/strict-release')

    def test_existing_output_is_not_overwritten(self):
        with self.assertRaisesRegex(ValueError, 'already exists'):
            m.package(self.source, self.root / 'strict-release', 'github.example.invalid/synthetic-org/strict-release')

    def test_router_assets_cannot_resurrect_a_replaced_child(self):
        source, output = self.changed_source()
        (source / 'skills/self-review').rename(source / 'skills/coding/self-review')
        (source / 'skills/coding/SKILL.md').write_text('# Router\n\nUse [skill:self-review].\n')
        m.package(source, output, 'github.example.invalid/synthetic-org/strict-release')
        for layout in ('flat', 'nested'):
            root = output / layout
            self.assertFalse((root / 'skills/coding/self-review/SKILL.md').exists())
            self.assertNotIn('PARENT_SELF_REVIEW', '\n'.join(p.read_text() for p in root.rglob('*.md')))
            self.assertIn('strict-release--review/SKILL.md', (root / 'skills/coding/SKILL.md').read_text())

    def test_symlink_sources_and_output_inside_source_reject(self):
        source, output = self.changed_source()
        link = source / 'projects/strict-release/skills/review/references/private.md'
        link.symlink_to(source / 'projects/synthetic-trunk/CLAUDE.md')
        with self.assertRaisesRegex(ValueError, 'symlink composition source'):
            m.package(source, output, 'github.example.invalid/synthetic-org/strict-release')
        with self.assertRaisesRegex(ValueError, 'outside the source tree'):
            m.package(source, source / 'output', 'github.example.invalid/synthetic-org/strict-release')


if __name__ == '__main__': unittest.main(verbosity=2)
