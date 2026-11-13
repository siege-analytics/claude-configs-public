---
ticket_refs:
  - siege-analytics/claude-configs-public#1371: design review summarised on the ticket (issuecomment-6850953261); PR closes it
  - siege-analytics/claude-configs-public#1372: class ticket; PR closes it
---
# Hostile review: refuse an admin merge in every gh spelling (#1371, #1372)

Reviewers: independent Claude subagents (same model family) with no authorship of the change. Each was given the code and the diff, not the author's conclusions, and was asked to refute. A cross-family review was not available: the cross-review source was inactive and failing its connection test, and ChatGPT connections were expired. Every round was read-only. The session's own gates blocked the reviewers' live probes, so their findings come from tracing the code. The author verified every adopted finding with a test row run through the real UMG, helper and destructive-guard.

## Design review: ACCEPT WITH CHANGES

P1/P2 classes, all adopted before implementation:

- whitespace that bash and the shared tokenizer split differently;
- gh run through a wrapper;
- a destructive-guard helper exit-code fail-open;
- gh under another name;
- gh alias definitions;
- over-refusal and scope wording (P3).

## Code review, round 1: REQUEST CHANGES

- **P1:** gh run by argument-supplying wrappers. Fixed: a wrapped gh must be visibly not a merge.
- **P2:**
  - shell alias definitions;
  - untokenisable text checked only for a literal flag.
  - Fixed: stripped-text rule, and shell alias refusal.
- **P3:**
  - a pipe in the destructive-guard fallback (replaced by bash parameter expansion);
  - inconsistent fault handling (the helper now exits 4, and destructive-guard falls back to text);
  - alias-check placement;
  - a stale test comment;
  - redirect regex;
  - the `require` idiom.
- **Kept fail-closed, with reason:** heredoc bodies are inspected as commands. The tokenizer cannot tell a newline from `;`, so skipping a "body" could hide a same-line command.

## Code review, round 2: REQUEST CHANGES

- **P1/P2:**
  - shells reached through a wrapper and reading stdin;
  - `-c` script selection with options in between.
  - Fixed: the runner's words, and all of them joined, are inspected recursively. A runner fed by a pipe or redirect without a program operand is refused.
- **P3:**
  - interpreters;
  - wrapped built-in gh groups over-refused;
  - alias substring.
  - Fixed: the built-in group list was widened; `_GH_WORD` is used for the alias check.

## Code review, round 3: REQUEST CHANGES (P2)

- **Fixed:**
  - stdin rule bypassed through a stdin pseudo-file or `-s`;
  - wrappers missing from the list (now reusing `_WRAPPER_VALUES`);
  - runner names (now a versioned-name pattern including awk, pwsh and others);
  - a regression on inline code that mentions an admin module (program text now also needs a gh word).
- **Not fixed here, routed:** the UMG refuses opaque runners only as `args[0]`, so wrapped runners reach the generic cwd model for any mutation. That is a general class beyond this ticket; the coordinating hub routed it to a separate class-level issue.

## Code review, round 4: REQUEST CHANGES (P2)

- **Fixed:**
  - shell `-e` treated as inline code;
  - option values taken as the program operand;
  - `|&` resetting the fed state;
  - stdin paths that need normalisation;
  - ssh remote stdin shells.
- **Result:** in a fed segment, a runner now needs inline code or a script-file operand.

## Code review, round 5: REQUEST CHANGES (P2)

- **Fixed:**
  - inline-code detection matched any later word, including positional parameters;
  - the non-shell flag set was too broad;
  - python's interactive modules.
- **Result:**
  - options are scanned only before the first operand, `--`, `-` or `-s`;
  - each runner has its own inline-code flag;
  - python `-m` is accepted only for an allow-list.
- **Recorded as residual:**
  - a script-file symlink to stdin created in the same command;
  - extensionless piped scripts are refused (accepted limitation).

## Code review, round 6 (final): one P2, fixed

- Case-insensitive inline-flag matching let option letters with a different meaning (noclobber, encoding) count as inline code. Matching is now case-sensitive, with explicit spellings where a runner accepts both.
- The reviewer reported no remaining P1/P2 outside the stated residual classes once this was fixed. The fix and its three regression rows were applied afterwards and are covered by the focused and full suites.

## Full-suite regression and code review, round 7

- **The regression:** the full hook suite caught one after round 6. `universal_mutation_gate_ssh` failed 7 rows:
  - The allowed allowlisted-ssh "stdin script from a file" shapes (#1171 D2a) were refused.
  - Existing deny rows lost their specific messages.
- **Fixed:**
  - A plain `<` file no longer counts as feeding a program, because it is the scripts-in-files residual. Pipes and the heredoc family still count.
  - The piped-program refusal is applied after the ordinary resolution, and only when the gate would otherwise admit the command. Every other refusal keeps its own message, and a piped program is still never admitted.
- **Round 7 (REQUEST CHANGES, one latent P2, fixed):** the admission mirror must not let an `error` cancel read-only, early-allow or gate admission, because the shell ignores `error` in those cases.
- **After the fix:** the ssh suite is 179/0 and the focused suite 27 OK. The reviewer found no other P1/P2.

## Dogfooding fix and code review, round 8: APPROVE

- **The problem:** the live gate refused a harmless read. The worktree path contains "admin", and an untokenisable `$` sent the command to the text fallback, which refused on "admin" anywhere.
- **Fixed:**
  - The fallback now needs admin text together with a gh word or merge text, or merge text together with a gh word.
  - In the UMG, it is applied only when the ordinary path would otherwise admit the command, the same deferral as the piped-program refusal.
- **Known consequence:** text that hides both the gh word and merge passes destructive-guard. The UMG still refuses it, and it falls inside the "commands assembled at runtime" residual.
- **Round 8:** APPROVE, no P1/P2.

## Residuals (stated in the PR)

- interpreters or wrappers not in the lists;
- scripts in files;
- gh aliases already in the user's config;
- commands assembled at runtime (the UMG refuses expansion shapes; destructive-guard covers them only through its text fallback);
- the shared-tokenizer whitespace class in other guards and the UMG wrapped-runner gap, both routed separately.

The real guarantee is server-side: no bypass actors, and non-admin tokens.
