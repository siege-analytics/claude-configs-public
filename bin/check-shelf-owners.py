#!/usr/bin/env python3
"""Check explicit, non-routing shelf consultation ownership against the tracked inventory."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(root: Path) -> list[str]:
    inventory = json.loads((root / 'catalog/skills-inventory.json').read_text())
    catalog = json.loads((root / 'catalog/shelf-ownership.json').read_text())
    sources = {item['source_path']: item for item in inventory['items']}
    expected = {p.relative_to(root).as_posix() for p in (root / 'skills/shelves').glob('*/SKILL.md')}
    expected.update(p.relative_to(root).as_posix() for p in (root / 'skills/shelves').glob('*/*/SKILL.md'))
    inventoried = {p for p in sources if p.startswith('skills/shelves/') and len(Path(p).parts) >= 4 and p.endswith('/SKILL.md')}
    errors: list[str] = []
    for path in sorted(expected - inventoried):
        errors.append(f'shelf source missing from inventory: {path}')
    for path in sorted(inventoried - expected):
        errors.append(f'deleted shelf still in inventory: {path}')
    if catalog.get('schema_version') != 1 or not isinstance(catalog.get('records'), list):
        return ['invalid shelf-ownership schema']
    records = catalog['records']
    paths = [r.get('source_path') for r in records]
    if len(paths) != len(set(paths)):
        errors.append('duplicate shelf source_path')
    for path in sorted(expected - set(paths)):
        errors.append(f'missing shelf record: {path}')
    for path in sorted(set(paths) - expected, key=str):
        errors.append(f'stale/deleted shelf record: {path}')
    for record in records:
        path = record.get('source_path')
        if path not in expected:
            continue
        if not (root / path).is_file():
            errors.append(f'missing shelf source: {path}')
        owner, quarantine = record.get('owner'), record.get('quarantine')
        if bool(owner) == bool(quarantine) or set(record) != ({'source_path', 'owner'} if owner else {'source_path', 'quarantine'}):
            errors.append(f'exactly one owner or quarantine required: {path}')
            continue
        if quarantine:
            if not isinstance(quarantine, dict) or set(quarantine) != {'reason'} or not isinstance(quarantine['reason'], str) or not quarantine['reason'].strip():
                errors.append(f'quarantine reason required: {path}')
            continue
        if not isinstance(owner, dict) or set(owner) != {'source_path', 'evidence', 'directive'}:
            errors.append(f'owner path, evidence and scoped directive required: {path}')
            continue
        op = owner['source_path']
        evidence, directive = owner['evidence'], owner['directive']
        item = sources.get(op)
        if not isinstance(op, str) or not item or not op.startswith('skills/') or not op.endswith('/SKILL.md') or op.startswith('skills/shelves/') or item['kind'] not in {'skill', 'skill-router'} or item.get('lifecycle') in {'retired', 'deprecated', 'archived'} or not (root / op).is_file():
            errors.append(f'owner must be active non-shelf SKILL.md: {path}: {op}')
            continue
        text = (root / op).read_text()
        if re.search(r'(?m)^status:\s*(inactive|archived|retired|deprecated)\b', text):
            errors.append(f'inactive owner: {path}: {op}')
        if not isinstance(evidence, str) or not evidence.strip() or evidence not in text.splitlines() or path not in evidence:
            errors.append(f'missing explicit scoped consultation evidence: {path}: {op}')
            continue
        if not isinstance(directive, str) or not directive.strip() or directive not in text.splitlines():
            errors.append(f'missing explicit scoped consultation directive: {path}: {op}')
            continue
        # The path-specific lens and the positive instruction must be within
        # the same Markdown section; a remote generic header is insufficient.
        pos = text.index(evidence)
        section_start = text.rfind('\n## ', 0, pos)
        section_end = text.find('\n## ', pos)
        block = text[section_start if section_start >= 0 else 0:section_end if section_end >= 0 else len(text)]
        if directive not in block or abs(block.index(directive) - block.index(evidence)) > 1800:
            errors.append(f'directive must accompany evidence in same section: {path}: {op}')
        if re.search(r'(?i)\b(?:do not|never|not to)\s+(?:read|consult|load|use)|\bnot for reading\b|\b(?:archive|archival|historical|record)\s+only\b', block):
            errors.append(f'contradictory non-consultation prose in owner section: {path}: {op}')
        if re.search(r'(?i)\b(do not (?:read|consult|load)|not for (?:reading|consultation|use)|never (?:read|consult|load)|archiv(?:e|al|ed)|unavailable|not shipped|deprecated|historical)\b', evidence + ' ' + directive):
            errors.append(f'negated or archival consultation evidence: {path}: {op}')
        if not re.search(r'(?i)\b(read|consult|load|anchor each review dimension|for [^:]+ rationale|for [^:]+ design|for [^:]+ modeling)\b', directive):
            errors.append(f'no positive scoped consultation directive: {path}: {op}')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    errors = check(args.root)
    for error in errors:
        print(error)
    if not errors:
        print('Shelf ownership: inventory parity and exclusive evidenced owner/quarantine OK')
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
