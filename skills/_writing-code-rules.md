---
description: Always-on. Code-authoring discipline. Docstring brevity, no history references in code comments, no speculative abstractions, verify symbols exist before naming them, verify dependencies are reachable before writing code that uses them, doc-edit symmetry, no silent error swallowing. Test-writing rules live in `_writing-tests-rules.md`; claim-grounding (commit/PR-body claims) lives in `_writing-claims-rules.md`.
---

# Writing Code

These rules apply whenever the agent writes production code -- any `.py` file outside `tests/`, plus the comments and docstrings that live in those files. The unifying boundary is "verify before touching code": the rules fire at code-edit time, not at claim time.

The sibling boundary in `_writing-claims-rules.md` is "verify before claiming": rules that fire when stating a fact in a commit body, PR body, or chat. The two files split the same underlying claim-grounding family by temporal trigger; consult writing-code when editing code, consult writing-claims when stating facts.

## The ten code-writing rules

**writing-code:1. Default to no docstring or a one-liner.** Multi-paragraph Sphinx-style docstrings are reserved for public API surface that is exported and consumed externally. Internal helpers and one-off functions get type hints and at most one sentence. Docstrings are code, not prose; the discipline lives here rather than in `[`writing-prose`](_writing-prose-rules.md)`.

**writing-code:2. No PR / sprint / issue references inside code comments.** "Sprint A item 2," "the v3.15.0 hardening," "PR #443 follow-up" all rot the moment the codebase moves. Reference behaviour, not history. The git log is the history layer; the ticket tracker is the planning layer; code comments are the behaviour layer. This rule applies specifically to code comments; commit-message footers and PR descriptions can and should reference tickets via `Refs:` / `Closes:` trailers per `[`commit`](commit/SKILL.md)`.

**writing-code:3. No speculative abstractions.** Helpers, base classes, and configuration scaffolding are introduced only when a second caller already exists. "Future-proofing" without a second caller is dead weight. Revisit when the second caller arrives, not before.

This rule applies primarily to production code (helpers, base classes). When the failure mode is "test fixtures introduced for one test that will hypothetically have a second caller someday," see `[`writing-tests`](_writing-tests-rules.md)` writing-tests:2 for the test-side application.

**writing-code:4. Verify before asserting a symbol exists.** Before writing code, a test, or documentation that names a method, class, attribute, flag, or behaviour: open the file, grep for the symbol, read the actual signature. Production code that calls a non-existent method (the `create_presentation_from_data` failure mode, where the method is `create_analytics_presentation`) and documentation that asserts current behaviour reflecting aspiration (the INVARIANTS identifier-validation claim) are the canonical failures here. If a behaviour is aspirational, label it: `_aspiration, not current behaviour_` or equivalent.

This rule pairs with writing-code:5 below: both have the same shape ("verify Y before writing code that uses Y") and fire at the same trigger time. See `[`verify-before-execute`](_verify-before-execute-rules.md)` for the parent claim-grounding discipline that covers prose claims about the same symbols in PR bodies, commit messages, and agent-to-agent messages.

**writing-code:5. No hypothetical code.** When you write code or a test that depends on a library, service, configuration, or external API, you must have already verified the dependency is reachable in the target environment, and you must exercise the real dependency before claiming the code works. Reachable means reachable in the workspace where the code is being written, in the same session, before the code is written. CI does not count. The PR-body label `untested locally; first run is CI` is a one-time escape hatch when the dependency genuinely cannot be reached locally; using it means the agent has tried and failed, not that the agent did not try. Repeated use of the label is a smell. A mock test that asserts the mock was called is not exercise.

The companion `[`environment-preflight`](_environment-preflight-rules.md)` describes the one-time-per-repo inventory that establishes what is reachable; this rule is the per-action application. The mechanical enforcement is `[`commit`](commit/SKILL.md)` step 4 (the affected-tests gate); the rule itself is in force at write-time, not just at commit-time. Symmetric with writing-code:4: both verify a precondition before code that depends on it.

**writing-code:6. Doc-edit symmetry.** When code edits in a PR touch a public symbol, the file containing the symbol must be re-read in the same PR (which means the symbol's docstring is re-read for free, since they are colocated). Documentation files that reference the touched symbol by name (matched by grep against the doc tree) must either appear in the same PR's changeset OR the PR body must contain a `Docs-checked: <list of doc files grepped, confirmed in sync>` trailer.

The doc tree default: `**/*.md` minus auto-generated paths (`htmlcov/`, `_build/`, `node_modules/`), plus the canonical names regardless of location (`README.md`, `CHANGELOG.md`, `INVARIANTS.md`, `CONTRIBUTING.md`). Per-repo override at `.claude/doc-paths.toml` that takes a glob list. The trailer names which files were grepped so an auditor can verify post-hoc.

The session's worst case: `INVARIANTS.md` kept asserting current behaviour that did not exist because the agent edited the code without going back to the doc. The rule lives in writing-code (not in writing-claims) because it fires at code-edit time; the operator editing code should find it where they look up "what applies when I edit code." See `[`writing-claims`](_writing-claims-rules.md)` for the broader claim-grounding family this rule belongs to by failure-mode shape.

**writing-code:7. Silent error swallowing.** When catching an exception, the handler must do exactly one of:

- Re-raise the same or a wrapped exception.
- Return a typed-failure result that the caller pattern-matches on (Result / Either / Option style, or a project-defined dataclass, or `Optional[T]` when the function signature is `Optional[T]` AND the docstring documents `None` as the failure indicator).
- Perform best-effort cleanup in a `finally` block where the failure does not affect downstream behaviour.
- Audit-log the failure with full context (input that caused it, exception class, exception message) AND return a typed-failure result per the second option.

Patterns banned: bare `except: pass`; `except Exception: log.error(...); return None` where the docstring does not document `None` as failure; `except: continue` in loops without per-iteration audit log; `except Exception: pass  # noqa` without an inline rationale comment naming the specific reason swallowing is correct here.

Forward-only on existing handlers. Existing `Optional[T]`-returning functions get a docstring update grace window of one minor release after writing-code:7 lands; any handler edited after that grace window must comply. New handlers in any PR must comply from day one.

**writing-code:8. Every callsite of an optionally-imported symbol checks the availability flag first.**

When a module declares an optional import via the `try: import X; X_AVAILABLE = True; except ImportError: X_AVAILABLE = False` pattern (or equivalent: `_HAS_X`, `HAS_X`, `X_INSTALLED`, project-defined), every callsite that uses `X` in the same module must be guarded by `if not X_AVAILABLE: <raise|skip|return>` before the call, or be inside a private helper function (leading-underscore name) whose docstring asserts the flag has been checked by the caller. Public callsites must check the flag inline; private helpers can defer to their callers only if the docstring documents the contract.

The guard must produce a clear failure message naming the missing package and the install command: `raise RuntimeError("shapely required; install with: pip install shapely")` not `raise RuntimeError("dependency missing")`. Bare `if not X_AVAILABLE: return None` is acceptable only if the function's documented contract is to be a no-op when the dependency is absent.

Two-line acceptance check at review time: grep for `X_AVAILABLE = False` (or the project's flag name) in the diff; for each module, grep for `X.` usages in that module; every usage outside a guarded block is a violation.

Forward-only. New optional imports must comply; existing modules audited as discovery surfaces them.

The session's concrete instance: both `census_gazetteer.py` and `wikidata_gazetteer.py` had `SHAPELY_AVAILABLE` flags but the geometry-construction callsites used `shapely.geometry.Polygon(...)` without guarding. The first call in an environment without shapely raised `NameError: name 'shapely' is not defined` instead of the intended clear `RuntimeError`. Cross-module re-export case (X re-exported from `__init__.py`, used in sibling module via `from .somemod import X`) is a known scanner gap; the failure mode is loud (immediate NameError) and the pattern is rare. Mechanical detection is high (multi-pass within a file; tracked at upstream issue #57 for v1.6.2); judgment-enforced via `[`code-review`](code-review/SKILL.md)` until the scanner enhancement lands.

**writing-code:9. No silently-dropped parameters.**

When a method or function signature accepts a parameter, the implementation must do exactly one of:

- (a) use the parameter in the body,
- (b) raise `NotImplementedError("<param>=<value> not supported in <ImplName>; see <central-capability-symbol> for support matrix")` when the parameter is non-default. If no central capability registry exists in the project yet, name the supporting impls inline in the message; this creates a follow-on writing-code:10 obligation to extract a registry at the next param-set change,
- (c) document in the docstring of the **base class default** that the implementation is a no-op for that parameter and name which engines honour it. Subclasses that legitimately use the parameter need not repeat the disclaimer; the carve-out is for the abstract-base or default-impl tier where "the parameter is part of the surface but this implementation chooses not to honour it" is the documented contract,
- (d) pass the parameter through to a delegated implementation via `**kwargs` star-arg unpacking or by name.

The session's concrete instance: `load_polygons` and `load_lines` accepted `format: str = "auto"` and `geometry_col: str = "geometry"`; the default implementation called `self.read_spatial(path, crs=crs)` and ignored both. A caller passing `format="shapefile"` to recover from an auto-detection miss had no effect; the override was silently dropped. API lie: the signature claimed the parameter mattered; the implementation said otherwise.

Parameters consumed by a decorator (e.g. introspected by `@validate_args` or similar) are a judgment-enforced carve-out the AST scanner cannot see. Reviewer attests in the PR body that decorator-side consumption accounts for the apparent unused parameter. The scanner consults `.claude/scanner-config.toml` if present for a project-specific decorator allow-list; default allow-list is `{functools.wraps, contextlib.contextmanager, classmethod, staticmethod, property}`.

Mechanical via AST walk in `[`detect-ai-fingerprints`](detect-ai-fingerprints/SKILL.md)`: collect signature args (name, default), collect `Name` and `keyword` references in body, flag args with non-`None` defaults that are neither referenced by name nor forwarded via `**kwargs`. Carve-out for decorator-consumed parameters via the allow-list above.

**writing-code:10. Capability declarations match implementations.**

When a module exposes a central "supported X" registry (a frozenset, dict, class attribute, or module-level constant) that a validator consumes, every implementation the validator gates access to must support every item in the registry. Mismatches mean the validator passes input the implementation will reject at runtime with a confusing error.

The session's concrete instance: `_SUPPORTED_AGG_NAMES` at line 68 of `dataframe_engine.py` is a frozenset of agg names the validator accepts. The pandas implementation does not implement `approx_count_distinct` (a member of the registry). A pandas caller passing `agg={"col": "approx_count_distinct"}` passes validation, then dies inside the pandas impl with `AttributeError`. The error is misleading because the validator already attested support.

This is the sibling rule of writing-code:9. writing-code:9 fires per-method-signature at function-definition review time; writing-code:10 fires at architecture review when a central registry's shape is examined against each consumer. Different scanners would catch each: writing-code:9 is one-pass AST per function; writing-code:10 needs cross-implementation tracing (validator to registry to consumers) that requires symbolic execution or extensive AST graph-building, infeasible at scanner tier. Judgment-enforced via `[`code-review`](code-review/SKILL.md)`; coverage matrix marks `prevention_path` accordingly.

When discovered, the fix has two shapes: (i) implement the missing capability in the lagging engine; (ii) narrow the registry to the intersection of what every gated impl actually supports, and add the broader names per-engine via `Engine.EXTRA_SUPPORTED` or equivalent. The choice is project-judgment; the rule's job is to surface the mismatch.

## Override

These rules are mandatory. No `[code-skip]` override. writing-code:5 (no hypothetical code) is mechanically enforced by `[`commit`](commit/SKILL.md)` step 4 (the affected-tests gate); writing-code:2 (history references in code comments) is mechanically enforced by `[`detect-ai-fingerprints`](detect-ai-fingerprints/SKILL.md)`; writing-code:9 (no silently-dropped parameters) lands mechanical at v2.2.0 via the AST scanner described above; writing-code:8 (multi-pass within file) ships under upstream issue #57 v1.6.2 milestone; the remaining six (writing-code:1, :3, :4, :6, :7, :10) are judgment-enforced via `[`code-review`](code-review/SKILL.md)`.

## Cross-references

- `[`writing-tests`](_writing-tests-rules.md)` writing-tests:2 (no cargo-cult patterns) is the test-side discipline for the same family of failures as writing-code:3.
- `[`writing-claims`](_writing-claims-rules.md)` writing-claims:1 (grep before declaring fix complete), writing-claims:2 (countable claims auditable), writing-claims:3 (confidence calibration) are the claim-side counterparts. The boundary: writing-code rules fire when editing code; writing-claims rules fire when stating facts in commit/PR bodies or chat.
- `[`verify-before-execute`](_verify-before-execute-rules.md)` Evidence clause is the parent discipline for writing-code:4 and writing-code:5; it also covers prose claims that name the same symbols.
- `[`environment-preflight`](_environment-preflight-rules.md)` is the one-time-per-repo inventory underlying writing-code:5.
- `[`commit`](commit/SKILL.md)` step 4 is the mechanical enforcement of writing-code:5.

## Migration note (v2.0.x only)

This file is derived from rules 3, 6, 9, 10, 12, 17, 18, and 20 of the deprecated `_no-ai-fingerprints-rules.md`. Rules 3 and 6 moved here from `_writing-prose-rules.md` because they apply to code-authoring acts (docstrings, code comments). Rules 10 and 17 moved here from `_writing-claims-rules.md` because they fire at code-edit time, and the operator editing code should find them in the writing-code lookup path; the underlying claim-grounding family connection is preserved via cross-reference. Old rule 20 (conditional-import callsite hygiene, shipped in v1.6.1) becomes writing-code:8 here. See `CHANGELOG.md` for the v2.0.0 migration table. This migration note is retained for one release cycle (v2.0.x) and removed in v2.1.0.

## Attribution

Defers to `[`output`](_output-rules.md)`. No AI / agent attribution in code, commits, or comments.
