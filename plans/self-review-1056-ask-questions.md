---
ticket_refs:
  - siege-analytics/claude-configs-public#1056: comment posted (design note, investigation, pre-mortem, junior/senior; hostile review and design revision)
---

# Self-review: ask-questions operator question protocol (#1056)

## Assumptions

Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket siege-analytics/claude-configs-public#1056 (operator directive of 2026-10-18 20:37 CDT, quoted in the ticket), the 2026-11-06 wording relayed by the Siege Utilities Hub, and the operator's 2026-11-06 12:59 CST clarification relayed by the Siege Utilities Hub; all three are quoted verbatim in skills/ask-questions/SKILL.md.
Goal source verification: BLOCK, with the exemption below. The first version of this artifact recorded "Manual PASS". That was wrong: the gate had refused `bash scripts/discipline/evaluate-ticket.sh` as opaque execution, and the hand-applied rubric left out the /think design-note-reference criterion. The evaluator itself, run as `./scripts/discipline/evaluate-ticket.sh 'siege-analytics/claude-configs-public#1056'` on 2026-11-06, exits 2 and prints: "BLOCK: ticket siege-analytics/claude-configs-public#1056 has gaps before it is fit for execution: - no /think design-note reference (need 'plans/think-*.md' path, 'Design: <path>' line, or inline '## Design' section)". That is its only gap. See "## Exemption: /think design-note reference" and https://github.com/siege-analytics/claude-configs-public/pull/1216#issuecomment-6698946100.
Plan reference: https://github.com/siege-analytics/claude-configs-public/issues/1056#issuecomment-6693026157 (revised by https://github.com/siege-analytics/claude-configs-public/issues/1056#issuecomment-6693399043)
Pre-author-inventory: plans/self-review-1056-ask-questions.md#pre-author-inventory
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1056#issuecomment-6693026157
Pre-mortem-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1056#issuecomment-6693026157
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1056#issuecomment-6693399043
Project-contribution: one routable, canonical procedure for asking the operator questions as a survey, so no agent or hub leaves the operator waiting between questions, and no rule text competes with it.

## Exemption: /think design-note reference

Reason:
- The design note exists on #1056 as a ticket comment, not in the issue body. The evaluator scans only the body.
- `skills/think/design-workflow.md` Step 7 and "Artifact destination" make the ticket comment the canonical copy of the design note.
- So the criterion's intent is met: a durable design, written before implementation and findable from the ticket. Only its body-location form is not.

Evidence:
- https://github.com/siege-analytics/claude-configs-public/issues/1056#issuecomment-6693026157 was created 2026-11-06T19:02:44Z. It contains `## Design note`, `## Investigation` and `## Pre-Mortem`.
- https://github.com/siege-analytics/claude-configs-public/issues/1056#issuecomment-6693399043 was created 2026-11-06T19:21:30Z. Its "### Design-note revision" records the operator's 12:59 CST clarification.
- Both comments predate the first work commit, 3f381b7, committed 2026-11-06T13:22:36-06:00 (19:22:36Z).
- The evaluator reports no other gap.

Falsification: this exemption is wrong if either comment lacks the cited design content, if either comment's created_at is later than 3f381b7's commit time, or if the evaluator, rerun on the unchanged issue body, reports any gap other than the /think design-note reference.

## Pre-author inventory

Contact points checked on origin/develop 1cd83f95 before authoring:

- Config state: `catalog/resolver-manifest.json` has 33 routes. Matching is per clause with case-insensitive alphanumeric-boundary phrases (`bin/resolve-load-set.py:48-87`). A route without `verbs` is one clause, so an exclude term anywhere in the prompt suppresses it. `validate_manifest` rejects a slug missing from the inventory (`:102-112`).
- Data shape: a new top-level skill is not in the frozen lifecycle bootstrap, so it needs `tier`, `owner`, `status`, `last-reviewed` and `verification` (`bin/skill-lifecycle.py:68-124`, `:400-402`). The YAML 1.1/1.2 frontmatter check requires the date to be quoted.
- Topology: develop 1cd83f95; `git log origin/develop..origin/main` lists one merge commit (9f47b03), which Root owns. This branch is cut from develop only.
- Competing text:
  - session-coordination:5 had per-slice release and question grouping.
  - strategic-agency:4 had its own short format.
  - autonomy:2 step 4 resumed work before the next question.
  - autonomy:3 put questions into tickets with its own format.

## Design

- `skills/ask-questions/SKILL.md` is the single procedure. It quotes all three operator statements. The 12:59 clarification is authoritative for how the hold is read.
- The procedure runs as a survey:
  1. Show the full list once.
  2. Ask one question per turn, with context, choices, pros and cons, a recommendation and a default.
  3. Go straight to the next question. The next question preempts background work.
  4. Between answers, do not route answers, update tickets or start work on them.
  5. After the last answer, summarize, then route and act on everything in one batch.
- Running work is never frozen or paused, including the tasks the questions are about. Silence is never an answer. The default is the recommendation.
- Route `ask-questions` (priority 80):
  - Terms: "ask questions", "ask me questions", "ask your questions", "ask all your questions", "decision questions", "one question at a time".
  - Exclude terms: "don't/do not ask questions", "don't/do not ask me questions", "no questions".
  - Bare "ask me" is not a term because it matches permission phrases such as "ask me before you push".
- session-coordination:5 defers to the skill and keeps only the hub rule: no answer routing or answer-based briefing until the survey is finished, with running work unaffected.
- strategic-agency:4 and autonomy:3 defer the question format and sequence to the skill. autonomy:2 step 4 sends the next question first.

## Test plan

- `bin/_test/resolve_load_set_test.py`:
  - 7 positive phrasings load `ask-questions`. They include the ticket's falsification prompt "use the ask questions skill" and two operator-correction prompts that contain "without asking" and "Don't ask them".
  - 5 negatives stay out: an unrelated prompt, "ask me before you push", a different-route prompt, prose about survey questions, and "don't ask questions, just do it".
  - The explicit `[skill:ask-questions]` token loads exactly the skill.
- Mutation check: pointing the route at another skill turns the test red at the first positive assertion; restoring it turns it green.
- The real CLI (`bin/resolve-load-set.py`) with the real inventory selects `skills/ask-questions/SKILL.md` for "use the ask questions skill" and nothing for "write a friendly greeting".
- `bin/validate-local.py --mode refresh` (generators plus every CI freshness check) and `--mode full` (the CI validation job's run steps), using a venv with the pinned PyYAML 6.0.3.

## Peer review

- Syntax check: the one changed `.py` file (`bin/_test/resolve_load_set_test.py`) parses and runs: `resolve_load_set_test: PASS`.
- Frontmatter: `bin/build.py --check` validated 199 skill/rule headers. `bin/skill-lifecycle.py --check` reports "1 complete, 198 legacy exceptions"; `ask-questions` is the complete record.
- Generated artifacts were regenerated with the repo tools, never by hand. `kernel-budget.json` and `review-risk-metrics.json` regenerated byte-identical.
- writing-prose and writing-code: the first version claimed "added lines contain no non-ASCII characters". That was false. The cross-family review's `bash skills/detect-ai-fingerprints/scan.sh --pr 1216` at a8aaa07 exited 1 with 4 findings:
  - three U+2192 arrows in this file's Quantified claims, now `->`;
  - an inherited unbounded `subprocess.run` in `bin/_test/resolve_load_set_test.py`. Every child now runs through `run_bounded` with a finite timeout. A test proves that a non-returning child is stopped within the bound, and removing the timeout turns that test red.

  The rerun result for the new head is recorded in the PR.
- writing-claims: counts below come from the actual runs.

## Lead review

- Class, not instance: competing question text was found and resolved in four places, not just the one the ticket named (see Pre-author inventory).
- Approach fit: this is a new task skill plus deferral, as the ticket's Goal 1-3 requires.
- Blast radius: one additive route with no exclusive group. Existing route assertions still pass. Four rule paragraphs are reworded to defer to the skill.
- Sequencing: the change takes effect only after a develop to main promotion and the exact-main install. The install is paused pending #1110.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| H2-3 | P3 | think step 5 could be read as allowing action on mid-survey answers | noted; the skill governs the answers it collects; think left unchanged |
| H2-6 | P3 | A curly-apostrophe "don't ask questions" is not excluded | noted; a false load costs one small skill; keeps the manifest ASCII |
| L2 | P3 | Enforcement is judgment-only | noted; out of scope per the ticket; `_coverage.md` names the scanner |

## Quantified claims

- "33 routes" -- `git show origin/develop:catalog/resolver-manifest.json | jq '.routes | length'` -> 33
- "199 skill/rule headers" -- `python3 bin/build.py --check` -> "199 skill/rule header(s) validated"
- "1 complete, 198 legacy exceptions" -- `python3 bin/skill-lifecycle.py --check` -> "skill lifecycle: current (1 complete, 198 legacy exceptions)"
- "7 positive / 5 negative phrasings" -- the two prompt tuples in `bin/_test/resolve_load_set_test.py` (#1056 block)

## Rework ledger

| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| skill-inventory rejected unquoted `last-reviewed` date | YAML 1.1/1.2 quoting rule not checked before writing frontmatter | seconds | one regeneration | low |
| progressive-loading metrics stale after a `build.py --check` | generators run by hand out of refresh order | seconds | one refresh | low |
| operator clarification changed the hold from dependent work to answer routing | none; new operator input | n/a | skill, :5, CHANGELOG, RESOLVER rewrite | n/a |
| hostile rounds 1 and 2 | competing text in autonomy and strategic-agency not grepped by name at design time | minutes | two edit rounds | medium |
