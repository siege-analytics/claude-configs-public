---
description: Always-on. Claim-grounding discipline. Grep before declaring a fix complete; ground countable claims in same-turn evidence; ground unquantified completeness claims (loop closed, ready to ship) in the same evidence shape; ground invented framework signals (new pattern names, coined disciplines) in existing artifacts; verify external-resource recommendations (URLs, file paths, tickets, free-vs-paid) at recommendation time; require three samples before promoting a pattern to a rule. Applies whenever the agent states a fact in a commit body, PR body, agent-to-agent message, or chat to the operator. Fact-grounding at code-edit time (verify symbol exists, doc-edit symmetry, dependency reachable) lives in `_writing-code-rules.md`.
---

# Writing Claims

These four rules apply whenever the agent states a fact in a commit body, PR body, agent-to-agent message, or chat to the operator. The unifying boundary is "verify before claiming": the rules fire at claim time, after the action that the claim is about has happened.

The sibling boundary in `_writing-code-rules.md` is "verify before touching code": rules that fire at code-edit time (verify the symbol exists before naming it, verify the dependency is reachable before depending on it, re-read docs that reference the symbol you just edited). The two files split the same underlying claim-grounding family by temporal trigger; consult writing-code when editing code, consult writing-claims when stating facts.

The parent discipline is `[rule:verify-before-execute]` Evidence clause: same-turn tool calls back factual claims. These four rules are specific shapes of that discipline applied at claim time.

## The six claim-grounding rules

**writing-claims:1. Grep before declaring a fix complete.** When fixing one call site of a problem, search the whole codebase for the same pattern before writing the commit body, the PR title, or the chat update that says the fix is done. The Paragraph-escape fix that needed three rounds (one site, then CodeRabbit pointing out five more, then a follow-up) is the canonical failure mode: the gate moved from "before writing the patch" to "before claiming the patch is complete" because the original phrasing let the agent fix one site, declare done, and only grep when the reviewer pushed back. Same applies to renames, signature changes, and security fixes: scope of the bug is always wider than the diff that surfaced it.

**writing-claims:2. Countable claims are auditable.** Any countable claim ("all four engines," "every call site," "no remaining occurrences," "fully covers the matrix," "completes the operation surface") must be preceded by the falsifying grep in the same response or the same tool sequence. If the grep is in a prior turn, it is stale and does not satisfy the rule. The grep output, not the claim, is the artifact. State the count, then make the claim. The session's worst case: a PR body claiming "all four engines call `_validate_agg_names`" when only two did.

In commit messages and PR bodies, a countable claim must be paired with a `Verified-by: <command output excerpt>` trailer. `[skill:detect-ai-fingerprints]` scans for the trigger phrases and requires the trailer.

**writing-claims:3. Confidence calibration: unquantified completeness claims need the same grounding.** Statements that imply finality without a count -- "I have completed," "addressed all," "ready to ship," "no remaining," "loop closed," "fully covers" -- are claims subject to writing-claims:2 even when no integer is named. Before stating them, run the falsifying check (re-run the test suite that would catch a regression, re-grep for the pattern, re-read the PR comments). State the check in the same response or the same artifact, then make the claim. The check is the artifact; the claim is the conclusion.

`[skill:detect-ai-fingerprints]` extends writing-claims:2's trigger set to cover these unquantified phrases. Same `Verified-by:` trailer requirement.

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

## Override

These rules are mandatory. No `[claim-skip]` override and no `[padding-skip]` override. The same-turn-evidence constraint and the artifact-backing requirement are the entire point; an override defeats the rule. The writing-claims:4 carve-out for new-rule-authoring is in the rule, not an override. `[skill:detect-ai-fingerprints]` trigger-set extension for writing-claims:4 pattern-naming detection is tracked as a v2.x.y follow-up.

## Cross-references

- `[rule:verify-before-execute]` Evidence clause is the parent discipline; these rules extend it to specific claim shapes.
- `[rule:writing-code]` writing-code:4 (verify symbol exists), writing-code:5 (no hypothetical code), and writing-code:6 (doc-edit symmetry) are the action-side counterparts. The boundary: writing-code rules fire when editing code; writing-claims rules fire when stating facts in commit/PR bodies or chat. The same operator workflow may invoke both -- edit code (writing-code rules apply), then write the commit body (writing-claims rules apply).
- `[skill:detect-ai-fingerprints]` mechanically enforces writing-claims:2 and writing-claims:3 trigger detection in commit/PR message bodies; the `Verified-by:` trailer is the required pairing. writing-claims:4 trigger-set extension (pattern-naming phrases) is queued as a v2.x.y follow-up.
- `[skill:code-review]` checks writing-claims:1 (scope-of-fix across the codebase) and writing-claims:4 (pattern-naming groundedness) at PR time.

## Migration note (v2.0.x only)

This file is derived from rules 11 and 13 of the deprecated `_no-ai-fingerprints-rules.md`, plus the R-22 confidence-calibration extension proposed in the v1.7.0 round and landed inside v2.0.0. Old rules 10 (verify symbol exists) and 17 (doc-edit symmetry) moved to `_writing-code-rules.md` because they fire at code-edit time; an operator editing code should find them in the writing-code lookup path, not via cross-reference from writing-claims. The underlying claim-grounding family connection is preserved via cross-reference. See `CHANGELOG.md` for the v2.0.0 migration table mapping old rule numbers to new `<file-stem>:<n>` identifiers. This migration note is retained for one release cycle (v2.0.x) and removed in v2.1.0.

## Attribution

Defers to `[rule:output]`. No AI / agent attribution in claims, code, commits, PRs, or comments.
