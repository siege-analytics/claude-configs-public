---
ticket_refs:
  - siege-analytics/claude-configs-public#1083: hooks start python3 ~33 times per Bash call
---

# Hostile review: #1083 fast skip (PR #1084)

**Reviewer:** an independent agent separate from the author. Its brief was read-only. It ran crafted payloads against the HEAD (pre-#1083) and staged hooks, using `env -i PATH=/usr/bin:/bin HOME=<scratch>`, from a scratch repo on `main`.

**Scope:** for each of the 13 hooks, whether the skip pattern is a superset of everything the hook acts on.

## Confirmed gaps (first version)

1. **The `\f` (form feed) JSON escape was not normalised.**
   - The original `[[:space:]]+` matches a decoded form feed, but the skip saw `\f` and exited 0.
   - post-error-revision-required, payload `git\frevert HEAD`: original rc=2, staged rc=0.
   - pr-base-guard, payload `gh\fpr\fcreate --base main`: original rc=2, staged rc=0.
   - Five push/PR hooks entered their push logic in the original but skipped in the staged version (shown by trace).
2. **An empty or misplaced command skipped the git-push fallback.**
   - fix-shape-guard, self-review and test-tracking-guard treat an empty `tool_input.command` inside a repo as `git push`.
   - `"command":""` and a nested `command` key exited early. Trace: the original ran the push gate, the staged version did not.
3. **Shell-quoted `gh` in coordinator-status-guard.** The hook tokenises with shlex, so `g\\h`, `"g"h` and `g''h` all become `gh`.
   - Payload `g\\h issue close 5 --comment done`: original rc=2, staged rc=0.
4. **The test only counted python3 starts.** It never compared verdicts, and it had no cases for escapes, empty or nested commands, or quoted `gh`.

**No gap found:**
- no-attribution, ticket-required, no-broad-staging, no-sensitive-files;
- the handling of `\"`, `\\`, `\/`, multiple `command` keys and newline mapping;
- pr-base-guard's quote stripping.

## Resolution (all before merge, in PR #1084)

- **Gap 1:** any JSON escape other than `\n \t \r \" \\ \/` takes the full path. That covers `\u`, `\f` and `\b`.
- **Gap 2:** the skip is taken only when `tool_input`'s first key is a non-empty `"command"`.
- **Gap 3:** coordinator-status-guard also matches the command with quotes and backslashes removed.
- **Gap 4:** `hooks/_test/git_hook_fast_skip.test.sh` now compares every case's exit code with an oracle copy of `hooks/` that has the skip deleted, run from a git repo on `main`. It has 213 cases, including every gap above.
- **Verified:**
  - escape handling under bash 5.2.21 and bash 3.2.57 (`bash:3.2` image);
  - a corpus replay of 2,845 commands × 13 hooks with 0 exit-code differences.
