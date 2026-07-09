#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

python3 bin/build.py --layout flat >/tmp/ccp-flat-layout-test.log

for slug in code-review qml-component-review; do
  if [[ ! -f "dist/flat/skills/$slug/SKILL.md" ]]; then
    printf 'missing flat top-level skill: %s\n' "$slug" >&2
    exit 1
  fi
done

if [[ -e dist/flat/skills/coding/code-review/SKILL.md ]]; then
  printf 'code-review remained nested in flat layout\n' >&2
  exit 1
fi

python3 - <<'PY'
from pathlib import Path

root = Path('dist/flat/skills')
missing = []
for skill_md in Path('skills').rglob('SKILL.md'):
    rel = skill_md.parent.relative_to('skills')
    if rel.parts and rel.parts[0] == 'shelves':
        continue
    if any((other.parent != skill_md.parent and skill_md.parent in other.parent.parents) for other in Path('skills').rglob('SKILL.md')):
        continue
    slug = skill_md.parent.name
    if not (root / slug / 'SKILL.md').exists():
        missing.append(f'{slug} from {rel}')
if missing:
    raise SystemExit('flat layout missing top-level leaf skills:\n  ' + '\n  '.join(missing))
PY

printf 'flat-skill-layout: ok\n'
