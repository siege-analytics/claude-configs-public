---
ticket_refs:
  - siege-analytics/claude-configs-public#1057: universal-mutation-gate blocks read-only commands
---

## Pre-Mortem
Task: port electinfo's positive read allowlist (electinfo/electinfo_claude_skills#349, deployed 2026-10-19) into `hooks/bash/universal-mutation-gate.sh`.
Ticket: siege-analytics/claude-configs-public#1057

### Tigers

#### Tiger 1: The allowlist proves a write is a read

Mitigation:
- It is a positive allowlist parsed with shlex; anything unrecognised falls through to the gate unchanged.
- It rejects `$()`, backticks, `<( >(`, heredocs, `&`, env prefixes, redirects except to `/dev/null`, and any multi-line command.
- `sed` is limited to exactly `-n Np [FILE]`. `jq` is limited to a filter, one file and display flags. `curl` and `awk` are not admitted.
- Three hostile-review rounds on the electinfo version (electinfo#349) found a denylist-only design, newline smuggling and quoted-ampersand false positives; all are fixed.
- Porting into this repo's `universal_mutation_gate_safelist` suite found `sed -i` permutation; also fixed. All 60 safelist cases pass.

#### Tiger 2: New indicators over-block reads

Mitigation:
- The indicators cover only writes: `git init/add/rm/mv/pull/clone/restore/switch/apply/worktree...`, `git -c` (#928), pip/npm/uv installs, `python -m venv`, `kill`/`pkill`, `gh api -X POST|PUT|PATCH|DELETE` and graphql mutations, fetch refspecs naming a local ref, and `git branch -f/-c/-u`.
- `universal_mutation_gate` passes 29/29.

### Launch-Blocking Assessment

None identified, provided the suites stay green at the head.
