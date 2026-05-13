---
description: Always-on. Fifteen mandatory guardrails against AI fingerprints in code, comments, commit messages, PR bodies, and chat output. From two rounds of hostile review of siege_utilities work that surfaced concrete failure modes.
---

# No AI Fingerprints

These fifteen rules are mandatory. The first eleven came out of an initial hostile review of siege_utilities work; rules 12-15 plus three tightenings (rules 7, 10, 11) came out of an extended siege_utilities arc where ten PRs went through six rounds of review and surfaced ~40 distinct failure modes. The rules are organized stylistic-first (cosmetic but pervasive) and structural-second (the ones that actually cause bugs).

Apply them to everything you write: code, comments, docstrings, commit messages, PR bodies, agent-to-agent messages, and chat output to the operator.

## The fifteen rules

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

**7. Tests must fail if the production behaviour breaks.** Before merging any test, ask: "If I reverted the implementation, would this test go red?" If the answer is no or unsure, the test verifies the mock setup, not the code. Delete or rewrite. Necessary condition: tests must import the module they claim to test. A test that re-implements the production algorithm in the test body is theater regardless of what it asserts. Check at PR time: grep for `from <project-namespace>` in any `test_*.py` file claiming to cover production code.

**8. No cargo-culted patterns across modules.** When writing tests or modules for multiple similar targets (five API connectors, three storage backends), do not copy-modify the same shape across them. Look at each target's actual public surface and write tests that exercise its specific behaviour. The Vista Social retry logic deserves retry tests; the Snowflake connector does not need fake retry tests just because Vista Social had them.

**9. No speculative abstractions.** Fixtures, helpers, and base classes are introduced only when a second caller already exists. "Future-proofing" without a second caller is dead weight. Revisit when the second caller arrives, not before.

**10. Verify before asserting.** Before writing code, a test, or documentation that names a method, class, attribute, flag, or behaviour: open the file, grep for the symbol, read the actual signature. Production code that calls a non-existent method (the `create_presentation_from_data` failure mode, where the method is `create_analytics_presentation`) and documentation that asserts current behaviour reflecting aspiration (the INVARIANTS identifier-validation claim) are the canonical failures here. If a behaviour is aspirational, label it: `_aspiration, not current behaviour_` or equivalent. See `[rule:verify-before-execute]` for the broader claim-grounding discipline that covers prose claims in PR bodies, commit messages, and agent-to-agent messages.

**11. Grep before declaring a fix complete.** When fixing one call site of a problem, search the whole codebase for the same pattern before writing the commit body, the PR title, or the chat update that says the fix is done. The Paragraph-escape fix that needed three rounds (one site, then CodeRabbit pointing out five more, then a follow-up) is the canonical failure mode: the gate moved from "before writing the patch" to "before claiming the patch is complete" because the original phrasing let the agent fix one site, declare done, and only grep when the reviewer pushed back. Same applies to renames, signature changes, and security fixes: scope of the bug is always wider than the diff that surfaced it.

**12. No hypothetical code.** When you write code or a test that depends on a library, service, configuration, or external API, you must have already verified the dependency is reachable in the target environment, and you must exercise the real dependency before claiming the code works. Reachable means reachable in the workspace where the code is being written, in the same session, before the code is written. CI does not count. The PR-body label `untested locally; first run is CI` is a one-time escape hatch when the dependency genuinely cannot be reached locally; using it means the agent has tried and failed, not that the agent did not try. Repeated use of the label is a smell. A mock test that asserts the mock was called is not exercise. The companion `[rule:environment-preflight]` describes the one-time-per-repo inventory that establishes what is reachable; this rule is the per-action application.

**13. Commit-message and PR-body claims are auditable.** Any countable claim ("all four engines," "every call site," "no remaining occurrences," "fully covers the matrix," "completes the operation surface") must be preceded by the falsifying grep in the same response or the same tool sequence. If the grep is in a prior turn, it is stale and does not satisfy the rule. The grep output, not the claim, is the artifact. State the count, then make the claim. The session's worst case: a PR body claiming "all four engines call `_validate_agg_names`" when only two did. Rule 10 covered claims in code and docs but not in commit bodies, PR descriptions, or chat updates to the operator; this rule fills that gap.

**14. BREAKING in the changelog if the change is breaking.** Any change that rejects input previously accepted, returns output previously not returned, or removes a public name gets a `### BREAKING` entry. Determined by diffing the public surface against the previous tag. Until tooling exists to do this mechanically (a public-surface differ that handles `__all__`, leading-underscore convention, and re-exports through `__init__`), the determination is operator-judgment with an explicit checklist: grep for renamed/removed top-level names, grep for new validators that reject previously-accepted input, grep for new return types in functions previously returning a different shape. Tooling is a follow-up ticket; the rule is in force now. The session's worst case: a `groupby_agg` validator was added that rejects `median`, `sem`, and other names pandas previously accepted, shipped in a minor release with no BREAKING section.

**15. Skip messages must name the remediation.** `pytest.skip("X not installed")` is not actionable. `pytest.skip("install X in this interpreter to run, see docs/setup.md")` is. A skip that does not tell the reader what to do to unskip is a skip the project quietly accepts forever. Same for `pytest.xfail`, `unittest.skipIf`, and any conditional `return` that bypasses a test body: name what the reader changes to make the test run.

## Override

These rules are mandatory. There is no `[fingerprint-skip]` override.

The closest thing to an exception is the rule-2 carve-out for memory ledgers, skill files, and rule files where structured rationale is the documented format. That carve-out is in the rule, not an override.

If you find yourself wanting to violate a rule for a specific case, surface it to the operator before acting. The rule may need amendment, the case may not warrant the exception you think it does, or both.

## Cross-references

- `[rule:verify-before-execute]` is the family rule for rules 10, 11, 12, and 13. Verify-before-execute requires same-turn evidence for any side-effecting action; these four rules extend the same discipline to claims about symbols (rule 10), scope-of-fix (rule 11), dependency reachability (rule 12), and countable assertions in prose (rule 13).
- `[rule:environment-preflight]` is the one-time-per-repo inventory that establishes what is reachable. Rule 12 is the per-action application of that inventory.
- `[skill:commit]` implements rule 5 directly. The Body section of the commit skill quotes rule 5's wording and the example body demonstrates the plain-prose style.
- `[skill:code-review]` checklist gains rules 7 (tests fail on regression, tests import the module), 8 (no cargo-culted patterns), 12 (dependency exercised before claim), 13 (countable claims preceded by grep), and 14 (public-surface diff for BREAKING) as project-default review questions.
- `[skill:detect-ai-fingerprints]` mechanically scans the stylistic rules (1, 2, 4, 5, 6) and a future enhancement will add the rule-7 grep (test files importing their module under test). Structural rules 7-15 require code-review judgment.

## Why this rule exists

Two rounds of hostile review of siege_utilities work surfaced concrete failure modes that all read as AI fingerprints. The cost of each individual fingerprint is small (a wordy comment, a redundant test, a self-justifying commit message, a hypothetical dependency, an unverified countable claim). The cost of the pattern is large: reviewers stop trusting the output, real bugs hide inside the noise, and the codebase accumulates the kind of low-grade slop that is hard to remove later because nothing about it is individually wrong enough to delete.

The rules ship as mandatory because the alternative (soft guidance, optional discipline) is exactly what produced the original problem. Hard rules with named failure modes are easier to apply than vibes about quality. The motivation is operator-stated: prefer prevention over cure. Friction at write-time is cheap; cleanup at review-time is expensive; cleanup after merge is expensive squared.

## Attribution

Defers to `[rule:output]`. No AI / agent attribution in code, commits, PRs, or comments.
