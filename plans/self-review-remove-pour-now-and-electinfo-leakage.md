# Self-review — chore/remove-pour-now-and-electinfo-leakage

## Assumptions

Domain(s): software engineering (documentation surgery, no executable code).
Geospatial cross-cut: no.
Goal source: operator instruction in workspace session `260606-fine-twilight`, 2026-06-07 00:08 UTC:
  > "I want you to make a plan to surgically remove the skills that don't belong in siege skills and place them in pour-now"
  > "make sure elect-info specific skills aren't in siege, and if they are, surgically remove them and graft them into electinfo"
  > "I think 3a. ALso you have permission to merge."
Plan reference: `workspace/dheeraj-electinfo/sessions/260606-fine-twilight/plans/remove-pour-now-from-siege.md` (operator-accepted).
Standing delegation: `workspace/dheeraj-electinfo:memory/project_siege_cleanup_2026_06_07_standing_delegation.md`.
Pre-author-inventory: NONE (no prior inventory ticket; scope was determined by direct file survey of `skills/` at branch base).
Investigate-artifact: TRIVIAL — survey performed via `grep -lr` on the working tree, output captured in the session transcript and in the plan file.
Pre-mortem-artifact: TRIVIAL — see Trivial-investigation declaration below.

## Trivial-investigation declaration

Investigation was trivial because the work consists of (a) two whole-file deletions of skills whose canonical homes exist elsewhere, and (b) prose-only stripping of customer-specific content from three documentation files, retaining the generic skill content. Risk surface is the build-check, which validates token references — passed before each commit.

## Peer review (the Junior's checklist — mechanics, correctness, craft floor)

### Syntax check
Syntax check: N/A — no `.py`, `.ts`, `.vue`, or other executable-language files modified. All changes are markdown.

### Token validation
`python3 bin/build.py --check` run after every edit batch and after final state.
Final result: `Discovered 144 leaf skills, 24 rules, 3 project skills, 1 project rules. Build check complete.` (exit 0)
Down from 146 leaf skills pre-change — accounting for the two deleted skills.

### Cross-reference integrity
Two dangling-reference checks performed:
- `grep -rn 'pour-now-triage' skills/` → no hits in surviving content.
- `grep -rn 'notion-knowledge-base' skills/` → originally one hit at `skills/RESOLVER.md:102`, now removed.
Both index-level references were stripped from `skills/RESOLVER.md` in the same commit as the file deletions.

### Generic content preservation
Each of the three stripped skills (`vue`, `api-integration`, `unity-catalog`) retains its generic doctrine. Confirmed by reading each file end-to-end after edits:
- `skills/vue/SKILL.md` (186 lines, was 242): keeps Composition API, Pinia setup-store, route-guard contract principles, error-handling, TypeScript discipline, anti-patterns. Drops the pour-now `business-admin` two-organization split, pour-now Vue Deviations table, pour-now-triage cross-refs.
- `skills/api-integration/SKILL.md` (168 lines, was 180): keeps the error-envelope contract, JWT refresh-rotation pattern, multi-tenant header pattern (now generalized), tracing rules, SDK wrapper rules, webhook auth, silent-on list. Drops "Current state (pour-now):" framing, `pournow/urls.py` paths, pour-now wiki links, pour-now-triage cross-refs.
- `skills/unity-catalog/SKILL.md` (178 lines, was 186): keeps the catalog-first rule, correct-API examples, pre-flight checks, Spark session config skeleton, schema registration flow, checklist, broken-UC recovery. Drops electinfo-specific `enterprise_bulk.individual_contributions` examples (replaced with generic `analytics.daily_events`), electinfo k8s service hostnames, electinfo configmap reference, electinfo-history section, electinfo skill cross-refs.

### Deleted files
- `skills/pour-now-triage/SKILL.md` (165 lines) — canonical version exists at `pour-now/pour-now-claude-configs:skills/pour-now/triage/SKILL.md`. Verified file presence; the pour-now version is substantively different (better-scoped frontmatter, narrow `paths`, `user-invocable: false`, references own `PROJECT.md`).
- `skills/notion-knowledge-base/SKILL.md` (367 lines) — canonical version exists at `electinfo/electinfo_claude_skills:skills/update-notion/SKILL.md`. Verified files differ only in em-dash style and one `user-invocable: false` line; electinfo has the substantive content.

## Lead review (the Lead's adversarial pass — did the Junior actually solve this?)

Domain: software engineering / documentation discipline.

**Approach-fit verdict:** the stripping pattern is correct for `vue` and `api-integration` (each has a clear generic core surrounded by pour-now-specific framing). `unity-catalog` was a closer call — every concrete example was electinfo. The chosen approach replaces electinfo identifiers with `<placeholder>` style and drops the electinfo-history narrative; the resulting skill is leaner but stays useful as catalog-discipline doctrine. Alternative was to move the whole skill into electinfo and delete from siege — rejected because the rule itself (catalog-first writes) IS generic UC guidance that any consumer benefits from.

**Sequencing assumption that must hold:** the two follow-on PRs (pour-now-configs absorb, electinfo absorb of unity-catalog history) must merge AFTER this PR or the cross-link section in the absorbed content will reference a deleted siege skill. Operator is informed; PR descriptions will document the order.

**Blast radius:** any downstream consumer of siege that pulls `release/flat` will next-sync lose `pour-now-triage` and `notion-knowledge-base` from their flat output. Consumers known to exist:
- `electinfo/electinfo_claude_skills` — already has its own `update-notion`; will lose its leaked `pour-now-triage` (which it shouldn't have had anyway).
- `pour-now/pour-now-claude-configs` — has its own `skills/pour-now/triage/` plus the leaked `skills/pour-now-triage/` flat copy; will lose the flat leak.
Neither loss is functionality loss.

**Finding (not blocking — flagged for follow-up):**
- `skills/_authoring-against-state-rules.md` contains heavy electinfo-specific empirical citations (`electinfo/enterprise#2076-#2093, #2094, #2123, #2143, ...`, `electinfo/airflow#55`, `electinfo_claude_skills`). The rule itself is generic; the evidence is entirely electinfo. Out of scope for this PR (which targets skills, not rules per operator's wording) — flagged in PR description as next-pass cleanup.
- `skills/consolidate/SKILL.md` line 102 has a literal link to `https://github.com/electinfo/ops/tree/main/app-spark` as an "example" — borderline acceptable as a worked example; same disposition.
- `skills/decision-to-ticket/SKILL.md` line 147 says `as demonstrated by electinfo/enterprise#2169` — empirical citation; same disposition.

**Did I close the class or defer it?** Closed the SKILLS class (the scope operator named). Deferred the RULES + empirical-citations class to follow-up — that decision is explicit, ticketed in PR body, and surfaced for operator approval before any follow-up work.

**Affirmative standards held:**
- Build check passes (`bin/build.py --check`).
- No broken `[skill:slug]` or `[rule:slug]` tokens.
- No broken cross-file references to the deleted skill directories.
- Generic content of stripped skills remains coherent and self-contained (re-read end-to-end).

## Quantified claims

PR body / commit message numbers to verify:
- "delete 2 skill dirs (532 lines total)" — pour-now-triage (165) + notion-knowledge-base (367) = 532 ✓ (`wc -l skills/pour-now-triage/SKILL.md skills/notion-knowledge-base/SKILL.md` against pre-delete state in `main`).
- "3 surviving skills stripped, ~150 net lines removed" — `git diff --stat main..HEAD` shows `3 files changed, 74 insertions(+), 150 deletions(-)` for the surviving files. Net = +74 -150 = -76 (deletions exceed insertions by 76). I'll state "~150 lines stripped, ~75 net lines removed" in the PR body.
- "1 RESOLVER index entry removed" — confirmed via the single Edit call on `skills/RESOLVER.md`.

## Evidence-predates-work

Artifact: `plans/self-review-remove-pour-now-and-electinfo-leakage.md`
This file is committed FIRST. The work commit follows.
After both commits land, the verification chain is:
  `git merge-base --is-ancestor <self-review-commit> <work-commit>; echo $?` → must print 0.
This will be added to the PR body after both commits are pushed.
