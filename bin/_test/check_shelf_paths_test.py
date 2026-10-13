#!/usr/bin/env python3
"""Actionable path and orphan negative fixtures."""
from __future__ import annotations
import importlib.util
import json
import tempfile
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('shelf_paths', Path(__file__).resolve().parents[1] / 'check-shelf-paths.py')
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        book = root / 'skills/shelves/topic/book'
        book.mkdir(parents=True)
        (root / 'catalog').mkdir()
        (root / 'catalog/shelf-reference-exceptions.json').write_text(json.dumps({'empty_placeholders': {}}))
        source = book / 'SKILL.md'
        ref = book / 'references/existing.md'
        ref.parent.mkdir()
        ref.write_text('# Real content\n')
        source.write_text('Read [`references/existing.md`](references/existing.md).\n')
        assert not mod.check(root)
        source.write_text('Read `references/absent.md` before responding.\n')
        assert any('missing local target' in x for x in mod.check(root)), 'missing backtick path passed'
        source.write_text('[read it](references/absent.md)\n')
        assert any('missing local target' in x for x in mod.check(root)), 'missing markdown link passed'
        source.write_text('[read](<references/absent.md>)\n')
        assert any('missing local target' in x for x in mod.check(root)), 'missing angle-wrapped Markdown link passed'
        source.write_text('[read][doc]\n\n[doc]: references/absent.md\n')
        assert any('missing local target' in x for x in mod.check(root)), 'missing reference-style Markdown link passed'
        source.write_text('[read][doc]\n\n[doc]: <references/absent.md>\n')
        assert any('missing local target' in x for x in mod.check(root)), 'missing angle-wrapped reference definition passed'
        source.write_text('Read `skills/shelves/topic/book/references/absent.md`.\n')
        assert any('missing local target' in x for x in mod.check(root)), 'missing repo-root path passed'
        source.write_text('See `https://example.test/rules/not-vendored.md` (upstream, not shipped).\n')
        errors = mod.check(root)
        assert any('orphan' in x for x in errors) and not any('missing local' in x for x in errors), errors
        source.write_text('Session plan unavailable historical provenance (not shipped): `plans/old.md`.\n')
        assert not any('missing local' in x for x in mod.check(root)), 'historical citation failed'
        source.write_text('Unavailable historical plan (not shipped): `plans/old.md`; read `references/absent.md` now.\n')
        assert any('missing local target' in x for x in mod.check(root)), 'historical qualifier masked other broken path'
        source.write_text('Do not read `references/absent.md`; it is not shipped.\n')
        assert not any('missing local' in x for x in mod.check(root)), 'explicitly negated example failed'
        source.write_text('Do not read `references/absent.md`; read `references/also-absent.md`.\n')
        assert any('also-absent' in x for x in mod.check(root)), 'negated example masked subsequent actionable path'
        source.write_text('Do not read `references/absent.md` but read `references/also-absent.md`.\n')
        assert any('also-absent' in x for x in mod.check(root)), 'conjunction masked later affirmative target'
        source.write_text('```markdown\nRead `references/absent.md`\n```\n')
        assert not any('missing local' in x for x in mod.check(root)), 'fenced code example failed'
        source.write_text('Use `_foo-rules.md` and `SKILL.md` as shorthand.\n')
        assert not any('missing local' in x for x in mod.check(root)), 'bare shorthand failed'
        source.write_text('Read `references/existing.md`.\n')
        assert not mod.check(root)
        ref2 = book / 'references/orphan.md';ref2.write_text('real supplemental material\n')
        source.write_text('Read `references/existing.md`; orphan.md is a bare name, not a link.\n')
        assert any('orphan' in x for x in mod.check(root)), 'orphan passed'
        source.write_text('Read `references/existing.md`. Here is `references/orphan.md` as an inert citation.\n')
        assert any('orphan' in x for x in mod.check(root)), 'bare backtick justified orphan'
        (root / 'catalog/shelf-reference-exceptions.json').write_text(json.dumps({'empty_placeholders': {'skills/shelves/topic/book/references/orphan.md': 'reason'}}))
        assert mod.check(root), 'nonempty orphan exception passed'
        ref2.write_text('\n')
        assert not mod.check(root), 'documented empty placeholder failed'
        ref2.unlink()
        assert mod.check(root), 'stale placeholder passed'
        nested = book / 'references/sub/deep.md'
        nested.parent.mkdir()
        nested.write_text('supplement\n')
        assert any('deep.md' in x for x in mod.check(root)), 'nested orphan passed'
    print('Shelf path negative fixtures: PASS')


if __name__ == '__main__':
    main()
