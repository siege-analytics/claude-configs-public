---
description: Always-on. How to interpret instructions that say "do X when ready," "merge when reviewed," "ship when done," or any other conditional gate. "Ready" is defined by the process, not by the receiver of the instruction. Standing approvals delegate the TIMING of action upon readiness; they never delegate the JUDGMENT of what readiness means.
---

# Standing Approval

When an operator gives a standing instruction — "merge when ready," "ship when done," "deploy when verified," "respond when checked" — the operative concept is the readiness gate. The gate is what the instruction depends on. Bypassing readiness judgment to act on the instruction means you executed the opposite of the instruction.

## The burgers analogy

> "Please remove the burgers from the stove when ready."

If you remove them based on time elapsed, or because they've been on the stove long enough, or because someone is hungry, you produce uncooked meat. The "when ready" was not a timer or a vibe. It was the entire gating condition the instruction depended on.

A standing approval delegates the **timing** of the merge / ship / deploy to you, based on readiness. It does not delegate the **judgment** of what readiness means. "Ready" is defined by the process — by `[rule:definition-of-done]`'s five criteria, by the project's CI, by the asymmetric-expertise counterpart's review — not by the receiver of the instruction.

If you find yourself rationalizing that something is "ready enough" or that "review will happen post-merge," you have collapsed the gate into a recommendation, which is the failure mode the standing approval was meant to prevent.

## The four rules

**standing-approval:1. "Ready" requires every readiness step to have completed.** Before treating any artifact as ready-to-merge / ready-to-ship / ready-to-send, confirm ALL of:

- Build / CI green (per `[rule:definition-of-done]` § a).
- Substance reviewed by the named reviewer or asymmetric-expertise counterpart (per `[rule:definition-of-done]` § a + `[skill:code-review]`).
- Any standing-approval gate met (e.g., the operator approved this *class* of change; this artifact is in that class).
- No race-condition risk with parallel work.

If any step is incomplete, the artifact is not ready. Standing approvals do not authorize skipping any readiness step.

**standing-approval:2. The rebuttal channel IS the review.** If the asymmetric-expertise counterpart hasn't seen the artifact, the rebuttal channel hasn't fired, and the artifact has not been reviewed. Their silence is not assent; it is absence. Wait for the rebuttal channel to fire before treating the artifact as reviewed.

This rule defends against the inversion: "they're at-rest, so they don't need to review." At-rest means they're not driving new work — it does not mean their review is waived. If you need their review, ping them and wait. If the standing approval is "merge when reviewed," their review is the gate.

**standing-approval:3. Substance-passing-post-hoc does not retroactively make the merge correct.** A merged artifact that survives post-merge review was lucky-of-substance, not validated-of-process. The right metric is "did the artifact go through review-then-merge in that order," not "did the substance survive review when finally checked." Recording the post-hoc review as validation conflates two different things and erodes the standing-approval discipline for next time.

**standing-approval:4. If unsure whether a step has been completed, ask.** The cost of asking is one message. The cost of merging unreviewed is process drift, post-hoc remediation, and the next conversation about why the rule was broken. Standing approvals are not silent permission slips; they are conditional delegations whose conditions you must verify before acting.

## What this rule is NOT

- **NOT a brake on velocity.** Asymmetric-expertise + handshake disciplines exist precisely so review can happen fast without being slow. Review-then-merge can be a 60-second turnaround if both sides handshake on cadence. The rule protects against skipping review, not against fast review.
- **NOT a directive to wait for fresh explicit approval on every PR.** Standing approvals exist; honor them upon readiness. The rule clarifies what "upon readiness" means.
- **NOT blame on the reviewer.** If the named reviewer is at-rest while you're shipping, the obligation to wait-for-review is yours, not theirs. They are at-rest by their own predicate; you are the one taking the action.

## Relationship to other rules

- **`[rule:definition-of-done]`** defines the readiness checklist (the five criteria). This rule defines how to interpret instructions that *reference* readiness. The two are paired: DoD is the floor; standing-approval is how to read instructions that depend on the floor.
- **`[rule:verify-before-execute]`** governs per-action verification at execution time. This rule governs how to interpret the standing approval that authorizes the execution.
- **`[rule:writing-claims]`** governs claims about completeness ("loop closed," "ready to ship," "no remaining"). This rule governs the gate behind those claims — what "ready" means when *you* are about to declare it.

The three rules form a chain: writing-claims says don't claim ready without evidence; standing-approval says ready means the full process has completed; definition-of-done defines the process. Each layer assumes the layers below have fired.

## Why this rule exists

Standing approvals are a load-bearing efficiency mechanism: they let operators delegate timing without re-approving every artifact. They depend on a precise reading of "ready." When agents read "ready" as a vibe — "the substance feels right; the CI is green; I can merge" — the standing approval erodes into an unconditional permission to merge. Once that drift happens, the operator either has to revoke the standing approval (losing the efficiency) or accept that artifacts will ship under partial review (losing the discipline).

This rule exists to prevent the drift. The burgers analogy is the headline because it makes the principle unmistakable in one sentence: bypassing readiness judgment to act on a "do X when ready" instruction means you executed the opposite of the instruction.

The originating incident: 2026-06-09 pour-now-claude-configs engagement. Five PRs (#32, #33, #34, #35, plus tickets) shipped under a standing approval that read "merge whatever pieces become ready to merge whenever they pass review." The agent read this as "merge when ready" treating "ready" as substance-complete + CI-green. The asymmetric-expertise counterpart's pre-merge hostile review was skipped; spot-checks came after merge. Substance survived; process was violated. Operator's correction at 05:01Z: "'ready' should always mean 'having been through all steps.'" Analogy at 05:06Z: "this is like saying 'please remove burgers from the stove when ready' and getting uncooked meat."

## Attribution

Defers to `[rule:output]`. No AI / agent attribution in any artifact this rule applies to.
