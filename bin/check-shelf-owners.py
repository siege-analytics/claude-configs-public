#!/usr/bin/env python3
"""Check explicit, non-routing shelf consultation ownership against the tracked inventory."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})(.*)$')
ANTI_CONSULT = re.compile(
    r"(?i)\b(?:do not|don't|never|not to)\s+(?:read|open|reference|follow|consult|load|use)\b"
    r"|\bavoid\s+(?:reading|opening|consulting|following)\b"
    r"|\bnot for (?:reading|reference|consultation|use)\b"
    r"|\b(?:archive|archival|historical|record|reference)\s+only\b"
    r"|\bnot a consultation path\b"
)


def prose(text: str) -> str:
    """Owner directives cannot be asserted by frontmatter, fenced examples or HTML comments."""
    if text.startswith('---\n'):
        end = text.find('\n---\n', 4)
        if end >= 0:
            text = text[end + 5:]
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    marker = ''
    visible = []
    for line in text.splitlines():
        match = FENCE.match(line)
        if marker:
            if match and match.group(1)[0] == marker[0] and len(match.group(1)) >= len(marker) and not match.group(2).strip():
                marker = ''
            continue
        if match:
            marker = match.group(1)
            continue
        visible.append(line)
    return '\n'.join(visible)


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
            if not isinstance(quarantine, dict) or set(quarantine) != {'reason'} or not isinstance(quarantine['reason'], str) or len(''.join(quarantine['reason'].split())) < 20:
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
        raw = (root / op).read_text()
        text = prose(raw)
        if re.search(r'(?m)^status:\s*(inactive|archived|retired|deprecated)\b', raw):
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
        if ANTI_CONSULT.search(block):
            errors.append(f'contradictory non-consultation prose in owner section: {path}: {op}')
        if ANTI_CONSULT.search(evidence + ' ' + directive) or re.search(r'(?i)\b(?:unavailable|not shipped|deprecated)\b', evidence + ' ' + directive):
            errors.append(f'negated or archival consultation evidence: {path}: {op}')
        strong = re.search(r'(?i)\b(?:read|consult|load|anchor each review dimension)\b', directive)
        scoped = re.search(r'(?i)\b(?:shel(?:f|ves)|book|reference|lens|path|review dimension)\b', directive) or path in directive
        contextual = re.search(r'(?i)\bfor [^:]+ (?:rationale|design|modeling)\b', directive) and re.search(r'(?i)companion shelves', block)
        if not ((strong and scoped) or contextual):
            errors.append(f'no positive scoped consultation directive: {path}: {op}')
        if path not in directive and not re.search(r'--\s*\S', evidence):
            errors.append(f'path lacks a scoped lens: {path}: {op}')
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
