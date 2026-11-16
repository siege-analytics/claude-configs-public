# Scanner host path boundary: #1357

## Assumptions
Read resolve-think-gate.py scanner selection and scanner_capability.py physical/owned_plan. Selection compares canonical Task paths, while the subsequent authority call forwarded raw host paths. Host spelling is not an additional authority grant. Producer, input, scratch and output validation remain unchanged.

## Test plan
The permanent actual-hook regression failed three positive subcases on unchanged a64 source: trailing session slash, symlinked parent component, and both together. Corrected source passes these cases and rejects a foreign session. Full scanner suite: 20 tests passed in 28.933 seconds. Supported unbound test-evidence producer recorded the focused regression in 0.823 seconds; no host identity was invented or cleared.

Build check, skill inventory freshness, generated source authority freshness and diff check passed.

## Findings
Only the resolver-to-owned_plan call changes: canonical gate and session identity paths match the existing selection predicate. No general symlink exemption or scanner input permission is added. An alias changing the session basename remains outside existing host identity recognition.

The complete staged scan remains non-clean with 63 inherited resolver diagnostics. Its normalized diagnostic multiset equals the previously independently accepted core1345 merge scan, and all 33 exception-handler ASTs equal protected a64. No new diagnostic or handler is introduced; existing debt remains tracked by #1329. The initial scan also caught one new prose em dash, which was removed before the final scan.

## Independent review
Root read the full source/test diff, accepted the canonical host identity boundary with unchanged physical input closure, and independently ran the regression: passed in 0.833 seconds. Root accepted the inherited 63-row scanner rebind with this boundary-specific test. This record does not claim installed or native runtime qualification.
