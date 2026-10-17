#!/usr/bin/env python3
"""Validate actionable local Markdown targets and justified shelf supplements."""
from __future__ import annotations
import argparse
import bisect
import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
DEFINITION = re.compile(r'^\s{0,3}\[([^\]]+)\]:\s*(<[^>]+>|\S+)')
REFERENCE = re.compile(r'(?<!!)\[([^\]]+)\](?:\[([^\]]*)\])?(?!\s*[:(])')
BACKTICK = re.compile(r'`([^`\n]+)`')
ACTION = re.compile(r'(?i)\b(read|open|consult|see|load|refer to|before responding|files? to read|reference files?|full|chapter|shipped|available|located|find|includes?|rules? file)\b')
NEGATED = re.compile(r"(?i)\b(?:do not|don't|never|not to)\s+(?:read|open|consult|load|use|follow)\b")
FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})(.*)$')
CLAUSE_BREAK = re.compile(r'(?i);|,\s+|:\s+|\s+--\s+|—|\s+[-–]\s+|\bbut\b|\bthen\b|[.!?]\s+')


def unescape(value: str) -> str:
    """CommonMark backslash escapes for punctuation in a local destination."""
    return re.sub(r'\\([!"#$%&\'()*+,./:;<=>?@\[\]\\^_`{|}~-])', r'\1', value)


def normalize(value: str) -> str:
    value = value.strip()
    if value.startswith('<') and value.endswith('>'):
        value = value[1:-1]
    return unescape(value).split('#', 1)[0]


def inline_links(line: str):
    """Parse balanced/escaped labels and balanced/escaped inline destinations."""
    for opener in re.finditer(r'(?<!!)\[', line):
        start_label = opener.start()
        # An escaped opening bracket is text, not a link label.
        backslashes = len(line[:start_label]) - len(line[:start_label].rstrip('\\'))
        if backslashes % 2:
            continue
        depth = 1
        i = opener.end()
        while i < len(line) and depth:
            char = line[i]
            if char == '\\' and i + 1 < len(line):
                i += 2
                continue
            if char == '[':
                depth += 1
            elif char == ']':
                depth -= 1
            i += 1
        if depth or i >= len(line) or line[i] != '(':
            continue
        start = i + 1
        while start < len(line) and line[start].isspace():
            start += 1
        if start >= len(line):
            continue
        if line[start] == '<':
            i = start + 1
            while i < len(line):
                if line[i] == '\\' and i + 1 < len(line):
                    i += 2
                elif line[i] == '>':
                    yield line[start:i + 1], start_label
                    break
                else:
                    i += 1
            continue
        depth = 0
        i = start
        while i < len(line):
            char = line[i]
            if char == '\\' and i + 1 < len(line):
                i += 2
                continue
            if char == '(':
                depth += 1
                if depth > 32:
                    break
            elif char == ')':
                if depth == 0:
                    if i > start:
                        yield line[start:i], start_label
                    break
                depth -= 1
            elif char.isspace() and depth == 0:
                if i > start:
                    yield line[start:i], start_label
                break
            i += 1


def prose_lines(lines: list[str]):
    """Exclude fenced examples; closers must match opening marker and length."""
    marker = ''
    for number, line in enumerate(lines, 1):
        match = FENCE.match(line)
        if marker:
            if match and match.group(1)[0] == marker[0] and len(match.group(1)) >= len(marker) and not match.group(2).strip():
                marker = ''
            continue
        if match:
            marker = match.group(1)
            continue
        yield number, line


def rendered_link_lines(prose: list[tuple[int, str]]) -> list[str]:
    """Mask literal link syntax in source order, never letting code cross blocks."""
    text = '\n'.join(line for _, line in prose)
    masked = list(text)
    backtick_masked = list(text)  # only comments are non-actionable to path citations
    boundaries = {len(text)}
    offset = 0
    previous_number = None
    previous_line = ''
    block_start = re.compile(r'^ {0,3}(?:#{1,6}(?:\s|$)|(?:[-+*]|\d+[.)])\s+)')
    for number, line in prose:
        if (previous_number is not None and number != previous_number + 1) or not line.strip() or not previous_line.strip() or block_start.match(line):
            boundaries.add(offset)
        if block_start.match(line):
            boundaries.add(offset + len(line) + 1)
        offset += len(line) + 1
        previous_number, previous_line = number, line
    limits = sorted(boundaries)

    def hide(start: int, end: int, *, comment: bool = False) -> None:
        for index in range(start, end):
            if masked[index] != '\n':
                masked[index] = ' '
                if comment:
                    backtick_masked[index] = ' '

    def escaped(index: int) -> bool:
        count = 0
        while index - count - 1 >= 0 and text[index - count - 1] == '\\':
            count += 1
        return count % 2 == 1

    i = 0
    while i < len(text):
        if text.startswith('<!--', i):
            end = text.find('-->', i + 4)
            if end >= 0:
                hide(i, end + 3, comment=True)
                i = end + 3
                continue
        if text[i] == '`' and not escaped(i):
            end_run = i
            while end_run < len(text) and text[end_run] == '`':
                end_run += 1
            length = end_run - i
            limit = limits[bisect.bisect_right(limits, i)] if bisect.bisect_right(limits, i) < len(limits) else len(text)
            j = end_run
            while j < limit:
                if text[j] != '`' or escaped(j):
                    j += 1
                    continue
                close_end = j
                while close_end < limit and text[close_end] == '`':
                    close_end += 1
                if close_end - j == length:
                    hide(i, close_end)
                    i = close_end
                    break
                j = close_end
            else:
                i = end_run  # unmatched backticks are literal, not masking delimiters
            continue
        i += 1
    return ''.join(masked).split('\n'), ''.join(backtick_masked).split('\n')


def target(root: Path, book: Path, value: str) -> Path | None:
    value = unquote(normalize(value))
    if value.startswith(('https://', 'http://', 'mailto:')) or not value or value.startswith('#') or ('<' in value and '>' in value):
        return None
    if value.startswith(('skills/', 'catalog/', 'plans/')):
        return root / value
    return book / value


def candidates(line: str, definitions: dict[str, str], link_line: str, backtick_line: str):
    inline = list(inline_links(link_line))
    for value, start in inline:
        yield value, start, True
    for match in REFERENCE.finditer(link_line):
        key = (match.group(2) or match.group(1)).lower()
        if key in definitions and not any(start == match.start() for _, start in inline):
            yield definitions[key], match.start(), True
    for match in BACKTICK.finditer(backtick_line):
        value = normalize(match.group(1))
        if value.endswith('.md') and (('/' in value and (ACTION.search(line) or value.startswith(('references/', 'rules/', 'skills/', './', '../')))) or (ACTION.search(line) and value.startswith(('ref-', 'practices-catalog.md')))):
            yield value, match.start(), False


def actionable_lines(source: Path):
    prose = list(prose_lines(source.read_text(errors='replace').splitlines()))
    link_lines, backtick_lines = rendered_link_lines(prose)
    definitions = {}
    for link_line in link_lines:
        found = DEFINITION.match(link_line)
        if found:
            definitions[found.group(1).lower()] = found.group(2)
    for (number, line), link_line, backtick_line in zip(prose, link_lines, backtick_lines):
        if DEFINITION.match(link_line):
            continue
        for value, start, is_link in candidates(line, definitions, link_line, backtick_line):
            prefix = (link_line if is_link else line)[:start]
            boundary = list(CLAUSE_BREAK.finditer(prefix))
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
