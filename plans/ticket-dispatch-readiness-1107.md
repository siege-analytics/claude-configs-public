# Ticket dispatch repair and readiness evidence (#1107)

## Context

Protected base: b3c560b18faabade9d47e49b3b39cb17883259c3. The readiness requirements in #1110 require a fix-or-accept decision for #1107. Exact baseline reproduction is retained in /private/tmp/ticket-dispatch-current-report.json: ticketless safe aliases/wrappers passed the configured Bash guard stack and a disposable ci invocation recorded subject only. Native commit-msg denied that message when invoked, but native registration is not universal across consumer repositories.

## Design

One shared Git normalizer resolves literal aliases, wrappers, global options and effective cwd. The existing message resolver checks each in-scope effective message separately. The shared code/data boundary and inspection-only redirect probe distinguish prose from executed Git; redirect inspection never authorizes a commit whose original message shape is unproven. Only a strict absence of Git can bypass the specialized Git policy. Branch/destructive checks retain their old decision for discovered or unresolved Git, and destructive non-Git rules still run.

Nonempty released-reader proof protects ordinary reads from quoted publication vocabulary. The native self-review fallback still handles empty/ref stdin. JSON extraction uses UTF8 bytes; only the ticket hook sets Python UTF8 mode. No candidate program, alias, editor or remote mutation runs during guard inspection.

## Acceptance

Deterministic ticketed -m/-F and canonical bounded message heredocs pass. Ticketless alias/wrapper messages, incidental ticket data, quoted amend/no-edit tokens, editor-dependent contents and temporal alias/file replacement deny. Proven routine reads and owned prose writes pass; actual Git, shared-resource mutations and unsafe wrappers retain their required controls. Scoped Git origin determines ticket applicability. Dynamic executable construction remains covered by the universal gate rather than a claim to inspect arbitrary programs.

## Assumptions

Local preflight is point-in-time feedback, not tamper-proof remote authority. Operator-controlled configuration and arbitrary external programs are outside literal dispatch proof. Unsupported editor/implicit messages must use a deterministic message route. Pure PR/issue text maintenance remains ceremony-free; metadata plus filesystem output remains a mixed operation. Existing native hooks add protection only where registered. No live source, settings, session gates, VERSION, installation or remote state is changed here.

## Ticket rubric exemption

Reason: historical issue #1107 has context, expected/actual evidence and constraints but lacks the rubric's named Acceptance, Design and Assumptions headings. Evidence: evaluate-ticket returned those three gaps; this artifact supplies the missing bounded contract, and the coordinator authorized this readiness repair. Falsification: a mismatch between issue intent, this contract and the reviewed source requires renewed design/review. This is the rubric's documented author-artifact exemption, not a passing evaluate-ticket claim.

## Pre-mortem

Severity: 50. A loose alias/code heuristic could create ticketless commits; an overbroad fallback could block routine reads or treat quoted prose as code. Changed configuration or message files before a later commit could invalidate preflight. Missing Unicode transport could turn a real command into empty input. Controls: per-message scope checks, strict literal normalization, rejected mutating companions, bounded existing message semantics, released-reader proof, UTF8 byte extraction and effect-based disposable fixtures. Implementation may proceed: YES, within the reviewed literal-dispatch boundary.

## Peer review

Independent read-only ACCEPT: plans/hostile-review-ticket-dispatch-1107.md. It binds the frozen runtime and tests by SHA256, records the earlier rejected quoted-wrapper fallback, and distinguishes reviewer observations from author suite results. Formal graph acceptance: plans/hostile-review-ticket-dispatch-graph-1107.md. Individual scanner F1-F4 acceptance: plans/hostile-review-ticket-dispatch-scanner-1107.md; the complete scan remains non-clean exit1. Final snapshot reconciliation remains separate from those source-bound approvals. Runtime SHA256 for git_command.py: 9047bb192cff0f6e4b5f8b0920fc0e511272ca3dab1c362e1033d952d6a753b6.

## Lead review

Function contract: literal dispatch returns normalized argv/cwd or an unresolved outcome; message inspection never borrows incidental command text. Chain: hook -> released read proof/normalizer -> scoped origin -> existing message resolver -> per-message ticket grammar -> allow/deny. The clean-code shelf's one-decision-per-place lens favors reusing those boundaries over another alias regex family. Readability assessment: 8/10; the combined compatibility CLI remains larger than ideal, but a broader extraction is outside this source freeze. No unresolved blocker is accepted by that readability observation.

## Quantified claims

Actual author suites: ticket 138 passed; reader 16 passed; commit detector 38 passed; destructive 32 passed; fix-shape 4 passed; self-review 819/820 passed. Logs are /private/tmp/ticket-dispatch-common-ticket-final.log, /private/tmp/ticket-dispatch-common-reader-corrected.log, /private/tmp/ticket-dispatch-common-detector-final.log, /private/tmp/ticket-dispatch-common-destructive-final.log, /private/tmp/ticket-dispatch-common-fixshape-final.log and /private/tmp/ticket-dispatch-common-selfreview-final.log. The corrected reader fixture includes its new released-reader dependency and retains exact byte inventory comparison; the earlier missing-dependency failure is preserved in /private/tmp/ticket-dispatch-common-reader-final.log. Separate actual empty/native-ref self-review controls retained denial. The independent artifact reports its own focused executions, not an independent full-suite run.

## Dependency and generated checks

Added immediate edges: self-review -> read-only-command and ticket-required -> git_command. Removed obsolete ticket edges to command-text.sh, commit-message-source and scope-check. Python data/message helpers remain audited Tier C dependencies. command-text.py is now in the explicit audited modification/deletion/rename/declared-B matrix. Every existing helper-removal/use and downgrade negative remains. Exact site/use digests: 1231a256a9f45177360f1dcdfb0a82f80282e28a9801fbe727ebd97b9c7fb9bb and 94457079e711f0e4be9ef27704231842e6c678b1bb0180f79be49bb6708c95f0. Ordered refresh and freshness checks passed via the existing pinned Homebrew Python/PyYAML environment; log /private/tmp/ticket-dispatch-ordered-refresh.log. Full review-risk regression passed through the version2 producer, with no source changes during the run; log /private/tmp/ticket-dispatch-review-risk-full.log. Complete selected scan returned exit1 with F1-F4 accepted one by one by an independent reviewer. See plans/ticket-dispatch-scanner-dispositions-1107.md and plans/ticket-dispatch-scan-evidence-1107.json for raw output, identities, reasons and falsifiers; no clean-scan claim or source suppression is used.

## Test plan and rollback

The local producer receipt uses an isolated synthetic task under /private/tmp/ticket-dispatch-local-evidence-1107; it does not attest a live Craft session. Final source commit is local only. Protected CI, accepted integration, release-to-main, backup, exact-source install and live canaries remain coordinator work. The default system Python lacked PyYAML; validation used the existing pinned Homebrew Python/PyYAML environment without package installation or global changes. Preserve existing user settings, task gates and unmanaged content. Revert this local change before publication if its boundary controls fail; do not disable hooks or rewrite main/history.

Verified-by: bash hooks/_test/ticket_required.test.sh; python3 -B hooks/_test/reader_git_safety.py; bash hooks/_test/commit_detector.test.sh; bash hooks/_test/destructive_bash_guard.test.sh; bash hooks/_test/fix_shape_guard.test.sh; bash hooks/_test/self_review_hook_819_820.test.sh; python3 bin/validate-local.py --mode refresh; retained logs named above.

Pre-mortem-artifact: plans/ticket-dispatch-readiness-1107.md
Hostile-review-artifact: plans/hostile-review-ticket-dispatch-1107.md

## Nov3 CA backstop correction

The CA reviewer found unresolved first-word executors returning handled without any resolved commit. Actual subshell, loop, command-substitution and opaque-wrapper callbacks reproduced the regression. The correction keeps unresolved executor payloads as possible code, while existing read/data classification and typed text-maintenance proofs preserve quoted prose. The fallback probe also retains this backstop; an exception cannot turn the same unresolved commit into success. Known foreign commits, foreign scope and ordinary data writes remain independent controls. This does not claim to execute or understand arbitrary programs.

The added callback matrix covers 110 controls: the original 16 forms, quoted watch/shell payloads, command substitutions, redirects, quoted prose, foreign scope and mixed commands. The complete ticket suite passed 248 scenarios and the actual reader/Git suite passed 16 tests after the correction. The latest source identity and CA closure supersede the earlier source-only approval for git_command.py; earlier review records remain historical evidence.

The first combined producer retained a 37/38 commit-detector failure: a built-in GitHub create body mentioning git commit was mistaken for opaque executable code. Canonical argv for literal gh issue/pr create now uses the existing code/data boundary; unknown executors keep their quoted payloads as possible code. Eight paired controls preserve bodies and redirects while denying real direct and opaque commit companions. The corrected detector passes 38 cases and the complete ticket suite passes 248. The failed producer receipt remains retained.

The CA closure review of tree d584d2fd reported four residual wrapper boundaries, additional prose regressions and optional-warning delivery failures. Its BLOCKERS verdict is retained as ca-peer-d584-full-report.md in the coordinator evidence directory, not converted to approval. The residual wrapper candidate boundaries now include subshell and backtick punctuation while preserving the current-repository scope check; four forms have own-scope, redirect, prose, foreign-scope and mixed-command controls. Built-in GitHub comment bodies use the existing data boundary. Current actual ticket coverage passes 276 scenarios, including 138 matrix controls. Nonisolated Python and sed expressions remain conservative under the bounded proof contract accepted by the independent native peer; isolated print-only Python passes existing positive proof.

The final bounded data check also proves simple literal sed in-place substitution forms: one expression, explicit filenames, no escapes or newlines and only nonexecution substitution flags. Actual execution expressions and opaque companions remain denied. Eight paired controls bring the ticket suite to 284, including 146 callback matrix controls. The scope-failure regression now covers both unresolved-shell and opaque-companion fallback paths; unavailable metadata must retain exit 2. Python without isolation remains unproven; the existing isolated read proof accepts print-only code. No arbitrary program introspection is claimed.

Final independent native review accepted the eight-source closure and C01/C02 dispositions; it independently passed the complete 284-case ticket suite, fifteen inline tests and scope/message failure controls. Its actual receipt is plans/peer-review-ca-findings-closure-1110.md. The CA service rate-limit failure and its prior blocking verdict remain distinct historical records. All sixteen final author integration groups passed without source or HEAD changes.
