---
ticket_refs:
  - siege-analytics/claude-configs-public#787
---

# Round 3 baseline: detect-ai-fingerprints test-suite verification

Round 3 reviewer's finding R3-F9 observed that historical self-review artifacts contain quantified claims ("6/6 pass", "12/12 pass", "17/17 pass" etc.) that were true-at-time-of-PR but no longer match current pass counts as the fixture set grew. Those claims are time-of-PR snapshots and stay as historical artifacts. This document is the current baseline.

## Aggregate: fixture counts as of 2026-09-07

Verified by running each test script on develop after all Round 3 fixes (#788, #789, #790, #791, #792, #793, #794) merged.

| Test script | Fixtures | Rule under test |
|---|---|---|
| test_writing_code_4.sh | 10 | Django ORM kwargs, same-file models (incl. defaults + create_defaults dict) |
| test_writing_code_7.sh | 13 | silent exception swallowing (incl. scaffold + noqa vocabulary) |
| test_writing_code_8.sh | 12 | optional-import callsite guards (branch-aware polarity) |
| test_writing_code_9.sh | 12 | silently-dropped parameters (scoped visitor + escape hatches) |
| test_writing_code_15.sh | 28 | unbounded blocking I/O (Popen chains, Session/Client instance methods, invalid timeout literals) |
| test_writing_tests_5.sh | 25 | untested exception handlers (except*, namespaced tests, controlled-vocab noqa) |
| test_writing_releases_3.sh | 8 | deprecation message format (version+keyword) |
| test_scan_sh_exit_code.sh | 10 | scan.sh counter regex covers all rule tokens |
| test_is_test_path.sh | 13 | path-segment-anchored test detection |
| test_rule_citations.sh | 1 | Rule-executed evidence for rule citations |
| **Total** | **132** | across 7 detectors + 3 dispatch/prose checks |

## Verification command

```bash
cd skills/detect-ai-fingerprints
for t in test_writing_code_4 test_writing_code_7 test_writing_code_8 test_writing_code_9 test_writing_code_15 test_writing_tests_5 test_writing_releases_3 test_scan_sh_exit_code test_is_test_path test_rule_citations; do
    echo -n "$t: "
    bash "$t.sh" 2>&1 | tail -1
done
```

Expected output on green develop:

```
test_writing_code_4: Results: 10 passed, 0 failed
test_writing_code_7: Results: 13 passed, 0 failed
test_writing_code_8: Results: 12 passed, 0 failed
test_writing_code_9: Results: 12 passed, 0 failed
test_writing_code_15: Results: 28 passed, 0 failed
test_writing_tests_5: Results: 25 passed, 0 failed
test_writing_releases_3: Results: 8 passed, 0 failed
test_scan_sh_exit_code: Results: 10 passed, 0 failed
test_is_test_path: Results: 13 passed, 0 failed
test_rule_citations: PASS: rule citations require matching Rule-executed evidence in messages
```

## Chronology (three rounds shipped)

- **Round 1** (Codex GPT-5.1-codex-max, session 260906-ivory-finch): 11 findings → 8 fixes in PRs #761, #763, #764. Epic #760 closed.
- **Round 2** (Claude Opus 4.7, session 260906-fit-whale): 8 findings → 4 fixes in PRs #767-770 + 8 followup PRs #772-779. Epic #766 closed.
- **Round 3** (GPT-5.5, session 260907-prime-laurel; two prior orphans: 260906-crisp-silver rate-limit, 260906-quiet-carbon model-not-supported): 9 findings → 8 fixes in PRs #788, #789, #790, #791, #792, #793, #794 + this baseline artifact. Epic #787 tracking.

## Historical snapshot claims

The following self-review artifacts contain quantified claims that were true when the respective PRs merged but do NOT match current pass counts. They stand as historical records of time-of-PR verification:

- `plans/self-review-56.md`: "6/6 pass" for test_writing_tests_5. Current: 25/25.
- `plans/self-review-57.md`: "6/6 pass" for test_writing_code_8. Current: 12/12.
- `plans/self-review-760-f1.md`: "6/6 pass". Current: 12/12.
- `plans/self-review-760-f2-f5.md`: "12/12 pass". Current: 12/12 (unchanged for wc:8).
- `plans/self-review-760-f6-f8.md`: "12/12 pass" for wt:5. Current: 25/25.
- `plans/self-review-766-*`: various historical counts.
- `plans/self-review-771-*`: various historical counts.

None of these earlier claims are wrong for their PR's snapshot; they are correct-as-of-merge and now merely-historical.
