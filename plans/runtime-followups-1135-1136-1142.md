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
