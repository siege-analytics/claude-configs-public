---
description: Always-on. Claim-grounding discipline. Grep before declaring a fix complete; ground countable claims in same-turn evidence; ground unquantified completeness claims (loop closed, ready to ship) in the same evidence shape; ground invented framework signals (new pattern names, coined disciplines) in existing artifacts; verify external-resource recommendations (URLs, file paths, tickets, free-vs-paid) at recommendation time; require three samples before promoting a pattern to a rule; verify finding-text against live source before scoping work; specific counts must cite the command that produced them; gate present/past-tense causal claims about production state behind a same-turn falsification probe or explicit `Hypothesis:`/`Untested:` label; before claiming a change to runtime-loaded code took effect, verify the consuming path matches the edited path. Applies whenever the agent states a fact in a commit body, PR body, agent-to-agent message, or chat to the operator. Fact-grounding at code-edit time (verify symbol exists, doc-edit symmetry, dependency reachable) lives in `_writing-code-rules.md`. Future-tense action commitments live in writing-prose:5.
---

# Writing Claims

These rules apply whenever the agent states a fact in a commit body, PR body, agent-to-agent message, or chat to the operator. The unifying boundary is "verify before claiming": the rules fire at claim time, after the action that the claim is about has happened.

The sibling boundary in `_writing-code-rules.md` is "verify before touching code": rules that fire at code-edit time (verify the symbol exists before naming it, verify the dependency is reachable before depending on it, re-read docs that reference the symbol you just edited). The two files split the same underlying claim-grounding family by temporal trigger; consult writing-code when editing code, consult writing-claims when stating facts.

The parent discipline is `[rule:verify-before-execute]` Evidence clause: same-turn tool calls back factual claims. These rules are specific shapes of that discipline applied at claim time.

## The ten claim-grounding rules

**writing-claims:1. Grep before declaring a fix complete.** When fixing one call site of a problem, search the whole codebase for the same pattern before writing the commit body, the PR title, or the chat update that says the fix is done. The Paragraph-escape fix that needed three rounds (one site, then CodeRabbit pointing out five more, then a follow-up) is the canonical failure mode: the gate moved from "before writing the patch" to "before claiming the patch is complete" because the original phrasing let the agent fix one site, declare done, and only grep when the reviewer pushed back. Same applies to renames, signature changes, and security fixes: scope of the bug is always wider than the diff that surfaced it.

**Scope of "complete" includes downstream class-completeness.** The narrow read of this rule is per-PR: grep before saying "this PR fixes X." The wider read -- required when the fix's value depends on no peers existing with the same shape -- is: grep before triggering a downstream re-run that depends on the fix being class-complete. The Spark Connect guard sequence that motivated this clarification had five PRs, each individually grep-passing for its own MV, none grep-passing for sibling MVs with the same `@dp.materialized_view + filter chain + partition_cols` shape. The first PR's "fixes gold" claim implicitly assumed class-completeness; the next four PRs proved the assumption wrong. If you are about to re-run a downstream job (gold tier rebuild, schema migration, pipeline rerun) that depends on the fix covering the whole class, the grep for siblings is required BEFORE the re-run, not after.

**writing-claims:2. Countable claims are auditable.** Any countable claim ("all four engines," "every call site," "no remaining occurrences," "fully covers the matrix," "completes the operation surface") must be preceded by the falsifying grep in the same response or the same tool sequence. If the grep is in a prior turn, it is stale and does not satisfy the rule. The grep output, not the claim, is the artifact. State the count, then make the claim. The session's worst case: a PR body claiming "all four engines call `_validate_agg_names`" when only two did.

In commit messages and PR bodies, a countable claim must be paired with a `Verified-by: <command output excerpt>` trailer. `[skill:detect-ai-fingerprints]` scans for the trigger phrases and requires the trailer.

**writing-claims:3. Confidence calibration: unquantified completeness claims need the same grounding.** Statements that imply finality without a count -- "I have completed," "addressed all," "ready to ship," "no remaining," "loop closed," "fully covers" -- are claims subject to writing-claims:2 even when no integer is named. Before stating them, run the falsifying check (re-run the test suite that would catch a regression, re-grep for the pattern, re-read the PR comments). State the check in the same response or the same artifact, then make the claim. The check is the artifact; the claim is the conclusion.

`[skill:detect-ai-fingerprints]` extends writing-claims:2's trigger set to cover these unquantified phrases. Same `Verified-by:` trailer requirement.

**Multi-PR session-pattern extension.** Confidence on "this fixes the tier" / "this completes the family" claims must be calibrated against session history, not just against the current PR. If N prior PRs in this session shipped same-shape fixes and each was claimed-complete-then-superseded by the next, the (N+1)th claim of completeness requires class-audit evidence inline -- a grep over the family, the audit-matrix as a code block, or a paste of the sibling-set with checkmarks. The session that motivated this extension shipped five same-shape Spark Connect guard PRs, each one claiming "fixes gold," each one superseded by the next within the hour. The (N+1)th claim was unwarranted by N=2 and dishonest by N=4. Per writing-rules:7, the session-scale check is the agent's responsibility until the wrap-up classifier (proposed under #186) automates it.

**writing-claims:4. Invented framework signals require existing artifact backing.** Coining a pattern name, discipline name, or meta-protocol in the same response that names a failure is itself a claim, and the implicit claim is "this pattern applies." Like writing-claims:1-3, this claim must be grounded: before naming the pattern, point to where it existed prior to this message -- in a shipped rule file, a prior PR, a LESSON entry, a documented skill, or an operator-stated discipline. The naming alone changes nothing; treating the act of naming a failure-mode shape as evidence the failure is addressed is the same mechanism as scoreboard framing -- where keeping score of failures (categorizing them, coining names for them, building a taxonomy of them) is mistaken for fixing them. Operator named this failure mode on 2026-05-14: "authoring rules without absorbing them", "inventing meta-patterns to dress up failures", and the broader "D&D supplementary manual" critique (elaborate rules with nothing compelling adherence).

Bad-example catalog from the originating session (260502-vital-channel + 260502-pure-vista, 2026-05-14): `author-self-application` (coined to frame applying a rule the agent authored as evidence of absorption), `claims-grounded-source-side-only` (coined to limit a critique's scope), `meta-meta-discipline` (coined as a higher-order discipline that did not pre-exist), `rule-protocol-applied-to-rule-release` (invented in the same message where the sibling agent was being told to stop doing exactly this). All four were retracted within the same day.

Carve-out: authoring a NEW rule artifact -- a numbered rule in a `_*-rules.md` file, a new `SKILL.md`, a `LESSON` entry -- is the one legitimate case for naming a new pattern, because the rule artifact itself is the backing. The carve-out is in the rule, not an override.

**writing-claims:5. Verify before recommending an external resource.** When recommending that an external resource (URL, file path, ticket reference, library API, book / free-vs-paid status, command-line flag) has property X (free, accessible, canonical, hosts content Y, supports flag Z), the property must be verified at recommendation time -- not asserted from memory or extrapolated from related-sounding sources. Same shape as writing-claims:1 ("grep before declaring a fix complete") applied to the recommendation surface. For URLs, the verification is a WebFetch / curl that confirms the property; for file paths, an `ls` / `stat`; for ticket references, a `gh issue view`; for library APIs, the actual function signature via Read/grep.

Bad-example catalog from session 260502-vital-channel (2026-05-17):
- "lethain.com hosts the free web version of An Elegant Puzzle" -- WebFetch showed it's a promotional landing page with purchase links; book is paid.
- "py.geocompx.org hosts the free Geocomputation with Python edition" -- WebFetch showed it's a landing page in development; full chapters not yet online; the R version at r.geocompx.org is the canonical free reference. Also mis-stated author list (claimed Muenchow as Python-edition author; actual: Dorman, Graser, Nowosad, Lovelace).
- Both surfaced past my own pre-recommendation checks; both caught only because operator pushed me to "see what's adjacent free," prompting WebFetch verification.

The discipline: when about to write "X is freely available at URL" or "X supports flag Y" or "X is canonical for Z," verify with the tool that would falsify the claim BEFORE writing the sentence. Mechanically expressible as `[skill:detect-ai-fingerprints]` extension: phrases like "freely available at," "free online edition," "canonical reference for," "available as a free PDF" should trigger a `Verified-by:` requirement on the recommendation. Tracked as a v2.x.y follow-up.

**writing-claims:6. Three samples before promoting a pattern to a rule.** When observing that a failure mode (or a beneficial discipline) recurs, do not promote it to a rule on the first or second instance. N=1 is an observation; N=2 is a candidate; N=3+ (or operator-statement-of-importance) is the promotion threshold. Premature promotion (single-instance pattern made into a rule) produces rule sprawl where each rule has thin grounding and the system as a whole loses signal-to-noise. Late promotion (sitting on a real recurring pattern past N=3+ because nobody noticed) produces undocumented disciplines that future agents have to rediscover.

Operationalization: when an agent observes a same-shape failure, BANK it as an observation with a one-line memo. When a same-shape observation accrues, link the prior memo and increment the sample count. At N=3 (or earlier if operator states the importance directly), draft the rule against the accumulated samples and submit per the standard rule-authoring flow. At N=2, hold and document but do NOT propose the rule.

Bad-example catalog (sessions 260502-vital-channel + 260502-pure-vista, 2026-05-17):
- Sibling-session observed two same-shape catches in my drafts (writing-claims:4-shape misses on the self-review SKILL.md) and explicitly declined to promote to a rule per the N=3 discipline. The third instance (writing-claims:5 above, the recommendation-verification miss) IS the third instance, but it's a different specific shape -- "recommending without verifying current state" -- so it earned its own rule rather than confirming a 4-prime extension.
- Sibling banked the chained-`git commit && git push` FP characterization as N=1 data, not promoted to a rule shape, because the failure mode is mechanical (a hook-timing artifact) not a discipline gap.

Carve-out: operator-stated-importance can collapse N=3 to N=1. When operator explicitly names something as "this should be a rule," the operator's statement IS the sample-of-importance; ship the rule. Operator's "I think this is right" + "all three" on the shelf-recommendations doc was operator-promotion of the priority list without N=3 of identical work; operator authority wins.

**writing-claims:7. Verify finding-text against live source before scoping work from it.**

When acting on a claim from a prior ticket, postmortem, design note, review, or any artifact authored at-an-earlier-state of the code, verify the artifact's factual claims against the current live source before scoping the work. The artifact records what was true at authoring time; the work happens against what is true now. Treating prior-artifact text as ground truth produces wrong-scoped fixes.

Same shape as writing-claims:1 (grep before declaring a fix complete) and writing-claims:5 (verify before recommending an external resource), applied to internal artifacts. Survey-context-skill's consult step handles this implicitly when the artifact is an entity doc page; this rule covers the broader surface of acting on findings, tickets, and reviews.

Operationalization: before writing the first line of a fix, re-read the relevant source files and confirm:
(a) the count or enumeration in the finding-text matches what exists ("duplicated across 4 endpoints" -> grep the actual count; if it is 3, the helper extraction has different scope).
(b) the type/shape claims in the finding-text match what is declared ("object_id is integer PK" -> read the model definition; if it is CharField, the proposed fix is the wrong shape).
(c) the file paths, line numbers, and symbol names still exist post any landed fixes between the artifact's authoring date and now.

Bad-example catalog from sessions 260502-vital-channel + sibling (2026-05-18):
- A2/SW#113 retraction: review asserted `DemographicSnapshot.object_id` was IntegerField PK without checking the source. Source showed CharField geoid-string. The retraction cost a closed ticket + author embarrassment; the rule firing on its own author in PR #113's review was the moment that shaped survey-context skill design.
- A6/SW#117: finding-text said "duplicated across 4 endpoints"; live source had 3 error-responding sites + 2 loop sites with different semantics. The intended helper would have over-generalized had the author scoped from finding-text alone.

The artifact is authored-at-a-prior-state. The work is against current-state. The reconciliation is the rule.

**writing-claims:8. Specific counts must cite the command that produced them.**

Any claim containing a specific integer count ("21 subpackages," "15 import sites," "4 stale shims," "all 29 public symbols") must be immediately preceded or followed by the command output that produced the number. A count without a command is an estimate presented as a fact. The agent's memory of "about 20" is not evidence that the number is 21; the difference between 21 and 25 is four missed items.

This rule is the quantitative strengthening of writing-claims:2. writing-claims:2 requires the falsifying grep for countable claims; writing-claims:8 requires the producing command for the count itself. The two compose: the count comes from a command (writing-claims:8), and the claim that the count covers the full class comes from a falsifying grep (writing-claims:2).

Operationalization: before writing a sentence containing a specific number, run the command that would produce that number. Paste the command and its output. Then write the sentence. The command is the artifact; the number is the conclusion.

Banned shapes:

- "All 21 subpackages define `__all__`" without `ls -d pkg/*/ | wc -l` or equivalent showing 21.
- "Updated all 15 internal import sites" without `grep -r "old_path" --include="*.py" | wc -l` showing 15.
- "Only 16 imports use the top-level path" without the grep that counted 16.

Acceptable shapes:

- `` `ls -d siege_utilities/*/ | wc -l` → 25 `` followed by "All 25 subpackages define `__all__`."
- `` `grep -rn "from old_path" --include="*.py" | wc -l` → 15 `` followed by "Updated all 15 internal import sites."

The command output anchors the claim to reality. When the agent's recalled count disagrees with the command's count, the command wins and the claim must be revised before stating it.

Bad-example catalog from session 260526-true-coral (siege_utilities Epic #572):
- PR #586 claimed "Verified all 21 subpackages already define `__all__`." Actual count: 25 subpackages, 4 of which (`conf`, `economic`, `education`, `reference`) lack `__all__`. The number 21 was fabricated from memory; no `ls` or `find` command was run. The false count shaped the PR's conclusion that no action was needed -- the conclusion was wrong because the count was wrong.
- PR #584 claimed "only 16 internal imports use `from siege_utilities import X` vs 1408 using subpackage paths." Actual grep on non-test files: 2 top-level imports, not 16. The ratio was even more extreme than claimed, but the specific number was still wrong.

Mechanical enforcement candidate: `[skill:detect-ai-fingerprints]` trigger-set extension for integer-count phrases ("all N," "N files," "N subpackages," "N import sites") requiring a `Verified-by:` or inline command-output block. Tracked for v2.x.y.

**writing-claims:9. Present/past-tense causal claims about production state require a same-turn falsification probe.** A statement that asserts *why* something happened or *with what effect* -- "Phase 3 took effect," "the DAG produces Z," "bulk-collapse drives the F3 gap," "the MV now reflects the new rule" -- is a causal claim about production state and must be paired in the same response with the probe that would falsify it. State the probe (the grep, the query, the row-level inspection) and the result together. If the probe didn't run, label the claim explicitly: `Hypothesis:` or `Untested:`.

**Scope (causal vs descriptive).** The rule fires when the claim asserts *why* something happened or *with what effect*, not when it asserts *what was observed at a specific surface*. A timestamp lookup is descriptive; a claim that the timestamp implies a particular cause is causal. The cheap test: if a colleague could ask "how do you know?" and the honest answer is "I inferred it from X," the claim is causal and needs a falsification probe. Descriptive observations are out of scope and don't need probes.

**Reference form (acceptable substitute for inline probe).** When the verifying probe ran in a *prior* turn or lives in a *linked* artifact, the claim may cite the artifact instead of restating the probe -- but the citation must be precise enough that a reader can locate the probe without searching. Acceptable forms: a PR/issue comment URL, a `#<NNN>` ticket reference, a `memory:<file>` path, or a `session:<id>` reference (optionally with turn/timestamp suffix, e.g. `session:260527-smooth-panther@2026-05-30T11:02CDT`). Vague references ("per my earlier investigation," "as established last week") do not satisfy the rule -- they shift the audit burden to the reader without naming the artifact.

Acceptable shapes:

- *Inline:* "Phase 3 took effect -- grep result: 0 violating rows in <output-table> (was 3,469)."
- *Inline:* "Hypothesis: <upstream-pattern> drives the gap. Probe: top-5 row inspection -- `SELECT <key>, <metric> FROM ...` → top-5 are <observed-shape>, not <hypothesized-shape> → hypothesis falsified."
- *Referenced:* "Phase 3 took effect (verified at <ticket-comment-url> -- probe inlined there)."

Banned shapes:

- "Phase 3 took effect." (causal claim with no probe and no reference)
- "Phase 3 took effect (per my earlier investigation)." (reference too vague -- no artifact pointer)
- "The DAG produces the 68.34% baseline." (causal claim about runtime output without a same-turn probe of the actual DAG run)

**Incident justification.** Operator-observed recurrence pattern in claude-configs-public#268: six wrong causal claims stated as fact in one ~6h session, each falsified after the fact at half-hour-or-more cost per incident. The pattern: claims about "X took effect" / "Y drives Z" / "the DAG produces N" stated without same-turn probe, falsified later. Every existing verify-before-X rule gates an *action* (Edit / Write / Bash). Verbal claims happen at the LLM-output layer, which no PreToolUse hook intercepts. This rule gates *claims*, not actions, and lives at the speech-time enforcement surface alongside writing-prose:5.

**Detection markers for Phase 2 scanner** (case-insensitive; intended for a future `hooks/resolver/post-claim-guard.sh` Stop-hook scanner, same re-injection pattern as `standing-order-guard.sh`):

- `(took effect|kicked in|landed|propagated|rolled out|fired|completed successfully)`
- `(is now|now (has|shows|reflects)|currently (contains|produces))`
- `(produces|outputs|emits) (the|a) <noun>`
- `(is|was) (the|a) (cause|reason|driver) of`
- `(verified|confirmed|validated)\s+(that|the)` -- often precedes verification claims the agent did not perform
- `after \w+ the (MV|DAG|job|table)( now| has)` -- temporal-causal pattern common in re-mat / re-deploy claims
- `the (DAG|MV|job|table|hook) (ran|fired|executed) with`

Non-regex flag (LLM-eval for Phase 2 tuning, not a regex trigger): `(because|since|due to) <causal clause without same-turn probe>` -- the causal-clause boundary isn't matchable end-to-end without natural-language understanding; tracked as an LLM-eval candidate, not as a regex marker.

**Anticipated Phase 2 hook path:** `hooks/resolver/post-claim-guard.sh` (not yet implemented). When built, it will follow the `standing-order-guard.sh` re-injection pattern: scan the just-emitted assistant response for the markers above and write `<workspace>/post-claim-warning.json` consumed by the next-turn `UserPromptSubmit` hook. The forward reference exists here so the audit chain isn't asymmetric -- readers know where the mechanical enforcement will live once the Stop-hook surface is confirmed in Claude Code. Same pattern as #266/#267 used for writing-prose:5's anticipated `post-action-guard.sh`.

Scanner flagging policy: flag any causal-marker hit without (a) inline probe in the same response, or (b) a URL / `#<NNN>` / `memory:<file>` / `session:<id>` reference within ±200 characters of the claim. Conservative default; operator-tunable false-positive rate.

**writing-claims:10. Before claiming a change to runtime-loaded code took effect, verify the consuming path matches the edited path.** Any deployment topology with separate write surfaces (worker-image-baked vs git-sync; vendored vs upstream; baked container vs config-loaded; Lambda zip vs source; CDN-cached vs source; firmware-baked vs config-loaded) has at least two paths only one of which the runtime loads. The path you edited and the path the runtime reads are not the same claim until the inspection matches on both. Verification probe must target the consuming path explicitly -- e.g., `kubectl exec <runtime-pod> -- grep <pattern> <consuming-path>`, `ls -la /opt/<project>/...` on the worker, equivalent inspection of the loaded artifact.

This is the operational core of the writing-claims:9 failure mode for runtime-loaded code: agent edits source path A, runtime loads source path B, agent claims the change took effect, runtime never saw it. The cheap test is grepping the consuming path before stating the claim.

**Anticipated Phase 2 hook path:** `hooks/resolver/post-claim-guard.sh` (shared with writing-claims:9 -- see that rule's Phase 2 section). The consuming-path detection is harder to mechanize than the causal-marker grep because it requires knowing the deployment topology (which path the runtime loads). Likely Phase 2 approach: an opt-in per-repo `consuming-paths.json` manifest the hook consults; absent the manifest, the rule remains operator-auditable only.

**Incident pattern.** Two silent no-ops in the same observed session: (a) materialized views claimed effective, but the runtime continued reading a worker-image-baked path instead of the edited registry path -- required a separate unblocker PR to bake the new path. (b) Recon SQL claimed running, but the scheduled DAG was reading stale vendored SQL, not the edited path -- required a separate unblocker PR to refresh the vendor sync. Both came from the same shape: editing the wrong of two equivalent-looking paths when the consuming runtime resolved by deployment-time decision (image bake, vendor sync), not by edit-time path. The generalization to non-Kubernetes topologies (Lambda, CDN, vendored deps, firmware) makes this a writing-claims:9 special-case worth promoting to its own line so the failure mode names itself.

## Override

These rules are mandatory. No `[claim-skip]` override and no `[padding-skip]` override. The same-turn-evidence constraint and the artifact-backing requirement are the entire point; an override defeats the rule. The writing-claims:4 carve-out for new-rule-authoring is in the rule, not an override. `[skill:detect-ai-fingerprints]` trigger-set extension for writing-claims:4 pattern-naming detection is tracked as a v2.x.y follow-up.

## Cross-references

- `[rule:verify-before-execute]` Evidence clause is the parent discipline; these rules extend it to specific claim shapes.
- `[rule:writing-code]` writing-code:4 (verify symbol exists), writing-code:5 (no hypothetical code), and writing-code:6 (doc-edit symmetry) are the action-side counterparts. The boundary: writing-code rules fire when editing code; writing-claims rules fire when stating facts in commit/PR bodies or chat. The same operator workflow may invoke both -- edit code (writing-code rules apply), then write the commit body (writing-claims rules apply).
- `[rule:writing-prose]` writing-prose:5 is the future-tense sibling of writing-claims:9. writing-claims:9 grounds present/past-tense causal claims about production state ("the DAG produces Z"); writing-prose:5 grounds future-tense commitments to action ("I'll monitor the DAG"). Same speech-time enforcement surface, same Phase 1 (rule) / Phase 2 (Stop-hook scanner) staging.
- `[skill:detect-ai-fingerprints]` mechanically enforces writing-claims:2 and writing-claims:3 trigger detection in commit/PR message bodies; the `Verified-by:` trailer is the required pairing. writing-claims:4 trigger-set extension (pattern-naming phrases) is queued as a v2.x.y follow-up. writing-claims:9 detection-markers are outside the scanner's current scope because they target live assistant-response text rather than staged diffs; the Phase 2 follow-up is a separate Stop-hook scanner.
- `[skill:code-review]` checks writing-claims:1 (scope-of-fix across the codebase) and writing-claims:4 (pattern-naming groundedness) at PR time.
- `[skill:self-review]` Quantified Claims section requires writing-claims:8 evidence inline for every specific count stated in the PR body or commit message.

## Migration note (v2.0.x only)

This file is derived from rules 11 and 13 of the deprecated `_no-ai-fingerprints-rules.md`, plus the R-22 confidence-calibration extension proposed in the v1.7.0 round and landed inside v2.0.0. Old rules 10 (verify symbol exists) and 17 (doc-edit symmetry) moved to `_writing-code-rules.md` because they fire at code-edit time; an operator editing code should find them in the writing-code lookup path, not via cross-reference from writing-claims. The underlying claim-grounding family connection is preserved via cross-reference. See `CHANGELOG.md` for the v2.0.0 migration table mapping old rule numbers to new `<file-stem>:<n>` identifiers. This migration note is retained for one release cycle (v2.0.x) and removed in v2.1.0.

## Attribution

Defers to `[rule:output]`. No AI / agent attribution in claims, code, commits, PRs, or comments.
