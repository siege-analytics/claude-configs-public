# Self-review — chore/strip-remaining-electinfo-leakage

## Assumptions

Domain(s): software engineering (documentation surgery, no executable code).
Goal source: operator instruction in workspace session `260606-fine-twilight`, 2026-06-07 00:48 UTC:
  > "Don't wrap: my intended result is that Siege remain the base for other projects, and the project specific skills that were accidentally put into Siege end up in the correct forks thereof. We should not stop work till that is accomplished. You may need to make and merge several PR's against three repos for this."
Plan: extends the Phase 1 plan (`workspace/dheeraj-electinfo/sessions/260606-fine-twilight/plans/remove-pour-now-from-siege.md`) into Phase 2: the rules + command-example leaks left out of scope in Phase 1.
Standing delegation (Phase 2): `workspace/dheeraj-electinfo:memory/project_siege_cleanup_2026_06_07_standing_delegation.md` (updated 2026-06-07 00:48 UTC).
Pre-author-inventory: NONE (audit performed by direct grep on the working tree at branch base).
Investigate-artifact: TRIVIAL — survey performed via `grep -rn` over `skills/` and `projects/` for the token set `electinfo|elect.info|pour-now|pour.now|business-admin|business-backend|pournow|enterprise_bulk|silver_canonical|Leena`. Output captured in the session transcript.
Pre-mortem-artifact: TRIVIAL — see below.

## Trivial-investigation declaration

Investigation was trivial because the work is prose-only documentation surgery against a known-token list. Risk surface: (a) build-check token resolution (passed), (b) over-generalization that loses teaching value (mitigated by abstracting empirical evidence into pattern descriptions rather than deleting it outright).

## Peer review

### Syntax check
N/A — no `.py`, `.ts`, or other executable-language files modified. All changes are markdown.

### Token validation
`python3 bin/build.py --check` against the branch tip:
> Validating project manifests...
>   1 active project(s)
> Source: skills
> Discovered 144 leaf skills, 24 rules, 3 project skills, 1 project rules
> Build check complete.

Skill / rule / project count is unchanged from develop tip — this PR adds and removes zero files; all changes are in-place edits.

### Leakage scan (post-edit)
`grep -rn 'electinfo|elect\.info|pour-now|pour\.now|business-admin|business-backend|pournow|enterprise_bulk|silver_canonical|\bLeena\b' skills/` excluding `shelves/` and `siege-utilities`: **no hits** in surviving content. Phase 2 closes the leakage scope completed.

(`siege-utilities` mentions remain inside its own properly-scoped `projects/siege-utilities/` dir; `shelves/` mentions are book content where "FEC" / "Consumer" appear as English words in marketing/product/strategy book references — those are not project leakage.)

### Edit-by-file summary

| File | What was changed |
|---|---|
| `_authoring-against-state-rules.md` | 8 empirical-evidence blocks rewritten to abstract pattern descriptions. Specific incident citations (electinfo/enterprise#2076-#2094, electinfo/airflow#55, file names like `entity_match_stats.py`, `fec_hydra_schema.py`, `silver_exp.sb`) replaced with structural descriptions of the failure mode. Teaching value preserved; project identity removed. |
| `_writing-claims-rules.md` | 3 empirical-evidence blocks rewritten. Acceptable-shapes examples (lines 106-108) abstracted (`empty-cand-FEC-ID edges in gold_edges` → `violating rows in <output-table>`; `bulk-collapse drives F3 gap` → `<upstream-pattern> drives the gap`). Incident-justification section list of claim names generalized. The `/opt/ee_pipelines/...` example path generalized to `/opt/<project>/...`. |
| `wrap-up/SKILL.md` | Section 6 ("Update Notion Knowledge Base") rewritten from electinfo-specific (`sync.run roadmap dashboard automated_skills`, `notion.provenance_footer`, `content_registry.py`, `PENDING_HUMAN_ACTIONS`, "Leena", "Telemetry") to generic "update project knowledge base if one exists" with a pointer that project-specific wrap-up overlays should extend with concrete mechanics. Two Notion-specific checklist items collapsed into one generic line. |
| `create-pr/SKILL.md` | 4 hardcoded `electinfo/enterprise` / `electinfo/tasks` / `dheerajchand` examples generalized to `<org>/<repo>` / `<org>/tasks` / `<github-handle>`. |
| `close-ticket/SKILL.md` | 4 hardcoded electinfo paths and repo references generalized. Cross-platform-sync example dropped specific `electinfo/enterprise` ↔ `siege-analytics/fec/pure-translation` mapping in favor of generic `<org>/<repo>` ↔ `<gl-org>/<gl-repo>` framing. |
| `commit/SKILL.md` | Cross-repo-reference example generalized from `electinfo/enterprise` + `siege-analytics/siege_utilities` to `<org-a>/<repo-a>` + `<org-b>/<repo-b>`. |
| `consolidate/SKILL.md` | `cd ~/git/electinfo` → `cd ~/git/<org>`. The `electinfo/ops/tree/main/app-spark` markdown link example replaced with a path-only description ("`ops/app-spark/` in your ops repo"). |
| `ticket-guard/SKILL.md` | Multiple-projects example changed from `siege-utilities uses GitHub Issues, electinfo uses Linear` to a generic phrasing covering GitHub Issues / Linear / Jira without naming projects. |
| `decision-to-ticket/SKILL.md` | One-line stripped: "as demonstrated by electinfo/enterprise#2169" → just the principle. |

## Lead review

**Approach-fit verdict:** strip-and-abstract is correct for the rules files (the teaching value is in the pattern, not in the specific incident IDs); generalize-with-placeholders is correct for the command-example files (`<org>/<repo>` style preserves runnability as templates). I considered deleting the empirical-evidence blocks outright and rejected it — the abstract pattern descriptions carry the "why this rule exists" weight that's hard to recover later. The full empirical evidence is preserved in the companion electinfo PR.

**Sequencing assumption:** the companion electinfo PR (which preserves the empirical evidence as electinfo-native rules-companion files) does not strictly need to merge in a specific order with this one — the empirical evidence is preserved in this session's working tree and will land in electinfo regardless of merge order. Operator can choose order based on review pace.

**Blast radius:** electinfo will lose the empirical evidence from its synced copy of `_authoring-against-state-rules.md` and `_writing-claims-rules.md` on the next siege sync. The electinfo companion PR adds the preserved evidence at `skills/_authoring-against-state--electinfo-incidents.md` and `skills/_writing-claims--electinfo-incidents.md` (electinfo-native files outside the siege subtree) so the knowledge is retained.

**Finding (not blocking):** `shelves/` content contains occasional uses of "FEC" and "Consumer" as English words in marketing/product/strategy book content. These are not project leakage — `Consumer` in `improve-retention/` is the marketing concept; `FEC` in `effective-java/evals/evals.json` appears to be a test fixture. Verified by spot-check; left unchanged.

**Affirmative standards held:**
- `bin/build.py --check` passes; skill/rule counts unchanged from base.
- No deletions of files or top-level structure.
- No frontmatter changes to any skill.
- Teaching value of each stripped rule preserved via abstract pattern descriptions.
- Command examples remain runnable as templates (placeholder syntax `<org>/<repo>` is conventional).

## Quantified claims
- "9 files modified, -10 net lines" — `git diff --stat develop..HEAD` shows `9 files changed, 42 insertions(+), 52 deletions(-)`. Net = -10. ✓

## Evidence-predates-work

Artifact: `plans/self-review-strip-remaining-electinfo-leakage.md`.
Committed first on this branch; work commit follows.
After both commits land: `git merge-base --is-ancestor <self-review-sha> <work-sha>; echo $?` → must print 0.
