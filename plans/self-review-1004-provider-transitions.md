# Shared-parent events across generations — #1004

Pre-mortem-artifact: plans/self-review-1004-provider-transitions.md
Hostile-review-artifact: plans/self-review-1004-provider-transitions.md

## Assumptions

The accepted generation tests and provider tests cover separate boundaries.
This slice joins them using actual immutable release objects, the selected
generation's composition and the existing shared-parent event evaluator.
The plan was independently accepted in #1004 comment 6219719757.

Host facts are synthetic and independently supplied. Selecting a generation
does not register, update or authorize a provider workflow. The test builds a
separate canonical consumer workflow checkout at every phase and explicitly
pins the parent revision as the reviewed workflow example does. No live host,
private consumer, shared installation or new policy engine participates.

## Failure analysis

- Testing the direct evaluator again would miss event normalization. Invoke
  `--host-event` with a separate canonical workflow checkout and exact facts.
- Reading a fresh composition instead of the selected one would miss mixed
  generations. Copy `content/` only from `resolve(store)` and compare the
  provider receipt with the generation and actual committed receipt bytes.
- Collapsing parent and consumer identities would hide shared-parent errors.
  Assert distinct parent source and consumer base, exact candidate head and
  executed workflow ref/revision/blob/digest for both profiles.
- Reusing a favorable head or old epoch would hide rollback mistakes. Require
  a new epoch when selecting the previous generation, a new eligibility
  result for the repaired head, and rejection of stale host head facts.
- Merely changing a copied receipt could make a weak negative. Evaluate the
  intact selected composition against the other real parent version and
  require a composition mismatch; neither generation is edited to fake drift.
- A fixture branch naming assumption can fail on detached CI checkouts. The
  disposable consumer creates its own main and feature branches; the workflow
  clone supplies its own fetched default-branch ref.

## Peer review

Independent exact-head implementation review is pending. This document records
the author's adversarial checks, not an independent verdict. The tests require
the expected denial reason as well as the exit/state so a generic fixture error
cannot stand in for wrong-target, missing-ticket or mixed-generation denial.
An initial run found an incorrect test lookup (`path` instead of the existing
composition receipt's `load_path`); it was corrected without changing the
production schema or renderer. That failed log is retained separately.

## Lead review

Only the existing generation test module and evidence documentation change.
The shared consumer fixture now accepts a project name; all existing scenarios
retain strict-release as their default. Each profile receives an isolated
consumer/store. Both reuse the same two parent releases. Parent origin changes
are confined to the disposable fixture and restored by test cleanup.

All eligible results still require the protected host check and carry no
authority outside a trusted host receipt. Negative results grant none. The
test checks that neither provider evaluation nor denials alter generation
selection, canonical workflow HEAD or the fixture's protected main ref.
The existing live-canary source pin remains valid because no runtime code is
modified by this slice.

## Quantified claims

The focused added scenario passed in 73.485 seconds. It contains two project
profiles and three generation phases, with allow, wrong target, missing ticket,
repaired head, stale head and mixed-generation probes at each phase: 36
provider invocations. Initial/upgrade/rollback epochs are 1/2/3. Log:
`/tmp/cc-1004-provider-transition-focused-v2.log`. The failed first fixture run
is `/tmp/cc-1004-provider-transition-focused.log`. Full repository validation
and final hosted results will be recorded on the implementation PR before
integration. This count does not describe live provider or Craft observations.

## Canary and rollback

All releases, repositories and generation stores are synthetic disposable
fixtures. A source rollback reverts this test/evidence slice; it changes no
runtime behavior or installed state. #1003 live delivery and #1004 live
activation remain separate acceptance work. #849 retirement is not authorized
by this integration test.
