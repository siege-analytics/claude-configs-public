#!/usr/bin/env python3
"""Think references must travel with either real builder layout."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('think_compose', ROOT / 'bin/compose-project.py')
compose = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compose)


class ThinkPackage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='think-package-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.output = Path(cls.temp.name) / 'dist'
        subprocess.run([sys.executable, str(ROOT / 'bin/build.py'), '--dist', str(cls.output)],
                       cwd=ROOT, check=True, capture_output=True, text=True, timeout=120)

    def package(self, layout):
        root = self.output / layout
        entries = list((root / 'skills').rglob('think/SKILL.md'))
        self.assertEqual(len(entries), 1, entries)
        folder = entries[0].parent
        self.assertEqual(list(folder.rglob('SKILL.md')), [entries[0]])
        # Validate outgoing links of this changed procedure, against all actual
        # delivered paths. Unrelated procedures are outside this test's scope.
        files = {p.relative_to(root).as_posix():
                 p.read_bytes() if p.parent == folder else b''
                 for p in root.rglob('*') if p.is_file()}
        supports = [folder / name for name in
                    ('design-workflow.md', 'task-evidence.md', 'premise-claims.md')]
        for support in supports:
            self.assertTrue(support.is_file(), support)
            self.assertGreater(support.stat().st_size, 500)
        return root, folder, files

    def test_clean_both_layouts_resolve_the_complete_procedure(self):
        for layout in ('nested', 'flat'):
            with self.subTest(layout=layout):
                _root, _folder, files = self.package(layout)
                compose.validate_packaged_links(files)

    def test_omitting_any_support_is_rejected_by_real_package_validator(self):
        for layout in ('nested', 'flat'):
            root, folder, files = self.package(layout)
            for name in ('design-workflow.md', 'task-evidence.md', 'premise-claims.md'):
                with self.subTest(layout=layout, missing=name):
                    broken = dict(files)
                    del broken[(folder / name).relative_to(root).as_posix()]
                    with self.assertRaisesRegex(ValueError, 'missing or out-of-scope packaged link'):
                        compose.validate_packaged_links(broken)

    def test_foreign_resource_substitution_is_rejected(self):
        for layout in ('nested', 'flat'):
            root, folder, files = self.package(layout)
            entry = (folder / 'SKILL.md').relative_to(root).as_posix()
            broken = dict(files)
            broken[entry] = broken[entry].replace(b'(design-workflow.md)', b'(file:///tmp/design-workflow.md)')
            self.assertNotEqual(broken[entry], files[entry])
            with self.assertRaisesRegex(ValueError, 'unsupported link scheme'):
                compose.validate_packaged_links(broken)


if __name__ == '__main__':
    unittest.main()
