---
ticket_refs:
  - siege-analytics/claude-configs-public#814: PR A vocabulary (predecessor)
  - siege-analytics/claude-configs-public#828: PR self-review hook fixes (sibling)
  - siege-analytics/claude-configs-public#827: PR D (Fix work-item for I-shape rows)
---

# Pre-mortem — PR B+C combined

**Ticket:** R11-meta remediation PR B+C combined (fallback execution after 3x spawn orphan)

## Real Risk 1

**Severity:** MEDIUM
**Likelihood:** low
**Trigger:** six additions in one PR produce a diff too large for reviewer to hostile-pass without missing a preservation check.
**Mitigation:** reviewer's six preservation checks are pre-agreed and named; each check maps 1:1 to a specific file+section. Diff is prose-only, no code paths to trace.
**Fallback:** reviewer flags check-scope; coordinator narrows follow-up commit to address specific check.

## Real Risk 2

**Severity:** MEDIUM
**Likelihood:** medium
**Trigger:** self-review dogfood accidentally uses Trivial-* declaration despite PR touching ESM (skill/rule) code. PR A's own enforcement (siege-analytics/claude-configs-public#814) blocks merge until fixed.
**Mitigation:** self-review artifact template pre-planned as full authoring-against-state:6 inventory; no Trivial-* section drafted.
**Fallback:** if merge blocks, amend self-review to remove Trivial-* and re-push.

## Real Risk 3

**Severity:** LOW
**Likelihood:** low
**Trigger:** cross-references between six additions reference wrong file paths or wrong rule numbers (e.g., writing-rules:8 numbered wrong).
**Mitigation:** dependency-ordered writes (B3 first since B1/B2 reference it); verify writing-rules numbering against `_writing-rules-rules.md` HEAD before adding :8 (verified :1-:7 present, :8 available).
**Fallback:** amend commit with corrected cross-references.

## Real Risk 4

**Severity:** LOW
**Likelihood:** low
**Trigger:** ticket-propagation-guard blocks because a ticket cited in-body lacks a comment posted with the propagation metadata.
**Mitigation:** frontmatter `ticket_refs:` block declares each referenced ticket with a status. Marks referenced-only (predecessor/sibling/work-item) so guard sees intent.
**Fallback:** post short "referenced in PR B+C" comment on each cited ticket after PR opens.

## Paper Tiger 1

**Severity:** LOW
**Trigger:** worry that combining PR B and PR C creates a coupling problem for future rebases.
**Why it's a paper tiger:** no other in-flight PR touches these files (siege-analytics/claude-configs-public#828 was hook-only; siege-analytics/claude-configs-public#822 was `bin/` only; siege-analytics/claude-configs-public#825 was automations-only). Rebase risk empirical zero.

## Paper Tiger 2

**Severity:** LOW
**Trigger:** worry that fallback-execution content differs from what would have shipped had the impl session fired.
**Why it's a paper tiger:** the brief IS what the coordinator executes here — same six additions, same acceptance criteria, same reviewer preservation checks. Sonnet never fired so no drift possible; briefs to `260907-early-raven` (Opus PR B) and `260907-true-torrent` (Opus PR C) also never fired and are equivalent content.

## What did NOT get inventoried and why

- `bin/build.py --check` behavior against a new `skills/shape-space-audit/` directory: not measured before write. Risk is low — build.py handles new skill directories automatically per its established pattern (verified by presence of many skill/ subdirectories already).
- CodeRabbit review scope on a large skill-prose diff: not measured. Risk is low — prose-heavy diffs typically get PASS from CodeRabbit unless there's actual code lint issues.
- Whether `hooks/git/self-review.sh` enforces the new `## Adversarial shape audit` subsection at push time: not measured. Enforcement is planned per B1 body but implementation is a v1.1 follow-up; this PR ships the discipline, hook enforcement lands separately. Judgment-enforced via reviewer's bounded hostile pass at PR time.

## Rollback plan

`git revert <merge-commit>` on `develop`, then optionally on `main` via promotion. Six additions unavailable; PR D can no longer cite `writing-code:8` shape table until re-created. Content in `plans/design-note-pr-bc-combined.md` is sufficient to reconstruct.
