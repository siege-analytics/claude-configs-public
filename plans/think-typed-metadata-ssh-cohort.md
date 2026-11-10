# Next source cohort preparation — #1260

Tracking: https://github.com/siege-analytics/claude-configs-public/issues/1260

## Context

Prepare the next source-only cohort after the separately queued #1255 publication. Root accepted these exact inputs: #1255 at 77630085a560b21129a19edb9fd93f5b51f25b45; #1170 at a3cc8d81502469da82ead69f143da01a1818742e; #1212 at 6617bd8b808c78840a64214138700ab06f22856b; #1216 at 6eb0db5dd57b681071b8b4ffa87e89e3294c4f39; #1257 at dcd03b062d8df1b744682a43505b2794841598f4; #1259 at ca47aa4e62b6573543729e8c782225fb83be0372.

#1255's typed metadata operation contract makes #1212's report-word B1 parser obsolete. Keep #1212's accepted B2 identity/classifier behavior and actual-state protections while avoiding a second vocabulary/owner-registry lane. The combined SSH and metadata-post operation must not drop foreign post authorization requirements under remote_contact_only or metadata_only.

## Goal

Produce a reviewed, source-only candidate whose ordinary two-parent ancestry contains the accepted inputs, whose operation classification preserves all metadata-post obligations across SSH companions, and whose planning/reporting path satisfies #1164 without wording workarounds. Keep client imports, live installs and protected branch publication separate.

## Design

Design: plans/think-typed-metadata-ssh-cohort.md

Start from fresh canonical develop in a new isolated worktree. Inspect exact accepted deltas before merging. Integrate #1255 as future baseline, then other accepted inputs through ordinary two-parent merges. Resolve the obsolete B1 portion against canonical typed metadata rather than copying its parser back; preserve exact B2 behavior. Record each conflict and its semantic resolution. Add an actual interaction fixture, run affected suites and the genuine unbound native test producer, then obtain Root review. Reconcile with fresh develop only after actual #1255 publication; do not merge/publish protected refs or import clients in this preparation task.

## Assumptions

- Current canonical develop is ce21650cdcacbbaaa25553c37f8a4bb3b74e73cd; it is the initial branch source, not a claim that #1255 has published.
- Existing user/Root authorization covers preparation and normal local validation, not bypassing review, owner holds or protected publication.
- #1164 concerns required artifact/report posts; typed operation semantics settle that path without recognizing status words as authority.
- Preserve historical fixture text and data while changing assertions to the actual operation contract where B1 behavior is obsolete.

## Acceptance criteria

- [ ] AC1: Every accepted input is an ancestor through ordinary two-parent merges, with no force, octopus or history rewrite.
  - Falsifiable-by: any accepted SHA fails git merge-base --is-ancestor or a merge has more than two parents.
  - Tool: Git ancestry and parent enumeration.
- [ ] AC2: A foreign metadata post combined with an allowed SSH action is denied; metadata_posts cannot disappear behind remote_contact_only or metadata_only.
  - Falsifiable-by: the combined unauthorized operation is accepted by the actual resolver/hook fixture.
  - Tool: real action-classifier and hook integration tests.
- [ ] AC3: Authorized SSH/report/artifact paths remain allowed; #1164 planning text needs no vocabulary workaround or fresh owner GO.
  - Falsifiable-by: legitimate positive fixtures are denied or marker/word changes alone determine permission.
  - Tool: affected hook suites, including old report texts under the typed operation contract.
- [ ] AC4: Accepted B2 identity/classifier controls remain intact without resurrecting obsolete B1 parser/registry machinery.
  - Falsifiable-by: foreign identity or actual-state negatives pass, or a second report-word authority parser is introduced.
  - Tool: exact accepted-source comparison, focused negative fixtures and independent review.
- [ ] AC5: Preparation does not modify main/develop, live settings, clients or held publication lanes; known full-SHA producer fix comes from #1255.
  - Falsifiable-by: any protected/live/client mutation or manual metric-hash workaround appears in the task's actions/diff.
  - Tool: Git ref/status audit and review.

## Composition decisions and receipts

- Initial plan commit: de397acf, before source merges. Future baseline #1255 was merged locally first; no protected ref or client was changed.
- #1170 conflict: retained both independent Git bootstrap and SSH helper families. The naive combined SSH flag calculation admitted a foreign local metadata post beside allowed SSH in both command orders at the UMG layer. This was not claimed as a whole configured-chain escape. The actual fixture returned 0 where 2 was required, then passed after preserving metadata-post obligations in classifier, resolver and UMG early-admission boundaries.
- Standalone own report and standalone allowed SSH pass the actual configured hook chain. Own combined post+SSH has resolver/UMG Task proof but remains rejected by the existing coordinator composition contract; no new composed reporting format is introduced.
- #1212 conflict: coordinator-status-guard.sh and its canonical scenario suite retain #1255 behavior. pipeline_state.py and the historical JSON corpus are byte-identical to accepted 6617bd8. B1 texts and old expected results remain evidence data, while assertions now test descriptive metadata operations without held wording/fresh-GO cases. Real state changes remain separately guarded.
- Changelog describes current typed behavior instead of reintroducing the superseded B1 linguistic requirements. Historical review plan/corpus remain intact.
- #1216, #1257 and #1259 source changes merged through ordinary two-parent commits. Derived catalogs are retained provisionally then regenerated with the actual combined producer; no metric SHA is hand-written.
- All six accepted input SHAs pass merge-base --is-ancestor against local 172399ca. All local first-parent composition merges have two parents. This is source preparation only; #1255 publication and fresh canonical-develop reconciliation remain future eligibility predicates owned by Root.
- Observed focused validation: SSH 179 scenarios; metadata reporting 10; interaction 4 (including actual configured standalone controls); coordinator 80 scenarios plus 10 metadata tests; artifact follow-up 14; complete historical B1/B2 suite 4 methods; bootstrap 35; reader safety 20; spawn 14 shell controls plus 15 structural tests; load-set resolver passed. No historical corpus rows were skipped.
- Actual combined build and inventory, review-risk, progressive-loading, generated-authority and kernel-budget producers completed successfully. Their freshness checks passed; derived files were not hand-edited. The source-only candidate still requires Root's independent integration review and later canonical-develop reconciliation; these test results do not claim publication readiness or a broader composed-post contract.
