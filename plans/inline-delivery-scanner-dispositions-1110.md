# Metrics CLI scanner dispositions (#1110)

Complete selected scan: exit 1, not clean. The strict map now associates the metrics generator with its actual inline-delivery tests. The remaining flags expect raised exceptions, while the CLI contract reports an error and returns 1. The main function AST is equal to protected develop; new reference-reader errors still use that contract. Acceptance depends on the observed outcomes and caller behavior, not unchanged lines or a finding count.

The retained raw output, source/test/map/scanner identities, protected base, selected tree and executable actual-module controls are in inline-delivery-scanner-evidence-1110.json. Controls inject failure at the build boundary of the actual main entry point and assert its nonzero result and diagnostic. They do not claim every originating error path is covered.

| ID | Finding | Reason | Evidence | Falsification |
| --- | --- | --- | --- | --- |
| D01 | line 84 tests5 OSError | File/copy failure must make the checker report failure, not propagate to a test harness. | Actual main with OSError returns 1 and reports the error text. | Missing reference data yields success or no diagnostic. |
| D02 | line 84 tests5 ValueError | Invalid reference data is a failed check. | Actual main with ValueError returns 1 and reports the error; the actual FIFO reader test also refuses nonregular input. | Invalid canonical input yields success. |
| D03 | line 84 tests5 SubprocessError | Selector process failure must fail the checker. | Actual main with SubprocessError returns 1 and reports the error text. | Failed selection yields successful metrics. |
| D04 | line 84 tests5 JSONDecodeError | Malformed selector data must fail the checker. | Actual main with JSONDecodeError returns 1 and reports the error text. | Malformed data yields success or silently stale output. |

These are proposed individual dispositions pending the independent scanner receipt. There is no path exclusion, decorator suppression, exit remapping or clean-scan claim. Source and metrics correctness reviews remain separate.
