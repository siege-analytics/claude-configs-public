# Self-review: scanner and hook audit gaps after PR D

Issue: siege-analytics/claude-configs-public#837

## Assumptions

- The work should target develop first through a feature branch.
- The scope is limited to scanner, hook, fixture, and review-routing documentation surfaces named in the issue.
- Scanner self-edits may use the documented `--ignore 'skills/detect-ai-fingerprints/*'` bootstrap path for the scanner preflight.
- Shelf references in code-review should be checked for routing, but no shelf content should change unless a broken route is found.

## Peer review

Changed surfaces:

- `hooks/git/pr-base-guard.sh`
- `hooks/git/detect-ai-fingerprints.sh`
- `hooks/_test/pr_base_guard.test.sh`
- `skills/detect-ai-fingerprints/scan.sh`
- `skills/detect-ai-fingerprints/scan_ast.py`
- `skills/detect-ai-fingerprints/test_rule_citations.sh`
- `skills/detect-ai-fingerprints/test_scan_sh_exit_code.sh`
- `skills/detect-ai-fingerprints/test_writing_code_8.sh`
- `skills/detect-ai-fingerprints/SKILL.md`
- `skills/code-review/SKILL.md`
- `skills/_coverage.md`

Correctness checks:

- PR base parsing now uses the quote-stripped command surface already built for trigger detection. That prevents body prose from changing base, head, or bypass parsing.
- Body-only message scans no longer lose line 1. Full commit-message scans keep the subject-line exemption through `--commit-message-file`.
- The writing-code:8 safe-region fix only expands Try classification to include else-branch success flags. It does not relax public callsite guarding.
- The Bash 3.2 empty-array repair only changes how the AST scanner process is invoked when no config args exist.
- The documented scanner-self ignore path now skips ignored added lines before regex work, so ignored fixture content is not processed before emission is suppressed.

Regression checks:

- R7-F2 optional-import fail-open protection remains covered by fixture `(u)` in `test_writing_code_8.sh`.
- PR D #827 fixtures `(z6)`, `(z7)`, `(z8)`, and `(z9)` remain passing.
- Hook `detect-ai-fingerprints` remains scoped to commit bodies because it now calls full-message mode.

## Lead review

Scope control:

- The diff stays within scanner, hook, fixture, and coverage documentation files.
- No main branch writes were made.
- No shelf router edits were made because the apparent `shelves--<slug>` references are valid build slugs.
- No docs consistency test was added because the available test surfaces validate references and build layout, not natural-language coverage claims.

Shelf-readiness and routing:

- `skills/code-review/SKILL.md` companion shelf refs were checked against `bin/build.py` slug rules. The `shelves--clean-code`, `shelves--design-patterns`, `shelves--refactoring-patterns`, `shelves--effective-java`, and `shelves--effective-kotlin` forms are valid for nested shelf skills.
- The fixed routing issue is the scanner path in `skills/code-review/SKILL.md`: it now points at `skills/detect-ai-fingerprints/scan.sh`, the file present in the repo.

## Quantified claims

Validation performed after repairs:

```text
bash -n hooks/git/pr-base-guard.sh hooks/git/detect-ai-fingerprints.sh skills/detect-ai-fingerprints/scan.sh skills/detect-ai-fingerprints/test_scan_sh_exit_code.sh
bash skills/detect-ai-fingerprints/test_scan_sh_exit_code.sh
bash skills/detect-ai-fingerprints/test_rule_citations.sh
bash skills/detect-ai-fingerprints/test_writing_code_8.sh
bash hooks/_test/pr_base_guard.test.sh
bash hooks/_test/detect_ai_fingerprints.test.sh
python3 -m py_compile skills/detect-ai-fingerprints/scan_ast.py
git diff --check
python3 bin/sync-skill-references.py --check
python3 bin/build.py --check
bash skills/detect-ai-fingerprints/scan.sh --ignore 'skills/detect-ai-fingerprints/*'
```

Observed counts:

- `test_scan_sh_exit_code.sh`: 11 passed, 0 failed.
- `test_writing_code_8.sh`: 34 passed, 0 failed.
- `pr_base_guard.test.sh`: 36 scenarios passed.
- `detect_ai_fingerprints.test.sh`: 5 passed, 0 failed.
- `bin/build.py --check`: 156 leaf skills, 35 rules, 3 project skills, 1 project rules discovered.

Failing-first evidence was collected before repairs:

- The new `(af2)` quoted-body PR fixture failed before the parser repair.
- The new body-only first-line message fixture failed before the message scanner repair.
- The new `(z6b)` try-body setup fixture failed before the writing-code:8 safe-region repair.
- `scan.sh --working` exposed the empty config array error before the invocation repair.

A raw working-diff scanner run without the documented bootstrap ignore reports the scanner editing its own `scan_ast.py` exception handlers, which is expected for scanner self-edits.

## Decision

Ready for PR to develop. No direct main push.
