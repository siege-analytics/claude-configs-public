---
ticket_refs:
  - siege-analytics/claude-configs-public#487: design posted
---
# Pre-Mortem: #487 — Senior adversarial checklist and slow-is-smooth disposition frame

## What could go wrong

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | Disposition preamble is too long — agents skip it or context-compress it away | Medium | The slow-is-smooth frame never fires because the agent doesn't read it | Keep it concise (under 20 lines). The RESOLVER is already long; the preamble must earn its space with density, not length. |
| 2 | Senior adversarial checklist becomes cargo-culted — the agent fills in boilerplate answers to each question | High | The checklist exists but produces no insight, same failure mode as the current pipeline | This is inherently honor-system until mechanically enforced. The checklist's value is in the phrasing (presumptive, not binary). Whether it works depends on whether the agent takes the persona seriously. |
| 3 | Rework ledger is empty on every self-review because the Junior doesn't track rework as it happens | High | The ledger section exists but is never populated — invisible skip | The self-review hook could check for amend commits in the branch log and flag if the ledger is empty when amends exist. File as follow-up ticket. |
| 4 | TRIVIAL mechanical rejection is too broad — blocks legitimate trivial changes to .sh/.py files (e.g., fixing a typo in a comment) | Medium | False negatives block valid work, agent gets stuck | Define "executable change" as changes outside comment lines. Or: allow TRIVIAL for comment-only diffs but require a one-line declaration. |
| 5 | Deploy-after-hook-change pre-push check breaks pushes for repos that don't use build.py --deploy | Low | Hook fires in wrong repo context | Scope the check to repos that have a bin/build.py. Check for file existence before asserting deploy requirement. |
| 6 | Pipeline-gate footer becomes wallpaper — the agent sees it every turn and stops reading it | Medium | Reminder loses effectiveness through repetition | Acceptable cost. Even wallpaper creates a baseline awareness. The footer is cheap (one line, no gate). If it stops working, remove it — no dependencies. |

## What would make us revert

- Senior checklist produces false positives that block legitimate fast-path work
- TRIVIAL rejection prevents actual trivial changes (comment fixes, typo corrections)
- Rework ledger enforcement blocks pushes on legitimate no-rework branches

## Rollback plan

Each piece is independent. Revert the specific commit for the piece that breaks:
- Disposition preamble: revert the RESOLVER.md edit
- Senior checklist: revert the self-review SKILL.md edit
- Rework ledger: revert the self-review SKILL.md format change
- Pipeline-gate footer: revert the pipeline-state-guard.sh edit
- Completion criteria: revert the RESOLVER.md rule #9 expansion

No inter-dependencies between pieces.

## Pre-mortem verdict

Risk #2 (cargo-culting the checklist) is the biggest concern and is inherently
unmitigable by this ticket alone. The checklist's effectiveness depends on the
agent taking the Senior persona seriously. Mechanical enforcement of the
checklist's substance (not just its existence) would require a separate hook
that validates the Senior's answers against the Junior's description — which
is a much harder problem. This ticket makes the right answers visible; it
cannot make the agent give them honestly.
