---
description: Project-specific rules for siege_utilities. These take precedence over general rules within the siege-utilities scope. Falls back to general rules for anything not described here.
---

# siege-utilities project rules

These rules apply only when working in the `siege-analytics/siege_utilities` repository. They take precedence over general rules within this scope. For any situation not described here, the general rules in `skills/RULES.md` apply.

## Overrides table

Any project rule that weakens a general rule must be declared here. If a project rule weakens a general rule without an entry in this table, the general rule wins.

| Project rule | General rule weakened | Justification |
|---|---|---|
| *(none yet)* | | |

## Error handling philosophy

### Rule SU-1: Errors are not data

Functions must not return valid-shaped empty results on failure. The following return values on error paths are bugs, not design choices:

- `return pd.DataFrame()` — lies about "no data found" vs "query failed"
- `return []` or `return {}` — hides structural failures behind empty collections
- `return 0.0` or `return ""` — makes numeric/string callers silently consume garbage
- `return None` without documentation — ambiguous between "not found" and "failed"

**Required:** raise an exception, log a warning/error, or return a documented sentinel that callers can distinguish from success. "Return empty on error" is a bug class, not a per-instance judgment call.

**Enforcement tiers:**

1. **Tier 1 — exception type breadth** (automated: `check_broad_except.py`): bare `except:` and `except Exception` handlers. These are caught by the linter.
2. **Tier 2 — return value on error** (hostile review): narrowed except blocks that still return `[]`, `{}`, `""`, `0.0`, or `None`. The linter passes these because the exception type is specific, but they still violate SU-1. Hostile review must scan for `return` statements inside `except` blocks.
3. **Tier 3 — non-error paths returning wrong types** (hostile review): functions that compute a value but return the wrong thing (e.g., computing `rowcount` then returning an empty DataFrame). These are logic bugs, not error-handling bugs, but they produce the same symptom: the caller cannot distinguish success from failure.

Tiers 2 and 3 are not currently lintable. Until a linter exists, every hostile-review pass must include a grep for `return []`, `return {}`, `return ""`, `return 0`, `return 0.0`, and `return None` inside except blocks.

### Rule SU-2: Does it do what it says?

If a function's name, docstring, or type signature claims generality, the implementation must match. Specific failure modes:

- Function accepts `crs: Any` but only works for EPSG codes → document the restriction or handle the full domain
- Function says "spatial database" but only works with PostGIS → name it `postgis_*` or handle SpatiaLite/DuckDB-spatial
- `except Exception: pass` anywhere → the function claims to handle all errors but actually discards them
- Function docstring lists N valid values for a parameter but the code only checks a subset — invalid values silently fall through to a default code path
- Return type annotation says `Union[X, Y]` but only X is ever returned

**Required:** either narrow the claim (rename, restrict type signature, document limitations) or widen the implementation. For enumerated parameter values, validate at the top of the function and raise `ValueError` for unrecognized inputs.

### Rule SU-3: No demo exemptions

Code under `examples/`, `notebooks/`, and demo scripts ships with the package. Users copy patterns from these files into their own code. Standards that apply to library code apply to demo code:

- No bare `except: pass`
- No hardcoded credentials or paths
- No silent fallbacks that hide broken dependencies
- Error messages must be actionable ("install X" not "something went wrong")

### Rule SU-4: Coverage invariant

Tests and notebooks are the feedback surface. Code without error-path tests and without notebook coverage is untested speculation that happened to compile.

#### SU-4a: Notebook coverage

The `notebooks/` directory demonstrates library capabilities. When a library function's contract changes (new parameter, changed return type, new exception, removed default), the review must check whether any notebook calls that function.

- If a notebook calls the changed function → update the notebook or file a ticket
- If no notebook calls the changed function → note the gap; this is drift between the library and its documentation surface
- If the change adds a new public module → at least one notebook cell must demonstrate it, including an error-path cell that shows what happens on bad input

This sub-rule is enforced by the `notebook-impact` skill, which must run on every fix or feature PR.

#### SU-4b: Error-path test coverage

Every public function that can fail must have at least one test exercising the failure path. "Failure path" means: exception raised, error logged, sentinel returned, or degraded result produced. Mocking all dependencies to always succeed is not testing — it is confirming that the happy path compiles.

Specific requirements:
- Every `except` block must be exercised by at least one test that triggers the exception
- Every `raise` statement must be exercised by a test that asserts the exception type and message
- Every "return empty on error" path (even documented ones) must have a test proving the caller can distinguish it from "no data found"
- Provider-based modules (overlays, geocoders, data clients) must test: provider is None, provider raises, provider returns unexpected shape

**Incident justification:** Round 7 hostile review (2026-05-28) found 10 real bugs that survived 6 prior review rounds because 90% of the 380-test suite only exercised happy paths. The bugs were in error paths that no test ever reached. Mocked-to-success tests gave false confidence that the code worked.

**Mechanical test:** if `pytest --co` lists N tests for a module with M except/raise sites, and fewer than M tests have "error", "fail", "invalid", "missing", or "raises" in their name, the module fails this rule.

## Branch and merge conventions

- All work branches from `develop`, PRs target `develop`
- `main` is downstream of `develop` — never merge unblessed work directly to `main`
- CI billing is currently disabled on this repo; merges may require `--admin` flag

## Bookshelf cross-reference

SU-1 through SU-4 were written from first principles during hostile review. These bookshelf sources provide the established foundations:

| Rule | Bookshelf concept | Source |
|---|---|---|
| SU-1 (Errors are not data) | Fail fast; invariant enforcement; making illegitimate states unrepresentable | `_robustness-rules.md` (Viafore) |
| SU-1 | Exceptions over error codes; handle errors at the appropriate abstraction level | `_principles-rules.md` (Martin) |
| SU-2 (Does it do what it says?) | Protocol-based dispatch; type safety as communication; constraining interfaces | `_robustness-rules.md` (Viafore) |
| SU-2 | Intention-revealing names; functions do one thing | `_principles-rules.md` (Martin) |
| SU-3 (No demo exemptions) | No undeclared dependencies; entry points over scripts | `_packaging-rules.md` (PyPA) |
| SU-3 | Deprecation warnings must name the replacement | `_scipy-spec-rules.md` (SPEC 4) |
| SU-4a (Notebook coverage) | Lazy registry must stay in sync; test the registry in CI | `_scipy-spec-rules.md` (SPEC 6) |
| SU-4b (Error-path coverage) | Round-trip properties; no-crash invariants; oracle comparison | `_property-testing-rules.md` (Hypothesis) |
| SU-4b | Test business logic against fakes, not mocks of the ORM | `_architecture-patterns-rules.md` (Percival & Gregory) |

## Review standards

Every PR to this repository must pass the `hostile-review` skill before merge. The hostile review specifically checks for the error-handling philosophy violations above (SU-1 through SU-4) in addition to standard code review criteria.
