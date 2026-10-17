---
name: over-engineering-audit
description: >
  Repo-wide audit for over-engineering. Scans the codebase for what to delete,
  simplify, or replace with stdlib/platform equivalents. Ranked one-line-per-finding
  report with five tags: delete, stdlib, platform, yagni, shrink. Use when the user
  says "audit for over-engineering", "find bloat", "what can we delete", "simplify
  this repo", or "is this over-engineered". One-shot report, applies nothing.
---

# Over-Engineering Audit

Scan the repo for unnecessary complexity. One finding per line, ranked biggest
cut first. The goal is a shorter, simpler codebase — not a style critique.

## Tags

| Tag | Definition | When to use |
|-----|-----------|-------------|
| `delete` | Dead code, unused flexibility, speculative feature | Unreachable branches, unused parameters with defaults, classes/functions with zero call sites, feature flags nobody reads |
| `stdlib` | Hand-rolled thing the standard library ships | Custom CSV parser vs `csv`; hand-rolled retry loop vs `tenacity` (if installed) or `urllib3.util.retry`; manual JSON schema validation vs `jsonschema` |
| `platform` | Code doing what the platform already provides | Python loop over rows vs vectorized pandas/numpy op; app-side spatial filter vs PostGIS `ST_Within`; app-side join vs SQL join; manual HTML escaping vs `markupsafe`; custom date parsing vs `datetime.fromisoformat` |
| `yagni` | Abstraction with one consumer, config nobody sets, layer with one caller | ABC/Protocol with one implementation; factory that produces one product; config key read in exactly one place; wrapper that only delegates to the wrapped object |
| `shrink` | Same logic, fewer lines | Manual loop buildable as comprehension; repeated blocks extractable to shared helper; verbose conditional replaceable with `or`/ternary; multi-step transform expressible as pipeline |

## Format

One line per finding:

```
<file>:<lines>: <tag> <what to cut>. <replacement>.
```

Multi-finding example:

```
geo/boundaries.py:L45-82:  stdlib   38-line URL builder. urllib.parse.urlencode, 2 lines.
engines/base.py:L120:      yagni    AbstractEngine registered but never subclassed outside engines/. Inline until a second consumer exists.
survey/weights.py:L30-44:  shrink   manual loop builds dict from two lists. dict(zip(keys, values)), 1 line.
reporting/charts.py:L8:    platform matplotlib color cycle set manually. Use plt.rcParams['axes.prop_cycle'], already configured.
data/loader.py:L55-90:     delete   retry-with-backoff wrapper around a local file read. Nothing replaces it.
```

End with the only metric that matters:

```
net: -N lines, -M deps possible.
```

Nothing to cut: `Lean already. Ship.` and stop.

## Hunt list

What to look for, roughly in order of impact:

1. **Dead code.** Functions, classes, modules with zero importers. `grep -rn` for the symbol name; if nothing outside its own file and tests references it, it's dead.
2. **Single-implementation abstractions.** ABCs, Protocols, base classes whose `__subclasses__()` or implementors number exactly one. The abstraction is speculative until a second implementation exists.
3. **Hand-rolled stdlib.** Custom implementations of things Python ships: path manipulation (`os.path` / `pathlib`), URL construction (`urllib.parse`), temporary files (`tempfile`), argument parsing, string formatting, date arithmetic, CSV/JSON/TOML parsing.
4. **Dependency doing what the platform does.** A pip dependency whose functionality is covered by stdlib, the database engine, or an already-installed heavier dependency. Example: `python-dateutil` for parsing when `datetime.fromisoformat` suffices; a spatial library for distance when PostGIS `ST_Distance` is available.
5. **Wrapper-only classes.** A class whose methods all delegate to a single wrapped object with no added logic. The wrapper adds indirection without value.
6. **Config nobody sets.** Configuration keys, environment variables, or constructor parameters that are only ever used with their default value across the entire codebase. The configurability is speculative.
7. **Dead flexibility.** Plugin registries with one plugin. Strategy patterns with one strategy. Event systems with one subscriber. Hook points nobody hooks.
8. **Verbose equivalents.** Multi-line blocks that have idiomatic one-line or few-line replacements (comprehensions, `dict(zip(...))`, `itertools`, `functools`, unpacking).

## Architectural carve-outs

Some patterns look like over-engineering but exist by design. Do NOT flag these:

- **Engine abstraction** (multi-engine DataFrame: pandas, DuckDB, Spark, PostGIS) — architectural decision §2 in CLAUDE.md. The abstraction serves a real multi-consumer need.
- **Lazy-loading `__getattr__`** (PEP 562 deferred imports) — architectural decision §6. Required because the dependency tree is enormous; you must be able to import one piece without pulling the whole library.
- **Pluggable provider contracts** (boundary providers, geocoders, data sources with shared return shapes) — architectural decision §5. Multiple providers exist or are planned; the contract enables composition.
- **The composition chain** (address → geocoder → GEOID → boundary provider → demographic overlay → choropleth) — canonical domain architecture per strategic intent.
- **Error types that distinguish failure modes** — SU-1 requires errors to be distinguishable from success. A custom exception hierarchy that serves this purpose is not over-engineering.
- **Logging and progress indicators** — tactical principle §3 requires observable output from every side-effecting process. Logging infrastructure that serves this is not bloat.

When in doubt: if the pattern is named in CLAUDE.md or the project's architectural decisions as intentional, it's a carve-out. If it's not named anywhere and has one consumer, it's a candidate.

## Scoring

After all findings, summarize:

```
net: -N lines, -M deps possible.
```

Where:
- **N** = total lines deletable or replaceable across all findings
- **M** = number of dependencies that become removable if findings are applied

If N = 0 and M = 0: `Lean already. Ship.`

## Boundaries

- **Complexity only.** Correctness bugs, security holes, and performance problems go to a normal review or hostile-review pass — not this one.
- **One-shot report.** Lists findings, applies nothing. The user decides what to act on.
- **No style opinions.** "I would have written it differently" is not a finding. A finding names what to cut and what replaces it. If nothing replaces it, the tag is `delete`.
- **Tests are not bloat.** A test file, even a verbose one, is not an over-engineering finding. Test infrastructure (custom frameworks, fixture factories, mock hierarchies) can be, but the tests themselves are not.
- **Docs are not bloat.** Docstrings, comments explaining why (not what), and README content are not findings. Excessive inline prose that restates what the code says may be a `shrink` candidate.
