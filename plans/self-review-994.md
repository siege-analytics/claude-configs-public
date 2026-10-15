# Self-review: effective ticket commit messages (#994)

## Assumptions

Domain(s): software engineering, governance enforcement, shell/Git safety
Geospatial cross-cut: no
Working as: software engineer, tech lead
Goal source: https://github.com/siege-analytics/claude-configs-public/issues/994
Goal source verification: issue #994 requires validation of the effective Git commit message, correct `-m`/`-F`/stdin/amend/template/`-c`/`-C` semantics, hostile path and quoting tests, native hook alignment, and elimination of unrelated argv ticket bypasses.
Pre-author-inventory: `plans/investigate-994.md`
Investigate-artifact: `plans/investigate-994.md`
Pre-mortem-artifact: `plans/pre-mortem-994.md`
Hostile-review-artifact: `plans/hostile-review-994.md`
Project-contribution: replace incidental command-string matching with one bounded effective-message contract shared by pre-tool and native Git enforcement.

## Pre-implementation comprehension

The original hook grepped all of `tool_input.command`. It therefore rejected ticketed message files and accepted ticket-like text in unrelated options or pathspecs. Git itself has multiple message sources and editor/cleanup stages, so correctness requires resolving only deterministic sources and failing closed when shell, editor, repository configuration, or unsupported Git options can still alter the result.

## Pre-author inventory

- `hooks/git/ticket-required.sh` contained all ticket grammar inline and skipped amend/no-edit unconditionally.
- `.githooks/commit-msg` had a narrower duplicate grammar and receives its file before final cleanup.
- `hooks/lib/` had no shared effective-message parser; existing security guards use `shlex` only for much narrower command shapes.
- `hooks/_test/ticket_required.test.sh` had 23 command-string scenarios and no file, cwd, stdin, repository-state, option-order, or incidental-argv negatives.

## Peer review

Independent Git-semantics and security reviews found and drove fixes for unsupported global-option bypass, newline chains, cleanup removal, heredoc context, shell comments, pathname expansion, `CDPATH`, mixed overrides, bounded reads, and descriptor-pinned path traversal. CodeRabbit's exact-SHA review then found wrapped `bash -c` command text and five harmless long-form flags; the reporter's focused F4 review found the new helper below the accepted Tier C dependency boundary. Each finding and resolution is recorded in `plans/hostile-review-994.md`.

## Lead review

The shared parser is large because it defines a security boundary, but it remains narrower than a shell: no evaluation, explicit supported Git forms, exact message-source precedence, and visible fail-closed errors for uncertain forms. The native hook uses the same ticket grammar and conservatively validates only cleanup-stable content. Repository confinement and bounded reads are enforced at the file-descriptor boundary rather than by string checks alone.

## Findings

| ID | Priority | Description | Resolution |
|---|---|---|---|
| R1 | P1 | Initial helper treated unsupported Git global options as unrelated commands. | fail closed when `commit` follows an unsupported global option |
| R2 | P1 | Shell comments/newlines/expansion could diverge from parsed argv. | quote-aware comments and newline/path-expansion rejection; chains/wrappers/groups block |
| R3 | P1 | Cleanup could remove a reference accepted before or during native hook execution. | inspect configured cleanup pre-tool; validate cleanup-stable native content |
| R4 | P1 | Resolve/stat/read sequence left path replacement concerns. | canonical in-repo target plus pinned no-follow descriptor traversal |
| R5 | P2 | Input caps were applied after full reads. | bounded JSON, message-file, native-file, and revision reads |
| R6 | P2 | Native ticket syntax drifted from pre-tool syntax. | one shared validator and positive/negative native fixtures |
| R7 | P1 | Wrapped commits inside a single `bash -c`/`sh -c`/`eval` token returned NOT_COMMIT. | detect raw commit text across joined tokens and within each token at every parsed non-commit exit |
| R8 | P2 | Five harmless long-form flags false-blocked while short forms passed. | accept all five and add one positive fixture per form |
| R9 | P1 | Accepted F4 policy classified authoritative `commit-message.py` as Tier B. | exact Tier C pattern, both caller edges, pinned graph snapshots, and exhaustive staged-shape downgrade tests |
| R10 | P1 | Literal raw-text scanning missed `bash -c 'g"it" commit …'` shell quote concatenation. | recursively tokenize static wrapper scripts without execution and fail closed for direct, obfuscated, nested, or dynamic/indeterminate commit-capable forms |
| R11 | P1 | Initial R10 fix overblocked unrelated static `bash -c`, `sh -c`, and `eval`. | return NOT_COMMIT when recursive static analysis proves no commit; add three positive non-interference fixtures |
| R12 | P1 | `bash -c -- 'g"it" commit …'` executed the script after an option terminator the analyzer treated as terminal. | once `-c` is present, continue past `--` and recursively inspect the next command-string token; add exact exploit fixture |
| R13 | P1 | `bash -o pipefail -c …` hid `-c` behind an option operand mistaken for the script. | statefully locate short `-c` clusters/`su --command` across operands and analyze the actual next script; add direct, nested, and positive controls |
| R14 | P1 | `su -cSCRIPT` attached the command operand to the short option, leaving no next token to inspect. | parse content after `c` as an attached script for `su`; add exact blocking and unrelated positive controls |
| R15 | P1 | Inline `git -c alias.c='!git co"mmit" …' c` executed a commit while the visible subcommand returned NOT_COMMIT. | resolve static/chained/shell inline aliases without execution and fail closed for config-env/dynamic indeterminacy; add three exploits and two positives |
| R16 | P1 | BSD/GNU `env -S`/`--split-string` retokenized an opaque operand into `sh -c` plus an obfuscated commit. | recursively inspect split-string operands; add short/long exploit fixtures and a static non-commit positive |
| R17 | P1 | `xargs` input substitution supplied `commit` as a Git subcommand after static command parsing. | fail closed for visible xargs→Git dispatch with dynamic/unknown subcommands; add exact exploit and unrelated pipeline control |
| R18 | P1 | Control-token handling returned NOT_COMMIT before detecting an obfuscated commit inside a piped shell wrapper. | run wrapper/alias/xargs analysis on full tokens before every chain/pipeline exit; add exploit and unrelated positive |
| R19 | P1 | GNU `xargs -a file` supplied a Git subcommand without any control token, bypassing the control-only xargs guard. | invoke xargs dispatch analysis before ordinary non-Git exits too; add file-fed exploit and unrelated positive |
| R20 | P1 | Pushed candidate `140da3d` allowed repository/global aliases that real Git dispatched to ticketless commits. | bounded effective-config lookup plus non-executing simple/prefixed/shell/chained expansion; cyclic/dynamic forms fail closed; add 14 block/pass regressions |
| R21 | P1 | Shell alias `!git -C inner commit` discarded its effective cwd and validated `-F` from the outer repository. | return reconstructed argv plus alias-selected cwd; add opposite file-content fixtures and real nested-repository execution proof |
| R22 | P1 | Commits before `&&`, absolute Git under pipe/`||`, and command-word expansions returned NOT_COMMIT and executed ticketless commits. | recursively classify every control segment; preserve absolute `cd &&`; fail closed on tokenizer errors with visible Git/commit words; add five negatives and three positives |
| R23 | P1 | Configured `!` aliases were parsed from caller cwd although Git starts them at repository top level. | resolve top level before shell alias parsing, then apply internal `-C`; add conflicting root/subdir fixtures and real execution proof |
| R24 | P1 | A preceding export/assignment could replace Git config after alias inspection and before dispatch. | fail closed when Git is combined with config lookup environment variables; cover export/assignment/env forms, positive control, and real proof |
| R25 | P1 | `command export`/`builtin export` or sourced scripts could mutate dispatch state before an unknown Git subcommand. | normalize builtin prefixes and fail closed for unknown Git dispatch after unsupported control-prefixes; preserve known-status positives |

## Test plan

- Syntax: Bash `-n`, Python 3.13 compile, and `git diff --check`.
- Focused: all scenarios in `ticket_required.test.sh` and `review_risk_policy.test.sh`.
- Packaging: full build, both consumer hook validators, and byte-identical shared helper in both packages.
- Full suite: the complete serial `build-and-publish.yml` validation command set plus every `hooks/_test/*.test.sh` file.
- Hosted: draft PR checks must pass before any merge decision.

## Quantified claims

- Focused ticket matrix: 154 scenarios pass, including configured alias/cwd/root/config-environment/prefix-mutation semantics and precision controls, commit-before-chain, absolute Git pipe/or, command-word expansions, four real Git dispatch proofs, and prior wrapper/retokenization/dynamic-dispatch attacks.
- Native commit/risk matrix: 19 scenarios pass.
- F4 risk matrix: `commit-message.py` rejects declared Tier B and the exhaustive graph plus modification/deletion/rename/downgrade suite passes.
- Full hook suite and serial CI matrix are rerun after the combined-tree evidence refresh and recorded in the replacement commit/PR evidence.
- Shared runtime: one parser is copied byte-identically into both `dist/claude-code/hooks/lib/` and `dist/craft-agent/hooks/lib/`.

## Rollback

Revert the issue #994 commits after the develop merge. The prior command-string behavior and F4 graph remain recoverable from history; no migration, deployment, release, or external state change is required. Existing native hooks remain source-controlled and protected checks still gate integration.
