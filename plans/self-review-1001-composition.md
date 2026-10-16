# #1001 composition self-review and failure analysis

Pre-mortem-artifact: this document, Failure analysis section (recorded after the initial graph prototype, before publication)
Hostile-review-artifact: this document, Peer review section; independent exact-commit review pending

## Assumptions

This bounded content compiler consumes the independently accepted #848 policy selection at `9741863473b883bdf9111f680a9cf5cf9dfceb84`. The synthetic identities and review-procedure identifiers come from that resolver. Composition is content selection, not policy precedence, capability proof or permission. Real consumer source stays private.

## Implementation plan

1. Build one graph for explicit replacement, ordered extension, alias and prerequisite resolution; preserve qualified IDs and source/package provenance.
2. Feed that graph into the existing resolver and token renderer; produce isolated derived consumer outputs for both layouts without changing parent sources.
3. Import heading overlays with explicit stable IDs, preserve locked resident blocks and budget the final expanded text.
4. Exercise both approved synthetic identities through actual packaged CLI and links; falsify scope, duplicate, cycle, conflict and authority claims.
5. Run existing regression/freshness suites, publish a draft against develop, and remediate independent exact-commit findings before acceptance.

## Failure analysis

- Replacement affects one route only: all four entry routes and rendered links use the same graph; raw stale links reject rather than silently loading an old default.
- Alias or prerequisite resurrects a default: graph traversal resolves every edge, and replaced source content is omitted from the consumer output.
- Deduplication scrambles extension order: merge ordering constraints before one topological sort. A shared prerequisite is deduplicated before sequence edges, avoiding a false cycle.
- Project content leaks through a global bundle: derive only the selected scope's rules and reject another target identity; parent sources remain byte-identical.
- Resident replacement waives evidence: parent integrity/workflow blocks disallow overrides, while permission and required-evidence values remain in the separate unchanged policy result.
- A prose heartbeat or successful build claims authority: outputs explicitly say configured and authorization effect none; no host rollout is claimed.
- A source symlink imports unrelated content: reject symlinks in source trees and their ancestor components, validate packaged local links, and refuse writing inside the source tree or over an existing standalone destination.
- A short source exceeds the budget after expansion: measure the final rendered resident and packaged selected skill text.

## Peer review

Pre-publication adversarial self-review added a shared-prerequisite regression, raw stale-link rejection, foreign-rule validation, symlink rejection and output isolation. This is not independent acceptance. The existing Craft coordinator will review the exact published head; findings and replacement verdicts belong directly on the PR.

## Lead review

The global resolver takes the new composition path only when an explicit derived manifest declares it. Existing manifest selection remains covered by its prior regressions. The production kernel and normal project selection are not migrated by this pilot. The compiler uses synthetic skill bodies under examples, alongside the approved policy's real identifiers. These bodies are test procedures, not a claim that all existing consumer Markdown has been migrated.

## Quantified claims

21 graph/resident scenarios and 14 package integration scenarios pass locally before publication. The first full local run passed behavioral suites but exposed stale inventory after a late router-copy regression was added; dependent freshness checks correctly failed. The inventory is regenerated after the final source/test set is staged. Full replacement matrix, hosted validation and independent acceptance must be recorded in the PR from their actual terminal results; this document does not pre-claim them.

## Test plan

Run both composition suites, existing resolver/consumer/build suites, gate-contract and effective-policy tests, all hooks/workflows and generated freshness checks. Package probes execute from outside the source tree. Verify selected content once/in order, scope isolation, unchanged parent digest, correct nested/flat links and locked policy values.

## Canary and rollback

Disposable output directories provide a build/read canary. No existing workspace or host installation is modified. Existing parent packages remain available; remove the separate fixture output to discard the pilot. Activation/rollback of a real consumer remains #1004, with live host proof under #1003.

## Publication validation

The replacement full run on the combined #848/#1005 base passed **80/80 commands**:
24 Python modules, 36 hook suites, two workflow suites and build/reference/freshness
checks. Both composition suites passed all 35 scenarios. Five additional ontology
bindings validated. Log on the shared review laptop: `/tmp/cc-1001-final-validation.log`.
Generated authority remains current at 198 sources, 804 snapshots and 2,912 mappings;
these counts cover the normal production layouts. The separate synthetic outputs
are tested directly and carry their own composition/source-policy receipts.
Independent exact-commit review and hosted CI remain pending at publication.

## Independent R1 remediation

The Craft reviewer rejected `ec18168357eb72bd49d3558d0f348089609f29bf` because
reference-style Markdown and HTML links could retain a missing replaced-default
path. The original inline-only regex was insufficient. Destination validation now
reads inline/angle/reference destinations and uses the standard-library HTML
parser for href/src attributes; it normalizes decoded package-relative paths.
External schemes and same-document anchors remain allowed. Both layouts are
validated before output. Three regression scenarios cover the reproductions,
both-layout scope/encoding negatives and valid packaged/external/anchor controls.
The focused total is now 38 scenarios. The original head's hosted full validation
passed; its independent rejection remains valid until the replacement is reviewed.
