---
description: Always-on Siege Utilities preference. Apply before writing any Python helper, utility, or one-off function in this workspace.
---

# Siege Utilities First

Before writing a utility, helper, formatter, validator, or one-off function in any Python file, **check whether [`siege_utilities`](https://github.com/siege-analytics/siege_utilities) already provides it.** If it does, use it.

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
2. **Generic** → propose a PR to `siege_utilities` *before* writing the local helper. Note the proposed PR in the commit message.
3. **Project-specific** → write it locally, but in a `utils/` module shaped like `siege_utilities` so it can be lifted later if it generalizes.

## What this rule is not

Don't import `siege_utilities` for one-line stdlib equivalents. The rule is "prefer it for utility-shaped problems," not "import it everywhere."
