# Self review: #827 R11 scanner shape-space repairs

## Assumptions

Goal source: siege-analytics/claude-configs-public#827
Working as: software engineer and tech lead
Pre-author-inventory: inspected writing-code:8 table from #830, `_extract_optional_imports`, `_name_matches_flag`, one-flag pairing logic, and existing `test_writing_code_8.sh` fixtures z5/R7-F2 through z9.
Investigate-artifact: plans/design-note-827-r11-scanner-shape-space.md
Pre-mortem-artifact: plans/design-note-827-r11-scanner-shape-space.md
Hostile-review-artifact: plans/hostile-review-827-r11-scanner-shape-space.md
Project-contribution: turns the R11 invalidating scanner findings into executable coverage and keeps the shape-space table honest by flipping only the repaired rows to covered.

## Adversarial shape audit

Shape space: writing-code:8 optional-import scanner shapes from the #830 table, with this PR scoped to rows 2-4 only.
Fixture-covered shapes: z6 try/except/else flag; z7 matplotlib.pyplot prefix flag; z8 PySpark one-flag/N-import; z9 guarded counterparts; z5 R7-F2 sole-flag misdirect preservation.
Prose-vs-implementation gap: rows 2-4 now have scanner code plus executable fixtures; rows 5-9 remain `not-covered` / `deferred` in the table.
Adversarial frame this round: PyPI-top-100 CI operator. This frame asks whether dominant package idioms from common optional dependencies work under real CI patterns, and whether a narrow fixture accidentally covers only local examples.

## Peer review

- writing-code:8 PASS - scanner now covers I1/I2/I3 with code paths and executable fixtures.
- writing-rules:8 PASS - coverage table rows 2-4 flipped only after scanner code and fixtures landed; M-shapes stay deferred.
- writing-tests:1 PASS - `test_writing_code_8.sh` grew failing-first fixtures z6/z7/z8/z9 and passes after implementation.
- writing-claims:3 PASS - no class-level claim says all optional-import patterns are covered; table enumerates covered and deferred shapes.
- writing-claims:2 PASS - validation output recorded before commit.

## Lead review

Approved. The implementation directly addresses #827 I1/I2/I3, preserves R7-F2 fail-open protection, and leaves M-shapes explicitly deferred instead of expanding claims beyond evidence.

## Quantified claims

- 3 newly covered writing-code:8 shape rows: table rows 2, 3, and 4.
- 4 new shell fixtures: z6, z7, z8, and z9.
- 33 writing-code:8 fixtures passing after the scanner change.
