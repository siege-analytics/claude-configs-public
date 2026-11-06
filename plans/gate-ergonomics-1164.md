---
ticket_refs:
  - siege-analytics/claude-configs-public#1164: comment posted https://github.com/siege-analytics/claude-configs-public/issues/1164#issuecomment-6650197025
  - siege-analytics/claude-configs-public#1168: progress comment posted with the PR
---
# Self-review: gate artifact lane and one-pass trailer rejections (#1164, #1168)

Goal source: #1164 and #1168 (ticket bodies and acceptance criteria), plus the hub role contract for this implementer.
Working as: software engineer (hook enforcement)
Plan reference: https://github.com/siege-analytics/claude-configs-public/issues/1164#issuecomment-6650197025
Pre-author-inventory: https://github.com/siege-analytics/claude-configs-public/issues/1164#issuecomment-6650197025
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1164#issuecomment-6650197025
Pre-mortem-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1164#issuecomment-6650197025
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1164
Project-contribution: Gate-required think-pipeline posts no longer need wording workarounds, and a commit learns every missing review trailer from its first rejection.

## Assumptions

- The artifacts-posted gate (`hooks/bash/universal-mutation-gate.sh:449-471`) reads only the self-attested `artifacts-posted-gate.json`. The posting conflict is therefore entirely inside `coordinator-status-guard.sh`, and the mutation gate needs no change. It is off-limits to this worker anyway.
- The pre-mortem, investigation and junior/senior skills already define a heading plus a `Ticket:` line. No skill prose is edited, which keeps this change clear of #1156.
- The guard's purpose is no unsupported completion or deploy claims. The artifact lane is held to parity with the unmarked rules: the same completion vocabulary needs the same evidence. It differs only in two ways:
  - the status-tone rules do not apply;
  - skill-defined hypothetical fields, and lines opening with a conditional, are exempt.
- `gh issue edit --body` is classified as an existing-artifact text edit by `hooks/lib/task_actions.py` and exits before the guard logic. That is pre-existing and unchanged here.

## Peer review

- **Shelf check, writing-tests:1:** every behavior change has a positive and a negative fixture.
  - Guard: AC1 has an unmarked control proving the heading is what admits the post. AC2 has unmarked and marked claim negatives. AC3 covers junior, senior and junior/senior posts.
  - Guard laundering negatives come from an in-process adversarial pass: checkbox, numbered, heading-line, mid-line-conditional and front-matter claims all block.
  - #1168: fixtures assert that every absent trailer is listed, and that none already present is listed, for each of the three hooks. A noisy-interpreter fixture covers the classifier-parse path.
  - Result: `coordinator_status_guard.test.sh` PASS (79/79); `tier_trailer_aggregation_1168.test.sh` PASS (29/29).
- **Shelf check, writing-claims:1:** counts below come from the recorded local runs. Hosted CI is reported separately and not claimed here.
- **Same-family adversarial pre-check.** This was an in-process subagent the implementer commissioned. It is not the independent hostile review. It found:
  - three laundering bypasses in the first lane draft: narrow claim list, mid-line conditional exemption, heading-borne status;
  - a coaching hint shown to genuine status updates;
  - a commit-msg JSON parse that broke on interpreter stderr.
  All are fixed with fixtures. It found no enforcement regression in the #1168 collectors.
- **Independent cross-family hostile review: PENDING.** The hub commissions it at the PR head. No result is claimed in this artifact.

## Lead review

- **Guard lane.** The marker must be the first non-blank line, after an optional YAML front-matter block. It must name a think-pipeline artifact and carry a `#N` task reference or a `Task-ID:` token.
  - Close, reopen, ready, PR review and API state transitions never take the lane.
  - The claim scan uses the base `completion` regex over every line, including the heading and front matter, after stripping list, checkbox and markup prefixes.
  - Evidence is computed by the same function as base (`missing_evidence`, extracted verbatim).
- **Artifact detection (hub-relayed false negative on siege_utilities #1846).** `hooks/lib/pipeline_state.py` writes `junior-senior-gate.json` and `artifacts-posted-gate.json`. It now also accepts the skill headings when content follows them.
  - The detection is additive: the stem thresholds are unchanged, so nothing previously recognized stops being recognized.
  - A prose mention or an empty heading does not count.
- **Trailer collectors.** A tier is replaced by the computed one only when an item has also been added to the rejection list. A replacement can therefore never lead to acceptance.
  - Classifier unavailability or an unparsable classifier result remains a hard block.
  - The legacy pre-policy path is unchanged.
- **Residual risk.** A relabeled line inside an allowlisted hypothetical field (for example `Mitigation: shipped`) is exempt.
  - The allowlist is bounded and matches the skill formats.
  - Base already accepts `Owner-signoff: N/A` as owner evidence. That is pre-existing and out of scope.

## Quantified claims

- coordinator_status_guard.test.sh: 79 passed, 0 failed (48 pre-existing scenarios unchanged, 31 new).
- tier_trailer_aggregation_1168.test.sh: 29 passed, 0 failed.
- pipeline_review_headings_1164.test.sh: 5 passed, 0 failed (exact #1846 headings, plus three negatives).
- Full hooks/_test, bin/_test and validate-hooks.py counts: recorded in the PR body from the run on the committed head.

## Test plan

Run the focused suites, then the full `hooks/_test` + `bin/_test` + `bin/validate-hooks.py` with python 3.11. Prove reverts: restoring develop's guard fails the new AC1/AC3 fixtures, and restoring develop's commit-msg fails the one-rejection/list fixtures. Hosted build-and-publish validation on the exact PR head. Cross-family hostile review is pending at the hub.
