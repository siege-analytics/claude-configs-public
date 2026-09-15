# Data Trust Rules

Shared default assumption: **tabular data lies**. Identifiers drift, crosswalks rot, files are truncated, encodings mismatch, vintages diverge. Every skill that ingests or joins external data reads this file first.

## Core principle

**Validate at boundaries.** Once data is inside the system, treat it as clean. At the boundary -- ingestion, API response, file read, user input, third-party library return -- assume nothing and check.

## Before you join

Ask of every column on the join key:

1. What's the vintage of this crosswalk? When was it built? When was the underlying source last updated?
2. Does it cover all the values I need? Run `left.key.nunique()` vs. `left.merge(right, on=key).key.nunique()` and count the drop.
3. Is the identifier system consistent (USPS vs. ISO vs. FIPS vs. Census name)?
4. Is there a NULL/empty rate ≥ 5%? That's a signal upstream is dropping rows.

If any answer is uncertain, proceed with a post-join audit (below).

## After every join -- log loss

```python
pre = len(left)
merged = left.merge(right, on=key, how="left")
unmatched = merged[merged[right_col].isna()]
if len(unmatched):
    log_warning(
        f"{description} join dropped {len(unmatched)}/{pre} rows "
        f"({len(unmatched)/pre:.1%}); sample unmatched: "
        f"{unmatched[[key]].drop_duplicates().head(5).to_dict('records')}"
    )
```

Silent NaN after a left-join is how dirty data corrupts analytics downstream.

## Ingestion-boundary validation

Don't trust column contents. Coerce and raise on unknown:

```python
def normalize_state(raw: str) -> str:
    raw = raw.strip().upper()
    if raw in USPS_CODES:
        return raw
    if raw in FIPS_TO_USPS:
        return FIPS_TO_USPS[raw]
    if raw in NAME_TO_USPS:
        return NAME_TO_USPS[raw]
    raise ValueError(f"unknown state identifier: {raw!r}")
```

Apply the same pattern to FIPS (leading zeros stripped by Excel), ZIP (9-digit split), date formats (`YYYY-MM-DD` vs `MM/DD/YYYY`), party codes (`D`/`DEM`/`Democratic`/`democrat`).

## Vintage pinning

Any join involving geography, jurisdiction, or categorical code has an implicit year dimension. Pin it:

```python
# BAD -- which vintage?
merged = donors.merge(counties, on="county_fips")

# GOOD -- explicit
counties_2020 = counties[counties.year == 2020]
merged = donors.merge(counties_2020, on="county_fips")
```

When upstream lacks a vintage column, infer it (row count heuristic, known schema changes) or treat as untrusted.

## Don't silently fall back

When a primary lookup fails, raising is almost always better than returning a default. The rare exception is a documented "not found" return type (e.g., `Optional[X]`). Cross-reference `coding/python-exceptions/SKILL.md`.

Anti-pattern:
```python
# Fails silently if tract_id is unknown -- tract is dropped from output
demographics = tract_lookup.get(tract_id, {})
```

Better:
```python
demographics = tract_lookup.get(tract_id)
if demographics is None:
    log_warning(f"unknown tract_id={tract_id!r}; dropping row")
    return None  # caller sees None and can count drops
```

## Checklist before shipping data code

- [ ] Every public function documents the identifier system(s) it accepts
- [ ] Normalization runs at ingestion with explicit failure mode on unknown input
- [ ] Join vintages are pinned (no ambiguous "current")
- [ ] Unmatched-row rate is logged after every left/outer join
- [ ] Tests include a "known-dirty" fixture covering Excel-stripped zeros, empty strings, ISO/USPS variants, renamed categorical values
- [ ] No `.get(key, default)` on lookup tables unless the default is semantically meaningful

## Applies to

Any skill that touches:
- DataFrames / GeoDataFrames / database rows
- External APIs (JSON, GraphQL, CSV downloads)
- File parsing (CSV, Excel, fixed-width)
- Cross-repository joins (e.g. linking Linear issues to GitHub PRs)

## See also

- `analysis/spatial/SKILL.md` -- decision framework with Step 1 data-trust check
- `analysis/spatial/reference.md` -- dirty-data recipes section
- `coding/python-exceptions/SKILL.md` -- raise-vs-silent-default decision

## Attribution Policy

NEVER include AI or agent attribution in code, commits, or documentation.
