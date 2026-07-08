---
ticket_refs:
  - siege-analytics/claude-configs-public#621
---

# Self-Review - untracked hygiene quoted paths

## Assumptions

Goal source: siege-analytics/claude-configs-public#621.
Role(s): implementer and reviewer-coordinator.
Pre-author-inventory: late review of PR #620 found that `git status --porcelain` quote-wrapped paths with spaces, causing `--emit-delete-script` to target filenames containing literal double quotes.
Hostile-review-artifact: late fresh review from session `260708-smooth-valley` requested changes; this is the mechanical follow-up.
Inventoried-shape: `scripts/discipline/untracked-hygiene.py`, `scripts/discipline/test_untracked_hygiene.sh`.

## Peer review

Shelf checks:

- Switched path collection to `git status --porcelain=v1 -z --untracked-files=all`.
- Stored decoded real paths in `Entry.path` rather than human-facing quoted paths.
- Added a regression test creating `example 2.md` and asserting the delete template emits `echo rm -rf -- 'example 2.md'` with no embedded double quotes.

## Lead review

[Lead] The bug was fail-safe but made the documented dry-run deletion template unusable for the target class. NUL-delimited porcelain output is the correct Git interface for machine parsing.

[Lead] The fix preserves non-destructive behavior: the tool still only prints `echo rm -rf` templates and never deletes files.

## Quantified claims

- Regression tests added: 1.
- Destructive operations introduced: 0.
- Path collection now uses NUL-delimited Git output: 1 call site.

## Verification commands

```text
bash scripts/discipline/test_untracked_hygiene.sh
python3 scripts/discipline/untracked-hygiene.py --emit-delete-script
python3 -m py_compile scripts/discipline/untracked-hygiene.py
bash skills/detect-ai-fingerprints/scan.sh
python3 bin/sync-skill-references.py --check
python3 bin/build.py
python3 bin/validate-hooks.py dist/claude-code/
python3 bin/validate-hooks.py dist/craft-agent/
```

## Result

Passed locally:

- `bash scripts/discipline/test_untracked_hygiene.sh`: PASS, space-containing duplicate path emitted without Git quote wrapping.
- Live `--emit-delete-script` output checked for embedded Git quote wrapping: none found.
- `python3 -m py_compile scripts/discipline/untracked-hygiene.py`: passed.
- `bash skills/detect-ai-fingerprints/scan.sh`: clean.
- `python3 bin/sync-skill-references.py --check`: clean.
- `python3 bin/build.py`: succeeded.
- `python3 bin/validate-hooks.py dist/claude-code/`: all hooks valid, existing warnings only.
- `python3 bin/validate-hooks.py dist/craft-agent/`: all hooks valid, existing warnings only.
