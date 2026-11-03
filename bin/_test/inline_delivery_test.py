#!/usr/bin/env python3
"""Actual prompt-hook delivery remains complete inside the SDK byte budget."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class InlineDelivery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory(prefix='inline-delivery-')
        cls.addClassCleanup(cls.fixture.cleanup)
        cls.root = Path(cls.fixture.name) / ('installed-' + 'x' * 80)
        cls.root.mkdir()
        for part in ('bin', 'catalog', 'hooks', 'skills'):
            subprocess.run(['cp', '-R', str(ROOT / part), str(cls.root / part)],
                           check=True, capture_output=True, timeout=30)
        cls.kernel = cls.root / 'skills/KERNEL.md'
        cls.selector = cls.root / 'bin/resolve-load-set.py'
        cls.kernel_bytes = cls.kernel.read_bytes()
        cls.selector_bytes = cls.selector.read_bytes()
        cls.hook = cls.root / 'hooks/resolver/inject-resolver.sh'

    def setUp(self):
        self.kernel.write_bytes(self.kernel_bytes)
        self.selector.write_bytes(self.selector_bytes)
        case = tempfile.TemporaryDirectory(prefix='case-', dir=self.fixture.name)
        self.addCleanup(case.cleanup)
        self.case = Path(case.name)
        self.storage = self.case / 'tmp'
        self.storage.mkdir()
        self.payload = {'prompt': 'write a friendly greeting', 'cwd': '/tmp'}

    def environment(self, extra=None):
        env = dict(os.environ)
        env.pop('CLAUDE_KERNEL_PATH', None)
        env.update(CLAUDE_PROGRESSIVE_LOADING='on', CRAFT_AGENT_PLANS_PATH='/nonexistent',
                   TMPDIR=str(self.storage))
        env.update(extra or {})
        return env

    def deliver(self, payload=None, extra=None):
        before = set(self.storage.glob('craft-hook-output.*'))
        result = subprocess.run(['bash', str(self.hook)], cwd=self.case,
                                input=json.dumps(payload or self.payload).encode(),
                                env=self.environment(extra), capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set(self.storage.glob('craft-hook-output.*')), before)
        return result.stdout

    def original_envelope(self, selected):
        return (b'<skill-kernel mode="on">\n' + self.kernel.read_bytes().rstrip(b'\n')
                + b'\n</skill-kernel>\n' + selected.rstrip(b'\n') + b'\n')

    def stub_selector(self, output):
        self.selector.write_text('import sys\nsys.stdout.buffer.write(' + repr(output) + ')\n')

    def assert_fallback(self, output):
        self.assertLess(len(output), 10000)
        self.assertIn(self.kernel.read_bytes(), output)
        self.assertIn(b'state: over-budget', output)
        self.assertIn(b'kernel only', output)
        self.assertNotIn(b'\nload:', output)
        self.assertNotIn(b'<project-resident>', output)
        output.decode('utf-8')

    def test_underbudget_delivery_preserves_exact_envelope(self):
        selected = subprocess.run([sys.executable, str(self.selector), '--payload-stdin',
                                   '--render-hook', '--mode', 'on'],
                                  input=json.dumps(self.payload).encode(), cwd=self.case,
                                  env=self.environment(), capture_output=True, timeout=15)
        self.assertEqual(selected.returncode, 0, selected.stderr)
        expected = self.original_envelope(selected.stdout)
        self.assertLess(len(expected), 10000)
        self.assertEqual(self.deliver(), expected)

    def test_actual_long_root_selection_falls_back_without_partial_loads(self):
        payload = {'prompt': 'review Python Spark SQL Databricks Unity Catalog spatial PostGIS code',
                   'cwd': '/tmp'}
        selected = subprocess.run([sys.executable, str(self.selector), '--payload-stdin',
                                   '--render-hook', '--mode', 'on'],
                                  input=json.dumps(payload).encode(), cwd=self.case,
                                  env=self.environment(), capture_output=True, timeout=15)
        self.assertEqual(selected.returncode, 0, selected.stderr)
        self.assertIn(b'\nload:', selected.stdout)
        self.assertGreaterEqual(len(self.original_envelope(selected.stdout)), 10000)
        self.assert_fallback(self.deliver(payload))

    def test_exact_byte_boundary(self):
        overhead = len(self.original_envelope(b'x')) - 1
        for size in (9999, 10000):
            with self.subTest(size=size):
                selected = b'x' * (size - overhead)
                expected = self.original_envelope(selected)
                self.assertEqual(len(expected), size)
                self.stub_selector(selected)
                output = self.deliver()
                if size == 9999:
                    self.assertEqual(output, expected)
                else:
                    self.assert_fallback(output)

    def test_multibyte_output_counts_utf8_bytes(self):
        overhead = len(self.original_envelope(b'x')) - 1
        selected = chr(0x754c).encode() * ((10000 - overhead + 2) // 3)
        expected = self.original_envelope(selected)
        self.assertGreaterEqual(len(expected), 10000)
        self.assertLess(len(expected.decode()), 10000)
        self.stub_selector(selected)
        self.assert_fallback(self.deliver())

    def test_optional_unicode_plan_warning_is_budgeted(self):
        plans = self.case / 'plans'
        plans.mkdir()
        for index in range(10):
            (plans / ('think-' + chr(0x754c) * 75 + '-' + str(index) + '.md')).write_text('')
        output = self.deliver()
        self.assert_fallback(output)
        self.assertNotIn(b'PIPELINE STATUS', output)

    def test_oversized_mandatory_kernel_blocks_without_partial_policy(self):
        self.kernel.write_bytes(chr(0xe9).encode() * 5000)
        output = self.deliver(extra={'CLAUDE_PROGRESSIVE_LOADING': 'kernel-only'})
        self.assertLess(len(output), 10000)
        self.assertFalse(json.loads(output)['continue'])
        self.assertNotIn(b'<skill-kernel', output)

    def test_missing_temporary_storage_blocks_with_sole_json(self):
        output = self.deliver(extra={'TMPDIR': str(self.case / 'absent' / 'storage')})
        self.assertFalse(json.loads(output)['continue'])
        self.assertNotIn(b'<skill-kernel', output)

    def test_metrics_use_trusted_fixed_reference_not_source_root_or_ambient_plans(self):
        import importlib.util
        from unittest.mock import patch
        spec = importlib.util.spec_from_file_location('portable_metrics', ROOT / 'bin/progressive-loading-metrics.py')
        metrics = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(metrics)
        inventory = json.loads((ROOT / 'catalog/skills-inventory.json').read_text())
        paths = {'bin/resolve-load-set.py', 'hooks/resolver/inject-resolver.sh',
                 'catalog/resolver-manifest.json', 'catalog/skills-inventory.json',
                 'skills/KERNEL.md', 'skills/RESOLVER.md', 'RESOLVER.md'}
        paths.update(item['canonical_source'] for item in inventory['items'])
        if (ROOT / 'dist/RULES_BUNDLE.md').is_file():
            paths.add('dist/RULES_BUNDLE.md')
        ambient = self.case / 'ambient-plans'
        ambient.mkdir()
        (ambient / 'think-unrelated.md').write_text('unrelated unfinished task')
        sentinel = self.case / 'untrusted-shadow-executed'
        measured = []
        for name in ('short', 'long-' + 'x' * 120):
            package = self.case / name
            for relative in paths:
                target = package / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / relative).read_bytes())
            (package / 'plans').mkdir()
            (package / 'plans/think-cwd.md').write_text('ambient cwd plan')
            # A copied whole bin directory would execute this untracked module.
            (package / 'bin/json.py').write_text('from pathlib import Path\nPath(' + repr(str(sentinel)) + ').write_text("executed")\nraise RuntimeError("untrusted shadow")\n')
            with patch.object(metrics, 'ROOT', package), patch.dict(os.environ, {
                'CRAFT_AGENT_PLANS_PATH': str(ambient), 'CLAUDE_PROGRESSIVE_LOADING': 'kernel-only',
                'CLAUDE_KERNEL_PATH': str(self.case / 'noncanonical-kernel')}):
                previous = Path.cwd()
                try:
                    os.chdir(package)
                    measured.append(metrics.build())
                finally:
                    os.chdir(previous)
            self.assertFalse(sentinel.exists())
        self.assertEqual(measured[0], measured[1])
        self.assertEqual(measured[0]['characters']['injected']['multi_route'], 9577)


    def test_reference_copy_refuses_fifo_without_blocking(self):
        fifo = self.case / 'source-fifo'
        os.mkfifo(fifo)
        code = """import importlib.util,sys
spec=importlib.util.spec_from_file_location('metrics',sys.argv[1])
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
try:module.reference_bytes(sys.argv[2])
except ValueError as error:
 assert 'regular file' in str(error),str(error)
 print('regular-file refusal')
else:raise AssertionError('FIFO was accepted')
"""
        result = subprocess.run([sys.executable, '-I', '-B', '-c', code,
                                 str(ROOT / 'bin/progressive-loading-metrics.py'), str(fifo)],
                                capture_output=True, timeout=3)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b'regular-file refusal', result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
