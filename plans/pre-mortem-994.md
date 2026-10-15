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
**Failure:** Quoted spaces/newlines or quoted literal glob characters become false positives.
**Mitigation:** Track quote context for newlines, comments, heredocs, and pathname expansion; positive fixtures preserve quoted multiline `-m`, paths with spaces, quoted `?`, absolute `cd`, and in-repository symlink targets.

Implementation may proceed: YES
