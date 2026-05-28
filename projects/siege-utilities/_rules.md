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

### Rule SU-2: Does it do what it says?

If a function's name, docstring, or type signature claims generality, the implementation must match. Specific failure modes:

- Function accepts `crs: Any` but only works for EPSG codes → document the restriction or handle the full domain
- Function says "spatial database" but only works with PostGIS → name it `postgis_*` or handle SpatiaLite/DuckDB-spatial
- `except Exception: pass` anywhere → the function claims to handle all errors but actually discards them

**Required:** either narrow the claim (rename, restrict type signature, document limitations) or widen the implementation.

### Rule SU-3: No demo exemptions

Code under `examples/`, `notebooks/`, and demo scripts ships with the package. Users copy patterns from these files into their own code. Standards that apply to library code apply to demo code:

- No bare `except: pass`
- No hardcoded credentials or paths
- No silent fallbacks that hide broken dependencies
- Error messages must be actionable ("install X" not "something went wrong")

### Rule SU-4: Notebook coverage invariant

The `notebooks/` directory demonstrates library capabilities. When a library function's contract changes (new parameter, changed return type, new exception, removed default), the review must check whether any notebook calls that function.

- If a notebook calls the changed function → update the notebook or file a ticket
- If no notebook calls the changed function → note the gap; this is drift between the library and its documentation surface
- If the change adds a new capability → consider whether a notebook should demonstrate it

This rule is enforced by the `notebook-impact` skill, which must run on every fix or feature PR.

## Branch and merge conventions

- All work branches from `develop`, PRs target `develop`
- `main` is downstream of `develop` — never merge unblessed work directly to `main`
- CI billing is currently disabled on this repo; merges may require `--admin` flag

## Review standards

Every PR to this repository must pass the `hostile-review` skill before merge. The hostile review specifically checks for the error-handling philosophy violations above (SU-1 through SU-4) in addition to standard code review criteria.
