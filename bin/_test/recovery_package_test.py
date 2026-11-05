#!/usr/bin/env python3
"""Recovery guidance must retain its portable host-controls reference."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('recovery_compose', ROOT / 'bin/compose-project.py')
compose = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(compose)


class RecoveryPackageTest(unittest.TestCase):
    def test_clean_packages_and_missing_host_controls(self):
        with tempfile.TemporaryDirectory(prefix='recovery-package-') as raw:
            output = Path(raw) / 'dist'
            subprocess.run([sys.executable, str(ROOT / 'bin/build.py'), '--dist', str(output)],
                           cwd=ROOT, check=True, capture_output=True, text=True, timeout=120)
            for layout in ('nested', 'flat'):
                with self.subTest(layout=layout):
                    root = output / layout
                    entries = list((root / 'skills').rglob('stalled-session-recovery/SKILL.md'))
                    self.assertEqual(len(entries), 1)
                    folder = entries[0].parent
                    self.assertEqual(list(folder.rglob('SKILL.md')), entries)
                    support = folder / 'host-controls.md'
                    self.assertTrue(support.is_file())
                    # Inspect this procedure's complete outgoing links against
                    # actual delivered paths; other skills keep their own tests.
                    files = {path.relative_to(root).as_posix():
                             path.read_bytes() if path.parent == folder else b''
                             for path in root.rglob('*') if path.is_file()}
                    compose.validate_packaged_links(files)
                    del files[support.relative_to(root).as_posix()]
                    with self.assertRaisesRegex(ValueError, 'missing or out-of-scope packaged link'):
                        compose.validate_packaged_links(files)


if __name__ == '__main__':
    unittest.main()
