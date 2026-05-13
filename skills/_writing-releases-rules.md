---
description: Always-on. Release-act discipline. Any change rejecting previously-accepted input or removing a public name gets a BREAKING entry. Any net increase in skip-site count needs an explicit justification in the PR body. Applies when cutting a release or merging a PR that affects the public surface or the test-suite coverage.
---

# Writing Releases

These rules apply at release-cut time and at PR-merge time when the change affects either the public API surface or the project's skip-site count. Release-cuts ship contracts to downstream consumers; quiet contract changes break consumers silently. Skip-site growth is the test-suite analogue: each accepted skip is a piece of coverage the project quietly accepted losing.

## The release-writing rules

**writing-releases:1. BREAKING in the changelog if the change is breaking.**

Any change that rejects input previously accepted, returns output previously not returned, or removes a public name gets a `### BREAKING` entry. Determined by diffing the public surface against the previous tag. Until tooling exists to do this mechanically (a public-surface differ that handles `__all__`, leading-underscore convention, and re-exports through `__init__`), the determination is operator-judgment with an explicit checklist:

- Grep for renamed/removed top-level names.
- Grep for new validators that reject previously-accepted input.
- Grep for new return types in functions previously returning a different shape.

Tooling is a follow-up ticket (tracked at the `claude-configs-public` repo's issue #51); the rule is in force now. The session's worst case: a `groupby_agg` validator was added that rejects `median`, `sem`, and other names pandas previously accepted, shipped in a minor release with no BREAKING section.

**writing-releases:2. Skip-count trending.**

When a PR adds a new `pytest.skip(...)`, `@pytest.mark.skipif(...)`, or `@pytest.mark.skip(...)` call site, the PR body must contain a `New-skip: <count>; <reason>` trailer naming the new skip count and why it cannot be unskipped today. The scanner counts skip sites in `main` vs the PR's diff; any net increase requires the trailer. Removing a skip needs no trailer.

The Django ORM tests in the originating arc accumulated skips ("Postgres not available," "GDAL not installed") and CI stayed green while the test surface silently shrank. `[rule:writing-tests]` writing-tests:3 says each skip must name its remediation; this rule says the project's total skip count must not silently trend upward.

Forward-only; existing skips are grandfathered. Mechanically enforced by `[skill:detect-ai-fingerprints]` `--pr <n>` mode (scans the PR diff for new skip sites, compares against the base, requires the trailer when the count increased).

## Override

These rules are mandatory. No `[release-skip]` override. writing-releases:1 stays operator-judgment until the public-surface differ ships; writing-releases:2 is mechanical from v2.0.0 onward.

## Cross-references

- `[rule:writing-tests]` writing-tests:3 (skip messages must name the remediation) is the per-skip discipline; writing-releases:2 is the across-PRs trending discipline. Both apply together.
- `[skill:create-pr]` is the artifact-skill that produces PR bodies; the `New-skip:` and `BREAKING` trailers are required when the rules fire.
- `[skill:detect-ai-fingerprints]` mechanically enforces writing-releases:2 when invoked in `--pr <n>` mode.

## Migration note

This file is derived from rule 14 of the deprecated `_no-ai-fingerprints-rules.md`, plus the R-21 skip-count-trending extension proposed in the v1.7.0 round and landed inside v2.0.0. See `CHANGELOG.md` for the v2.0.0 migration table. This migration note is retained for one release cycle (v2.0.x) and removed in v2.1.0.

## Attribution

Defers to `[rule:output]`. No AI / agent attribution in releases, changelogs, commits, or comments.
