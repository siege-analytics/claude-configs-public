# Self-review: workspace skill ownership

Domain: software engineering
Goal source: plans/workspace-skill-ownership.md
Plan reference: plans/workspace-skill-ownership.md
Investigate-artifact: plans/workspace-skill-ownership.md
Pre-mortem-artifact: plans/workspace-skill-ownership.md
Hostile-review-artifact: plans/hostile-review-workspace-skill-ownership.md

## Assumptions

Working as: implementer in an isolated worktree based on 6d8f06d.
Reading for: preserve operator skill content during accepted-main activation and
retire only the observed legacy dispatcher bytes authorized by the coordinator.
Failure shapes: custom directories or nested files disappear; same-name modified
legacy Markdown disappears; local metadata replaces immutable retirement policy.

Exact incoming managed paths retain their overwrite contract. Unknown obsolete
paths retain their content because no trusted prior ownership receipt exists.
The production retirement catalog records an observed installation artifact,
without inventing a source revision. The immutable source snapshot supplies that
catalog during exact-main deployment. No live or global settings were touched.

## Peer review

The separate reviewer caught an observed-size error before integration: the
installed artifact is 17802 bytes, while the supplied 17796 value counted Unicode
characters. The production catalog now uses the independently measured byte
length with the unchanged observed digest. The final separate review approved the corrected source with no remaining
must-fix finding; its independent policy suite also passed. The fixture tests the real immutable build
and activation chain with committed synthetic legacy metadata. Production keeps
the observed hash and size rather than publishing the private dispatcher bytes.

## Lead review

Function lens: the loader bounds deletion authority to skills/RESOLVER.md and
validates size, digest and provenance. The retirement helper preserves missing,
nonregular, aliased and changed files. The copier checks incoming file paths
before merging them. Unknown content remains outside that write set.

Chain lens: accepted Git snapshot -> build module and committed catalog -> path
preflight -> exact managed file merge -> artifact verification -> deployment
stamp. Additional preserved content is not falsely claimed as managed output.

DDIA shelf lens: committed metadata is the retirement authority, installed bytes
are the subject of the ownership decision, and build outputs are derived. A
filename alone cannot establish ownership. Conservative preservation avoids
turning incomplete historical evidence into durable content loss.

## Validation and limitations

The final deploy_source_policy_test passed with three real immutable builds.
It checks a custom top-level directory, custom file within managed think/,
unrelated root Markdown, exact known-hash legacy retirement and equal-size
modified legacy preservation. Log: /private/tmp/skill-ownership-policy-test.log.
Staged diff whitespace check passed.

Full review_risk_test stopped at the inherited integration entrypoint floor:
source hub-concurrency-gate count four versus manifest count three, and stale
hardcoded source registration digest. The coordinator owns the combined refresh.
The new catalog has a Tier C path pattern and audited dependency floor. Direct
review-risk.py classification of the new catalog returned valid Tier C.

Scanner baseline disposition: Reason: the scanner scans entire touched Python
files and reports existing unbounded subprocess calls, existing silent exception
handlers, and the existing test-discovery heuristic in those files. Evidence:
/private/tmp/skill-ownership-scan.log records the nonzero result; these constructs
predate this patch in 6d8f06d. Newly introduced prose and exception-handler findings
were corrected. Falsification: a diagnostic on a newly introduced construct would
invalidate this disposition and require a source fix. This is not a clean scanner
claim; the coordinator owns the existing scanner debt and integration decision.
