# Investigation: effective commit messages for ticket-required (#994)

## Failure premise

The pre-tool hook scanned the full shell command text rather than the message Git would use. This made `-F path` reject valid ticketed files and let any unrelated `#NNN` in argv satisfy the guard.

### Verified Shapes

**Current pre-tool behavior - PROBED.** A scoped fixture with `message file.txt` ending in `Refs: #331` returned exit 2 for `git commit -F "message file.txt"`. The same hook returned exit 0 for `git commit -m "subject without ticket" "unrelated-#994.txt"`.

**Git message source precedence - PROBED.** Temporary repositories established that repeated `-m` forms paragraphs, repeated `-F` uses the last file, `-m` conflicts with `-F`/`-C`/`-c`, `-C` is non-editing unless `--edit`, `-c` edits unless `--no-edit`, explicit `-m`/`-F` replaces `--amend --no-edit`, and templates are ignored beside deterministic explicit sources.

**Native hook timing - PROBED.** A capture hook showed `commit-msg` receives the proposed message before `--cleanup=strip` removes comment lines. Native validation therefore must ignore cleanup-removable comment and post-scissors content.

**Repository path boundary - PROBED.** `tool_input.cwd` can be a repository subdirectory; relative `-F` paths must resolve from that directory, canonicalize inside the worktree, and remain pinned during reading. Absolute or symlink-resolved targets outside the worktree must block.

**Shell transformation boundary - PROBED.** Shell comments, newlines, command chains, command substitution, tilde/glob/brace expansion, wrappers, relative `cd` under `CDPATH`, and opaque stdin can make shell execution differ from source spelling. They require an exact bounded parser or documented fail-closed treatment, never evaluation.

**F4 dependency boundary - PROBED.** On accepted develop commit `f97d194fedf1eda053a16e938851c6151f308d72`, `python3 bin/review-risk.py --paths hooks/lib/commit-message.py --declared B` returned valid Tier B even though both `ticket-required.sh` and native `commit-msg` trust the helper to allow or block commits. The accepted F4 audit provides exact helper-edge, modification, deletion, rename, and downgrade fixtures that can be extended narrowly.

**Configured alias boundary - PROBED.** On pushed candidate `140da3dafcaeebde35e6cc2e0fc4c0524ed76cce`, the real hook blocked direct `git commit -m 'subject only'` but returned allow for repository aliases `ci=commit`, `cm='commit -m'`, `c=commit`, and `save='!git commit'`; real Git then created four ticketless commits. Effective alias configuration therefore participates in command dispatch and must be inspected without executing alias content.

**Control/command-word boundary - PROBED.** The same real hook returned allow for `git commit --no-verify … && true`, absolute `/usr/bin/git commit … | cat`, absolute Git before `|| true`, `git${IFS}commit …`, and `$(echo git) commit …`; executing each command created a ticketless commit. Commit-capable segments must be classified regardless of position or executable path, and parser rejection of shell expansion must not collapse to NOT_COMMIT when Git/commit command text remains visible.

## Disposition

Implement one shared Python resolver/validator. The PreToolUse hook uses command mode; native `commit-msg` uses file mode and cleanup-stable validation. Supported deterministic forms are explicit and all uncertain forms fail closed with remediation.

## Reproduction evidence

- Before: valid `-F` ticket file -> exit 2.
- Before: unticketed `-m` plus unrelated `unrelated-#994.txt` argv -> exit 0.
- After: both outcomes reverse in `hooks/_test/ticket_required.test.sh`.
