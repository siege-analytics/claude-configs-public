# Self review: task-scoped gates and hub spokes

## Assumptions

Goal source: quoted user request in session 260905-clever-quasar: "Ensure design notes, think gate, investigate gate, etc. are task-only blocking rather than workspace-blocking" and follow-up request to revise hub directions for spoke source choice and worker/reviewer retirement.
Working as: tech lead and software engineer.
Pre-author-inventory: conversation summary plus direct inspection of `hooks/resolver/think-gate-guard.sh`, `hooks/resolver/investigate-gate-guard.sh`, `hooks/resolver/pipeline-state-guard.sh`, `hooks/bash/universal-mutation-gate.sh`, and `hooks/lib/resolve-think-gate.py` in `.wt-task-scoped-gates`.
Investigate-artifact: conversation summary and direct hook/rule inspection in session 260905-clever-quasar.
Pre-mortem-artifact: this artifact, sections "Peer review" and "Lead review".
Hostile-review-artifact: plans/hostile-review-task-scoped-gates.md
Project-contribution: prevents unrelated sessions in the same workspace or repo from inheriting another task's design/think/investigation state, while improving hub source selection and cleanup discipline.

## Peer review

- writing-code:5 PASS - hook changes rely on inspected local files and existing `resolve-think-gate.py` behavior rather than hypothetical APIs.
- writing-tests:1 PASS - regression tests exercise the failure mode that would fail if foreign workspace-root or same-repo foreign-session gates were still accepted.
- writing-claims:2 PASS - validation claims are backed by same-turn command output: `bash hooks/_test/session_signal_resolution.test.sh` passed 14 tests; `bash hooks/_test/investigate_gate_schema.test.sh` passed 5 tests; `bash hooks/_test/universal_mutation_gate.test.sh` passed 18 tests; `bash hooks/_test/ca_enforcement_gate.test.sh` passed 7 tests; `python3 bin/build.py --check` completed with 0 conversions; `python3 bin/sync-skill-references.py --check` completed with 0 conversions.
- writing-prose:1 PASS - added prose uses plain ASCII punctuation in the changed rule/changelog/self-review text.
- Hostile review PASS after fixes - `plans/hostile-review-task-scoped-gates.md` records initial BLOCK findings, fixes, and added tests for same-repo local gates plus env override validation.

Full hook loop note: the all-shell-hook loop passed the touched gate tests and many unrelated suites, then reported existing failures in `hooks/_test/ticket_required.test.sh` and `hooks/_test/verify_enforcement.test.sh`. Those failures are not introduced by this change and the focused impacted suites pass.

## Lead review

As tech lead, I approve the task-scoping design because resolver rejection is now authoritative for workspace-root, repo-local, and env-override signals when current repo/session metadata does not match.

As software engineer, I approve the implementation because prompt-time gates remain advisory for the current task, mutation surfaces remain blocking when no valid current-task gate exists, and tests cover both foreign-repo and same-repo foreign-session contamination.

As tech lead, I approve the hub-rule additions because source-selection rationale must now be recorded and retirement must name a durable handoff location before workers/reviewers are safe to archive/delete.
