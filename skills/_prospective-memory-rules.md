---
description: Always-on. Standing conditional instructions ("do X when Y") decay over the trajectory; compliance drops 2–21% under load (Tian et al. 2026). This rule names the mitigations: repeat the conditional in each verification block; re-quote standing constraints at decision points; treat self-checks as cognitive-load-dependent and prefer mechanical hooks where available. Sibling to `[rule:standing-approval]` which defines how to PARSE the conditional; this rule defines how to RETAIN it.
---

# Prospective Memory

A standing instruction with a conditional gate — "merge when reviewed," "ship when CI green," "send when she signs off" — is a **prospective memory** task: the agent must hold the conditional in active attention and only execute when the condition fires later in the trajectory. LLMs are empirically poor at this.

[Tian et al. (2026), "Did You Forget What I Asked? Prospective Memory Failures in Large Language Models"](https://arxiv.org/pdf/2603.23530) measures compliance drops of **2–21%** under concurrent task load, with **"terminal constraints" (instructions at the end of prompts) most vulnerable** to being forgotten or ignored. The failure mode parallels human cognitive psychology on prospective memory: the harder the trajectory loads working attention, the more likely the conditional gate decays into a soft suggestion.

The sibling rule `[rule:standing-approval]` defines how to PARSE a "do X when Y" instruction — what "Y" means, what the gate requires. This rule defines how to RETAIN the parsed instruction over a long trajectory so it actually fires at execution time. Both are needed; either alone is insufficient.

## The four rules

**prospective-memory:1. Repeat the standing instruction's conditional in every covered action's verification block.** When `[rule:verify-before-execute]` fires on an action covered by a standing instruction (merge, push, send, deploy), add a `**Standing-conditional**` line to the block:

```
**Standing-conditional**: <quote the conditional from the standing instruction, verbatim>
**Conditional-met**: <evidence the condition holds; same-turn tool calls only>
```

The conditional is quoted verbatim, not paraphrased, because paraphrase is where the decay shows. If you can't quote the conditional verbatim, you've already lost it — re-read the originating message before acting.

This mitigation is from Tian et al.'s "explicit reminders" + "repeat critical instructions" finding.

**prospective-memory:2. Position constraints at the FRONT of any plan, not at the terminal end.** When authoring multi-step plans (in commit messages, PR bodies, agent-to-agent handoffs, task lists), put the conditional gate FIRST, not last. "After CI passes, merge" is more reliable than "merge — after CI passes."

This mitigation is from Tian et al.'s "terminal constraints most vulnerable" finding: instructions positioned at the end of long contexts are forgotten more often. Front-loading is mechanical defeat of position-based decay.

**prospective-memory:3. Cognitive load reduces compliance; mechanical hooks beat self-checks under load.** The empirically measured drop (2–21%) applies UNDER LOAD. When the agent is in a high-load state — long conversation, dense tool-call cycles, multiple parallel artifacts, time pressure — self-checks decay. Mechanical interventions (CI blocks, PreToolUse hooks, tool-layer permission tiers per Anthropic's [Claude Code auto mode](https://www.anthropic.com/engineering/claude-code-auto-mode)) do not decay.

The rule of thumb: if the conditional is load-bearing AND the trajectory is long-running, **wire a mechanical check** for it. Examples in the pour-now / siege framework: PreToolUse hook blocks on `mcp__github__merge_pull_request` when the PR's review-approved state is missing; CI gates that block merge until a named reviewer has signed off. The mechanical check is the artifact that survives the agent's cognitive load.

Self-checks remain necessary for novel conditionals where a hook hasn't been wired yet. They are not sufficient.

**prospective-memory:4. Quit-as-default-when-uncertain.** Per ["Check Yourself Before You Wreck Yourself: Selectively Quitting Improves LLM Agent Safety"](https://arxiv.org/pdf/2510.16492): when the conditional's status is ambiguous (you can't verify whether it holds, OR you can't remember the conditional verbatim, OR the standing instruction is from far enough back that recall is suspect), **the default action is to NOT execute and to ask**. Asking costs one message; the readiness-burgers-analogy failure mode costs a remediation conversation.

The siege existing rule `[rule:verify-before-execute]` § Evidence requires same-turn tool calls for corrections. This rule extends the principle to standing-conditional checks: same-turn verification or no action. If the verification can't be produced in the same turn, the action does not happen.

## What this rule is NOT

- **NOT a directive to re-quote every instruction in every verification block.** Only standing conditionals — instructions that carry into future actions via a "when X" gate. A one-shot user instruction in the immediately preceding turn is not a standing conditional; the verify block already covers it via Standards/Intent.
- **NOT a substitute for the hooks.** Mechanical enforcement (rule 3 above) is the strongest mitigation. The verification-block additions (rule 1) are the second-best when no hook is available. Don't read the rule as "the verify block alone is enough."
- **NOT applicable to instruction following at the per-turn level.** Per-turn instructions ("read file X then summarize") are not prospective memory tasks — they execute in the immediate trajectory. This rule applies specifically to standing instructions that gate FUTURE actions on FUTURE conditions.

## Relationship to other rules

- **`[rule:standing-approval]`** — defines how to PARSE a "do X when Y" instruction (what "ready" means; gate vs. permission vs. timing-deferral). This rule defines how to RETAIN the parsed instruction over a long trajectory. Standing-approval is the linguistic layer; prospective-memory is the attention/memory layer.
- **`[rule:verify-before-execute]`** — defines the per-action verification block. This rule extends the block with the `Standing-conditional` / `Conditional-met` rows when a standing instruction is in force.
- **`[rule:definition-of-done]`** — defines what "done" means structurally. This rule defines how to keep the done-ness checks live over time.
- **`[rule:writing-claims]`** — defines claim-grounding discipline. The `Conditional-met` evidence in this rule's block is the same shape as writing-claims:2's same-turn falsifying check.

## Why this rule exists

The originating session's 2026-06-09T05:17Z diagnosis (smooth-gold session `260603-windy-bronze`, attached as `docs/diagnoses/2026-06-09-conditional-as-unconditional.md` in this PR) catalogued nine mechanisms that compound to produce conditional-as-unconditional failures. The standing-approval rule (siege PR #381) addresses the parsing mechanism (mechanisms 2b, 2c, 2i). This rule addresses the retention mechanisms (2e, 2d, 2g):

- **2e (long-context conditional decay)** — directly addressed by rules 1 (repeat) and 2 (position).
- **2d (no mechanical enforcement)** — directly addressed by rule 3 (prefer hooks).
- **2g (multi-agent visibility gap)** — addressed by rule 4 (quit-when-uncertain; ask rather than infer).

Mechanism 2a (training selection toward completion) is not addressable at the rule layer; it requires training-side intervention (see ["Sycophancy in Large Language Models"](https://arxiv.org/html/2411.15287v1) for the canonical analysis). The runtime mitigations in this rule do not fix the underlying disposition but reduce the surface area where it produces wrong actions.

## Empirical references

- Tian et al. (2026), "Did You Forget What I Asked? Prospective Memory Failures in Large Language Models," [arxiv 2603.23530](https://arxiv.org/pdf/2603.23530)
- "Check Yourself Before You Wreck Yourself: Selectively Quitting Improves LLM Agent Safety," [arxiv 2510.16492](https://arxiv.org/pdf/2510.16492)
- "Sycophancy in Large Language Models: Causes and Mitigations," [arxiv 2411.15287](https://arxiv.org/html/2411.15287v1)
- "AGENTIF: Benchmarking Instruction Following of Large Language Models in Agentic Scenarios," [arxiv 2505.16944](https://arxiv.org/pdf/2505.16944)
- "When helpfulness backfires: LLMs and the risk of false medical information due to sycophantic behavior," [npj Digital Medicine](https://www.nature.com/articles/s41746-025-02008-z)
- "The Instruction Gap: LLMs get lost in Following Instruction," [arxiv 2601.03269](https://arxiv.org/html/2601.03269)
- Anthropic, "How we built Claude Code auto mode," [anthropic.com](https://www.anthropic.com/engineering/claude-code-auto-mode)

## Attribution

Defers to `[rule:output]`. No AI / agent attribution in any artifact this rule applies to.
