# Local full validation preflight

Ticket: https://github.com/siege-analytics/claude-configs-public/issues/1156
Goal source: root's authorized implementation assignment for the independent tool-preflight slice, 2026-11-04.
Source baseline: c7a6fe757dd0b4d51f70776785a5d9c4a36cef87, containing develop 56bc3a6.
Status: prework design, recorded before implementation.

## Investigated facts

`bin/validate-local.py` dispatches selected validate-job run commands through PATH Bash, with isolated Git/shell startup variables. Its outer Python dependency check does not check the child PATH python3. `RUNNER_TEMP` is physical but inherited `TMPDIR` remains unchanged. Synthetic adapter tests use tiny workflows; they must not acquire unrelated Git/base64 requirements.

Prior local release-prep logs show: Linux actual-commit custom-string cleanup fails because Git does not strip `;;` (`core-1154-linux-intermediate-full.log:3227`); Darwin reader real-effects control fails with GNU base64 `-D` (`caution-full-validation-controlled.log:2580`); Darwin temp alias fails with registration symlink diagnostic (`caution-full-validation-mac-tmp-alias-failed.log:589`); physical TMPDIR alone leaves managed command-vector failures (`caution-selected-registration-physical-tmp.log:13`), while exact python3 spelling control passes (`caution-selected-registration-python3-control.log`). No Bash version floor is inferred. Actual selected commands use arrays/nullglob, pipefail, process substitution, here-strings and NUL-delimited read.

## Design and authorization

Only full execution gets early probes, before any selected workflow step. `--list`, check and refresh retain their existing prerequisites. Small explicit selection rules recognize actual known hook suites and Python commands, not a new shell dependency engine. All selected child environments (including step bindings) are checked. A selected hook suite needs actual multi-character Git comment stripping; Darwin reader selection needs actual PATH base64 decode/output behavior. Selected build/registration entrypoints need the pinned YAML dependency in the child PATH python3; registration additionally needs lexical absolute reported interpreter agreement with outer sys.executable (never realpath-normalized). Unrelated synthetic Python snippets acquire neither extra predicate. Full dispatch checks actual Bash features with bounded subprocesses. Probes write only disposable scratch fixtures. Failures identify feature, affected step and remediation; no install, PATH rewrite or skip flag.

Child-only TMPDIR and RUNNER_TEMP share a resolved physical temporary directory. This does not alter HOME or process-global environment. Existing isolation and group cancellation remain intact. No hooks, classifier, policy or installed settings change. Root owns integration/release; stop after focused tests for review, before commit/push.

## Risks and verification plan

Tiger 1 (blocking if present): broad dependency selection can invalidate synthetic workflows. Use exact known suite paths/glob plus direct python3 command detection; test unrelated full workflows and preview/check/refresh negatives.
Tiger 2 (blocking if present): symlink normalization could hide the interpreter vector mismatch. Compare lexical absolute strings and test two symlink names of the same binary.
Tiger 3 (blocking if present): preflight may run after side effects or under a different environment. Probe before all steps using effective step bindings; test a leading marker and per-step PATH failure.
Paper Tiger: platform probe could require BSD base64 on Linux. Darwin-only condition follows the actual Darwin fixture.

Focused tests retain all existing dispatch, startup isolation, failure propagation, timeout and descendant-cancellation controls; add incompatible feature shims, no-side-effect assertions, literal interpreter mismatch, physical TMPDIR and unused-prerequisite controls. No shared catalog regeneration or unrelated full suite before root review.


## Focused validation and source freeze

Implementation changes are limited to the adapter and its tests, plus this plan. Child environments use a physical temporary directory even when a step supplies temp-directory bindings. Feature selection recognizes the current CI entrypoint spellings and its hook-array assignment; it does not infer dependencies from echoed paths or arbitrary shell syntax. New CI entrypoint forms need an explicit adapter update.

Using existing `/Users/dheerajchand/.venvs/ccp/bin/python3` with its bin directory and `/opt/homebrew/bin` in the invocation PATH (no installed environment changes), `bin/_test/local_validation_test.py` passed 15 tests. These retain the prior seven dispatch/isolation/timeout tests and add eight scoped controls. A preflight-only call against `full_steps(workflow_steps())` passed without dispatching workflow commands. `git diff --check` passed. The earlier default `/usr/bin/python3` attempt stopped at missing YAML; no dependency was installed.

No commit, push, protected merge, shared catalog regeneration or full workflow execution performed. Root/peer review is the next gate.

## Selector review correction

Root review identified that per-line tokenization could mistake heredoc bodies and multiline quoted echo text for executable entrypoints. Before any per-line recognition, the adapter now tokenizes the complete command and conservatively disables prerequisite inference on parse failure, multiline tokens (LF/CR), or tokens mentioning `<<`. This also excludes here-strings and quoted heredoc-marker mentions. Unsupported complex shapes lose only the early diagnostic: the actual selected workflow commands and tests still execute unchanged. This is conservative, not a general shell parser.

New controls cover heredoc build text, multiline quoted registration and hook-array text, quoted delimiter mentions and incomplete quoting. Actual subprocess controls run synthetic data commands with incompatible unused Python/Git/base64 shims and assert their marker completes without touching those tools. A selection smoke assertion retains all four current CI prerequisite-bearing steps. The updated focused suite passed 18 tests; a fresh actual-command preflight-only smoke passed with all four selections intact, without workflow dispatch. Existing protected-state, temp, first-failure and cancellation controls remain.

## Publication candidate

On 2026-11-05 this isolated branch fast-forwarded from c7a6fe7 to published main f004df3c66cf6374548cfc49d0e49c375aa4376c. The adapter and test bytes retained their previously reviewed SHA-256 values: 1222a0d6621061848dc9afcd12de397d1db46c05b9b7cd3e2cdb4e7f51a8ce60 and 807b74f1fcd2da6e45d68e3cb87e3a6f3579303445946c33d13b06886ad7e61f. No new source behavior was added during publication preparation.

## Assumptions

This improves the local full-validation runner, not Craft hook permission or a replacement for protected CI. Its selected prerequisite adapters recognize the current workflow entrypoints. Unrecognized complex commands still run unchanged; they receive no guessed extra requirements. Existing tools and dependencies are selected by the caller without installation or global configuration changes.

## Peer review

Prior independent source review accepted the prototype after Root identified and corrected heredoc/multiline data misclassification. The source hashes above remain unchanged. Final direct PR review and protected exact-head checks remain pending at candidate publication; no merged or installed status is claimed.

## Lead review

Feature probes precede workflow side effects under the same per-step child environments. Runtime and Git startup markers remain isolated. Physical temporary paths apply only to full-mode children; check, refresh and preview retain their existing dispatch contract. Timeouts kill disposable probe process groups and propagate failures. No validator or workflow step is skipped.

Pre-mortem-artifact: plans/local-full-preflight-1156.md#risks-and-verification-plan
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1156

## Quantified claims

The current eighteen focused tests passed in 8.925 seconds using the existing CCP Python environment. A separate actual-workflow preflight-only invocation passed all four prerequisite-bearing selections without dispatching workflow commands. Generated-source-authority check passed unchanged. The first smoke invocation lacked its import path and failed before probes; correcting the smoke harness import path produced the reported pass without changing source. Full workflow execution is not claimed locally; protected CI remains required before merge. Raw focused log: /tmp/local-preflight-1156-focused-final.log.

## Canary and rollback

Synthetic workflows prove incompatible selected tools fail before marker writes, unused tool shims remain unused, and full children receive physical scratch paths. No installed files or settings change in this slice. A normal source revert restores the previous runner if the candidate regresses an actual environment.

## Selected scanner disposition

The first exact staged scan completed nonclean with seventeen findings: five plan wording findings and twelve AST findings. The plan wording was corrected. The source findings have these bounded interpretations, for independent review; no clean scan or exhaustive exception-branch coverage is claimed.

- `full_prerequisites` at line 147 catches tokenization ValueError and continues only prerequisite inference. Actual workflow dispatch remains unchanged and synthetic malformed/data-shape tests verify that unused tools are not inferred.
- `probe` at line 121 catches ProcessLookupError only after attempting to kill its isolated process group; that means the group has already exited. It then waits with a five-second bound and re-raises the original failure. It does not convert timeout/cancellation into success.
- The ten writing-tests-5 findings require a pytest.raises convention in a unittest/subprocess suite. Actual CLI failure propagation, timeout and malformed workflow controls are the relevant contract here. This mismatch is not evidence that every reported internal exception type has been individually raised. Existing run-step cancellation and the main error-reporting boundary remain covered by their retained tests; no exhaustive syscall-race claim is made.

Raw original scan: /tmp/local-preflight-1156-staged-scan.log. Corrected staged rescan is retained separately. No ignore option, scanner suppression or production exclusion was used.
