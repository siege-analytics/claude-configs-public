---
description: Always-on. Twenty mandatory guardrails against AI fingerprints in code, comments, commit messages, PR bodies, and chat output. From four rounds of hostile review and self-diagnosis of siege_utilities work that surfaced concrete failure modes.
---

# No AI Fingerprints

These twenty rules are mandatory. The first eleven came out of an initial hostile review of siege_utilities work; rules 12-15 plus three tightenings (rules 7, 10, 11) came out of an extended siege_utilities arc where ten PRs went through six rounds of review; rules 16-18 came out of a follow-up retrospective where the agent self-diagnosed the gaps that the v1.5.0 rules did not close; rules 19-20 came out of a v1.6.0 negotiation that surfaced two failure modes too narrow for the v1.6.0 cut. The rules are organized stylistic-first (cosmetic but pervasive) and structural-second (the ones that actually cause bugs).

Apply them to everything you write: code, comments, docstrings, commit messages, PR bodies, agent-to-agent messages, and chat output to the operator.

## The twenty rules

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

**10. Verify before asserting.** Before writing code, a test, or documentation that names a method, class, attribute, flag, or behaviour: open the file, grep for the symbol, read the actual signature. Production code that calls a non-existent method (the `create_presentation_from_data` failure mode, where the method is `create_analytics_presentation`) and documentation that asserts current behaviour reflecting aspiration (the INVARIANTS identifier-validation claim) are the canonical failures here. If a behaviour is aspirational, label it: `_aspiration, not current behaviour_` or equivalent. See `[`verify-before-execute`](_verify-before-execute-rules.md)` for the broader claim-grounding discipline that covers prose claims in PR bodies, commit messages, and agent-to-agent messages.

**11. Grep before declaring a fix complete.** When fixing one call site of a problem, search the whole codebase for the same pattern before writing the commit body, the PR title, or the chat update that says the fix is done. The Paragraph-escape fix that needed three rounds (one site, then CodeRabbit pointing out five more, then a follow-up) is the canonical failure mode: the gate moved from "before writing the patch" to "before claiming the patch is complete" because the original phrasing let the agent fix one site, declare done, and only grep when the reviewer pushed back. Same applies to renames, signature changes, and security fixes: scope of the bug is always wider than the diff that surfaced it.

**12. No hypothetical code.** When you write code or a test that depends on a library, service, configuration, or external API, you must have already verified the dependency is reachable in the target environment, and you must exercise the real dependency before claiming the code works. Reachable means reachable in the workspace where the code is being written, in the same session, before the code is written. CI does not count. The PR-body label `untested locally; first run is CI` is a one-time escape hatch when the dependency genuinely cannot be reached locally; using it means the agent has tried and failed, not that the agent did not try. Repeated use of the label is a smell. A mock test that asserts the mock was called is not exercise. The companion `[`environment-preflight`](_environment-preflight-rules.md)` describes the one-time-per-repo inventory that establishes what is reachable; this rule is the per-action application.

**13. Commit-message and PR-body claims are auditable.** Any countable claim ("all four engines," "every call site," "no remaining occurrences," "fully covers the matrix," "completes the operation surface") must be preceded by the falsifying grep in the same response or the same tool sequence. If the grep is in a prior turn, it is stale and does not satisfy the rule. The grep output, not the claim, is the artifact. State the count, then make the claim. The session's worst case: a PR body claiming "all four engines call `_validate_agg_names`" when only two did. Rule 10 covered claims in code and docs but not in commit bodies, PR descriptions, or chat updates to the operator; this rule fills that gap.

**14. BREAKING in the changelog if the change is breaking.** Any change that rejects input previously accepted, returns output previously not returned, or removes a public name gets a `### BREAKING` entry. Determined by diffing the public surface against the previous tag. Until tooling exists to do this mechanically (a public-surface differ that handles `__all__`, leading-underscore convention, and re-exports through `__init__`), the determination is operator-judgment with an explicit checklist: grep for renamed/removed top-level names, grep for new validators that reject previously-accepted input, grep for new return types in functions previously returning a different shape. Tooling is a follow-up ticket; the rule is in force now. The session's worst case: a `groupby_agg` validator was added that rejects `median`, `sem`, and other names pandas previously accepted, shipped in a minor release with no BREAKING section.

**15. Skip messages must name the remediation.** `pytest.skip("X not installed")` is not actionable. `pytest.skip("install X in this interpreter to run, see docs/setup.md")` is. A skip that does not tell the reader what to do to unskip is a skip the project quietly accepts forever. Same for `pytest.xfail`, `unittest.skipIf`, and any conditional `return` that bypasses a test body: name what the reader changes to make the test run.

**16. Mock fidelity.** When mocking an external library (a third-party package on PyPI or equivalent registry, with its own exception hierarchy and response shapes; not `unittest.mock` of stdlib internals):
(a) Use the library's real exception classes via `from <pkg>.exceptions import X`, not `Exception` reassignment.
(b) At least one test in the module must use a fixture built from a real response captured from the library (recorded once, committed as JSON), not a hand-rolled stub.

The session's worst case: a Facebook test fed a plain dict where the SDK returns `AbstractObject`. The test read correctly; the mock just was not the real thing, so production-only AttributeErrors did not surface. Forward-only on existing connector tests; new connector tests must comply.

**17. Doc-edit symmetry.** When code edits in a PR touch a public symbol, the file containing the symbol must be re-read in the same PR (which means the symbol's docstring is re-read for free, since they are colocated). Documentation files that reference the touched symbol by name (matched by grep against the doc tree) must either appear in the same PR's changeset OR the PR body must contain a `Docs-checked: <list of doc files grepped, confirmed in sync>` trailer.

The doc tree default: `**/*.md` minus auto-generated paths (`htmlcov/`, `_build/`, `node_modules/`), plus the canonical names regardless of location (`README.md`, `CHANGELOG.md`, `INVARIANTS.md`, `CONTRIBUTING.md`). Per-repo override at `.claude/doc-paths.toml` that takes a glob list. The trailer names which files were grepped so an auditor can verify post-hoc.

The session's worst case: `INVARIANTS.md` kept asserting current behaviour that did not exist because the agent edited the code without going back to the doc. Aspirational documentation surviving multiple edits is the asymmetric failure rule 10 cannot catch on its own.

**18. Silent error swallowing.** When catching an exception, the handler must do exactly one of:
(a) re-raise the same or a wrapped exception;
(b) return a typed-failure result that the caller pattern-matches on (Result / Either / Option style, or a project-defined dataclass, or `Optional[T]` when the function signature is `Optional[T]` AND the docstring documents `None` as the failure indicator);
(c) perform best-effort cleanup in a `finally` block where the failure does not affect downstream behaviour;
(d) audit-log the failure with full context (input that caused it, exception class, exception message) AND return a typed-failure result per (b).

Patterns banned: bare `except: pass`; `except Exception: log.error(...); return None` where the docstring does not document `None` as failure; `except: continue` in loops without per-iteration audit log; `except Exception: pass  # noqa` without an inline rationale comment naming the specific reason swallowing is correct here.

Forward-only on existing handlers. Existing `Optional[T]`-returning functions get a docstring update grace window of one minor release after R-18 lands; any handler edited after that grace window must comply. New handlers in any PR must comply from day one.

**19. Every `except` block in production code is exercised by a test that forces it to fire.** The test must induce the exception class the handler catches (via dependency injection, monkeypatching, or a real-but-failing input), then assert on the handler's behaviour: the return value, the re-raised exception, the audit-log entry, the typed-failure result. Smoke tests that exercise only the happy path do not count.

Two-line acceptance check at review time: grep for `except` in the diff; for each match, grep test files in the same PR for a test that either (i) names the same exception class via `pytest.raises(<ExcClass>)`, `assertRaises(<ExcClass>)`, or `with raises(<ExcClass>)`, or (ii) calls a fixture or monkeypatch that the test docstring or fixture body documents as inducing the handler's exception. Naming the exception class is the bar; happy-path tests that incidentally exercise the wrapped call do not count.

Forward-only on existing handlers. New `except` blocks in any PR must comply from day one. Existing untested handlers are eligible for promotion to `LESSONS.md` as discovery surfaces them; bulk-backfilling is out of scope.

Two carve-outs:
(a) `except` in `finally`-cleanup code that is purely best-effort (closes a file, removes a temp directory) where the failure is documented as ignorable in the handler comment.
(b) `except` in `__del__` or signal handlers where induction in a test is not safe.

Both carve-outs require a one-line comment naming why no test exists. Without the comment, the handler counts as untested.

The session's concrete instance: the gazetteer Census backend caught `requests.exceptions.RequestException` and fell back to TIGERWeb, but no test forced the Census request to fail. The fallback shape was assumed correct because the happy path returned the same data shape; in practice the fallback path returned a different schema because the TIGERWeb adapter normalised differently. Mechanical detection is partial (cross-file evidence; tracked for v1.6.2 scanner enhancement); judgment-enforced via `[`code-review`](code-review/SKILL.md)` from v1.6.1.

**20. Every callsite of an optionally-imported symbol checks the availability flag first.** When a module declares an optional import via the `try: import X; X_AVAILABLE = True; except ImportError: X_AVAILABLE = False` pattern (or equivalent: `_HAS_X`, `HAS_X`, `X_INSTALLED`, project-defined), every callsite that uses `X` in the same module must be guarded by `if not X_AVAILABLE: <raise|skip|return>` before the call, or be inside a private helper function (leading-underscore name) whose docstring asserts the flag has been checked by the caller. Public callsites must check the flag inline; private helpers can defer to their callers only if the docstring documents the contract.

The guard must produce a clear failure message naming the missing package and the install command: `raise RuntimeError("shapely required; install with: pip install shapely")` not `raise RuntimeError("dependency missing")`. Bare `if not X_AVAILABLE: return None` is acceptable only if the function's documented contract is to be a no-op when the dependency is absent.

Two-line acceptance check at review time: grep for `X_AVAILABLE = False` (or the project's flag name) in the diff; for each module, grep for `X.` usages in that module; every usage outside a guarded block is a violation.

Forward-only. New optional imports must comply; existing modules audited as discovery surfaces them.

The session's concrete instance: both `census_gazetteer.py` and `wikidata_gazetteer.py` had `SHAPELY_AVAILABLE` flags but the geometry-construction callsites used `shapely.geometry.Polygon(...)` without guarding. The first call in an environment without shapely raised `NameError: name 'shapely' is not defined` instead of the intended clear `RuntimeError`. Cross-module re-export case (X re-exported from `__init__.py`, used in sibling module via `from .somemod import X`) is a known scanner gap; the failure mode is loud (immediate NameError) and the pattern is rare. Mechanical detection is high (multi-pass within a file; tracked for v1.6.2 scanner enhancement); judgment-enforced via `[`code-review`](code-review/SKILL.md)` from v1.6.1.

## Override

These rules are mandatory. There is no `[fingerprint-skip]` override.

The closest thing to an exception is the rule-2 carve-out for memory ledgers, skill files, and rule files where structured rationale is the documented format. That carve-out is in the rule, not an override.

If you find yourself wanting to violate a rule for a specific case, surface it to the operator before acting. The rule may need amendment, the case may not warrant the exception you think it does, or both.

## Cross-references

- `[`verify-before-execute`](_verify-before-execute-rules.md)` is the family rule for rules 10, 11, 12, 13, and 17. Verify-before-execute requires same-turn evidence for any side-effecting action; these rules extend the same discipline to claims about symbols (rule 10), scope-of-fix (rule 11), dependency reachability (rule 12), countable assertions in prose (rule 13), and doc-symbol synchronisation (rule 17).
- `[`environment-preflight`](_environment-preflight-rules.md)` is the one-time-per-repo inventory that establishes what is reachable. Rule 12 is the per-action application of that inventory.
- `[`commit`](commit/SKILL.md)` implements rule 5 directly and gates on rule 12 via the affected-tests pre-commit hook (commit-skill step 4). The Body section of the commit skill quotes rule 5's wording and the example body demonstrates the plain-prose style.
- `[`code-review`](code-review/SKILL.md)` checklist gains rules 7 (tests fail on regression, tests import the module), 8 (no cargo-culted patterns), 12 (dependency exercised before claim), 13 (countable claims preceded by grep), 14 (public-surface diff for BREAKING), 16 (mock fidelity), 17 (doc-edit symmetry), and 18 (no silent error swallowing) as project-default review questions.
- `[`detect-ai-fingerprints`](detect-ai-fingerprints/SKILL.md)` mechanically scans the stylistic rules (1, 2, 4, 5, 6) plus rule 13 (countable-claims trigger phrases requiring `Verified-by:` trailer) and rule 15 (skip messages naming actionable remediation). A future enhancement will add the rule-7 grep (test files importing their module under test). Structural rules 7-12, 14, 16, 17, and 18 require code-review judgment.

## Why this rule exists

Three rounds of hostile review of siege_utilities work surfaced concrete failure modes that all read as AI fingerprints. The cost of each individual fingerprint is small (a wordy comment, a redundant test, a self-justifying commit message, a hypothetical dependency, an unverified countable claim, a shape-correct mock that does not enforce real exception classes). The cost of the pattern is large: reviewers stop trusting the output, real bugs hide inside the noise, and the codebase accumulates the kind of low-grade slop that is hard to remove later because nothing about it is individually wrong enough to delete.

The rules ship as mandatory because the alternative (soft guidance, optional discipline) is exactly what produced the original problem. Hard rules with named failure modes are easier to apply than vibes about quality. The motivation is operator-stated: prefer prevention over cure. Friction at write-time is cheap; cleanup at review-time is expensive; cleanup after merge is expensive squared.

## Attribution

Defers to `[`output`](_output-rules.md)`. No AI / agent attribution in code, commits, PRs, or comments.
