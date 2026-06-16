## Assumptions
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #435
Goal source verification: Manual — ticket has Context, Goal, Acceptance criteria, Approach. Structurally fit.
Plan reference: https://github.com/siege-analytics/claude-configs-public/issues/435#issuecomment-4714475335
Pre-author-inventory: NONE (modifying existing workflow, no pre-existing abstraction to inventory)
Investigate-artifact: TRIVIAL (see declaration below)
Pre-mortem-artifact: TRIVIAL (see declaration below)

## Trivial-investigation declaration
Single file modified (`.github/workflows/build-and-publish.yml`). The change restructures the auto-tag step to resolve version before build and auto-increment patch when the tag exists. Investigation surface: (1) confirmed `bin/build.py` reads VERSION file (line 788-789), so version must be resolved before build — verified, (2) confirmed `[skip ci]` is natively supported by GitHub Actions — well-documented standard feature, (3) confirmed workflow already has `contents: write` permission for pushing to release branches — the same permission covers pushing commits to main.

## Trivial-pre-mortem declaration
Risk surface: CI workflow change. Failure modes: (a) version resolution step errors → build proceeds with stale VERSION, tagged with wrong number — mitigated by the fact that the step only runs on main push, and the original behavior (skip) is the fallback. (b) `[skip ci]` doesn't prevent re-trigger → mitigated by `github.actor != 'github-actions[bot]'` guard. (c) Infinite patch increment loop → impossible; tags are finite and the loop terminates when a non-existent tag is found. Rollback: revert the workflow file to previous commit.

## Peer review

### Syntax check
Syntax check: N/A (no .py changes). YAML file validated by visual inspection of indentation.

### Test suite
Test suite: N/A (CI workflow file — tested by CI execution itself).

### Build validation
Build: `python bin/build.py --check` → "Build check complete." (exit 0).

### Shelf: conventions
The workflow change follows existing GitHub Actions conventions: step outputs via `$GITHUB_OUTPUT`, conditional execution via `if:`, actor filtering for bot-commit guards.

### YAML structure
- Indentation consistent (2-space) throughout
- Step IDs used correctly: `resolve-version` referenced by `auto-tag` step via `steps.resolve-version.outputs.*`
- `if:` conditions match between resolve-version and auto-tag steps
- `[skip ci]` in commit message follows GitHub Actions convention

## Lead review

### Phase A: Structural coherence
Design note on #435 matches implementation. Three-step flow (resolve → build → tag) ensures dist has correct VERSION. Actor guard + `[skip ci]` provides two independent loop-prevention mechanisms. Step ordering change (configure-git before resolve-version) is necessary because resolve-version may write to VERSION.

### Phase B: Verification
- `bumped` output logic: `[ "$RESOLVED" != "$VERSION" ] && echo true || echo false` — correct shell conditional
- While loop terminates: `git rev-parse` returns non-zero for non-existent tags, breaking the loop
- VERSION file update is local only until the commit-and-push in auto-tag step
- Tag-triggered runs (line 6: `tags: ['v*']`) still work: resolve-version and auto-tag both have `github.ref == 'refs/heads/main'` guards, so tag-triggered runs skip them entirely and proceed directly to build → publish → tag-release-branches → create-release

### Phase C: Findings triage

## Findings

No findings.

## Quantified claims

No specific counts stated in this change.

## Evidence-predates-work
Artifact: plans/self-review-435.md
