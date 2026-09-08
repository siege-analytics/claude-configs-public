# Design note: #827 R11 scanner shape-space repairs

## Goal source

siege-analytics/claude-configs-public#827

## Spec source

`skills/_writing-code-rules.md` writing-code:8 shape-space coverage table from PR B+C (#830). PR D may flip only rows 2, 3, and 4 from `not-covered` to `covered`; rows 5-9 remain deferred/not-covered.

## Target repairs

1. I1: `try / except / else` availability flags. Scanner must inspect `ast.Try.orelse` so flags assigned in the success branch pair with imports.
2. I2: dotted-source prefix flags. `import matplotlib.pyplot as plt` must pair with `MATPLOTLIB_AVAILABLE` by recognizing a real dotted prefix boundary.
3. I3: one-flag/N-import dependency families. Multiple imports from the same dependency family, such as PySpark's `pyspark.sql` and `pyspark.sql.functions`, can share `PYSPARK_AVAILABLE`.

## Non-goals

- Do not cover M-shapes from writing-code:8 rows 5-9 in this PR.
- Do not weaken R7-F2 sole-flag misdirect protection: `import re` plus `MRE_AVAILABLE` must still fail open and emit a scanner warning, not bind to the wrong flag.
- Do not change non-writing-code:8 scanner rules.

## Implementation sketch

- Collect availability flag assignments from `node.orelse` in `_extract_optional_imports`.
- Extend `_name_matches_flag` with dotted-prefix matching using an actual `.` boundary.
- Add a sole-flag dependency-family path: when every source module in a try block matches the same sole flag, bind all imports in that try block to the flag. If any source does not match, preserve fail-open behavior.

## Validation

- Add failing-first fixtures z6/z7/z8/z9 to `test_writing_code_8.sh`.
- Confirm fixtures fail on old scanner behavior.
- Confirm all writing-code:8 fixtures pass after scanner repair.
- Run scanner syntax, broader detector tests, build check, and skill reference sync.

### Verified Shapes

**S1** PROBED: old behavior fails z6/z7/z8 while z9 is silent because missing detection fails open.
**S2** PROBED: new behavior fires on unguarded try/except/else flag shape z6.
**S3** PROBED: new behavior fires on unguarded matplotlib dotted-prefix shape z7.
**S4** PROBED: new behavior fires on unguarded PySpark one-flag/N-import shape z8.
**S5** PROBED: guarded dotted-prefix and one-flag/N-import counterparts are silent in z9.
**S6** PROBED: R7-F2 `import re` plus `MRE_AVAILABLE` fixture z5 still fails open with scanner warning and no writing-code:8 emission.

### Tiger 1

**Severity:** HIGH
Likelihood: medium
Mitigation: preserve z5 R7-F2 test and make sole-flag family binding require every source to match the sole flag.
Trigger: scanner suggests `MRE_AVAILABLE` for `re` or otherwise binds unrelated sole flags.
Fallback: remove sole-flag family binding and leave I3 not-covered.

### Tiger 2

**Severity:** MEDIUM
Likelihood: medium
Mitigation: table rows flip only for I1/I2/I3 with fixtures; M rows remain deferred.
Trigger: PR claims AnnAssign/from-star/nested-try/conditional-import/cross-block-shadowing coverage.
Fallback: revert table rows for any unimplemented shape.
