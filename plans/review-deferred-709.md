---
propagation-deferred: review-deferred artifact for PR #725 / ticket #709; the deferral itself is the propagation record
---

# Review deferred: #709 (PR #725)

## What was reviewed by whom

- long-swan (260525-long-swan, Opus 4.7): self-review at `plans/self-review-709.md` covers the diff and the assumptions carried from bright-gust. Junior + Senior sections written.
- bright-gust (260831-bright-gust, Opus 5): authored the primary implementation. Its trajectory (design + pre-mortem + fact-sheet + test-run PASS) is in-tree.

## What remains unreviewed and why

External hostile review NOT delivered. Cross-provider dispatch failed in all four ladder steps for #709 during the same session:

- **Step 1 (same-provider respawn):** claude-max/Opus 5 spawns orphaned 4 times in the 90 minutes preceding this ticket (broad-crane, soft-peak orphaned on epic-682 successor attempts; hostile-review siblings also orphaning consistently). Rate-limit residue from bright-gust's Sep 3 00:06 CDT death (spent $177 on 4837 messages) has not cleared 12 hours later.
- **Step 2 (different-provider respawn):** chatgpt-plus/GPT-5.5 attempt (misty-vista) died at 10:42 CDT with `expired_oauth_token` and `errorCanRetry: false`. Source needs re-auth in Craft Agent workspace UI. Operator not available to re-auth immediately.
- **Step 3 (cross-review MCP):** `mcp__cross-review__list_providers` returns only `openai`. `mcp__cross-review__review` against openai returns `credit_balance_exhausted` on all four models (gpt-4o, gpt-4o-mini, o3, o4-mini). Anthropic + Google 1Password items don't exist.
- **Step 4 (this artifact):** deferring per the just-merged #720 protocol.

The PR (#725) is doc-only on the skill file plus a comment cleanup on the guard hook. Substantively-low blast radius. Test scenarios (5/5) pass at branch head. But the design's central claim — that the two keys (`findings`, `verifiedShapes`) are semantically distinct and both required — has NOT been independently challenged. A reviewer could reasonably attack that claim from angles the author did not anticipate.

## Retry command

When claude-max rate-limit clears OR chatgpt-plus is re-authenticated OR OpenAI credits are added:

```
mcp__session__spawn_session name="Hostile review PR #725" \
  llmConnection="claude-max" model="claude-opus-5" \
  permissionMode="allow-all" \
  workingDirectory="/Users/dheerajchand/git/siege-analytics/claude-configs-public" \
  prompt="Hostile review of PR #725 (branch fix/709-investigate-gate-schema). Target: skills/investigate/SKILL.md diff + hooks/resolver/investigate-gate-guard.sh comment cleanup + hooks/_test/investigate_gate_schema.test.sh new scenarios. Read the design at plans/design-709.md and the pre-mortem at plans/pre-mortem-709.md before attacking. Follow skills/hostile-review/SKILL.md protocol. Cite by file:line. Post as PR comment."
```

Or via cross-review once credits land:

```
mcp__cross-review__review \
  file_path="/tmp/e682/wt709/skills/investigate/SKILL.md" \
  skill_slug="hostile-review" provider="openai" model="o3"
```

## Severity self-assessment

**LOW-MEDIUM.** The PR is doc-only on skill text + comment edits on a hook; the substantive change is documentation of an existing schema divergence, not a behavior change. Test scenarios verify the documented example passes the gate.

Attack surface a hostile reviewer might find:

- Are the two keys REALLY semantically distinct, or does the design overstate their separation to justify not renaming? A reviewer might argue the split is historical accident + partial coverage rather than intentional.
- The empirical-evidence table cites four signal files (#683, #704, #718, untagged). If any of those ticket references misidentifies the actual file's shape, the table is wrong. Author (long-swan) did not verify each cited file's contents same-turn — trusted bright-gust's fact-sheet.
- The guard-hook comment cleanup may inadvertently drop semantically load-bearing prose. Author trusted the diff's shape without a line-by-line review against the prior comment block.
- Ticket AC1/AC2 REJECTION is a design-level pivot; a hostile reviewer might argue the design misread the ticket and there's a middle-path (both keys documented AND one renamed to a common convention).

None of these are hard-blocking without external review. The `review-deferred` label surfaces that this PR shipped without one.

## Followup

- **Owner:** Dheeraj (operator) OR any successor session that inherits epic-682 responsibility.
- **Target:** re-attempt hostile review once ANY of {claude-max rate window resets, chatgpt-plus re-authed, OpenAI credits added}. All three are external to this session.
- **Sweep mechanism:** the just-merged #720 fix notes as followup "a scheduled sweep skill that retries deferred reviews." No sweep exists yet. Until then, the operator watches for the `review-deferred` label on the PR list.

## Reference

- Retry ladder canonical source: `skills/hostile-review/SKILL.md` `## Dispatch verification and orphan fallback` (merged via PR #720, 2026-09-03 09:44 CDT).
- Session-coordination companion: `skills/_session-coordination-rules.md` `## Orphan dispatch`.
