# Self-review: selected build input (#1027)

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
from exact Git objects; source/descriptor fields and ownership are closed;
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
