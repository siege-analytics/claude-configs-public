# Task-scoped runtime bootstrap recovery (#1051, #1121)

## Assumptions

Goal source: operator instruction 2026-10-29: fix mutation gates per task; use the Google Analytics session as the reproducer; coordinate through the Siege Claude configs hub.
Plan reference: issue #1051 approved design and resolved Q2 (unscoped mutations fail closed).
Investigate-artifact: plans/task-gate-bootstrap-recovery.md
Pre-mortem-artifact: plans/task-gate-bootstrap-recovery.md
Hostile-review-artifact: plans/hostile-review-task-gate-bootstrap.md
Project-contribution: Let an authorized operational task create its own scoped signals without global state or another task's gate.

The installed resolver already keys gates by session and task. The actual GA session successfully created its own task gate through Write and ran a bounded mkdir through Bash under the original installed hooks. Its shell environment contains a literal template, but that does not establish a callback identity failure. No identity recovery change is shipped. Separately, the configs reviewer demonstrated that synthetic literal-template environments can share an invented identity. Reject unresolved directory templates before any identity fallback or own-scratch authorization; do not guess a replacement session.

The confirmed failure is stale memory and insufficient bootstrap guidance: the session tried workspace-root signals, mandatory hash generation and issue creation before an ordinary report run. Improve the denial with the own-session task path, explicit task ID and plain slug instructions. Make this invariant visible in the always-loaded kernel and think skill; correct the private historical memory with a dated supersession note. Preserve scope selection, fail-closed unscoped mutations and effective tier requirements. Regression coverage denies both task authorization and scratch Write for each supported directory variable containing an unresolved template; ordinary reads remain allowed.

The source fix uses an isolated worktree based on develop plus the already-approved main promotion merge; the normal clone remains on main because its project hooks are live runtime inputs. The configs hub is the coordinator of record for review; the Utilities hub is no longer assigned configs work.

Alternatives: a global signal/override would recreate cross-task interference; permissive opaque-script allowance would weaken command boundaries. A new task-runner framework is unnecessary because own-task Write bootstrapping already exists. The chosen fix teaches the existing supported workflow.

## Pre-mortem

- Tiger: guidance is mistaken for broader authority. Retain existing own-session lifecycle boundaries and cross-session negative tests.
- Tiger: source registration or unrelated task changes affect the fix. Preserve task matching; test independent designing and implementing tasks with arbitrary stable slugs and exact bindings.
- Tiger: shell environment output is mistaken for actual callback evidence. Require live Write and Bash probes; leave identity recovery unchanged and reject unresolved templates.
- Tiger: diagnostics are mistaken for task approval. The message describes opening the task; existing status, scope and tier checks still decide the subsequent mutation.

## Peer review

Independent Codex review found no must-fix in the guidance repair or the narrow template rejection; five focused checks passed for each review. The configs hub assigned its existing cross-model reviewer, which demonstrated the synthetic template isolation flaw and is reviewing the repair. Review must check unchanged identity recovery and template rejection, arbitrary-slug bootstrap, cross-session negatives and unchanged task-tier semantics. Results will be recorded before source promotion.

## Lead review

The approved #1051 contract remains unchanged: reads and own signal lifecycle operations do not borrow a gate; otherwise exact target scope selects the task, unscoped mutations block, and only that task's status and artifacts apply. This repair makes that existing workflow discoverable to the model. Source and installed runtime changes require explicit receipts and bounded UAT in the affected session.

## Quantified claims

Local task-keyed suite: 52 tests passed in 272.910s before the final template rejection; its new dedicated negative passed separately, with five independent identity/isolation checks also passing. The unchanged session-anchor suite passed 13/13. Build succeeded. Build, kernel budget, generated-source authority, skill inventory and review-risk checks pass. Independent exact-source review approved b324824. Full hook scenarios and the cross-model configs review remain required before promotion. Actual GA own-task Write, Bash scaffolding, evidence writes and status transition succeeded under original hooks; the report completed and its PDF exists; the GA session reports no source changes, overrides or shared-gate writes. PDF contents were not inspected. No all-runtime parity claim is made.

## Test plan

Run the full hook scenario suites, including the final 53-case task-keyed suite; build/freshness and review-risk checks; independent current-commit review; installed drift and bounded live-session verification. Roll back managed runtime files to the pre-install backup if the installed task isolation or bootstrap checks regress. Preserve session/task state and unrelated local source.


## Kernel verifier integration follow-up

Hosted CI rejected the updated packaged kernel because verify-enforcement.sh still pinned its previous digest. Update only EXPECTED_KERNEL_SHA256 to the SHA256 of all four newly built packaged kernels, `1e94ede28fd98551f492ba275991393719e5d657f759113e960a555a031f78a4`. Independent review verified source-to-package reference resolution, matching kernel-budget catalog and unchanged regular/non-symlink/nonempty exact-digest enforcement. The affected progressive_mount_test passes locally. Hosted full validation must pass on this follow-up before merge.


## Expanded configs-review corrections

The configs reviewer ran 104 old/new probes and found additional reproducible cases: template session ID variables still produced shared synthetic authority; alternate directory-variable guidance could name an unwritable bootstrap path; and a plain task ID could borrow a matching pre-mortem from shared workspace/repository shelves. Reject unresolved delimiters in the common session-ID sanitizer, use the same supported directory precedence for the help path, and document non-hidden slugs. Plain task IDs now require the current host session plans; full owner/repo#N ticket evidence retains repository-plan compatibility.

Independent review then reproduced link-based borrowing through the own plans directory. Plain-ID evidence now opens the host directory, plans directory and final file through descriptor-relative no-follow operations, requires a regular single-link file, and reads once for task identity/risk/launch checks. Regressions deny foreign file symlinks, hardlinks and plans-directory links. The first embedded Python docstring broke the enclosing shell quoting; replacing it with a comment restored bash syntax and valid-task allowances. Six corrected positive/negative cases pass independently, with a separate full-ticket repository-plan allowance also passing. No remaining must-fix from that reviewer. The final 57-case suite and hosted validation must pass before promotion.


## Resolved host directory and canonical identity

Pass the resolver-produced own-session directory through action JSON into artifact validation. A central helper preserves the existing directory precedence and ID-only fallback, so plain-ID pre-mortems work for hosts supplying an ID without a directory. The #831 descriptive-task fixture now stores its plan in its own session; task fixture helpers distinguish numeric full tickets from plain IDs using the same predicate. Independent #831 and five host/provenance/lifecycle checks passed.

Session identity is validated without lossy sanitization: canonical alphanumeric/dot/dash/underscore IDs (excluding dot and dot-dot) are preserved; template/variable syntax and relative directory bindings fail closed. Extended checks cover dollar/percent templates and dot traversal IDs. Six independent identity/precedence/transcript/alternate-directory cases pass after correcting fixture placement. Final full validation remains required. No automatic session discovery or permission bypass is introduced.


## Inline budget integration

Hosted 486e2a5 validation found the larger selected prompt at 10048 bytes, exceeding the existing 10000-byte inline budget on its longer path. Shorten only the new kernel paragraph; keep procedural detail in think and the denial message. All four regenerated kernels match the refreshed verifier pin `6796027e2ce6017c9f84a00eea52fcdf7cb80a18538d745bc14e6c11ad180d9f`. No limit or integrity check is relaxed. Independent review approved the preserved invariants, matching package hashes, load-set test, progressive loading 20/20 and progressive mount. A long-checkout-path local run also passes 20/20, with the large selection at 9664 bytes.
