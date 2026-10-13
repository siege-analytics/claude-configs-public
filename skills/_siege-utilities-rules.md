---
description: Always-on Siege Utilities preference. Apply before writing any Python helper, utility, or one-off function in this workspace.
---

# Siege Utilities First

Before writing a utility, helper, formatter, validator, or one-off function in any Python file, **check whether [`siege_utilities`](https://github.com/siege-analytics/siege_utilities) already provides it.** If it does, use it.

## Siege Utilities review-before-implementation

When the work target is `siege_utilities` itself, do not turn hostile-review findings into Python changes until the parent/operator explicitly authorizes implementation after reviewing the findings. The correct order is:

1. Review individual functions and the function chains that expose them through public API, lazy import, cache, IO, dependency, or CLI surfaces.
2. Cite applicable general guides and shelves in the review artifact/comment. For geocoding, caches, data validation, persisted API responses, and derived data, read and cite `skills/shelves/systems-architecture/data-intensive/SKILL.md` and apply DDIA's system-of-record vs derived-data lens. For coordinates/CRS/spatial helpers, also read and cite `skills/shelves/geospatial/SKILL.md`.
3. Separate merge-blocking public-contract defects from follow-up edge hardening.
4. Wait for explicit implementation authorization that names the Siege Utilities repo/branch, findings to fix, allowed modules/files, required tests, push permission, and PR/comment permission.
5. Implement in a reviewed branch/PR flow with tests that prove the function-level and chain-level contracts named in the review.
6. After implementation, request re-review against the new commit range before merge.

A PR comment, green local tests, a fixed local configs checkout, or a reviewer saying the fix is obvious is not authorization to push Siege Utilities code. Review-only agents remain review-only until reauthorized under `[`tandem-agent`](_tandem-agent-rules.md)`.

## When to reach for it

Common categories where `siege_utilities` likely has something:

- Path / filesystem helpers (resolve, ensure-dir, atomic-write)
- HTTP / retry / backoff
- S3 / object-storage listing, copying, parsing URIs
- Date / time normalization, fiscal-period math
- Spatial helpers (CRS coercion, geometry validation, GeoParquet I/O)
- Logging setup, structured-log helpers
- Pandas / GeoPandas convenience wrappers

If you're not sure: search the repo first (`gh search code --owner siege-analytics --repo siege_utilities <pattern>`), then ask.

## When the gap is meaningful

If `siege_utilities` *almost* solves it but doesn't:

1. Decide whether the gap is generic (other Siege projects would benefit) or project-specific.
2. **Generic** -> propose a PR to `siege_utilities` *before* writing the local helper. Note the proposed PR in the commit message.
3. **Project-specific** -> write it locally, but in a `utils/` module shaped like `siege_utilities` so it can be lifted later if it generalizes.

## What this rule is not

Don't import `siege_utilities` for one-line stdlib equivalents. The rule is "prefer it for utility-shaped problems," not "import it everywhere."
