## Assumptions

Fix #1395 from verified develop e50be6fcc17bc7fa208209b0272a5223463a98d4. Qualified remote evidence has active GIT_CONFIG_COUNT=1 with a credential.* key; no credential plaintext is needed. Environment presence grants no authority. The existing producer authentication contract supplies one canonical child context for preflight and execution, with actual Task ownership and selected repo/index unchanged.

## Test plan

The real hook reproduced the credential-count preexec refusal before the fix. Focused5 passed5.032s. The final supported Task-bound producer passed scanner32 in38.686s, source28 in26.643s, registered4 in3.307s, review-risk and build/authority/inventory/metrics/validator checks. It used the actual CODEX_SESSION_ID through supported native SESSION_ID mapping and --think-gate, writing the actual adjacent test-gate.json. The initial unbound successful receipt is preserved separately; it was not edited into a Task-bound receipt. Full build passed before these checks.

The real credential-count hook-to-producer case verifies selected repo/default tree, unchanged input environment and absence of the injected helper marker. The context spy checks all3 preflight Git calls under active config channels. Local helper audit remains a real denial under GIT_CONFIG, count and malformed parameter injection. Existing foreign target/index, working filter, transport/helper and source-closure negatives remain in the maintained suites.

## Findings

Validation previously rejected configuration before the producer isolated it. A shared execution_environment now precedes every preflight Git read and the scanner child. It strips ambient config channels instead of trusting credential configuration; target/index/object overrides remain refused, and fixed fsmonitor/hooks settings remain in effect. All three source closure pins changed together. The final scanner is COMPLETE NONCLEAN42, raw dc1a9c0f8fb5bb1fa9420196f848ccd9041c9b7671177baf83735d2d82adccd2. Each reported handler matches published e50 AST; caller relevance and per-row Reason/Evidence/Falsification are retained in core1395-final42-proposed-dispositions-20261114.json. This is not a clean scan or a claim that each exception was fault-injected.

## Independent review

Root inspected the actual production/test diff and all42 findings, compared the handler ASTs with published source, verified final source hashes and accepted the changed canonical-context caller and residual dispositions: https://github.com/siege-analytics/claude-configs-public/issues/1395#issuecomment-6869399562. Required hosted CI and installed/native acceptance remain separate observations.
