# Hostile review: #827 R11 scanner shape-space repairs

Frame: PyPI-top-100 CI operator maintaining optional integrations across scientific/data packages.

## Review surface

- `skills/detect-ai-fingerprints/scan_ast.py`
- `skills/detect-ai-fingerprints/test_writing_code_8.sh`
- `skills/_writing-code-rules.md`
- `CHANGELOG.md`
- `plans/design-note-827-r11-scanner-shape-space.md`
- `plans/self-review-827-r11-scanner-shape-space.md`

## Category 10c scanner-shape coverage audit

Question: did this PR merely update prose/table rows, or did it provide AST/control-flow-aware scanner behavior plus executable fixture evidence for each newly covered shape?

Answer: PASS.

- Row 2 I1 has implementation evidence: `_extract_optional_imports` reads `ast.Try.orelse` for availability flag assignment. Fixture evidence: z6 fails before the code patch and passes after it.
- Row 3 I2 has implementation evidence: `_name_matches_flag` accepts a real dotted-boundary source-prefix match, e.g. `matplotlib.pyplot` -> `MATPLOTLIB_AVAILABLE`. Fixture evidence: z7 fails before the code patch and passes after it.
- Row 4 I3 has implementation evidence: sole-flag dependency-family binding is allowed only when all source modules in the try block match the sole flag. Fixture evidence: z8 catches unguarded `udf`; z9 shows guarded counterparts remain silent.
- R7-F2 remains protected: z5 still proves `import re` + `MRE_AVAILABLE` fails open with `scan-ast-warning`, avoiding wrong-flag suggestions.

## Adversarial probes

### Probe 1: dangerous sole-flag broadening

Attack: The one-flag/N-import change could bind unrelated imports to one flag and manufacture false writing-code:8 claims.

Result: PASS. Binding all imports is allowed only when every source module matches the sole flag by exact/dotted-prefix/collapsed form. If one source does not match, the scanner retains the existing fail-open path and warning. Existing z5 and z5-style no-stem-match cases remain locked.

### Probe 2: dotted-prefix over-match

Attack: Prefix matching could turn substring matches into false positives, such as `re` matching `MRE_AVAILABLE` or `foo` matching `foobar`.

Result: PASS. Prefix matching requires `src_fold.startswith(stem_fold + ".")`, so it applies to dotted package boundaries, not arbitrary substrings.

### Probe 3: prose overclaiming

Attack: Updating rows 2-4 might imply all writing-code:8 optional-import variants are covered.

Result: PASS. Rows 5-9 remain not-covered/deferred; self-review explicitly names the non-goal and the table keeps the uncovered shape-space visible.

### Probe 4: fixture-only illusion

Attack: Tests could pass because they search broad output, not because scanner pairs the right flag.

Result: PASS with note. z7/z8 assert both the binding name and expected flag in scanner output; z9 asserts guarded counterparts are silent. This is adequate for this shell fixture style and is backed by code-path inspection.

## Validation observed

- Failing-first run before scanner patch: 30 passed, 3 failed; failing fixtures z6/z7/z8.
- After patch: `bash skills/detect-ai-fingerprints/test_writing_code_8.sh` -> 33 passed, 0 failed.
- Full detector suite: all `skills/detect-ai-fingerprints/test_*.sh` passed.
- `python3 bin/sync-skill-references.py --check` passed.
- `python3 bin/build.py --check` passed.

## Verdict

PASS. This PR may proceed as a concrete #827 repair, not merely meta-governance. It is properly scoped to I1/I2/I3 and does not claim M-shape coverage.
