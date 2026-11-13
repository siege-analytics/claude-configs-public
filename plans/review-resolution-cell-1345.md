## Assumptions
Goal source: issue #1345 and PR #1335 review threads PRRT_kwDOR0YC-M628IZ7 and PRRT_kwDOR0YC-M628IZ_.
Read both publication adapters, the artifact contract and the real publication fixtures. The existing table layout is identifier, priority, finding, resolution. A word in the finding cannot resolve a defect. Require the complete trimmed resolution cell to equal fixed, with case-insensitive compatibility; malformed extra cells remain unresolved. Compact prose parsing retains its existing boundary rules, and its documented example now matches those rules.

## Test plan
Before the fix, real publication fixtures reproduced acceptance of an unresolved fixed-width finding and fixed-later resolution, plus rejection of the documented fixed-period example. After the fix, the actual lean_publication_review.test.sh wrapper passed all 16 cases, including both tool and native publishers, historical records, missing independent review and unresolved findings. self_review_disclosure_test.py passed all 7 cases. Full build passed. Generated inventory, authority and measurement checks are recorded with the final publication evidence. No runtime installation or live business operation was attempted.

## Findings
The resolution predicate and documentation defects are fixed. No unrelated Task, scope, review-source or independent-review protections changed. The two adapters use the same bounded awk expression without adding a packaged dependency.

## Independent review
Root inspected the four source files and independently executed the four new publication regressions: all passed in 3.408 seconds. This record does not substitute for the direct exact-head PR review or required CI.
