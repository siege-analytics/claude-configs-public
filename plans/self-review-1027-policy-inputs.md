# Explicit policy-input boundary — #1027

Pre-mortem-artifact: plans/self-review-1027-policy-inputs.md
Hostile-review-artifact: plans/self-review-1027-policy-inputs.md

## Assumptions

The accepted extraction plan and its constraints are recorded in #1027 comments
6225067704 and 6225119253. This first reviewable dependency separates policy
input verification from the Siege compatibility selection. It does not complete
the build/registration or coherent-generation independence acceptance matrix.

The same bounded evaluator and contract validator serve both paths. A host must
obtain registration path and digest from its previously trusted configuration.
A candidate, bundle descriptor, self-written lock or composition receipt cannot
establish that trust. Configured evidence and caller-provided capability states
remain non-authorizing. No generic executable discovery or policy language is
added. The repository's current selected policy and contract bytes are unchanged.

## Failure analysis

- Moving a digest into mutable data could let that data authorize itself. The
  compatibility registration retains a compiled independent digest; the generic
  verifier requires the caller's independent pin before using any declared path.
- A candidate could edit policy and selection together. An isolated Git fixture
  actually commits a replacement and reseals its registration; the previous
  host pin rejects it. Unselected working policy edits continue to be ignored.
- A hidden Siege read could make the extraction cosmetic. The positive test
  launches copies of the two real engine modules and schema in a fixture with
  no bundle directory, legacy skill/hook tree, examples or Siege catalogs.
- Mere schema validity could conceal blob/raw/canonical mismatch. The existing
  hostile snapshot tests now exercise the explicit verifier with an independently
  supplied test registration instead of patching a module-global seal.
- A declaration could masquerade as implemented enforcement. The independent
  fixture deliberately declares adapters without implementing them; even caller
  assertions that all are verified cannot produce an authorizing result.
- The source closure test could be overclaimed. It exercises policy loading and
  explanation only. Actual packaging and registration are still required later.

## Peer review

Independent implementation review is pending. The coordinator accepted the
bounded extraction plan, not these implementation bytes. Exact-head review and
terminal hosted checks remain prerequisites for integration.

## Lead review

The existing Siege wrapper delegates to the public registered-input loader.
The loader verifies registration, selected receipt, Git ancestry/blob, policy
digests, contract agreement and explicitly selected fixtures. Optional empty
fixture selection is data in the independently pinned registration; it cannot
disable this repository's selected two-fixture agreement check. The policy
selection source in explanation can now describe the actual selected path.

Capability target validation is declarative and never executes a declared path.
The existing three operation kinds remain required; each project supplies its
own reviewed defaults and capability requirements within that vocabulary.
Symlink and path escape checks apply before descriptor/contract reads.

## Quantified claims

Focused working-tree validation passed 42/42 policy tests in 4.336 seconds,
including eight new independent-input scenarios. Log:
`/tmp/cc-1027-policy-inputs-tests.log`. An earlier run failed one existing clone
fixture because the imported working module expected a new registration absent
from the older cloned HEAD; the test now copies the unchanged compatibility
registration associated with that imported module. This was a fixture issue,
not a relaxed loader check. Gate tests passed 21/21 in 2.019 seconds; ontology
tests passed 25/25 in 0.639 seconds, and review-risk tests passed. Both normal
build and build-check passed. Generated inventory, ontology, review-risk,
progressive-loading and source-authority checks are current. The independent
review and full committed-checkout validation remain pending at this checkpoint.

## Canary and rollback

Only disposable local Git/source fixtures are used. There is no runtime install,
live host observation, provider change or shared workspace mutation. Rollback
reverts this extraction and restores the compiled legacy selection inputs as
one source change. Existing installed packages are unaffected by source work.
