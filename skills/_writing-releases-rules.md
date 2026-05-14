---
description: Always-on. Release-act discipline. Any change rejecting previously-accepted input or removing a public name gets a BREAKING entry. Any net increase in skip-site count needs an explicit justification in the PR body. Every DeprecationWarning and PendingDeprecationWarning names a removal target by version or date with a removal-commitment keyword. Applies when cutting a release, merging a PR that affects the public surface or the test-suite coverage, or adding a deprecation warning.
---

# Writing Releases

These rules apply at release-cut time and at PR-merge time when the change affects either the public API surface or the project's skip-site count. Release-cuts ship contracts to downstream consumers; quiet contract changes break consumers silently. Skip-site growth is the test-suite analogue: each accepted skip is a piece of coverage the project quietly accepted losing.

## The four release-writing rules

**writing-releases:1. BREAKING in the changelog if the change is breaking.**

Any change that rejects input previously accepted, returns output previously not returned, or removes a public name gets a `### BREAKING` entry. Determined by diffing the public surface against the previous tag. Until tooling exists to do this mechanically (a public-surface differ that handles `__all__`, leading-underscore convention, and re-exports through `__init__`), the determination is operator-judgment with an explicit checklist:

- Grep for renamed/removed top-level names.
- Grep for new validators that reject previously-accepted input.
- Grep for new return types in functions previously returning a different shape.

Tooling is a follow-up ticket (tracked at the `claude-configs-public` repo's issue #51); the rule is in force now. The session's worst case: a `groupby_agg` validator was added that rejects `median`, `sem`, and other names pandas previously accepted, shipped in a minor release with no BREAKING section.

**Composition with other rules' fix exercises (v2.3.1).** When a fix exercise for a different rule (commonly `[`writing-code`](_writing-code-rules.md)` writing-code:11 no-silent-processes) produces a breaking-change side effect, the BREAKING-changelog entry per writing-releases:1 lands as a separate commit on the same fix-exercise PR rather than being folded into the originating rule's commit. This composes the disciplines without losing per-rule attribution: the writing-code:11 commit cites that rule and stays scoped to the floor-fix; the writing-releases:1 commit cites the BREAKING change separately and stays scoped to the changelog. Anti-pattern: bundling the BREAKING entry into the writing-code:11 commit, which loses the "one commit per rule" eval-loop signal-attribution. The session's concrete instance: pass 6 databricks `runtime_secret_exists` had its return type narrowed from `bool` to `str` to provide a richer floor signal; the writing-code:11 fix and the writing-releases:1 BREAKING entry shipped as two commits on the same PR.

**writing-releases:2. Skip-count trending.**

When a PR adds a new `pytest.skip(...)`, `@pytest.mark.skipif(...)`, or `@pytest.mark.skip(...)` call site, the PR body must contain a `New-skip: <count>; <reason>` trailer naming the new skip count and why it cannot be unskipped today. The scanner counts skip sites in `main` vs the PR's diff; any net increase requires the trailer. Removing a skip needs no trailer.

The Django ORM tests in the originating arc accumulated skips ("Postgres not available," "GDAL not installed") and CI stayed green while the test surface silently shrank. `[`writing-tests`](_writing-tests-rules.md)` writing-tests:3 says each skip must name its remediation; this rule says the project's total skip count must not silently trend upward.

Forward-only; existing skips are grandfathered. Mechanically enforced by `[`detect-ai-fingerprints`](meta/detect-ai-fingerprints/SKILL.md)` `--pr <n>` mode (scans the PR diff for new skip sites, compares against the base, requires the trailer when the count increased).

**writing-releases:3. Deprecation messages name a removal target.**

Every `DeprecationWarning(...)` and `PendingDeprecationWarning(...)` message string must contain BOTH:

- (a) a version anchor (`vN.N.N` pattern) OR a date anchor (`YYYY-MM-DD`), AND
- (b) a removal-commitment keyword from `{remove, removed, dropped, slated for, target, EOL}`.

Both tokens must appear in the same message string. Python implicit string concat across adjacent literals (`"foo " "bar"`) and `+`-concat of string literals are flattened by the scanner before checking, so a deprecation message split across multiple source-line literals does not falsely trigger the rule. The version anchors **when** the removal happens; the keyword anchors **what** is being committed to.

Banned shapes (no commitment):

- `DeprecationWarning("foo, will be removed in a future release")`
- `DeprecationWarning("use bar instead, X is deprecated")` (no version, no removal keyword)
- `DeprecationWarning("deprecated, remove in the next minor")` (no version)
- `DeprecationWarning("foo deprecated since v1.0.0, will be deprecated in a future release")` (version anchors deprecation point only; no removal version)

Acceptable shapes:

- `DeprecationWarning("X deprecated since v3.15.0; will be removed in v3.17.0")`
- `DeprecationWarning("removed in v4.0.0")`
- `DeprecationWarning("EOL by 2026-09-01; use Y instead")`
- `DeprecationWarning("foo, deprecated since v3.15.0 because [reason]. Will be dropped in v3.17.0.")` (version + removal keyword in same string; arbitrary explanation prose between them does not break the check)

The session's concrete instance: `data/dataframe_engine.py` shipped a deprecation shim with the message "remove in the next minor release" approximately 2026-03-30. Three releases shipped since (v3.15.0, v3.15.1, v3.16.0); the shim is still there. The author's intent at write-time was the next minor release; the prose did not commit to a specific version, so when "next minor" arrived no scanner or reviewer flagged the missed removal. The rule's purpose is to make the commitment grep-able.

This is the deprecation-message analogue of `[`writing-tests`](_writing-tests-rules.md)` writing-tests:3 (skip messages name remediation): the runtime warning is the natural site to encode the commitment because that is where consumers see it. PR bodies and CHANGELOG entries are out of scope of this rule (writing-releases:1 covers them).

**Scope: runtime warning calls only.** This rule covers `DeprecationWarning(...)` and `PendingDeprecationWarning(...)` call expressions. Tooling-only deprecation markers (RST `.. deprecated::` directives in docstrings, `@deprecated` decorators, Sphinx-style `.. versionchanged::` notes) are out of scope here. The composing rule that requires a tooling marker also emit a runtime warning is tracked separately as a v2.3.0 candidate; until that lands, an RST-marked deprecation with no accompanying `warnings.warn(...)` call passes this rule (because there is no runtime message to check) but fails the deprecation-completeness intent. Reviewer should catch the tooling-vs-runtime divergence by judgment until the v2.3.0 rule mechanizes it.

Forward-only; existing deprecation warnings are grandfathered with a one-minor-release grace window after writing-releases:3 lands. New deprecations in any PR must comply from day one. Mechanically enforced by `[`detect-ai-fingerprints`](meta/detect-ai-fingerprints/SKILL.md)` AST scanner: walks `Call` nodes whose `func.id` matches `DeprecationWarning|PendingDeprecationWarning`, flattens the message arg through implicit concat and `BinOp(Add)` of `Constant` strings, then applies the both-tokens-present check on the flattened string.

**writing-releases:4. Tooling deprecation markers require runtime warning.**

Functions, methods, classes, or modules marked deprecated in tooling (RST `.. deprecated::` directive in docstring, `@deprecated` decorator, Sphinx `.. versionchanged::` note, equivalent project-defined markers) must emit a `DeprecationWarning` at runtime via `warnings.warn(..., DeprecationWarning)` or equivalent. The runtime warning's message must comply with `[`writing-releases`](_writing-releases-rules.md)` writing-releases:3 (version-or-date anchor + removal-commitment keyword in the same string).

This is the composing rule with writing-releases:3:

- writing-releases:3 covers the runtime-warning side: IF a runtime DeprecationWarning is emitted, the message commits to a removal target.
- writing-releases:4 covers the tooling-vs-runtime divergence: IF a tooling marker says deprecated, the runtime ALSO emits a warning so consumers see it at the call site, not just in Sphinx-rendered docs.

Composed, the two close both halves: tooling marker -> runtime warning required (writing-releases:4) -> message commits to a target (writing-releases:3).

Banned shapes:

- Function with `.. deprecated:: 3.15.0 use Y instead` in docstring but no `warnings.warn(...)` call in the body. Sphinx-rendered docs say deprecated; runtime says nothing; consumers using the function in a non-Sphinx context (notebook, script, REPL) see no signal.
- `@deprecated` decorator applied without a runtime warning side-effect (the decorator's documented behavior must include emitting a warning; a marker-only decorator that does not emit fails the rule).

Acceptable shapes:

- Function with `.. deprecated::` in docstring AND `warnings.warn("X is deprecated since v3.15.0; will be removed in v3.17.0", DeprecationWarning)` at the body's entry.
- `@deprecated` decorator that internally calls `warnings.warn(...)` per writing-releases:3 conventions.
- Marker without runtime warning is acceptable ONLY for deprecated *exports from `__init__.py`* where the warning fires on import attempt rather than call (covered by Python's own `__getattr__` deprecation hook pattern); the import-time warning satisfies the "runtime signal exists" requirement.

The session's concrete instances: pass 2 surfaced 2 `.. deprecated::` markers in `geo/spatial_data.py` without runtime warnings (parked at v2.2.0 ship as RG-5 candidates because writing-releases:3's scope was runtime-only).

Mechanical via AST scanner: walk function/class/module docstrings for RST `.. deprecated::` patterns; walk `decorator_list` for `@deprecated` (or project-configurable equivalent names); cross-reference with body Call nodes for `warnings.warn(...)` with `DeprecationWarning`-or-subclass category. Flag any deprecated-marker without a corresponding runtime warning emission. Forward-only with one-minor-release grace window same as writing-releases:3.

## Override

These rules are mandatory. No `[release-skip]` override. writing-releases:1 stays operator-judgment until the public-surface differ ships; writing-releases:2 is mechanical from v2.0.0 onward; writing-releases:3 is mechanical from v2.2.0 onward (one-minor-release grace window for existing deprecation warnings); writing-releases:4 is mechanical from v2.3.1 onward (one-minor-release grace window for existing tooling-marker-without-runtime-warning patterns).

## Cross-references

- `[`writing-tests`](_writing-tests-rules.md)` writing-tests:3 (skip messages must name the remediation) is the per-skip discipline; writing-releases:2 is the across-PRs trending discipline. Both apply together. writing-tests:3 and writing-releases:3 are siblings: each requires the runtime message (skip / deprecation) name a follow-up commitment grep-able to a future date or version.
- `[`create-pr`](git-workflow/create-pr/SKILL.md)` is the artifact-skill that produces PR bodies; the `New-skip:` and `BREAKING` trailers are required when the rules fire.
- `[`detect-ai-fingerprints`](meta/detect-ai-fingerprints/SKILL.md)` mechanically enforces writing-releases:2 when invoked in `--pr <n>` mode and writing-releases:3 via the AST scanner on `.py` files.

## Migration note

This file is derived from rule 14 of the deprecated `_no-ai-fingerprints-rules.md`, plus the R-21 skip-count-trending extension proposed in the v1.7.0 round and landed inside v2.0.0. See `CHANGELOG.md` for the v2.0.0 migration table. This migration note is retained for one release cycle (v2.0.x) and removed in v2.1.0.

## Attribution

Defers to `[`output`](_output-rules.md)`. No AI / agent attribution in releases, changelogs, commits, or comments.
