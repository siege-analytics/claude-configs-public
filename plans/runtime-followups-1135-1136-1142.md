# Runtime reliability follow-ups

Pre-mortem-artifact: plans/runtime-followups-1135-1136-1142.md
Hostile-review-artifact: plans/runtime-followups-1135-1136-1142.md

## Assumptions

The operator authorized continued repair toward the intended architecture. Keep released main installed while developing in this isolated worktree. Preserve per-task authority, input bounds, native CLI isolation and operator state. Backend capability differences remain explicit; no unsupported vendor patch or model switch.

## Design and pre-mortem

Use one metadata serializer for the router, mutation guard and legacy exports. Keep every decision-bearing command/path/identity value intact; exclude content/edit bodies from environment transport. Original semantic input stays on stdin or an inherited descriptor, including complete spawn prompts/results for fingerprinting. Pin the shared helper in the registration receipt before import. Invalid metadata cannot become mutation authority; prompt-only diagnostics remain advisory.

Audit sites: six resolver prompt guards (identity metadata only; semantic extraction uses original shell input), universal mutation guard (exact command/target metadata), test guard (identity metadata; native Git update lines remain separate), hub concurrency (identity metadata plus full semantic payload on fd3), router (sealed identity before projection, unchanged raw stdin to children).

Improve scanner test discovery without treating file presence as handler coverage. Same-snapshot test evidence and actual raises/assertRaises AST checks remain required. Comprehension free-variable loads must count without counting shadowed loop targets. Locate the empty-repo grep emitter before changing its behavior.

## Peer review

Requested bounded independent review through Siege Claude Hub (261020-ivory-comet), reusing reviewer 261019-lucid-puma. Review is in progress; this candidate commit enables exact-Git fixture verification and is not an approval or install receipt. Final source pin file: /private/tmp/runtime-followup-source-pins.json.

## Lead review

Reproduce each reported failure first, then test large legitimate payloads and scope/identity/size negatives. Do not use a scan-count waiver or omit required failures.

## Quantified claims

Prototype checks: 5 real-hook transport/bounds tests and 23 selected-source scanner tests passed, with legacy scanner shell suites passing. Source self scan emitted no findings. These precede candidate commit and do not replace exact-head tests or protected CI. No new live runtime or backend parity is certified. Final test/scan/CI/install receipts will record exact source and observed effects.

## Test plan

Shared metadata contracts, real router/guard large-input controls, scanner missing/unrelated/snapshot evidence negatives, reproduced diagnostic regression, generated freshness, native push and required protected CI. Install only accepted exact main and repeat bounded host acceptance.

## Candidate verification

Candidate d0ffc87 passed all 29 router tests through the real reviewed-deployment fixture, without relaxing source authority. The final serializer review removes an artificial two-container nesting cutoff so every recognized nested identity survives projection. The CLI catches ValueError (which includes UnicodeError); TypeError cannot originate from decoded JSON values. Invalid UTF-8 is tested through the actual CLI. Explicit maps now include the router and installer fixtures as well as tooling tests. These are bounded final adjustments awaiting the same independent reviewer; no live apply.

The broader task-keyed suite completed 72/72 controls (prototype source run); the ordered refresh completed with all generated checks current. Final scanner verification passes 24 cases, including locals() in a comprehension body versus its outer iterable. Router29, payload5 and scanner23 also completed through the actual test receipt producer at1045020; the scanner source change requires a new receipt before push. No test-gate hand editing or bypass is used.

Final source audit found that actual unittest.assertRaisesRegex evidence was omitted from scanner inference. Recognize that standard assertion beside assertRaises, with a matching-class positive and unrelated-class negative. This changes evidence recognition, never test-file-existence waivers. Native/CI acceptance will rebind after this source change; source scan remains conservatively non-clean for other handler evidence and existing cleanup paths.

## Independent integration findings and corrections

The existing Craft reviewer reproduced two compatibility regressions: malformed hub callbacks changed from advisory exit0 to2, and empty-stdin standing-order invocations stopped before reading explicitly bound signals. Root reproduced both against the candidate. Hub preflight now retains only the established malformed/non-object-input advisory behavior; valid callbacks with oversized required metadata still exit2 before taking a reservation. All six advisory prompt guards use an empty object only for genuinely empty stdin, preserving environment-bound diagnostics without changing original semantic input.

Post-correction execution: hub legacy26 scenarios and session-signal18 scenarios pass; real transport6 tests pass, including malformed/empty hub controls versus valid oversized metadata denial with no ledger created. Independent scanner failures were run under a different interpreter/temp environment and require a controlled rerun before classification. Source review is still pending final pin rebinding. No live apply or permission change occurred.

## Protected CI dependency audit correction

Superseded CI at1a5bbd2 stopped at the exact helper-edge audit before hook scenarios. The shared metadata helper adds seven literal invocation sites on registered enforcement entrypoints. Added those exact edges and refreshed their frozen invocation-site digest, retaining removal/duplicate/comment-decoy/variable-use negative checks. The helper, its dedicated test and the versioned scanner evidence map now explicitly receive the C review floor; no tier was downgraded. The full review_risk_test.py audit passed, and generated review-risk metrics/check passed. These policy/test/metric files require final bounded independent delta review; CI must rerun at the final commit.

The hub's dependency-boundary questions prompted a further audit improvement: registered shell entrypoints' direct inline Python imports now count as real helper edges. The audit records the mutation gate's metadata-helper import and the two session-anchor imports, with exact frozen site evidence and the same removal/stale-digest controls. The transport test launcher also explicitly receives C, closing the indirect test-disable floor gap. Full review_risk_test.py passed with these controls; risk metrics are current. The graph's scope is registered entrypoints; the unregistered retained review guard remains C by its path pattern, and the global router's dynamic helper load is separately covered by registration-hash verification and its real negative test. No blanket dynamic-import completeness claim is made.

## Native interpreter compatibility correction

The repo-local map initially introduced a TOML parser requirement on every mapped scan. A direct native /usr/bin/python3 (3.9.6, neither tomllib nor tomli installed) reproduction returned incomplete2. Replaced only the new map with .claude/scanner-test-map.json, strict schema_version1/source_to_tests, duplicate-key rejection, canonical Python paths and same-snapshot declared inputs. The existing optional TOML decorator-config behavior is unchanged. Both the direct AST CLI and complete staged-snapshot scan now return0 for the mapped positive under that actual system interpreter, with no runtime package installed. The first staged fixture correctly reported an untracked declared test as missing; after explicitly staging that fixture test, both native paths passed. Before/after raw results are /private/tmp/followup-native-map-before.json and /private/tmp/followup-native-map-after.json.

The snapshot selector includes the JSON map. Validation also runs for map-only diffs and sources without handlers. Scanner27 and all legacy scanner shell suites pass; added malformed/version/bool/duplicate/path and no-TOML-import controls. Ordered generated refresh passed. The new map is C; the old optional TOML config retains its C floor, so no review floor was lowered. The final five production Python sources must receive a new real test receipt before push, and this bounded scanner-only delta needs the same independent reviewer. Earlier runtime helper/guard bytes remain unchanged.

The full review-risk audit also passed with the JSON map path and retained TOML floor.

An actual near-limit UserPromptSubmit payload plus100KB ambient environment now passes through all six advisory guards (transport suite7/7). A controlled before/after probe using released392fe4b think-guard bytes reproduces Argument list too long/exit1; candidate bytes return0 without that diagnostic. Raw command, byte count, hashes and results: /private/tmp/followup-prompt-transport-revert.json. This supplements the large edit and full hub-payload controls with the precise prompt transport failure shape.
