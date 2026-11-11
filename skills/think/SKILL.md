---
name: think
description: "MANDATORY design-first gate. Enforces structured design before any code is written for a feature, refactor, or architecture change. Slash-invokable as /think; also enforced via the resolver before any non-trivial implementation. Do NOT skip this skill."
allowed-tools: Read Grep Glob
---

# Think First

Design before implementation. Existing task authorization can cover ordinary methods; it does not release an explicit owner hold or project sign-off. Use [`strategic-agency`](../_strategic-agency-rules.md) and [`autonomy`](../_autonomy-rules.md) to distinguish routine execution from missing material decisions, [`standing-approval`](../_standing-approval-rules.md) for readiness and role limits, and KERNEL K1 for scope. Do not ask the owner to repeat an authorization already given.

## Procedure

1. Read [the design workflow](design-workflow.md) before preparing the design. Preserve ticket fitness, accumulated knowledge, context and sibling audits, real alternatives, documentation/mission alignment, authorization verification and required posting.
2. Complete its required investigation then pre-mortem routing before implementation. Follow [`investigate`](../investigate/SKILL.md), [`pre-mortem`](../pre-mortem/SKILL.md) and applicable [`survey-context`](../survey-context/SKILL.md). A tier's mechanical minimum does not waive these authored preparation obligations.
3. Read [task evidence and lifecycle](task-evidence.md) before creating or changing signals. Bootstrap the host's own task in designing, prepare evidence, then transition that same task to implementing. Keep companions adjacent and exact session/task identity consistent.
4. For class-of-bug fixes or verifiable premise changes, also read [premise claims](premise-claims.md). Preserve canonical claims when updating or disposing a task.
5. Continue within the existing grant once applicable prerequisites are satisfied. Hold only dependent actions for genuinely missing owner decisions or actual holds; independent authorized work continues.

## Before an edit versus before a commit

The mutation gate requires an implementing gate owned by this session and task. Its effective tier is the higher of the target-path floor from `bin/review-risk.py` and the optional declared tier; a declaration can raise but never lower it. Unavailable classification fails closed to C:

| Pre-edit tier | Mechanical evidence |
|---|---|
| A | implementing task gate |
| B | A + investigate-gate with a finding + pre-mortem with a classified risk |
| C | B + junior/senior and artifacts-posted |

Commit review is a separate checkpoint owned by [`self-review`](../self-review/SKILL.md), with its own tiered artifact and trailer requirements. Tier B's commit-review format does not waive B's pre-edit evidence or the design workflow. A gate's existence does not prove approval.

## Task scope

`repo_root` is the actual target clone/worktree, not session CWD or the Craft configs workspace merely because it is the CWD; scratch under this session's `data/` uses the repository that physically contains it (see task evidence, "Gate metadata for scratch execution"). Declare actual absolute `scope_paths`; binding never widens scope. Another task's status cannot authorize or block this task. Use the host-resolved own `tasks/<stable-slug>/think-gate.json`; an authorized operational task may use an explicit task_id without a ticket or hash. Read task evidence for complete schema, path, companion and compatibility requirements. Never bypass scope rejection with root copies or another task's artifacts.

## When This Skill Applies

This skill is **MANDATORY**. It auto-triggers whenever you are about to:
- Add a new feature or capability
- Refactor existing code
- Make architectural decisions
- Change data models or schemas
- Touch more than 3 files
- Do anything where the approach isn't obvious

Complete the full design workflow and verify its applicable authorization before writing code. An existing task or standing approval can satisfy ordinary implementation authority; any design sign-off required by the owner or project must still be obtained. Do not skip preparation or invent a new approval checkpoint.

**Exemptions** (the ONLY cases where you may skip this skill):
- Changes to non-executable content only (markdown prose, comments with no functional effect, whitespace). Any change to `.sh`, `.py`, `.sql`, `.js`, `.ts`, or other executable code is non-trivial and requires the full pipeline: the Junior cannot classify code changes out of the pipeline. See #338.
- Tasks where the user has given detailed, specific, step-by-step instructions
- Pure research or exploration (use the Explore agent instead)

**Not exempt -- highest-stakes edits that require the full pipeline:**
- Skill files (`skills/**/SKILL.md`) -- these change the behavior of every future task
- Hook scripts (`hooks/**/*.sh`) -- these change what the pipeline enforces
- Rule files (`_*-rules.md`) -- these change the standards the pipeline evaluates against
- CLAUDE.md and project conventions -- these change how agents interpret the codebase

"Documentation-only edit" does NOT include skill/hook/rule edits. Changing a skill is changing the pipeline's behavior -- it requires think, investigate, and pre-mortem like any behavioral change. The recursive case (the pipeline editing itself) is the highest-stakes change because a broken skill silently degrades all future work.

## Iron Laws

1. **No code before design.** Not even "just a quick prototype." Prototypes become production code.
2. **No implementation during design.** Reading code to understand the system is fine. Writing code is not.
3. **Consider real alternatives.** Explain the selected method and tradeoffs. Do not fabricate options or require user selection when the authorized requirements already settle the method.
4. **State your assumptions.** Every unstated assumption is a future bug.
5. **Preserve owner decisions and exercise delegated judgment.** Choose routine methods within the authorized outcome. Escalate materially unresolved product, scope, risk or authority choices and explicit sign-offs; do not ask the user to repeat a decision already delegated.
6. **Measure twice, cut once.** The Junior optimizes for speed of one task. The Lead optimizes for speed of the project. Every 2-second check the Junior skips costs the human operator hours of rework. The agent's seconds are cheap; the human's hours are not. This is not caution -- it is resource allocation.
