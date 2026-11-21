---
name: think
description: "Understand a requested change and choose a proportionate implementation approach. Use for features, fixes, refactors and architecture decisions; keep preparation brief when the approach is clear."
allowed-tools: Read Grep Glob
---

# Think First

Understand the outcome, relevant facts and consequences, then do the work. Preparation supports delivery; it is not a separate permission ceremony.

## Procedure

1. Read the request and relevant existing code, tests and prior decisions. Verify premises that affect the approach against the actual target branch. For a bug, inspect related callers and siblings where the same failure could occur.
For substantive changes, retain concrete evidence of preparation in the existing task or review: relevant documentation/source references, the facts they establish, and how those facts affect the approach. A claim that documentation was consulted, a role label or an artifact-present flag is not proof. Check current authoritative documentation when correctness depends on unfamiliar or changeable external behavior; do not invent citations or research. Reuse valid evidence rather than rereading unchanged material for ceremony.

2. Choose the simplest approach that meets the goal. Record material assumptions, tradeoffs and how the result will be verified. A short note in the existing task or PR is sufficient; use [the design workflow](design-workflow.md) for larger changes. Do not invent alternatives or a formal document when the method is already clear.
3. Use [task evidence and lifecycle](task-evidence.md) to bind actual session/task identity and target scope where the host requires it. Account for test and tool execution effects as well as edited files. Advance the same task to implementing when ready.
4. Implement, run relevant checks, review and deliver under [`self-review`](../self-review/SKILL.md). Fix discovered prerequisites within the existing grant. Continue independent work if a particular action is unavailable.

## Before an edit versus before a commit

An edit requires the host's actual own-task scope and implementing status where enforced. Investigation files, pre-mortem files, junior/senior comments and proof of posting are not universal pre-edit prerequisites. Existing companions are historical evidence; their absence does not create a permission requirement.

Review risk determines proportionate validation and publication review, not an organizational hierarchy before every edit. Use [`self-review`](../self-review/SKILL.md) for that contract. [`investigate`](../investigate/SKILL.md) and [`pre-mortem`](../pre-mortem/SKILL.md) are optional tools when uncertainty or consequences justify deeper work, or when the operator expressly requests them.

## Task scope

Use the actual target clone/worktree as `repo_root` and actual absolute `scope_paths`; the session cwd does not establish ownership. Scratch execution belongs to its physical target as explained in task evidence. Another task cannot authorize or block this one. Authorized operational work may use an explicit task ID without a GitHub issue. Do not dispose unfinished work or widen scope to conceal a refusal. Task scope checks modeled targets; it is not an operating-system sandbox. Before running project scripts or tools with indirect effects, inspect the relevant code/configuration and confirm those effects fit the actual grant. Repository ownership does not by itself authorize global installation, deployment or destructive operations.

## Authority and completion

Existing task authorization covers ordinary implementation methods and repairs. Ask only for a material decision or authority that is actually missing; preserve explicit owner holds, protected operations and consequential external-action boundaries. A task-state file is not authority. Diagnose a refusal rather than retrying the same effect through another tool or actor. See [`strategic-agency`](../_strategic-agency-rules.md), [`autonomy`](../_autonomy-rules.md) and [`standing-approval`](../_standing-approval-rules.md).

Do not stop at a plan, status report, review handoff or completed preparation unit while eligible work toward the assigned outcome remains. Verify delivery in the intended environment; distinguish source readiness from deployed behavior.
