---
ticket_refs:
  - siege-analytics/claude-configs-public#1095: git guards match their verbs in prose; spawn-guard accepts empty labels
---

# Self-review: #1095 git guards match verbs as code; spawn-guard explicit labels

## Assumptions

Pre-author-inventory: on develop, `commit_detector` fails 3 cases, `sensitive_files` 4 and `broad_staging` 5. electinfo has carried these fixes in its vendored copy since 2026-09-02 (6c1a624, 2934a87, c5dd99c, 69b114a, f75d3fd). The electinfo#348 audit confirmed upstream v3.5.73 lacks all of them.
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1095
Pre-mortem-artifact: plans/pre-mortem-1095-git-guard-command-text.md
Hostile-review-artifact: https://github.com/electinfo/electinfo_claude_skills/issues/348
Project-contribution: documentation, issue bodies and fixtures that mention `git commit`/`git add -A` stop tripping the guards. Upstream gains electinfo's fixes, so electinfo can drop its vendored edits.

- `hooks/lib/command-text.py/.sh` are electinfo's versions, unchanged. The guard edits are electinfo's deltas against upstream cbf9ef9, applied onto the current upstream guards. The payload cap (5ded75f) is not ported: it is low impact, and the fast skip reads the full payload.

## Peer review

- **writing-code:** the electinfo patches for ticket-required, branch-guard, no-sensitive-files and spawn-guard applied cleanly. no-attribution and no-broad-staging were merged by hand around the #1083 fast skip.
- **writing-tests:**
  - commit_detector 24/24, sensitive_files 11/11, broad_staging 9/9, spawn_guard 14/14 and git_hook_fast_skip 213/213.
  - The first three fail 3, 4 and 5 cases on develop.
- **Gate evidence:**
  - review_risk_test PASS, after registering 5 `command-text.sh` edges and an invocation-site digest whose only new sites are those 5 source lines;
  - `command-text` classified Tier C.

## Test plan

- `bash hooks/_test/{commit_detector,sensitive_files,broad_staging,spawn_guard,git_hook_fast_skip}.test.sh`
- `python3 bin/_test/review_risk_test.py`
- the full CI validate job, locally from a clean dist.

## Lead review

- **Solves #1095:** yes.
- **Out of scope:** the 1 MB payload cap; the missing-scanner warning in detect-ai-fingerprints.

## Quantified claims

- 4 ported suites with 58 cases; 12 develop failures.
