## Assumptions
Goal source: issue #1345 and PR #1335 review threads PRRT_kwDOR0YC-M628IZ7 and PRRT_kwDOR0YC-M628IZ_.
Read both publication adapters, the artifact contract and the real publication fixtures. The existing table layout is identifier, priority, finding, resolution. A word in the finding cannot resolve a defect. Require the complete trimmed resolution cell to equal fixed, with case-insensitive compatibility; malformed extra cells remain unresolved. Compact prose parsing retains its existing boundary rules, and its documented example now matches those rules.

## Test plan
Before the fix, real publication fixtures reproduced acceptance of an unresolved fixed-width finding and fixed-later resolution, plus rejection of the documented fixed-period example. After the fix, the actual lean_publication_review.test.sh wrapper passed all 16 cases, including both tool and native publishers, historical records, missing independent review and unresolved findings. self_review_disclosure_test.py passed all 7 cases. Full build passed. Generated inventory, authority and measurement checks are recorded with the final publication evidence. No runtime installation or live business operation was attempted.

## Findings
The resolution predicate and documentation defects are fixed. No unrelated Task, scope, review-source or independent-review protections changed. The two adapters use the same bounded awk expression without adding a packaged dependency.

## Independent review
Root inspected the four source files and independently executed the four new publication regressions: all passed in 3.408 seconds. This record does not substitute for the direct exact-head PR review or required CI.

## Develop integration
Integrated protected develop 77d83c20e3ca9a50f3a697bfa6fe8b593ec38f7d through an ordinary merge after #1344 landed. The accepted publication changes are byte-identical to their source commit. The actual producer rerun passed 16 publication tests in 13.896 seconds; all five official freshness checks passed.

The complete merge-selected scan returned 1 with 63 findings, not a clean result. Raw SHA256: 04392aaace0d9befaf53be3dc2214f33d284211aeb9c3837e032d4dac977ef27. Raw output and the per-finding author map are retained in external evidence core1345-publication-fix-20261113/core1345-merge-scan.txt and core1345-merge-scan-dispositions.json. Root independently verified the exact row multiset, owning-function hashes, handler sources and protected resolver bytes: 62 rows retain the prior individual #1344 dispositions; the remaining protected scanner-authority handler returns an explicit structured denial rather than silently granting authority. Existing inherited coverage debt remains tracked by #1329. Independent acceptance is retained in the same evidence directory as merge-scan-root-independent-acceptance.json. No resolver behavior was edited by this fix.

## GFM compatibility correction
Independent review found valid escaped-pipe finding text and an optional trailing separator were rejected by the first strict field count. Both reproduced through actual publication fixtures before correction. Consulted the official GFM table specification, https://github.github.com/gfm/#tables-extension, examples 199 and 200: escaped pipes remain cell content even within inline code, and trailing delimiters are optional. The tokenizer now preserves escaped character pairs, splits unescaped delimiters, and accepts only four cells with an optional empty trailing field. Resolution content must still be the complete trimmed word fixed. Escaped resolution text, unresolved rows and extra unescaped columns remain blocked.

The actual supported producer passed all 22 publication tests in 19.524 seconds. Adjacent disclosure tests passed all 7 cases. These results are local tests, not hosted CI or installed-runtime evidence. Auto-merge was disabled when the compatibility issue was found; the corrected source requires its own exact-head CI.

Root inspected the final tokenizer and optional-trailing-separator condition, then independently passed all six new actual publication cases in 5.335 seconds. The direct PR review will bind that acceptance to the corrective head.
