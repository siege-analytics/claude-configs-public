# Ticket dispatch scanner dispositions (#1107)

Proposed finding-level analysis; independent acceptance required. Full selected staged scan completed with exit1, not a clean scan. Protected base b3c560b18faabade9d47e49b3b39cb17883259c3; reviewed selection60ef5a8747508c401a73e151dd8bab1e0b1a68f9. Raw SHA25696a7eefb609a18747e2984ddb85708e7128c633d26498fbc9b516902ae642f12, retained in /private/tmp/ticket-dispatch-staged-scan.log. Source/test/scanner/map identities and full raw output: plans/ticket-dispatch-scan-evidence-1107.json (original private metadata: /private/tmp/ticket-dispatch-scanner-identities.json). No ignores, overrides, source suppression or exit remapping. Configuration absent/default; existing source-test map unchanged.

## F1: command-text.py:321 writing-tests-5

Reason: locator reports no test file, but actual CLI fixtures live in hooks/_test/commit_detector.test.sh. Its main exception fallback is unchanged from protected base; the new Python caller imports code_only and does not execute the CLI __main__ handler.

Evidence: commit_detector suite38 passed; reader Safety.test_ticket_redirect_fallback_keeps_prose_data_and_shell_payload_code and full-stack test exercise the actual shared data boundary and wrapped code. Mapped fixture existence and actual invocation refute the no-test-file observation; they do not prove every handler has individual exception coverage.

Falsification: missing actual fixture/caller, false-negative wrapped Git candidate or false-positive quoted prose invalidates this disposition. No all-handler coverage claim.

## F2: extract-json.py:28 writing-tests-5

Reason: locator misses hooks/_test/reader_git_safety.py. The broad parse-error empty-result contract already existed; valid Unicode transport now uses bytes without changing that fallback.

Evidence: actual ASCII-locale raw/escaped Unicode ticket allow/deny pairs and extractor scalar/fallback/container/malformed controls passed. The fixture dispatches the actual CLI, not a reimplementation. Reader16 passed. No claim that every hypothetical JSON I/O failure is exercised.

Falsification: missing dispatch fixture, changed null/empty/false/zero semantics or valid Unicode becoming empty would invalidate this locator explanation.

## F3: git_command.py:395 writing-code-7 silent-swallow Pass

Reason: an inspection-only absence proof failure cannot authorize the operation. The original policy failure and legacy conservative candidate denial remain after this catch. This is failure-preserving fallback, not return-to-success from a failed proof.

Evidence: actual full-stack no-Git prose positive pairs and real Git/unknown-wrapper negatives pass. Additional /private/tmp/ticket-probe-failure-control.py injects UnknownShape and OSError into the second inspection in both branch/destructive policies; all4 controls preserve exit2 and original error. Its log is /private/tmp/ticket-probe-failure-control.log. Independent reviewer can rerun this isolated source-level fault control. No configured candidate program executes.

Falsification: a failed inspection returning none/absence authority for the tested Git candidate, dropping the original denial, or bypassing destructive shell fallthrough invalidates this disposition.

## F4: git_command.py:316 writing-tests-5

Reason: locator misses the actual reader_git_safety.py fixture, whose name/location differs from its inferred tests directories. The new classifier dependency is included in its bytecode fixture and inventory equality remains strict.

Evidence: reader16 passed, including alias normalization, per-message provenance, Unicode, quoted/nested wrapper denial, full16 configured guard stack, read proof and real effect checks. Independent runtime review reran its three focused methods. Full review-risk graph test passed, including removal/use/downgrade controls. This is not a claim all12 handlers have direct fault coverage.

Falsification: fixture no longer importing/executing this source, changed no-Git proof semantics or loss of mutation denial invalidates this locator disposition.

## Acceptance boundary

Each row is proposed as a demonstrated heuristic/expected-outcome false positive, not deferred real debt. Historical raw scan and source identities remain; adding review-only artifacts requires final full-snapshot reconciliation. Runtime/test changes require new scan and review. Protected CI, installation and live Craft evidence remain separate.

Verified-by: actual selected scan exit1/raw SHA above; bash hooks/_test/commit_detector.test.sh; python3 -B hooks/_test/reader_git_safety.py; python3 -B /private/tmp/ticket-probe-failure-control.py; full review_risk_test via version2 producer; named retained logs and independent source receipt.
