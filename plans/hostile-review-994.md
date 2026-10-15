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
| H13 | S2 | CodeRabbit showed `bash -c`, `sh -c`, and `eval` can carry `git commit` inside one token and return NOT_COMMIT. | Shared raw-text detection now checks both joined argv and each token at every parsed non-commit exit; three direct hostile fixtures block. |
| H14 | S3 | CodeRabbit found harmless long forms `--quiet`, `--only`, `--include`, `--no-gpg-sign`, and `--no-signoff` were false-blocked while short forms passed. | All five non-message-mutating options are accepted and individually covered by positive fixtures. |
| H15 | S2 | After F4 merged to develop, the new authoritative `commit-message.py` helper still classified Tier B and was absent from the pinned graph. | The exact helper is Tier C; native and pre-tool caller edges are hash-pinned; exhaustive modification, deletion, rename, and declared-B fixtures include it. |
| H16 | S2 | A second hostile pass showed shell quote concatenation inside `bash -c` (`g"it" commit`) executes Git while evading literal raw-text detection. | Known shell/eval command strings are recursively analyzed without execution; direct, obfuscated, nested, or dynamically indeterminate commit-capable forms fail closed. |
| H17 | S2 | The first H16 remediation blocked every `bash -c`, `sh -c`, and `eval`, including demonstrably unrelated static scripts. | Static wrapper scripts are recursively tokenized; positive controls require unrelated `bash -c`, `sh -c`, and `eval` commands to return NOT_COMMIT while H16 exploits remain blocked. |
| H18 | S2 | A third hostile pass found `bash -c -- 'g"it" commit …'`: Bash treats `--` as an option terminator, but the analyzer stopped before the following script. | After `-c` is observed, `--` now terminates option parsing but preserves the next token as the command string; the exact executable exploit is a blocking fixture. |
| H19 | S2 | A fourth hostile pass found `bash -o pipefail -c …`: the analyzer mistook the `-o` operand for a script and never reached `-c`. | Command-option state tracks short `-c` clusters and `su --command` across intervening operands, optional `--`, and nested env forms; direct/nested exploits plus an unrelated option-bearing positive are fixtures. |
| H20 | S2 | A fifth hostile pass found util-linux-style `su -cSCRIPT`, where the short-option operand is attached and no next token exists. | For `su`, content after `c` in a short option cluster is recursively inspected as the script; exact blocking and unrelated positive fixtures pin the command-specific grammar. |
| H21 | S2 | A sixth hostile pass found `git -c alias.c='!git co"mmit" …' c`, where an inline Git alias dispatches a commit behind a non-commit subcommand. | Inline `-c` aliases are resolved across attached/separate definitions, static chains, shell aliases, assignment prefixes, and indeterminate `--config-env`; three commit exploits and two static non-commit controls are fixtures. |
| H22 | S2 | A corrected seventh hostile pass found BSD/GNU `env -S`/`--split-string`, which retokenizes one opaque operand into an obfuscated `sh -c` commit. | Split-string operands are recursively tokenized with the same bounded analysis; BSD short and GNU long exploits plus a static non-commit positive are fixtures. |
| H23 | S2 | An eighth hostile pass found `printf 'commit\\n' | xargs -I{} git {} …`, where input substitution supplies the Git subcommand after static parsing. | Pipelines where `xargs` visibly dispatches Git with a missing, placeholder, option-derived, or unknown/alias-capable subcommand fail closed; an unrelated `xargs echo` control passes. |
| H24 | S2 | A ninth hostile pass found `bash -c 'g"it" commit …' | cat`: control-token handling returned NOT_COMMIT before wrapper analysis. | Wrapper, inline-alias, and xargs dispatch checks now run across the full token list before any chain/pipeline exit; exact exploit and unrelated piped-wrapper fixtures pin ordering and non-interference. |
| H25 | S2 | A tenth hostile pass found GNU `xargs -a file … git @ …`: file-fed substitution needs no shell control token, so the ordinary non-Git exit skipped xargs analysis. | The same xargs→Git dynamic-subcommand check now precedes both control and ordinary non-Git exits; file-fed exploit and unrelated echo fixtures pin both paths. |

## Residual boundary

The parser deliberately does not emulate a shell or editor. Opaque pipes/stdin, editor-dependent messages, relative `cd`, shell expansion, unsupported Git globals, `--fixup`/`--squash`/`--trailer`, and cleanup modes that can remove content are blocked with a deterministic-source remedy. A concurrent actor can still change a message file after the pre-tool hook completes, but Git's native `commit-msg` hook validates the actual proposed message before commit creation.

## Verdict

No reviewed S1-S3 finding remains unresolved on the combined F1-F4 tree. The enforcement change remains Tier C and integration remains conditional on fresh protected hosted checks and reporter exact-SHA re-review.
