---
description: Always-on. Eleven mandatory guardrails against AI fingerprints in code, comments, commit messages, PR bodies, and chat output. From a hostile review of siege_utilities work that surfaced concrete failure modes.
---

# No AI Fingerprints

These eleven rules are mandatory. They came out of a hostile code review of siege_utilities work where the reviewer named eleven concrete failure modes. The rules are organized stylistic-first (cosmetic but pervasive) and structural-second (the ones that actually cause bugs).

Apply them to everything you write: code, comments, docstrings, commit messages, PR bodies, and chat output.

## The eleven rules

### Stylistic

**1. No em-dashes anywhere.** The character at Unicode U+2014 (the long dash often inserted by editors and word-processors) is the single most reliable AI tell. Use `--`, a comma, or a period instead. The same applies to en-dashes (U+2013) used as separators in prose.

**2. No "Why:" or "How to apply:" structured blocks in code comments or commit messages.** If the rationale is non-obvious, write one sentence inline. If it is obvious, write nothing. (This rule does not apply to memory ledgers, skill files, or rule files where structured rationale is the documented format.)

**3. Default to no docstring or a one-liner.** Multi-paragraph Sphinx-style docstrings are reserved for public API surface that is exported and consumed externally. Internal helpers and one-off functions get type hints and at most one sentence.

**4. Strip self-justifying adverbs.** Do not write "deliberately," "intentionally," "explicitly," "fundamentally," "essentially," "crucially," or "notably." If a reader could disagree with the design, the diff and the test cover it; the comment does not need to argue.

**5. Commit messages: subject line + plain-prose body, as long as the explanation genuinely needs and no longer.**
- No bulleted "what this PR does" lists. Bullets are a tell.
- No structural headers (`## Summary`, `## Why`, `## Test plan`) in the commit body. PR bodies may have a short summary and a test plan; the commit body is prose only.
- No self-justifying adverbs (rule 4 applies here too).
- No narrating the diff ("This commit changes line 48 to use StringType").
- Length is determined by what the why genuinely requires. A typo fix is one line; a non-obvious rewrite may be three paragraphs. Padding to look thorough is a tell; truncating to look terse is a different tell.

**6. No PR / sprint / issue references inside code comments.** "Sprint A item 2," "the v3.15.0 hardening," "PR #443 follow-up" all rot the moment the codebase moves. Reference behaviour, not history. The git log is the history layer; the ticket tracker is the planning layer; code comments are the behaviour layer.

### Structural

**7. Tests must fail if the production behaviour breaks.** Before merging any test, ask: "If I reverted the implementation, would this test go red?" If the answer is no or unsure, the test verifies the mock setup, not the code. Delete or rewrite.

**8. No cargo-culted patterns across modules.** When writing tests or modules for multiple similar targets (five API connectors, three storage backends), do not copy-modify the same shape across them. Look at each target's actual public surface and write tests that exercise its specific behaviour. The Vista Social retry logic deserves retry tests; the Snowflake connector does not need fake retry tests just because Vista Social had them.

**9. No speculative abstractions.** Fixtures, helpers, and base classes are introduced only when a second caller already exists. "Future-proofing" without a second caller is dead weight. Revisit when the second caller arrives, not before.

**10. Verify before asserting.** Before writing code, a test, or documentation that names a method, class, attribute, flag, or behaviour: open the file, grep for the symbol, read the actual signature. Production code that calls a non-existent method (the `create_presentation_from_data` failure mode, where the method is `create_analytics_presentation`) and documentation that asserts current behaviour reflecting aspiration (the INVARIANTS identifier-validation claim) are the canonical failures here. If a behaviour is aspirational, label it explicitly: `_aspiration, not current behaviour_` or equivalent.

**11. Grep before patching, not after.** When fixing one call site of a problem, search the whole codebase for the same pattern first. The Paragraph-escape fix that needed three rounds (one site, then CodeRabbit pointing out five more, then a follow-up) is the canonical failure mode. The same applies to renames, signature changes, and security fixes: scope of the bug is always wider than the diff that surfaced it.

## Override

These rules are mandatory. There is no `[fingerprint-skip]` override.

The closest thing to an exception is the rule-2 carve-out for memory ledgers, skill files, and rule files where structured rationale is the documented format. That carve-out is in the rule, not an override.

If you find yourself wanting to violate a rule for a specific case, surface it to the operator before acting. The rule may need amendment, the case may not warrant the exception you think it does, or both.

## Cross-references

- `[`verify-before-execute`](_verify-before-execute-rules.md)` is the family rule for rules 10 and 11. Verify-before-execute requires same-turn evidence for any side-effecting action; rules 10 and 11 extend the same discipline to claims (rule 10) and to scope-of-fix (rule 11).
- `[`commit`](git-workflow/commit/SKILL.md)` implements rule 5 directly. The Body section of the commit skill quotes rule 5's wording and the example body demonstrates the plain-prose style.
- `[`code-review`](coding/code-review/SKILL.md)` checklist gains rules 7 (tests fail on regression) and 8 (no cargo-culted patterns) as project-default review questions.

## Why this rule exists

A hostile code review of siege_utilities work surfaced eleven concrete failure modes that all read as AI fingerprints. The cost of each individual fingerprint is small (a wordy comment, a redundant test, a self-justifying commit message). The cost of the pattern is large: reviewers stop trusting the output, real bugs hide inside the noise, and the codebase accumulates the kind of low-grade slop that is hard to remove later because nothing about it is individually wrong enough to delete.

The rules ship as mandatory because the alternative (soft guidance, optional discipline) is exactly what produced the original problem. Hard rules with named failure modes are easier to apply than vibes about quality.

## Attribution

Defers to `[`output`](_output-rules.md)`. No AI / agent attribution in code, commits, PRs, or comments.
