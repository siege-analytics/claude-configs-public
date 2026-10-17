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

Review comment [6226106213](https://github.com/siege-analytics/claude-configs-public/pull/1029#issuecomment-6226106213)
requires a bounded correction to publisher qualification at
`b65b9d9323a572d4b682cc483c079dd75c126f09`. The correction below addresses
that finding; independent acceptance of the replacement head remains pending.

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

## Publisher qualification correction

The generated inventory and manifest now carry `publisher_local_slug` from
source discovery. The existing graph requires the published slug to equal
`publisher + "--" + publisher_local_slug` when qualified and
`publisher_local_slug` otherwise. It validates the local identifier, the
publisher-root boundary, the `SKILL.md` filename and the source directory's
discovered local name, including the existing `shelves--` convention. Physical
source directories containing `--` remain excluded by discovery and rejected
by the installed graph.

The installed graph validates the whole inventory before selection and resident
rendering. No policy pin, publisher/project ownership rule, composer, resolver
or authorization contract changes. Older composed inventories lacking the local
slug must be regenerated together with this graph; the local slug is provenance,
not a signature or authority to adopt policy. Consistently replacing an entire
unsigned content declaration is outside this metadata-integrity correction.

## Exemption: ticket template fitness

Reason: #1027 is the approved parent extraction issue; this revision is limited
to the concrete qualification failure in review comment 6226106213 and the
operator's matching remediation instructions.
Evidence: `bash scripts/discipline/evaluate-ticket.sh 1027` reports missing
Context/Goal, evidence-token, design-note and Assumptions sections. The actual
issue body defines Outcome, Boundaries, Execution plan and Acceptance, including
qualified names, one composition path and independent policy authority. The
linked review supplies the failing mutation and exact required invariant.
Falsification: A change outside publisher qualification integrity, or tests
that cannot reproduce the reviewed resident-output failure, invalidates this
exemption. No parent-ticket rewrite is needed for this bounded revision.

## Reviewer Assumptions

Working as: author-side remediation and self-review; independent approval is
reserved for the existing reviewer.
Reading for: #1027 requires explicit publisher selection and qualified names
without implicit policy adoption, using the existing composition machinery.
Failure shapes: either qualification-flag direction is accepted after mutation;
a self-consistent renamed slug disagrees with its source; valid Siege or shelf
content changes when repackaged.

The function/chain review follows discovery -> generated inventory -> installed
ProcedureGraph -> selection -> resident renderer. The derived-data lens in
`skills/shelves/systems-architecture/data-intensive/SKILL.md` keeps the source
declaration as the system of record and treats inventory as a rebuildable
projection. Checking only the published prefix leaves that projection ambiguous;
the local-name/source check makes its derivation exact. Existing graph tests
cover ordering, cycles and scope; this patch introduces no I/O or mutable state
inside the graph and retains its ValueError failure contract.

## Correction validation receipts

- Red reproduction: `/private/tmp/cc-1029-qualification-red.log` records the new
  installed mutations accepting resident output on the reviewed implementation.
- Focused pass: 15 selected-composition tests, including 13 mutation variants in
  each emitted layout. Both flag directions, prefix/suffix mismatch, invalid or
  null local metadata, source mismatch and shelf derivation reject before
  resident output even for an unrelated project request. Valid qualified and
  unqualified ordinary/shelf publications resolve in both layouts. Log:
  `/private/tmp/cc-1029-qualification-final-focused.log`.
- Existing graph/resident 21/21, project composition 22/22 and resident delivery
  11/11 passed in `/private/tmp/cc-1029-{procedure,project,resident}.log`.
- Normal build and build-check passed in `/private/tmp/cc-1029-build.log` and
  `/private/tmp/cc-1029-build-check.log`. The source inventory was regenerated;
  its changes record the new selected-composition and shelf-review references.
- Compared with the reviewed head, both Siege identities keep the same 52 output
  files, with 40 byte-identical and 12 changes limited to the graph or the added
  local-slug metadata. Skill, rule, resident and composition-receipt bytes remain
  identical. Explicit Siege and compatibility invocations still match exactly.
  Receipt: `/private/tmp/cc-1029-qualification-40xoffsu/parity.json`.
- Full committed-head validation follows the normal commit. The matrix receipt
  and log will be `/private/tmp/cc-1029-qualification-40xoffsu/matrix.json` and
  `matrix.log`; the PR handoff records their terminal result and exact head/tree.
  This artifact does not pre-claim that result or independent review acceptance.

The mechanical scanner prompted bounded subprocess timeouts in the touched
integration fixture. Its remaining `writing-tests-5` report says the composer
has no corresponding test file; this is a filename-discovery limitation. The
existing `bin/_test/project_composition_test.py` and the selected-composition
suite execute the actual CLI and its error handler, including the reviewed
invalid-inventory and invalid-source cases. That exception handler is unchanged.
Generated-authority and review-risk checks initially caught stale inventory after
the review artifact added a shelf reference; regeneration precedes the final
freshness checks and committed-head matrix.

Verified-by: focused logs and parity receipt above; terminal exact-head evidence belongs to the PR handoff.
