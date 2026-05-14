---
description: Always-on. Code-authoring discipline. Docstring brevity, no history references in code comments, no speculative abstractions, verify symbols exist before naming them, verify dependencies are reachable before writing code that uses them, doc-edit symmetry, no silent error swallowing. Test-writing rules live in `_writing-tests-rules.md`; claim-grounding (commit/PR-body claims) lives in `_writing-claims-rules.md`.
---

# Writing Code

These rules apply whenever the agent writes production code -- any `.py` file outside `tests/`, plus the comments and docstrings that live in those files. The unifying boundary is "verify before touching code": the rules fire at code-edit time, not at claim time.

The sibling boundary in `_writing-claims-rules.md` is "verify before claiming": rules that fire when stating a fact in a commit body, PR body, or chat. The two files split the same underlying claim-grounding family by temporal trigger; consult writing-code when editing code, consult writing-claims when stating facts.

## The fourteen code-writing rules

**writing-code:1. Default to no docstring or a one-liner.** Multi-paragraph Sphinx-style docstrings are reserved for public API surface that is exported and consumed externally. Internal helpers and one-off functions get type hints and at most one sentence. Docstrings are code, not prose; the discipline lives here rather than in `[`writing-prose`](_writing-prose-rules.md)`.

**writing-code:2. No PR / sprint / issue references inside code comments.** "Sprint A item 2," "the v3.15.0 hardening," "PR #443 follow-up" all rot the moment the codebase moves. Reference behaviour, not history. The git log is the history layer; the ticket tracker is the planning layer; code comments are the behaviour layer. This rule applies specifically to code comments; commit-message footers and PR descriptions can and should reference tickets via `Refs:` / `Closes:` trailers per `[`commit`](git-workflow/commit/SKILL.md)`.

**writing-code:3. No speculative abstractions.** Helpers, base classes, and configuration scaffolding are introduced only when a second caller already exists. "Future-proofing" without a second caller is dead weight. Revisit when the second caller arrives, not before.

This rule applies primarily to production code (helpers, base classes). When the failure mode is "test fixtures introduced for one test that will hypothetically have a second caller someday," see `[`writing-tests`](_writing-tests-rules.md)` writing-tests:2 for the test-side application.

**writing-code:4. Verify before asserting a symbol exists.** Before writing code, a test, or documentation that names a method, class, attribute, flag, or behaviour: open the file, grep for the symbol, read the actual signature. Production code that calls a non-existent method (the `create_presentation_from_data` failure mode, where the method is `create_analytics_presentation`) and documentation that asserts current behaviour reflecting aspiration (the INVARIANTS identifier-validation claim) are the canonical failures here. If a behaviour is aspirational, label it: `_aspiration, not current behaviour_` or equivalent.

This rule pairs with writing-code:5 below: both have the same shape ("verify Y before writing code that uses Y") and fire at the same trigger time. See `[`verify-before-execute`](_verify-before-execute-rules.md)` for the parent claim-grounding discipline that covers prose claims about the same symbols in PR bodies, commit messages, and agent-to-agent messages.

**writing-code:5. No hypothetical code.** When you write code or a test that depends on a library, service, configuration, or external API, you must have already verified the dependency is reachable in the target environment, and you must exercise the real dependency before claiming the code works. Reachable means reachable in the workspace where the code is being written, in the same session, before the code is written. CI does not count. The PR-body label `untested locally; first run is CI` is a one-time escape hatch when the dependency genuinely cannot be reached locally; using it means the agent has tried and failed, not that the agent did not try. Repeated use of the label is a smell. A mock test that asserts the mock was called is not exercise.

The companion `[`environment-preflight`](_environment-preflight-rules.md)` describes the one-time-per-repo inventory that establishes what is reachable; this rule is the per-action application. The mechanical enforcement is `[`commit`](git-workflow/commit/SKILL.md)` step 4 (the affected-tests gate); the rule itself is in force at write-time, not just at commit-time. Symmetric with writing-code:4: both verify a precondition before code that depends on it.

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

The session's concrete instance: both `census_gazetteer.py` and `wikidata_gazetteer.py` had `SHAPELY_AVAILABLE` flags but the geometry-construction callsites used `shapely.geometry.Polygon(...)` without guarding. The first call in an environment without shapely raised `NameError: name 'shapely' is not defined` instead of the intended clear `RuntimeError`. Cross-module re-export case (X re-exported from `__init__.py`, used in sibling module via `from .somemod import X`) is a known scanner gap; the failure mode is loud (immediate NameError) and the pattern is rare. Mechanical detection is high (multi-pass within a file; tracked at upstream issue #57 for v1.6.2); judgment-enforced via `[`code-review`](coding/code-review/SKILL.md)` until the scanner enhancement lands.

**writing-code:9. No silently-dropped parameters.**

When a method or function signature accepts a parameter, the implementation must do exactly one of:

- (a) use the parameter in the body,
- (b) raise `NotImplementedError("<param>=<value> not supported in <ImplName>; see <central-capability-symbol> for support matrix")` when the parameter is non-default. If no central capability registry exists in the project yet, name the supporting impls inline in the message; this creates a follow-on writing-code:10 obligation to extract a registry at the next param-set change,
- (c) document in the docstring of the **base class default** that the implementation is a no-op for that parameter and name which engines honour it. Subclasses that legitimately use the parameter need not repeat the disclaimer; the carve-out is for the abstract-base or default-impl tier where "the parameter is part of the surface but this implementation chooses not to honour it" is the documented contract,
- (d) pass the parameter through to a delegated implementation via `**kwargs` star-arg unpacking or by name.

The session's concrete instance: `load_polygons` and `load_lines` accepted `format: str = "auto"` and `geometry_col: str = "geometry"`; the default implementation called `self.read_spatial(path, crs=crs)` and ignored both. A caller passing `format="shapefile"` to recover from an auto-detection miss had no effect; the override was silently dropped. API lie: the signature claimed the parameter mattered; the implementation said otherwise.

Parameters consumed by a decorator (e.g. introspected by `@validate_args` or similar) are a judgment-enforced carve-out the AST scanner cannot see. Reviewer attests in the PR body that decorator-side consumption accounts for the apparent unused parameter. The scanner consults `.claude/scanner-config.toml` if present for a project-specific decorator allow-list; default allow-list is `{functools.wraps, contextlib.contextmanager, classmethod, staticmethod, property}`.

Mechanical via AST walk in `[`detect-ai-fingerprints`](meta/detect-ai-fingerprints/SKILL.md)`: collect signature args (name, default), collect `Name` and `keyword` references in body, flag args with non-`None` defaults that are neither referenced by name nor forwarded via `**kwargs`. Carve-out for decorator-consumed parameters via the allow-list above.

**writing-code:10. Capability declarations match implementations.**

When a module exposes a central "supported X" registry (a frozenset, dict, class attribute, or module-level constant) that a validator consumes, every implementation the validator gates access to must support every item in the registry. Mismatches mean the validator passes input the implementation will reject at runtime with a confusing error.

The session's concrete instance: `_SUPPORTED_AGG_NAMES` at line 68 of `dataframe_engine.py` is a frozenset of agg names the validator accepts. The pandas implementation does not implement `approx_count_distinct` (a member of the registry). A pandas caller passing `agg={"col": "approx_count_distinct"}` passes validation, then dies inside the pandas impl with `AttributeError`. The error is misleading because the validator already attested support.

This is the sibling rule of writing-code:9. writing-code:9 fires per-method-signature at function-definition review time; writing-code:10 fires at architecture review when a central registry's shape is examined against each consumer. Different scanners would catch each: writing-code:9 is one-pass AST per function; writing-code:10 needs cross-implementation tracing (validator to registry to consumers) that requires symbolic execution or extensive AST graph-building, infeasible at scanner tier. Judgment-enforced via `[`code-review`](coding/code-review/SKILL.md)`; coverage matrix marks `prevention_path` accordingly.

When discovered, the fix has two shapes: (i) implement the missing capability in the lagging engine; (ii) narrow the registry to the intersection of what every gated impl actually supports, and add the broader names per-engine via `Engine.EXTRA_SUPPORTED` or equivalent. The choice is project-judgment; the rule's job is to surface the mismatch.

**writing-code:11. No silent processes.**

Every function, method, script, or scheduled process that performs side effects (writes to disk, hits the network, mutates external state, registers UDFs, dispatches work, modifies a database, sends a message, emits a log to a downstream sink) must produce at least one observable signal at completion. The required-minimum floor is non-negotiable; the additive shapes are encouraged for high-signal processes.

**Required minimum (non-negotiable floor):** every side-effecting process must produce at least one of:

- (a) an inspectable return value naming what happened (status, count, structured result, the path written, the row count affected, the slide reference added). The return value must be inspectable: `True`/`False` is acceptable when the contract is binary; `None` is not acceptable when a real signal would fit.
- (b) a log line at INFO level or higher naming what happened (rows processed, files written, no-op reason, dependency-registered, slide-added). The log line must name the action and a unique-enough identifier for an auditor to confirm the action by greping logs.

The side-effect-artifact alone (file written to disk, mutation done) does NOT satisfy the floor. A function that writes a file, returns `None`, and does not log fails the floor: an auditor cannot confirm the action happened from the function's output. The fix is either return the path (a) or log "wrote `<path>`" (b). Both is fine; one is required.

**Additional shapes for high-signal processes:**

- (c) a metric written to a metrics sink (counter, gauge, timer, histogram), encouraged for batch jobs, scheduled processes, library entry points where downstream wants aggregable observability.
- (d) a side-effect with audit trail (commit on a known branch, ticket update, file in a known location with a known schema), encouraged for migrations, infrastructure changes, scheduled processes where the audit log is part of the process contract.

(c) and (d) are additive to the (a)-or-(b) floor, never substitutes.

**Carve-outs:**

- **Pure functions with no side effects:** the return value IS the output by definition; no log line required. A pure helper that computes `f(x) -> y` already satisfies (a).
- **Test assertions:** pytest's pass/fail dispatch is the signal; an `assert x == y` does not need a return value or log.
- **CLI subcommands whose stdout output is the contract:** when a `cli foo bar` command's stdout output is conventionally the consumer's input (operator pipes it, greps it, parses it), the printed output IS the observability. A log line in addition is fine but not required.

**Per-process-type guidance (advisory cookbook layered onto the menu):**

- Internal helper -> probably (a) return value.
- Library entry point -> probably (a) + (b).
- Batch job / scheduled process -> probably (b) + (c) + (d).
- Migration script -> probably (b) + (d).

**Contract-preservation override (v2.3.1).** When changing the floor shape from (a) to (b) or vice versa would break an established contract (existing call sites depending on the return type, or downstream tools depending on log presence), choose the additive option even if the per-process-type advisory would suggest otherwise. The session's concrete instance: `_ensure_sedona`'s pre-existing `None`-return contract made (b) log-only the right floor choice; switching to (a) return value would have broken every call site. Anti-pattern: rigidly following the advisory and inducing a breaking change to satisfy menu-style preference. The advisory is advisory; the floor is non-negotiable; the choice between floor shapes respects existing contracts.

Empirical evidence from the v2.3.0 fix-exercise (siege_utilities PR #487, five functions across powerpoint, logging, databricks):

| Case | Chosen floor | Per-process-type advisory predicted | Match? |
|---|---|---|---|
| `_ensure_sedona` | (b) log-only | (a) return value (helper) | **No — contract preserved** |
| `runtime_secret_exists` | (a) return value | (a) return value (helper) | Yes |
| `ensure_secret_scope` | (a)+(b) | (a)+(b) (library entry) | Yes |
| `put_secret` | (a)+(b) | (a)+(b) (library entry) | Yes |
| `_add_*_slide` family | (a) return value (with public-method log layered above) | (a) return value (helper) | Yes |

Distribution: 4 of 5 cases matched advisory; 1 of 5 (`_ensure_sedona`) used the contract-preservation override. The override is rare-but-load-bearing: it prevents the menu from inducing breakage in 1 of 5 retroactive-fix cases. Without the override, the (a)/(b) menu would force a choice that satisfies the rule's letter but violates writing-releases:1 (BREAKING-when-public-surface-changes-incompatibly). Two rules composing to prevent each other: not what we want.

**Family-of-methods scaling pattern (v2.3.1).** When writing-code:11 applies to a method family of N>5 (e.g. PowerPoint `_add_*_slide` family with 19 methods), document the convention at the enclosing class or module docstring, then per-method application can be ratchet-applied across multiple PRs without re-establishing the pattern. The class-docstring convention names the family-wide signal shape ("each `_add_*_slide` method returns the slide reference and logs `added <slide-name>` at INFO"); subsequent per-method commits cite the convention and apply it. Anti-pattern: blocking a PR on completing the full family at once, when ratchet-apply across releases is operationally cheaper and the convention itself is the load-bearing wording. The session's concrete instance: PowerPoint family applied to 4 + ratcheted at Issue #485 for the remaining 15.

The session's concrete instances:

- The PowerPoint `_add_*_slide` private methods (~20 instances in one file) mutate the `prs` argument and return `None`. A consumer iterating the methods to verify slides got added cannot tell from output alone whether the slide is in the deck. Floor fix: return the slide reference (a), or log "added `<slide-name>`" (b).
- `_ensure_sedona` re-raises on ImportError (writing-code:7-correct) but on success returns `None` silently. Caller cannot tell from output whether Sedona registered, was already registered, or was skipped because `_enable_sedona=False`. Floor fix: log.debug naming the path taken (e.g. "registered Sedona", "Sedona already registered", "skipped (config)").
- Operator-stated principle (2026-05-13 21:51 CDT): "no process should be written without output or logging. We should always be able to measure output." This rule is the formalization.

**Family of discipline:** writing-code:11 is the success-side complement to writing-code:7 (silent error swallowing). writing-code:7 covers the error path: every caught exception must produce a typed-failure result, an audit log, or a re-raise. writing-code:11 covers the success path: every side-effecting completion must produce an inspectable signal. Paired along the error/success boundary, the two rules close the observable-signal failure family.

Forward-only. Existing silent processes in the codebase are flagged when discovered but the rule's expectation is that codebases address them as discovery surfaces them, not big-bang. The fix-exercise pattern from v2.2.0-rc1 (each rule application becomes a per-rule commit citing the rule that drove the change) applies here.

Judgment-enforced via `[`code-review`](coding/code-review/SKILL.md)` at v2.3.0. Mechanical detection is tractable but non-trivial: AST-walk for side-effect detection (Call to known-side-effecting builtins like `open`, `os.write`, `subprocess.run`, plus method calls on known-mutable types), cross-reference with return type and log calls in body. Tracked for v2.3.x scanner enhancement.

**writing-code:12. No duplicate imports at module scope.**

Imports must appear exactly once at module scope. Duplicate `import X` statements (or `from X import Y` of the same name) are slop from branch-merging that linters often miss. Aliased imports of the same module count as duplicates unless both aliases are actually used in the body.

Banned shapes:

- `import os` followed later by `import os` (duplicate).
- `import warnings` followed by `import warnings as _warnings_mod` where `_warnings_mod` is never referenced (alias unused).
- `from collections import OrderedDict` repeated in a different `from collections import` block (folded).

Acceptable shapes:

- `import os` once.
- `import warnings` and `import warnings as _w` when both `warnings.warn(...)` and `_w.filterwarnings(...)` are referenced.
- Conditional imports inside `try:` / `except ImportError:` blocks (these are not "module scope" duplicates; they are availability fallbacks per writing-code:8).

The session's concrete instance: pass 2 `siege_utilities/geo/spatial_data.py` had two pairs of duplicate module-level imports (`import os` twice; `import warnings` parallel to `import warnings as _warnings_mod`). Slop from branch-merging.

Mechanical via AST scanner: walk module-level `Import` and `ImportFrom` nodes; for each `Import`, collect `(name, asname)` pairs; for each `ImportFrom`, collect `(module, name, asname)`; flag any pair appearing more than once. Aliased duplicates flagged unless both aliases are referenced in the module body (Name walk). Forward-only; existing duplicates flagged when scanned.

**writing-code:13. Consistent failure-mode contract within a function and across sibling methods.**

A function declares ONE failure-indication mechanism. Either `Optional[T]` returns with documented `None`-as-failure, OR a typed exception, OR a Result-style structured object. Mixing return-`None` with raise-Error for distinct failure cases inside the same function is banned: the caller has to handle two failure paths for one call.

Sibling methods within a class (methods sharing a name prefix or common verb) should follow the same failure-mode contract. If `create_X_presentation` raises and `create_Y_presentation` returns `None`, the API surface lies about its uniformity.

Banned shapes:

- `def get_dataset(...): if status != 200: return None; ... raise SpatialDataError(...)`: return-None for HTTP failure, raise for everything else. Caller has to handle both.
- A class with `create_alpha_presentation -> Path` (raises on failure), `create_beta_presentation -> Path` (raises), `create_gamma_presentation -> Path` (raises), and `create_comprehensive_presentation -> Dict` (returns `None` on failure). Naming says one shape; impls do another.

Acceptable shapes:

- One mechanism per function: `Optional[T]` with docstring `"or None if not found"`, OR typed exception, OR Result/Either/Option-style.
- Sibling methods consistent: all raise, OR all return Optional, OR all return Result.
- Genuine shape divergence renamed: `create_*_presentation` (writes file, raises) vs `build_*_presentation_structure` (returns Dict for caller to render). Naming differentiates the contract.

The session's concrete instances:

- Pass 2 SP14: `_get_dataset_metadata` returns None for HTTP non-2xx, raises SpatialDataError for other failures.
- Pass 4 PG7: `PowerPointGenerator.generate_powerpoint_presentation` returns `bool` while sibling `create_*_presentation` methods return `Path` and raise on failure. Same class, two failure-indication paradigms.
- Pass 8 (filed as Issue #483): `credential_manager` 1Password backend returns None for "not found" and raises for transport errors, but the wrapping helpers conflate the two.

Cross-rule composition: writing-code:13 closes the failure-contract gap that writing-code:7 (silent error swallowing) left open. writing-code:7 ensures every except produces a typed-failure result OR re-raise OR audit-log; writing-code:13 ensures the choice is consistent within a function and across sibling methods. Paired together, they prevent both silent swallow and inconsistent contract.

Judgment-enforced via `[`code-review`](coding/code-review/SKILL.md)`. Mechanical detection requires control-flow analysis (Optional return + raise on different paths in same function); tractable but non-trivial. Tracked for v2.3.x scanner enhancement.

Empirical note (v2.4.0): the rename-over-converge option of writing-code:13 has zero-of-five firing rate across v2.3.0 and v2.3.1 fix exercises; real-world inconsistent contracts converged cleanly in every case. Option retained for completeness; recurrence threshold set at 5+ exercises before reconsidering removal. Coverage matrix entry annotated.

**writing-code:14. No exception-as-dispatch when alternatives are content-distinguishable.**

When a function dispatches between two or more alternative successful operations (parse-as-WKB-or-WKT, fetch-from-cache-or-source, treat-as-path-or-url), do not use try/except as the dispatcher. Inspect the input and dispatch deterministically.

**Definition.** Alternatives are **content-distinguishable** when the input itself can be inspected (regex match, leading bytes, first-token classification, type check, isinstance check, pure-function predicate) to dispatch deterministically without exception flow. The inspection is cheap and reliable; the exception-as-dispatch is the silent-swallow that hides bugs.

Banned shape:

```python
try:
    return shapely_wkb.loads(s, hex=True)
except Exception:
    return shapely_wkt.loads(s)
```

A corrupt WKB-hex string falls through to WKT, which then raises a confusing WKT parse error or silently returns garbage. The dispatcher swallows the WKB error.

Acceptable shape:

```python
if all(c in HEX_CHARS for c in s[:8]):
    return shapely_wkb.loads(s, hex=True)
return shapely_wkt.loads(s)
```

Or:

```python
def _looks_like_wkb_hex(s: str) -> bool:
    return bool(WKB_HEAD_RE.match(s))

if _looks_like_wkb_hex(s):
    return shapely_wkb.loads(s, hex=True)
return shapely_wkt.loads(s)
```

**Carve-out.** When alternatives genuinely cannot be inspected without attempting the operation (some grammar contexts, ambiguous tokenization, parse-attempt-IS-the-inspection cases), exception-as-dispatch is the legitimate fallback. The carve-out is not "the inspection is annoying to write"; it is "no inspection function exists that would not itself need the parse to disambiguate." When in doubt, write the inspection helper and explicitly document that exception-as-dispatch was rejected because content was distinguishable.

The session's three concrete instances (triangulated across module shapes):

- DuckDBEngine `_parse_geom`: WKB-hex vs WKT dispatch via try/except. Pure-hex chars in head are the deterministic distinguisher.
- `logging.py` `_create_rotating_file_handler`: ImportError-as-availability-check via try/except for `pwd` module. `hasattr(os, 'getuid')` (or equivalent runtime-context predicate) is the deterministic distinguisher.
- `databricks.get_dbutils`: environment-detect via try/except chain (notebook-context vs script-context). Runtime context check (`'dbutils' in globals()` or environment variable) is the deterministic distinguisher.

Cross-rule composition with writing-code:7: writing-code:14 is a specific case of writing-code:7 where the silent swallow happens via dispatch rather than via empty handler. writing-code:7's scanner detects the four base banned shapes (Pass / Return None|False / Continue / log+terminator); writing-code:14 detects the dispatch shape (catch-all returning a different valid result via alternative path). Both rules can apply; writing-code:14 is more specific and produces a sharper diagnostic.

Judgment-enforced via `[`code-review`](coding/code-review/SKILL.md)` at v2.4.0. Mechanical detection candidate: TC5 alternative-return-shape from sibling's writing-code:7 scanner test-case set (catch-all `except` whose body returns a different result without re-raise). Scanner enhancement queued for v2.4.x.

## Override

These rules are mandatory. No `[code-skip]` override. writing-code:5 (no hypothetical code) is mechanically enforced by `[`commit`](git-workflow/commit/SKILL.md)` step 4 (the affected-tests gate); writing-code:2 (history references in code comments) is mechanically enforced by `[`detect-ai-fingerprints`](meta/detect-ai-fingerprints/SKILL.md)`; writing-code:9 (no silently-dropped parameters) lands mechanical at v2.2.0 via the AST scanner described above; writing-code:12 (no duplicate imports) lands mechanical at v2.3.1 via AST scanner; writing-code:7 (silent error swallowing) lands mechanical at v2.3.1.1 via AST scanner with carve-outs for Optional[T]+docstring, `# noqa: writing-code-7` opt-out, and the `except ImportError`+flag-pattern idiom (writing-code:8 territory); writing-code:8 (multi-pass within file) ships under upstream issue #57 v1.6.2 milestone; the remaining eight (writing-code:1, :3, :4, :6, :10, :11, :13, :14) are judgment-enforced via `[`code-review`](coding/code-review/SKILL.md)`. writing-code:11, :13, :14 scanner enhancements tracked for v2.3.x and beyond. writing-code:7 scanner has two enhancement candidates queued for v2.3.2/v2.4.0: TC5 catch-all-with-alternative-return-shape (also the writing-code:14 mechanical detection candidate) and TC8 catch-all-wrapping-pure-logic-body.

## Cross-references

- `[`writing-tests`](_writing-tests-rules.md)` writing-tests:2 (no cargo-cult patterns) is the test-side discipline for the same family of failures as writing-code:3.
- `[`writing-claims`](_writing-claims-rules.md)` writing-claims:1 (grep before declaring fix complete), writing-claims:2 (countable claims auditable), writing-claims:3 (confidence calibration) are the claim-side counterparts. The boundary: writing-code rules fire when editing code; writing-claims rules fire when stating facts in commit/PR bodies or chat.
- `[`verify-before-execute`](_verify-before-execute-rules.md)` Evidence clause is the parent discipline for writing-code:4 and writing-code:5; it also covers prose claims that name the same symbols.
- `[`environment-preflight`](_environment-preflight-rules.md)` is the one-time-per-repo inventory underlying writing-code:5.
- `[`commit`](git-workflow/commit/SKILL.md)` step 4 is the mechanical enforcement of writing-code:5.

## Migration note (v2.0.x only)

This file is derived from rules 3, 6, 9, 10, 12, 17, 18, and 20 of the deprecated `_no-ai-fingerprints-rules.md`. Rules 3 and 6 moved here from `_writing-prose-rules.md` because they apply to code-authoring acts (docstrings, code comments). Rules 10 and 17 moved here from `_writing-claims-rules.md` because they fire at code-edit time, and the operator editing code should find them in the writing-code lookup path; the underlying claim-grounding family connection is preserved via cross-reference. Old rule 20 (conditional-import callsite hygiene, shipped in v1.6.1) becomes writing-code:8 here. See `CHANGELOG.md` for the v2.0.0 migration table. This migration note is retained for one release cycle (v2.0.x) and removed in v2.1.0.

## Attribution

Defers to `[`output`](_output-rules.md)`. No AI / agent attribution in code, commits, or comments.
