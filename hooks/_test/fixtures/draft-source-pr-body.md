## Summary

An F3 panel fetched from one summary row could be authorized by a newer row's attestation or survive a verdict change before HTML finalization. This change binds the fetched row's full timestamp and row-own subject/cycle/grain to a fresh panel decision, then rechecks marked HTML at finalization. Candidate panels and the conduit split remain held.

## Tickets

- Part-of electinfo/enterprise#3133. This source repair does not close the financial outcome.

## Changes

- Capture the fetched panel vintage and deny a grant if the live subject row or attestation no longer matches it.
- Recheck marked panels at response finalization even when an earlier page-wide permission was true; remove stale captions and response validators when the HTML changes.
- Add regression controls for stale rows, withdrawn verdicts, malformed timestamps and fail-dark provider behavior.
- Include the actual author review and separate independent source review in the same commit.

## Testing and review

- The current Task-bound Django run passed 89/89 focused tests for the current source blobs. The older 111- and 317-test receipts refer to earlier source selections and are not current full-suite evidence.
- The canonical exact ten-path staged scanner executed and exited 1 with six findings, not a clean scan. Four are unchanged real CMS contract/coverage debt; two are independently demonstrated Optional-failure and closure-use detector false positives. See the committed review records for individual evidence and falsification criteria.
- The strict post-commit test-evidence CLI was refused before execution. Independent protocol and blob review established that the genuine current receipt binds the committed source; this is not a claim that the refused CLI passed.

## Limits

This is a source-review PR to `develop`, not financial, installed-serving or release approval. No complete dated eligible population, immutable generation lineage, FEC-and-Steve parity, ten cycle-by-grain attestations or 477 UNKNOWN dispositions is established. The candidate, conduit-split, financial and serving holds remain. CI, protected review and installed verification remain separate.
