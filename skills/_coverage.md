---
description: Coverage matrix. Maps each known failure mode (from the originating siege_utilities arcs and subsequent retrospectives) to the rule that covers it, the enforcement mechanism, the tooling status, and (for non-mechanical rows) the prevention-path that names what mechanization would require. Format is TOML; one entry per failure mode; rule_id uses the `<file-stem>:<n>` scheme. Read when auditing which rules are mechanical vs honor-system, or when surfacing tooling gaps for follow-up.
---

# Coverage matrix

This file is the audit artifact that answers "are the rules sufficient?" with grep-able truth instead of estimation. Each entry maps one failure mode to the rule(s) that cover it and the mechanical status of enforcement. The judgment column is not a permanent home: every entry that is not `mechanical` carries a `prevention_path` field naming what would mechanize it (or why mechanization is genuinely out of scope), so the matrix doubles as a worklist.

For the human-readable per-act files, see `RULES.md`. The matrix below is the machine-readable companion.

## Format

Each entry is a TOML table under `[[failure_mode]]` with these fields:

- `name` -- short identifier for the failure mode
- `description` -- one-sentence summary of the failure
- `rule_id` -- list of one or more `<file-stem>:<n>` identifiers covering this failure
- `enforcement` -- one of `scanner | hook | code-review | operator-honor` (the strongest enforcement that applies)
- `tooling_status` -- one of `mechanical | judgment | gap`. `mechanical` = automated check fires. `judgment` = rule exists; enforcement is human or agent reviewer. `gap` = no rule exists yet to prevent the failure mode (distinct from `judgment`; the matrix preserves the distinction so a row's status answers "is this prevented at all" separately from "is the prevention mechanized").
- `prevention_path` -- required when `tooling_status` is `judgment` or `gap`; either `needs: <description of the tooling that would mechanize this>` or `judgment-only: <reason mechanization is out of scope>`. Omitted when `tooling_status = "mechanical"`.
- `originating_arc` -- inline table with `session-id` (required), `pr-number` (omitted when no single landing PR), `incident-name` (omitted when no named incident). The session-id always carries the row; pr-number and incident-name are queryable when present.

## Entries

```toml
[[failure_mode]]
name = "ai-typographic-unicode"
description = "AI-typographic Unicode characters in prose: em-dash U+2014, en-dash U+2013, arrows U+2192/U+2190/U+21D2/U+21D0, curly quotes U+2018/U+2019/U+201C/U+201D, ellipsis U+2026, middle dot U+00B7, bullet U+2022, non-breaking space U+00A0. The em/en dash kernel is the historical originating finding; the broader char class was added in v2.2.0 from the dataframe_engine.py review."
rule_id = ["writing-prose:1"]
enforcement = "scanner"
tooling_status = "mechanical"
originating_arc = { session-id = "260502-vital-channel", incident-name = "initial-siege-utilities-hostile-review" }

[[failure_mode]]
name = "structured-rationale-blocks"
description = "Why: / How to apply: blocks in code comments or commit messages."
rule_id = ["writing-prose:2"]
enforcement = "scanner"
tooling_status = "mechanical"
originating_arc = { session-id = "260502-vital-channel", incident-name = "initial-siege-utilities-hostile-review" }

[[failure_mode]]
name = "self-justifying-adverbs"
description = "Words like deliberately, intentionally, explicitly, fundamentally, essentially, crucially, notably arguing with the reader."
rule_id = ["writing-prose:3"]
enforcement = "scanner"
tooling_status = "mechanical"
originating_arc = { session-id = "260502-vital-channel", incident-name = "initial-siege-utilities-hostile-review" }

[[failure_mode]]
name = "bulleted-commit-bodies"
description = "Bulleted what-this-PR-does lists or ## Summary / ## Why headers in commit bodies."
rule_id = ["writing-prose:4"]
enforcement = "scanner"
tooling_status = "mechanical"
originating_arc = { session-id = "260502-vital-channel", incident-name = "initial-siege-utilities-hostile-review" }

[[failure_mode]]
name = "multi-paragraph-docstrings-on-internal-helpers"
description = "Sphinx-style multi-paragraph docstrings on functions that are not exported API."
rule_id = ["writing-code:1"]
enforcement = "code-review"
tooling_status = "judgment"
prevention_path = "needs: project-namespace + __all__ detection to identify public vs internal API; without it the rule cannot mechanically distinguish 'helper' from 'public function'"
originating_arc = { session-id = "260502-vital-channel", incident-name = "initial-siege-utilities-hostile-review" }

[[failure_mode]]
name = "history-references-in-code-comments"
description = "PR #N, Sprint X, vN.N.N hardening, TICKET-N references in code comments."
rule_id = ["writing-code:2"]
enforcement = "scanner"
tooling_status = "mechanical"
originating_arc = { session-id = "260502-vital-channel", incident-name = "initial-siege-utilities-hostile-review" }

[[failure_mode]]
name = "speculative-abstractions"
description = "Helpers, fixtures, base classes introduced with no second caller."
rule_id = ["writing-code:3"]
enforcement = "code-review"
tooling_status = "judgment"
prevention_path = "judgment-only: 'second caller exists' is not mechanically determinable without runtime context or whole-codebase call-graph analysis"
originating_arc = { session-id = "260502-vital-channel", incident-name = "initial-siege-utilities-hostile-review" }

[[failure_mode]]
name = "asserting-nonexistent-symbol"
description = "Code, test, or doc names a method/class/attribute that does not exist (e.g., create_presentation_from_data when the method is create_analytics_presentation)."
rule_id = ["writing-code:4"]
enforcement = "code-review"
tooling_status = "judgment"
prevention_path = "needs: project-namespace detection plus symbol-existence grep at PR-open"
originating_arc = { session-id = "260502-vital-channel", incident-name = "create-presentation-from-data-typo" }

[[failure_mode]]
name = "hypothetical-code-no-installed-dep"
description = "Code shipped depending on a library that was not verified installed in the workspace; agent infers availability from imports failing in the default Python rather than checking the actual interpreter."
rule_id = ["writing-code:5"]
enforcement = "hook"
tooling_status = "mechanical"
originating_arc = { session-id = "260502-vital-channel", incident-name = "szsh-pyspark-failure" }

[[failure_mode]]
name = "doc-asserts-aspirational-behaviour"
description = "INVARIANTS.md or similar doc asserts current behaviour reflecting aspiration; code edits drift the doc out of sync silently because the agent edits code without re-reading the doc."
rule_id = ["writing-code:6"]
enforcement = "code-review"
tooling_status = "judgment"
prevention_path = "needs: cross-file grep at PR-open: for each touched public symbol, list doc files referencing it, compare against PR changeset"
originating_arc = { session-id = "260502-vital-channel", incident-name = "invariants-identifier-validation-failure" }

[[failure_mode]]
name = "silent-exception-swallowing"
description = "except Exception: pass or except Exception: log.error; return None without typed failure documented in docstring. AST scanner detects four banned shapes (Pass / Return None|False / Continue / log+terminator) with carve-outs for # noqa, ImportError+flag-pattern, and Optional[T]+docstring."
rule_id = ["writing-code:7"]
enforcement = "scanner"
tooling_status = "mechanical"
originating_arc = { session-id = "260502-vital-channel", incident-name = "v1.6.0-retrospective" }

[[failure_mode]]
name = "tests-that-pass-on-broken-production"
description = "Tests that pass even when the implementation is reverted; tests that re-implement the production algorithm in the test body."
rule_id = ["writing-tests:1"]
enforcement = "code-review"
tooling_status = "judgment"
prevention_path = "needs: AST-walk per test file for module-import detection plus project-namespace config"
originating_arc = { session-id = "260502-vital-channel", incident-name = "extended-siege-utilities-arc" }

[[failure_mode]]
name = "cargo-culted-test-shapes-across-modules"
description = "Test file pasted across five similar connectors with same retry/error/timeout tests regardless of what each connector actually does."
rule_id = ["writing-tests:2"]
enforcement = "code-review"
tooling_status = "judgment"
prevention_path = "judgment-only: mechanical cross-file similarity detection is heuristic-laden and would generate too many false positives to be useful"
originating_arc = { session-id = "260502-vital-channel", incident-name = "vista-social-snowflake-cargo-cult" }

[[failure_mode]]
name = "skip-messages-without-remediation"
description = "pytest.skip('X not installed') with no instructions for how to unskip."
rule_id = ["writing-tests:3"]
enforcement = "scanner"
tooling_status = "mechanical"
originating_arc = { session-id = "260502-vital-channel", incident-name = "extended-siege-utilities-arc" }

[[failure_mode]]
name = "shape-correct-mock-without-real-exceptions"
description = "MagicMock() that stands in for an external library but does not use the library's real exception classes."
rule_id = ["writing-tests:4"]
enforcement = "code-review"
tooling_status = "judgment"
prevention_path = "needs: import-graph analysis to detect Mock() / MagicMock() instantiations whose target is a third-party library, then verify the test file imports the library's exception module"
originating_arc = { session-id = "260502-vital-channel", incident-name = "facebook-sdk-abstractobject-failure" }

[[failure_mode]]
name = "mock-without-spec"
description = "MagicMock() without spec=<RealClass>, allowing calls to non-existent methods to silently succeed."
rule_id = ["writing-tests:4"]
enforcement = "scanner"
tooling_status = "mechanical"
originating_arc = { session-id = "260502-vital-channel", incident-name = "v1.7.0-retrospective" }

[[failure_mode]]
name = "fixture-without-real-response"
description = "Mock fixture is a hand-rolled dict instead of a real captured response from the library; production shapes diverge silently."
rule_id = ["writing-tests:4"]
enforcement = "code-review"
tooling_status = "judgment"
prevention_path = "needs: fixture-shape validator that compares against committed JSON capture; requires per-project fixture-format config"
originating_arc = { session-id = "260502-vital-channel", incident-name = "facebook-sdk-plain-dict-fixture" }

[[failure_mode]]
name = "fix-declared-complete-before-scope-grep"
description = "Single-site fix declared done without grepping for the same pattern elsewhere; Paragraph-escape three-round failure."
rule_id = ["writing-claims:1"]
enforcement = "code-review"
tooling_status = "judgment"
prevention_path = "judgment-only: detecting 'a fix is being declared complete' from natural-language text is not reliably mechanizable; the rule's value is in operator/reviewer enforcement"
originating_arc = { session-id = "260502-vital-channel", incident-name = "paragraph-escape-three-rounds" }

[[failure_mode]]
name = "countable-claim-unverified"
description = "PR body claims 'all four engines call X' when only two do; commit body claims 'no remaining occurrences' without the grep that would falsify it."
rule_id = ["writing-claims:2"]
enforcement = "scanner"
tooling_status = "mechanical"
originating_arc = { session-id = "260502-vital-channel", incident-name = "all-four-engines-false-claim" }

[[failure_mode]]
name = "completeness-claim-unverified"
description = "'Loop closed', 'ready to ship', 'addressed all', 'no remaining' without the falsifying check; same family as countable claims but no integer is named."
rule_id = ["writing-claims:3"]
enforcement = "scanner"
tooling_status = "mechanical"
originating_arc = { session-id = "260502-vital-channel", incident-name = "v1.7.0-retrospective" }

[[failure_mode]]
name = "breaking-change-shipped-as-minor"
description = "A change rejects previously-accepted input or removes a public name; ships in a minor release with no BREAKING entry in CHANGELOG."
rule_id = ["writing-releases:1"]
enforcement = "operator-honor"
tooling_status = "gap"
prevention_path = "needs: public-surface differ that handles __all__, leading-underscore convention, and re-exports through __init__ (tracked at upstream issue #51)"
originating_arc = { session-id = "260502-vital-channel", incident-name = "groupby-agg-breaking-shipped-as-minor" }

[[failure_mode]]
name = "skip-count-silent-trend"
description = "PR adds new pytest.skip sites; CI stays green; test surface shrinks invisibly because no one is counting."
rule_id = ["writing-releases:2"]
enforcement = "scanner"
tooling_status = "mechanical"
originating_arc = { session-id = "260502-vital-channel", incident-name = "v1.7.0-retrospective" }

[[failure_mode]]
name = "untested-exception-handler"
description = "An except block in production code with no test that forces the exception to fire; behaviour on failure is unverified until the first production firing reveals divergence."
rule_id = ["writing-tests:5"]
enforcement = "code-review"
tooling_status = "judgment"
prevention_path = "needs: cross-file evidence detector that grep-matches except-class in source against pytest.raises / assertRaises / with raises in the same PR's test files (tracked at upstream issue #56 for v1.6.2)"
originating_arc = { session-id = "260502-vital-channel", pr-number = 55, incident-name = "gazetteer-census-fallback-schema-divergence" }

[[failure_mode]]
name = "unguarded-optional-import-callsite"
description = "Module declares X_AVAILABLE = False fallback for an optional import but a callsite uses X.foo(...) without first checking X_AVAILABLE; first call in a missing-dep environment raises NameError instead of the intended clear RuntimeError naming the package and install command."
rule_id = ["writing-code:8"]
enforcement = "code-review"
tooling_status = "judgment"
prevention_path = "needs: multi-pass-within-file detector that extracts the optional-import flag, then re-scans for unguarded callsites (tracked at upstream issue #57 for v1.6.2)"
originating_arc = { session-id = "260502-vital-channel", pr-number = 55, incident-name = "shapely-available-unguarded-callsites" }

[[failure_mode]]
name = "silently-dropped-parameter"
description = "Method or function signature accepts a parameter; the implementation neither uses it, raises NotImplementedError, documents it as a no-op, nor forwards it via **kwargs. Caller's override has no effect; the API lies about its surface."
rule_id = ["writing-code:9"]
enforcement = "scanner"
tooling_status = "mechanical"
originating_arc = { session-id = "260502-vital-channel", incident-name = "siege-utilities-dataframe-engine-hostile-review-2026-05-13" }

[[failure_mode]]
name = "capability-registry-impl-mismatch"
description = "Module exposes a central 'supported X' registry (frozenset, dict, class attr) consumed by a validator; an implementation gated by the validator does not support every registry item; caller passes validation, then dies inside the impl with a confusing AttributeError or similar."
rule_id = ["writing-code:10"]
enforcement = "code-review"
tooling_status = "judgment"
prevention_path = "judgment-only: cross-implementation tracing (validator -> registry -> consumers) requires symbolic execution or extensive AST graph-building, infeasible at scanner tier"
originating_arc = { session-id = "260502-vital-channel", incident-name = "siege-utilities-dataframe-engine-hostile-review-2026-05-13" }

[[failure_mode]]
name = "deprecation-without-removal-target"
description = "DeprecationWarning or PendingDeprecationWarning message string lacks a version-or-date anchor and a removal-commitment keyword in the same string; 'in a future release' / 'next minor' / 'eventually' shipped without grep-able commitment."
rule_id = ["writing-releases:3"]
enforcement = "scanner"
tooling_status = "mechanical"
originating_arc = { session-id = "260502-vital-channel", incident-name = "siege-utilities-dataframe-engine-hostile-review-2026-05-13" }

[[failure_mode]]
name = "no-silent-process"
description = "Side-effecting function/method/script/scheduled-process completes without producing an inspectable signal; auditor cannot confirm the action happened from output alone. Mutate-and-return-None is the canonical shape (e.g. PowerPoint _add_*_slide methods mutate the prs argument and return None)."
rule_id = ["writing-code:11"]
enforcement = "code-review"
tooling_status = "judgment"
prevention_path = "needs: AST-walk for side-effect detection (Call to known-side-effecting builtins like open/os.write/subprocess.run, plus method calls on known-mutable types), cross-reference with return type and log calls in body. Tractable for v2.3.x scanner enhancement."
originating_arc = { session-id = "260502-vital-channel", incident-name = "operator-directive-no-silent-processes-2026-05-13", pr-number = 478 }

[[failure_mode]]
name = "duplicate-imports-at-module-scope"
description = "Module has duplicate `import X` statements or `from X import Y` repeated; or aliased import where the alias is never used. Slop from branch-merging that linters often miss."
rule_id = ["writing-code:12"]
enforcement = "scanner"
tooling_status = "mechanical"
originating_arc = { session-id = "260502-vital-channel", incident-name = "siege-utilities-spatial-data-pass-2-duplicate-imports-2026-05-13" }

[[failure_mode]]
name = "inconsistent-failure-mode-contract"
description = "A function declares two failure-indication mechanisms (return None for one failure shape, raise for another), OR sibling methods within a class follow different failure contracts (one raises, one returns None) without naming differentiation. Caller has to handle two failure paths or the API surface lies about its uniformity. Empirical note (v2.4.0): rename-over-converge option in writing-code:13's body has zero-of-five firing rate across v2.3.0 + v2.3.1 fix exercises; real-world inconsistent contracts converge cleanly. Option retained for completeness; recurrence threshold set at 5+ exercises before reconsidering removal."
rule_id = ["writing-code:13"]
enforcement = "code-review"
tooling_status = "judgment"
prevention_path = "needs: control-flow analysis (Optional return + raise on different paths in same function); also cross-method analysis for sibling-method consistency; tractable for v2.3.x scanner enhancement"
originating_arc = { session-id = "260502-vital-channel", incident-name = "siege-utilities-spatial-data-pass-2-and-powerpoint-pass-4-failure-contract-2026-05-13" }

[[failure_mode]]
name = "deprecation-marker-without-runtime-warning"
description = "Function/class/module marked deprecated in tooling (RST .. deprecated:: directive in docstring, @deprecated decorator, Sphinx versionchanged note) but body lacks corresponding runtime warnings.warn(..., DeprecationWarning) call. Sphinx-rendered docs say deprecated; runtime says nothing; consumers in non-Sphinx contexts (notebook, script, REPL) see no signal."
rule_id = ["writing-releases:4"]
enforcement = "scanner"
tooling_status = "mechanical"
originating_arc = { session-id = "260502-vital-channel", incident-name = "siege-utilities-spatial-data-pass-2-rst-deprecated-markers-2026-05-13" }

[[failure_mode]]
name = "exception-as-dispatch-content-distinguishable"
description = "Function uses try/except as the dispatcher between alternative successful operations (parse-as-WKB-or-WKT, fetch-from-cache-or-source) when the input could be inspected to dispatch deterministically. Catch-all swallow returns a different valid result via alternative path; corrupt input falls through to the wrong branch and produces confusing downstream errors or silent wrong-data."
rule_id = ["writing-code:14"]
enforcement = "code-review"
tooling_status = "judgment"
prevention_path = "needs: AST scanner for catch-all except whose body returns a different result without raise/re-raise (TC5 alternative-return-shape from sibling's writing-code:7 scanner test-case set). Tractable for v2.4.x scanner enhancement."
originating_arc = { session-id = "260502-vital-channel", incident-name = "rg6-content-distinguishable-triangulation-2026-05-13" }
```

## Tooling-status summary

- `mechanical` rows: 15 (writing-prose:1, :2, :3, :4; writing-code:2, :5, :7, :9, :12; writing-tests:3; writing-tests:4 mock-without-spec; writing-claims:2, :3; writing-releases:2, :3, :4).
- `judgment` rows: 16 (writing-code:1, :3, :4, :6, :8, :10, :11, :13, :14; writing-tests:1, :2, :4 fixture-real-response, :4 mock-real-exceptions, :5; writing-claims:1; counted with dual-coverage rows on writing-tests:4).
- `gap` rows: 1 (writing-releases:1, pending public-surface differ at upstream issue #51).

The `gap` and `judgment` categories stay distinct: `gap` means no rule exists to prevent the failure mode and only operator honor catches it; `judgment` means a rule exists with defined enforcement (code review, scanner, hook) but the enforcement is judgment-bound rather than mechanical. The distinction lets the matrix answer "is this prevented at all?" separately from "is the prevention mechanized?".

The mechanical/judgment ratio is the matrix's audit signal. Each `judgment` row that gains a `prevention_path` of the form `needs: <X>` is a candidate ratchet target; each `judgment-only: <reason>` row is acknowledged as out of scope and stays put. The single `gap` row is the operator's worklist for adding a rule (or shipping the differ tool that converts it to `mechanical`).

## Querying the matrix

Because `originating_arc` is structured, the matrix is queryable. Examples of useful greps:

- All rows from a session: `grep 'session-id = "260502-vital-channel"' _coverage.md`
- All rows from a specific incident: `grep 'incident-name = "facebook-sdk-abstractobject-failure"' _coverage.md`
- All gap rows: `grep 'tooling_status = "gap"' _coverage.md`
- All judgment-only rows (acknowledged out of scope): `grep 'judgment-only:' _coverage.md`
- All needs-tooling rows (ratchet candidates): `grep '"needs:' _coverage.md`

## Attribution

Defers to `[`output`](_output-rules.md)`. No AI / agent attribution in this file or its updates.
