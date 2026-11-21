# Self-review: #181 prohibits all co-author trailers

Ticket: siege-analytics/claude-configs-public#181 (historical evidence; this PR does not close it)
Review tier: C (commit enforcement hook and attribution policy)
Base: develop 4b123ca6319e2e5b0603d3545f0693f01f74c6b2

## Assumptions

Goal source: operator directive in this task: do not add any `Co-Authored-By` trailer, human or agent; an encountered trailer is a bounded cleanup task, not a reason to stop authorized work.

Issue #181 records the concrete failure: GitHub squash merges added Craft Agent co-author trailers to user-visible commits. The current `_output-rules.md` prohibited AI/agent attribution but explicitly preserved legitimate human co-author records, and `no-attribution.sh` only rejected AI-specific co-author patterns. That exception conflicts with the operator's current directive. The commit hook is the mechanical boundary; the PR workflow also needs to avoid host-generated squash trailers.

## Lead review

- Ban every `Co-Authored-By` trailer centrally and in commit, PR, wrap-up, consolidation, template and contribution instructions.
- Broaden the early commit-command scan, enforce the rule again in native `.githooks/commit-msg` against the final message file (including `-F` and editor messages), and add human co-author regression cases at both boundaries.
- Keep the existing continuation rule: a prohibited trailer does not halt source work; clean owned unpublished history before publication. Never rewrite protected/shared history.
- The PR workflow directs maintainers away from a squash operation that would synthesize the forbidden trailer.
- No author identity, unrelated commit metadata, or protected history is changed.

## Test plan

- `bash hooks/_test/commit_detector.test.sh`: 39 passed, 0 failed, including AI and human co-author cases and a non-commit false-positive control.
- `bash hooks/_test/review_risk_policy.test.sh`: 14 passed, 0 failed, including native final-message-file rejection.
- `bash -n .githooks/commit-msg hooks/git/no-attribution.sh hooks/_test/commit_detector.test.sh hooks/_test/review_risk_policy.test.sh`: passed.
- `git diff --check`: passed.
- `python3 bin/sync-skill-references.py --check`: passed.
- `uv run --with-requirements requirements-validation.txt python3 bin/skill-inventory.py --check`: passed after refreshing the generated inventory.
- `uv run --with-requirements requirements-validation.txt python3 bin/generated-source-authority.py --check`: passed after refreshing the generated source-authority catalog.
- `uv run --with-requirements requirements-validation.txt python3 bin/build.py --check`: passed; all 199 skill/rule headers validated.
- Hosted CI is pending on this exact candidate.

## Peer review

Independent review: `plans/hostile-review-181-no-coauthor-trailers.md`. The reviewer found that the early PreToolUse hook can be bypassed by `git commit -F` because it cannot see the final message file. Fixed by enforcing the trailer ban in native `.githooks/commit-msg`, which receives that file, and adding a final-message-file regression case. The reviewer also found the early-hook diagnostic mislabeled a human trailer as AI attribution; changed it to “prohibited attribution.” The reviewer confirmed the remaining instruction copies are consistent.

## Findings

The initial source-level check was incomplete for `-F` and editor messages. The final-message hook closes that gap. Hosted CI remains required; the local packaging check is limited by missing PyYAML.

## Quantified claims

- 17 files changed: 8 instruction surfaces, 2 hook boundaries, 2 regression tests, 3 generated catalogs and 2 review records.
- Focused suites: 39 commit-detector cases and 14 native review-policy cases passed; 0 failed.
- No production or protected history was modified.
