# Self-review — #980 shelf integrity (Tier C)

Pre-mortem-artifact: plans/pre-mortem-980-shelf-integrity.md
Hostile-review-artifact: plans/hostile-review-980-shelf-integrity.md

## Assumptions

Working as: engineering maintainer for `siege-analytics/claude-configs-public`. Goal source: [#980](https://github.com/siege-analytics/claude-configs-public/issues/980), its audit comment, and [epic #962](https://github.com/siege-analytics/claude-configs-public/issues/962). Exact base `develop` 022fb81; only PR to `develop`. Scope: source shelf metadata, integrity checks, truthful content repairs, CI validation, and regenerated source-hash catalogs. No runtime resolver change.

## Peer review

Independent hostile reviewer: `sessions/261013-brave-torrent/data/hostile-review-980.md`, verdict **CHANGES_REQUIRED**. Four findings (angle/reference-style link bypass, prose orphan bypass, archival owner evidence, negated example false positive) were accepted and patched. Dispositions and residual caveats: `plans/hostile-review-980-shelf-integrity.md`. Independent focused re-review (`sessions/261013-polished-leaf/data/re-review-980.md`) found three residual semantic gaps; all accepted and patched with negative fixtures (bare backtick orphan, contradictory owner section, and `but read` target). Re-review of these latest deltas remains an open external check, not claimed as accepted. Initial reviewer could not run tests under read-only permissions; this author ran the full matrix.

## Lead review

- 83 category/book inventory records = 12 single evidenced active non-shelf owners with same-section positive scoped directives + 71 reasoned quarantines; root meta-router excluded. Four one-byte retained placeholders have explicit exceptions; substantive supplemental references link from the same book. No source deleted or canonicalized without link migration.
- The scope is reversible with a single feature-commit revert on `develop`; no consumer releases, deployment, installation, publish job, or resolver changed. Quarantined entries remain non-routable. A future owner needs a real active skill's explicit consultation path, not a shelf-router reference.
- Main risk: path validation is intentionally targeted to actionable Markdown `.md` references; it is not a universal parser and does not inspect dynamic or non-Markdown assets. Four one-byte empty placeholders remain tracked but promise no content.

## Quantified claims

- **14 Python suite files** (12 existing + 2 new negative-fixture suites), **36 hook suite files**, **2 workflow policy suite files** passed under Python 3.13 after hostile repairs. `build.py --check`, `sync-skill-references.py --check`, authority, inventory, lifecycle, kernel, review-risk, progressive metrics, both new checks and `git diff --check` passed after an ignored local `dist/` build. CI uses Python 3.12.
- Tracked shelf bytes: **6,064,932 → 6,068,649, +3,717 bytes** (storage increase, not runtime savings). Five canary resolver load sets and `selected_content` identical against base. Three actual hook injections: generic **7,364 → 7,364**, Python review **7,464 → 7,464**, spatial **7,438 → 7,438** bytes. Observed injected delta **0 bytes** in these scenarios, not all possible prompts. An explicit `shelves--geospatial` request still selects **zero shelf sources** even though its wording also matches the ordinary spatial route.
- Four reviewer findings have direct negative/positive fixtures; missing angle/ref-style links, prose-only and nested orphans, archive-only owners now fail, while explicitly negated/fenced examples and upstream URLs pass.

Unresolved question for reviewer: whether a future source syntax beyond supported Markdown links/backticks warrants a separately scoped parser extension. Do not imply comprehensive proof from this bounded guard or canary.
