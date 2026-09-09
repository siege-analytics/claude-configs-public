# Design note: tandem-agent operating model

## Goal source

Operator correction in Craft Agent session `260905-clever-quasar`: the skill work must not be partial. The full skills revision must let coordinator and collaborator agents work in tandem correctly, including active collaborator checks and no unauthorized implementation.

Refs: #842.

## Problem

The prior hotfix fixed invalid nested shelf slugs but did not fully close the operating-model gaps that caused the Siege Utilities reviewer to implement/push without authorization and caused the coordinator to under-check collaborator state.

## Design

Add one always-on rule file, `skills/_tandem-agent-rules.md`, and cross-link it from the skills that create or consume collaborator work:

- `_session-coordination-rules.md`: adds active collaborator check/no-set-and-forget rule.
- `_work-item-ownership-rules.md`: links coordinator reporting to tandem role contracts.
- `_standing-approval-rules.md`: clarifies standing approvals do not expand collaborator roles.
- `code-review/SKILL.md`: defines review-only role contract, pinned commit range, durable output, re-review.
- `hostile-review/SKILL.md`: separates reviewer task completion from work-gate closure and forbids direct posting unless scoped.
- `cross-review/SKILL.md`: fixes contradictory direct-post instructions and requires parent/coordinator delivery by default.
- `_siege-utilities-rules.md`: requires explicit implementation authorization fields and re-review after fixes.
- `_coverage.md`: records tandem failure modes and ratchet paths.
- All active `shelves--...` `[skill:]` references: converted to explicit shelf file paths because this runtime cannot load the generated shelf names directly.

## Intended behavior

A coordinator can now run a reviewer and an implementer in tandem without ambiguity:

1. Coordinator issues a role contract.
2. Reviewer performs review-only work and sends durable findings.
3. Operator/coordinator decides implementation scope.
4. Implementer changes code only inside explicit authorization.
5. Reviewer re-reviews the new commit range.
6. Coordinator retires or pauses collaborators explicitly.

## Non-goals

- No new mechanical hook is implemented in this slice.
- No Siege Utilities Python implementation is authorized by this skills change.
- Broader #842 gate/scaffold redesign remains open.
- This does not create flat alias directories for shelves; it avoids the broken alias form by making consumers read concrete files.
