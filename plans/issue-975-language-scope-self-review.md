# #975 Tier C self-review — draft to develop only

Base: `b9b631988091fcabdc1c531087da57c5ca1a0419`; integration: draft PR to `develop`. No merge, ready, main, release, deploy, or install.

Pre-mortem-artifact: plans/issue-975-language-scope-premortem.md
Hostile-review-artifact: plans/issue-975-language-scope-self-review.md#peer-review

## Assumptions

Only the exact GitHub Siege Utilities origin is verified. A source reference, content score, filename, or QML application name is not a runtime consumer. Resolver selection loads SKILL.md/rules metadata, not all companion references; references remain on demand. Distinct lifecycle purposes remain intact.

## Peer review

Independent **Hostile review — language scope** first returned NOT READY (native paths, spatial SU leakage, suffix and validator defects), then ACCEPT for the draft after targeted fixes and sandbox probes. The reviewer could not run tests under its mutation gate. Independent **Adversarial review — resolver** found slash shelf selection, explicit stack asymmetry, rule-token silence and rejected ticket-token ambiguity; after fixes its focused re-review returned ACCEPT with 38 fixture and resolver checks passing. Both roles were review-only; neither edited files or authorized merge.

## Lead review

I inspected the feature-branch diff, exact-base ancestry, generated output authority, foreign-host negatives, shelf isolation, same-slug source identities and all-or-nothing budgets. I fixed the two follow-up blockers, reran the full suites, and keep PR #991 draft to `develop`. The lead's acceptance is for reviewability, not release readiness.

## Quantified claims

39 classified sources, 51 source/consumer fixture cases, 198 sources, 804 artifact snapshots, 2,904 generated mappings; kernel 6,995 chars/1,749 estimated tokens, max injection 8,006 chars. Full rerun: 16/16 Python, 36/36 hooks, 2/2 workflow policies, package hook/resolver canaries, flat layout and freshness checks. Costs below are exact ledger values, not ambient savings; new packaged baselines were independently reproduced from an isolated exact-base archive build.

## Scope and review findings

- 39 classified language/framework/spatial-intersection sources, including 11 language shelf sources, four exact Siege Utilities project sources and one compatibility pointer. Only `github.com/siege-analytics/siege_utilities` is a known runtime project identity; all other host/repo consumers are UNKNOWN. Inbound references are not consumer evidence. No source retired or lifecycle-completed.
- Removed broad global Siege Utilities requirement; project-only review/reuse guidance lives in exact overlay. QML slug now optional generic review; old ChordLibrary/MuseScore text retained as non-prescriptive `reference.md` with UNKNOWN identity. Vue reset/Sentry/skipToast are examples conditional on target policy.
- Scoped global spatial SU imports/backlog snippets and referenced historical examples to exact origin. Follow-up F1 removed the unconditional GeoPandas quick-start import, clarified Sedona's exact-host runtime section, and corrected README's stale global preference. `language-scope.py` now rejects ungated imports/prescriptions in reusable-global authored and consumer package content; foreign-host selected files are tested in source, Claude Code and Craft Agent forms. This touches the spatial intersection necessary to prevent #975 leakage; new Scala-on-Spark/data routing belongs to #976.
- Explicit DRF, React+TypeScript/TSX, Vue/Pinia, Rust routes stack narrowly. Follow-up F2 resolves typed tokens by concrete `(kind, slug)`/source identity: colliding Python, React and DRF rules versus skills load distinct files; wrong-kind tokens reject, untyped slash/prose retain deterministic winners, and each selected concrete file counts toward the budget. Consumer manifests retain all source identities and synchronize legacy slug winner costs with packaged bytes. Rejected tokens cannot trigger prose routes or ticket conflicts. Visible `source_path` disambiguates same-slug rule/skill. Removed native `paths:` frontmatter only from ledger-covered sources so it cannot bypass manifest budgets; other sources' path metadata remains outside this batch.
- Earlier hostile and resolver reviewers blocked native paths, spatial SU leakage, suffix and generic REST overmatches, unverified baseline/ledger coverage, slash shelf, explicit stack, and rejected typed ticket ambiguity; these were addressed before the initial draft. Follow-up F2 re-review caught stale legacy `known` package costs after adding `known_by_source`; synchronized both maps and verified every packaged cost against bytes. **F1 spatial scope re-review: ACCEPT** by static inspection (reviewer's mutation gate prevented test execution); **F2 typed identity re-review: ACCEPT** (198/198 concrete entries and 193/193 legacy winners consistent in both consumer packages). Lead ran the full matrix and freshness checks under Execute. Neither review authorizes merge/release.

## Measured effects (chars / estimated tokens)

Source authored → packaged Craft Agent: compatibility rule `3131/783 → 695/174` authored; `3152/788 → 695/174` packaged. Exact project rule `10037/2510 → 11286/2822` authored and packaged. QML generic source `7320/1830 → 2337/585` authored; full packaged folder `7320/1830 → 9814/2454` because history is preserved as an optional reference. These are not ambient savings.

Fixture selection in Craft Agent package (before → after): generic unknown `0 → 0`; Python review `10843/2711 → 11852/2964`; exact Siege Utilities Python review `46758/11691 → 49016/12256`; foreign-host Python review `10843/2711 → 11852/2964`; DRF `10843/2711 → 32610/8155`; React+TSX `11301/2826 → 18629/4659`; Vue `0 → 9667/2417`; Rust `0 → 7367/1843`; multi-route `50803/12703 → 51977/12997`. Explicit shelf before erroneously loaded `10843/2711`, now unknown `0`. Over-budget remains kernel-only (requested `149199/37303 → 150373/37597`, loaded zero). A typed React rule+skill pair selects two concrete files at `20336/5085`; foreign spatial skills select `15628/3907` with no ungated SU instruction. Full per-source four-form authored/packaged costs and all 51 fixture selections are in the ledger and fixture catalog. Baseline authored/source selection is verified from git base; packaged baseline is attested from isolated exact-base build, not reproduced in CI.

## Residual risks / falsification

- Bare hostname/email with `.rs` or `.py` TLD can be mistaken for a source file; `vue.example.com` may activate Vue. Positive and negative suffix fixtures cover normal files, common hosts, and sourcemaps. Both false-positive classes remain budget-limited and do not authorize project overlays or shelves; clarify ambiguous tasks rather than assert project identity.
- Remaining native `paths:` on non-ledger sources (including data/Databricks, analysis, api-integration, library-api-evolution, ops, skillbuilder) are not claimed fixed here; data and Scala routing remain #976. The manifest is authoritative for this batch's selected sources, not an assertion about all native frontmatter in the repository.
- Distinct code review, exception, architecture, data, project and shelf responsibilities preserved. Avoid interpreting a missing source reference or a quality score as zero consumers.
- 12 selected items, 80,000 selected authored characters, 20,000 estimated tokens remain all-or-nothing; multidomain requests can hit over-budget and visibly fall back to kernel-only.

## Validation and dependencies

Regenerate after final tracked-source changes: `build.py --check` → `build.py` → `skill-inventory.py` → `generated-source-authority.py` → `progressive-loading-metrics.py` → `language-scope.py --write`, then all `--check` commands, package canaries and `git diff --check`.

Full current suite passed after final code change: 15 baseline + one new Python tests (Python 3.13 locally; CI Python 3.12), 36 hook tests, two workflow policy tests. An earlier attempt with macOS Python 3.9 passed 14/16 and failed two baseline tests using `str | None` annotations; the entire suite passed under Python 3.13. Hook dependencies: Bash, git, Python 3.12+, standard utilities (`find`, `sed`, `grep`, `mktemp`) available in CI; new ledger checks additionally require built dist, a full git history for exact-base `git show`, and standard-library subprocess/tempfile/json. Missing dist/git base fails loudly; no network or credential dependency. Rollback: revert this feature-branch PR on `develop` if future CI or review disproves scope claims.
