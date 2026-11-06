## Context

Part of #1156, following #1162/#1163. Current develop 0c082661 contains the reviewed quote-aware test-tracking trigger. The filter removes quoted data so ordinary issue bodies mentioning `git push` do not launch the ignored-test scan. A shell reading that quoted text from stdin executes it, however:

```sh
printf '%s\n' 'git push origin feature' | bash
```

`ct_code_only` removes the quoted payload and the guard no longer sees its trigger. With an ignored `tests/test_*.py` present, this dispatch must reach the existing bounded scan and block. No real push is required for the regression.

## Goal

Preserve raw trigger text for recognized executable shell-stdin carriers while retaining quote-aware filtering for inert documentation and other non-executing consumers. Keep the existing scan deadline, offender cap, overrides and diagnostics unchanged.

## Acceptance criteria

- The literal printf-to-bash reproduction reaches the existing ignored-test rejection.
- Direct/absolute shell pipeline consumers with no arguments or optional `-s` retain visible trigger text.
- Quoted issue titles/bodies and printf-to-cat data mentions remain admitted without scanning ignored tests.
- Existing live-expansion and shell-c controls retain their denials; clean repositories still pass executable carriers.
- Preserve existing harness behavior; no host PATH fixture fix is claimed without a concrete reproduced failure.

## Assumptions and design before code

This remains a command-shape heuristic, not general shell execution analysis. Use a bounded literal shell-stdin recognition path to retain the raw command before the trigger check. Restrict recognition to executable dispatch positions rather than any occurrence of a shell name in data. Existing command-text fallback for helper failures stays conservative. No universal mutation permission, runtime installation, settings change or timeout increase.

## Investigation and pre-mortem

Source inspection confirms test-tracking-guard.sh applies ct_code_only before its trigger; quoted payloads disappear while the pipe consumer remains. The helper already handles shell-c arguments but has no stdin execution model. Tiger: matching any shell word anywhere would over-trigger inert quoted mentions; test printf payloads piped to cat and quoted shell names used as data. Tiger: a new filter could lose real executable triggers; red-first literal carrier plus absolute direct consumer must block with an offender. Tiger: source timeout must not be weakened; retain the actual six-second deadline/failure controls. Fixture PATH injection can be overwritten by a real `/home/craftagents/bin` prepend; isolate that optional bootstrap for the fake-runner cases if reproduced in an owned disposable policy fixture.

## Verification

Run the actual hook harness against disposable repositories, preserve baseline failures, run relevant fast-skip/source text regressions and validate source/package wiring if changed. Independent source review before publication. Root requested source preparation only: do not publish, merge or install this branch without follow-up.

## Bounded delivery and actual evidence

Root timeboxed the first repair to the reported direct pipeline. This patch recognizes a direct literal bash/sh/zsh/dash/ash/ksh consumer (including an absolute path), optionally `-s`, after an unquoted pipe in the quote-stripped command. It does not claim wrapped consumers, heredoc/here-string handling, encoded commands, or general shell interpretation. Heredoc/here-string and wrapped-shell cases remain unmodeled future limitations. No fixture portability edits were required by the actual local run.

The two new executable pipeline regressions returned exit 0 before the source fix, while inert quoted whole-pipeline and printf-to-cat controls passed. The baseline run later overlapped the source edit, invalidating its later timeout results; only the completed early regression cases count as red evidence. The final frozen-source full harness passed 29/29, including actual six-second bound and prerequisite controls. Raw logs: /tmp/test-tracking-1204-red.log and /tmp/test-tracking-1204-green.log. No real push was executed.
