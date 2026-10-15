# Pre-mortem: effective ticket commit-message enforcement (#994)

## Tiger 1 - Parser validates source spelling, not shell execution

**Severity:** CRITICAL
**Likelihood:** HIGH
**Failure:** A shell comment, expansion, wrapper, chain, heredoc descriptor, or `CDPATH` changes the arguments Git receives while the guard validates different text.
**Mitigation:** Never evaluate commands. Support a bounded literal command grammar, reject ambiguous shell transformations, and add negative fixtures for comments, chains, wrappers, relative `cd`, stdin, tilde/glob/brace expansion, and non-stdin heredocs.

## Tiger 2 - Message file escapes the repository

**Severity:** HIGH
**Likelihood:** MEDIUM
**Failure:** `-F` reads an arbitrary outside file or a symlink/path replacement changes the target after validation.
**Mitigation:** Resolve from `tool_input.cwd`, require the canonical target inside the repository, and open the canonical relative path through pinned directory descriptors with `O_NOFOLLOW`.

## Tiger 3 - Git option precedence is modeled incorrectly

**Severity:** HIGH
**Likelihood:** MEDIUM
**Failure:** Repeated `-m`/`-F`, `-C`/`-c`, templates, edit flags, or amend combinations produce a different message from the one validated.
**Mitigation:** Probe Git directly, model only deterministic combinations, and fail closed for editors, conflicts, unsupported message mutators, and unsafe cleanup modes.

## Tiger 4 - Native and pre-tool ticket rules drift

**Severity:** HIGH
**Likelihood:** HIGH
**Failure:** The pre-tool layer accepts Jira/task/override syntax that native `commit-msg` rejects, or native cleanup removes the only validated ticket.
**Mitigation:** Share one validator, test both layers, reject bare overrides first, require non-whitespace evidence, and make native validation ignore cleanup-removable comment/post-scissors text.

## Tiger 5 - Inputs exhaust hook memory

**Severity:** MEDIUM
**Likelihood:** MEDIUM
**Failure:** A large JSON command, heredoc, file, native message, or reused commit message is fully allocated before a size decision.
**Mitigation:** Enforce a 1 MiB boundary before shell/native reads, bound file descriptor reads, bound command reads, and stream reused revision output only to the limit.

## Tiger 6 - Security hardening blocks ordinary deterministic commits

**Severity:** MEDIUM
**Likelihood:** MEDIUM
**Failure:** Quoted spaces/newlines, quoted literal glob characters, or harmless long-form commit flags become false positives.
**Mitigation:** Track quote context for newlines, comments, heredocs, and pathname expansion; positive fixtures preserve quoted multiline `-m`, paths with spaces, quoted `?`, absolute `cd`, in-repository symlink targets, and long-form non-message flags.

## Tiger 7 - New enforcement helper falls below its callers' tier

**Severity:** HIGH
**Likelihood:** HIGH
**Failure:** A later helper-only modification, deletion, or rename changes ticket allow/block behavior while declaring Tier B.
**Mitigation:** Add the exact helper to the F4 Tier C path pattern, pin both real caller edges, and include it in exhaustive modification/deletion/rename/declared-B fixtures.

## Tiger 8 - Configured Git aliases hide commit dispatch

**Severity:** HIGH
**Likelihood:** MEDIUM
**Failure:** A repository/global alias expands a non-`commit` subcommand into `commit`, so the pre-tool parser returns NOT_COMMIT while Git creates a ticketless commit.
**Mitigation:** Read effective alias configuration with bounded NUL-delimited Git output; expand static aliases without execution; validate reconstructed commit argv and cwd; fail closed for cycles, dynamic content, malformed/oversized configuration, and unresolved shell dispatch; retain ticketed and non-commit positive controls.

## Tiger 9 - Commit dispatch appears outside the final simple-command segment

**Severity:** HIGH
**Likelihood:** MEDIUM
**Failure:** A commit before a control operator, an absolute Git executable, or command-word expansion escapes literal final-segment matching and returns NOT_COMMIT.
**Mitigation:** Recursively classify every control-separated segment; normalize executable basenames; preserve only the bounded absolute `cd &&` form; and fail closed on tokenizer errors when visible Git/commit words can be transformed by shell expansion. Pair each negative with unrelated status/expansion positives.

Implementation may proceed: YES
