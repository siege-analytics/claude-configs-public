# Self-review: skill inventory and metrics

## Assumptions
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: User-approved Skill Library Simplification Plan, 2026-10-12.
Goal source verification: Phase 0 explicitly requires a machine-readable inventory, human report, overlap/generated-copy diagnostics, token-cost report, and evidence-preserving unknown classifications.
Plan reference: Craft Agent plan `skill-library-simplification.md`, Phase 0.
Pre-author-inventory: existing `bin/build.py` discovery/scoring logic, `skills/`, `projects/`, token reference forms, and generated flat project naming.
Investigate-artifact: this document and the generated report produced by the implementation.
Pre-mortem-artifact: this document, Risks section.
Hostile-review-artifact: `plans/hostile-review-skill-inventory.md`
Project-contribution: creates the factual baseline needed to simplify safely without deleting low-scoring but valuable knowledge.

## Pre-implementation comprehension
Current behavior: the build discovers skills and rules and prints quality warnings, but there is no committed complete inventory showing source authority, tier, references, size, tests, ownership gaps, lifecycle, or overlaps.
Intended behavior: one deterministic command generates a stable JSON catalog and concise Markdown report; CI fails if committed inventory output is stale.
Steps: reuse repository discovery conventions; scan source files and references; compute conservative size/token estimates; classify only evidence-backed tiers; flag unknown owner/status/usage rather than inventing values; add fixtures and CI check mode.
Success criteria: deterministic output, no runtime behavior change, complete discovered source coverage, explicit unknowns, duplicate/source-copy findings, and green full build/hook suite.

## Risks

1. Treating routers/shelves as normal leaf skills can distort quality conclusions.
   Mitigation: record kind/path-based classification separately from score.
2. Heuristic ownership or usage claims can become false facts.
   Mitigation: use `unknown` unless committed metadata or direct references provide evidence.
3. Generated project copies can be mistaken for canonical sources.
   Mitigation: explicitly identify source/copy relationships and report unresolved ambiguity.
4. JSON churn can make every PR noisy.
   Mitigation: stable sorting, repository-relative paths, no timestamps.
5. Approximate tokens can be presented as exact.
   Mitigation: label the character/4 measure as an estimate.
6. The catalog can immediately become stale.
   Mitigation: `--check` mode in hosted CI.

## Senior adversarial checklist
1. The initial temptation is to equate low quality score with deletion; this PR must not recommend deletion automatically.
2. Observable result is reproducible catalog equality, not “better visibility.”
3. Build/runtime behavior must remain untouched.
4. Inbound references are not equivalent to runtime invocation and will be labeled accordingly.
5. Existing discovery and flat naming code will be read before implementation.
6. Work is isolated in `feat/skill-inventory-metrics` from synchronized develop/main.
7. Tests must include duplicate slugs, references, project sources, shelves, and stale-output failure.
8. The scanner covers the class of source items rather than a hand-maintained list.
9. Done means CI can regenerate and compare the catalog.
10. Full validation and hostile review will not be skipped because this is “only reporting.”

## Peer review
- Syntax: `py_compile` passed for generator and fixture under Python 3.14.
- Discovery: exact parity with `build.py` at 198 authoritative sources; no missing or extra sources.
- Output plan: derived from `build.py`; 198 sources and zero destination collisions.
- Determinism/freshness: repeated serialization is identical; tracked output self-reference is excluded; stale Markdown fails `--check`.
- Namespaces: same-named skill/rule references remain separate; duplicate shelf slugs and duplicate destinations fail.
- Project overlays: active project owners/tier/output paths are recorded; archived project sources are visible but excluded from outputs.
- Full validation: token sync, build check, full build, all package/hook validators, settings drift, policy fixtures, deployment fixtures, inventory fixtures, and all 32 hook scenario files passed.
- Hostile review: three rounds completed; all S1/S2 findings fixed in `plans/hostile-review-skill-inventory.md`.

## Lead review
Approach fit: inventory before reduction is the lowest-risk first step. Blast radius should be limited to reporting scripts, catalog artifacts, tests, and CI validation. Sequencing requires this baseline to merge before lifecycle metadata or kernel work.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| I1 | P1 | No deterministic committed inventory exists. | fixed: generated JSON/Markdown plus CI freshness check |
| I2 | P2 | Ownership, lifecycle, and runtime-use evidence are incomplete. | exposed as unknown; Phase 1 addresses metadata |

## Quantified claims
- “198 authored source items” — `python3 bin/skill-inventory.py && jq '.summary.item_count' catalog/skills-inventory.json` → 198.
- “665,558 estimated source tokens” — `.summary.estimated_tokens` → 665558; defined as `ceil(characters/4)`, not tokenizer-exact.
- “6 C, 18 D, 133 F” — `.summary.quality_grade_counts`; reproduces `build.py`'s existing general-skill rubric.
- “32 hook scenario files passed” — final validation loop → `HOOK_SUMMARY count=32 failed=0`.

## Rework ledger
| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| Owner parser absorbed later frontmatter | DOTALL regex was too broad | Low | Low | 1:1 |
| Rule references misreported as duplicate definitions | Identifier regex was not definition-anchored | Low | Low | 1:1 |
| Same slug assigned quality to skill and rule | Kind was omitted from score attachment | Low | Low | 1:1 |
| macOS `/var`/`/private/var` parity failure | Core library call did not canonicalize root | Low | Low | 1:1 |
| Hostile review found evidence/output/project gaps | Initial generator did not use build authority deeply enough | Medium | Medium | 1:1 |

## Evidence-predates-work
Artifact: plans/self-review-skill-inventory.md
First-added commit: `d4161ab7c13322657c9f81a557cbbb6aeafcb65b`
Work commit: subsequent inventory implementation commit
Verification: `git merge-base --is-ancestor d4161ab7c13322657c9f81a557cbbb6aeafcb65b HEAD; echo $?` → 0 before push.
