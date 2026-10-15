# #976 Tier C — pre-mortem and self-review

Base: `develop` at `f115158b58db3690d2ea63999699284dc79db1bb`. Target: draft PR to `develop` only. No release, main promotion, installation, deployment, retirement, or merge.

Pre-mortem-artifact: plans/issue-976-data-scope-premortem.md
Hostile-review-artifact: plans/issue-976-data-scope-review.md

## Assumptions

Goal source: #976 audit comments and #962 epic (outside this diff).
Working as: software engineer, data engineer, geospatial analyst, tech lead.
Pre-author-inventory: plans/issue-976-data-scope-review.md#pre-author-inventory
Investigate-artifact: plans/issue-976-data-scope-review.md
Project-contribution: preserve trustworthy deterministic data task selection while keeping optional references and project-specific invariants out of foreign repositories.

### Verified Shapes

- PROBED: exact base and branch identity via `git rev-parse HEAD`/`git merge-base`, both `f115158b58db3690d2ea63999699284dc79db1bb` before changes.
- PROBED: active `skills/{pipeline-jobs,analysis,unity-catalog,scala-on-spark,sql,spark,databricks,spatial,postgis,geopandas,sedona,duckdb-spatial}/SKILL.md`, manifest, #975 ledger/test, and #976 issue comments inspected before route edits.
- ATTESTED: only `github.com/siege-analytics/siege_utilities` is verified by project definition + exact resolver repo, not production installation; all other consumers UNKNOWN.

## Pre-author inventory

Contact surfaces: selector/runtime (`bin/resolve-load-set.py`, manifest), operational data skills and global SU prose, exact-project overlay, reference shelves, #975 fixtures/checker, generated source/package authority and progressive metrics, protected CI risk policy. No source removal. The base inventory is 198 authoritative sources; the focused data ledger enumerates 34 sources and four disposition classes. External electinfo paths are historical references, not new project overlays.

## Peer review

Review-only Execute-mode **Data scope pre-mortem**, **Data scope hostile review**, and **Data scope second review** inspected the same worktree. The hostile and second reviewers repeatedly returned CHANGES REQUESTED on specific catalog/Scala/visualization/host/newline/bytes/test weaknesses; focused fixes and 78 source/Claude/Craft fixtures followed. Both then returned provisional ACCEPT pending the exact committed SHA, explicitly not merge/deploy approval. Peer check cited writing-code:1 and writing-tests:1; 17 Python PASS, 36 hooks PASS, two workflow policies PASS, `git diff --check` clean, Claude/Craft package canaries PASS. Shelf references remain opt-in; peer review did not treat shelf links as runtime consumers.

## Lead review

As lead/software engineer, I inspected every changed route and source-path identity, reproduced and fixed independent counterexamples, verified exact-base archive reconstruction plus current package UTF-8 bytes and selected content, and reran the full suite after the last code changes. I will ask for exact-SHA reviewer confirmation after commit; local tests do not authorize merge. A post-mortem is not triggered: this is a pre-integration draft change, not a shipped failure.

## Quantified claims

34 dispositions, 78 source/Claude/Craft fixtures, 198 sources, 804 artifact snapshots, 2,904 generated mappings, zero lifecycle completions. Kernel 6,995 characters / ≈1,749 estimated tokens; selected-content limits 12 items, 80,000 characters, 20,000 estimated tokens with visible kernel-only overflow. Full final suite: 17 Python, 36 hooks, two workflow tests; flat/Claude/Craft canaries and freshness all PASS. These are selected-content character/estimated-token/UTF-8-byte measurements, not observed runtime-token or ambient-load savings.

## Pre-mortem (before edits; Execute-mode review-only spoke)

- **Tiger — catalog corruption through raw writes:** generic Databricks/Delta keywords previously missed raw Parquet/Iceberg/ORC and catalog registration. Route operational write signatures to Unity Catalog, test positives and read-only/negation negatives; do not authorize a raw-path write by omission.
- **Tiger — project overlay leakage:** exact GitHub `siege_utilities` origin only; foreign host and bare owner/repo must receive global data stack without SU rules. Scope-check global operational source and generated package text; keep legacy compatibility pointer non-routed.
- **Tiger — broad noun routes:** engine mentions in prose/visualization and isolated Scala files must not masquerade as operations. Pair action with technology per clause, reject read-only/negated clauses, require Spark/Databricks evidence for Scala, and preserve kernel-only unknown/ambiguous/overflow.
- **Paper tigers:** exact-host overlay, shelf rejection, and 12/80,000/20,000 budget already existed at base; extend tests rather than replace them.
- **Elephant — consumers and cost:** only exact GitHub SU repo is a verified overlay identity. All other production consumers remain UNKNOWN; inbound refs are not installations. Character/4 is a model, not measured runtime tokens. Packaged artifacts on disk are not automatically mounted. Transitive reference loads are unmeasured.

## Self-review and independent hostile findings

Two review-only Execute-mode spokes found a broken synthetic selector inventory, missing catalog signatures (including Spark/Hive-scoped `INSERT INTO`, with PostgreSQL/SQLite negatives), spatial-analysis routing loss, unpaired action/technology and multiline task headers, `.scala` over-selection, unconditional Python ETL stack, partial SU scope scanning, packaged baseline verification gaps, byte/character conflation, visualization/“how-to” false positives versus same-task concrete edits, SparkApplication CRD write qualifiers, stale paths, and missing Tier C floor for the verifier. Fixed each with dedicated fixture(s), expanded global scope scan, archive-based baseline package rebuild, separate UTF-8 byte measurements, doc corrections, and Tier C policy assertions. Requested focused re-review after these changes; reviewer acceptance remains separate from local green checks.

**Residual risks:** clause/action heuristics cannot infer every natural-language intent, and a named operational engine may still need user clarification in ambiguous prose. Unknown external consumers and transitive shelf references cannot be inferred from static links. This PR claims route-contract coverage for tested signatures, not production adoption or a reduction in ambient runtime load. Roll back as a single independent `develop` revert if selection changes prove harmful; previous `main` remains untouched.

## Exact-base versus current measurements

`catalog/data-scope-ledger.json` covers 34 sources: authored 311,812 → 311,763 characters (312,578 → 312,529 UTF-8 bytes); nested/flat/Claude packaged owned files 1,330,491 → 1,330,442 characters each, Craft 1,330,460 → 1,330,411. These are stored-source deltas, **not runtime savings**. Kernel remains 6,995 characters / ≈1,749 tokens. The 78 `catalog/data-scope-fixtures.json` prompts report each source/Claude/Craft selected path, chars, estimated tokens, and UTF-8 selected bytes; verifier reconstructs packages from the exact-base git archive and checks current generated files.

Examples (source selection excluding kernel): ETL unknown/0 → `pipeline-jobs` 5,755 chars/≈1,439 tokens; analysis unknown/0 → `analysis` 3,980/995; raw Iceberg catalog write unknown/0 → `unity-catalog` 7,743/≈1,936; PostGIS `spatial,coding,sql` 21,006/5,252 → `postgis,spatial,sql,coding` 31,071/≈7,769; exact SU PostGIS adds SU rules 42,357/≈10,591, foreign host stays global-only 31,071/≈7,769. Multi-route 51,350/≈12,839 → 61,415/≈15,356. Over-budget remains kernel-only with 13 prospective items / 148,198 chars / ≈37,054 tokens (no selected bodies loaded). ArcGIS and pure choropleth remain kernel-only; no shelf auto-selection.

## Verification

- 17/17 Python suites (16 baseline + new data scope) on modern Python; macOS `/usr/bin/python3` is 3.9 and cannot parse an existing 3.10+ test, so use supported Python (CI specifies 3.12).
- 36/36 hook suites; 2/2 protected workflow tests.
- `bin/build.py --check`, source reference/shelf checks, inventory/authority/lifecycle/kernel/progressive/risk/language/data freshness, generated Claude/Craft route canaries, flat layout, hook validation, and `git diff --check` passed.
- Generated authority: 198 sources, 804 artifact snapshots, 2,904 mappings; zero lifecycle completions. `dist/` ignored/untracked as intended. No deployment or installation was run.
