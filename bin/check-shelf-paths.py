#!/usr/bin/env python3
"""Validate actionable local Markdown targets and justified shelf supplements."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
INLINE = re.compile(r'(?<!!)\[([^\]]+)\]\(\s*(<[^>]+>|[^\s)]+)')
DEFINITION = re.compile(r'^\s{0,3}\[([^\]]+)\]:\s*(<[^>]+>|\S+)')
REFERENCE = re.compile(r'(?<!!)\[([^\]]+)\](?:\[([^\]]*)\])?(?!\s*[:(])')
BACKTICK = re.compile(r'`([^`\n]+)`')
ACTION = re.compile(r'(?i)\b(read|open|consult|see|load|refer to|before responding|files? to read|reference files?|full|chapter|shipped|available|located|find|includes?|rules? file)\b')
NEGATED = re.compile(r"(?i)\b(?:do not|don't|never|not to)\s+(?:read|open|consult|load|use|follow)\b")
FENCE = re.compile(r'^\s*(```|~~~)')


def normalize(value: str) -> str:
    value = value.strip()
    if value.startswith('<') and value.endswith('>'):
        value = value[1:-1]
    return value.split('#', 1)[0]


def target(root: Path, book: Path, value: str) -> Path | None:
    value = unquote(normalize(value))
    if value.startswith(('https://', 'http://', 'mailto:')) or not value or value.startswith('#') or ('<' in value and '>' in value):
        return None
    if value.startswith(('skills/', 'catalog/', 'plans/')):
        return root / value
    return book / value


def candidates(line: str, definitions: dict[str, str]):
    for match in INLINE.finditer(line):
        yield match.group(2), match.start(), True
    # Reference definitions only become actionable when referenced in this file.
    for match in REFERENCE.finditer(line):
        key = (match.group(2) or match.group(1)).lower()
        if key in definitions and not INLINE.match(line, match.start()):
            yield definitions[key], match.start(), True
    for match in BACKTICK.finditer(line):
        value = normalize(match.group(1))
        if value.endswith('.md') and (('/' in value and (ACTION.search(line) or value.startswith(('references/', 'rules/', 'skills/', './', '../')))) or (ACTION.search(line) and value.startswith(('ref-', 'practices-catalog.md')))):
            yield value, match.start(), False


def actionable_lines(source: Path):
    lines = source.read_text(errors='replace').splitlines()
    definitions: dict[str, str] = {}
    fenced = False
    for line in lines:
        if FENCE.match(line):
            fenced = not fenced
        elif not fenced:
            found = DEFINITION.match(line)
            if found:
                definitions[found.group(1).lower()] = found.group(2)
    fenced = False
    for number, line in enumerate(lines, 1):
        if FENCE.match(line):
            fenced = not fenced
            continue
        if fenced or DEFINITION.match(line):
            continue
        for value, start, is_link in candidates(line, definitions):
            # Semicolon-separated instructions are independent: a negated example
            # cannot suppress an actionable missing target later on the same line.
            prefix = line[:start]
            boundary = list(re.finditer(r'(?i);|\bbut\b|\bthen\b|[.!?]\s+', prefix))
            clause = prefix[boundary[-1].end():] if boundary else prefix
            if NEGATED.search(clause):
                continue
            value = normalize(value)
            if value.startswith('plans/') and 'unavailable historical' in line.lower() and 'not shipped' in line.lower():
                continue
            if not is_link and '/' not in value and not value.startswith(('ref-', 'practices-catalog.md')):
                continue
            if value.endswith('.md'):
                affirmative = bool(re.search(r'(?i)\b(read|consult|open|see|load|refer to)\b', clause))
                yield number, value, is_link or affirmative


def check(root: Path) -> list[str]:
    errors: list[str] = []
    shelf = root / 'skills/shelves'
    allowed = json.loads((root / 'catalog/shelf-reference-exceptions.json').read_text())['empty_placeholders']
    if not isinstance(allowed, dict):
        return ['invalid empty placeholder exceptions']
    seen_empty = set()
    for book in sorted(shelf.glob('*/*/SKILL.md')):
        refs = sorted((book.parent / 'references').rglob('*.md'))
        linked = set()
        for source in book.parent.rglob('*.md'):
            if source in refs:
                continue
            linked.update(dest.resolve() for _, value, justifies in actionable_lines(source)
                          if justifies and (dest := target(root, source.parent, value)) is not None)
        for ref in refs:
            rel = ref.relative_to(root).as_posix()
            if ref.resolve() in linked:
                continue
            if rel in allowed and isinstance(allowed[rel], str) and allowed[rel].strip() and ref.stat().st_size <= 1:
                seen_empty.add(rel)
            else:
                errors.append(f'unjustified orphan supplemental reference: {rel}')
    for rel in sorted(set(allowed) - seen_empty):
        errors.append(f'stale/nonempty/linked placeholder exception: {rel}')
    for source in sorted(shelf.rglob('*.md')):
        if source.name != 'SKILL.md' and 'references' not in source.relative_to(shelf).parts:
            continue
        for line_no, value, _ in actionable_lines(source):
            dest = target(root, source.parent, value)
            if dest is not None and (not dest.is_file() or not dest.resolve().is_relative_to(root.resolve())):
                errors.append(f'missing local target: {source.relative_to(root)}:{line_no}: {value}')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    errors = check(args.root)
    for error in errors:
        print(error)
    if not errors:
        print('Shelf paths: actionable targets and supplemental reference justification OK')
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
