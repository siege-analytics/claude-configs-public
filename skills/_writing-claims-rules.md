---
description: Always-on. Claim-grounding discipline. Grep before declaring a fix complete; ground countable claims in same-turn evidence; ground unquantified completeness claims (loop closed, ready to ship) in the same evidence shape. Applies whenever the agent states a fact in a commit body, PR body, agent-to-agent message, or chat to the operator. Fact-grounding at code-edit time (verify symbol exists, doc-edit symmetry, dependency reachable) lives in `_writing-code-rules.md`.
---

# Writing Claims

These three rules apply whenever the agent states a fact in a commit body, PR body, agent-to-agent message, or chat to the operator. The unifying boundary is "verify before claiming": the rules fire at claim time, after the action that the claim is about has happened.

The sibling boundary in `_writing-code-rules.md` is "verify before touching code": rules that fire at code-edit time (verify the symbol exists before naming it, verify the dependency is reachable before depending on it, re-read docs that reference the symbol you just edited). The two files split the same underlying claim-grounding family by temporal trigger; consult writing-code when editing code, consult writing-claims when stating facts.

The parent discipline is `[`verify-before-execute`](_verify-before-execute-rules.md)` Evidence clause: same-turn tool calls back factual claims. These three rules are specific shapes of that discipline applied at claim time.

## The three claim-grounding rules

**writing-claims:1. Grep before declaring a fix complete.** When fixing one call site of a problem, search the whole codebase for the same pattern before writing the commit body, the PR title, or the chat update that says the fix is done. The Paragraph-escape fix that needed three rounds (one site, then CodeRabbit pointing out five more, then a follow-up) is the canonical failure mode: the gate moved from "before writing the patch" to "before claiming the patch is complete" because the original phrasing let the agent fix one site, declare done, and only grep when the reviewer pushed back. Same applies to renames, signature changes, and security fixes: scope of the bug is always wider than the diff that surfaced it.

**writing-claims:2. Countable claims are auditable.** Any countable claim ("all four engines," "every call site," "no remaining occurrences," "fully covers the matrix," "completes the operation surface") must be preceded by the falsifying grep in the same response or the same tool sequence. If the grep is in a prior turn, it is stale and does not satisfy the rule. The grep output, not the claim, is the artifact. State the count, then make the claim. The session's worst case: a PR body claiming "all four engines call `_validate_agg_names`" when only two did.

In commit messages and PR bodies, a countable claim must be paired with a `Verified-by: <command output excerpt>` trailer. `[`detect-ai-fingerprints`](meta/detect-ai-fingerprints/SKILL.md)` scans for the trigger phrases and requires the trailer.

**writing-claims:3. Confidence calibration: unquantified completeness claims need the same grounding.** Statements that imply finality without a count -- "I have completed," "addressed all," "ready to ship," "no remaining," "loop closed," "fully covers" -- are claims subject to writing-claims:2 even when no integer is named. Before stating them, run the falsifying check (re-run the test suite that would catch a regression, re-grep for the pattern, re-read the PR comments). State the check in the same response or the same artifact, then make the claim. The check is the artifact; the claim is the conclusion.

`[`detect-ai-fingerprints`](meta/detect-ai-fingerprints/SKILL.md)` extends writing-claims:2's trigger set to cover these unquantified phrases. Same `Verified-by:` trailer requirement.

## Override

These rules are mandatory. No `[claim-skip]` override. The same-turn-evidence constraint is the entire point; an override defeats the rule.

## Cross-references

- `[`verify-before-execute`](_verify-before-execute-rules.md)` Evidence clause is the parent discipline; these rules extend it to specific claim shapes.
- `[`writing-code`](_writing-code-rules.md)` writing-code:4 (verify symbol exists), writing-code:5 (no hypothetical code), and writing-code:6 (doc-edit symmetry) are the action-side counterparts. The boundary: writing-code rules fire when editing code; writing-claims rules fire when stating facts in commit/PR bodies or chat. The same operator workflow may invoke both -- edit code (writing-code rules apply), then write the commit body (writing-claims rules apply).
- `[`detect-ai-fingerprints`](meta/detect-ai-fingerprints/SKILL.md)` mechanically enforces writing-claims:2 and writing-claims:3 trigger detection in commit/PR message bodies; the `Verified-by:` trailer is the required pairing.
- `[`code-review`](coding/code-review/SKILL.md)` checks writing-claims:1 (scope-of-fix across the codebase) at PR time.

## Migration note (v2.0.x only)

This file is derived from rules 11 and 13 of the deprecated `_no-ai-fingerprints-rules.md`, plus the R-22 confidence-calibration extension proposed in the v1.7.0 round and landed inside v2.0.0. Old rules 10 (verify symbol exists) and 17 (doc-edit symmetry) moved to `_writing-code-rules.md` because they fire at code-edit time; an operator editing code should find them in the writing-code lookup path, not via cross-reference from writing-claims. The underlying claim-grounding family connection is preserved via cross-reference. See `CHANGELOG.md` for the v2.0.0 migration table mapping old rule numbers to new `<file-stem>:<n>` identifiers. This migration note is retained for one release cycle (v2.0.x) and removed in v2.1.0.

## Attribution

Defers to `[`output`](_output-rules.md)`. No AI / agent attribution in claims, code, commits, PRs, or comments.
