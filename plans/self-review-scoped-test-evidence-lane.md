# Self-review: scoped test receipt execution (#386)

Goal source: #386
Plan reference: plans/scoped-test-evidence-lane.md
Investigate-artifact: plans/scoped-test-evidence-lane.md
Pre-mortem-artifact: plans/pre-mortem-scoped-test-evidence-lane.md
Hostile-review-artifact: plans/hostile-review-scoped-test-evidence-lane.md
Project-contribution: Make the content-bound producer usable through the same task/tier authority without restoring executable test runners as ungated diagnostics.

## Assumptions

The operator authorized remaining repairs and the coordinator explicitly delegated this isolated source lane. Base e876812 includes P1 and the reader/protected Git safety changes. The owned policy directory is the existing trusted package boundary; the lane does not establish package provenance or reinterpret arbitrary scripts as trusted. Native terminal producer compatibility remains unchanged.

## Peer review

Independent review found and reproduced the overly broad producer-filename candidate match. It was fixed at invocation/record intent and given normal source-maintenance positives. The corrected seven-method real-hook suite passed independently in 12.003 seconds; the reviewer approved the bounded slice. Coordinator source inspection agreed. Review is not claimed for broader runtime capabilities.

## Lead review

The implementation reuses shell_tokens, select_task, own_session_path, task_tier and existing universal-mutation-gate artifact checks. Known executable paths are not invented write targets. Only repository root/source targets select mutation authority; typed gate/receipt metadata is checked against that exact selected own implementing task afterward. The code cannot use own scratch as early computation authority. Unknown/foreign producer forms remain outside the lane; ordinary source maintenance of a producer-named file remains a normal task mutation.

Tests remain arbitrary execution with repo-root authority; this is not an OS sandbox or a proof that every possible child action is bounded. Effective tier and artifacts still apply. Documentation explains resolved literal paths and keeps native receipt compatibility separate.

## Quantified claims

- Scoped lane: seven real-hook methods pass, including an actual successful two-source producer invocation; independent re-run also passes.
- Existing task-keyed suite: 65 passed, zero failed, 325.639 seconds.
- Existing content-evidence suite: 16 passed, zero failed, 12.733 seconds.
- Python syntax compilation and git diff --check pass.
- No live workspace, source settings, user config or consumer registration was written.

## Test plan

Coordinator integration refreshes combined skill inventory/risk metrics and source/package freshness, then runs the full required checks and final review before promotion. Runtime event delivery and clean exact-main installation are separate acceptance. Retain the source fixtures and truthful unsupported states rather than treating a local receipt as full backend proof.
