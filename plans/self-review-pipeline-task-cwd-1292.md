# Task-owned turn-start evidence (#1292)

This is a post-implementation self-review. The issue's observed failure and
positive control predate this work; this file does not claim pre-edit review.

The host fixes a session cwd independently of its implementing task worktree.
Turn-start diagnostics have no mutation targets, so applying the action-scope
selector to the cwd misses valid own-task evidence. The hook now uses the
existing unique own-session selector, including its explicit task binding.
An explicit gate-path override must still match that selected task. Multiple
unbound tasks produce an ambiguity diagnostic and write no companions.
Mutation selection and physical write scopes remain unchanged.

Verification: the new regression fails on unmodified develop (missing both
companions). The repaired real hook passes eight layouts: linked sibling
worktree, non-Git cwd, matching cwd, foreign session metadata, ambiguous tasks,
explicit binding, unknown binding, and foreign gate override. The positive
cross-cwd cases also exercise the real mutation gate and deny writes in the
unowned cwd. Existing concurrent/legacy writers (legacy multi-task case now
explicitly binds its intended task), ticketless-plan isolation, invalid session
IDs, native identity and conflicting host metadata controls pass: six test
methods on Python3.9 and Python3.11. Final Python3.11 run: 10.923 seconds.
`python3.11 bin/build.py --check` passes. The initial system Python build attempt
could not import PyYAML; no source change or global dependency install was needed.

Risk: a session with several active tasks must bind the intended task; silently
selecting a task from cwd would reintroduce the defect. No all-task fan-out,
foreign session fallback, forged companions, or mutation-authority relaxation
is introduced. Rollback: revert the single source commit. Native installed
acceptance and hosted CI remain separate delivery steps.
