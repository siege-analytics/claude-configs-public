# Self review: tandem-agent operating model

## Assumptions

Goal source: operator said the full skills revision must be done so agents can work in tandem correctly, not a partial shelf hotfix.
Working as: software engineer and tech lead
Pre-author-inventory: read current session coordination, standing approval, work-item ownership, code-review, hostile-review, cross-review, drive-while-away, and Siege Utilities rules; grepped active skills/rules for coordination, reviewer, worker, implementation, authorization, handoff, and status terms.
Investigate-artifact: plans/design-note-tandem-agent-operating-model.md
Pre-mortem-artifact: plans/design-note-tandem-agent-operating-model.md
Hostile-review-artifact: plans/self-review-tandem-agent-operating-model.md
Project-contribution: turns collaborator operation from implicit norms into explicit rules and review/implementation contracts.

## Peer review

- writing-rules:1 PASS — no claim of mechanical enforcement without adding a hook; coverage rows mark judgment/tooling-needed status.
- writing-rules:8 PASS — invalid shelf `[skill:shelves--...]` forms are removed across active skills and replaced with explicit `skills/shelves/.../SKILL.md` paths.
- session-coordination PASS — adds no-set-and-forget collaborator checking without weakening existing at-rest/baton rules.
- standing-approval PASS — clarifies standing approvals delegate timing but not role expansion.
- review lifecycle PASS — reviewer task completion, work-gate closure, implementation authorization, and re-review are now separated.
- direct posting PASS — spawned reviewers report to coordinator by default; direct external comments require explicit comment-only scope.
- Siege Utilities PASS — implementation requires explicit repo/branch/files/findings/tests/push/PR permission and re-review.
- Shelf routing PASS — collaborators can read shelves by file path rather than failing on non-loadable `shelves--...` aliases.

## Lead review

Approved for a guidance/rules slice. It is comprehensive for the current tandem failure class because it touches the coordinator, reviewer, cross-review dispatcher, standing approval, work-item reporting, Siege Utilities local rule, and coverage matrix rather than only the immediate bad slug symptom.

## Quantified claims

- 1 new always-on tandem rule file.
- 6 tandem-agent rules.
- 5 new coverage rows for tandem failure modes.
- Existing affected skills/rules cross-linked: session coordination, work-item ownership, standing approval, code-review, hostile-review, cross-review, Siege Utilities.
- 0 remaining active `[skill:shelves--...]` references after grep.
