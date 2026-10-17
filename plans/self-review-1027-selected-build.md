# Self-review: selected build input (#1027)

Correction status: all acceptance/readiness verdicts on
`d00f73faa216d9617323faac362c2281e1a5412d` are obsolete after the reproduced
generated-path overwrite. Earlier results below remain historical evidence,
not acceptance of that head. See the correction record at the end.

## Assumptions

Domain(s): software engineering
Geospatial cross-cut: no
Working as: author-side implementation session; independent exact-head review remains external.
Goal source: https://github.com/siege-analytics/claude-configs-public/issues/1027
Goal source verification: evaluate-ticket reports template gaps; exemption below.
Plan reference: plans/pre-mortem-1027-selected-build.md
Pre-author-inventory: plans/pre-mortem-1027-selected-build.md#investigation-and-pre-author-inventory
Investigate-artifact: plans/pre-mortem-1027-selected-build.md
Pre-mortem-artifact: plans/pre-mortem-1027-selected-build.md
Hostile-review-artifact: plans/hostile-review-1027-selected-build.md
Project-contribution: explicit component selection through the existing builder and composer, preserving independent policy trust.

## Exemption: parent ticket template

Reason: The accepted architectural issue uses Outcome/Boundaries/Acceptance
rather than the ticket linter's Context/Goal/Assumptions template. The operator
authorized implementation against its two accepted boundary comments.
Evidence: `bash scripts/discipline/evaluate-ticket.sh 1027` reports missing
Context, Goal, evidence token, think path and Assumptions; accepted detailed
plan is https://github.com/siege-analytics/claude-configs-public/issues/1027#issuecomment-6225119253.
Falsification: A discrepancy between that plan, the operator instructions and
the implementation blocks the completion claim regardless of green checks.

## Peer review

Author-side review applies writing-code, writing-tests, writing-claims and
writing-prose; read the data-intensive shelf for derived artifacts and atomic
publication. The existing coordinator/reviewer remains the independent reviewer.

## Lead review

In software engineering, source identity, coherent snapshots, closed schemas,
separate trust inputs and failure before publication are required. No source
build can stand in for actual registration or host capability observation.

## Quantified claims

Baseline identity: `git rev-parse HEAD` returned
c7d9d65e30dfd4450682a63b33fd0b53b979e2a0 with a clean tree.

## Test plan

Run selected build falsification first, existing composition/policy/resident
regressions next, then normal build/freshness and all Python/hook suites at the
committed head. Compare explicit Siege output with the compatibility composer
and preserve the full legacy export. Exercise source omission, changed bytes,
component pairing, candidate trust replacement, dependencies, ambiguity/cycles,
partial output and unsupported capability/backend cases.

## Rework ledger

See the rework ledger update below.

## Evidence-predates-work

This artifact and pre-mortem are written before implementation. The canonical
pre-implementation comment is https://github.com/siege-analytics/claude-configs-public/issues/1027#issuecomment-6227308333; source changes followed it.

## Implementation review checkpoint

The source change adds a closed selected build input and normal build CLI
routing into the existing composer. The immutable Git file reader moved from
package-generation.py to source_snapshot.py and is shared, not duplicated.
Generation still verifies its release/runtime and uses its existing state
machine. The new helper is included in that tool-byte compatibility closure.

The selected result is limited to resolver composition. Backend and capability
requirements fail closed instead of installing the fixed legacy hook stack.
The existing builder/export path remains retained and measured. This is the
operator-permitted reviewable dependency boundary, not completion of #1027.
See examples/selected-build/README.md for every remaining acceptance item.

Peer review against writing-code and writing-tests: source snapshots are read
from exact Git objects; source/descriptor fields and ownership are closed
(ownership claim superseded by the correction record below);
profile adoption is compared to independent registered policy; graph/token/link
validation remains in the existing engine. Tests invoke real subprocesses and
Git objects. The only injected failure is the publication rename error; the
existing destination and invalid-composition failures also use real files.

Lead review in software engineering: the claim matches the mechanism. No
settings, native hooks, runtime installation, activation, rollback or host
observations are inferred from the content receipt. In the data-intensive
shelf's derived-data terms, Git objects are source and generated content is
rebuildable evidence. The temporary build directory prevents rendering errors
from publishing a partial package; cooperating writers serialize. This does
not claim hostile-filesystem atomic registration or replace #1003's stronger
registration boundary.

## Validation evidence at source checkpoint

- `python3 -B bin/_test/package_selection_test.py`: 18 tests, OK, 43.062s;
  `/tmp/cc-1027-selected-tests.log`.
- Existing `project_composition_test.py`: 22 tests, OK;
  `selected_composition_test.py`: 15 tests, OK;
  `/tmp/cc-1027-composition.log`.
- `python3 -B bin/_test/effective_policy_test.py`: 42 tests, OK, 4.722s;
  `/tmp/cc-1027-policy.log`.
- `python3 -B bin/_test/ontology_test.py`: 25 tests, OK, 0.695s;
  `/tmp/cc-1027-ontology.log`.
- Normal build and build-check: exit 0; `/tmp/cc-1027-build-working.log` and
  `/tmp/cc-1027-build-check.log`. Existing token and skill-quality warnings remain.
- Legacy output comparison: `/tmp/cc-1027-legacy-parity.json`, 3379 files on
  both sides, no additions/removals. Thirteen changed files contain timestamps
  or the added high-risk path patterns; all other bytes match the exact base.
- Exact committed-head full matrix, final parity and source hygiene receipts
  will be posted to #1027 and the draft PR before handoff. No passing result
  for that matrix is claimed at this pre-commit checkpoint.

Syntax check: ast.parse passed on all 8 modified Python files before commit.
Doc build: ontology.py --write/--check generates and verifies wiki/Ontology.md;
no Sphinx tree or notebook is changed. Independent source review is pending.

## Rework ledger update

| Rework trigger | Root cause | Correction |
| --- | --- | --- |
| Initial selection test expected a different diagnostic punctuation | Assertion omitted the validator's colon | Match the actual deterministic diagnostic |
| Siege example passed an unknown operation type | Corpus used commit instead of bounded ticket-commit | Use the existing type/message contract |
| Ontology negative tests stopped before intended checks | New bound descriptor absent from synthetic setup | Copy the new fixture and increase exact binding count by its two fields |
| Risk freshness test rejected generated inventory | Later source edits invalidated earlier inventory generation | Regenerate after source freeze, before exact-head matrix |

Verified-by: the commands and host-local evidence paths above; terminal committed-head receipts belong on the issue and PR.

## Scanner disclosure

The unfiltered staged scanner was run; it is not green. Its whole-file AST
pass reports pre-existing unbounded subprocess calls in build.py and the
existing ontology/risk tests, and cannot discover bin/_test exception tests
for build.py or package-generation.py. The generated wiki uses the existing
generator's middle-dot/arrow typography. These are disclosed findings, not
suppressed by a scanner/policy change or described as a passing scan. New
lexical findings in authored prose were corrected. Publication remains draft
for review with the operator-requested dependency handoff; these findings
are part of the review evidence. The normal Git hooks remain mandatory.

## Committed-fixture correction

The first committed-head example failed because a clean clone already contained
the selected fixture sources and git commit correctly refused an empty commit.
The initial matrix was stopped after its early freshness checks, not accepted.
The fixture now returns the existing exact revision when its index/worktree is
clean; changed synthetic sources still receive a fixture commit. The existing
executable-example test covers both construction states on committed replay.
Evidence: /tmp/cc-1027-example-siege-committed.log.

## Generated ownership correction: pre-commit review

Trigger: [PR blocker 6227734449](https://github.com/siege-analytics/claude-configs-public/pull/1031#issuecomment-6227734449)
and [issue backlink 6227739609](https://github.com/siege-analytics/claude-configs-public/issues/1027#issuecomment-6227739609).
The original assumption quoted above is preserved and superseded, not deleted.
The [pre-fix post-error revision](https://github.com/siege-analytics/claude-configs-public/issues/1027#issuecomment-6227762888)
records the red replay, intended correction and failure risks before source edits.

Exact rejected source: head d00f73faa216d9617323faac362c2281e1a5412d,
tree c9a513dac10e7927e15173fbd369a3891ca4620b,
parent c7d9d65e30dfd4450682a63b33fd0b53b979e2a0.
The exact posted probe was extracted verbatim and run before source changes:

```text
declared 0
SECOND_PUBLISHER_BYTES
reversed 0
FIRST_PUBLISHER_BYTES
AssertionError: duplicate generated path was published
```

Evidence: `cache/selected-build-correction/parent-collision-red.log`.
Two distinct pinned sources, `bundles/first/skills/outer/inner/shared.txt` and
`bundles/second/skills/outer/inner/shared.txt`, reached the same nested target
`skills/outer/inner/shared.txt`. Source inventory uniqueness did not imply
output uniqueness. Both receipts retained their source pins despite lost bytes.

The revised invariant is checked at `GeneratedFiles.add`: a generated target
has one claim, independent of bytes or order. Rendered primary skills, assets,
rules, resident/rules bundles, manifests, copied resolver tools and composition
receipts use this insertion function. NFC/casefold identity and ancestor claims
also reject portable aliases and file/directory conflicts. Diagnostic owners
contain selected slugs and source-relative paths, never absolute source roots
or file contents. Both layouts finish validation in memory before writes.
The existing selected builder's staged publication remains unchanged.

The exact posted probe now exits 0 with both inner builds rejecting:

```text
declared 1: generated path collision 'skills/outer/inner/shared.txt'
reversed 1: generated path collision 'skills/outer/inner/shared.txt'
```

Each actual JSON diagnostic names both source paths and reports
`authorization_effect: none`; neither destination exists. Full output is in
`cache/selected-build-correction/parent-collision-green.log`.
The new nested and flat/router tests were also replayed with the corrected test
files over the exact original product source. Each entry path reports eight
failed subcases across two tests, all caused by successful publication where
rejection was expected (`direct-revert-red.log`, `selected-revert-red.log`).

### Peer and lead review of the correction

Working as: author-side correction and adversarial self-review, not independent
review. Reading for: the accepted one-composer/no-order-precedence contract.
Predicted failures: equal bytes silently deduplicated, primary or reserved
assignments bypassing the guard, flat rejection after nested output is written.

The data-intensive shelf's derived-data lens applies: pinned Git objects remain
the source of record; packages are rebuildable projections. Previously corrupted
packages can outlive a code fix, so old-head verdicts are obsolete and consumers
must rebuild from the corrected source. This session performs no registration.

The call chain is normal copied `build.py --selection`, `package_selection.build`,
`compose-project.package`, `GeneratedFiles.add`, then publication. Existing direct
composer, graph, resident and installed resolver callers are included in the
focused/dependent replay. Tests load `bin/compose-project.py` by an absolute
path from their checkout, or copy that exact file into the isolated source;
selected builds additionally enforce scaffold byte equality. No editable install
or mock renderer supplies the evidence.

The shared hostile corpus executes both public CLIs, both publisher orders,
equal/different bytes, nested and flat-only router collisions, file/directory
and Unicode aliases, output absence, sentinel preservation, and preservation
of a previously built complete package. Qualified publishers retain both assets
in each layout and repeated identical selections yield byte-identical output.
The primary/asset case alias rejects during discovery on case-insensitive
filesystems; on case-sensitive filesystems it reaches the insertion check.
Root-level primary skills already fail canonical-path validation, so a fake
root fixture is not presented as generated-resident collision coverage.
Direct insertion tests cover primary, rule and reserved/generated target claims
with equal and different bytes, asserting the first claim is never overwritten.

Review-risk already classifies the composer and both suites as Tier C; no
classifier or policy changes are needed. Algorithmic work is proportional to
path depth per assignment. No alternate evaluator, output precedence, or
registration mechanism was added. Independent review remains required.

### Correction validation and scanner disclosure

Working-source direct suite: 22 tests passed. The focused/dependent ledger is
`cache/selected-build-correction/focused.json`; the exact committed-head full
matrix and exhaustive legacy parity will be posted to #1031 and #1027 before
handoff. This pre-commit record does not claim those future runs have passed.

The unfiltered working scanner reports one finding: writing-tests-5 cannot find
tests for the composer's unchanged CLI exception handler in `bin/_test`.
The same finding is reproduced on the exact original composer by `scan_ast.py`
(`scanner-parent.log`). The staged scan will retain and disclose it; no ignore
filter, annotation, scanner change or hook bypass is used. Full-PR findings
inherited from d00f73f remain separate from this correction's scan.

### Correction rework ledger

| Trigger | Cause | Correction |
| --- | --- | --- |
| Initial red subcases contaminated later subcases | Bad output survived a failed assertion | Remove only fixture output before the next independent attempt |
| Root reserved-file fixture failed before ownership check | Root skill produces noncanonical `skills/./SKILL.md` | Cover reserved claims directly without widening accepted source layouts |
| Primary case alias rejected during discovery | Case-insensitive source glob sees the alias as a skill | Accept that specific earlier rejection; retain insertion coverage separately |
| Repeated pinned build tried an empty fixture commit | Seal helper always committed | Reuse the exact revision when synthetic source is clean |
| Unicode owner assertion differed from Git snapshot | Git precomposes Unicode names on this filesystem | Compare source-relative diagnostic names in NFC |

Verified-by: the exact posted red/green probe, original-source negative replay,
focused ledger and subsequent exact committed-head comment; no independent
ACCEPT, registration completion or merge is asserted.

## Further falsification before publication: Unicode folding

The unpublished candidate a9db468a9ee99fd7e3cc88143631fc1f8899f713 passed
ordinary case and Unicode-normalization probes but failed their combination.
Its partial full-suite run is historical, not an acceptance matrix. The earlier
NFC/casefold claim above is superseded by canonical caseless comparison.

The real copied builder accepted source filenames `\u0390.txt` and
`\u03aa\u0301.txt` from the two publishers at the colliding nested directory.
It returned 0 and the filesystem retained only `SECOND_PUBLISHER_BYTES`.
Evidence: `cache/selected-build-correction/unicode-collision-red.log`.
The pre-fix [post-error revision](https://github.com/siege-analytics/claude-configs-public/issues/1027#issuecomment-6228028656)
records this falsification before the further source change.

`GeneratedFiles.add` now compares `NFD(casefold(NFD(path)))`, normalizing both
before and after folding. Original names remain in diagnostics. The shared
hostile corpus includes this mixed case/normalization pair through both CLIs,
both orders and both absent/existing destinations. The separate Unicode probe
and targeted regressions must pass before the next commit; the full matrix and
legacy parity restart at that final committed head. Neither prior commit is
rewritten. No published green claim is based on the interrupted candidate run.

Two harness assumptions were exposed while keeping disposable work under this
checkout: a documentation test mistook its nested fixture path for source-root
leakage, and a scanner non-repository fixture inherited the outer repository by
Git upward discovery. The unchanged documentation test passes from an exact-head
isolated clone with temporary files outside that clone. Test processes now bound
Git discovery at the temporary-fixture parent. Both original failures are kept;
no product assertion, scanner or hook was disabled.

Further-correction green checkpoint: the direct and copied-builder alias tests
both pass (one test each, with the complete alias/order/destination subcases).
The separate mixed-Unicode probe rejects with both owners and no output. The
original posted F1 probe also passes again. These are working-source results;
final committed-head receipts remain required before push.
