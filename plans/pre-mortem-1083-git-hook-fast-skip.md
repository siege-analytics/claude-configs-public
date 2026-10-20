---
ticket_refs:
  - siege-analytics/claude-configs-public#1083: hooks start python3 ~33 times per Bash call
---

## Pre-Mortem
Task: let the 13 Bash hooks that act only on git/gh/glab commands, or on script execution, exit before starting python3 when the command cannot match their trigger.
Ticket: siege-analytics/claude-configs-public#1083

### Tigers

#### Tiger 1: A skip hides a real trigger (Severity: high)

Mitigation:
- Each skip pattern is the hook's own trigger regex, or a looser superset (branch-guard, post-error-revision-required, coordinator-status-guard).
- It is matched against the JSON `"command"` strings, after `\n`, `\t` and `\r` are turned into spaces. So a trigger after an escaped newline or tab still has a boundary.
- Payloads using any JSON escape other than `\n \t \r \" \\ \/` never skip. This covers `\u` (encoded letters), and `\f` and `\b`, which the hooks' `[[:space:]]` would treat as whitespace. The `\f` case was a review finding.
- The skip is taken only when `tool_input`'s first key is a non-empty `"command"`. An empty command keeps the hooks' git-push fallback; this was a review finding.
- coordinator-status-guard also tests the command with quotes removed, because shlex joins `g''h` into `gh`. This was a review finding.
- `hooks/_test/git_hook_fast_skip.test.sh` asserts 213 cases. Each compares the exit code with an oracle copy of the hooks that has the skip removed, and counts python3 starts. The trigger is checked plain, after a newline, after a tab, inside a compound, inside `bash -c`, and with escaped letters, a form feed, an empty command, a nested command and quoted gh.
- A replay of 2,845 real commands through all 13 hooks, old against new, shows 0 exit-code differences (73,970 runs).

#### Tiger 2: Git-hook invocations lose their fail-closed path (Severity: high)

Mitigation:
- The skip needs a JSON `"command"` string. Git hooks get refs on stdin, so they take the full path unchanged, including the "empty command in a repo means git push" fallback.
- The test covers this case for every hook.

#### Tiger 3: Portability (Severity: medium)

Mitigation:
- The skip uses `grep -oE` and bash `[[ =~ ]]` with POSIX classes only, which are available in BSD grep and bash 3.2 on macOS.
- The test avoids associative arrays.

### Launch-Blocking Assessment

None identified, provided the suites stay green at the head.
