# Scanner runtime recovery independent review

Verdict: approved for this bounded scanner/test delta. No remaining must-fix
finding in the reviewed scope. Review-only: no source edits, source suppression,
generated-catalog changes or installed/global configuration operations.

Reviewed working integration source in
/private/tmp/claude-runtime-integration-20261029: scanner shell transport/error
handling, scanner fixture subprocess budgets and its two new scanner regressions,
plus the malformed-reader/offset regression and actionable platform skips in
hooks/_test/reader_git_safety.py. Task-actions/read-classifier production behavior
was not changed in this slice. This receipt does not approve the final whole
branch, remaining scanner dispositions or protected CI.

## Scanner transport and completeness

The old per-line loop process substitutions could retain descriptors under stock
macOS Bash 3.2 until the enclosing function returned. A large diff could therefore
produce resource errors while the scanner still exited one. That provisional run
is incomplete, regardless of whether it also reported valid findings.

The final match_lines helper captures each grep match stream, distinguishes
ordinary no-match status one from matcher failure greater than one, and returns
an explicit incomplete result for failures. The caller consumes captured text
through a here-string and propagates failure as exit two. Diff and message modes
both use that propagation. Empty match streams emit no finding, while multiple
matches on a line retain separate reports. The change does not suppress findings
or reinterpret a complete finding-bearing result as clean.

Independent actual checks:

- ScannerSourceTest.test_large_diff_under_small_descriptor_budget_completes:
  passed using /bin/bash and RLIMIT_NOFILE=64 against a real staged 120-line diff.
- ScannerSourceTest.test_lexical_match_process_failure_is_incomplete: passed;
  injected grep status two produces scanner exit two for both staged-diff and
  message modes.
- Those two methods passed in 7.924 seconds. Log:
  /private/tmp/scanner-fd-independent-targeted-test.log.
- A direct stock-Bash message smoke test with two banned adverbs returned one
  and reported both matches, preserving non-clean semantics and multiplicity.
- Shell syntax and scoped diff whitespace checks passed.

The coordinator separately reported the complete scanner-source suite passing
21/21 in 21.149 seconds at /private/tmp/runtime-scanner-source-final.log. The
selected test subprocess timeout additions keep their arguments/assertions and
bound otherwise unchanged temporary Git/scanner operations.

## Reader syntax and nested offset control

The new reader test independently passed in 0.080 seconds; log:
/private/tmp/reader-syntax-independent-test.log. It proves malformed Python source
is not read-only authority, malformed quoted shell syntax yields the unknown
verb and nonzero read-classifier result, and attached grep-option expansion is
accepted at value offset ten but rejected at key offset two.

The shape offset parameter is used inside the nested generator expression.
The paired positive/negative test demonstrates that behavior directly; a scanner
complaint that the parameter is unused is a heuristic false positive, not a
reason to remove the parameter or alter classification. No production behavior
change was needed. Revised platform skip messages name how to run the real
controls rather than presenting an unexplained skip.

## Acceptance boundary and classification

Agree with the proposed Tier C floor for scan.sh, scan_ast.py, scan_snapshot.py,
the three scanner acceptance policy SKILL documents, and scanner_source_test.py.
Those files control source selection, evidence completeness and acceptance.
The floor must cover modifications, deletions and rename source paths using the
normal protected-policy tests; it is not a substitute for those checks.

A fresh complete full-branch scan remains mandatory. The provisional
/private/tmp/runtime-fullbranch-scan-provisional.log contained a resource failure
and cannot supply a complete/non-clean acceptance record. Remaining raw findings
require the independently reviewed per-finding evidence contract. This approval
neither supplies those dispositions nor converts exit one to a scan pass.

## Reviewed source identities

Working-file SHA256 values at review completion, before final commit binding:

- skills/detect-ai-fingerprints/scan.sh:
  e7fc8ef0ab0c77a5e196fbbe26ae2a718463f49a168e90d5fe1de7526896b939
- bin/_test/scanner_source_test.py:
  6e9ff64758b01a3b98fe7c3fca3e6031a503c745e41470124e5d117fc4e15a8e
- hooks/_test/reader_git_safety.py:
  af749405294c0a456fd2e97e7eb8c829a5c9827bd30e367e4da037b8c8ae1222

The coordinator owns the final committed identity, aggregate tests and complete
scanner rerun. Later source changes require scoped re-review.
