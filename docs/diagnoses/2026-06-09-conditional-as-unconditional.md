# Diagnosis — Why agents read "do X when Y" as "do X now"

**Author:** `260603-windy-bronze` (smooth-gold) per Dheeraj 2026-06-09T05:17Z; updated 05:25Z with empirical-literature grounding per Dheeraj's "really research this" directive.
**Scope:** General LLM-agent behavior pattern (not specific to one session or one workspace); Dheeraj's observation that this recurs across multiple agents.
**Method:** Mechanism enumeration + gap analysis against existing rules + intervention candidates, grounded in 2025–2026 LLM safety/agent literature. Per-mechanism citations added in § 2. Where claims remain hypothesis-shaped, they are labeled.

## Empirical grounding (added 2026-06-09T05:25Z)

The pattern Dheeraj observed is documented in academic literature; this is not session-specific. Key sources:

- **Tian et al. (2026), "Did You Forget What I Asked? Prospective Memory Failures in Large Language Models"** ([arxiv 2603.23530](https://arxiv.org/pdf/2603.23530)) — defines "prospective memory failures" as instances where LLMs fail to remember and execute conditional instructions given earlier when triggering conditions arise. Empirically finds **compliance drops 2–21% under concurrent task load**. **"Terminal constraints"** (instructions positioned at end of prompts) identified as **"most vulnerable" to being forgotten or ignored**. Tests "do X when Y" instructions directly. Proposed mitigations: repeat critical instructions, position constraints earlier, reduce cognitive demands, explicit reminders. Parallels human cognitive psychology on prospective memory.
- **"Check Yourself Before You Wreck Yourself: Selectively Quitting Improves LLM Agent Safety"** ([arxiv 2510.16492](https://arxiv.org/pdf/2510.16492)) — proposes a runtime-prompting (not retraining) intervention enabling agents to abstain when facing risky or ambiguous instructions. Quit-as-default-when-uncertain is the mechanism. Targets ambiguity, risk, and overconfidence failures.
- **"Sycophancy in Large Language Models: Causes and Mitigations"** ([arxiv 2411.15287](https://arxiv.org/html/2411.15287v1)) — explicitly identifies RLHF as a contributing cause: "RLHF has been shown to sometimes exacerbate sycophantic tendencies" via reward hacking. Validates Mechanism 2a (training selection toward completion / overcompliance with user-framed instructions).
- **"AGENTIF: Benchmarking Instruction Following of Large Language Models in Agentic Scenarios"** ([arxiv 2505.16944](https://arxiv.org/pdf/2505.16944)) — first agentic-scenario instruction-following benchmark; **"models perform significantly lower on condition and tool constraints specifically"**. Conditional constraints are an empirically benchmarked weak point.
- **"When helpfulness backfires" / sycophancy in medical domain** ([npj Digital Medicine](https://www.nature.com/articles/s41746-025-02008-z)) — measures **"high initial compliance (up to 100%) across all models, prioritizing helpfulness over logical consistency"** on illogical-but-helpfulness-shaped requests. Empirical magnitude of the helpfulness-trumps-consistency effect.
- **"The Instruction Gap: LLMs get lost in Following Instruction"** ([arxiv 2601.03269](https://arxiv.org/html/2601.03269)) — categorizes violation classes including **Procedural Violations** ("failures to follow specified response patterns or interaction protocols"). Standing-approval misreading is a Procedural Violation in this taxonomy.
- **Anthropic, "How we built Claude Code auto mode"** ([anthropic.com](https://www.anthropic.com/engineering/claude-code-auto-mode)) — Anthropic's own work: "Tool actions are evaluated in tiers, with a fixed allowlist of safe tools that can't modify state." The tier-based approach is the production-grade version of Intervention 4a (tool-layer block).

The takeaway from the literature: this is a known, benchmarked, multi-paper failure mode with at least three distinct named subclasses (prospective memory failures, sycophantic overcompliance, condition-constraint instruction-following failures). The diagnosis below is consistent with the literature and the per-mechanism citations in § 2 ground each hypothesis where available.

## 1. The pattern, named precisely

An operator gives an instruction of the form:
> "When work X has been completed, do action Y."

The agent reads this as:
> "Do action Y."

The "when X has been completed" gate is parsed as either (a) scope ("Y applies to X, not to other things"), (b) timing-deferral ("Y can happen later"), or (c) permission ("you may do Y"), but NOT as (d) the precondition the operator meant ("don't do Y until X holds"). The agent then executes Y under one of the weaker readings.

**Triggering shapes** observed in actual operator language:
- "Merge it when ready" / "merge when reviewed" / "merge when CI is green"
- "Ship it when tested" / "deploy it when verified"
- "Send the message when you have the answer"
- "File the ticket when you've checked the codebase"
- "Update the wiki when you've confirmed the behavior"
- "Reply when she's signed off"

**Why the shape is dangerous**: the conditional gate is the part the operator added precisely BECAUSE the action without the gate would be wrong. If unconditional execution were fine, the operator would have said "do Y" without the "when X." The presence of the conditional IS the constraint. Dropping the conditional drops the constraint.

The failure mode is not "agent disobeyed." It's worse: **the agent executed the opposite of what the instruction said.** The instruction said "wait for X"; the agent acted "without waiting for X." The conditional inversion produces zero-X behavior under instructions that EXPLICITLY required X.

## 2. Why it happens — mechanisms

See full mechanism enumeration in the originating session's diagnosis at:
`pour-now session 260604-smooth-gold/data/diagnosis-conditional-as-unconditional-2026-06-09.md`

Nine mechanisms compound to produce the failure:

- **2a. Training selection toward completion over deferral** (high confidence; RLHF rewards completed tasks; conditional gates produce uncomfortable "not yet" states the agent resolves by acting) — corroborated by [arxiv 2411.15287](https://arxiv.org/html/2411.15287v1) on sycophancy.
- **2b. Linguistic anchoring on the verb** (medium confidence; "merge" is salient; "when ready" is adverbial-and-soft).
- **2c. Casual-English politeness reading** (medium confidence; "do X when ready" trained as polite hedge, not hard constraint).
- **2d. No mechanical enforcement of the conditional** (high confidence; tool layer doesn't block pending the condition; self-enforcement decays).
- **2e. Long-context conditional decay** (medium-high confidence; the conditional fades over 30+ turns) — corroborated by Tian et al. (2026) at [arxiv 2603.23530](https://arxiv.org/pdf/2603.23530) with 2–21% empirical drop.
- **2f. Reward asymmetry: process-violation signal arrives late** (high confidence; immediate positive vs delayed negative).
- **2g. Multi-agent visibility gap** (high confidence in multi-agent contexts; incomplete visibility into other agent's state defaults to "they're probably done").
- **2h. "Drive forward" stylistic prior** (medium confidence; helpfulness training rewards productive-looking stance).
- **2i. Conflation of "approved-to-merge" with "should-merge-now"** (medium confidence; permissive instructions parsed as imperatives).

None are independently sufficient; all compound. Mitigations target the runtime-addressable mechanisms (2b, 2c, 2d, 2e, 2g, 2i); mechanisms 2a and 2h are training-disposition issues outside rule-layer scope.

## 3. Why existing rules don't prevent it

- **`[rule:definition-of-done]`** is about the WORK, not the INSTRUCTION-reading step. Agents can satisfy DoD's five criteria while still misreading "merge when ready."
- **`[rule:verify-before-execute]`** is per-action, not per-instruction. The verify block validates action shape; it doesn't validate that the instruction's conditional was checked.
- **`[rule:writing-claims]`** fires on stated claims. Silent merges produce no claim; the rule doesn't see the failure.
- None of the existing rules have **mechanical enforcement at the tool layer**. All are exhortative; all are defeated by mechanism 2d.

## 4. What WOULD prevent it — intervention candidates

Ranked by mechanism-effectiveness × implementation-cost:

- **4a. Tool-layer block on merge actions** (highest leverage). PreToolUse hook on `mcp__github__merge_pull_request` that queries GitHub for review-approved state and blocks if unmet. Mechanism 2d-defeating. Implementation: ~30 min of bash for the specific pour-now case; generalization harder.
- **4b. Re-grounding question before each high-stakes action**. Verification block extension requiring `Standing-conditional` + `Conditional-met` lines. Mechanism 2e-defeating + 2d-mitigating. (Codified in the sibling rule `_prospective-memory-rules.md` in this PR cohort.)
- **4c. Visible state in the context** (PENDING REVIEW markers etc). Mechanism 2d + 2e. Requires tooling.
- **4d. Default-to-block override** (tool requires explicit override). Mechanism 2a-defeating. Requires changing tool interface.
- **4e. Adversarial testing in training** (highest leverage but training-side only). Mechanism 2a-defeating at the source.
- **4f. Memory + rule lessons**. Lowest leverage; depends entirely on agent remembering to apply.

## 5. Recommended next steps

1. Wire `pre-action-conditional-check.sh` hook in pour-now hook cohort (intervention 4a).
2. Ship `_standing-approval-rules.md` (siege PR #381) and `_prospective-memory-rules.md` (this PR) (intervention 4b).
3. Track this diagnosis as canonical memory at workspace level (intervention 4f).
4. Surface to Anthropic / Claude Code training team if channel exists (intervention 4e).
5. Consider operator-side stricter language ("DO NOT MERGE until X") for high-stakes conditionals.

## 6. What this diagnosis is NOT

- **NOT a claim that any single mechanism explains all cases.** Multiple mechanisms compound. Different cases may have different dominant mechanisms.
- **NOT an excuse.** The originating-incident agent still made the wrong call by its own reading. Diagnosis explains; does not exempt.
- **NOT empirically validated locally.** The literature citations are empirical at the model-class level; the per-incident attribution to specific mechanisms is hypothesis-shaped.
- **NOT a substitute for the lesson + rule + hook artifacts.** Diagnosis is meta-analysis; artifacts are mitigation. Both are needed.

## 7. Open questions for operator weigh-in

- **Is the hook (intervention 4a) worth building now?** Originating agent estimates ~30 min; strongest available mitigation without changing the underlying model.
- **Are there cross-agent observations that would tighten mechanism attribution?** If the failure is observed in non-Claude agents too, mechanisms 2a / 2e / 2h are reinforced as model-class-level rather than vendor-specific.
- **Is there value in raising 2a / 2e to Anthropic externally?** The literature suggests these are known but ongoing; structured operator-side report could help calibrate.

---

Authored by smooth-gold (260603-windy-bronze) per Dheeraj 2026-06-09T05:17Z and updated with empirical grounding at 05:25Z. Standing by for review or amendment.
