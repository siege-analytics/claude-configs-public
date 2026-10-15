# Self-review: epic #962 F1 lifecycle first promotion

## Assumptions

Domain(s): software engineering, review governance
Geospatial cross-cut: no
Working as: software engineer
Goal source: https://github.com/siege-analytics/claude-configs-public/issues/962#issuecomment-6184498727
Goal source verification: F1 requires the verified first promotion baseline to pass while arbitrary missing history fails and bootstrap digest, gap expansion, and append-only completion protections remain enforced.
Plan reference: `plans/pre-mortem-962-f1-lifecycle-promotion.md`
Pre-author-inventory: issue #962 F1 reproduction, PR #954 review 5528052156, `bin/skill-lifecycle.py`, `bin/_test/skill_lifecycle_test.py`, and `.github/workflows/build-and-publish.yml`
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/962#issuecomment-6184498727
Pre-mortem-artifact: `plans/pre-mortem-962-f1-lifecycle-promotion.md`
Hostile-review-artifact: `plans/hostile-review-962-f1-lifecycle-promotion.md`
Project-contribution: unblock only the first canonical lifecycle-aware promotion from `develop` to `main` while preserving the one-way migration ratchet and develop-only integration boundary.

## Pre-implementation comprehension

Current behavior: `python3 bin/skill-lifecycle.py --check` passes on `develop`, but the same command with `--previous-ref b2d91ef2900f58ddb37c10e1eb2803a7aeaa6753` exits 1 because current `main` predates the lifecycle report. The workflow supplies that SHA as both a promotion pull request's base and the first promotion push's `before` value.

Intended behavior: the exact pinned main baseline passes only when event identity, repository identity, parent order, ancestry, and tree identity prove a canonical `develop` promotion. Any arbitrary baseline, feature/fork PR, direct/squash push, changed merge tree, or missing promoted-branch lifecycle history remains blocked.

Implementation steps: normalize Git refs; separate the event transition baseline from the lifecycle ratchet comparison baseline; validate canonical PR/push merge context; compare gaps and completions with the promoted develop commit's parent; pass explicit event context from Actions; add Git-history fixtures; document the exception; run focused, negative, full-suite, canary, and rollback validation.

Success criteria: both promotion PR and first-main-push fixtures pass; aliases resolve to the exact pinned SHA; arbitrary missing history and every malformed promotion context fail; bootstrap digest, gap expansion, and append-only completion fixtures still fail closed; no publication/deployment/install/promotion occurs.

Primary risk: trusting event-shaped strings without binding them to the commit graph would convert the pinned exception into a forgeable bypass. The implementation therefore requires structural Git proof in addition to context strings.

## Peer review

- **writing-code:** refs resolve to full commit SHAs before policy comparison; subprocesses use argument arrays; the exception is isolated behind the exact pinned baseline; missing Git/event/API evidence fails closed.
- **writing-tests:** the temporary Git graph covers PR and push positives plus arbitrary history, wrong branches, fork/missing repository identity, direct push, changed tree, feature second parent, mutable/missing push provenance, later develop advancement, and missing ratchet history. Existing gap expansion, completion regression, and append-only deletion negatives remain active.
- **writing-claims:** documentation distinguishes the immutable associated-PR head SHA from a mutable branch tip and makes no claim that a branch name is recoverable from Git history alone.
- **writing-prose:** `docs/skill-lifecycle.md` records previous-ref selection, both exact boundaries, event conditions, and ratchet continuity; README links it.
- **writing-releases:** the workflow change is in validation only. No publish-job condition, release branch, tag, version, artifact, main ref, deployment, or installation changed.
- **writing-rules:** the bootstrap digest remains code-pinned; the first-promotion pin cannot authorize a missing report unless event identity and the commit graph prove the transition.

## Lead review

In software engineering, fail-closed boundary validation holds because the real pre-lifecycle main SHA is compared only after ref normalization and requires exact two-parent structure, parent order, ancestry, same tree, and a prior develop lifecycle report. In review governance, proportional evidence holds because the classifier returns Tier C and the implementation has pre-mortem, two independent hostile-review rounds with rejected revisions, negative fixtures, full-suite evidence, and rollback.

Approach-fit verdict: accepted. Separating the event transition baseline from the lifecycle comparison baseline solves the actual bootstrap mismatch without making `previous_gap_state=None` broadly acceptable. The push path uses immutable GitHub associated-PR evidence because Git history alone cannot prove a historical branch name and the live branch tip races. Blast radius is limited to lifecycle validation and its Actions context. The required sequencing assumption is that canonical main promotions use GitHub merge commits from same-repository `develop`; squash/rebase/direct pushes intentionally fail.

## Findings

| ID | Priority | Description | Resolution |
|---|---|---|---|
| F1 | P1 | The pinned pre-lifecycle main baseline blocks the first canonical promotion. | fixed with exact event/graph proof and promoted-parent ratchet state |
| H1 | P1/P2 | Initial push logic accepted a feature-derived second parent. | fixed with canonical promotion provenance and feature negative |
| H2 | P2 | Missing PR head repository was replaced with canonical identity. | fixed; missing identity remains empty and fails closed |
| H3 | P2 | Live `origin/develop` could race or retroactively bless another commit. | fixed; unique associated merged PR supplies immutable head SHA |

No finding was waived. Two final independent hostile reviews returned `ACCEPT`.

## Test plan

Observed:

1. Before change: ordinary develop check passed; `--previous-ref b2d91ef2900f58ddb37c10e1eb2803a7aeaa6753` exited 1 with missing lifecycle history.
2. Focused lifecycle fixtures pass under Python 3.14, including both event positives and all fail-closed cases above.
3. Build, build freshness, both consumer selectors, flat layout, and source/consumer hook validation pass.
4. All Python modules, hook suites, workflow policy suites, release-note canaries, and generated policy/freshness checks pass.
5. `git diff --check` and Tier C classification pass.
6. Branch canary remained `fix/962-f1-lifecycle-promotion`; `origin/develop` remained `0bae4ff108de5ad3b339a868818b05ea1e7c70bd` and `origin/main` remained `b2d91ef2900f58ddb37c10e1eb2803a7aeaa6753` throughout validation.

The first local full-suite attempt ran Python tests before building packages and stopped at `data_scope_test.py` because `dist/claude-code/bin/resolve-load-set.py` did not exist. The sequence was corrected to match hosted CI, the build completed, and the full suite was rerun from the beginning. macOS system Python 3.9 then rejected a pre-existing `Path | None` annotation in `validate-hooks.py`; all complete validation ran under installed Python 3.14, matching hosted CI's modern Python semantics.

## Quantified claims

- "17/17 Python modules pass" — `for test_file in bin/_test/*_test.py; do python3.14 "$test_file"; done` → `PYTHON_TESTS_PASS=17`.
- "36/36 hook suites pass" — `for test_file in hooks/_test/*.test.sh; do bash "$test_file"; done` → `HOOK_SUITES_PASS=36`.
- "2/2 workflow policy suites pass" — `for test_file in .github/workflows/_test*.sh; do bash "$test_file"; done` → `WORKFLOW_POLICY_SUITES_PASS=2`.
- "198 sources / 804 snapshots / 2,904 generated mappings are current" — `python3.14 bin/generated-source-authority.py --check` → `generated source authority: current (198 sources, 804 artifact snapshots, 2904 generated file mappings)`.
- "0 lifecycle completions / 198 legacy exceptions remain current" — `python3.14 bin/skill-lifecycle.py --check` → `skill lifecycle: current (0 complete, 198 legacy exceptions)`.
- "Two final independent hostile reviews accept" — two isolated reviewer calls after immutable associated-PR provenance each returned `ACCEPT`; evidence and prior rejected rounds are recorded in `plans/hostile-review-962-f1-lifecycle-promotion.md`.

## Rework ledger

1. Reproduced the exact real-main failure before implementation.
2. Initial implementation bound PR context but inferred push provenance from merge parent 2. Hostile review supplied a feature-branch counterexample; no push or commit occurred.
3. First revision compared parent 2 with live `origin/develop`. Hostile review demonstrated both a race false block and retroactive blessing; no push or commit occurred.
4. Final revision queries the pushed commit's associated PR, filters to one merged same-repository `develop` → `main` PR, and passes its immutable head SHA. Python requires that SHA to equal parent 2. Both reviewers accepted.
5. Full validation was restarted after correcting build-before-test order and using installed Python 3.14 instead of system Python 3.9.

## Rollback

Revert the single F1 commit from `develop`. This restores the prior fail-closed behavior without changing lifecycle catalogs or any released/installed artifact. The historical review artifacts may remain as evidence, but no runtime state or remote branch other than the F1 feature branch requires rollback.
