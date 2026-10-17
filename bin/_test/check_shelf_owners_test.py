#!/usr/bin/env python3
"""Negative ownership fixtures; no shelf may own itself or inherit router links."""
from __future__ import annotations
import importlib.util
import json
import tempfile
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('shelf_owners', Path(__file__).resolve().parents[1] / 'check-shelf-owners.py')
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def fixture(root):
    shelf = 'skills/shelves/topic/book/SKILL.md'
    owner = 'skills/worker/SKILL.md'
    for path, text in ((shelf, '# Book\n'), (owner, '# Worker\n## Companion shelves\nFor review: read `'+shelf+'` when applicable.\n')):
        p = root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    (root / 'catalog').mkdir()
    inventory = {'items': [{'source_path': shelf, 'kind': 'reference-shelf'}, {'source_path': owner, 'kind': 'skill'}]}
    (root / 'catalog/skills-inventory.json').write_text(json.dumps(inventory))
    record = {'source_path': shelf, 'owner': {'source_path': owner, 'evidence': 'For review: read `'+shelf+'` when applicable.', 'directive': 'For review: read `'+shelf+'` when applicable.'}}
    return record


def run(root, records):
    (root / 'catalog/shelf-ownership.json').write_text(json.dumps({'schema_version': 1, 'records': records}))
    return mod.check(root)


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        record = fixture(root)
        assert not run(root, [record])
        assert run(root, []), 'missing inventory record passed'
        assert run(root, [record, record]), 'duplicate owner decision passed'
        assert run(root, [dict(record, quarantine={'reason': 'no'})]), 'owner + quarantine passed'
        assert run(root, [{'source_path': record['source_path'], 'quarantine': {'reason': '  '}}]), 'empty reason passed'
        assert not run(root, [{'source_path': record['source_path'], 'quarantine': {'reason': 'No active scoped inbound consultation path'}}])
        assert run(root, [{'source_path': record['source_path'], 'quarantine': {'reason': 'No owner yet'}}]), 'short vague quarantine passed'
        bad = json.loads(json.dumps(record));bad['owner']['source_path'] = record['source_path']
        assert run(root, [bad]), 'shelf self-ownership passed'
        bad = json.loads(json.dumps(record));bad['owner']['source_path'] = 'skills/shelves/topic/SKILL.md'
        assert run(root, [bad]), 'category router ownership passed'
        bad = json.loads(json.dumps(record));bad['owner']['evidence'] = 'book'
        assert run(root, [bad]), 'unverified evidence passed'
        bad = json.loads(json.dumps(record));bad['owner']['evidence'] = '`'+record['source_path']+'`'
        assert run(root, [bad]), 'router-only link passed'
        (root / 'skills/worker/SKILL.md').write_text('## Companion shelves\nThis list is not for reading.\n- `'+record['source_path']+'` -- for archival record only.\n')
        bad = json.loads(json.dumps(record))
        bad['owner']['evidence'] = '- `'+record['source_path']+'` -- for archival record only.'
        bad['owner']['directive'] = 'This list is not for reading.'
        assert run(root, [bad]), 'negated/archive-only evidence passed'
        (root / 'skills/worker/SKILL.md').write_text('## Companion shelves\nThis list is not for reading.\nFor design rationale:\n- `'+record['source_path']+'` -- overview of the topic.\n')
        bad['owner']['evidence'] = '- `'+record['source_path']+'` -- overview of the topic.'
        bad['owner']['directive'] = 'For design rationale:'
        assert run(root, [bad]), 'contradictory same-section owner passed'
        for verb in ('open', 'reference', 'follow'):
            (root / 'skills/worker/SKILL.md').write_text('## Companion shelves\nFor design rationale:\nDo not '+verb+' this shelf.\n- `'+record['source_path']+'` -- engineering rationale.\n')
            bad['owner']['evidence'] = '- `'+record['source_path']+'` -- engineering rationale.'
            bad['owner']['directive'] = 'For design rationale:'
            assert run(root, [bad]), 'do-not-'+verb+' owner passed'
        (root / 'skills/worker/SKILL.md').write_text('## Companion shelves\nRead logs for diagnostics.\n- `'+record['source_path']+'` -- engineering rationale.\n')
        bad['owner']['directive'] = 'Read logs for diagnostics.'
        assert run(root, [bad]), 'unrelated read-logs directive passed'
        (root / 'skills/worker/SKILL.md').write_text('## Companion shelves\nRead shelf books for review.\n<!-- - `'+record['source_path']+'` -- engineering rationale. -->\n')
        bad['owner']['directive'] = 'Read shelf books for review.'
        assert run(root, [bad]), 'HTML comment evidence passed'
        (root / 'skills/worker/SKILL.md').write_text('## Companion shelves\nRead shelf books for review.\n````markdown\n- `'+record['source_path']+'` -- engineering rationale.\n```\n````\n')
        assert run(root, [bad]), 'fenced evidence passed'
        (root / 'skills/worker/SKILL.md').write_text('# Worker\n## Companion shelves\n'+record['owner']['evidence']+'\n')
        (root / 'skills/worker/SKILL.md').write_text('---\nstatus: archived\n---\n'+record['owner']['evidence'])
        assert run(root, [record]), 'inactive owner passed'
        (root / 'skills/worker/SKILL.md').unlink()
        assert run(root, [record]), 'deleted owner passed'
        assert run(root, [dict(record, source_path='skills/shelves/topic/deleted/SKILL.md')]), 'stale shelf passed'
        extra = root / 'skills/shelves/topic/new/SKILL.md'
        extra.parent.mkdir()
        extra.write_text('# New\n')
        assert any('missing from inventory' in x for x in run(root, [record])), 'new uninventoried shelf passed'
    print('Shelf owner negative fixtures: PASS')


if __name__ == '__main__':
    main()
