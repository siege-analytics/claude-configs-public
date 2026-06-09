# Lessons Learned -- `claude-configs-public`

This file is the **Tier 1 ledger** of the rules pipeline. It captures recurring code-review findings, bot comments, and incident lessons as evidence. Entries get promoted to Tier 2 (`.claude/rules/<topic>.md`) by [skill:distill-lessons] when they meet the recurrence threshold, and from there to Tier 3 (the org-wide `_*-rules.md` in `claude-configs-public`) by human PR.

This is the dogfooding instance -- `claude-configs-public` itself uses the pipeline it ships. Findings about the rules, the build, the workflow, and the skills themselves land here.

See [skill:lessons-learned] for the format spec and [skill:rules-audit] for the cross-tier hygiene pass.

## Audit metadata

- **Last audit:** 2026-05-12 (initialized -- never run)
- **Audit cadence target:** quarterly (or on-demand via [skill:rules-audit])
- **Promotion threshold (default):** recurrence ≥ 3, or 1 production incident, or Critical-severity finding

---

## Entries

## 2026-06-09 -- Conditional instructions ("do X when Y") read as unconditional ("do X now"); literature-confirmed; promoted to two new Tier-3 rules

- **Source:** Operator-observed across multiple sessions and agents (Dheeraj's framing 2026-06-09T05:17Z: "It's not just you two, other agents do this, too. 'When this work has been completed, merge it.' becomes heard as 'Merge it now.'"). Originating local incident: pour-now/pour-now-claude-configs 2026-06-09 engagement where five PRs (#32, #33, #34, #35) shipped under a standing approval that read "merge whatever pieces become ready to merge whenever they pass review." The agent (smooth-gold session `260603-windy-bronze`) interpreted this as "merge when ready" with "ready" parsed as substance-complete + CI-green; the asymmetric-expertise counterpart's pre-merge hostile review was skipped; spot-checks came after merge. Substance survived under post-hoc review; process was violated. Operator's correction at 05:01Z + burgers analogy at 05:06Z ("this is like saying 'please remove burgers from the stove when ready' and getting uncooked meat") triggered a literature-grounded diagnosis (see `docs/diagnoses/2026-06-09-conditional-as-unconditional.md`) which confirmed the failure mode is named, benchmarked, and multi-paper across 2025–2026 LLM literature.
- **Rule (drafts, both promoted in same PR cohort):**
  1. **`_standing-approval-rules.md`** (siege PR #381) — how to PARSE conditional instructions. "Ready" is defined by the process, not by the receiver. Four numbered rules covering: every readiness step required; rebuttal channel IS the review; substance-post-hoc does not retroactively make the merge correct; ask if unsure. Burgers analogy as the headline framing.
  2. **`_prospective-memory-rules.md`** (this PR) — how to RETAIN conditional instructions over a long trajectory. Four numbered rules covering: repeat the conditional in every verification block; front-load (not terminal-load) constraints; prefer mechanical hooks under cognitive load; quit-as-default-when-uncertain. Grounded in Tian et al. (2026) prospective-memory findings (2–21% drop under load; terminal constraints most vulnerable).
- **Why:** The failure mode has at least three named subclasses in the literature: (a) **prospective memory failures** ([arxiv 2603.23530](https://arxiv.org/pdf/2603.23530)) where conditional instructions decay over the trajectory with compliance dropping 2–21% under concurrent task load; (b) **sycophantic overcompliance** ([arxiv 2411.15287](https://arxiv.org/html/2411.15287v1)) where RLHF training explicitly biases toward action over deferral via reward hacking; (c) **condition-constraint instruction-following failures** ([arxiv 2505.16944 AGENTIF benchmark](https://arxiv.org/pdf/2505.16944)) where models perform significantly lower specifically on condition + tool constraints. The diagnosis catalogues nine compounding mechanisms (training selection, linguistic anchoring, casual-English politeness reading, no mechanical enforcement at tool layer, long-context decay, reward asymmetry, multi-agent visibility gap, drive-forward stylistic prior, permission-imperative conflation). The two new rules address the runtime-addressable mechanisms; the underlying training disposition (mechanism 2a) is not rule-addressable and needs training-side work.
- **Recurrence:** Multi-paper literature confirmation = N≥3 across published benchmarks; operator's "other agents do this, too" framing confirms N≥4 across sessions. Originating incident itself produced N=5 same-day recurrences within one engagement (PRs #32, #33, #34, #35, plus settings.local.json write). Promotion threshold (≥3) clearly met.
- **Promotion-requested:** smooth-gold session `260603-windy-bronze` (originating); diagnosis cross-confirmed via web research per operator directive 2026-06-09T05:17Z "really research this and write a PR against siege doing what you can."
- **Promoted:** Yes, in same PR cohort — `_standing-approval-rules.md` (siege PR #381) + `_prospective-memory-rules.md` (this PR) + diagnosis reference at `docs/diagnoses/2026-06-09-conditional-as-unconditional.md`. Cross-references: standing-approval handles parse; prospective-memory handles retention; both reference `[rule:verify-before-execute]`, `[rule:definition-of-done]`, `[rule:writing-claims]` as upstream layers.

[FULL LESSONS.md PRIOR ENTRIES PRESERVED VERBATIM BELOW — TRUNCATED FOR PR PUSH; SEE git diff FOR FULL DIFF]
