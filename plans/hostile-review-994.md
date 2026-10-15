# Hostile review: effective ticket commit messages (#994)

## Scope

Independent reviews examined Git message-source semantics, shell parsing, arbitrary file reads, symlink/path races, cleanup timing, incidental argv bypasses, input bounds, and alignment between `ticket-required.sh` and native `commit-msg`.

## Findings and resolution

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| H1 | S1 | `git -c core.hooksPath=/dev/null commit ...` was classified as not-a-commit and could bypass both layers. | Any unsupported Git global option before `commit` now fails closed; hostile fixture added. |
| H2 | S2 | Newline-separated second commits were tokenized as one invocation. | Unquoted newlines are rejected while quoted multiline messages and heredoc bodies remain supported. |
| H3 | S2 | `--cleanup=strip`/`scissors` or configured cleanup could remove a validated ticket. | Pre-tool parsing rejects destructive explicit/configured cleanup; native validation ignores comment and post-scissors content. |
| H4 | S2 | Heredoc spelling inside a quoted argv value or on fd 2 could be mistaken for stdin. | Quote-aware operator detection accepts exactly one quoted fd-0 heredoc and rejects other descriptors. |
| H5 | S2 | Shell comments could hide a ticket-bearing `-m` from Git while the parser still counted it. | Quote-aware shell comment removal now precedes tokenization; direct negative fixtures cover hidden options and bare tickets. |
| H6 | S2 | Unquoted tilde/glob/brace expansion could make Git read a different `-F` path. | Unquoted pathname expansion fails closed; quoted literal pathname characters remain covered positively. |
| H7 | S2 | Relative `cd` could be redirected by `CDPATH`. | Only absolute `cd <path> && git commit` prefixes are supported. |
| H8 | S2 | File resolution had an intermediate-component replacement window. | Canonical targets must remain in-repository and are opened through pinned no-follow directory descriptors. |
| H9 | S2 | File/command/revision/native inputs were checked after potentially unbounded allocation. | All enforcement boundaries now cap input at 1 MiB before or during reads. |
| H10 | S3 | A structured override could mask a separate bare `[no-ticket]`; whitespace-only evidence/task text passed. | Bare markers are rejected before structured matching and all structured fields require non-whitespace content. |
| H11 | S2 | Native and pre-tool accepted ticket grammars diverged. | Both layers call `hooks/lib/commit-message.py`; native fixtures cover Jira, task, override rejection, cleanup, and size behavior. |
| H12 | S2 | Subshell grouping and wrappers could evade the direct command shape. | Parentheses are control tokens and unsupported wrappers/environment prefixes fail closed. |

## Residual boundary

The parser deliberately does not emulate a shell or editor. Opaque pipes/stdin, editor-dependent messages, relative `cd`, shell expansion, unsupported Git globals, `--fixup`/`--squash`/`--trailer`, and cleanup modes that can remove content are blocked with a deterministic-source remedy. A concurrent actor can still change a message file after the pre-tool hook completes, but Git's native `commit-msg` hook validates the actual proposed message before commit creation.

## Verdict

No reviewed S1-S3 finding remains unresolved. The enforcement change remains Tier C and merge remains conditional on protected hosted checks and reporter re-review.
