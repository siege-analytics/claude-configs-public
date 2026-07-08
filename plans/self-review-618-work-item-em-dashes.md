---
ticket_refs:
  - siege-analytics/claude-configs-public#618
---

# Self-Review - work-item ownership em dash cleanup

## Assumptions

Goal source: siege-analytics/claude-configs-public#618.
Role(s): implementer and reviewer-coordinator.
Pre-author-inventory: late review of PR #614 reported literal U+2014 glyphs in `skills/_work-item-ownership-rules.md` and pointed out that `scan.sh --working` was vacuous after commit.
Hostile-review-artifact: late fresh review from session `260708-copper-halo` requested changes; this is the mechanical follow-up.
Inventoried-shape: `skills/_work-item-ownership-rules.md`.

## Peer review

Shelf checks:

- Replaced all literal U+2014 glyphs in `skills/_work-item-ownership-rules.md` with ASCII `--`.
- Counted remaining U+2014 glyphs in the file: 0.
- Will validate with staged/cached scan before commit and a commit-range/PR scan after commit/PR creation.

## Lead review

[Lead] The late reviewer found a real post-merge blocker. The correct fix is small and mechanical: remove the literal glyphs and verify with a non-vacuous scan mode.

[Lead] This does not alter the work-item ownership semantics released in v3.5.15; it only makes the rule file comply with the repository's own prose fingerprint rule.

## Quantified claims

- Literal U+2014 glyphs before fix in released file: 11.
- Literal U+2014 glyphs after fix in edited file: 0.
- Files with semantic rule text changed: 1.

## Verification commands

```text
python3 - <<'PY'
from pathlib import Path
print(Path('skills/_work-item-ownership-rules.md').read_text().count('\u2014'))
PY
bash skills/detect-ai-fingerprints/scan.sh
python3 bin/sync-skill-references.py --check
python3 bin/build.py
python3 bin/validate-hooks.py dist/claude-code/
python3 bin/validate-hooks.py dist/craft-agent/
```

## Result

Passed locally:

- U+2014 count in `skills/_work-item-ownership-rules.md`: 0.
- `bash skills/detect-ai-fingerprints/scan.sh` using default staged-diff mode: clean.
- `python3 bin/sync-skill-references.py --check`: clean.
- `python3 bin/build.py`: succeeded.
- `python3 bin/validate-hooks.py dist/claude-code/`: all hooks valid, existing warnings only.
- `python3 bin/validate-hooks.py dist/craft-agent/`: all hooks valid, existing warnings only.
