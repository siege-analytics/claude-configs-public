# Explicit content composition — #1027

Pre-mortem-artifact: plans/self-review-1027-composition-inputs.md
Hostile-review-artifact: plans/self-review-1027-composition-inputs.md

## Assumptions

This dependency follows #1028 and accepted plan 6225119253. It extracts content
composition, not normal source builds, settings/native registration, kernel
delivery or component generations. Those remain necessary for #1027 acceptance.
The existing coordinator reviews this work; no additional worker is involved.

## Failure analysis

- Content selection must not replace the trusted policy pin. The same explicit
  registered-input verifier checks that pin before composition. The content
  descriptor has no policy adoption or authorization fields.
- Hidden Siege defaults could make absence testing cosmetic. The integration
  test launches copied real modules from an independent Git source closure
  containing no Siege catalogs, legacy skills/hooks/examples or bundle folder.
  Both emitted layouts run their real resolver and resident renderer.
- Publisher identity must not borrow project scope. Publisher roots cannot be
  under projects; graph entries retain publisher ownership independently of the
  selected project. Explicit qualification, duplicate detection, graph cycles,
  scope checks and symlink checks precede output.
- Content replacement must not weaken actual policy. Policy remains in the
  non-authorizing receipt with its independent source/pin. The selected review
  procedure must still resolve even when no review alias/route was requested.
- Legacy compatibility could conceal a second algorithm. Defaults now load a
  Siege descriptor then execute the same discovery, graph and rendering code.
  The explicit legacy qualification flag retains old names; it is not a hidden
  namespace fallback or implicit adoption rule.
- New vocabulary could imply authority. Ontology 1.1 adds content-publisher and
  content-selection, updates bindings, and tests both against the existing
  prohibition on new authority relationships. The approved gate contract remains
  pinned to its original 1.0 vocabulary; its existing meanings are unchanged.
- An empty selected resident could pass the composer yet fail the runtime
  reader. An independent post-commit probe reproduced that gap. Empty or
  whitespace-only residents now reject before output; both cases have regression
  coverage. The initial full matrix was stopped rather than reported accepted.

## Peer review

Independent source review is pending. #1028 remains frozen at its separate
review head; this dependent checkout is not a second implementation of that
input verifier and does not supersede its evidence.

## Lead review

One composer accepts independently pinned policy inputs and explicit content
data. The Siege descriptor supplies the formerly automatic alias, prerequisite,
route and three resident blocks. Publisher file digests and selection digest are
recorded separately from the project/policy receipt. The legacy
parent_content_sha256 remains a compatibility aggregate of declared publishers.
There is no new policy engine, resolver, executable discovery or installation
path. Qualified publisher content must use explicit qualified references; no
unqualified name is silently rebound to a convenient publisher.

## Quantified claims

Working-tree validation: existing project composition tests 22/22 and graph/
resident tests 21/21 passed. Twelve selected-composition tests passed, including the empty-resident regression,
including real copied-module invocation and a synthetic Siege content publisher
under an independent no-ticket/trunk policy. This is not a real Siege library or
host-installation acceptance claim. Explicit Siege and compatibility invocations produce byte-identical packages
for both existing identities. Baseline comparison retains all 52 output files;
36 are byte-identical and 16 changes contain only publisher-aware graph code or
input/publisher provenance. Rendered skill/rule/resident bytes and previous
semantic receipt fields are unchanged. Evidence:
`/tmp/cc-1027-composition-parity.json`. Normal build, 25 ontology tests and
review-risk tests passed; generated authority, kernel and progressive metrics
are current. Full validation and independent review remain pending.

## Canary and rollback

Only disposable synthetic source and output directories are used. No installed
runtime or shared settings are changed. Reverting this source dependency restores
the previous compiled composition choices; accepted installed generations remain
the rollback target. Build/registration/transition evidence is not inferred from
these content tests.
