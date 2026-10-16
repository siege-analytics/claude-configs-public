# Self-review: #1003 preparation review corrections

Pre-mortem-artifact: plans/self-review-1003-packet-corrections.md
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/pull/1026#issuecomment-6221200978

## Assumptions

- This isolated patch is based on PR #1026 head `3ce21ca445e5ffe2d5fb29cd6fec1480cd5e902d` and preserves accepted runtime source `6a3c2efc593f209ba6d9594a29e43bfb8cab634a`.
- The production packet retains its exact installed-artifact and path checks. No live run, shared installation or application patch is included.
- Existing coordinator work stays in its own checkout. This patch can be cherry-picked or applied after its independent review.

## Changes and negative tests

The workflow derives a temporary proposal with the runner's workspace path and matching cleanup path. It validates that copy, then checks that requiring approval fails with the specific missing-approval diagnostic. The reviewed live proposal is unchanged except for the required driver digest refresh.

The selector subprocess suppresses bytecode writes itself, like the existing build, composition and hook subprocesses. Its materialization regression removes caller bytecode suppression and verifies the prepared payload contains no Python bytecode. Exact payload verification remains strict.

Before the fix, the plain Python materialization test reproduced hosted run `38936843357`'s digest failure. A retained independent materialization shows `bin/__pycache__/procedure_composition.cpython-313.pyc` appearing after the payload was hashed. The separate runner-home mismatch was reproduced with only `Path.home()` changed to `/home/runner`.

## Peer review

Author review only for this correction. The initial findings are in PR #1026 review `5551093725`, inline `4297211631`, and comment `6221200978`. Independent review of the correction remains required; those findings do not constitute acceptance of this patch.

## Lead review

The correction adds no capability/approval schema or lifecycle gate. The installed automation-bridge and SDK CWD findings remain explicit planning limitations on #1003. Local prepared-payload success does not establish live registration or authorize a canary.

## Quantified claims

The exact corrected workflow step passed locally with global bytecode suppression absent: 12/12 preparation tests in 39.137 seconds, then positive proposal validation and the expected missing-approval rejection; total 39.383 seconds. Evidence: `/tmp/cc-1026-correction-ci-step.log`.

The unchanged base's broader matrix is reported on PR #1026. This patch does not relabel that evidence as a new full-suite run. The generated package build, `review_risk_test.py`, review-risk metrics freshness, skill inventory freshness and staged whitespace check also passed. The review-risk check initially stopped because this new checkout lacked generated packages; rebuilding them supplied that prerequisite. Independent review evidence remains pending in the PR thread before integration.

## Rollback

Before adoption, discard this isolated patch. After adoption, revert its single correction commit; that restores the known CI/payload defects, so it is a source rollback only and grants no live-run readiness.
