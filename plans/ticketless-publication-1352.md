## Assumptions
Goal source: issue #1352 and PR #1335 discussion4559647055. Read the canonical ticket_reference function, all three commit/publication adapters, commit guidance, and real adapter fixtures. Keep the existing reference grammar unchanged; routine authorized work can use a meaningful [task: request] reference without a new issue or operator waiver. Bare [no-ticket] remains invalid.

## Test plan
The actual Python publication and artifact suites passed 37 tests in 38.414 seconds. The reference matrix exercises native commit-msg, native pre-push and tool publication for task references, project identifiers, URLs and the legacy structured override, plus bare, empty, malformed and missing negative cases. The actual risk suite passed 13 checks. The aggregate trailer suite passed 37 checks after its old diagnostic label expectations were updated; its first run had four label-only failures, not silently discarded. Full build and shell syntax checks passed. Generated inventory, source authority and loading metrics were regenerated through their normal producers.

## Findings
The duplicated two-token regex in each adapter contradicted the canonical commit grammar and documented task route. Each now calls the same ticket_reference function through a read-only message-policy entry point. No command execution, Git mutation, review-tier reduction, task binding or production scope change is added. Fixture-only copies include the canonical library dependencies and use meaningful task references so review behavior remains independently tested.

## Independent review
Separate reviewer result: plans/ticketless-publication-1352-independent.md. Exact-head review and required hosted CI remain necessary publication checks; local fixture results are not installed-runtime acceptance.

## Scanner disclosure
The staged scan returned 1 with two findings, retained externally as core1352-staged-scan-20261113.txt. The existing unresolved-Git fallback Pass remains byte-identical in main() apart from the earlier new message entry point; it deliberately continues to the conservative candidate check below, rather than granting an action. The second finding is the scanner's test-discovery miss for git_command.py: canonical ticket tests and the real three-adapter matrix live under hooks/_test, outside its searched test paths. The newly added UnknownShape handler rejects malformed/bare references with exit 2, exercised by the adapter matrix. This is not a clean-scan claim; inherited discovery debt remains tracked by #1329.

## Hosted probe correction
The first hosted run, 43372655666, failed because the source and generated-package synthetic probes copied the hook without its newly required shared parser library. The actual built consumer already contains that library. Both isolated probe builders now copy the real hooks/lib tree, retaining their missing-reference, no-op and symlink denial controls. The corrected contract suite passed all 21 cases in 2.908 seconds. The failed run is retained; a corrected source head requires fresh hosted CI.

The probe-only corrective staged scan reported five existing gate_contract.py exception-test coverage findings. Its only code changes are the two dependency-copy lines; the handlers are unchanged. Raw output is retained as core1352-probe-correction-staged-scan-20261113.txt, with inherited coverage debt under #1329. The generated actual package probe also passed.
