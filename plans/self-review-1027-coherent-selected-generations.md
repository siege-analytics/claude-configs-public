# Self-review: coherent selected generations (#1027)

## Assumptions

Domain(s): software engineering
Geospatial cross-cut: no
Working as: author-side implementation; independent acceptance remains external.
Goal source: https://github.com/siege-analytics/claude-configs-public/issues/1027
Goal source verification: BLOCK: ticket 1027 has gaps before it is fit for execution; exemption below.
Plan reference: plans/pre-mortem-1027-coherent-selected-generations.md
Pre-author-inventory: plans/pre-mortem-1027-coherent-selected-generations.md#investigation-and-pre-author-inventory
Investigate-artifact: plans/pre-mortem-1027-coherent-selected-generations.md
Pre-mortem-artifact: plans/pre-mortem-1027-coherent-selected-generations.md
Hostile-review-artifact: plans/hostile-review-1027-coherent-selected-generations.md
Project-contribution: coherent selected package transitions and exact rollback without transferring policy or provider authority.

## Exemption: parent ticket template

Reason: The approved architectural issue uses Outcome/Boundaries/Acceptance;
the operator supplied explicit implementation/proof requirements for this dependency.
Evidence: evaluate-ticket reports missing Context/Goal/evidence token/think reference/
Assumptions. Accepted boundary comments are 6225067704 and 6225119253.
Falsification: Any mismatch with those boundaries blocks completion regardless of CI.

## Peer review

Apply writing-code/tests/claims/prose, public-contract review and the nested DDIA
shelf. Source identity, derived inventories, adoption pins and operation evidence
are separate. Tests must run the real build, registration, resolver and Git path.
The public-chain review found two candidate defects: rewriting declaration JSON
changed emitted bytes, and checking an older strict runtime against the caller's
new scaffold blocked rollback. Preserve exact input bytes and validate each
retained package with its own pinned normal builder. The independent and initial
Siege examples pass; the strengthened Siege scaffold replay remains pending.

## Lead review

In software engineering: one selector and one evaluator, deterministic ownership,
explicit independent inputs and failure before usable activation are the standards.
In persisted data: retained immutable payloads plus a single epoch token provide
rollback; old evidence cannot become current merely because bytes match again.
Independent hostile acceptance is external; this author artifact cannot supply it.

## Test plan

Hostile red/green baseline; bundle-only/scaffold-only/project-only/policy/registration
changes; wrong component pairs/profile/pins, changed source/package/settings/native
bytes, stale receipts/tokens, locks, existing targets, symlinks/path escapes,
interruption before publication and actual process death, cleanup preservation;
then coherent upgrade and exact prior-set rollback at a new epoch. Run actual
native allow/deny/no-op/option-like names and resolver/settings consumers at each
transition. Preserve custom skills, resident content and operator settings.

Final exact-head matrix: build/check; every generated freshness command; all Python,
hook/scanner suites; package/provider/native/registration/generation tests; independent
and Siege executable fixtures; exact bytes/modes/inventory/settings/decision parity;
source syntax and unfiltered scanner disclosure. Retain failed runs. Test fixtures
stay inside this workspace with canonical paths and a bounded Git discovery ceiling.

## Adversarial shape audit

Shape space: independently versioned Git inputs; JSON declarations, command/event
vectors, stable registration versus selected runtime, epoch tokens and OS failure
boundaries. Frame: concurrent reader/operator trying to falsify a coherent switch.
Prose claims require executable paths and negative fixtures, not green summaries.

## Findings

No new accepted-parent defect was found. Candidate staging/rollback defects are
local to this extension and are recorded below. Accepted parent source is not
rewritten. Normal registration/native parser and policy algorithms stay intact.

## Quantified claims

`git rev-parse HEAD`: 9a884ec172f7c5cddbbc0edc5626807f18fb5f66.
Working evidence: initial complete generation suite passed 10 tests in 231.222s;
independent and initial Siege executable examples passed epochs 1/2/3 with exact
payload rollback. The refined suite has 12 tests. Final source and committed
head counts/digests will be posted with the complete command ledger.

## Rework ledger

Investigation output exceeded tool display limits; reread bounded source/history
sections before design. Candidate red: stage-selected absent before extension. Candidate parity red:
canonicalizing selected-build input reordered resolver JSON output; preserving
its raw representation restored complete equality. Candidate rollback review:
strict compatibility must validate old scaffold with old pinned tools; real
Siege scaffold red/green is retained separately. The first ontology refresh ran
before dist existed and failed; build then refresh passed. These are distinct
from accepted-parent defects and are not relabeled as passing runs.

## Evidence-predates-work

This artifact, pre-mortem and hostile plan are written before product edits.
The preimplementation issue comment records chronology before executable work.

## Reviewer assumptions and layer review

Working as: author reviewer, not independent approver.
Reading for: separate immutable input ownership, explicit adoption, one coherent
selected set and exact prior-set rollback at a new epoch through public APIs.
Failure shapes: mixed native/settings/resolver bytes; generated receipts replacing
approval pins; a failed switch or candidate cleanup damaging active/prior payloads.

Correctness and domain: distinct source roles plus external profile/policy and
registration pins are verified by the existing builder. Source identity may share
a commit without merging authority. No operation/provider receipt becomes input.
Security: strict argv parsing remains accepted behavior; paths reject links/escape,
subprocess calls use vectors and timeouts, the local operator remains outside the
trust claim. Data integrity/DDIA: immutable payloads are derived from Git/approved
inputs, one current.json is the commit point, readers retain shared locks through
actual dispatch, rollback increments epoch and rebuilds the exact retained set.
Performance: selection rebuilds both layouts; consumers verify complete inventories,
so compatibility fixtures are slower by design. No unbounded retry was added.
Error/resource handling: locks use context managers/ExitStack, subprocess calls are
bounded, interrupted final publication cannot verify, cleanup excludes generations.
Readability: existing release and selected modes share select/observe/resolve;
the added public command and stable consumer binding are documented together.

## Scanner disposition

The first unfiltered staged scan completed with 38 findings. Two added prose
adverbs were removed. The remaining classes are generated ontology typography,
existing timeout omissions in two touched test modules, and the scanner's missing
bin/_test discovery for three runtime modules. The accepted dependency workflow
records these diagnostics without changing the scanner or suppressing paths.
Their full final output, exit 1 and source selection are disclosed separately from
passing scanner regression suites. This is not a clean-scan claim. The user's
immutable-parent and no-weaken requirements take precedence over expanding this
dependency into unrelated scanner/test-layout/ontology-generator repairs.

## Later falsification results

The complete 11-test transition suite fails against an unmodified accepted-parent
source snapshot because its physically independent scaffold lacks selected-generation
support. This is expected dependency RED, not a parent defect. The strict Siege
scaffold replay then found a real candidate rollback failure (compatibility scaffold
differs: bin/build.py); corrected public rollback restores all 1,758 payload entries,
unchanged settings, original identities and native denial with authorization none.

A settings-order probe found that insertion-order command indexes could redirect
an event after a JSON key reorder. Sort event keys in both registration and native
lookup; preserve group/hook order. The direct probe is RED before and GREEN after.
A regression exercises the public renderer, and Siege now executes its actual
registered settings resolver at baseline, upgrade and rollback.

A forged receipt probe now recomputes the entire candidate manifest and inventory;
it still fails the normal rebuild from external pins. Stale forward observation
cannot authorize rollback even at the correct current epoch. Two test-harness
imports initially failed (nonexistent fixture.registration, then missing bin import
path); both are fixed, their failed logs remain, and no product failure is hidden.
The filename forged-receipt-green.log was premature: it contains a failed first
attempt. Its successful replacement is forged-receipt-second.log.

The working full matrix exposed one release-mode regression: the first lazy loader
resolved release-handoff under a temporarily changed tool root in the unchanged
wrong-tools test. Cache the verifier after first load, retaining lazy independent
source loading and the original matching-tools rejection. The failing 19-test run
is retained; the same targeted test passes after correction (16.666s).

Shelf lens: clean-code/refactoring-patterns score 8/10. Stage/verify and selected
registration remain long functions; smaller publication helpers are a possible
later readability improvement, not a reason to duplicate their state transitions.
Design-patterns lens: the existing adapter/selector boundary carries variation;
no new strategy framework or activation state machine is needed here.

## Completed working-source matrix

The corrected snapshot passes 130/130 commands: 37 Python suites, 36 hook suites,
11 scanner suites, build/check and freshness, package/provider/native contracts,
and both registration/generation examples. Snapshot tree:
4c1d7ceb89d867881d0efd7a1f8581eb8a2e2be5; 1,482 source files verified byte/mode
exact before execution. Matrix SHA-256: ea3bc7ed61c5117b89804231fa32b4afae9115251f1c58fcfa501c55763005b8.

The first superseded matrix retains its release-loader failure and interruption
record. The complete replacement includes the corrected 19-test release generation
suite, 12-test selected generation suite and strict scaffold/settings rollback.
A separate parity probe verifies ten accepted boundary files byte-for-byte and ten
function/class ASTs unchanged. Its first symbol lookup used the wrong file and
failed; the corrected checker and both logs remain in cache/coherent-generations.

Author assessment: the parent acceptance map has implementation/proof for each
listed item. The final committed-head matrix must pass before push; independent
review and merge remain required before issue closure. This artifact records
working-source evidence without claiming a future exact-head run has passed.

Verified-by: cache/coherent-generations/working-refined/matrix.json; final committed
head, source scanner output and full command/log digests will be posted on the draft
PR and issue before handoff. Source scan exit 1 remains disclosed, never called clean.
