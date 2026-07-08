---
ticket_refs:
  - siege-analytics/claude-configs-public#617
---

# Self-Review - untracked workspace hygiene

## Assumptions

Goal source: siege-analytics/claude-configs-public#617.
Role(s): implementer and reviewer-coordinator.
Pre-author-inventory: collapsed `git status --porcelain` showed 111 untracked entries: 85 number-suffixed duplicate/copy paths, 12 untracked skill/rule tree paths, 8 other paths, 2 Python cache paths, 2 plan artifacts, 1 IDE config path, and 1 stale generated output path. The new inventory tool uses `--untracked-files=all`, so it expands directories and reports 141 file-level entries after local/generated ignores apply.
Hostile-review-artifact: not required for this non-destructive policy/tooling change; no files are deleted.
Inventoried-shape: `.gitignore`, `scripts/discipline/`, `docs/`.

## Peer review

Shelf checks:

- Added a read-only inventory tool: `scripts/discipline/untracked-hygiene.py`.
- Tool classifies untracked paths and can emit a dry-run deletion template for number-suffixed duplicate/copy paths only.
- Added `.gitignore` entries only for clearly local/generated categories: `.idea/`, `dist.stale/`, `__pycache__/`, `*.py[cod]`.
- Added `docs/untracked-hygiene.md` documenting that broad `git clean -fd` is not the default workflow.
- Did not delete any untracked files.

## Lead review

[Lead] This satisfies the safety boundary: the branch creates inventory and policy, not destructive cleanup. Ambiguous paths remain visible for explicit review rather than being hidden by broad ignores.

[Lead] The script makes future cleanup reviewable by producing exact path lists and echo-prefixed deletion templates.

## Quantified claims

- Current collapsed untracked entries inventoried before ignore changes: 111.
- Current file-level untracked entries reported by the new tool after ignore changes: 141.
- Categories ignored by policy update: 4 narrow local/generated patterns.
- Deleted files: 0.
- New product files: 2.

## Verification commands

```text
python3 scripts/discipline/untracked-hygiene.py
python3 scripts/discipline/untracked-hygiene.py --json
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

- `python3 scripts/discipline/untracked-hygiene.py`: reported 141 file-level entries, all classified as number-suffixed duplicate/copy or plan artifact after local/generated ignores apply.
- `python3 scripts/discipline/untracked-hygiene.py --json`: succeeded.
- `python3 scripts/discipline/untracked-hygiene.py --emit-delete-script`: succeeded and emitted echo-prefixed dry-run removals only.
- `python3 -m py_compile scripts/discipline/untracked-hygiene.py`: passed.
- `bash skills/detect-ai-fingerprints/scan.sh`: clean.
- `python3 bin/sync-skill-references.py --check`: clean.
- `python3 bin/build.py`: succeeded.
- `python3 bin/validate-hooks.py dist/claude-code/`: all hooks valid, existing warnings only.
- `python3 bin/validate-hooks.py dist/craft-agent/`: all hooks valid, existing warnings only.
