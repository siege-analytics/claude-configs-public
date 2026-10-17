# Self-review: native argument boundary correction (#1027)

## Assumptions

Working as: author-side correction; independent acceptance remains external.
Goal: fix PR #1032 finding 6228927453 under the operator's explicit scope.
The issue template exemption in self-review-1027-selected-registration.md applies.
Pre-mortem-artifact: plans/pre-mortem-1027-native-arguments.md
Hostile-review-artifact: plans/hostile-review-1027-native-arguments.md

## Peer review

Review-only independent acceptance remains pending. No additional worker is
started under the issue's existing coordinator/reviewer boundary.

## Lead review

Native Git data must never enter the settings option parser. Binding verification
and pending-state refusal must precede every operation. Native arguments cannot
select settings events, replace host bindings, or append a command. Existing policy
and compatibility rules remain authoritative.

## Quantified claims

No passing correction claim yet. The baseline probe is red before edits; exact
commands, ref effects and log hashes will accompany committed-head publication.

## Test plan and working evidence

The posted parent probe is retained red; the selected registration suite passed
14 tests, native suite passed 18 tests, protected policy passed 14 tests and
effective policy passed 42 tests in working-source runs. The independent example
passed real alias allow/deny probes. Final additions extend the same cases to
space/Unicode destination paths and file URLs. Full committed-head build/check,
freshness, all Python/hook/scanner suites and both examples remain mandatory
before push; precommit results do not substitute for that replay.

The unfiltered staged scan reports two inherited runtime test-discovery warnings.
Their public failure paths are exercised in the selected suite; the scanner does
not discover bin/_test for those source names. This is disclosed under the
operator's scanner-evidence requirement, without suppressions or a clean claim.

Verified-by: cache/selected-registration/argv-correction/evidence contains raw
red and working logs; the PR publication comment will pin head/tree/parent and
complete fresh command/log hashes. The source review found no additional blocker;
independent exact-head review remains pending and the PR stays draft.
