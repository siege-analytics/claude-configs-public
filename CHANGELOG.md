# Changelog

All notable changes to this project are documented here. Versioning follows [SemVer](https://semver.org/).

## [Unreleased]

(no changes pending)

## [2.3.1] -- 2026-05-13

Cohort release picking up the v2.3.0 fix-exercise carve-outs plus three new rules and one corollary fold negotiated across the v2.3.0 audit cycle. Per the v2.3.0 sequencing decision, v2.3.0 shipped writing-code:11 alone to keep the eval-loop signal clean for that endemic-pattern rule; v2.3.1 picks up everything that was deferred or surfaced during that cycle.

Negotiated with sibling session 260502-vital-channel; cross-pass evidence from passes 2-8 of the siege_utilities hostile review (geo, vista_social, powerpoint, logging, databricks, credential_manager). All five additions have multi-instance evidence per the rule-eval-loop discipline (`[skill:rule-eval-loop]`, shipped in PR #65).

### Added -- writing-code:12 (no duplicate imports at module scope)

Mechanical via AST scanner. Imports must appear exactly once at module scope; aliased duplicates flagged unless both aliases are referenced. Conditional imports inside `try`/`except ImportError` blocks are availability fallbacks per writing-code:8, not duplicates. Originating evidence: `geo/spatial_data.py` had two pairs of duplicate module-level imports (`import os` twice; `import warnings` parallel to `import warnings as _warnings_mod`), slop from branch-merging linters missed.

### Added -- writing-code:13 (consistent failure-mode contract)

Judgment-enforced. A function declares ONE failure-indication mechanism (Optional with documented None-as-failure, OR typed exception, OR Result-style); sibling methods within a class follow the same contract or differentiate naming when the contract genuinely diverges. Originating evidence: `_get_dataset_metadata` returns None for HTTP non-2xx but raises for other failures; `PowerPointGenerator.generate_powerpoint_presentation` returns `bool` while sibling `create_*_presentation` methods raise; `credential_manager` 1Password backend mixes None-not-found and raise-transport-error without surfacing the distinction. Composes with writing-code:7 (silent error swallowing): :7 covers the per-handler choice; :13 covers the across-function and across-method consistency.

### Added -- writing-releases:4 (tooling deprecation markers require runtime warning)

Mechanical via AST scanner. Functions/classes/modules marked deprecated in tooling (RST `.. deprecated::`, `@deprecated` decorator, Sphinx `.. versionchanged::`) must emit `warnings.warn(..., DeprecationWarning)` at runtime; the runtime warning's message complies with writing-releases:3 (version-or-date anchor + removal-commitment keyword). Composes with writing-releases:3: :4 covers the tooling-vs-runtime divergence; :3 covers the runtime message format. Originating evidence: pass 2 surfaced 2 RST `.. deprecated::` markers in `geo/spatial_data.py` without runtime warnings (parked at v2.2.0 ship as RG-5 candidates because writing-releases:3's scope was runtime-only).

### Changed -- writing-code:11 carve-outs (three additions to body)

Three carve-outs surfaced during the v2.3.0 fix exercise (siege_utilities PR #487 + PR #484), all banked verbatim from sibling's eval observations:

1. **Contract-preservation override** on per-process-type advisory: when changing the floor shape from (a) to (b) or vice versa would break an established contract, choose the additive option even if the advisory would suggest otherwise. Originating evidence: `_ensure_sedona`'s pre-existing `None`-return contract made (b) log-only the right floor choice.
2. **Family-of-methods scaling pattern** for N>5 method families: document the convention at the enclosing class/module docstring, then per-method application can be ratchet-applied across multiple PRs without re-establishing the pattern. Originating evidence: PowerPoint `_add_*_slide` family (19 methods, applied to 4 + ratcheted at Issue #485).
3. **Per-rule-commit composition with writing-releases:1** when a writing-code:11 fix produces a breaking-change side effect: the BREAKING-changelog entry per writing-releases:1 lands as a separate commit on the same fix-exercise PR, composing the disciplines without losing per-rule attribution. Lifted from databricks `bool` -> `str` return-type changes in PR #487.

### Changed -- writing-releases:1 (composition discipline added to body)

The third writing-code:11 carve-out belongs operationally with writing-releases:1, not writing-code:11. Body extended to name the composition pattern: when a fix exercise for writing-code:11 (or any other rule) produces a breaking-change side effect, the BREAKING entry lands as a separate commit on the same PR.

### Changed -- writing-tests:1 retroactive-fix corollary (body extension, RG-9 fold)

Tests that codify now-banned behaviour as feature must be renamed and have the rule citation in their docstring or commit message; do not delete. Author-time correctness != rule-time correctness; rules win. Two-instance evidence: siege_utilities PR #478 (engine-abstraction silent-swallow) + PR #484 (credential security domain silent-swallow). The corollary's three-step recipe (rename / cite rule / preserve test) was applied reproducibly across both module shapes; it was also self-validated in PR #484 against the unshipped rule, suggesting the discipline is intuitive enough that experienced operators converge on it organically.

### Coverage matrix updates

Three new entries: `duplicate-imports-at-module-scope` (writing-code:12, mechanical), `inconsistent-failure-mode-contract` (writing-code:13, judgment), `deprecation-marker-without-runtime-warning` (writing-releases:4, mechanical). Tooling-status summary: mechanical 12 -> 14; judgment 15 -> 16; gap unchanged at 1.

### Followups

- writing-code:7 mechanical scanner: queued for v2.3.1.x patch with one-minor-release grace window. Sibling will provide the test-case set from the 14-violation aggregation across 8 audit passes.
- writing-code:11 scanner enhancement: tracked for v2.3.x.
- v2.4.0 cohort: RG-6 (exception-as-dispatch banned when content-distinguishable) + RG-8 (method-naming consistency within a class). RG-6 has triangulated evidence from three module shapes ready to draft from.

## [2.3.0] -- 2026-05-13

Adds writing-code:11 (no silent processes), the success-side complement to writing-code:7 (silent error swallowing). Operator-stated principle: "no process should be written without output or logging. We should always be able to measure output." Negotiated across two rounds with sibling session 260502-vital-channel; cross-pass evidence from four hostile-review passes (engines/dataframe_engine.py, geo/spatial_data.py, reporting/powerpoint_generator.py, core/logging.py + core/sql_safety.py) confirmed the success-side observability gap is endemic across module shapes.

This release ships writing-code:11 alone per the v2.3.0 sequencing decision: the rule's blast radius (an internal-helper pattern endemic across the codebase) deserves a dedicated release-and-fix-exercise lane so eval-loop signal stays clean. v2.3.1 will pick up RG-3 (duplicate-imports), RG-4 (inconsistent failure-mode contracts), RG-5 (deprecation-marker-without-runtime-warning), plus any wording carve-outs from the v2.3.0 fix exercise.

### Added -- writing-code:11 (no silent processes)

Every side-effecting process must produce at least one observable signal at completion. Two-level structure:

**Required minimum (non-negotiable floor):** every side-effecting process must produce at least one of (a) an inspectable return value naming what happened, OR (b) a log line at INFO level or higher naming what happened. The side-effect-artifact alone (file written, mutation done) does NOT satisfy the floor; an auditor cannot confirm the action happened from the function's output.

**Additional shapes for high-signal processes:** (c) a metric written to a metrics sink, (d) a side-effect with audit trail. These are additive to the (a)-or-(b) floor, never substitutes.

**Carve-outs:** pure functions with no side effects (return value IS the output); test assertions (pytest pass/fail dispatch is the signal); CLI subcommands whose stdout output is the contract (printed output IS the observability).

**Per-process-type advisory:** internal helper -> probably (a); library entry point -> probably (a) + (b); batch / scheduled -> probably (b) + (c) + (d); migration -> probably (b) + (d).

Originating evidence:

- The PowerPoint `_add_*_slide` private methods (~20 instances in one file) mutate the `prs` argument and return `None`. Endemic mutate-and-return-None pattern across the codebase.
- `_ensure_sedona` re-raises on ImportError (writing-code:7-correct) but on success returns `None` silently. Caller cannot tell which path was taken.
- core/logging.py (PR #480 in siege_utilities) shipped a silent NullHandler fallback when file handler creation fails; the LOGGING module silently failing to log. Highest-irony finding of the cycle and the kind of failure writing-code:11 will catch reflexively.

### Family-of-discipline framing

writing-code:11 is the success-side complement to writing-code:7 (silent error swallowing). Paired along the error/success boundary, the two rules close the observable-signal failure family. Same pattern as RG-5 (v2.3.1 candidate) composing with writing-releases:3 (tooling-marker / runtime-warning halves).

### Tooling status

Judgment-enforced via `[skill:code-review]` at v2.3.0. Mechanical detection is tractable (AST-walk for side-effect builtins + cross-reference with return type and log calls); tracked for v2.3.x scanner enhancement.

### Coverage matrix

One new entry: `no-silent-process` (writing-code:11, code-review enforcement, judgment status). Tooling-status summary updated: judgment 14 -> 15.

### Migration

No identifier remap. Existing silent processes in any consumer codebase are flagged when discovered but the rule's expectation is that codebases address them as discovery surfaces them, not big-bang. The fix-exercise pattern from v2.2.0-rc1 (each rule application becomes a per-rule commit citing the rule that drove the change) applies here.

### Followups

- v2.3.1: RG-3 (duplicate-imports), RG-4 (inconsistent failure-mode contracts), RG-5 (deprecation-marker-without-runtime-warning), RG-7 wording carve-outs from v2.3.0 fix exercise, writing-tests:1 retroactive-fix corollary extension (folds RG-9).
- v2.4.0: RG-6 (exception-as-dispatch banned when content-distinguishable), RG-8 (method-naming consistency within a class).
- writing-code:11 scanner enhancement -> v2.3.x.
- Rule-eval-loop meta-skill at `skills/meta/rule-eval-loop/SKILL.md` -> opens after v2.3.0 fix exercise lands (recurrence-3 promotion threshold met by LESSON 323a0f5).

## [2.2.0] -- 2026-05-13

Adds four rule changes from a hostile-review pass on `siege_utilities/engines/dataframe_engine.py` (lines 1-450) by sibling session 260502-vital-channel. Cross-session negotiation across four rounds of `send_agent_message` ratified per-rule wording, scanner specs, and sequencing. A second hostile-review pass on `siege_utilities/geo/spatial_data.py` (different module shape: HTTP data fetchers, 2258 lines) confirmed the four rules transfer cleanly across module shapes; cross-pass evidence aggregates 13+ writing-prose:1 hits, 2 writing-releases:3 hits (one per pass; two additional pass-2 findings are RST `.. deprecated::` markers without runtime warnings and parked as RG-5 v2.3.0 candidates per the scope split below), 3 writing-code:9 hits, 1 writing-code:10 hit. Rules are not over-fit to the originating arc.

### Added -- writing-code:9 (no silently-dropped parameters)

When a method or function signature accepts a parameter, the implementation must use it, raise `NotImplementedError` with the documented message format, document it as a base-class no-op (subclasses that legitimately use the parameter need no disclaimer), or pass through via `**kwargs`. Decorator-consumed parameters are a judgment-enforced carve-out the AST scanner cannot see; reviewer attests in PR body.

Originating evidence: `load_polygons` and `load_lines` in `dataframe_engine.py` accepted `format: str = "auto"` and `geometry_col: str = "geometry"`; the default implementation called `self.read_spatial(path, crs=crs)` and ignored both. Caller's `format="shapefile"` override had no effect.

Mechanical via AST scanner at `skills/meta/detect-ai-fingerprints/scan_ast.py`. Decorator allow-list (default `{functools.wraps, contextlib.contextmanager, classmethod, staticmethod, property}`) extensible per project via `.claude/scanner-config.toml`'s `scanner.allow_decorators` array.

### Added -- writing-code:10 (capability declarations match implementations)

When a module exposes a central "supported X" registry consumed by a validator, every implementation the validator gates access to must support every registry item. Sibling rule of writing-code:9: writing-code:9 fires per-method-signature; writing-code:10 fires at architecture review when a registry's shape is examined against each consumer.

Originating evidence: `_SUPPORTED_AGG_NAMES` accepts `approx_count_distinct` but the pandas implementation does not implement it; pandas callers pass validation, then die with `AttributeError`.

Judgment-enforced; coverage matrix carries `prevention_path = "judgment-only: cross-implementation tracing requires symbolic execution or extensive AST graph-building, infeasible at scanner tier"`.

### Added -- writing-releases:3 (deprecation messages name a removal target)

Every `DeprecationWarning(...)` and `PendingDeprecationWarning(...)` message string must contain BOTH a version anchor (`vN.N.N`) or date anchor (`YYYY-MM-DD`) AND a removal-commitment keyword from `{remove, removed, dropped, slated for, target, EOL}`. Both tokens must appear in the same message string. The version anchors when the removal happens; the keyword anchors what is being committed to.

Originating evidence: `data/dataframe_engine.py` shipped a deprecation shim 2026-03-30 with the message "remove in the next minor release"; three releases shipped since (v3.15.0, v3.15.1, v3.16.0), shim is still present. The message had no grep-able commitment for what "next minor" meant.

Scope: runtime warning calls only. RST `.. deprecated::` directives in docstrings, `@deprecated` decorators, and similar tooling-only markers are out of scope here; the composing rule that requires a tooling marker also emit a runtime warning is tracked as a v2.3.0 candidate.

Mechanical via the same AST scanner. Catches three call shapes: direct construction (`DeprecationWarning(msg)`), `warnings.warn(msg, DeprecationWarning)` two-arg form, and `warnings.warn(msg, category=DeprecationWarning)` keyword form. Flattens implicit string concat (`"foo " "bar"`) and `BinOp(Add)` of string literals before checking; f-strings with all-Constant parts are flattened, dynamic f-strings are skipped. Forward-only with one-minor-release grace window for existing deprecations.

### Changed -- writing-prose:1 renamed and extended (semantic rename, identifier stable)

The rule formerly titled "No em-dashes anywhere" is renamed to **"No AI-typographic Unicode characters."** Same identifier (`writing-prose:1`); same kernel (em/en dashes still covered); broader char class added: arrows (U+2192 U+2190 U+21D2 U+21D0), curly quotes (U+2018 U+2019 U+201C U+201D), ellipsis (U+2026), middle dot (U+00B7), bullet (U+2022), non-breaking space (U+00A0).

Audit-trail callout: consumers grepping LESSONS or PR bodies for "no em-dashes" should know the rule is the same identifier and still covers em-dashes/en-dashes as its kernel; the broader char class additions are the same discipline applied to the same family of typographic Unicode that produces the same AI-generated reading. The migration is content-level, not identifier-level -- no identifier remap, no migration table.

Path-based whitelist for U+00A0 in `templates/` and `i18n/` (legitimate in HTML email templates and i18n string tables). Other characters in the list have no path-based whitelist.

Per-class scanner emit IDs (`writing-prose-1-arrow-right`, `writing-prose-1-curly-squote-left`, `writing-prose-1-nbsp`, etc.) so the fixer knows the substitution to apply without re-reading the violating line. Continues the existing `writing-prose-1-em-dash` / `-en-dash` granularity.

### Changed -- coverage matrix entry rename and tooling-status counts

`em-dash-as-ai-tell` row renamed to `ai-typographic-unicode` and description rewritten to cover the full char class with em/en dashes named as the historical kernel and the broader additions credited to v2.2.0. Three new entries: `silently-dropped-parameter` (writing-code:9, mechanical), `capability-registry-impl-mismatch` (writing-code:10, judgment-only), `deprecation-without-removal-target` (writing-releases:3, mechanical). Tooling-status summary: mechanical 10 -> 12, judgment 13 -> 14, gap unchanged at 1.

### Migration

No identifier remap. Consumers do not need to update inline `[rule:writing-prose:1]` references -- the identifier and the kernel are unchanged. Consumers documenting the rule's title in their own files should update the wording from "No em-dashes" to "No AI-typographic Unicode characters" if the title is quoted; if the documentation refers to the rule by identifier only, no change.

Forward-only enforcement for the new rules:

- writing-code:9 mechanical from v2.2.0; existing silent-drop sites are flagged when scanned but the rule's expectation is that codebases address them as discovery surfaces them.
- writing-code:10 judgment-enforced; reviewer applies per architecture review.
- writing-releases:3 mechanical from v2.2.0 with one-minor-release grace window for existing deprecation warnings; new deprecations in any PR must comply day one.

### Followups

- Test fixtures for `scan_ast.py` (synthetic .py files exercising every carve-out + every failure case) are a v2.2.x candidate. First-cut scope ships with the rule body grace-window covering the expectation; smoke-tested in PR.
- Three rule-gap candidates (RG-3 duplicate-imports, RG-4 inconsistent-failure-contracts, RG-5 deprecation-marker-without-runtime-warning) surfaced in pass 2 are deferred to v2.3.0 negotiation pending the v2.2.0 fix-exercise evidence.
- Diff-line-filtering on `scan_ast.py` (report only violations whose line falls in the diff's added-line set) is a v2.2.x candidate if false-positive volume in pre-existing code becomes a problem during the fix exercise.

## [2.0.1] -- 2026-05-13

Patch fixing two gaps in v2.0.0 surfaced by parent session 260502-vital-channel during load-verification of the `v2.0.0-flat` sync.

### Fixed -- build script now includes RULES.md and _coverage.md (#62)

`bin/build.py`'s `find_rules()` matched `_*-rules.md` only. The two new v2.0.0 files at `skills/` root (`RULES.md` entry point, `_coverage.md` matrix) did not match the pattern and were never copied to `dist/<layout>/skills/`. Consumers syncing from `v2.0.0-flat` got the per-act rule files but not the entry-point or matrix. Build extended to copy both via `write_resolved` so inline `[skill:X]` and `[rule:X]` tokens get layout-resolved.

### Fixed -- two stale rule-N references in commit/SKILL.md (#62)

The v2.0.0 cross-reference pass caught the top-level checklist and main section bodies but missed two inline mentions inside the Affected-tests gate subsection prose:

- Line 137: `rule 7` -> `[rule:writing-tests]` writing-tests:1
- Line 152: `Rule 12` -> `[rule:writing-code]` writing-code:5

### Known stale refs (out of scope for this patch)

`skills/_definition-of-done-rules.md` lines 43 and 84 reference `[skill:coding] Rule 6`. No `Rule 6` exists in `skills/coding/`. Pre-dates v2.0.0; was already broken in v1.6.x. Filing separately for triage; not a v2.0.0 regression.

### Migration

Consumers pinned to `v2.0.0-flat` should re-sync to `v2.0.1-flat` to pick up `skills/RULES.md` and `skills/_coverage.md`.

## [2.0.0] -- 2026-05-13

Major release: refactor the always-on rule set from a single accreting file into per-act rule files, plus a coverage matrix that turns "is the failure mode prevented?" from estimation into grep-able truth. Rule wording is unchanged from the v1.6.x line; placements move to per-act homes and identifiers move from flat numbering (rule 1-20) to per-file `<file-stem>:<n>`.

### BREAKING

`_no-ai-fingerprints-rules.md` is deleted. Rules are decomposed by act into five files: `_writing-prose-rules.md`, `_writing-code-rules.md`, `_writing-tests-rules.md`, `_writing-claims-rules.md`, `_writing-releases-rules.md`. Identifiers change from `rule N` to `<file-stem>:<n>` (e.g., `writing-prose:1` for the em-dash rule). The resolver glob `_*-rules.md` picks up the new files automatically; consumers that hard-coded the old filename must update once. Skills (commit, code-review, detect-ai-fingerprints, lessons-learned) are updated to cite the new identifiers; consumers that quote the old `rule N` form in their own documentation should update via the migration table below.

### Migration table

| Old | New |
|---|---|
| rule 1 (em-dashes) | writing-prose:1 |
| rule 2 (Why/How blocks) | writing-prose:2 |
| rule 3 (docstring brevity) | writing-code:1 |
| rule 4 (banned adverbs) | writing-prose:3 |
| rule 5 (commit-message body) | writing-prose:4 |
| rule 6 (history refs in code comments) | writing-code:2 |
| rule 7 (tests fail on revert + import the module) | writing-tests:1 |
| rule 8 (no cargo-cult patterns) | writing-tests:2 |
| rule 9 (no speculative abstractions) | writing-code:3 |
| rule 10 (verify symbol exists) | writing-code:4 |
| rule 11 (grep before declaring fix complete) | writing-claims:1 |
| rule 12 (no hypothetical code) | writing-code:5 |
| rule 13 (countable claims auditable) | writing-claims:2 |
| rule 14 (BREAKING in changelog) | writing-releases:1 |
| rule 15 (skip messages name remediation) | writing-tests:3 |
| rule 16 (mock fidelity) | writing-tests:4 |
| rule 17 (doc-edit symmetry) | writing-code:6 |
| rule 18 (silent error swallowing) | writing-code:7 |
| rule 19 (untested exception handlers) | writing-tests:5 |
| rule 20 (conditional-import callsite hygiene) | writing-code:8 |

Each new rule file carries an addendum at the bottom naming which old rule numbers it derives from; addendums are retained for one release cycle (v2.0.x) and removed in v2.1.0. The CHANGELOG migration table stays for the audit trail.

### Added -- five per-act rule files

- `_writing-prose-rules.md` (4 rules): em-dashes, structured rationale blocks, banned adverbs, commit-message body shape. For natural-language output: chat, commit/PR bodies, agent-to-agent messages, comments-as-prose.
- `_writing-code-rules.md` (8 rules): docstring brevity, no history references in code comments, no speculative abstractions, verify symbol exists, no hypothetical code, doc-edit symmetry, silent error swallowing, conditional-import callsite hygiene. For writing production code (any `.py` outside `tests/`).
- `_writing-tests-rules.md` (5 rules): tests fail on revert + import the module, no cargo-cult patterns, skip messages name remediation, mock fidelity (real exceptions, real-shape fixtures, `spec=` on `MagicMock`), every `except` block exercised by a test that forces it. For writing tests or fixtures.
- `_writing-claims-rules.md` (3 rules): grep before declaring a fix complete, countable claims auditable, confidence calibration on unquantified completeness claims. For stating facts in commit/PR bodies, agent-to-agent messages, chat to the operator.
- `_writing-releases-rules.md` (2 rules): BREAKING in CHANGELOG when public surface changes incompatibly, skip-count must not silently trend upward. For cutting releases or merging PRs that affect the public surface or test-suite skip count.

### Added -- entry point at `skills/RULES.md`

`RULES.md` is the single human-facing entry point. Lists the five per-act rule files plus the meta-rule files (verify-before-execute, definition-of-done, environment-preflight, output, principles, language-specific). One line per file with a one-line description and "when it applies" column.

### Added -- coverage matrix at `skills/_coverage.md`

Machine-readable TOML matrix mapping each known failure mode (from the originating siege_utilities arcs and subsequent retrospectives) to the rule(s) that cover it, the enforcement mechanism, the tooling status, and a `prevention_path` field naming what would mechanize judgment-only and gap rows. The `originating_arc` field is structured (session-id, pr-number, incident-name) for cross-referencing; example queries are documented at the bottom of the file. The matrix doubles as a worklist: each judgment row is a candidate ratchet target; the single gap row is the operator's worklist.

### Framework articulation

The boundary between writing-code and writing-claims is "family-of-enforcement-trigger" rather than "family-of-failure". Rules that fire at code-edit time (verify symbol exists, no hypothetical code, doc-edit symmetry) live in writing-code; rules that fire at claim time (grep before declaring fix complete, countable claims, completeness claims) live in writing-claims. The two share an underlying claim-grounding family that is preserved via cross-reference. This framework was articulated by parent session 260502-vital-channel during the rule-12 placement reopen and locks the writing-code/writing-claims split; the next reviewer should not have to re-derive it.

### Negotiation provenance

Five `send_agent_message` rounds with parent session 260502-vital-channel across approximately three hours (drafted in parallel side-branches; placement decisions reconciled to parent's table; ambiguous placements ratified individually). Operator delegated negotiation authority and weighted parent's lived-experience diagnosis heavily.

### Skill updates

`[skill:commit]`, `[skill:code-review]`, `[skill:detect-ai-fingerprints]` (SKILL.md and `scan.sh` emit strings), `[skill:lessons-learned]`, `[rule:verify-before-execute]`, `[rule:environment-preflight]` updated to cite the new `<file-stem>:<n>` identifiers. The detect-ai-fingerprints scanner emits `writing-prose-1-em-dash` instead of `rule-1-em-dash`, etc.

### Known issues (filed as v2.0.x follow-ups)

- Bash 3.2 scanner exit-code crash on the violations path (script reaches exit cleanly under `bash -x` trace mode but exits 139 without trace; all violations emit correctly before the crash, but callers that check `$?` see 139 instead of 1). Pre-existing; surfaced during v2.0.0 self-scan validation. To file post-merge.

## [1.6.1] -- 2026-05-13

Adds rules 19 and 20 to `[rule:no-ai-fingerprints]`. Two rules deferred from v1.6.0 with multi-round negotiation rather than time-pressure collapse. Wording for both confirmed verbatim across two `send_agent_message` rounds with parent session 260502-vital-channel before merge.

### Added -- two new no-ai-fingerprints rules (#55)

- Rule 19 (untested exception handlers): every `except` block in production code is exercised by a test that forces it via `pytest.raises(<ExcClass>)`, `assertRaises(<ExcClass>)`, or `with raises(<ExcClass>)`, OR via a documented inducing fixture or monkeypatch. Two carve-outs (`finally` best-effort cleanup, `__del__` / signal handlers) require a one-line comment naming why no test exists. Forward-only on existing handlers.
- Rule 20 (conditional-import callsite hygiene): every callsite of an optionally-imported symbol checks the availability flag inline before the call, OR is inside a private helper (leading-underscore name) whose docstring asserts the flag has been checked by the caller. The guard's failure message must name the missing package and the install command. Forward-only on existing modules.

### Changed -- code-review checklist gains rules 19 and 20 (#55)

`skills/coding/code-review/SKILL.md` checklist adds two judgment-enforced items naming both rules. The mechanical-pre-flight scanner section is updated to describe the new judgment-only checks specific to v1.6.1.

### Scanner enhancements deferred to v1.6.2

Cross-file evidence detection for R-19 (handler in source file, test in test file with matching exception class) and multi-pass within-file detection for R-20 (extract flag, then re-scan for unguarded callsites) are new scan shapes that don't fit the existing line-by-line scanner. Filed as a single v1.6.2 milestone so they ship together.

### Migration to v2.0.0

Rule 19 lands at `writing-tests:5` in v2.0.0; rule 20 lands at `writing-code:8`. The v2.0.0 refactor PR (in side-branch drafting) folds both into their per-act files at rebase time.

### Negotiation provenance

Two `send_agent_message` rounds between sessions 260502-pure-vista and 260502-vital-channel. R-19 acceptance check tightened to specific patterns (`pytest.raises` / `assertRaises` / `with raises` family); R-20 deferral clause restricted to private helpers with docstring-asserted contracts. Operator delegated negotiation authority and set the binding 2026-05-20 deadline; ship landed seven days early.

### No breaking changes

Additive (two new rules, two checklist additions). No rule weakened or removed; no skill contract changed.

## [1.6.0] -- 2026-05-13

Adds rules 16-18 to `[rule:no-ai-fingerprints]`, a new affected-tests gate as `[skill:commit]` step 4, and two scanner enhancements (countable-claims with `Verified-by:` trailer; actionable skip messages). From a parent-session retrospective on v1.5.0 coverage; the parent estimated 70% prevention, this release closes most of the gap.

### Added -- three new no-ai-fingerprints rules (#53)

- Rule 16 (mock fidelity): when mocking a third-party library (not stdlib), use the library's real exception classes via `from <pkg>.exceptions import X` and at least one test in the module must use a fixture built from a real captured response (committed as JSON), not a hand-rolled stub. Forward-only on existing tests.
- Rule 17 (doc-edit symmetry): when code edits in a PR touch a public symbol, the file containing the symbol must be re-read in the same PR; documentation files referencing the symbol by name must either appear in the changeset OR the PR body must contain a `Docs-checked: <list>` trailer. Default doc-tree scope is `**/*.md` minus auto-generated paths plus the canonical names; per-repo override at `.claude/doc-paths.toml`.
- Rule 18 (silent error swallowing): exception handlers must re-raise, return a typed-failure result, do best-effort cleanup in a `finally` block, or audit-log-plus-typed-failure. The `bare except: pass` and `except Exception: log.error(...); return None` families are banned unless the function signature is `Optional[T]` AND the docstring documents `None` as the failure indicator. Forward-only on existing handlers with a one-minor-release docstring grace window for existing `Optional[T]` functions.

### Added -- affected-tests gate in commit skill (#53)

`[skill:commit]` step 4 runs `pytest -x` against test files matching the touched source files in the staged diff. Default heuristic: given `<package>/X.py`, look for `tests/test_X.py`, `tests/test_X_*.py`, `tests/<package>/test_X.py`. Per-repo override at `.claude/affected-tests.toml` with a source-glob to test-glob mapping. 60-second timeout per affected-test run; tests slower than that should be marked `slow` and run at PR-open time. Non-zero exit blocks the commit; `[run-skip: <reason>]` override exists for legitimate cases (test infra under repair, dependency unavailable per rule 12 escape hatch).

This is the mechanical enforcement of rule 12 (no hypothetical code). The honor-system version was "I checked"; the mechanical version is "the tests ran and passed in the same commit-attempt."

### Changed -- detect-ai-fingerprints scanner gains two checks (#53)

- Rule 13 mechanical enforcement: scanner detects countable-claim trigger phrases (`all N`, `all X engines/connectors/call sites`, `every (call site/engine/caller/connector)`, `no remaining`, `fully covers`, `completes the X surface`) in commit and PR message bodies. When present, the body must contain a `Verified-by: <command output excerpt>` trailer. Without the trailer, the claim line is reported as `rule-13-countable-claim-no-verified-by`. Conservative trigger set on first roll-out; tunable in v1.6.x.
- Rule 15 mechanical enforcement: scanner detects `pytest.skip(...)`, `pytest.xfail(...)`, `@pytest.mark.skipif(...)`, `self.skipTest(...)`, `unittest.skip(...)` in `.py` files in the staged diff. The skip message must contain at least one actionable verb (`install`, `set`, `configure`, `run`, `enable`, `start`, `provide`, `export`) plus an identifier-shaped token (env var, command name, file path, package name). Without both, the line is reported as `rule-15-skip-not-actionable`.

### Committed for v1.6.1 within seven days

R-19 (untested exception handlers; forward-only adoption) and R-20 (conditional-import callsite hygiene; may need a paired-helper-pattern design as a separate ticket) land together in v1.6.1 with full multi-round negotiation. Missing the seven-day window is itself a LESSONS entry.

### On separate tracks

- Public-surface differ tooling for rule 14 stays at #51, operator-judgment enforcement until the differ ships.
- Retrospective post-merge scan (T5) is a separate proposal post-v1.6.1.

### Negotiation provenance

Two `send_agent_message` rounds between sessions 260502-pure-vista and 260502-vital-channel. R-18 wording includes the parent's grace-window refinement for `Optional[T]`-returning functions; all other wording confirmed verbatim. Operator delegated negotiation authority and weighted the parent's lived-experience diagnosis heavily.

### No breaking changes

Additive (three new rules, one new commit-skill step, two new scanner checks). No rule weakened or removed; no skill contract removed. The commit-skill step 4 addition is new behaviour but follows the existing `[run-skip]`-style override pattern.

## [1.5.0] -- 2026-05-13

Adds rules 12-15 to `[rule:no-ai-fingerprints]`, tightens rules 7, 10, and 11, and ships a new always-on sibling `[rule:environment-preflight]`. From an extended siege_utilities arc that surfaced ~40 distinct failure modes through ten PRs and six rounds of hostile review; the existing eleven rules covered roughly 60% of them.

### Added -- four new no-ai-fingerprints rules (#50)

- Rule 12 (no hypothetical code): when code or a test depends on a library, service, configuration, or external API, the dependency must be reachable in the workspace where the code is being written, in the same session, before the code is written. CI does not count. The PR-body label `untested locally; first run is CI` is a one-time escape hatch when local truly cannot reach the dependency.
- Rule 13 (auditable countable claims): any countable claim ("all four engines," "every call site," "no remaining occurrences") must be preceded by the falsifying grep in the same response. The grep output, not the claim, is the artifact. State the count, then make the claim.
- Rule 14 (BREAKING in changelog): any change that rejects input previously accepted, returns output previously not returned, or removes a public name gets a `### BREAKING` entry. Determination is operator-judgment with explicit checklist until the public-surface differ tool exists (tracked at #51).
- Rule 15 (skip messages name remediation): `pytest.skip("X not installed")` is rejected; `pytest.skip("install X in this interpreter to run, see docs/setup.md")` is accepted. Same for `xfail`, `skipIf`, and conditional bypass `return`s.

Drafted rules 15 and 16 from the v1.4.0 proposal collapsed into rule 12; the original draft's rule 17 became rule 15 in the final numbering. Contiguous numbering preserved per negotiation.

### Changed -- three rule tightenings (#50)

- Rule 7: necessary condition added that tests must import the module they claim to test. A test that re-implements the production algorithm in the test body is theater regardless of what it asserts.
- Rule 10: cross-references `[rule:verify-before-execute]` for the broader claim-grounding discipline that covers prose claims in PR bodies, commit messages, and agent-to-agent messages. Rule 10 keeps its named hook for symbol existence (the `create_presentation_from_data` failure); the broader discipline lives in verify-before-execute.
- Rule 11: gate moved from "before patching" to "before declaring a fix complete." The Paragraph-escape three-round failure happened because the original phrasing let the agent fix one site, declare done, and only grep when the reviewer pushed back.

### Added -- `_environment-preflight-rules.md` always-on sibling (#50)

New always-on rule prescribing a one-time-per-repo inventory: README environment section, interpreters and core deps, shell environment (with `ZSH_FORCE_FULL_INIT=1` if applicable), local services, credentials, CI-vs-local parity. Rule 12 (no hypothetical code) is the per-action application of the inventory this rule establishes.

### Changed -- verify-before-execute claim-grounding clause (#50)

`_verify-before-execute-rules.md` gains an explicit clause that the same-turn evidence requirement covers prose claims in chat to the operator, in PR bodies, in commit messages, and in agent-to-agent messages. Resolves the rule 10 vs verify-before-execute overlap per option (a) of the negotiation: rule 10 keeps its named hook, the broader discipline is documented once in verify-before-execute.

### Negotiation transcript

Wording on all four substantive asks (rule 12 target-environment definition, rule 13 same-turn-grep enforcement, rule 14 tooling-deferred enforcement, contiguous numbering) and the rule 10 conflict resolution was confirmed verbatim by parent session 260502-vital-channel across two `send_agent_message` rounds before merge. Operator delegated full negotiation authority with explicit "prefer prevention over cure" framing, which weighted toward stronger wording on every call.

### No breaking changes

Additive (four new rules) plus tightenings to existing rules. No rule weakened or removed; no skill contract changed. Downstream consumers can pin to `v1.5.0-flat` or `v1.5.0-nested` without code changes.

### Follow-ups

- `#51` Public-surface differ tooling for rule 14 (operator-judgment until tooling lands)
- detect-ai-fingerprints scanner enhancement: rule-7 grep for test files importing their module under test (needs project-namespace-detection design)
- detect-ai-fingerprints scanner enhancement: separate `--pr-body` mode that allows bullets and headers per rule 5's PR-body carve-out (current `--message-file` mode is too strict for PR bodies)

## [1.4.1] -- 2026-05-12

Fixes a shipping bug in v1.4.0 where the scanner from `[skill:detect-ai-fingerprints]` would trip `unbound variable` on bash 3.2 (macOS default) when called without `--ignore`. The production gates (`[skill:commit]` step 3 and `[skill:code-review]` pre-flight) call the scanner without `--ignore`, so on a macOS workspace the gate would die before reporting any real violation. Discovered immediately after tagging v1.4.0; superseded.

### Fixed -- defensive expansion for empty IGNORE_GLOBS (#48)

`is_ignored()` in `scan.sh` now checks `(( ${#IGNORE_GLOBS[@]} == 0 ))` before iterating. Bash 3.2 with `set -u` treats an empty array's `${arr[@]}` expansion as unbound; bash 4+ does not, which is why the bug evaded smoke tests on the development machine. The smoke tests themselves were the second mistake: they all used `--ignore` to suppress self-detection (since the scanner reports its own definition files by design), so the no-`--ignore` codepath was never exercised before release.

Lesson logged to `LESSONS.md`: smoke tests must include the production-default invocation, not just the developer-debug invocation.

## [1.4.0] -- 2026-05-12

Adds `[skill:detect-ai-fingerprints]`, a mechanical scanner for stylistic rules 1-6 of `[rule:no-ai-fingerprints]`. Wired into `[skill:commit]` step 3 (pre-review gate) and `[skill:code-review]` start.

### Added -- detect-ai-fingerprints scanner (#46)

The scanner lives at `skills/meta/detect-ai-fingerprints/scan.sh`. Inputs: staged diff (default), working-tree diff (`--working`), GitHub PR diff (`--pr <n>`), commit/PR message text (`--message <text>`), or message file (`--message-file <path>`). Output: `file:line:rule-id` violations and a 0/1 exit code.

Catches rules 1, 2, 4, 5, 6 mechanically. Rule 3 (multi-paragraph docstrings on internal helpers) cannot be done mechanically without distinguishing public from internal API. Rules 7-11 are judgment-bound and stay in `[skill:code-review]`.

The scanner has no `[fingerprint-skip]` override. The narrow `--ignore <glob>` flag exists for ad-hoc inspection and for the bootstrap commit landing changes to the scanner; production gates do not pass it.

### Changed -- commit step 3 calls the scanner before code-review (#46)

`skills/git-workflow/commit/SKILL.md` step 3 invokes `[skill:detect-ai-fingerprints]` first. Non-zero exit blocks the commit; the scanner has no override. `[skill:code-review]` runs second for the structural rules and the six-layer methodology. The `[review-skip]` override applies only to code-review, not to the scanner.

### Changed -- code-review runs scanner as mechanical pre-flight (#46)

`skills/coding/code-review/SKILL.md` adds a "Mechanical pre-flight (run first)" section. Scanner findings prefix the six-layer human review so reviewer attention is not wasted on em-dash hunting.

### No breaking changes

Additive. Existing behaviour preserved; new scanner is invoked by callers but does not change their contracts.

## [1.3.0] -- 2026-05-12

Adds eleven mandatory always-on rules guarding against AI fingerprints in code, comments, commit messages, PR bodies, and chat output. From a hostile review of siege_utilities work that surfaced concrete failure modes, six stylistic and five structural.

### Added -- `_no-ai-fingerprints-rules.md` (#43)

The eleven rules at `skills/_no-ai-fingerprints-rules.md`:

1. No em-dashes (U+2014) anywhere; use `--`, a comma, or a period.
2. No "Why:" / "How to apply:" structured blocks in code comments or commit messages (carve-out for memory ledgers, skill files, rule files where structured rationale is the documented format).
3. Default to no docstring or a one-liner; multi-paragraph docstrings reserved for public API.
4. Strip self-justifying adverbs ("deliberately," "intentionally," "explicitly," "fundamentally," "essentially," "crucially," "notably").
5. Commit messages are subject + plain-prose body; no bullets, no headers, no diff narration; length determined by what the why requires.
6. No PR / sprint / issue references in code comments; `git log` is the history layer.
7. Tests must fail if production behaviour breaks ("if I reverted the implementation, would this test go red?").
8. No cargo-culted patterns across modules; each target gets tests for its actual public surface.
9. No speculative abstractions; introduce a fixture or base class only when a second caller exists.
10. Verify before asserting any method, class, attribute, flag, or behaviour; open the file and grep the symbol.
11. Grep before patching, not after; scope of a bug is wider than the diff that surfaced it.

The rules are mandatory. There is no `[fingerprint-skip]` override. The closest thing is the rule-2 carve-out for documentation formats.

### Negotiated changes during PR review

Rule 5 as originally proposed capped commit body at two sentences. The cap was rejected after counter-proposal: it would have banned legitimate multi-paragraph commit bodies in non-AI engineering practice (Linus, Postgres, Kubernetes maintainers). Replaced with structural ban (no bullets, no headers, no self-justifying adverbs, no diff narration) plus length-determined-by-what-the-why-requires guidance. Counter-proposal accepted by parent session before merge.

Rule 10 trigger tightened: "before writing code, a test, or documentation that names a method, class, attribute, flag, or behaviour."

### Changed -- commit skill aligned with rule 5 (#43)

`skills/git-workflow/commit/SKILL.md` Body section rewritten as plain-prose guidance: no bullets, no headers, no self-justifying adverbs, no diff narration. Length determined by what the why genuinely requires.

### Changed -- self-consistency sweep on rule files and root docs (#43)

Em-dashes removed from all `_*-rules.md` files plus `CONTRIBUTING.md`, `CHANGELOG.md`, `README.md`, and `LESSONS.md`. Banned adverbs (rule 4) removed from the same set, except where rule 4 itself lists them as quoted examples. Skill-tree sweep (~100 `SKILL.md` files) deferred to a follow-up PR.

### No breaking changes

The rules are new always-on additions. The commit-skill Body section change tightens existing guidance without changing the skill's contract.

## [1.2.1] -- 2026-05-12

Tightens `[rule:verify-before-execute]` by requiring a same-conversation `[skill:think]` reference for non-trivial actions.

### Changed -- verify block requires Design line for non-trivial actions (#37)

The verification block gains a fourth line:

```
- **Design:** <for non-trivial actions -- same-conversation [skill:think] reference>
```

Triggers and exemptions are quoted from `[skill:think]`'s "When This Skill Applies" section verbatim -- same triggers (new feature, refactor, architecture change, schema change, >3 files, non-obvious approach) and same exemptions (single-line fix, step-by-step user instructions, doc-only edit, git op). Cross-referencing rather than paraphrasing prevents drift.

The constraint is "same-conversation," mirroring Evidence's "same-response." Designs go stale across conversation boundaries -- a design from a prior session does not satisfy the Design line.

Worked examples updated; two anti-patterns added (skipping Design with "it's straightforward"; treating a prior session's design as current). Relationship-to-other-rules section pairs think with verify explicitly.

## [1.2.0] -- 2026-05-12

Adds the `verify-before-execute` always-on rule: every side-effecting action must be preceded by a visible verification block grounded in same-turn evidence. Addresses the recurring observation that agents take actions without first investigating the actual state.

### Added -- `_verify-before-execute-rules.md` (#35)

New always-on rule that requires a visible verification block before any `Write`, `Edit`, `NotebookEdit`, side-effecting `Bash`, commit, push, delete, or deploy:

```
**Verify-before-execute**
- **Standards:** <which rules/skills/checklists apply>
- **Intent:** <one sentence linking goal to this specific change>
- **Evidence:** <for corrections only -- observed failure + same-turn tool call>
```

The strongest constraint: for corrections, the Evidence line must reference a tool call from the **same response**, not a prior turn or memory. Files change between turns; treating prior-turn knowledge as current-turn evidence is the primary failure mode this rule addresses.

The block is mandatory. The single override is `[verify-skip: <reason>]` and is itself a flag for retrospective review.

The rule includes worked examples (correction with same-turn evidence, feature with omitted Evidence line, trivial action with override) and an anti-pattern catalog covering "editing a file without reading," "claiming a test passes without running it," "retrying a failed command in hope," and "treating prior-turn reads as current evidence."

### Changed -- commit skill wires the rule (#35)

`skills/git-workflow/commit/SKILL.md` adds step 0 (verify-before-execute block before any other check) and a checklist row. Other skills (code-review, create-pr) intentionally not wired yet -- observe whether the commit-skill wiring catches the failure mode in practice before broadening.

### No breaking changes

Additive only. Existing skills retain their behavior; the new rule loads always-on but is enforced by judgment (no CI/lint check on block format yet -- kept as a possible follow-up if the discipline doesn't hold).

## [1.1.0] -- 2026-05-08

Adds the lessons-learned rules pipeline: a three-tier system that turns recurring code-review findings, CodeRabbit threads, and incident lessons into durable, evidence-backed rules. Also tightens the Definition of Done by running code-review at commit time, not just at PR-open.

### Added -- Pre-commit code-review gate (#29)

Operationalizes Definition of Done criterion (a) at the pre-commit transition. Every commit invokes `[skill:code-review]` against the staged diff. Blockers stop the commit; Majors must be fixed in the same commit or deferred to a follow-up ticket. A `[review-skip]` override exists for documented exceptions, mirroring `[no-ticket]` and `[direct-commit]`.

The pre-PR review (in `[skill:create-pr]`) still runs as a second pass over the cumulative diff. The two reviews are complementary: pre-commit catches findings while context is fresh; pre-PR catches drift across multiple commits.

- `skills/git-workflow/commit/SKILL.md` -- new step 3 + Pre-review gate section + checklist row
- `skills/_definition-of-done-rules.md` -- criterion (a) names both transitions; transitions table updated

### Added -- Lessons-learned rules pipeline (#31, #33)

Three-tier system for capturing, distilling, and curating durable rules:

| Tier | Lives in | Owned by | Promotion gate |
|---|---|---|---|
| 1 -- Ledger | `<repo>/LESSONS.md` | `[skill:lessons-learned]` | recurrence ≥ 3, or 1 production incident, or Critical-severity → Tier 2 |
| 2 -- Project rules | `<repo>/.claude/rules/<topic>.md` | `[skill:distill-lessons]` | appears in 2+ projects, or is language/framework-level → Tier 3 |
| 3 -- Org rules (this repo) | `claude-configs-public/skills/_*-rules.md` | Human PR with cited evidence | (top of pipeline) |

**New skills:**
- `skills/meta/lessons-learned/` (+ `template/LESSONS.md`) -- Tier-1 capture. Three discipline rules: every entry has a link, rules-not-advice, recurrence counter not duplicates.
- `skills/meta/distill-lessons/` -- Tier-1 → Tier-2 promotion. One rule at a time, with a conflict gate (refuses to write a contradictory rule) and human wording confirmation.
- `skills/meta/rules-audit/` -- cross-tier hygiene pass. Four phases: Tier-1 hygiene, Tier-2 hygiene, cross-tier (Tier-2 → Tier-3 candidates, conflicts with newer evidence, stale upstream rules), coverage. Surface-only, never auto-acts.

**Integration:**
- `skills/coding/code-review/SKILL.md` -- loads project `.claude/rules/*.md` at the start of every review; logs recurring findings via `[skill:lessons-learned]` at the end.
- `skills/session/coderabbit-response/SKILL.md` -- new step 8: feed the ledger for recurring CR findings.
- `skills/session/pr-comments/SKILL.md` -- new workflow step: feed the ledger for recurring human-reviewer flags.
- `skills/session/wrap-up/SKILL.md` -- sweeps for ledger entries before the CLAUDE.md update; checks rules-audit cadence and nudges (non-blocking) if >60 days since last audit; clarifies CLAUDE.md = session-scoped, LESSONS.md = durable.

### Added -- Tier-3 PR requirements documented (#33)

`CONTRIBUTING.md` now has a "How rules get promoted into this repo" section. Adding or amending a rule in any `_*-rules.md` requires citing ≥2 Tier-2 projects (or 1 + language/framework justification), listing the originating Tier-1 evidence, and passing the conflict gate. PRs without cited evidence are asked to gather evidence first or downgrade to discussion issues.

### No breaking changes

All additions and additive integrations. Existing skills retain their behavior; new behavior is opt-in via the new skills. Downstream consumers can pin to `v1.1.0-nested` or `v1.1.0-flat` once published.

## [1.0.0] -- 2026-05-07

Major release. Decouples skill identity from filesystem layout; one source serves Claude Code (resolver hook) and Craft Agent (slash-command pane) via a build step.

### Added -- Dual-layout build (slug-token references)

Decouples skill identity (slug) from filesystem layout. Cross-references between skills now use `[skill:<slug>]` and `[rule:<slug>]` tokens; the build expands them to layout-appropriate paths.

- `bin/build.py` -- produces `dist/nested/` (mirrors source for Claude Code with the resolver hook) and `dist/flat/` (leaf skills at `skills/<slug>/` for Craft Agent's pane). Token resolution + RESOLVER generation per layout.
- `bin/sync-skill-references.py` -- mechanical converter from path-form to token-form Markdown links. Used for the one-time migration; CI runs it in `--check` mode to enforce token form on every PR.
- `skills/RESOLVER.template.md` -- slug-token version of the resolver. Build emits per-layout RESOLVER.md from this template.
- `.github/workflows/build-and-publish.yml` -- validate references on every PR; build and publish to `release/nested` and `release/flat` on every push to main; tag fan-out (`vX.Y.Z` → `vX.Y.Z-nested` + `vX.Y.Z-flat`) on tag push.
- `CONTRIBUTING.md` -- slug-token convention, contributor workflow, build commands, downstream consumer instructions.

### Changed -- `RESOLVER.md` is now a build artifact

`skills/RESOLVER.md` removed from source; replaced by `skills/RESOLVER.template.md`. The build generates `RESOLVER.md` per layout with paths appropriate to that layout. Hand-editing the resolver now means editing the template.

### Changed -- Cross-references converted to tokens (mechanical)

249 skill cross-references and 39 rule cross-references across 46 SKILL.md and `_*-rules.md` files converted from path-form Markdown links to `[skill:slug]` / `[rule:slug]` tokens. No content change beyond link form. Going forward, contributors use tokens; CI catches path-form references that slip in by habit.

### Breaking -- pin to a release-branch tag, not the source tag

`main` now contains build infrastructure (tokens unresolved). Downstream consumers should pin to `v1.0.0-nested` or `v1.0.0-flat` (release-branch tags), not `v1.0.0` (source tag). See [Distribution layouts](README.md#distribution-layouts).

This is a breaking change to the consumption pattern; existing v0.x consumers pulling from `main` need to update their subtree pull command. The skills themselves are unchanged.

## [0.3.0] -- 2026-05-06

Adds the Definition of Done as an always-on rule with hard enforcement, and makes `pre-work-check` and `think` slash-invokable to match their README classifications.

### Added -- Definition of Done (`_definition-of-done-rules.md`)

New always-on rule file `skills/_definition-of-done-rules.md`, sibling of `_principles-rules.md` and `_output-rules.md`. Five hard criteria for "done":

- **(a) Code-reviewed** -- every behavior change goes through review
- **(b) Edge cases explored** -- concrete checklist (empty / boundary / duplicate / out-of-order / very-small / very-large / mixed-types / partial-failure / null / identifier-collision)
- **(c) Tests written** -- mandatory; no test infrastructure means add it first; PRs without tests must justify in description
- **(d) Non-trivial updates → update the ticket** -- status, comments, links, final summary
- **(e) Work has a ticket** -- every behavior change starts from one

Hard enforcement, not recommendations. Soft rules erode; these are documented responses to specific Siege incidents.

Cross-referenced from:
- `skills/coding/SKILL.md` Rule 6 (one-line reference)
- `skills/coding/python/SKILL.md` "Tests and Documentation" section (paragraph reference)
- `skills/coding/code-review/SKILL.md` §1 (edge-case checklist promoted from one bullet to 9-item explicit checklist)
- `skills/git-workflow/create-pr/SKILL.md` ("Definition of Done gate (mandatory)" subsection -- failed criteria → PR opens as draft)
- `skills/session/wrap-up/SKILL.md` (Step 0 verification ahead of commit/cleanup)

Registered in `skills/RESOLVER.md` Conventions table.

### Changed -- `pre-work-check` and `think` are slash-invokable

Both skills already classified as user-invokable in README (Action / Analytical). Frontmatter brought into line:

- `skills/planning/pre-work-check/SKILL.md` -- `disable-model-invocation: true` added; now slash-invokable as `/pre-work-check`
- `skills/thinking/think/SKILL.md` -- `disable-model-invocation: true` added; now slash-invokable as `/think`

Resolver-driven enforcement is unchanged. Both skills remain auto-applied gates via the resolver hook; the change adds manual invocation as an option.

### Documentation

- `README.md` -- adds `_definition-of-done-rules.md` to Always-on conventions table; new "Definition of Done" section explaining the five criteria and PR/wrap-up gating

## [0.2.0] -- 2026-05-02

## [0.2.0] -- 2026-05-02

Spatial skill overhaul -- adds the four-engine spatial skill set (PostGIS / GeoPandas / Sedona / DuckDB-spatial), the universal cross-engine principles, two book distillations (Mastering PostGIS, Geographic Data Science with Python), and substantially expanded spatial-statistics coverage.

### Added -- Spatial skill set (`feat/spatial-skill-overhaul`)

A four-engine spatial skill set with capability-tier dispatch. Replaces the generic "spatial" decision skill with per-engine operational skills plus an augmented router.

**New skills:**

- **`skills/coding/geopandas/`** -- GeoPandas + folded Shapely for single-node Python spatial work. Has explicit no-GDAL fallbacks for `geo-lite` environments.
- **`skills/coding/sedona/`** -- Apache Sedona for distributed spatial work on Spark. One skill for both PySpark and Scala scaffolding (the spatial logic is identical). Includes raster.
- **`skills/coding/duckdb-spatial/`** -- DuckDB's spatial extension as the no-server / no-GDAL path. Bundles GEOS / GDAL / PROJ in a single binary; the strongest single tool for GDAL-less environments (Lambda, slim images, locked-down envs).

**Augmented:**

- **`skills/coding/postgis/`** -- added 9 reference files (Mastering PostGIS distillation, indexing strategies, geometry vs geography, spatial joins performance, query optimization, topology, vacuuming and bloat, pitfalls, SU-PostGIS interop map). Existing SKILL.md preserved; new "Companion shelves and references" section links them.
- **`skills/analysis/spatial/SKILL.md`** -- augmented as the load-bearing engine-selection router. Three axes: data scale × GDAL availability × workload pattern. Existing 6-step decision framework preserved; new "Always start with: capability detection" prelude calls `siege_utilities.geo.capabilities.geo_capabilities()`. Six new reference files: engine-selection, gdal-availability-matrix, crs-decision-tree, siege-utilities-spatial, capability-tiers, spatial-statistics.

**siege_utilities integration:**

Each engine has a dedicated `siege-utilities-<engine>.md` reference describing what SU obviates and what's still bring-your-own. Cross-engine consolidated map at `skills/analysis/spatial/references/siege-utilities-spatial.md`.

**Resolver registrations:**

- `skills/RESOLVER.md` Coding section: rows for `geopandas`, `sedona`, `duckdb-spatial` (PostGIS row already existed)
- `skills/RESOLVER.md` Analysis section: spatial row reframed to emphasize router's dispatch role
- `RESOLVER.md` (top-level) Writing-code section: row pointing at `analysis/spatial/SKILL.md` as the entry for any spatial work

### Added -- Universal cross-engine spatial principles

`skills/analysis/spatial/references/principles/` -- 6 files articulating the spatial principles that translate across all four engines (PostGIS, GeoPandas, Sedona, DuckDB-spatial). Distinct from the engine-faithful Mastering PostGIS distillation (which is PostgreSQL-specific). Each principle file shows the principle, why it's universal, and per-engine implementation:

- `index.md` -- meta-index + reading order
- `crs-is-meaning.md` -- SRID as semantic layer; project before measuring
- `validate-on-ingest.md` -- repair geometry at the boundary; never silently drop
- `bbox-pre-filter.md` -- every fast spatial op = bbox pre-filter + exact predicate
- `subdivide-complex-polygons.md` -- universal 10-100× speedup; per-engine recipes
- `spatial-indexing-discipline.md` -- every spatial column gets a spatial index, always
- `name-by-srid.md` -- column-naming convention that makes CRS bugs surface at schema-validation time (load-bearing for engines without per-row CRS storage)

### Updated -- Mastering PostGIS chapters 3-9 added

Following Ch 1-2 in the previous commit, Ch 3 (vector operations), 4 (raster), 5 (exporting), 6 (ETL), 7 (PL/pgSQL programming), 8 (web backends -- `pg_tileserv` / `pg_featureserv` / MVT), 9 (pgRouting). Each is principle-level distillation with cross-links to topic refs and per-engine notes where principles transfer.

### Updated -- Topology framing reversed

`skills/coding/postgis/references/topology.md` was framed as "rarely the right tool." Reframed to **option C (pragmatic with use cases)** centered on the load-bearing Siege use case: **point-derived boundaries** (Voronoi tessellation, alpha-shape concave hulls, kernel-density contours, regionalization output). When you produce boundaries from points, shared-edge integrity matters and topology earns its operational complexity. Concrete worked example for Voronoi + topology pipeline. Cross-engine note: topology is PostGIS-specific; other engines reconstruct meshes per operation.

### Added -- *Geographic Data Science with Python* distillation + 5 topic refs

Distillation of [GDSPy](https://geographicdata.science/book/intro.html) (Rey, Arribas-Bel, Wolf, 2023; CC-BY-NC-ND online edition) -- the canonical modern textbook for spatial analysis on top of GeoPandas + the PySAL ecosystem. Companion to the Mastering PostGIS distillation: GDSPy is methodology-faithful (engine-agnostic math); Mastering PostGIS is engine-faithful (PostgreSQL idioms).

- `analysis/spatial/references/geographic-data-science-distilled.md` -- book intro, chapter map, currency caveat, citation
- `analysis/spatial/references/spatial-weights.md` -- the W matrix in depth; kernel/KNN/distance-band/hybrid; standardization; sensitivity (was under-weighted in `spatial-statistics.md`)
- `analysis/spatial/references/regionalization.md` -- constrained spatial clustering (max-p / SKATER / AZP); redistricting algorithms; compactness measures (Polsby-Popper, Schwartzberg, Reock); pointers to `gerrychain`
- `analysis/spatial/references/spatial-inequality.md` -- Gini, Theil, Atkinson; **Theil decomposition into between-region vs within-region inequality**; Lorenz curves
- `analysis/spatial/references/spatial-feature-engineering.md` -- neighbor-aggregate features, distance-to features, density features; **spatial cross-validation as non-negotiable** (random K-fold leaks signal across spatially-adjacent rows)
- `analysis/spatial/references/point-pattern-analysis.md` -- Ripley's K, L, G, F, J functions; KDE; CSR tests; cross-K for two-pattern association (reverses earlier "out of scope" call)

### Added -- Mastering PostGIS book-skill folder structure

`skills/coding/postgis/references/mastering-postgis-distilled.md` (single file) promoted to `skills/coding/postgis/references/mastering-postgis/` (folder with chapter-themed reference files mirroring the book's TOC). `index.md` carries the meta-index, currency caveats, and citation; chapter files are added incrementally (Ch 1 + Ch 2 done in this PR, Ch 3-9 deferred to a follow-up).

### Updated -- siege-utilities-duckdb-spatial.md

Added the 4th per-engine SU interop map for symmetry with the other three engines. Documents SU's currently-thin DuckDB integration (format conversion only) and the SU-1 / SU-7 / SU-9 upstream PR candidates that would close most inline-SQL gaps.

### Updated -- Sedona scaffolding rebalanced toward PySpark

Sedona content was equal-weighted between PySpark and Scala; rebalanced to **PySpark as the default scaffolding** since most Siege Sedona work is Python. Scala variant moved to a single dedicated reference file (`scaffolding-python-vs-scala.md`).

### Updated -- spatial-statistics.md expanded

Was ~250 lines; now ~580 lines with hotspot analysis substantially expanded (methodological choices, multiple-testing correction, edge effects), plus new use cases: empirical Bayes rate smoothing, segregation indices, 2SFCA accessibility. Per-engine implementation matrix for 11 methods. Cross-links to the new GDSPy-derived references above.

### Documentation

- `README.md` -- updated Router Skills table to reflect actual sub-skills; added Always-on conventions section listing all `_*-rules.md` files; added Spatial skills section with per-engine table; added Releases & versioning section; corrected stale Reference Skills entries; added pre-work-check / qml-component-review / infrastructure/ops to skill tables; added `siege_utilities` first-class section.

## [0.1.0] -- 2026-05-02

First tagged release. Marks the inaugural stable surface of `claude-configs-public` as a usable, reusable Claude Code skill catalog with the **DBrain** book-skill library, an always-on rules system, and the resolver-gated discovery layer.

### Added -- DBrain book-skill library (`skills/shelves/`)

A book-derived skill library integrated and adapted from two MIT-licensed upstream skill libraries -- [ZLStas/skills](https://github.com/ZLStas/skills) and [wondelai/skills](https://github.com/wondelai/skills) -- organized into 11 topic shelves:

- `engineering-principles/` -- Clean Code, Clean Architecture, Design Patterns, Domain-Driven Design, Refactoring Patterns, Pragmatic Programmer, Software Design Philosophy
- `systems-architecture/` -- Designing Data-Intensive Applications, System Design, Microservices Patterns, Release It!, High-Performance Browser Networking, System Design Interview
- `languages/` -- Effective Python / Java / Kotlin / TypeScript, Kotlin in Action, Spring Boot in Action, Programming Rust, Rust in Action, Using Asyncio in Python, Web Scraping with Python
- `data-and-pipelines/` -- Data Pipelines Pocket Reference (Densmore)
- `product/` -- Jobs to Be Done, Continuous Discovery, Design Sprint, Lean Startup, Lean UX, Inspired, The Mom Test, Improve Retention
- `marketing/` -- CRO, StoryBrand, Contagious, Made to Stick, Scorecard / One-Page Marketing, Hooked
- `sales/` -- Predictable Revenue, Negotiation, Influence, $100M Offers
- `strategy/` -- Blue Ocean, Crossing the Chasm, Traction (EOS), Obviously Awesome
- `design/` -- Refactoring UI, iOS HIG, UX Heuristics, Web Typography, Top, Don't Make Me Think, Microinteractions
- `team/` -- Drive (Pink), the 37signals Way
- `storytelling/` -- Storytelling with Data, Animation at Work

Inspired by [GBrain](https://github.com/garrytan/gbrain). 53 unique book skills, each with an attribution footer pinning the upstream commit.

### Added -- Always-on rules

Sibling files of `_output-rules.md` and `_data-trust-rules.md`, registered in the resolver Conventions table:

- `_principles-rules.md` -- Clean Code maxims (always-on for any code task)
- `_python-rules.md` -- Effective Python idioms
- `_jvm-rules.md` -- Effective Java + Effective Kotlin (merged), applied for Java / Kotlin / Scala-on-Spark
- `_typescript-rules.md` -- Effective TypeScript idioms
- `_rust-rules.md` -- Rust idioms
- `_siege-utilities-rules.md` -- workspace-wide preference for [`siege_utilities`](https://github.com/siege-analytics/siege_utilities) before writing local helpers; consider upstream PRs when the gap is generic

### Added -- New skills

- `coding/scala-on-spark/` -- thin delegating skill that fires for `.scala` / `%scala` / `Dataset[T]` work and chains `coding/spark/` + `shelves/languages/effective-java/` + `shelves/languages/effective-kotlin/` + `shelves/systems-architecture/data-intensive/`.
- `coding/qml-component-review/` -- QML component decomposition, properties-in / signals-out discipline, MuseScore plugin work.
- `infrastructure/ops/` -- guardrails for shared infrastructure (cyberpower UPS, K8s pod limits, Rundeck concurrency).

### Added -- Companion-shelves delegation in existing coding skills

Inserted "Companion shelves" sections into `coding/python`, `coding/python-patterns`, `coding/python-exceptions`, `coding/code-review`, `coding/sql`, `coding/spark`, `coding/django`, `coding/postgis`, `coding/pipeline-jobs`. Each block points the agent to the relevant book skills in `shelves/` for principle-level rationale alongside the project-specific skill content.

### Added -- Resolver registrations

- `skills/RESOLVER.md` Conventions table now lists all `_*-rules.md` files (DBrain rules + siege_utilities rule).
- `skills/RESOLVER.md` Coding section gains rows for `scala-on-spark` and `qml-component-review`.
- `skills/RESOLVER.md` Planning section gains row for `pre-work-check`.
- `skills/RESOLVER.md` Infrastructure section gains row for `infrastructure/ops`.
- `skills/RESOLVER.md` new "Shelves (book-derived libraries)" section dispatches to each of the 11 shelves.
- Top-level `RESOLVER.md` Writing-code section gains rows for Scala on Spark, service-boundary design, storage-engine selection, and Python utility helpers (siege_utilities-first).

### Added -- `LICENSE` (MIT)

First explicit license file. Matches both upstream sources.

### Added -- `THIRD_PARTY_NOTICES.md`

Full attribution for upstream MIT-licensed skill libraries with commit pins and the per-book mapping.

### Fixed

- `skills/analysis/SKILL.md` -- restored data-trust framing as the first question of the analysis router. Spatial / entity-resolution / graph methods exist *because* tabular identifiers are dirty; opening the router with "do you actually need geometry?" inverted that premise. Also added Rule 5 making `_data-trust-rules.md` an always-on convention rather than documentation.
- `skills/coding/python/SKILL.md` -- restored "Tests and Documentation -- non-negotiable" section. The only place in the skills tree making tests + docs a hard merge gate at the language level.
- `skills/coding/SKILL.md` -- restored Rule 5 (`_output-rules.md` discovery path), Rule 6 (language-agnostic tests-and-docs policy), and the `python-patterns` / `python-exceptions` reviewer-lens gotcha.

### Documentation

- `README.md` -- DBrain section, shelf overview table, Credits, GBrain attribution, MIT license note.
- This `CHANGELOG.md`.

[Unreleased]: https://github.com/siege-analytics/claude-configs-public/compare/v2.0.1...HEAD
[2.0.1]: https://github.com/siege-analytics/claude-configs-public/releases/tag/v2.0.1
[2.0.0]: https://github.com/siege-analytics/claude-configs-public/releases/tag/v2.0.0
[1.6.1]: https://github.com/siege-analytics/claude-configs-public/releases/tag/v1.6.1
[1.6.0]: https://github.com/siege-analytics/claude-configs-public/releases/tag/v1.6.0
[1.5.0]: https://github.com/siege-analytics/claude-configs-public/releases/tag/v1.5.0
[1.4.1]: https://github.com/siege-analytics/claude-configs-public/releases/tag/v1.4.1
[1.4.0]: https://github.com/siege-analytics/claude-configs-public/releases/tag/v1.4.0
[1.3.0]: https://github.com/siege-analytics/claude-configs-public/releases/tag/v1.3.0
[1.2.1]: https://github.com/siege-analytics/claude-configs-public/releases/tag/v1.2.1
[1.2.0]: https://github.com/siege-analytics/claude-configs-public/releases/tag/v1.2.0
[1.1.0]: https://github.com/siege-analytics/claude-configs-public/releases/tag/v1.1.0
[1.0.0]: https://github.com/siege-analytics/claude-configs-public/releases/tag/v1.0.0
[0.3.0]: https://github.com/siege-analytics/claude-configs-public/releases/tag/v0.3.0
[0.2.0]: https://github.com/siege-analytics/claude-configs-public/releases/tag/v0.2.0
[0.1.0]: https://github.com/siege-analytics/claude-configs-public/releases/tag/v0.1.0
