# Promotion review residuals

Refs: #1107, #1110, #1147

## Plan

Reproduce all six automated review findings against develop 863abba in disposable repositories. Correct only verified ticket dispatch, traceability, selector publication and metadata transport failures. Retain the existing read, foreign repository, mixed mutation and failure controls. Freeze source bytes before independent review, ordered refresh and a source-bound producer. Use a feature PR to develop; do not modify main or the live installation.

## Assumptions

The Git helper performs literal inspection, not arbitrary program introspection. The existing Git prefix parser owns global-option, alias and target-directory resolution. Inspection-only comment handling is unavailable to ordinary mutation classification; its default lexer remains unchanged. An unresolved target cannot borrow the payload cwd's foreign scope. Non-Bash metadata keeps its independent 96 KiB bound; the 64 KiB command bound belongs to Bash.

## Corrections

- Review comments 4462865225 and 4462865244: structured trace fields and task identifiers require non-whitespace content. Other ticket formats remain available.
- Comments 4462865254 and 4462865262: opaque argv is inspected through the existing literal lexer and Git prefix resolver, including global options and target paths. Failed target inspection remains conservative. Parsed comment-bearing Git commands resolve their actual target before message checks. Dashed external Git forms retain their old conservative boundary.
- Comment 4462865223: any failed selector output is discarded, including small resident-looking stdout. Delivery keeps the canonical kernel and the visible selector-unavailable diagnostic.
- Comment 4462865269: only Bash uses the command-specific 64 KiB bound. Other tools still obey the complete metadata bound.

## Pre-mortem

A broader read exception could release an executable payload, while a raw-text check could mistake prose for a command. Target inspection must distinguish foreign cwd from the actual Git -C target. Lexical inspection must not authorize ordinary mutation comments. Failed selector stdout must never become resident policy. Tests retain these paired positives and negatives, including paths with spaces and explicit diagnostics.

## Peer review

Independent native review accepted all eight frozen source changes and each scanner disposition R01-R13. A separate independent review accepted the canonical-path fixture correction and ran its explicit alias control. Actual receipts are retained in the adjacent peer-review files; service status is not substituted for source closure.

## Lead review

The coordinator inspected the source and paired tests, read all three independent receipts, and rehashed all nine frozen inputs. Its adversarial pass found the intermediate dashed-Git regression; the correction and its own/foreign controls passed before freeze. Affirmative standards are complete kernel publication, nonblank traceability, literal target-derived Git scope, unchanged ordinary mutation parsing and retained metadata bounds. Source lead review accepted the bounded corrections; protected CI and live installation remain separate.

## Quantified claims

All six old-source findings reproduced. The final source-bound producer passed all nineteen groups under stable HEAD 863abba with nine unchanged declared inputs. It includes 331 ticket scenarios, sixteen reader tests, sixteen delivery tests, ten payload tests and twenty-seven scanner source tests. Full review-risk and final freshness passed. No dependency snapshot or floor was changed. Failure-bearing first attempts remain retained; the receipt keeps the actual precommit tested revision.

Pre-mortem-artifact: plans/promotion-review-residuals-1147.md
Hostile-review-artifact: plans/peer-review-promotion-residuals-1147.md
Verified-by: bash hooks/_test/ticket_required.test.sh; bash hooks/_test/reader_git_safety.test.sh; python3 -B bin/_test/inline_delivery_test.py; python3 -B bin/_test/hook_payload_test.py; review_risk_test.verify_dependency_graph(); durable promotion-evidence-20261103 logs.

## Canonical test-path correction

The first nineteen-group producer retained one failure: scanner test lookup returned the canonical private/var path while the fixture expected its var alias. The assertion now compares canonical identity and tests an explicit repository symlink as well, retaining the TOML-unavailable behavior. This is a fixture oracle correction, not a production path change or a shorter temporary-root workaround. Its actual failed receipt remains retained; the replacement nine-input producer passed all nineteen groups. Unknown owned shell groups remain conservative; the preserved read claim covers the actual proved and paired read fixtures, not every grouped command.
